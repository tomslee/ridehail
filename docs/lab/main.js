/* global Chart */
export const colors = new Map([
  // Road
  ["ROAD", "rgba(232, 232, 232, 0.5)"],
  // Vehicles
  ["IDLE", "rgba(100, 149, 237, 0.5)"],
  ["DISPATCHED", "rgba(215, 142, 0, 0.5)"],
  ["WITH_RIDER", "rgba(60, 179, 113, 0.5)"],
  ["PURPLE", "rgba(160, 109, 153, 0.5)"],
  // Trips
  ["UNASSIGNED", "rgba(237, 100, 149, 0.5)"],
  ["WAITING", "rgba(237, 100, 149, 0.5)"],
  ["RIDING", "rgba(60, 179, 113, 0.5)"],
]);

import {
  initStatsChart,
  initDriverChart,
  plotStatsChart,
  plotDriverChart,
} from "./modules/stats.js";
import { initMap, plotMap } from "./modules/map.js";
import {
  initWhatIfPhasesChart,
  initWhatIfIncomeChart,
  initWhatIfWaitChart,
  initWhatIfNChart,
  plotWhatIfPhasesChart,
  plotWhatIfIncomeChart,
  plotWhatIfWaitChart,
  plotWhatIfNChart,
} from "./modules/whatif.js";

// Tabs
const tabList = document.querySelectorAll(".mdl-layout__tab");
tabList.forEach(function (element) {
  // destroy any existing charts
  element.onclick = function (element) {
    if (window.chart instanceof Chart) {
      window.chart.destroy();
    }
    if (window.statsChart instanceof Chart) {
      window.statsChart.destroy();
    }
    switch (element.currentTarget.id) {
      case "tab-experiment":
        resetLabUIAndSimulation();
        break;
      case "tab-what-if":
        resetWhatIfUIAndSimulation();
        break;
      case "tab-read":
        break;
      case "tab-TO":
        break;
    }
  };
});

// Top controls
const spinner = document.getElementById("spinner");
const resetButton = document.getElementById("reset-button");
const fabButton = document.getElementById("fab-button");
const nextStepButton = document.getElementById("next-step-button");
const uiModeRadios = document.querySelectorAll(
  'input[type=radio][name="ui-mode"]'
);
const scaleRadios = document.querySelectorAll(
  'input[type=radio][name="scale"]'
);
const chartTypeRadios = document.querySelectorAll(
  'input[type=radio][name="chart-type"]'
);

const inputCitySize = document.getElementById("input-city-size");
const optionCitySize = document.getElementById("option-city-size");
inputCitySize.onchange = function () {
  optionCitySize.innerHTML = this.value;
  labSimSettings.citySize = this.value;
  resetLabUIAndSimulation(labUISettings);
};

const inputTwoZone = document.getElementById("input-two-zone");
const optionTwoZone = document.getElementById("option-two-zone");
inputTwoZone.onchange = function () {
  optionTwoZone.innerHTML = this.value;
  labSimSettings.tripInhomogeneity = this.value;
  updateSimulationOptions(SimulationActions.Update);
};

const inputMaxTripDistance = document.getElementById("input-max-trip-distance");
const optionMaxTripDistance = document.getElementById(
  "option-max-trip-distance"
);
inputMaxTripDistance.onchange = function () {
  labSimSettings.maxTripDistance = parseInt(this.value);
  this.value = Math.min(
    labSimSettings.maxTripDistance,
    labSimSettings.citySize
  );
  optionMaxTripDistance.innerHTML = this.value;
  resetLabUIAndSimulation(labUISettings);
};

// Vehicles
const inputVehicleCount = document.getElementById("input-vehicle-count");
const optionVehicleCount = document.getElementById("option-vehicle-count");
inputVehicleCount.onchange = function () {
  optionVehicleCount.innerHTML = this.value;
  labSimSettings.vehicleCount = parseInt(this.value);
  /* simSettings do not use all parameters. Set them to null */
  if (
    labSimSettings.action == SimulationActions.Pause ||
    labSimSettings.action == SimulationActions.Play
  ) {
    // update live
    updateSimulationOptions(SimulationActions.Update);
  }
};

const inputMeanVehicleSpeed = document.getElementById(
  "input-mean-vehicle-speed"
);
const optionMeanVehicleSpeed = document.getElementById(
  "option-mean-vehicle-speed"
);

inputMeanVehicleSpeed.onchange = function () {
  optionMeanVehicleSpeed.innerHTML = this.value;
  labSimSettings.meanVehicleSpeed = parseFloat(this.value);
  resetLabUIAndSimulation(labUISettings);
};

