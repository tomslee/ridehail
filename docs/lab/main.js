// /* global Chart */
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
  ["RIDING", "rgba(237, 100, 149, 0.5)"],
]);
import {
  initStatsChart,
  initDriverChart,
  plotStats,
  plotDriverStats,
} from "./modules/stats.js";
import { initMap, plotMap } from "./modules/map.js";

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
  resetUIAndSimulation(labUISettings);
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
  resetUIAndSimulation(labUISettings);
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
  resetUIAndSimulation(labUISettings);
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
  resetUIAndSimulation(labUISettings);
};

const inputPerKmPrice = document.getElementById("input-per-km-price");
const optionPerKmPrice = document.getElementById("option-per-km-price");
inputPerKmPrice.onchange = function () {
  optionPerKmPrice.innerHTML = this.value;
  labSimSettings.pricePerKm = this.value;
  resetUIAndSimulation(labUISettings);
};

const inputPerMinutePrice = document.getElementById("input-per-minute-price");
const optionPerMinutePrice = document.getElementById("option-per-minute-price");
inputPerMinutePrice.onchange = function () {
  optionPerMinutePrice.innerHTML = this.value;
  labSimSettings.perMinutePrice = this.value;
  resetUIAndSimulation(labUISettings);
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
  // resetUIAndSimulation(labUISettings);
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
  resetUIAndSimulation(labUISettings);
};

const inputPerKmOpsCost = document.getElementById("input-per-km-ops-cost");
const optionPerKmOpsCost = document.getElementById("option-per-km-ops-cost");
inputPerKmOpsCost.onchange = function () {
  optionPerKmOpsCost.innerHTML = this.value;
  labSimSettings.perKmOpsCost = this.value;
  resetUIAndSimulation(labUISettings);
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
  resetUIAndSimulation(labUISettings);
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
};

/**
 * @Class
 * Container for simulation settings, which will be posted to webworker to
 * interact with the pyodide python module
 */
class simSettings {
  /**
   * For now, a set of "reasonable" defaults are set on initialization. It
   * would be good to have these chosen in a less arbitrary fashion.
   */
  constructor() {
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
    this.chartType = null;
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

async function resetUIAndSimulation(labUISettings) {
  resetButton.removeAttribute("disabled");
  nextStepButton.removeAttribute("disabled");
  fabButton.removeAttribute("disabled");
  spinner.classList.remove("is-active");
  spinner.style.display = "none";
  fabButton.firstElementChild.innerHTML = SimulationActions.Play;
  nextStepButton.removeAttribute("disabled");
  optionFrameTimeout.innerHTML = inputFrameTimeout.value;
  labSimSettings.frameTimeout = inputFrameTimeout.value;
  labSimSettings.frameIndex = 0;
  labSimSettings.action = SimulationActions.Reset;
  /* Simple or advanced? */
  updateUIMode(labUISettings.uiMode);
  w.postMessage(labSimSettings);
  document.getElementById("frame-count").innerHTML = labSimSettings.frameIndex;
  document.getElementById("top-control-spinner").style.display = "none";
  // Create a new chart
  if (labUISettings.chartType == "stats") {
    pgDriverCanvas.style.display = "block";
    initStatsChart(labUISettings, labSimSettings, "bar");
    initDriverChart(labUISettings, labSimSettings);
  } else if (labUISettings.chartType == "map") {
    pgDriverCanvas.style.display = "none";
    initMap(labUISettings, labSimSettings);
  }
}

resetButton.onclick = function () {
  labUISettings.ctx = pgCanvas.getContext("2d");
  resetUIAndSimulation(labUISettings);
};

function toggleFabButton() {
  if (fabButton.firstElementChild.innerHTML == SimulationActions.Play) {
    // pause the simulation
    fabButton.firstElementChild.innerHTML = SimulationActions.Pause;
    nextStepButton.setAttribute("disabled", "");
  } else {
    // start or continue the simulation
    fabButton.firstElementChild.innerHTML = SimulationActions.Play;
    nextStepButton.removeAttribute("disabled");
    resetButton.removeAttribute("disabled");
  }
  let resetControls = document.querySelectorAll(".ui-mode-reset");
  resetControls.forEach(function (element) {
    let input = element.getElementsByTagName("input")[0];
    if (labSimSettings.action == SimulationActions.Pause) {
      input.setAttribute("disabled", "");
    } else {
      input.removeAttribute("disabled");
    }
  });
}

function clickFabButton() {
  // If the button is currently showing "Play", then the action to take
  // is play
  if (fabButton.firstElementChild.innerHTML == SimulationActions.Play) {
    labSimSettings.action = SimulationActions.Play;
  } else {
    // The button should be showing "Pause", and the action to take is to pause
    labSimSettings.action = SimulationActions.Pause;
  }
  labSimSettings.frameIndex = document.getElementById("frame-count").innerHTML;
  (labSimSettings.chartType = document.querySelector(
    'input[type="radio"][name="chart-type"]:checked'
  ).value),
    (labSimSettings.citySize = parseInt(inputCitySize.value));
  labSimSettings.vehicleCount = parseInt(inputVehicleCount.value);
  labSimSettings.requestRate = parseFloat(inputRequestRate.value);
  w.postMessage(labSimSettings);
  // Now make the button look different
  toggleFabButton();
}

fabButton.onclick = function () {
  clickFabButton();
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
    resetUIAndSimulation(labUISettings);
  })
);

