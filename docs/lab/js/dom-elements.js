//
// DOM Elements - organized by category
export const DOM_ELEMENTS = {
  controls: {
    spinner: document.getElementById("spinner"),
    resetButton: document.getElementById("reset-button"),
    fabButton: document.getElementById("fab-button"),
    nextStepButton: document.getElementById("next-step-button"),
  },
  // there is a one-to-one mapping between input and option controls.
  inputs: {
    citySize: document.getElementById("input-city-size"),
    vehicleCount: document.getElementById("input-vehicle-count"),
    requestRate: document.getElementById("input-request-rate"),
    maxTripDistance: document.getElementById("input-max-trip-distance"),
    inhomogeneity: document.getElementById("input-inhomogeneity"),
    price: document.getElementById("input-price"),
    platformCommission: document.getElementById("input-platform-commission"),
    reservationWage: document.getElementById("input-reservation-wage"),
    demandElasticity: document.getElementById("input-demand-elasticity"),
    meanVehicleSpeed: document.getElementById("input-mean-vehicle-speed"),
    perKmPrice: document.getElementById("input-per-km-price"),
    perMinutePrice: document.getElementById("input-per-minute-price"),
    perKmOpsCost: document.getElementById("input-per-km-ops-cost"),
    perHourOpportunityCost: document.getElementById(
      "input-per-hour-opportunity-cost"
    ),
    frameTimeout: document.getElementById("input-frame-timeout"),
    smoothingWindow: document.getElementById("input-smoothing-window"),
  },
  options: {
    citySize: document.getElementById("option-city-size"),
    vehicleCount: document.getElementById("option-vehicle-count"),
    requestRate: document.getElementById("option-request-rate"),
    maxTripDistance: document.getElementById("option-max-trip-distance"),
    inhomogeneity: document.getElementById("option-inhomogeneity"),
    price: document.getElementById("option-price"),
    platformCommission: document.getElementById("option-platform-commission"),
    reservationWage: document.getElementById("option-reservation-wage"),
    demandElasticity: document.getElementById("option-demand-elasticity"),
    meanVehicleSpeed: document.getElementById("option-mean-vehicle-speed"),
    perKmPrice: document.getElementById("option-per-km-price"),
    perMinutePrice: document.getElementById("option-per-minute-price"),
    perKmOpsCost: document.getElementById("option-per-km-ops-cost"),
    perHourOpportunityCost: document.getElementById(
      "option-per-hour-opportunity-cost"
    ),
    frameTimeout: document.getElementById("option-frame-timeout"),
    smoothingWindow: document.getElementById("option-smoothing-window"),
  },
  displays: {
    frameCount: document.getElementById("frame-count"),
    spinner: document.getElementById("top-control-spinner"),
  },
  checkboxes: {
    equilibrate: document.getElementById("checkbox-equilibrate"),
  },
  canvases: {
    labMap: document.getElementById("lab-map-chart-canvas"),
    labCity: document.getElementById("lab-city-chart-canvas"),
    labPhases: document.getElementById("lab-phases-chart-canvas"),
    labTrip: document.getElementById("lab-trip-chart-canvas"),
    labIncome: document.getElementById("lab-income-chart-canvas"),
  },
  charts: {
    chartColumn: document.getElementById("chart-column"),
  },
  whatIf: {
    resetButton: document.getElementById("what-if-reset-button"),
    baselineFabButton: document.getElementById("what-if-baseline-fab-button"),
    comparisonFabButton: document.getElementById(
      "what-if-comparison-fab-button"
    ),
    setComparisonButtons: document.querySelectorAll(
      ".what-if-set-comparison button"
    ),
    baselineRadios: document.querySelectorAll(
      'input[type=radio][name="what-if-radio-baseline"]'
    ),
    baselinePreset: document.getElementById("what-if-radio-baseline-preset"),
    frameCount: document.getElementById("what-if-frame-count"),
    canvasParents: document.querySelectorAll(".what-if-canvas-parent"),
    canvases: {
      phases: document.getElementById("what-if-phases-chart-canvas"),
      income: document.getElementById("what-if-income-chart-canvas"),
      wait: document.getElementById("what-if-wait-chart-canvas"),
      n: document.getElementById("what-if-n-chart-canvas"),
      demand: document.getElementById("what-if-demand-chart-canvas"),
      platform: document.getElementById("what-if-platform-chart-canvas"),
    },
    settingsTable: document.getElementById("what-if-table-settings"),
    measuresTable: document.getElementById("what-if-table-measures"),
    chartColumn: document.getElementById("what-if-chart-column"),

    //document.querySelectorAll(".what-if-chart-canvas").
  },
  collections: {
    tabList: document.querySelectorAll(".mdl-layout__tab"),
    resetControls: document.querySelectorAll(".ui-mode-reset input"),
    equilibrateControls: document.querySelectorAll(".ui-mode-equilibrate"),
    canvasParents: document.querySelectorAll(".lab-canvas-parent"),
    advancedControls: document.querySelectorAll(".ui-mode-advanced"),
    simpleControls: document.querySelectorAll(".ui-mode-simple"),
    scaleRadios: document.querySelectorAll('input[type=radio][name="scale"]'),
    uiModeRadios: document.querySelectorAll(
      'input[type=radio][name="ui-mode"]'
    ),
    getSelectedUiMode() {
      return Array.from(this.uiModeRadios).find((radio) => radio.checked)
        ?.value;
    },
    chartTypeRadios: document.querySelectorAll(
      'input[type=radio][name="chart-type"]'
    ),
    statsDescriptions: document.querySelectorAll(".lab-stats-descriptions"),
    zoom: document.querySelectorAll(".ui-zoom-hide"),
  },
};