const inputRequestRate = document.getElementById("input-request-rate");
const optionRequestRate = document.getElementById("option-request-rate");
inputRequestRate.onchange = function () {
  optionRequestRate.innerHTML = this.value;
  labSimSettings.requestRate = parseFloat(this.value);
  if (
    labSimSettings.action == SimulationActions.Pause ||
    labSimSettings.action == SimulationActions.Play
  ) {
    // update live
    updateSimulationOptions(SimulationActions.Update);
  }
};

const checkboxEquilibrate = document.getElementById("checkbox-equilibrate");
checkboxEquilibrate.onclick = function () {
  labSimSettings.equilibrate = checkboxEquilibrate.checked;
  if (
    labSimSettings.action == SimulationActions.Pause ||
    labSimSettings.action == SimulationActions.Play
  ) {
    // update live
    updateSimulationOptions(SimulationActions.Update);
  }
};

// Fares and wages
const inputPrice = document.getElementById("input-price");
const optionPrice = document.getElementById("option-price");
inputPrice.onchange = function () {
  optionPrice.innerHTML = this.value;
  labSimSettings.price = this.value;
  resetLabUIAndSimulation(labUISettings);
};

const inputPerKmPrice = document.getElementById("input-per-km-price");
const optionPerKmPrice = document.getElementById("option-per-km-price");
inputPerKmPrice.onchange = function () {
  optionPerKmPrice.innerHTML = this.value;
  labSimSettings.pricePerKm = this.value;
  resetLabUIAndSimulation(labUISettings);
};

const inputPerMinutePrice = document.getElementById("input-per-minute-price");
const optionPerMinutePrice = document.getElementById("option-per-minute-price");
inputPerMinutePrice.onchange = function () {
  optionPerMinutePrice.innerHTML = this.value;
  labSimSettings.perMinutePrice = this.value;
  resetLabUIAndSimulation(labUISettings);
};

const inputPlatformCommission = document.getElementById(
  "input-platform-commission"
);
const optionPlatformCommission = document.getElementById(
  "option-platform-commission"
);
inputPlatformCommission.onchange = function () {
  optionPlatformCommission.innerHTML = this.value;
  labSimSettings.platformCommission = this.value;
  // resetLabUIAndSimulation(labUISettings);
  if (
    labSimSettings.action == SimulationActions.Pause ||
    labSimSettings.action == SimulationActions.Play
  ) {
    // update live
    updateSimulationOptions(SimulationActions.Update);
  }
};

const inputReservationWage = document.getElementById("input-reservation-wage");
const optionReservationWage = document.getElementById(
  "option-reservation-wage"
);
inputReservationWage.onchange = function () {
  optionReservationWage.innerHTML = this.value;
  labSimSettings.reservationWage = this.value;
  resetLabUIAndSimulation(labUISettings);
};

const inputPerKmOpsCost = document.getElementById("input-per-km-ops-cost");
const optionPerKmOpsCost = document.getElementById("option-per-km-ops-cost");
inputPerKmOpsCost.onchange = function () {
  optionPerKmOpsCost.innerHTML = this.value;
  labSimSettings.perKmOpsCost = this.value;
  resetLabUIAndSimulation(labUISettings);
};

const inputPerHourOpportunityCost = document.getElementById(
  "input-per-hour-opportunity-cost"
);
const optionPerHourOpportunityCost = document.getElementById(
  "option-per-hour-opportunity-cost"
);
inputPerHourOpportunityCost.onchange = function () {
  optionPerHourOpportunityCost.innerHTML = this.value;
  labSimSettings.perHourOpportunityCost = this.value;
  resetLabUIAndSimulation(labUISettings);
};

// Display
const inputFrameTimeout = document.getElementById("input-frame-timeout");
const optionFrameTimeout = document.getElementById("option-frame-timeout");
const inputSmoothingWindow = document.getElementById("input-smoothing-window");
const optionSmoothingWindow = document.getElementById(
  "option-smoothing-window"
);

const pgCanvas = document.getElementById("pg-chart-canvas");
const pgDriverCanvas = document.getElementById("pg-driver-chart-canvas");

const resetControls = document.querySelectorAll(".ui-mode-reset input");
const advancedControls = document.querySelectorAll(".ui-mode-advanced");
const simpleControls = document.querySelectorAll(".ui-mode-simple");

/**
 * @enum
 * Different chart types that are active in the UI
 */
var ChartType = {
  Map: "map",
  Stats: "stats",
  WhatIf: "whatIf",
};

/**
 * @enum
 * possible simulation actions and sim_states, for the fabButton
 */
