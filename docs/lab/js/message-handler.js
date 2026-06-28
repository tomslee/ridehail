/*
 * Listen to and handle messages coming *from* webworker.js
 * These messages are either simulation results or simple
 * text strings (error messages, status messages).
 * They arrive in the form of event.data
 */

import { CHART_TYPES, SimulationActions } from "./constants.js";
import { appState } from "./app-state.js";
import { checkVehicleCountChange } from "./vehicle-count-monitor.js";
import {
  plotCityChart,
  plotPhasesChart,
  plotTripChart,
  plotIncomeChart,
} from "../modules/stats.js";
import { plotMap } from "../modules/map.js";
import {
  plotWhatIfNChart,
  plotWhatIfDemandChart,
  plotWhatIfPhasesChart,
  plotWhatIfIncomeChart,
  plotWhatIfWaitChart,
  plotWhatIfPlatformChart,
  fillWhatIfSettingsTable,
  fillWhatIfMeasuresTable,
} from "../modules/whatif.js";

export class MessageHandler {
  constructor(handlePyodideReady, updateBlockCounters, handleSliderHelp) {
    this.handlePyodideReady = handlePyodideReady;
    this.updateBlockCounters = updateBlockCounters;
    this.handleSliderHelp = handleSliderHelp;
    this.resultsCallback = null; // Callback for results requests
    this.setupWorker();
  }

  setupWorker() {
    // The worker (webworker.js) posts messages. Listen
    // to them here with w.onmessage, which provides
    // an event
    if (typeof w === "undefined") {
      window.w = new Worker("webworker.js", { type: "module" });
    }
    w.onmessage = (event) => this.handleMessage(event);
  }

  handleMessage(event) {
    // the message is usually a set of results, held as an object
    // in event.data. Cast it into a Map here for easier processing
    // especially, I think, in the charts.
    const results = new Map(Object.entries(event.data));

    try {
      // Check for results response (for config download)
      if (results.get("action") === "results") {
        if (this.resultsCallback) {
          this.resultsCallback(event.data.results);
          this.resultsCallback = null;
        }
        return;
      }

      // The "Pyodide loaded" message also carries a "version" field (see
      // webworker.js), so it's no longer guaranteed to be size 1 - match on
      // "text" explicitly rather than tightening the implicit size<=1 rule.
      // Error messages ({error, message, stack}, see webworker.js's catch
      // blocks) are also 2-3 keys with neither "text" nor size<=1, so without
      // matching on "error" explicitly they fell through to the simulation
      // frame path below instead of reaching handleWorkerError: an ack got
      // sent (harmless), but chartType/name are both undefined on an error
      // object, so neither messageHandlers nor updateBlockCounters found a
      // match and the error vanished into a console.log with no alert and no
      // indication anything had failed - e.g. a Python ConfigValidationError
      // from init_simulation would silently and permanently stall whichever
      // run hit it, with no visible cause and no way to tell from the UI.
      if (results.has("text") || results.has("error") || results.size <= 1) {
        return this.handleSingleResult(results);
      }

      // From here on, this is a simulation frame, and the worker is waiting
      // for an ack before it produces the next one (backpressure - see
      // webworker.js/scheduleNextFrame): without this, the worker has no way
      // to know whether we're keeping up, so it just kept self-pacing on its
      // own timer regardless of render speed, letting it run arbitrarily far
      // ahead whenever rendering was slower than animationDelay.
      //
      // Ack immediately, before doing any of the (potentially slow)
      // rendering work below: that lets the worker start computing/
      // marshalling the *next* frame while this one is still being rendered
      // here, instead of only after rendering finishes. Measurement showed
      // rendering (plotMap's synchronous work) taking tens of ms per frame
      // on Town scale, and that time was landing entirely in front of the
      // worker's own pacing/compute pipeline because the ack used to wait
      // for it - inflating the real gap between frames well past
      // animationDelay. This still caps the worker at one frame ahead of
      // what's been dequeued here (scheduleNextFrame only produces one frame
      // per ack), so a render that's genuinely slower than the worker's
      // production rate still throttles it - it just overlaps the two
      // instead of serializing them.
      w.postMessage({ action: SimulationActions.FrameAck });

      // `action` is set synchronously on click (before the Pause message
      // even reaches the worker), so any frame arriving while paused is
      // necessarily stale - drop it rather than animate through it, so
      // Pause feels instant.
      if (this._simSettingsFor(results)?.action === SimulationActions.Pause) {
        return;
      }

      // Check for vehicle count changes (only for lab experiment, not What If comparisons)
      const chartType = results.get("chartType");
      if (chartType !== CHART_TYPES.WHAT_IF) {
        checkVehicleCountChange(results);
      }

      const messageHandlers = {
        vehicles: () => plotMap(results),
        [CHART_TYPES.STATS]: () => this.handleStatsMessage(results),
        [CHART_TYPES.WHAT_IF]: () => this.handleWhatIfMessage(results),
      };

      // Isolate rendering from the block-counter update: a throw in any chart
      // or table render must NOT prevent updateBlockCounters from running.
      // Otherwise a single bad render (e.g. an unmapped settings key in
      // fillWhatIfSettingsTable) freezes the counter at 0 while the worker
      // keeps producing frames - an unrecoverable, silent stall.
      try {
        if (results.has("vehicles")) {
          messageHandlers.vehicles();
        } else {
          const handler = messageHandlers[results.get("chartType")];
          if (handler) {
            handler();
          }
        }
      } catch (renderError) {
        console.error(
          "Error rendering frame (block counter still advances):",
          renderError.message,
          renderError.stack
        );
      }

      this.updateBlockCounters(results);
    } catch (error) {
      console.error("Error in message handler:", error.message, error.stack);
    }
  }

