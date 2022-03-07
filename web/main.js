/* global Chart */
export const colors = new Map([
  // Road
  ["ROAD", "rgba(232, 232, 232, 0.7)"],
  // Vehicles
  ["IDLE", "rgba(100, 149, 237, 0.7)"],
  ["DISPATCHED", "rgba(215, 142, 0, 0.7)"],
  ["WITH_RIDER", "rgba(60, 179, 113, 0.7)"],
  // Trips
  ["UNASSIGNED", "rgba(237, 100, 149, 0.7)"],
  ["WAITING", "rgba(237, 100, 149, 0.7)"],
  ["RIDING", "rgba(237, 100, 149, 0.7)"],
]);
import {
  initStatsChart,
  initDriverChart,
  plotStats,
  plotDriverStats,
} from "./modules/stats.js";
import { initMap, plotMap } from "./modules/map.js";
const minutesPerHour = 60;
const inputCitySize = document.getElementById("input-city-size");
const optionCitySize = document.getElementById("option-city-size");
const inputVehicleCount = document.getElementById("input-vehicle-count");
const optionVehicleCount = document.getElementById("option-vehicle-count");
const inputRequestRate = document.getElementById("input-request-rate");
const optionRequestRate = document.getElementById("option-request-rate");
//const inputBlocksPerUnit = document.getElementById("input-blocks-per-unit");
//const optionBlocksPerUnit = document.getElementById("option-blocks-per-unit");
const checkboxEquilibrate = document.getElementById("checkbox-equilibrate");
const inputMeanVehicleSpeed = document.getElementById(
  "input-mean-vehicle-speed"
);
const optionMeanVehicleSpeed = document.getElementById(
  "option-mean-vehicle-speed"
);
const inputTwoZone = document.getElementById("input-two-zone");
const optionTwoZone = document.getElementById("option-two-zone");
const inputPerKmPrice = document.getElementById("input-per-km-price");
const optionPerKmPrice = document.getElementById("option-per-km-price");
const inputPerMinPrice = document.getElementById("input-per-min-price");
const optionPerMinPrice = document.getElementById("option-per-min-price");
const inputPlatformCommission = document.getElementById(
  "input-platform-commission"
);
const optionPlatformCommission = document.getElementById(
  "option-platform-commission"
);
const inputPerKmOpsCost = document.getElementById("input-per-km-ops-cost");
const optionPerKmOpsCost = document.getElementById("option-per-km-ops-cost");
const inputPerUnitOppCost = document.getElementById("input-per-unit-opp-cost");
const optionPerUnitOppCost = document.getElementById(
  "option-per-unit-opp-cost"
);

const inputFrameTimeout = document.getElementById("input-frame-timeout");
const optionFrameTimeout = document.getElementById("option-frame-timeout");
const inputSmoothingWindow = document.getElementById("input-smoothing-window");
const optionSmoothingWindow = document.getElementById(
  "option-smoothing-window"
);
const spinner = document.getElementById("spinner");
const resetButton = document.getElementById("reset-button");
const fabButton = document.getElementById("fab-button");
const nextStepButton = document.getElementById("next-step-button");
const pgCanvas = document.getElementById("pg-chart-canvas");
const pgDriverCanvas = document.getElementById("pg-driver-chart-canvas");
const storyTimeButton1 = document.getElementById("st1-button");
const storyTimeButton2 = document.getElementById("st2-button");
const stCanvas1 = document.getElementById("st1-chart-canvas");
const stCanvas2 = document.getElementById("st2-chart-canvas");
const uiModeRadios = document.querySelectorAll(
  'input[type=radio][name="ui-mode"]'
);
const communityRadios = document.querySelectorAll(
  'input[type=radio][name="community"]'
);
const chartTypeRadios = document.querySelectorAll(
  'input[type=radio][name="chart-type"]'
);

var uiSettings = {
  uiMode: document.querySelector('input[type="radio"][name="ui-mode"]:checked')
    .value,
  ctx: pgCanvas.getContext("2d"),
  ctxDriver: pgDriverCanvas.getContext("2d"),
  chartType: document.querySelector(
    'input[type="radio"][name="chart-type"]:checked'
  ).value,
};

export var simSettings = {
  frameIndex: 0,
  simState: "reset",
  action: fabButton.firstElementChild.innerHTML,
  chartType: document.querySelector(
    'input[type="radio"][name="chart-type"]:checked'
  ).value,
  citySize: inputCitySize.value,
  vehicleCount: inputVehicleCount.value,
  requestRate: inputRequestRate.value,
  frameTimeout: inputFrameTimeout.value,
  smoothingWindow: inputSmoothingWindow.value,
  cityScaleUnit: "min",
  blocksPerUnit: 1,
  tripInhomogeneity: 0,
  meanVehicleSpeed: inputMeanVehicleSpeed.value,
  useCityScale: uiSettings.uiMode,
  equilibrate: false,
  equilibration: "price",
  perKmPrice: inputPerKmPrice.value,
  perMinPrice: inputPerMinPrice.value,
  price: 1.25,
  platformCommission: 0.25,
  perKmOpsCost: inputPerKmOpsCost.value,
  perUnitOppCost: inputPerUnitOppCost.value / minutesPerHour,
  reservedWage: 0.35,
  randomNumberSeed: 87,
  vehicleRadius: 9,
  roadWidth: 10,
};