export var SimulationActions = {
  Play: "play_arrow",
  Pause: "pause",
  Reset: "reset",
  SingleStep: "single-step",
  Update: "update",
  UpdateDisplay: "updateDisplay",
  Done: "pause",
};

/**
 * @Class
 * Container for simulation settings, which will be posted to webworker to
 * interact with the pyodide python module
 */
class SimSettings {
  /**
   * For now, a set of "reasonable" defaults are set on initialization. It
   * would be good to have these chosen in a less arbitrary fashion.
   */
  constructor() {
    this.name = "SimSettings";
    this.citySize = 4;
    this.vehicleCount = 1;
    this.requestRate = 0.1;
    this.smoothingWindow = 20;
    this.maxTripDistance = null;
    this.tripInhomogeneity = 0;
    this.tripInhomogeneousDestinations = false;
    this.idleVehiclesMoving = true;
    this.randomNumberSeed = 87;
    this.equilibrate = false;
    this.equilibration = "price";
    this.equilibrationInterval = 5;
    this.demandElasticity = 0;
    this.price = 1.0;
    this.platformCommission = 0;
    this.reservationWage = 0;
    this.useCityScale = false;
    this.minutesPerBlock = 1;
    this.meanVehicleSpeed = 30.0;
    this.perKmPrice = 0.18;
    this.perMinutePrice = 0.81;
    this.perKmOpsCost = 0.2;
    this.perHourOpportunityCost = 10;
    this.verbosity = 0;
    this.timeBlocks = 0;
    this.frameIndex = 0;
    this.action = null;
    this.frameTimeout = 0;
  }
}

var labUISettings = {
  uiMode: document.querySelector('input[type="radio"][name="ui-mode"]:checked')
    .value,
  ctx: pgCanvas.getContext("2d"),
  ctxDriver: pgDriverCanvas.getContext("2d"),
  chartType: document.querySelector(
    'input[type="radio"][name="chart-type"]:checked'
  ).value,
  vehicleRadius: 9,
  roadWidth: 10,
};

/*
 * What if? tab
 */
const whatIfResetButton = document.getElementById("what-if-reset-button");
const whatIfFabButton = document.getElementById("what-if-fab-button");
const whatIfComparisonButton = document.getElementById(
  "what-if-comparison-button"
);
const whatIfPhasesCanvas = document.getElementById(
  "what-if-phases-chart-canvas"
);
const whatIfIncomeCanvas = document.getElementById(
  "what-if-income-chart-canvas"
);
const whatIfWaitCanvas = document.getElementById("what-if-wait-chart-canvas");
const whatIfNCanvas = document.getElementById("what-if-n-chart-canvas");
var baselineData = null;

var whatIfUISettings = {
  ctxWhatIfPhases: whatIfPhasesCanvas.getContext("2d"),
  ctxWhatIfIncome: whatIfIncomeCanvas.getContext("2d"),
  ctxWhatIfWait: whatIfWaitCanvas.getContext("2d"),
  ctxWhatIfN: whatIfNCanvas.getContext("2d"),
  chartType: ChartType.WhatIf,
};

const whatIfSetComparisonButtons = document.querySelectorAll(
  ".what-if-set-comparison button"
);
whatIfSetComparisonButtons.forEach(function (element) {
  element.addEventListener("click", function () {
    switch (this.id) {
      case "what-if-price-remove":
        whatIfSimSettingsComparison.price -= 0.1;
        break;
      case "what-if-price-add":
        whatIfSimSettingsComparison.price += 0.1;
        break;
      case "what-if-commission-remove":
        whatIfSimSettingsComparison.platformCommission -= 0.05;
        break;
      case "what-if-commission-add":
        whatIfSimSettingsComparison.platformCommission += 0.05;
        break;
      case "what-if-reservation-wage-remove":
        whatIfSimSettingsComparison.reservationWage -= 0.01;
        break;
      case "what-if-reservation-wage-add":
        whatIfSimSettingsComparison.reservationWage += 0.01;
        break;
      case "what-if-demand-remove":
        whatIfSimSettingsComparison.requestRate -= 0.5;
        break;
      case "what-if-demand-add":
        whatIfSimSettingsComparison.requestRate += 0.5;
        break;
    }
    updateWhatIfTopControlValues();
  });
});

/*
 * UI actions
 */

/*
 * Story time
 */

/*
 * Top-level controls (reset, play/pause, next step)
 */

function updateSimulationOptions(updateType) {
  labSimSettings.action = updateType;
  w.postMessage(labSimSettings);
}

