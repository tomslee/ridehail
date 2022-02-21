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
var chartType = null;


const ChartType = {
  map: "map",
  stats: "stats"
};

//window.addEventListener('DOMContentLoaded', (event) => {
//});

fabButton.onclick = function(){
  let config = {
    chart_type: configChartType.innerHTML,
    city_size: configCitySize.innerHTML,
    vehicle_count: configVehicleCount.innerHTML,
    request_rate: configRequestRate.innerHTML,
  }
  chartType = ChartType.stats;
  initStatsChart();
  w.postMessage(config);
}

var currentValue = "stats";

statsRadio.onclick = function(){
  configChartType.innerHTML = this.value;
}
mapRadio.onclick = function(){
  configChartType.innerHTML = this.value;
}

if (typeof(w) == "undefined") {
  // var w = new Worker("webworker.js", {type: 'module'});
  var w = new Worker("webworker.js");
}

export const ctx = canvas.getContext('2d');
export function disableSpinner(){
  spinner.classList.remove("is-active");
};

// Listen to the web worker
w.onmessage = function(event){
  // lineChart.data.datasets[0].data.push({x: event.data[0], y: event.data[1].get("vehicle_fraction_idle")});
  // data comes in from a self.postMessage([blockIndex, vehicleColors, vehicleLocations]);
  console.log("main: event.data=", event.data);
  if (event.data != null){
    if(chartType == ChartType.map){
      plotMap(event.data);
    } else if (chartType == ChartType.stats){
      plotStats(event.data);
    }
  }
};
