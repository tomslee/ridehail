import {initStatsChart, plotStats} from "./modules/stats.js";
import {initMapChart, plotMap} from "./modules/map.js";
const inputCitySize = document.getElementById("input-city-size");
const optionCitySize = document.getElementById("option-city-size");
const inputVehicleCount = document.getElementById("input-vehicle-count");
const optionVehicleCount = document.getElementById("option-vehicle-count");
const inputRequestRate = document.getElementById("input-request-rate");
const optionRequestRate = document.getElementById("option-request-rate");
const optionChartType = document.getElementById("option-chart-type");
const spinner = document.getElementById("spinner");
const resetButton = document.getElementById("reset-button");
const fabButton = document.getElementById("fab-button");
const nextStepButton = document.getElementById("next-step-button");
const mapRadio = document.getElementById("option-map");
const statsRadio = document.getElementById("option-stats");
const canvas = document.getElementById('chartcanvas');
const maxVehicleCount = 30;
var labels = [];
const offset = 0.0;
export var message = {
  frameIndex: 0,
  action: fabButton.firstElementChild.innerHTML,
  chartType: optionChartType.innerHTML,
  citySize: optionCitySize.innerHTML,
  vehicleCount: optionVehicleCount.innerHTML,
  requestRate: optionRequestRate.innerHTML,
  smoothingWindow: 5,
};

const ChartType = {
  map: "map",
  stats: "stats"
};
var chartType = ChartType.stats;

/*
 * UI actions
*/

/*
 * Top-level controls (reset, play/pause, next step)
 */

function resetUIAndSimulation(){
  fabButton.removeAttribute("disabled");
  fabButton.firstElementChild.innerHTML = "play_arrow";
  nextStepButton.removeAttribute("disabled");
  message.frameIndex = 0;
  message.action = "reset";
  document.getElementById("block-count").innerHTML=message.frameIndex;
  // Destroy any charts
  if (window.chart instanceof Chart) {
      window.chart.destroy();
  };
  if (message.chartType == "Stats") {
    initStatsChart();
  } else if (message.chartType == "Map") {
    initMapChart();
  }
  w.postMessage(message);
};

resetButton.onclick = function(){
  resetUIAndSimulation();
};

function toggleFabButton(){
  if (fabButton.firstElementChild.innerHTML == "play_arrow"){
    fabButton.firstElementChild.innerHTML = "pause";
    nextStepButton.setAttribute("disabled", '');
  } else {
    resetButton.removeAttribute("disabled");
    nextStepButton.removeAttribute("disabled");
    fabButton.firstElementChild.innerHTML = "play_arrow";
  }
};

fabButton.onclick = function(){
  message.action = fabButton.firstElementChild.innerHTML
  message.frameIndex = document.getElementById("block-count").innerHTML;
  message.chartType = optionChartType.innerHTML
  message.citySize = optionCitySize.innerHTML
  message.vehicleCount = optionVehicleCount.innerHTML
  message.requestRate = optionRequestRate.innerHTML
  message.timeBlocks = 1000;
  toggleFabButton();
  w.postMessage(message);
}

nextStepButton.onclick = function(){
  message.action = "single-step";
  w.postMessage(message);
};
/*
 * Simulation options
 */

inputCitySize.onchange = function(){
  optionCitySize.innerHTML = this.value;
  message.citySize = this.value
  resetUIAndSimulation();
};
inputVehicleCount.onchange = function(){
  optionVehicleCount.innerHTML = this.value;
  message.vehicleCount = this.value
  resetUIAndSimulation();
};
inputRequestRate.onchange = function(){
  optionRequestRate.innerHTML = this.value;
  message.RequestRate = this.value;
  resetUIAndSimulation();
};


/*
 * Display options
 */

statsRadio.onclick = function(){
  optionChartType.innerHTML = this.value;
  message.chartType = this.value;
  resetUIAndSimulation();
}
mapRadio.onclick = function(){
  optionChartType.innerHTML = this.value;
  message.chartType = this.value;
  resetUIAndSimulation();
}

if (typeof(w) == "undefined") {
  // var w = new Worker("webworker.js", {type: 'module'});
  var w = new Worker("webworker.js");
}

export const ctx = canvas.getContext('2d');
function handlePyodideready(){
  spinner.classList.remove("is-active");
  resetButton.removeAttribute("disabled");
  fabButton.removeAttribute("disabled");
  nextStepButton.removeAttribute("disabled");
  resetUIAndSimulation();
};

// Listen to the web worker
w.onmessage = function(event){
  // lineChart.data.datasets[0].data.push({x: event.data[0], y: event.data[1].get("vehicle_fraction_idle")});
  // data comes in from a self.postMessage([blockIndex, vehicleColors, vehicleLocations]);
  console.log("main onmessage: ", event.data);
  if (event.data.size > 1){
    console.log("main: frame=", event.data.get("block"), ", event.data=", event.data);
    message.frameIndex = event.data.get("block")
    document.getElementById("block-count").innerHTML=event.data.get("block");
    if (event.data.has("vehicles")){
      plotMap(event.data);
    } else if (event.data.has("values")){
      plotStats(event.data);
    }
  } else if (event.data.size == 1) {
    if (event.data.get("text") == "Pyodide loaded"){
      console.log("Disabling spinner");
      handlePyodideready();
    } else {
      // probably an error message
      console.log("main: event.data=", event.data);
    }
  };
};