function toggleWhatIfFabButton(button) {
  if (button.firstElementChild.innerHTML == SimulationActions.Play) {
    button.firstElementChild.innerHTML = SimulationActions.Pause;
    whatIfSetComparisonButtons.forEach(function (element) {
      element.setAttribute("disabled", "");
    });
    if (button == whatIfFabButton) {
      whatIfComparisonButton.setAttribute("disabled", "");
    } else if (button == whatIfComparisonButton) {
      whatIfFabButton.setAttribute("disabled", "");
    }
  } else if (button.firstElementChild.innerHTML == SimulationActions.Pause) {
    button.firstElementChild.innerHTML = SimulationActions.Play;
    whatIfSetComparisonButtons.forEach(function (element) {
      element.removeAttribute("disabled");
    });
    if (button == whatIfFabButton) {
      whatIfComparisonButton.removeAttribute("disabled");
      whatIfComparisonButton.firstElementChild.innerHTML =
        SimulationActions.Play;
    } else if (button == whatIfComparisonButton) {
      // whatIfFabButton.removeAttribute("disabled");
      // whatIfFabButton.firstElementChild.innerHTML = SimulationActions.Play;
      // Require a reset before running the baseline again
    }
  }
}

function resetWhatIfUIAndSimulation() {
  whatIfSimSettingsComparison.action = SimulationActions.Reset;
  w.postMessage(whatIfSimSettingsComparison);
  whatIfResetButton.removeAttribute("disabled");
  whatIfFabButton.removeAttribute("disabled");
  whatIfComparisonButton.setAttribute("disabled", "");
  whatIfFabButton.firstElementChild.innerHTML = SimulationActions.Play;
  whatIfSimSettingsComparison = clone(whatIfSimSettingsDefault);
  whatIfSimSettingsComparison.name = "whatIfSimSettingsComparison";
  whatIfSetComparisonButtons.forEach(function (element) {
    element.setAttribute("disabled", "");
  });
  updateWhatIfTopControlValues();
  // Charts
  baselineData = null;
  if (window.whatIfPhasesChart instanceof Chart) {
    window.whatIfPhasesChart.destroy();
  }
  if (window.whatIfIncomeChart instanceof Chart) {
    window.whatIfIncomeChart.destroy();
  }
  if (window.whatIfWaitChart instanceof Chart) {
    window.whatIfWaitChart.destroy();
  }
  if (window.whatIfNChart instanceof Chart) {
    window.whatIfNChart.destroy();
  }
  initWhatIfPhasesChart(baselineData, whatIfUISettings);
  initWhatIfIncomeChart(baselineData, whatIfUISettings);
  initWhatIfWaitChart(baselineData, whatIfUISettings);
  initWhatIfNChart(baselineData, whatIfUISettings);
}

function updateWhatIfTopControlValues() {
  document.getElementById("what-if-price").innerHTML = new Intl.NumberFormat({
    style: "currency",
    currency: "CAD",
  }).format(whatIfSimSettingsComparison.price);
  document.getElementById("what-if-commission").innerHTML = Math.round(
    whatIfSimSettingsComparison.platformCommission * 100
  );
  document.getElementById("what-if-cap").innerHTML =
    whatIfSimSettingsComparison.vehicleCount;
  document.getElementById("what-if-reservation-wage").innerHTML =
    new Intl.NumberFormat({ style: "currency", currency: "CAD" }).format(
      whatIfSimSettingsComparison.reservationWage * 60
    );
  document.getElementById("what-if-demand").innerHTML = Math.round(
    whatIfSimSettingsComparison.requestRate * 60
  );
}

function resetLabUIAndSimulation() {
  resetButton.removeAttribute("disabled");
  nextStepButton.removeAttribute("disabled");
  fabButton.removeAttribute("disabled");
  fabButton.firstElementChild.innerHTML = SimulationActions.Play;
  spinner.classList.remove("is-active");
  spinner.style.display = "none";
  optionFrameTimeout.innerHTML = inputFrameTimeout.value;
  labSimSettings.action = SimulationActions.Reset;
  /* Simple or advanced? */
  updateUIMode(labUISettings.uiMode);
  w.postMessage(labSimSettings);
  labSimSettings.frameIndex = 0;
  document.getElementById("frame-count").innerHTML = labSimSettings.frameIndex;
  document.getElementById("top-control-spinner").style.display = "none";
  // Create a new chart
  if (labUISettings.chartType == ChartType.Stats) {
    pgDriverCanvas.style.display = "block";
    initStatsChart(labUISettings, labSimSettings);
    initDriverChart(labUISettings, labSimSettings);
  } else if (labUISettings.chartType == ChartType.Map) {
    pgDriverCanvas.style.display = "none";
    initMap(labUISettings, labSimSettings);
  }
}