/*
 * UI actions
 */

/*
 * Story time
 */

storyTimeButton1.onclick = async function () {
  // Reset to defaults
  // Override where necessary
  simSettings.simState = "play";
  simSettings.citySize = 4;
  simSettings.requestRate = 0;
  simSettings.vehicleCount = 1;
  simSettings.frameTimeout = 300;
  simSettings.timeBlocks = 20;
  simSettings.vehicleRadius = 9;
  simSettings.roadWidth = 10;
  simSettings.tripInhomogeneity = 0;
  simSettings.chartType = "map";
  uiSettings.chartType = "map";
  uiSettings.ctx = stCanvas1.getContext("2d");
  await resetUIAndSimulation(uiSettings);
  simSettings.frameIndex = 0;
  simSettings.action = "play_arrow";
  w.postMessage(simSettings);
};

storyTimeButton2.onclick = async function () {
  // Reset to defaults
  // Override where necessary
  simSettings.simState = "play";
  simSettings.citySize = 4;
  simSettings.requestRate = 0.16;
  simSettings.vehicleCount = 1;
  simSettings.frameTimeout = 300;
  simSettings.timeBlocks = 50;
  simSettings.vehicleRadius = 9;
  simSettings.roadWidth = 10;
  simSettings.tripInhomogeneity = 0;
  simSettings.chartType = "map";
  uiSettings.chartType = "map";
  uiSettings.ctx = stCanvas2.getContext("2d");
  await resetUIAndSimulation(uiSettings);
  simSettings.action = "play_arrow";
  simSettings.frameIndex = 0;
  w.postMessage(simSettings);
};

/*
 * Top-level controls (reset, play/pause, next step)
 */

function updateSimulationOptions(updateType) {
  simSettings.action = updateType;
  w.postMessage(simSettings);
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
  simSettings.frameIndex = 0;
  simSettings.frameTimeout = inputFrameTimeout.value;
  simSettings.simState = "reset";
  simSettings.action = "reset";
  /* Simple or advanced? */
  updateUIMode(uiSettings.uiMode);
  w.postMessage(simSettings);
  document.getElementById("frame-count").innerHTML = simSettings.frameIndex;
  // Destroy any charts
  if (window.chart instanceof Chart) {
    window.chart.destroy();
  }
  // Create a new chart
  if (uiSettings.chartType == "stats") {
    pgDriverCanvas.style.display = "block";
    initStatsChart(uiSettings.ctx, "bar");
    initDriverChart(uiSettings.ctxDriver);
  } else if (uiSettings.chartType == "map") {
    pgDriverCanvas.style.display = "none";
    initMap(uiSettings.ctx);
  }
}

resetButton.onclick = function () {
  uiSettings.ctx = pgCanvas.getContext("2d");
  resetUIAndSimulation(uiSettings);
};

function toggleFabButton() {
  if (fabButton.firstElementChild.innerHTML == "play_arrow") {
    // pause the simulation
    simSettings.simState = "pause";
    fabButton.firstElementChild.innerHTML = "pause";
    nextStepButton.setAttribute("disabled", "");
  } else {
    // start or continue the simulation
    simSettings.simState = "play";
    resetButton.removeAttribute("disabled");
    nextStepButton.removeAttribute("disabled");
    fabButton.firstElementChild.innerHTML = "play_arrow";
  }
}

function clickFabButton() {
  simSettings.action = fabButton.firstElementChild.innerHTML;
  simSettings.frameIndex = document.getElementById("frame-count").innerHTML;
  (simSettings.chartType = document.querySelector(
    'input[type="radio"][name="chart-type"]:checked'
  ).value),
    (simSettings.citySize = inputCitySize.value);
  simSettings.vehicleCount = inputVehicleCount.value;
  simSettings.requestRate = inputRequestRate.value;
  simSettings.timeBlocks = 2000;
  toggleFabButton();
  w.postMessage(simSettings);
}

fabButton.onclick = function () {
  clickFabButton();
};