function updateUIMode(uiModeRadiosValue) {
  labUISettings.uiMode = uiModeRadiosValue;
  /* Controls are either advanced (only), simple (only) or both */
  let simpleControls = document.querySelectorAll(".ui-mode-simple");
  simpleControls.forEach(function (element) {
    if (labUISettings.uiMode == "advanced") {
      element.style.display = "none";
    } else {
      element.style.display = "block";
    }
  });
  let advancedControls = document.querySelectorAll(".ui-mode-advanced");
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
  radio.addEventListener("change", () => updateChartType(radio.value))
);

function updateChartType(value) {
  labUISettings.chartType = value;
  labSimSettings.chartType = value;
  if (labUISettings.chartType == "stats") {
    inputFrameTimeout.value = 10;
    labSimSettings.frameTimeout = 10;
  } else {
    inputFrameTimeout.value = 300;
    labSimSettings.frameTimeout = 300;
  }
  optionFrameTimeout.innerHTML = inputFrameTimeout.value;
  let statsDescriptions = document.querySelectorAll(".pg-stats-descriptions");
  statsDescriptions.forEach(function (element) {
    if (labUISettings.chartType == "map") {
      element.style.display = "none";
    } else {
      element.style.display = "block";
    }
  });
  resetUIAndSimulation(labUISettings);
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
  labUISettings.ctx = pgCanvas.getContext("2d");
  labUISettings.ctxDriver = pgDriverCanvas.getContext("2d");
  resetUIAndSimulation(labUISettings);
}

/*
 * Simulation options
 */

inputFrameTimeout.onchange = function () {
  optionFrameTimeout.innerHTML = this.value;
  labSimSettings.frameTimeout = this.value;
  // ctx = pgCanvas.getContext("2d");
  // resetUIAndSimulation(ctx);
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
  labUISettings.ctx = pgCanvas.getContext("2d");
  resetUIAndSimulation(labUISettings);
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
    clickFabButton();
  }
});

var labSimSettings = new simSettings();
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
/*
 * Interaction with web worker
 */

if (typeof w == "undefined") {
  // var w = new Worker("webworker.js", {type: 'module'});
  var w = new Worker("webworker.js");
}

function handlePyodideready() {
  resetUIAndSimulation(labUISettings);
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
    labSimSettings.frameIndex = event.data.get("block");
    document.getElementById("frame-count").innerHTML =
      labSimSettings.frameIndex;
    if (event.data.has("vehicles")) {
      plotMap(event.data);
    } else {
      plotStats(event.data, "bar");
      plotDriverStats(event.data);
    }
    updateTextStatus(event.data);
  } else if (event.data.size == 1) {
    if (event.data.get("text") == "Pyodide loaded") {
      handlePyodideready();
    } else {
      // probably an error labSimSettings
      console.log("Error in main: event.data=", event.data);
    }
  }
};
