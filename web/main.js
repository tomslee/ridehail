import {initStatsChart, plotStats} from "./modules/stats.js";
import {initMapChart, plotMap} from "./modules/map.js";
const configVehicleCount = document.getElementById("config-vehicle-count");
const configRequestRate = document.getElementById("config-request-rate");
const configChartType = document.getElementById("config-chart-type");
const spinner = document.getElementById("spinner");
const configCitySize = document.getElementById("config-city-size");
const fabButton = document.getElementById("fabButton");
const mapRadio = document.getElementById("option-map");
const statsRadio = document.getElementById("option-stats");
const canvas = document.getElementById('chartcanvas');
var citySize = 4;
const maxVehicleCount = 30;
var labels = [];
const offset = 0.0;
var config = {
  frame_index: 0,
  action: fabButton.firstElementChild.innerHTML,
  chart_type: configChartType.innerHTML,
  city_size: configCitySize.innerHTML,
  vehicle_count: configVehicleCount.innerHTML,
  request_rate: configRequestRate.innerHTML,
};

const ChartType = {
  map: "map",
  stats: "stats"
};
var chartType = ChartType.stats;

/*
 * UI actions
*/

fabButton.onclick = function(){
  config.action = fabButton.firstElementChild.innerHTML
  config.frame_index = 0
  config.action = fabButton.firstElementChild.innerHTML
  config.chart_type = configChartType.innerHTML
  config.city_size = configCitySize.innerHTML
  config.vehicle_count = configVehicleCount.innerHTML
  config.request_rate = configRequestRate.innerHTML
  w.postMessage(config);
  if (fabButton.firstElementChild.innerHTML == "play_arrow"){
    // pressed to pause
    fabButton.firstElementChild.innerHTML = "pause";
  } else {
    // pressed to start
    initStatsChart();
    fabButton.firstElementChild.innerHTML = "play_arrow";
  };
}

var currentValue = "stats";

statsRadio.onclick = function(){
  configChartType.innerHTML = this.value;
  initStatsChart();
}
mapRadio.onclick = function(){
  configChartType.innerHTML = this.value;
  initMapChart();
}

if (typeof(w) == "undefined") {
  // var w = new Worker("webworker.js", {type: 'module'});
  var w = new Worker("webworker.js");
}

export const ctx = canvas.getContext('2d');
export function disableSpinner(){
  spinner.classList.remove("is-active");
};
initStatsChart();

// Listen to the web worker
w.onmessage = function(event){
  // lineChart.data.datasets[0].data.push({x: event.data[0], y: event.data[1].get("vehicle_fraction_idle")});
  // data comes in from a self.postMessage([blockIndex, vehicleColors, vehicleLocations]);
  if (event.data != null){
    console.log("main: frame=", event.data[0], ", event.data=", event.data);
    document.getElementById("block-count").innerHTML=event.data[0];
    if(chartType == ChartType.map){
      plotMap(event.data);
    } else if (chartType == ChartType.stats){
      plotStats(event.data);
    }
  }
};