nextStepButton.onclick = function () {
  simSettings.action = "single-step";
  simSettings.simState = "pause";
  w.postMessage(simSettings);
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
  let advancedControls = document.querySelectorAll(".ui-mode-advanced");
  let simpleControls = document.querySelectorAll(".ui-mode-simple");
  simpleControls.forEach(function (element) {
    if (uiSettings.uiMode == "advanced") {
      element.style.display = "none";
    } else {
      element.style.display = "block";
    }
  });
  advancedControls.forEach(function (element) {
    if (uiSettings.uiMode == "advanced") {
      element.style.display = "block";
    } else {
      element.style.display = "none";
    }
  });
  if (uiSettings.uiMode == "advanced") {
    simSettings.useCityScale = true;
  } else if (uiSettings.uiMode == "simple") {
    simSettings.useCityScale = false;
  }
}

chartTypeRadios.forEach((radio) =>
  radio.addEventListener("change", () => updateChartType(radio.value))
);

function updateChartType(value) {
  uiSettings.chartType = value;
  simSettings.chartType = value;
  if (uiSettings.chartType == "stats") {
    inputFrameTimeout.value = 10;
    simSettings.frameTimeout = 10;
  } else {
    inputFrameTimeout.value = 300;
    simSettings.frameTimeout = 300;
  }
  resetUIAndSimulation(uiSettings);
}

/* 
   * cityScaleUnitRadios.forEach((radio) =>
  radio.addEventListener("change", () => updateCityScaleUnit(radio.value))
);

function updateCityScaleUnit(value) {
  simSettings.cityScaleUnit = value;
  resetUIAndSimulation(uiSettings);
}
*/
/*
 * Community radio button
 */

communityRadios.forEach((radio) =>
  radio.addEventListener("change", () => updateOptionsForCommunity(radio.value))
);

function updateOptionsForCommunity(value) {
  let citySizeValue = inputCitySize.value;
  let citySizeMin = inputCitySize.min;
  let citySizeMax = inputCitySize.max;
  let citySizeStep = inputCitySize.step;
  let vehicleCountValue = inputVehicleCount.value;
  let vehicleCountMin = inputVehicleCount.min;
  let vehicleCountMax = inputVehicleCount.max;
  let vehicleCountStep = inputVehicleCount.step;
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
    requestRateValue = 0.5;
    requestRateMin = 0;
    requestRateMax = 2;
    requestRateStep = 0.1;
    simSettings.roadWidth = 10;
    simSettings.vehicleRadius = 10;
  } else if (value == "town") {
    citySizeValue = 24;
    citySizeMin = 16;
    citySizeMax = 64;
    citySizeStep = 4;
    vehicleCountValue = 224;
    vehicleCountMin = 8;
    vehicleCountMax = 512;
    vehicleCountStep = 8;
    requestRateValue = 8;
    requestRateMin = 1;
    requestRateMax = 48;
    requestRateStep = 4;
    simSettings.roadWidth = 6;
    simSettings.vehicleRadius = 6;
  } else if (value == "city") {
    citySizeValue = 48;
    citySizeMin = 32;
    citySizeMax = 64;
    citySizeStep = 8;
    vehicleCountValue = 1760;
    vehicleCountMin = 32;
    vehicleCountMax = 6400;
    vehicleCountStep = 16;
    requestRateValue = 48;
    requestRateMin = 8;
    requestRateMax = 196;
    requestRateStep = 8;
    simSettings.roadWidth = 3;
    simSettings.vehicleRadius = 3;
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
  inputRequestRate.min = requestRateMin;
  inputRequestRate.max = requestRateMax;
  inputRequestRate.step = requestRateStep;
  inputRequestRate.value = requestRateValue;
  optionRequestRate.innerHTML = 60 * requestRateValue;
  simSettings.action = "reset";
  simSettings.frameIndex = 0;
  (simSettings.chartType = document.querySelector(
    'input[type="radio"][name="chart-type"]:checked'
  ).value),
    (simSettings.citySize = citySizeValue);
  simSettings.vehicleCount = vehicleCountValue;
  simSettings.requestRate = requestRateValue;
  simSettings.timeBlocks = 1000;
  uiSettings.ctx = pgCanvas.getContext("2d");
  uiSettings.ctxDriver = pgDriverCanvas.getContext("2d");
  resetUIAndSimulation(uiSettings);
}

/*
 * Simulation options
 */

/* TODO: I am sure these can all be linked to a single event listener */

checkboxEquilibrate.onclick = function () {
  simSettings.equilibrate = checkboxEquilibrate.checked;
  if (simSettings.simState == "pause" || simSettings.simState == "play") {
    // update live
    updateSimulationOptions("updateSim");
  }
};

inputTwoZone.onchange = function () {
  optionTwoZone.innerHTML = this.value;
  simSettings.tripInhomogeneity = this.value;
  updateSimulationOptions("updateSim");
};

inputCitySize.onchange = function () {
  optionCitySize.innerHTML = this.value;
  simSettings.citySize = this.value;
  resetUIAndSimulation(uiSettings);
};