resetButton.onclick = function () {
  resetLabUIAndSimulation();
};

whatIfResetButton.onclick = function () {
  resetWhatIfUIAndSimulation();
};

function toggleLabFabButton(button) {
  if (button.firstElementChild.innerHTML == SimulationActions.Play) {
    // The button shows the Play arrow. Toggle it to show Pause
    button.firstElementChild.innerHTML = SimulationActions.Pause;
    // While the simulation is playing, also disable Next Step
    nextStepButton.setAttribute("disabled", "");
    resetControls.forEach(function (element) {
      element.setAttribute("disabled", "");
    });
  } else {
    // The button shows Pause. Toggle it to show the Play arrow.
    button.firstElementChild.innerHTML = SimulationActions.Play;
    // While the simulation is Paused, also enable Reset and Next Step
    nextStepButton.removeAttribute("disabled");
    resetButton.removeAttribute("disabled");
    resetControls.forEach(function (element) {
      element.removeAttribute("disabled");
    });
  }
}

function clickFabButton(button, simSettings) {
  // If the button is showing "Play", then the action to take is play
  if (button.firstElementChild.innerHTML == SimulationActions.Play) {
    simSettings.action = SimulationActions.Play;
  } else {
    // The button should be showing "Pause", and the action to take is to pause
    simSettings.action = SimulationActions.Pause;
  }
  w.postMessage(simSettings);
  // Now make the button look different
  if (button == whatIfFabButton) {
    toggleWhatIfFabButton(button);
  } else if (button == whatIfComparisonButton) {
    toggleWhatIfFabButton(button);
  } else if (button == fabButton) {
    toggleLabFabButton(button);
  }
}

fabButton.onclick = function () {
  labSimSettings.frameIndex = document.getElementById("frame-count").innerHTML;
  labSimSettings.chartType = document.querySelector(
    'input[type="radio"][name="chart-type"]:checked'
  ).value;
  labSimSettings.citySize = parseInt(inputCitySize.value);
  labSimSettings.vehicleCount = parseInt(inputVehicleCount.value);
  labSimSettings.requestRate = parseFloat(inputRequestRate.value);
  clickFabButton(fabButton, labSimSettings);
};

whatIfFabButton.onclick = function () {
  clickFabButton(whatIfFabButton, whatIfSimSettingsBaseline);
};

whatIfComparisonButton.onclick = function () {
  clickFabButton(whatIfComparisonButton, whatIfSimSettingsComparison);
};

nextStepButton.onclick = function () {
  labSimSettings.action = SimulationActions.SingleStep;
  w.postMessage(labSimSettings);
};

/*
 * UI Mode radio button
 */
uiModeRadios.forEach((radio) =>
  radio.addEventListener("change", () => {
    updateUIMode(radio.value);
    resetLabUIAndSimulation();
  })
);

function updateUIMode(uiModeRadiosValue) {
  labUISettings.uiMode = uiModeRadiosValue;
  /* Controls are either advanced (only), simple (only) or both */
  simpleControls.forEach(function (element) {
    if (labUISettings.uiMode == "advanced") {
      element.style.display = "none";
    } else {
      element.style.display = "block";
    }
  });
  advancedControls.forEach(function (element) {
    if (labUISettings.uiMode == "advanced") {
      element.style.display = "block";
    } else {
      element.style.display = "none";
    }
  });
  /* labSimSettings do not use all parameters. Set them to null */
  if (labUISettings.uiMode == "advanced") {
    labSimSettings.useCityScale = true;
    // max trip distance cannoe be bigger than citySize
    labSimSettings.maxTripDistance = parseInt(inputMaxTripDistance.value);
  } else if (labUISettings.uiMode == "simple") {
    labSimSettings.useCityScale = false;
    labSimSettings.maxTripDistance = null;
  }
}

chartTypeRadios.forEach((radio) =>
  radio.addEventListener("change", () =>
    updateChartType(radio.value, labSimSettings, labUISettings)
  )
);

function updateChartType(value, simSettings, uiSettings) {
  // "value" comes in as a string from the UI world
  if (value == "stats") {
    uiSettings.chartType = ChartType.Stats;
    simSettings.chartType = ChartType.Stats;
  } else if (value == "map") {
    uiSettings.chartType = ChartType.Map;
    simSettings.chartType = ChartType.Map;
  } else if (value == "whatIf") {
    uiSettings.chartType = ChartType.WhatIf;
    simSettings.chartType = ChartType.WhatIf;
  }
  if (uiSettings.chartType == ChartType.Stats) {
    inputFrameTimeout.value = 10;
    simSettings.frameTimeout = 10;
  } else if (uiSettings.chartType == ChartType.Map) {
    inputFrameTimeout.value = 300;
    simSettings.frameTimeout = 300;
  }
  optionFrameTimeout.innerHTML = inputFrameTimeout.value;
  let statsDescriptions = document.querySelectorAll(".pg-stats-descriptions");
  statsDescriptions.forEach(function (element) {
    if (uiSettings.chartType == ChartType.Stats) {
      element.style.display = "block";
    } else {
      element.style.display = "none";
    }
  });
  resetLabUIAndSimulation();
}

