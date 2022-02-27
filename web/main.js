/* global Chart */
export const colors = new Map([
  // Vehicles
  ["IDLE", "rgba(100, 149, 237, 0.7)"],
  ["DISPATCHED", "rgba(215, 142, 0, 0.7)"],
  ["WITH_RIDER", "rgba(60, 179, 113, 0.7)"],
  // Trips
  ["UNASSIGNED", "rgba(237, 100, 149, 0.7)"],
  ["WAITING", "rgba(237, 100, 149, 0.7)"],
  ["RIDING", "rgba(237, 100, 149, 0.7)"],
]);
import { initStatsChart, plotStats } from "./modules/stats.js";
import { initMap, plotMap } from "./modules/map.js";
const inputCitySize = document.getElementById("input-city-size");
const optionCitySize = document.getElementById("option-city-size");
const inputVehicleCount = document.getElementById("input-vehicle-count");
const optionVehicleCount = document.getElementById("option-vehicle-count");
const inputRequestRate = document.getElementById("input-request-rate");
const optionRequestRate = document.getElementById("option-request-rate");
const optionChartType = document.getElementById("option-chart-type");
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
const mapRadio = document.getElementById("option-map");
const statsRadio = document.getElementById("option-stats");
const canvas = document.getElementById("pg-chart-canvas");
const storyTimeButton1 = document.getElementById("st1-button");
const storyTimeButton2 = document.getElementById("st2-button");
const stCanvas1 = document.getElementById("st1-chart-canvas");
const stCanvas2 = document.getElementById("st2-chart-canvas");
var ctx = canvas.getContext("2d");
export var message = {
  frameIndex: 0,
  action: fabButton.firstElementChild.innerHTML,
  chartType: optionChartType.innerHTML,
  citySize: optionCitySize.innerHTML,
  vehicleCount: optionVehicleCount.innerHTML,
  requestRate: optionRequestRate.innerHTML,
  frameTimeout: optionFrameTimeout.innerHTML,
  smoothingWindow: optionSmoothingWindow.innerHTML,
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
  message.citySize = 4;
  message.requestRate = 0;
  message.vehicleCount = 1;
  message.frameTimeout = 300;
  message.timeBlocks = 20;
  ctx = stCanvas1.getContext("2d");
  message.chartType = "Map";
  await resetUIAndSimulation(ctx);
  message.action = "play_arrow";
  message.frameIndex = 0;
  w.postMessage(message);
};

storyTimeButton2.onclick = async function () {
  // Reset to defaults
  // Override where necessary
  message.citySize = 4;
  message.requestRate = 0.1;
  message.vehicleCount = 1;
  message.frameTimeout = 300;
  message.timeBlocks = 50;
  ctx = stCanvas2.getContext("2d");
  message.chartType = "Map";
  await resetUIAndSimulation(ctx);
  message.action = "play_arrow";
  message.frameIndex = 0;
  w.postMessage(message);
};

/*
 * Top-level controls (reset, play/pause, next step)
 */

async function resetUIAndSimulation(ctx) {
  fabButton.removeAttribute("disabled");
  fabButton.firstElementChild.innerHTML = "play_arrow";
  nextStepButton.removeAttribute("disabled");
  message.frameIndex = 0;
  message.action = "reset";
  document.getElementById("frame-count").innerHTML = message.frameIndex;
  // Destroy any charts
  if (window.chart instanceof Chart) {
    window.chart.destroy();
  }
  if (message.chartType == "Stats") {
    initStatsChart(ctx);
  } else if (message.chartType == "Map") {
    initMap(ctx);
  }
  w.postMessage(message);
}

resetButton.onclick = function () {
  ctx = canvas.getContext("2d");
  resetUIAndSimulation(ctx);
};

function toggleFabButton() {
  if (fabButton.firstElementChild.innerHTML == "play_arrow") {
    fabButton.firstElementChild.innerHTML = "pause";
    nextStepButton.setAttribute("disabled", "");
  } else {
    resetButton.removeAttribute("disabled");
    nextStepButton.removeAttribute("disabled");
    fabButton.firstElementChild.innerHTML = "play_arrow";
  }
}

