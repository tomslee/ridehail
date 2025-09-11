/*
 * Listen to and handle messages coming *from* webworker.js
 * These messages are either simulation results or simple
 * text strings (error messages, status messages).
 * They arrive in the form of event.data
 */

import { CHART_TYPES } from "./config.js";
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
import { DOM_ELEMENTS } from "./dom-elements.js";

export class MessageHandler {
  constructor(handlePyodideReady, updateFrameCounters) {
    this.handlePyodideReady = handlePyodideReady;
    this.updateFrameCounters = updateFrameCounters;
    this.setupWorker();
  }

  setupWorker() {
    // The worker (webworker.js) posts messages. Listen
    // to them here with w.onmessage, which provides
    // an event
    if (typeof w === "undefined") {
      // var w = new Worker("webworker.js", { type: "module" });
      window.w = new Worker("webworker.js");
    }
    w.onmessage = (event) => this.handleMessage(event);
  }

  handleMessage(event) {
    const results = new Map(Object.entries(event.data));

    try {
      if (results.size <= 1) {
        return this.handleSingleResult(results);
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

      this.updateFrameCounters(results);
    } catch (error) {
      console.error("Error in message handler:", error.message, error.stack);
    }
  }

  handleSingleResult(results) {
    if (results.get("text") === "Pyodide loaded") {
      this.handlePyodideReady();
    } else {
      console.log("Error in main: results=", results);
    }
  }

  handleStatsMessage(results) {
    plotCityChart(results);
    plotPhasesChart(results);
    plotTripChart(results);
    plotIncomeChart(results);
  }

  handleWhatIfMessage(results) {
    plotWhatIfNChart(baselineData, results);
    plotWhatIfDemandChart(baselineData, results);
    plotWhatIfPhasesChart(baselineData, results);
    plotWhatIfIncomeChart(baselineData, results);
    plotWhatIfWaitChart(baselineData, results);
    plotWhatIfPlatformChart(baselineData, results);

    const frameIndex = results.get("block");
    if (frameIndex % 10 === 0) {
      fillWhatIfSettingsTable(whatIfController.baselineData, results);
      fillWhatIfMeasuresTable(whatIfController.baselineData, results);
    }
  }
}