scaleRadios.forEach((radio) =>
  radio.addEventListener("change", () => updateOptionsForScale(radio.value))
);

function updateOptionsForScale(value) {
  let citySizeValue = inputCitySize.value;
  let citySizeMin = inputCitySize.min;
  let citySizeMax = inputCitySize.max;
  let citySizeStep = inputCitySize.step;
  let vehicleCountValue = inputVehicleCount.value;
  let vehicleCountMin = inputVehicleCount.min;
  let vehicleCountMax = inputVehicleCount.max;
  let vehicleCountStep = inputVehicleCount.step;
  let maxTripDistanceValue = inputMaxTripDistance.value;
  let maxTripDistanceMin = inputMaxTripDistance.min;
  let maxTripDistanceMax = inputMaxTripDistance.max;
  let maxTripDistanceStep = inputMaxTripDistance.step;
  let requestRateValue = inputRequestRate.value;
  let requestRateMin = inputRequestRate.min;
  let requestRateMax = inputRequestRate.max;
  let requestRateStep = inputRequestRate.step;
  if (value == "village") {
    citySizeValue = 8;
    citySizeMin = 4;
    citySizeMax = 16;
    citySizeStep = 2;
    vehicleCountValue = 8;
    vehicleCountMin = 1;
    vehicleCountMax = 16;
    vehicleCountStep = 1;
    maxTripDistanceValue = 4;
    maxTripDistanceMin = 1;
    maxTripDistanceMax = 4;
    maxTripDistanceStep = 1;
    requestRateValue = 0.5;
    requestRateMin = 0;
    requestRateMax = 2;
    requestRateStep = 0.1;
    labUISettings.roadWidth = 10;
    labUISettings.vehicleRadius = 10;
  } else if (value == "town") {
    citySizeValue = 24;
    citySizeMin = 16;
    citySizeMax = 64;
    citySizeStep = 4;
    vehicleCountValue = 160;
    vehicleCountMin = 8;
    vehicleCountMax = 512;
    vehicleCountStep = 8;
    maxTripDistanceValue = 24;
    maxTripDistanceMin = 1;
    maxTripDistanceMax = 24;
    maxTripDistanceStep = 1;
    requestRateValue = 8;
    requestRateMin = 0;
    requestRateMax = 48;
    requestRateStep = 4;
    labUISettings.roadWidth = 6;
    labUISettings.vehicleRadius = 6;
  } else if (value == "city") {
    citySizeValue = 48;
    citySizeMin = 32;
    citySizeMax = 64;
    citySizeStep = 8;
    vehicleCountValue = 1760;
    vehicleCountMin = 32;
    vehicleCountMax = 6400;
    vehicleCountStep = 16;
    maxTripDistanceValue = 48;
    maxTripDistanceMin = 1;
    maxTripDistanceMax = 48;
    maxTripDistanceStep = 1;
    requestRateValue = 48;
    requestRateMin = 8;
    requestRateMax = 196;
    requestRateStep = 8;
    labUISettings.roadWidth = 3;
    labUISettings.vehicleRadius = 3;
  }
  inputCitySize.min = citySizeMin;
  inputCitySize.max = citySizeMax;
  inputCitySize.step = citySizeStep;
  inputCitySize.value = citySizeValue;
  optionCitySize.innerHTML = citySizeValue;
  inputVehicleCount.min = vehicleCountMin;
  inputVehicleCount.max = vehicleCountMax;
  inputVehicleCount.step = vehicleCountStep;
  inputVehicleCount.value = vehicleCountValue;
  optionVehicleCount.innerHTML = vehicleCountValue;
  inputMaxTripDistance.min = maxTripDistanceMin;
  inputMaxTripDistance.max = maxTripDistanceMax;
  inputMaxTripDistance.step = maxTripDistanceStep;
  inputMaxTripDistance.value = maxTripDistanceValue;
  optionMaxTripDistance.innerHTML = maxTripDistanceValue;
  inputRequestRate.min = requestRateMin;
  inputRequestRate.max = requestRateMax;
  inputRequestRate.step = requestRateStep;
  inputRequestRate.value = requestRateValue;
  optionRequestRate.innerHTML = requestRateValue;
  inputPrice.value = 1.2;
  optionPrice.innerHTML = inputPrice.value;
  inputPlatformCommission.value = 0.25;
  optionPlatformCommission.innerHTML = inputPlatformCommission.value;
  inputReservationWage.value = 0.35;
  optionReservationWage.innerHTML = inputReservationWage.value;
  labSimSettings.action = SimulationActions.Reset;
  labSimSettings.frameIndex = 0;
  (labSimSettings.chartType = document.querySelector(
    'input[type="radio"][name="chart-type"]:checked'
  ).value),
    (labSimSettings.citySize = citySizeValue);
  resetLabUIAndSimulation();
}