fabButton.onclick = function () {
  message.action = fabButton.firstElementChild.innerHTML;
  message.frameIndex = document.getElementById("frame-count").innerHTML;
  message.chartType = optionChartType.innerHTML;
  message.citySize = optionCitySize.innerHTML;
  message.vehicleCount = optionVehicleCount.innerHTML;
  message.requestRate = optionRequestRate.innerHTML;
  message.timeBlocks = 1000;
  toggleFabButton();
  w.postMessage(message);
};

nextStepButton.onclick = function () {
  message.action = "single-step";
  w.postMessage(message);
};
/*
 * Simulation options
 */

inputCitySize.onchange = function () {
  optionCitySize.innerHTML = this.value;
  message.citySize = this.value;
  ctx = canvas.getContext("2d");
  resetUIAndSimulation(ctx);
};
inputVehicleCount.onchange = function () {
  optionVehicleCount.innerHTML = this.value;
  message.vehicleCount = this.value;
  ctx = canvas.getContext("2d");
  resetUIAndSimulation(ctx);
};
inputRequestRate.onchange = function () {
  optionRequestRate.innerHTML = this.value;
  message.requestRate = this.value;
  ctx = canvas.getContext("2d");
  resetUIAndSimulation(ctx);
};
inputFrameTimeout.onchange = function () {
  optionFrameTimeout.innerHTML = this.value;
  message.frameTimeout = this.value;
  ctx = canvas.getContext("2d");
  resetUIAndSimulation(ctx);
};
inputSmoothingWindow.onchange = function () {
  optionSmoothingWindow.innerHTML = this.value;
  message.smoothingWindow = this.value;
  ctx = canvas.getContext("2d");
  resetUIAndSimulation(ctx);
};

/*
 * Display options
 */

statsRadio.onclick = function () {
  optionChartType.innerHTML = this.value;
  message.chartType = this.value;
  ctx = canvas.getContext("2d");
  resetUIAndSimulation(ctx);
};
mapRadio.onclick = function () {
  optionChartType.innerHTML = this.value;
  message.chartType = this.value;
  ctx = canvas.getContext("2d");
  resetUIAndSimulation(ctx);
};

/*
 * Capture keypress events
 */

document.addEventListener("keyup", function (event) {
  if (event.key === "f" || event.key === "F") {
    let element = document.getElementById("pg-canvas-parent");
    element.classList.toggle("mdl-cell--4-col");
    element.classList.toggle("mdl-cell--8-col");
    element = document.getElementById("display-options");
    element.classList.toggle("mdl-cell--4-col");
    element.classList.toggle("mdl-cell--2-col");
    element = document.getElementById("simulation-options");
    element.classList.toggle("mdl-cell--4-col");
    element.classList.toggle("mdl-cell--2-col");
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
  spinner.classList.remove("is-active");
  resetButton.removeAttribute("disabled");
  fabButton.removeAttribute("disabled");
  nextStepButton.removeAttribute("disabled");
  ctx = canvas.getContext("2d");
  resetUIAndSimulation(ctx);
}

// Listen to the web worker
w.onmessage = function (event) {
  // lineChart.data.datasets[0].data.push({x: event.data[0], y: event.data[1].get("vehicle_fraction_idle")});
  // data comes in from a self.postMessage([blockIndex, vehicleColors, vehicleLocations]);
  if (event.data.size > 1) {
    message.frameIndex = event.data.get("block");
    document.getElementById("frame-count").innerHTML = message.frameIndex;
    if (event.data.has("vehicles")) {
      plotMap(event.data);
    } else if (event.data.has("values")) {
      plotStats(event.data);
    }
  } else if (event.data.size == 1) {
    if (event.data.get("text") == "Pyodide loaded") {
      handlePyodideready();
    } else {
      // probably an error message
      console.log("Error in main: event.data=", event.data);
    }
  }
};
