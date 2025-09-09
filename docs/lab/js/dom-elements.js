//
// DOM Elements - organized by category
export const DOM_ELEMENTS = {
  controls: {
    spinner: document.getElementById("spinner"),
    resetButton: document.getElementById("reset-button"),
    fabButton: document.getElementById("fab-button"),
    nextStepButton: document.getElementById("next-step-button"),
  },
  inputs: {
    citySize: document.getElementById("input-city-size"),
    maxTripDistance: document.getElementById("input-max-trip-distance"),
    vehicleCount: document.getElementById("input-vehicle-count"),
    requestRate: document.getElementById("input-request-rate"),
    inhomogeneity: document.getElementById("input-two-zone"),
    meanVehicleSpeed: document.getElementById("input-mean-vehicle-speed"),
    price: document.getElementById("input-price"),
    perKmPrice: document.getElementById("input-per-km-price"),
    perMinutePrice: document.getElementById("input-per-minute-price"),
    demandElasticity: document.getElementById("input-demand-elasticity"),
    platformCommission: document.getElementById("input-platform-commission"),
    reservationWage: document.getElementById("input-reservation-wage"),
    perKmOpsCost: document.getElementById("input-per-km-ops-cost"),
    perHourOpportunityCost: document.getElementById(
      "input-per-hour-opportunity-cost"
    ),
    frameTimeout: document.getElementById("input-frame-timeout"),
    smoothingWindow: document.getElementById("input-smoothing-window"),
  },
  displays: {
    frameCount: document.getElementById("frame-count"),
    spinner: document.getElementById("top-control-spinner"),
  },
  options: {
    citySize: document.getElementById("option-city-size"),
    maxTripDistance: document.getElementById("option-max-trip-distance"),
    vehicleCount: document.getElementById("option-vehicle-count"),
    requestRate: document.getElementById("option-request-rate"),
    inhomogeneity: document.getElementById("option-two-zone"),
    meanVehicleSpeed: document.getElementById("option-mean-vehicle-speed"),
    price: document.getElementById("option-price"),
    perKmPrice: document.getElementById("option-per-km-price"),
    perMinutePrice: document.getElementById("option-per-minute-price"),
    demandElasticity: document.getElementById("option-demand-elasticity"),
    platformCommission: document.getElementById("option-platform-commission"),
    reservationWage: document.getElementById("option-reservation-wage"),
    perKmOpsCost: document.getElementById("option-per-km-ops-cost"),
    perHourOpportunityCost: document.getElementById(
      "option-per-hour-opportunity-cost"
    ),
    frameTimeout: document.getElementById("option-frame-timeout"),
    smoothingWindow: document.getElementById("option-smoothing-window"),
  },
  checkboxes: {
    equilibrate: document.getElementById("checkbox-equilibrate"),
  },
  canvases: {
    pgMap: document.getElementById("pg-map-chart-canvas"),
    pgCity: document.getElementById("pg-city-chart-canvas"),
    pgPhases: document.getElementById("pg-phases-chart-canvas"),
    pgTrip: document.getElementById("pg-trip-chart-canvas"),
    pgIncome: document.getElementById("pg-income-chart-canvas"),
  },
  whatIf: {
    resetButton: document.getElementById("what-if-reset-button"),
    fabButton: document.getElementById("what-if-fab-button"),
    comparisonButton: document.getElementById("what-if-comparison-button"),
    setComparisonButtons: document.querySelectorAll(
      ".what-if-set-comparison button"
    ),
    baselineRadios: document.querySelectorAll(
      'input[type=radio][name="what-if-radio-baseline"]'
    ),
    frameCount: document.getElementById("what-if-frame-count"),
    canvases: {
      phases: document.getElementById("what-if-phases-chart-canvas"),
      income: document.getElementById("what-if-income-chart-canvas"),
      wait: document.getElementById("what-if-wait-chart-canvas"),
      n: document.getElementById("what-if-n-chart-canvas"),
      demand: document.getElementById("what-if-demand-chart-canvas"),
      platform: document.getElementById("what-if-platform-chart-canvas"),
    },
  },
  collections: {
    tabList: document.querySelectorAll(".mdl-layout__tab"),
    resetControls: document.querySelectorAll(".ui-mode-reset input"),
    equilibrateControls: document.querySelectorAll(".ui-mode-equilibrate"),
  },
};
