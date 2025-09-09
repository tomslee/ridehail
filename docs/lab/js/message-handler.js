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
    const resultsMap = new Map(Object.entries(event.data));

    try {
      if (resultsMap.size <= 1) {
        return this.handleSingleResult(resultsMap);
      }

      const messageHandlers = {
        vehicles: () => plotMap(resultsMap),
        [CHART_TYPES.STATS]: () => this.handleStatsMessage(resultsMap),
        [CHART_TYPES.WHAT_IF]: () => this.handleWhatIfMessage(resultsMap),
      };

      if (resultsMap.has("vehicles")) {
        messageHandlers.vehicles();
      } else {
        const handler = messageHandlers[resultsMap.get("chartType")];
        if (handler) {
          handler();
        }
      }

      this.updateFrameCounters(resultsMap);
    } catch (error) {
      console.error("Error in message handler:", error.message, error.stack);
    }
  }

  handleSingleResult(resultsMap) {
    if (resultsMap.get("text") === "Pyodide loaded") {
      this.handlePyodideReady();
    } else {
      console.log("Error in main: resultsMap=", resultsMap);
    }
  }

  handleStatsMessage(resultsMap) {
    plotCityChart(resultsMap);
    plotPhasesChart(resultsMap);
    plotTripChart(resultsMap);
    plotIncomeChart(resultsMap);
  }

  handleWhatIfMessage(resultsMap) {
    plotWhatIfNChart(whatIfController.baselineData, resultsMap);
    plotWhatIfDemandChart(whatIfController.baselineData, resultsMap);
    plotWhatIfPhasesChart(whatIfController.baselineData, resultsMap);
    plotWhatIfIncomeChart(whatIfController.baselineData, resultsMap);
    plotWhatIfWaitChart(whatIfController.baselineData, resultsMap);
    plotWhatIfPlatformChart(whatIfController.baselineData, resultsMap);

    const frameIndex = resultsMap.get("block");
    if (frameIndex % 10 === 0) {
      fillWhatIfSettingsTable(whatIfController.baselineData, resultsMap);
      fillWhatIfMeasuresTable(whatIfController.baselineData, resultsMap);
    }
  }
}