  /**
   * Resolve the SimSettings instance that controls a given results message,
   * keyed by the `name` field the worker echoes back in every frame.
   */
  _simSettingsFor(results) {
    const name = results.get("name");
    if (name === "whatIfSimSettingsBaseline") {
      return appState.whatIfSimSettingsBaseline;
    } else if (name === "whatIfSimSettingsComparison") {
      return appState.whatIfSimSettingsComparison;
    }
    return appState.labSimSettings;
  }

  handleSingleResult(results) {
    if (results.get("text") === "Pyodide loaded") {
      this.handlePyodideReady(results.get("version"));
      if (this.handleSliderHelp && results.has("sliderHelp")) {
        this.handleSliderHelp(results.get("sliderHelp"));
      }
    } else if (results.has("error")) {
      // Handle error messages from worker
      this.handleWorkerError(results);
    } else {
      console.error(
        "Error in messageHandler.handleSingleResult: results=",
        results,
      );
    }
  }

  handleWorkerError(results) {
    const errorType = results.get("error");
    const message = results.get("message");
    const stack = results.get("stack");

    console.error(`Worker error (${errorType}):`, message);
    if (stack) {
      console.error("Stack trace:", stack);
    }

    // Show user-friendly error message
    const errorMessages = {
      initialization:
        "Failed to initialize simulation engine. Please refresh the page.",
      simulation: "Simulation error occurred. Check console for details.",
      unknown: "An unexpected error occurred in the simulation worker.",
    };

    const userMessage = errorMessages[errorType] || errorMessages.unknown;

    // Display error to user (you can customize this with a toast/modal)
    alert(`Error: ${userMessage}\n\nDetails: ${message}`);
  }

  handleStatsMessage(results) {
    plotCityChart(results);
    plotPhasesChart(results);
    plotTripChart(results);
    plotIncomeChart(results);
  }

  handleWhatIfMessage(results) {
    // During baseline simulation, pass null for baselineData so only one bar shows
    // During comparison simulation, pass the stored baseline data so both bars show
    const isBaselineSimulation =
      results.get("name") === "whatIfSimSettingsBaseline";
    const baselineData = isBaselineSimulation
      ? null
      : appState.getBaselineData();

    plotWhatIfNChart(baselineData, results);
    plotWhatIfDemandChart(baselineData, results);
    plotWhatIfPhasesChart(baselineData, results);
    plotWhatIfIncomeChart(baselineData, results);
    plotWhatIfWaitChart(baselineData, results);
    plotWhatIfPlatformChart(baselineData, results);

    const frameIndex = results.get("frame");
    if (frameIndex % 10 === 0) {
      const baselineSimSettings = appState.whatIfSimSettingsBaseline;
      const comparisonSimSettings = isBaselineSimulation
        ? null
        : appState.whatIfSimSettingsComparison;
      fillWhatIfSettingsTable(baselineSimSettings, comparisonSimSettings);
      fillWhatIfMeasuresTable(baselineData, results);
    }
  }

  /**
   * Request simulation results from the worker for config download
   * @returns {Promise<Object>} Promise that resolves with simulation results dictionary
   */
  requestSimulationResults() {
    return new Promise((resolve) => {
      this.resultsCallback = resolve;
      w.postMessage({ action: "getResults" });
    });
  }
}
