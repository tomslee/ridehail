/**
 * Unified Application State Manager
 *
 * Centralizes all shared state across the ridehail simulation application.
 * Replaces scattered global variables with a single, managed state container.
 */

import { SimSettings, WhatIfSimSettingsDefault } from "./sim-settings.js";
import { SCALE_CONFIGS, CHART_TYPES, CITY_SCALE } from "./config.js";
import { DOM_ELEMENTS } from "./dom-elements.js";

export class AppState {
  constructor() {
    // Simulation settings
    this._labSimSettings = null;
    this._whatIfSimSettingsBaseline = null;
    this._whatIfSimSettingsComparison = null;

    // Data storage
    this._baselineData = null;

    // UI settings
    this._labUISettings = null;
    this._whatIfUISettings = null;

    // Chart management (replaces window.chart usage)
    this._charts = new Map();

    // Vehicle count tracking for equilibration notifications
    this._previousVehicleCount = null;

    this._initialized = false;
  }

  /**
   * Initialize the app state with default values
   */
  initialize() {
    if (this._initialized) return;

    // Initialize simulation settings
    this._labSimSettings = new SimSettings(
      SCALE_CONFIGS.village,
      "labSimSettings",
    );
    this._whatIfSimSettingsBaseline = new WhatIfSimSettingsDefault();
    this._whatIfSimSettingsComparison = new WhatIfSimSettingsDefault();
    this._whatIfSimSettingsBaseline.name = "whatIfSimSettingsBaseline";
    this._whatIfSimSettingsComparison.name = "whatIfSimSettingsComparison";

    // Initialize UI settings
    this._labUISettings = {
      ctxCity: DOM_ELEMENTS.canvases.labCity.getContext("2d"),
      ctxPhases: DOM_ELEMENTS.canvases.labPhases.getContext("2d"),
      ctxTrip: DOM_ELEMENTS.canvases.labTrip.getContext("2d"),
      ctxIncome: DOM_ELEMENTS.canvases.labIncome.getContext("2d"),
      ctxMap: DOM_ELEMENTS.canvases.labMap.getContext("2d"),
      chartType: CHART_TYPES.MAP,
      scale: CITY_SCALE.VILLAGE,
      displayVehicleRadius: 9,
      displayRoadWidth: 10,
    };

    this._whatIfUISettings = {
      ctxWhatIfN: DOM_ELEMENTS.whatIf.canvases.n.getContext("2d"),
      ctxWhatIfDemand: DOM_ELEMENTS.whatIf.canvases.demand.getContext("2d"),
      ctxWhatIfPhases: DOM_ELEMENTS.whatIf.canvases.phases.getContext("2d"),
      ctxWhatIfIncome: DOM_ELEMENTS.whatIf.canvases.income.getContext("2d"),
      ctxWhatIfWait: DOM_ELEMENTS.whatIf.canvases.wait.getContext("2d"),
      ctxWhatIfPlatform: DOM_ELEMENTS.whatIf.canvases.platform.getContext("2d"),
      chartType: CHART_TYPES.WHAT_IF,
      settingsTable: DOM_ELEMENTS.whatIf.settingsTable,
      measuresTable: DOM_ELEMENTS.whatIf.measuresTable,
    };

    this._initialized = true;
  }

  // === Simulation Settings ===

  get labSimSettings() {
    return this._labSimSettings;
  }

  set labSimSettings(value) {
    this._labSimSettings = value;
  }

  get whatIfSimSettingsBaseline() {
    return this._whatIfSimSettingsBaseline;
  }

  set whatIfSimSettingsBaseline(value) {
    this._whatIfSimSettingsBaseline = value;
  }

  get whatIfSimSettingsComparison() {
    return this._whatIfSimSettingsComparison;
  }

  set whatIfSimSettingsComparison(value) {
    this._whatIfSimSettingsComparison = value;
  }

  // === Baseline Data Management ===

  setBaselineData(data) {
    this._baselineData = data;
  }

  getBaselineData() {
    return this._baselineData;
  }

  hasBaselineData() {
    return this._baselineData !== null;
  }

  clearBaselineData() {
    this._baselineData = null;
  }

  // === UI Settings ===

  get labUISettings() {
    return this._labUISettings;
  }

  set labUISettings(value) {
    this._labUISettings = value;
  }

  get whatIfUISettings() {
    return this._whatIfUISettings;
  }

  set whatIfUISettings(value) {
    this._whatIfUISettings = value;
  }

  // === Chart Management ===

  /**
   * Store a chart instance with a given key
   * @param {string} key - Unique identifier for the chart
   * @param {Chart} chart - Chart.js instance
   */
  setChart(key, chart) {
    // Destroy existing chart if it exists
    if (this._charts.has(key)) {
      const existingChart = this._charts.get(key);
      if (existingChart && typeof existingChart.destroy === "function") {
        existingChart.destroy();
      }
    }
    this._charts.set(key, chart);
  }

  /**
   * Get a chart instance by key
   * @param {string} key - Chart identifier
   * @returns {Chart|undefined} Chart instance or undefined if not found
   */
  getChart(key) {
    return this._charts.get(key);
  }

  /**
   * Check if a chart exists
   * @param {string} key - Chart identifier
   * @returns {boolean} True if chart exists
   */
  hasChart(key) {
    return this._charts.has(key);
  }

  /**
   * Remove and destroy a chart
   * @param {string} key - Chart identifier
   */
  removeChart(key) {
    if (this._charts.has(key)) {
      const chart = this._charts.get(key);
      if (chart && typeof chart.destroy === "function") {
        chart.destroy();
      }
      this._charts.delete(key);
    }
  }

  /**
   * Destroy all charts
   */
  destroyAllCharts() {
    for (const [key, chart] of this._charts) {
      if (chart && typeof chart.destroy === "function") {
        chart.destroy();
      }
    }
    this._charts.clear();
  }

  // === Vehicle Count Tracking ===

  /**
   * Get the previous vehicle count
   * @returns {number|null} Previous vehicle count or null if not set
   */
  get previousVehicleCount() {
    return this._previousVehicleCount;
  }

  /**
   * Set the previous vehicle count
   * @param {number|null} value - Vehicle count to store
   */
  set previousVehicleCount(value) {
    this._previousVehicleCount = value;
  }

  /**
   * Check if previous vehicle count has been set
   * @returns {boolean} True if previous vehicle count exists
   */
  hasPreviousVehicleCount() {
    return this._previousVehicleCount !== null;
  }

  // === Utility Methods ===

  /**
   * Reset state to initial values (useful for testing or resetting the app)
   */
  reset() {
    this.clearBaselineData();
    this.destroyAllCharts();
    this._initialized = false;
    this.initialize();
  }

  /**
   * Get a summary of current state for debugging
   */
  getStateDebugInfo() {
    return {
      initialized: this._initialized,
      hasBaselineData: this.hasBaselineData(),
      chartCount: this._charts.size,
      labSimSettingsScale: this._labSimSettings?.scale,
      labUIChartType: this._labUISettings?.chartType,
    };
  }
}

// Export singleton instance
export const appState = new AppState();