/*
 * Simulation options
 */

inputFrameTimeout.onchange = function () {
  optionFrameTimeout.innerHTML = this.value;
  labSimSettings.frameTimeout = this.value;
  if (
    labSimSettings.action == SimulationActions.Pause ||
    labSimSettings.action == SimulationActions.Play
  ) {
    // update live
    updateSimulationOptions(SimulationActions.UpdateDisplay);
  }
};
inputSmoothingWindow.onchange = function () {
  optionSmoothingWindow.innerHTML = this.value;
  labSimSettings.smoothingWindow = this.value;
  resetLabUIAndSimulation(labUISettings);
};

/*
 * Capture keypress events
 */

document.addEventListener("keyup", function (event) {
  if (event.key === "z" || event.key === "Z") {
    // zoom
    const elementList = document.querySelectorAll(".ui-zoom-hide");
    elementList.forEach(function (element) {
      if (element.style.display == "none") {
        element.style.display = "block";
      } else {
        element.style.display = "none";
      }
    });
    let element = document.getElementById("chart-column");
    element.classList.toggle("mdl-cell--4-col");
    element.classList.toggle("mdl-cell--7-col");
    // element = document.getElementById("column-2");
    // element.classList.toggle("mdl-cell--3-col");
    // element.classList.toggle("mdl-cell--2-col");
  } else if (event.key === "p" || event.key === "P") {
    //spacebar
    clickFabButton(fabButton);
  }
});

var labSimSettings = new SimSettings();
labSimSettings.name = "labSimSettings";
labSimSettings.citySize = inputCitySize.value;
labSimSettings.vehicleCount = inputVehicleCount.value;
labSimSettings.requestRate = inputRequestRate.value;
labSimSettings.smoothingWindow = inputSmoothingWindow.value;
labSimSettings.useCityScale = labUISettings.uiMode;
labSimSettings.platformCommission = inputPlatformCommission.value;
labSimSettings.price = inputPrice.value;
labSimSettings.reservationWage = inputReservationWage.value;
labSimSettings.meanVehicleSpeed = inputMeanVehicleSpeed.value;
labSimSettings.perKmPrice = inputPerKmPrice.value;
labSimSettings.perMinutePrice = inputPerMinutePrice.value;
labSimSettings.perKmOpsCost = inputPerKmOpsCost.value;
labSimSettings.perHourOpportunityCost = inputPerHourOpportunityCost.value;
labSimSettings.action = fabButton.firstElementChild.innerHTML;
labSimSettings.frameTimeout = inputFrameTimeout.value;
labSimSettings.chartType = document.querySelector(
  'input[type="radio"][name="chart-type"]:checked'
).value;

var whatIfSimSettingsDefault = new SimSettings();
whatIfSimSettingsDefault.name = "whatIfSimSettingsDefault";
whatIfSimSettingsDefault.citySize = 24;
whatIfSimSettingsDefault.vehicleCount = 160;
whatIfSimSettingsDefault.requestRate = 8;
whatIfSimSettingsDefault.timeBlocks = 100;
whatIfSimSettingsDefault.smoothingWindow = 120;
whatIfSimSettingsDefault.useCityScale = false;
whatIfSimSettingsDefault.platformCommission = 0.25;
whatIfSimSettingsDefault.price = 0.6;
whatIfSimSettingsDefault.reservationWage = 0.21;
whatIfSimSettingsDefault.tripInhomogeneity = 0.5;
whatIfSimSettingsDefault.meanVehicleSpeed = 30;
whatIfSimSettingsDefault.equilibrate = true;
whatIfSimSettingsDefault.perKmPrice = 0.8;
whatIfSimSettingsDefault.perMinutePrice = 0.2;
whatIfSimSettingsDefault.perKmOpsCost = 0.25;
whatIfSimSettingsDefault.perHourOpportunityCost = 5.0;
whatIfSimSettingsDefault.action = whatIfFabButton.firstElementChild.innerHTML;
whatIfSimSettingsDefault.frameTimeout = 0;
whatIfSimSettingsDefault.chartType = ChartType.WhatIf;
function clone(o) {
  return JSON.parse(JSON.stringify(o));
}
var whatIfSimSettingsBaseline = clone(whatIfSimSettingsDefault);
var whatIfSimSettingsComparison = clone(whatIfSimSettingsDefault);
whatIfSimSettingsBaseline.name = "whatIfSimSettingsBaseline";
whatIfSimSettingsComparison.name = "whatIfSimSettingsComparison";

