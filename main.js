import {initMapChart, plotMap} from "./modules/map.js";
import {initStatsChart, plotStats} from "./modules/stats.js";
var citySize = 4;
const maxVehicleCount = 30;
var labels = [];
const offset = 0.0;
var chartType = null;

function setData(offset, x, y){
  let data = [];
  for (var i = 0; i < x.length; i++) {
    data.push({x: x[i], y: y[i]});
  };
  return data;
}

const ChartType = {
  map: "map",
  stats: "stats"
};

const mapButton = document.getElementById("mapButton");
mapButton.onclick = function(){
  chartType = ChartType.map;
  initMapChart();
  w.postMessage(chartType);
  console.log("map message posted");
};
const statsButton = document.getElementById("statsButton");
statsButton.onclick = function(){
  // if (window.chart instanceof Chart) {
      // window.chart.destroy();
  // };
  chartType = ChartType.stats;
  initStatsChart();
  w.postMessage(chartType);
  console.log("stats message posted");
}

if (typeof(w) == "undefined") {
  var w = new Worker("webworker.js");
}

// Listen to the web worker
w.onmessage = function(event){
  // console.log("In main.js, event.data=" + event.data);
  // lineChart.data.datasets[0].data.push({x: event.data[0], y: event.data[1].get("vehicle_fraction_idle")});
  // data comes in from a self.postMessage([blockIndex, vehicleColors, vehicleLocations]);
  if (event.data != null){
    if(chartType == ChartType.map){
      console.log("m: ", event.data)
      plotMap(event.data);
    } else if (chartType == ChartType.stats){
      console.log("m: ", event.data)
      plotStats(event.data);
    }
  }
};
