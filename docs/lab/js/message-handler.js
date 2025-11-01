/*
 * Listen to and handle messages coming *from* webworker.js
 * These messages are either simulation results or simple
 * text strings (error messages, status messages).
 * They arrive in the form of event.data
 */

import { CHART_TYPES } from "./constants.js";
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
  constructor(handlePyodideReady, updateBlockCounters) {
    this.handlePyodideReady = handlePyodideReady;
    this.updateBlockCounters = updateBlockCounters;
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

      if (results.size <= 1) {
        return this.handleSingleResult(results);
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

      if (results.has("vehicles")) {
        messageHandlers.vehicles();
      } else {
        const handler = messageHandlers[results.get("chartType")];
        if (handler) {
          handler();
        }
      }

      this.updateBlockCounters(results);
    } catch (error) {
      console.error("Error in message handler:", error.message, error.stack);
    }
  }

  handleSingleResult(results) {
    if (results.get("text") === "Pyodide loaded") {
      this.handlePyodideReady();
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