inputVehicleCount.onchange = function () {
  optionVehicleCount.innerHTML = this.value;
  simSettings.vehicleCount = this.value;
  if (simSettings.simState == "pause" || simSettings.simState == "play") {
    // update live
    updateSimulationOptions("updateSim");
  }
};
inputRequestRate.onchange = function () {
  optionRequestRate.innerHTML = 60 * this.value;
  simSettings.requestRate = this.value;
  if (simSettings.simState == "pause" || simSettings.simState == "play") {
    // update live
    updateSimulationOptions("updateSim");
  }
};
inputMeanVehicleSpeed.onchange = function () {
  optionMeanVehicleSpeed.innerHTML = this.value;
  simSettings.meanVehicleSpeed = this.value;
  resetUIAndSimulation(uiSettings);
};
/*
inputBlocksPerUnit.onchange = function () {
  optionBlocksPerUnit.innerHTML = this.value;
  simSettings.blocksPerUnit = this.value;
  resetUIAndSimulation(uiSettings);
};
*/
inputPerKmPrice.onchange = function () {
  optionPerKmPrice.innerHTML = this.value;
  simSettings.pricePerKm = this.value;
  resetUIAndSimulation(uiSettings);
};
inputPerMinPrice.onchange = function () {
  optionPerMinPrice.innerHTML = this.value;
  simSettings.perMinPrice = this.value;
  resetUIAndSimulation(uiSettings);
};
inputPlatformCommission.onchange = function () {
  optionPlatformCommission.innerHTML = this.value;
  simSettings.platformCommission = this.value;
  resetUIAndSimulation(uiSettings);
};
inputPerKmOpsCost.onchange = function () {
  optionPerKmOpsCost.innerHTML = this.value;
  simSettings.perKmOpsCost = this.value;
  resetUIAndSimulation(uiSettings);
};
inputPerUnitOppCost.onchange = function () {
  optionPerUnitOppCost.innerHTML = this.value;
  simSettings.perUnitOppCost = this.value / minutesPerHour;
  resetUIAndSimulation(uiSettings);
};

inputFrameTimeout.onchange = function () {
  optionFrameTimeout.innerHTML = this.value;
  simSettings.frameTimeout = this.value;
  // ctx = pgCanvas.getContext("2d");
  // resetUIAndSimulation(ctx);
  if (simSettings.simState == "pause" || simSettings.simState == "play") {
    // update live
    updateSimulationOptions("updateDisplay");
  }
};
inputSmoothingWindow.onchange = function () {
  optionSmoothingWindow.innerHTML = this.value;
  simSettings.smoothingWindow = this.value;
  uiSettings.ctx = pgCanvas.getContext("2d");
  resetUIAndSimulation(uiSettings);
};

/*
 * Capture keypress events
 */

document.addEventListener("keyup", function (event) {
  if (event.key === "f" || event.key === "F") {
    let element = document.getElementById("chart-column");
    element.classList.toggle("mdl-cell--4-col");
    element.classList.toggle("mdl-cell--6-col");
    // let style = getComputedStyle(element);
    // let width = style.getPropertyValue("width");
    element = document.getElementById("money-options");
    element.classList.toggle("mdl-cell--4-col");
    element.classList.toggle("mdl-cell--3-col");
    element = document.getElementById("simulation-options");
    element.classList.toggle("mdl-cell--4-col");
    element.classList.toggle("mdl-cell--2-col");
  } else if (event.code === "Space") {
    //spacebar
    clickFabButton();
  }
});
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
  document.getElementById("text-status-reserved-wage").innerHTML =
    eventData.get("reserved_wage") * minutesPerHour;
  document.getElementById("text-status-platform-commission").innerHTML =
    eventData.get("platform_commission") * 100;
  if (eventData.has("values")) {
    document.getElementById("text-status-driver-income").innerHTML = Math.round(
      eventData.get("price") *
        (1.0 - eventData.get("platform_commission")) *
        eventData.get("values")[2] *
        minutesPerHour
    );
    document.getElementById("text-status-wait-time").innerHTML =
      Math.round(10 * eventData.get("values")[3]) / 10;
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
    simSettings.frameIndex = event.data.get("block");
    document.getElementById("frame-count").innerHTML = simSettings.frameIndex;
    if (event.data.has("vehicles")) {
      plotMap(event.data);
    } else if (event.data.has("values")) {
      plotStats(event.data, "bar");
      plotDriverStats(event.data);
    }
    updateTextStatus(event.data);
  } else if (event.data.size == 1) {
    if (event.data.get("text") == "Pyodide loaded") {
      handlePyodideready();
    } else {
      // probably an error simSettings
      console.log("Error in main: event.data=", event.data);
    }
  }
};
