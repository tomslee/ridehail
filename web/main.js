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
var citySize = 4;
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
  // if (fabButton.firstElementChild.innerHTML == "play_arrow"){
    // initStatsChart();
  // };
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
  resetUIAndSimulation();
};
inputVehicleCount.onchange = function(){
  optionVehicleCount.innerHTML = this.value;
  resetUIAndSimulation();
};
inputRequestRate.onchange = function(){
  optionRequestRate.innerHTML = this.value;
  resetUIAndSimulation();
};


/*
 * Display options
 */

statsRadio.onclick = function(){
  optionChartType.innerHTML = this.value;
  initStatsChart();
}
mapRadio.onclick = function(){
  optionChartType.innerHTML = this.value;
  initMapChart();
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
  initStatsChart();
};

// Listen to the web worker
w.onmessage = function(event){
  // lineChart.data.datasets[0].data.push({x: event.data[0], y: event.data[1].get("vehicle_fraction_idle")});
  // data comes in from a self.postMessage([blockIndex, vehicleColors, vehicleLocations]);
  if (event.data.length > 1){
    console.log("main: frame=", event.data[0], ", event.data=", event.data);
    message.frameIndex = event.data[0]
    document.getElementById("block-count").innerHTML=event.data[0];
    if(chartType == ChartType.map){
      plotMap(event.data);
    } else if (chartType == ChartType.stats){
      plotStats(event.data);
    }
  } else if (event.data.length == 1) {
    if (event.data[0] == "Pyodide loaded"){
      console.log("Disabling spinner");
      handlePyodideready();
    } else {
      // probably an error message
      console.log("main: event.data=", event.data);
    }
  };
};
