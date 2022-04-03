/* global Chart */
export const colors = new Map([
  // Map
  ["ROAD", "rgba(232, 232, 232, 0.5)"],
  // Vehicles
  ["IDLE", "rgba(100, 149, 237, 0.5)"],
  ["DISPATCHED", "rgba(215, 142, 0, 0.5)"],
  ["WITH_RIDER", "rgba(60, 179, 113, 0.5)"],
  ["PURPLE", "rgba(160, 109, 153, 0.5)"],
  ["SURPLUS", "rgba(237, 100, 149, 0.5)"],
  // Trips
  ["UNASSIGNED", "rgba(237, 100, 149, 0.5)"],
  ["WAITING", "rgba(237, 100, 149, 0.5)"],
  ["RIDING", "rgba(60, 179, 113, 0.5)"],
]);

import {
  initCityChart,
  initPhasesChart,
  initTripChart,
  initIncomeChart,
  plotCityChart,
  plotPhasesChart,
  plotTripChart,
  plotIncomeChart,
} from "./modules/stats.js";
import { initMap, plotMap } from "./modules/map.js";
import {
  initWhatIfPhasesChart,
  initWhatIfIncomeChart,
  initWhatIfWaitChart,
  initWhatIfNChart,
  initWhatIfPlatformChart,
  plotWhatIfPhasesChart,
  plotWhatIfIncomeChart,
  plotWhatIfWaitChart,
  plotWhatIfNChart,
  plotWhatIfPlatformChart,
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
const scaleRadios = document.querySelectorAll(
  'input[type=radio][name="scale"]'
);
const chartTypeRadios = document.querySelectorAll(
  'input[type=radio][name="chart-type"]'
);
const uiModeRadios = document.querySelectorAll(
  'input[type=radio][name="ui-mode"]'
);
const inputCitySize = document.getElementById("input-city-size");
const optionCitySize = document.getElementById("option-city-size");
inputCitySize.onchange = function () {
  optionCitySize.innerHTML = this.value;
  labSimSettings.citySize = this.value;
  resetLabUIAndSimulation(labUISettings);
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
  updateSimulationOptions(SimulationActions.Update);
};

const inputRequestRate = document.getElementById("input-request-rate");
const optionRequestRate = document.getElementById("option-request-rate");
inputRequestRate.onchange = function () {
  optionRequestRate.innerHTML = this.value;
  labSimSettings.requestRate = parseFloat(this.value);
  // update live
  updateSimulationOptions(SimulationActions.Update);
};

const inputTwoZone = document.getElementById("input-two-zone");
const optionTwoZone = document.getElementById("option-two-zone");
inputTwoZone.onchange = function () {
  optionTwoZone.innerHTML = this.value;
  labSimSettings.tripInhomogeneity = this.value;
  updateSimulationOptions(SimulationActions.Update);
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

const checkboxEquilibrate = document.getElementById("checkbox-equilibrate");
checkboxEquilibrate.onclick = function () {
  labSimSettings.equilibrate = checkboxEquilibrate.checked;
  // TODO: This hides it all the time at the moment
  // because I don't have the reference price worked out
  equilibrateControls.forEach(function (element) {
    if (checkboxEquilibrate.checked) {
      // element.style.display = "block";
      element.style.display = "none";
    } else {
      element.style.display = "none";
    }
  });
  updateSimulationOptions(SimulationActions.Update);
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

const inputDemandElasticity = document.getElementById(
  "input-demand-elasticity"
);
const optionDemandElasticity = document.getElementById(
  "option-demand-elasticity"
);
inputDemandElasticity.onchange = function () {
  optionDemandElasticity.innerHTML = this.value;
  labSimSettings.demandElasticity = this.value;
  updateSimulationOptions(SimulationActions.Update);
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

const pgMapCanvas = document.getElementById("pg-map-chart-canvas");
const pgCityCanvas = document.getElementById("pg-city-chart-canvas");
const pgPhasesCanvas = document.getElementById("pg-phases-chart-canvas");
const pgTripCanvas = document.getElementById("pg-trip-chart-canvas");
const pgIncomeCanvas = document.getElementById("pg-income-chart-canvas");

const resetControls = document.querySelectorAll(".ui-mode-reset input");
const advancedControls = document.querySelectorAll(".ui-mode-advanced");
const equilibrateControls = document.querySelectorAll(".ui-mode-equilibrate");
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
  ctxCity: pgCityCanvas.getContext("2d"),
  ctxPhases: pgPhasesCanvas.getContext("2d"),
  ctxTrip: pgTripCanvas.getContext("2d"),
  ctxIncome: pgIncomeCanvas.getContext("2d"),
  ctxMap: pgMapCanvas.getContext("2d"),
  chartType: document.querySelector(
    'input[type="radio"][name="chart-type"]:checked'
  ).value,
  vehicleRadius: 9,
  roadWidth: 10,
};

// File drop
// <div id="file-drop-target" ondrop="drop_handler(event)" ondragover="dragover_handler(event)">
const dropTarget = document.getElementById("file-drop-target");
dropTarget.ondrop = function (event) {
  event.dataTransfer.dropEffect = "move";
  const data = event.dataTransfer.getData("text/plain");
  console.log("Drop incoming: ", data);
  event.target.textContent = data;
  event.preventDefault();
};
dropTarget.ondragover = function (ev) {
  ev.preventDefault();
  // Get the id of the target and add the moved element to the target's DOM
  // const data = ev.dataTransfer.getData("text/plain");
  // ev.target.appendChild(document.getElementById(data));
};

/*
 * What if? tab
 */
const whatIfResetButton = document.getElementById("what-if-reset-button");
const whatIfFabButton = document.getElementById("what-if-fab-button");
const whatIfComparisonButton = document.getElementById(
  "what-if-comparison-button"
);
const whatIfBaselineRadios = document.querySelectorAll(
  'input[type=radio][name="what-if-radio-baseline"]'
);
const whatIfPhasesCanvas = document.getElementById(
  "what-if-phases-chart-canvas"
);
const whatIfIncomeCanvas = document.getElementById(
  "what-if-income-chart-canvas"
);
const whatIfWaitCanvas = document.getElementById("what-if-wait-chart-canvas");
const whatIfNCanvas = document.getElementById("what-if-n-chart-canvas");
const whatIfPlatformCanvas = document.getElementById(
  "what-if-platform-chart-canvas"
);
var baselineData = null;

var whatIfUISettings = {
  ctxWhatIfPhases: whatIfPhasesCanvas.getContext("2d"),
  ctxWhatIfIncome: whatIfIncomeCanvas.getContext("2d"),
  ctxWhatIfWait: whatIfWaitCanvas.getContext("2d"),
  ctxWhatIfN: whatIfNCanvas.getContext("2d"),
  ctxWhatIfPlatform: whatIfPlatformCanvas.getContext("2d"),
  chartType: ChartType.WhatIf,
};

const whatIfSetComparisonButtons = document.querySelectorAll(
  ".what-if-set-comparison button"
);
whatIfSetComparisonButtons.forEach(function (element) {
  element.addEventListener("click", function () {
    switch (this.id) {
      case "what-if-price-remove":
        whatIfSimSettingsComparison.price =
          parseFloat(whatIfSimSettingsComparison.price) - 0.1;
        whatIfSimSettingsComparison.price =
          Math.round(whatIfSimSettingsComparison.price * 10) / 10;
        break;
      case "what-if-price-add":
        whatIfSimSettingsComparison.price =
          parseFloat(whatIfSimSettingsComparison.price) + 0.1;
        whatIfSimSettingsComparison.price =
          Math.round(whatIfSimSettingsComparison.price * 10) / 10;
        break;
      case "what-if-commission-remove":
        whatIfSimSettingsComparison.platformCommission =
          parseFloat(whatIfSimSettingsComparison.platformCommission) - 0.05;
        whatIfSimSettingsComparison.platformCommission =
          Math.round(whatIfSimSettingsComparison.platformCommission * 10) / 10;
        break;
      case "what-if-commission-add":
        whatIfSimSettingsComparison.platformCommission =
          parseFloat(whatIfSimSettingsComparison.platformCommission) + 0.05;
        whatIfSimSettingsComparison.platformCommission =
          Math.round(whatIfSimSettingsComparison.platformCommission * 10) / 10;
        break;
      case "what-if-reservation-wage-remove":
        whatIfSimSettingsComparison.reservationWage =
          parseFloat(whatIfSimSettingsComparison.reservationWage) - 0.1;
        whatIfSimSettingsComparison.reservationWage =
          Math.round(whatIfSimSettingsComparison.reservationWage * 10) / 10;
        break;
      case "what-if-reservation-wage-add":
        whatIfSimSettingsComparison.reservationWage =
          parseFloat(whatIfSimSettingsComparison.reservationWage) + 0.1;
        whatIfSimSettingsComparison.reservationWage =
          Math.round(whatIfSimSettingsComparison.reservationWage * 10) / 10;
        break;
      case "what-if-demand-remove":
        whatIfSimSettingsComparison.requestRate =
          parseFloat(whatIfSimSettingsComparison.requestRate) - 0.5;
        whatIfSimSettingsComparison.requestRate =
          Math.round(whatIfSimSettingsComparison.requestRate * 10) / 10;
        break;
      case "what-if-demand-add":
        whatIfSimSettingsComparison.requestRate =
          parseFloat(whatIfSimSettingsComparison.requestRate) + 0.5;
        whatIfSimSettingsComparison.requestRate =
          Math.round(whatIfSimSettingsComparison.requestRate * 10) / 10;
        break;
      case "what-if-demand-elasticity-remove":
        if (whatIfSimSettingsComparison.demandElasticity >= 0.1) {
          whatIfSimSettingsComparison.demandElasticity =
            parseFloat(whatIfSimSettingsComparison.demandElasticity) - 0.1;
        }
        whatIfSimSettingsComparison.demandElasticity =
          Math.round(whatIfSimSettingsComparison.demandElasticity * 10) / 10;
        break;
      case "what-if-demand-elasticity-add":
        whatIfSimSettingsComparison.demandElasticity =
          parseFloat(whatIfSimSettingsComparison.demandElasticity) + 0.1;
        whatIfSimSettingsComparison.demandElasticity =
          Math.round(whatIfSimSettingsComparison.demandElasticity * 10) / 10;
        break;
    }
    updateWhatIfTopControlValues();
  });
});

whatIfBaselineRadios.forEach((radio) =>
  radio.addEventListener("change", () => {
    if (radio.value == "preset") {
      whatIfSimSettingsBaseline = new WhatIfSimSettingsDefault();
      whatIfSimSettingsComparison = new WhatIfSimSettingsDefault();
    } else if (radio.value == "lab") {
      whatIfSimSettingsBaseline = Object.assign({}, labSimSettings);
      whatIfSimSettingsBaseline.chartType = ChartType.WhatIf;
      whatIfSimSettingsBaseline.name = "whatIfSimSettingsBaseline";
      whatIfSimSettingsBaseline.timeBlocks = 200;
      whatIfSimSettingsBaseline.frameIndex = 0;
      whatIfSimSettingsComparison = Object.assign(
        {},
        whatIfSimSettingsBaseline
      );
      whatIfSimSettingsComparison.name = "whatIfSimSettingsComparison";
    }
    updateWhatIfTopControlValues();
  })
);

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
    whatIfSetComparisonButtons.forEach(function (element) {
      element.removeAttribute("disabled");
    });
    if (button == whatIfFabButton) {
      // disable the baseline until a reset
      button.setAttribute("disabled", "");
      whatIfComparisonButton.removeAttribute("disabled");
      whatIfComparisonButton.firstElementChild.innerHTML =
        SimulationActions.Play;
    } else if (button == whatIfComparisonButton) {
      // whatIfFabButton.removeAttribute("disabled");
      // whatIfFabButton.firstElementChild.innerHTML = SimulationActions.Play;
      // Require a reset before running the baseline again
      button.firstElementChild.innerHTML = SimulationActions.Play;
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
  if (whatIfBaselineRadios.value == "preset") {
    whatIfSimSettingsBaseline = new WhatIfSimSettingsDefault();
    whatIfSimSettingsComparison = new WhatIfSimSettingsDefault();
  } else if (whatIfBaselineRadios.value == "lab") {
    whatIfSimSettingsBaseline = Object.assign({}, labSimSettings);
    whatIfSimSettingsComparison = Object.assign({}, whatIfSimSettingsBaseline);
  }
  whatIfSimSettingsBaseline.name = "whatIfSimSettingsBaseline";
  whatIfSimSettingsComparison.name = "whatIfSimSettingsComparison";
  whatIfSetComparisonButtons.forEach(function (element) {
    element.setAttribute("disabled", "");
  });
  updateWhatIfTopControlValues();

  // Charts
  baselineData = null;
  // Remove the canvases
  document.querySelectorAll(".what-if-chart-canvas").forEach((e) => e.remove());
  let canvasIDList = [
    "what-if-phases-chart-canvas",
    "what-if-income-chart-canvas",
    "what-if-wait-chart-canvas",
    "what-if-n-chart-canvas",
    "what-if-platform-chart-canvas",
  ];
  let i = 0;
  document.querySelectorAll(".what-if-canvas-parent").forEach(function (e) {
    let canvas = document.createElement("canvas");
    canvas.setAttribute("class", "what-if-chart-canvas");
    canvas.setAttribute("id", canvasIDList[i]);
    e.appendChild(canvas);
    switch (i) {
      case 0:
        whatIfUISettings.ctxWhatIfN = canvas.getContext("2d");
        break;
      case 1:
        whatIfUISettings.ctxWhatIfPhases = canvas.getContext("2d");
        break;
      case 2:
        whatIfUISettings.ctxWhatIfIncome = canvas.getContext("2d");
        break;
      case 3:
        whatIfUISettings.ctxWhatIfWait = canvas.getContext("2d");
        break;
      case 4:
        whatIfUISettings.ctxWhatIfPlatform = canvas.getContext("2d");
        break;
    }
    i += 1;
  });

  initWhatIfNChart(baselineData, whatIfUISettings);
  initWhatIfPhasesChart(baselineData, whatIfUISettings);
  initWhatIfIncomeChart(baselineData, whatIfUISettings);
  initWhatIfWaitChart(baselineData, whatIfUISettings);
  initWhatIfPlatformChart(baselineData, whatIfUISettings);
}

function updateWhatIfTopControlValues() {
  document.getElementById("what-if-price").innerHTML = new Intl.NumberFormat(
    "EN-CA",
    {
      style: "currency",
      currency: "CAD",
    }
  ).format(whatIfSimSettingsComparison.price);
  let temperature =
    whatIfSimSettingsComparison.price - whatIfSimSettingsBaseline.price;
  let backgroundColor = "#f0f3f3";
  if (temperature > 0.01) {
    backgroundColor = colors.get("WAITING");
  } else if (temperature < -0.01) {
    backgroundColor = colors.get("IDLE");
  } else {
    backgroundColor = "transparent";
  }
  document.getElementById("what-if-price").style.backgroundColor =
    backgroundColor;
  if (temperature < -0.01 || temperature > 0.01) {
    document.getElementById("what-if-price").style.fontWeight = "bold";
  } else {
    document.getElementById("what-if-price").style.fontWeight = "normal";
  }
  document.getElementById("what-if-commission").innerHTML =
    Math.round(whatIfSimSettingsComparison.platformCommission * 100) + "%";
  temperature =
    whatIfSimSettingsComparison.platformCommission -
    whatIfSimSettingsBaseline.platformCommission;
  if (temperature > 0.01) {
    backgroundColor = colors.get("WAITING");
  } else if (temperature < -0.01) {
    backgroundColor = colors.get("IDLE");
  } else {
    backgroundColor = "transparent";
  }
  document.getElementById("what-if-commission").style.backgroundColor =
    backgroundColor;
  if (temperature < -0.01 || temperature > 0.01) {
    document.getElementById("what-if-commission").style.fontWeight = "bold";
  } else {
    document.getElementById("what-if-commission").style.fontWeight = "normal";
  }
  document.getElementById("what-if-cap").innerHTML =
    whatIfSimSettingsComparison.vehicleCount;
  document.getElementById("what-if-reservation-wage").innerHTML =
    new Intl.NumberFormat("EN-CA", {
      style: "currency",
      currency: "CAD",
    }).format(whatIfSimSettingsComparison.reservationWage * 60);
  temperature =
    whatIfSimSettingsComparison.reservationWage -
    whatIfSimSettingsBaseline.reservationWage;
  if (temperature > 0.01) {
    backgroundColor = colors.get("WAITING");
  } else if (temperature < -0.01) {
    backgroundColor = colors.get("IDLE");
  } else {
    backgroundColor = "transparent";
  }
  document.getElementById("what-if-reservation-wage").style.backgroundColor =
    backgroundColor;
  if (temperature < -0.01 || temperature > 0.01) {
    document.getElementById("what-if-reservation-wage").style.fontWeight =
      "bold";
  } else {
    document.getElementById("what-if-reservation-wage").style.fontWeight =
      "normal";
  }
  document.getElementById("what-if-demand").innerHTML = Math.round(
    whatIfSimSettingsComparison.requestRate * 60
  );
  temperature =
    whatIfSimSettingsComparison.requestRate -
    whatIfSimSettingsBaseline.requestRate;
  if (temperature > 0.01) {
    backgroundColor = colors.get("WAITING");
  } else if (temperature < -0.01) {
    backgroundColor = colors.get("IDLE");
  } else {
    backgroundColor = "transparent";
  }
  document.getElementById("what-if-demand").style.backgroundColor =
    backgroundColor;
  if (temperature < -0.01 || temperature > 0.01) {
    document.getElementById("what-if-demand").style.fontWeight = "bold";
  } else {
    document.getElementById("what-if-demand").style.fontWeight = "normal";
  }
  document.getElementById("what-if-demand-elasticity").innerHTML =
    whatIfSimSettingsComparison.demandElasticity;
  temperature =
    whatIfSimSettingsComparison.demandElasticity -
    whatIfSimSettingsBaseline.demandElasticity;
  if (temperature > 0.05) {
    backgroundColor = colors.get("WAITING");
  } else if (temperature < -0.05) {
    backgroundColor = colors.get("IDLE");
  } else {
    backgroundColor = "transparent";
  }
  document.getElementById("what-if-demand-elasticity").style.backgroundColor =
    backgroundColor;
  if (temperature < -0.01 || temperature > 0.01) {
    document.getElementById("what-if-demand-elasticity").style.fontWeight =
      "bold";
  } else {
    document.getElementById("what-if-demand-elasticity").style.fontWeight =
      "normal";
  }
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

  // Charts
  baselineData = null;
  // Remove the canvases
  let canvasIDList = [
    "pg-city-chart-canvas",
    "pg-phases-chart-canvas",
    "pg-trip-chart-canvas",
    "pg-income-chart-canvas",
    "pg-map-chart-canvas",
  ];
  document
    .querySelectorAll(".pg-chart-canvas")
    .forEach((canvas) => canvas.remove());
  let i = 0;
  document.querySelectorAll(".pg-canvas-parent").forEach(function (div) {
    let canvas = document.createElement("canvas");
    canvas.setAttribute("class", "pg-chart-canvas");
    canvas.setAttribute("id", canvasIDList[i]);
    switch (i) {
      case 0:
        if (labUISettings.chartType == ChartType.Stats) {
          div.removeAttribute("hidden");
          div.appendChild(canvas);
          labUISettings.ctxCity = canvas.getContext("2d");
          initCityChart(labUISettings, labSimSettings);
        } else {
          div.setAttribute("hidden", "");
        }
        break;
      case 1:
        if (labUISettings.chartType == ChartType.Stats) {
          div.removeAttribute("hidden");
          div.appendChild(canvas);
          labUISettings.ctxPhases = canvas.getContext("2d");
          initPhasesChart(labUISettings, labSimSettings);
        } else {
          div.setAttribute("hidden", "");
        }
        break;
      case 2:
        if (labUISettings.chartType == ChartType.Stats) {
          div.removeAttribute("hidden");
          div.appendChild(canvas);
          labUISettings.ctxTrip = canvas.getContext("2d");
          initTripChart(labUISettings, labSimSettings);
        } else {
          div.setAttribute("hidden", "");
        }
        break;
      case 3:
        if (labUISettings.chartType == ChartType.Stats) {
          div.removeAttribute("hidden");
          div.appendChild(canvas);
          labUISettings.ctxIncome = canvas.getContext("2d");
          initIncomeChart(labUISettings, labSimSettings);
        } else {
          div.setAttribute("hidden", "");
        }
        break;
      case 4:
        if (labUISettings.chartType == ChartType.Map) {
          div.removeAttribute("hidden");
          div.appendChild(canvas);
          labUISettings.ctxMap = canvas.getContext("2d");
          initMap(labUISettings, labSimSettings);
        } else {
          div.setAttribute("hidden", "");
        }
        break;
    }
    i += 1;
  });
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
  if (button == fabButton) {
    // record current state
    simSettings.frameIndex = document.getElementById("frame-count").innerHTML;
    simSettings.chartType = document.querySelector(
      'input[type="radio"][name="chart-type"]:checked'
    ).value;
    simSettings.citySize = parseInt(inputCitySize.value);
    simSettings.vehicleCount = parseInt(inputVehicleCount.value);
    simSettings.requestRate = parseFloat(inputRequestRate.value);
  }
  if (button.firstElementChild.innerHTML == SimulationActions.Play) {
    // If the button is showing "Play", then the action to take is play
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
    inputFrameTimeout.value = 0;
    simSettings.frameTimeout = 0;
  } else if (uiSettings.chartType == ChartType.Map) {
    inputFrameTimeout.value = 400;
    simSettings.frameTimeout = 400;
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
    element.classList.toggle("mdl-cell--5-col");
    element.classList.toggle("mdl-cell--10-col");
    element = document.getElementById("what-if-chart-column");
    element.classList.toggle("mdl-cell--8-col");
    element.classList.toggle("mdl-cell--12-col");
  } else if (event.key === "p" || event.key === "P") {
    clickFabButton(fabButton, labSimSettings);
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

class WhatIfSimSettingsDefault extends SimSettings {
  constructor() {
    super();
    this.name = "whatIfSimSettingsDefault";
    this.citySize = 24;
    this.vehicleCount = 160;
    this.requestRate = 8;
    this.timeBlocks = 200;
    this.smoothingWindow = 50;
    this.useCityScale = false;
    this.platformCommission = 0.25;
    this.price = 0.6;
    this.reservationWage = 0.21;
    this.tripInhomogeneity = 0.5;
    this.meanVehicleSpeed = 30;
    this.equilibrate = true;
    this.perKmPrice = 0.8;
    this.perMinutePrice = 0.2;
    this.perKmOpsCost = 0.25;
    this.perHourOpportunityCost = 5.0;
    this.action = whatIfFabButton.firstElementChild.innerHTML;
    this.frameTimeout = 0;
    this.chartType = ChartType.WhatIf;
  }
}

var whatIfSimSettingsBaseline = new WhatIfSimSettingsDefault();
var whatIfSimSettingsComparison = new WhatIfSimSettingsDefault();
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

// Listen to the web worker
w.onmessage = function (event) {
  // lineChart.data.datasets[0].data.push({x: event.data[0], y: event.data[1].get("vehicle_fraction_idle")});
  // data comes in from a self.postMessage([blockIndex, vehicleColors, vehicleLocations]);
  if (event.data.size > 1) {
    let frameIndex = event.data.get("block");
    if (event.data.has("vehicles")) {
      plotMap(event.data);
    } else if (event.data.get("chartType") == ChartType.Stats) {
      plotCityChart(event.data);
      plotPhasesChart(event.data);
      plotTripChart(event.data);
      plotIncomeChart(event.data);
    } else if (event.data.get("chartType") == ChartType.WhatIf) {
      // covers both baseline and comparison runs
      plotWhatIfPhasesChart(baselineData, event.data);
      plotWhatIfIncomeChart(baselineData, event.data);
      plotWhatIfWaitChart(baselineData, event.data);
      plotWhatIfNChart(baselineData, event.data);
      plotWhatIfPlatformChart(baselineData, event.data);
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