window.onload = function () {
  //resetLabUIAndSimulation();
};

/*
 * Interaction with web worker
 */

if (typeof w == "undefined") {
  // var w = new Worker("webworker.js", {type: 'module'});
  var w = new Worker("webworker.js");
}

function handlePyodideready() {
  resetWhatIfUIAndSimulation();
  resetLabUIAndSimulation();
}

// Update the text status under the canvas
function updateTextStatus(eventData) {
  document.getElementById("text-status-vehicle-count").innerHTML =
    eventData.get("vehicle_count");
  document.getElementById("text-status-price").innerHTML =
    Math.round(100 * eventData.get("price")) / 100;
  document.getElementById("text-status-reservation-wage").innerHTML =
    eventData.get("reservation_wage");
  document.getElementById("text-status-platform-commission").innerHTML =
    eventData.get("platform_commission") * 100;
  if (!eventData.has("vehicles")) {
    document.getElementById("text-status-driver-income").innerHTML = Math.round(
      eventData.get("price") *
        (1.0 - eventData.get("platform_commission")) *
        eventData.get("VEHICLE_FRACTION_P3")
    );
    document.getElementById("text-status-wait-time").innerHTML =
      Math.round(10 * eventData.get("TRIP_MEAN_WAIT_TIME")) / 10;
  }
  document.getElementById("text-status-per-km-price").innerHTML =
    eventData.get("per_km_price");
  document.getElementById("text-status-per-min-price").innerHTML =
    eventData.get("per_min_price");
}

// Listen to the web worker
w.onmessage = function (event) {
  // lineChart.data.datasets[0].data.push({x: event.data[0], y: event.data[1].get("vehicle_fraction_idle")});
  // data comes in from a self.postMessage([blockIndex, vehicleColors, vehicleLocations]);
  if (event.data.size > 1) {
    let frameIndex = event.data.get("block");
    if (event.data.has("vehicles")) {
      plotMap(event.data);
    } else if (event.data.get("chartType") == ChartType.Stats) {
      plotStatsChart(event.data);
      plotDriverChart(event.data);
      updateTextStatus(event.data);
    } else if (event.data.get("chartType") == ChartType.WhatIf) {
      // covers both baseline and comparison runs
      plotWhatIfPhasesChart(baselineData, event.data);
      plotWhatIfIncomeChart(baselineData, event.data);
      plotWhatIfWaitChart(baselineData, event.data);
      plotWhatIfNChart(baselineData, event.data);
    }
    if (event.data.get("name") == "labSimSettings") {
      document.getElementById("frame-count").innerHTML = frameIndex;
      if (
        frameIndex >= labSimSettings.timeBlocks &&
        labSimSettings.timeBlocks != 0
      ) {
        labSimSettings.action = SimulationActions.Done;
        w.postMessage(labSimSettings);
        toggleLabFabButton();
      }
    } else if (event.data.get("name") == "whatIfSimSettingsBaseline") {
      if (
        frameIndex >= whatIfSimSettingsBaseline.timeBlocks &&
        whatIfSimSettingsBaseline.timeBlocks != 0
      ) {
        whatIfSimSettingsBaseline.action = SimulationActions.Done;
        baselineData = event.data;
        w.postMessage(whatIfSimSettingsBaseline);
        toggleWhatIfFabButton(whatIfFabButton);
      }
    } else if (event.data.get("name") == "whatIfSimSettingsComparison") {
      if (
        frameIndex >= whatIfSimSettingsComparison.timeBlocks &&
        whatIfSimSettingsComparison.timeBlocks != 0
      ) {
        whatIfSimSettingsComparison.action = SimulationActions.Done;
        w.postMessage(whatIfSimSettingsComparison);
        toggleWhatIfFabButton(whatIfComparisonButton);
      }
    }
  } else if (event.data.size == 1) {
    if (event.data.get("text") == "Pyodide loaded") {
      handlePyodideready();
    } else {
      // probably an error labSimSettings
      console.log("Error in main: event.data=", event.data);
    }
  }
};
