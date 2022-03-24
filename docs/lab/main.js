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
  labSettings.citySize = this.value;
  resetUIAndSimulation(uiSettings);
};

const inputTwoZone = document.getElementById("input-two-zone");
const optionTwoZone = document.getElementById("option-two-zone");
inputTwoZone.onchange = function () {
  optionTwoZone.innerHTML = this.value;
  labSettings.tripInhomogeneity = this.value;
  updateSimulationOptions("updateSim");
};

const inputMaxTripDistance = document.getElementById("input-max-trip-distance");
const optionMaxTripDistance = document.getElementById(
  "option-max-trip-distance"
);
inputMaxTripDistance.onchange = function () {
  labSettings.maxTripDistance = parseInt(this.value);
  this.value = Math.min(labSettings.maxTripDistance, labSettings.citySize);
  optionMaxTripDistance.innerHTML = this.value;
  resetUIAndSimulation(uiSettings);
};

// Vehicles
const inputVehicleCount = document.getElementById("input-vehicle-count");
const optionVehicleCount = document.getElementById("option-vehicle-count");
inputVehicleCount.onchange = function () {
  optionVehicleCount.innerHTML = this.value;
  labSettings.vehicleCount = parseInt(this.value);
  /* simSettings do not use all parameters. Set them to null */
  if (labSettings.simState == "pause" || labSettings.simState == "play") {
    // update live
    updateSimulationOptions("updateSim");
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
  labSettings.meanVehicleSpeed = parseFloat(this.value);
  resetUIAndSimulation(uiSettings);
};

const inputRequestRate = document.getElementById("input-request-rate");
const optionRequestRate = document.getElementById("option-request-rate");
inputRequestRate.onchange = function () {
  optionRequestRate.innerHTML = this.value;
  labSettings.requestRate = parseFloat(this.value);
  if (labSettings.simState == "pause" || labSettings.simState == "play") {
    // update live
    updateSimulationOptions("updateSim");
  }
};

const checkboxEquilibrate = document.getElementById("checkbox-equilibrate");
checkboxEquilibrate.onclick = function () {
  labSettings.equilibrate = checkboxEquilibrate.checked;
  if (labSettings.simState == "pause" || labSettings.simState == "play") {
    // update live
    updateSimulationOptions("updateSim");
  }
};

// Fares and wages
const inputPrice = document.getElementById("input-price");
const optionPrice = document.getElementById("option-price");
inputPrice.onchange = function () {
  optionPrice.innerHTML = this.value;
  labSettings.price = this.value;
  resetUIAndSimulation(uiSettings);
};

const inputPerKmPrice = document.getElementById("input-per-km-price");
const optionPerKmPrice = document.getElementById("option-per-km-price");
inputPerKmPrice.onchange = function () {
  optionPerKmPrice.innerHTML = this.value;
  labSettings.pricePerKm = this.value;
  resetUIAndSimulation(uiSettings);
};

const inputPerMinutePrice = document.getElementById("input-per-minute-price");
const optionPerMinutePrice = document.getElementById("option-per-minute-price");
inputPerMinutePrice.onchange = function () {
  optionPerMinutePrice.innerHTML = this.value;
  labSettings.perMinutePrice = this.value;
  resetUIAndSimulation(uiSettings);
};

const inputPlatformCommission = document.getElementById(
  "input-platform-commission"
);
const optionPlatformCommission = document.getElementById(
  "option-platform-commission"
);
inputPlatformCommission.onchange = function () {
  optionPlatformCommission.innerHTML = this.value;
  labSettings.platformCommission = this.value;
  // resetUIAndSimulation(uiSettings);
  if (labSettings.simState == "pause" || labSettings.simState == "play_arrow") {
    // update live
    updateSimulationOptions("updateSim");
  }
};

const inputReservationWage = document.getElementById("input-reservation-wage");
const optionReservationWage = document.getElementById(
  "option-reservation-wage"
);
inputReservationWage.onchange = function () {
  optionReservationWage.innerHTML = this.value;
  labSettings.reservationWage = this.value;
  resetUIAndSimulation(uiSettings);
};

const inputPerKmOpsCost = document.getElementById("input-per-km-ops-cost");
const optionPerKmOpsCost = document.getElementById("option-per-km-ops-cost");
inputPerKmOpsCost.onchange = function () {
  optionPerKmOpsCost.innerHTML = this.value;
  labSettings.perKmOpsCost = this.value;
  resetUIAndSimulation(uiSettings);
};

const inputPerHourOpportunityCost = document.getElementById(
  "input-per-hour-opportunity-cost"
);
const optionPerHourOpportunityCost = document.getElementById(
  "option-per-hour-opportunity-cost"
);
inputPerHourOpportunityCost.onchange = function () {
  optionPerHourOpportunityCost.innerHTML = this.value;
  labSettings.perHourOpportunityCost = this.value;
  resetUIAndSimulation(uiSettings);
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

class simSettings {
  constructor() {
    this.citySize = inputCitySize.value;
    this.vehicleCount = inputVehicleCount.value;
    this.requestRate = inputRequestRate.value;
    this.smoothingWindow = inputSmoothingWindow.value;
    this.maxTripDistance = null;
    this.tripInhomogeneity = 0;
    this.tripInhomogeneousDestinations = false;
    this.idleVehiclesMoving = true;
    this.equilibrate = false;
    this.equilibration = "price";
    this.equilibrationInterval = 5;
    this.demandElasticity = 0;
    this.price = inputPrice.value;
    this.platformCommission = 0;
    this.reservationWage = 0;
    this.useCityScale = false;
    this.minutesPerBlock = 1;
    this.meanVehicleSpeed = 30.0;
    this.perKmPrice = 0.18;
    this.perMinutePrice = 0.81;
    this.perKmOpsCost = 0.2;
    this.perHourOpportunityCost = 10;
    this.randomNumberSeed = 87;
    this.verbosity = 0;
    this.timeBlocks = 0;
    this.frameIndex = 0;
    this.action = null;
    this.simState = "reset";
    this.frameTimeout = 0;
    this.chartType = null;
  }
}

var uiSettings = {
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
  labSettings.action = updateType;
  w.postMessage(labSettings);
}

async function resetUIAndSimulation(uiSettings) {
  resetButton.removeAttribute("disabled");
  nextStepButton.removeAttribute("disabled");
  fabButton.removeAttribute("disabled");
  spinner.classList.remove("is-active");
  spinner.style.display = "none";
  fabButton.firstElementChild.innerHTML = "play_arrow";
  nextStepButton.removeAttribute("disabled");
  optionFrameTimeout.innerHTML = inputFrameTimeout.value;
  labSettings.frameTimeout = inputFrameTimeout.value;
  labSettings.frameIndex = 0;
  labSettings.simState = "reset";
  labSettings.action = "reset";
  /* Simple or advanced? */
  updateUIMode(uiSettings.uiMode);
  w.postMessage(labSettings);
  document.getElementById("frame-count").innerHTML = labSettings.frameIndex;
  document.getElementById("top-control-spinner").style.display = "none";
  // Create a new chart
  if (uiSettings.chartType == "stats") {
    pgDriverCanvas.style.display = "block";
    initStatsChart(uiSettings, labSettings, "bar");
    initDriverChart(uiSettings, labSettings);
  } else if (uiSettings.chartType == "map") {
    pgDriverCanvas.style.display = "none";
    initMap(uiSettings, labSettings);
  }
}

resetButton.onclick = function () {
  uiSettings.ctx = pgCanvas.getContext("2d");
  resetUIAndSimulation(uiSettings);
};

function toggleFabButton() {
  if (fabButton.firstElementChild.innerHTML == "play_arrow") {
    // pause the simulation
    labSettings.simState = "pause";
    fabButton.firstElementChild.innerHTML = "pause";
    nextStepButton.setAttribute("disabled", "");
  } else {
    // start or continue the simulation
    labSettings.simState = "play";
    resetButton.removeAttribute("disabled");
    nextStepButton.removeAttribute("disabled");
    fabButton.firstElementChild.innerHTML = "play_arrow";
  }
  let resetControls = document.querySelectorAll(".ui-mode-reset");
  resetControls.forEach(function (element) {
    let input = element.getElementsByTagName("input")[0];
    if (labSettings.simState == "pause") {
      input.setAttribute("disabled", "");
    } else {
      input.removeAttribute("disabled");
    }
  });
}

function clickFabButton() {
  labSettings.action = fabButton.firstElementChild.innerHTML;
  labSettings.frameIndex = document.getElementById("frame-count").innerHTML;
  (labSettings.chartType = document.querySelector(
    'input[type="radio"][name="chart-type"]:checked'
  ).value),
    (labSettings.citySize = parseInt(inputCitySize.value));
  labSettings.vehicleCount = parseInt(inputVehicleCount.value);
  labSettings.requestRate = parseFloat(inputRequestRate.value);
  toggleFabButton();
  w.postMessage(labSettings);
}

fabButton.onclick = function () {
  clickFabButton();
};

nextStepButton.onclick = function () {
  labSettings.action = "single-step";
  labSettings.simState = "pause";
  w.postMessage(labSettings);
};

/*
 * UI Mode radio button
 */
uiModeRadios.forEach((radio) =>
  radio.addEventListener("change", () => {
    updateUIMode(radio.value);
    uiSettings.ctx = pgCanvas.getContext("2d");
    resetUIAndSimulation(uiSettings);
  })
);

function updateUIMode(uiModeRadiosValue) {
  uiSettings.uiMode = uiModeRadiosValue;
  /* Controls are either advanced (only), simple (only) or both */
  let simpleControls = document.querySelectorAll(".ui-mode-simple");
  simpleControls.forEach(function (element) {
    if (uiSettings.uiMode == "advanced") {
      element.style.display = "none";
    } else {
      element.style.display = "block";
    }
  });
  let advancedControls = document.querySelectorAll(".ui-mode-advanced");
  advancedControls.forEach(function (element) {
    if (uiSettings.uiMode == "advanced") {
      element.style.display = "block";
    } else {
      element.style.display = "none";
    }
  });
  /* labSettings do not use all parameters. Set them to null */
  if (uiSettings.uiMode == "advanced") {
    labSettings.useCityScale = true;
    // max trip distance cannoe be bigger than citySize
    labSettings.maxTripDistance = parseInt(inputMaxTripDistance.value);
  } else if (uiSettings.uiMode == "simple") {
    labSettings.useCityScale = false;
    labSettings.maxTripDistance = null;
  }
}

chartTypeRadios.forEach((radio) =>
  radio.addEventListener("change", () => updateChartType(radio.value))
);

function updateChartType(value) {
  uiSettings.chartType = value;
  labSettings.chartType = value;
  if (uiSettings.chartType == "stats") {
    inputFrameTimeout.value = 10;
    labSettings.frameTimeout = 10;
  } else {
    inputFrameTimeout.value = 300;
    labSettings.frameTimeout = 300;
  }
  optionFrameTimeout.innerHTML = inputFrameTimeout.value;
  let statsDescriptions = document.querySelectorAll(".pg-stats-descriptions");
  statsDescriptions.forEach(function (element) {
    if (uiSettings.chartType == "map") {
      element.style.display = "none";
    } else {
      element.style.display = "block";
    }
  });
  resetUIAndSimulation(uiSettings);
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
    uiSettings.roadWidth = 10;
    uiSettings.vehicleRadius = 10;
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
    uiSettings.roadWidth = 6;
    uiSettings.vehicleRadius = 6;
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
    uiSettings.roadWidth = 3;
    uiSettings.vehicleRadius = 3;
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
  labSettings.action = "reset";
  labSettings.frameIndex = 0;
  (labSettings.chartType = document.querySelector(
    'input[type="radio"][name="chart-type"]:checked'
  ).value),
    (labSettings.citySize = citySizeValue);
  uiSettings.ctx = pgCanvas.getContext("2d");
  uiSettings.ctxDriver = pgDriverCanvas.getContext("2d");
  resetUIAndSimulation(uiSettings);
}

/*
 * Simulation options
 */

inputFrameTimeout.onchange = function () {
  optionFrameTimeout.innerHTML = this.value;
  labSettings.frameTimeout = this.value;
  // ctx = pgCanvas.getContext("2d");
  // resetUIAndSimulation(ctx);
  if (labSettings.simState == "pause" || labSettings.simState == "play") {
    // update live
    updateSimulationOptions("updateDisplay");
  }
};
inputSmoothingWindow.onchange = function () {
  optionSmoothingWindow.innerHTML = this.value;
  labSettings.smoothingWindow = this.value;
  uiSettings.ctx = pgCanvas.getContext("2d");
  resetUIAndSimulation(uiSettings);
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

var labSettings = new simSettings();
labSettings.useCityScale = uiSettings.uiMode;
labSettings.platformCommission = inputPlatformCommission.value;
labSettings.reservationWage = inputReservationWage.value;
labSettings.meanVehicleSpeed = inputMeanVehicleSpeed.value;
labSettings.perKmPrice = inputPerKmPrice.value;
labSettings.perMinutePrice = inputPerMinutePrice.value;
labSettings.perKmOpsCost = inputPerKmOpsCost.value;
labSettings.perHourOpportunityCost = inputPerHourOpportunityCost.value;
labSettings.action = fabButton.firstElementChild.innerHTML;
labSettings.frameTimeout = inputFrameTimeout.value;
labSettings.chartType = document.querySelector(
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
  resetUIAndSimulation(uiSettings);
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
    labSettings.frameIndex = event.data.get("block");
    document.getElementById("frame-count").innerHTML = labSettings.frameIndex;
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
      // probably an error labSettings
      console.log("Error in main: event.data=", event.data);
    }
  }
};
