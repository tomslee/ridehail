/*
 * JavaScript webworker.js
 * from https://pyodide.org/en/stable/usage/webworker.html
 *
 * Setup your project to serve `webworker.js`. You should also serve
 * `pyodide.js`, and all its associated `.asm.js`, `.data`, `.json`,
 * and `.wasm` files as well:
 */
importScripts("./pyodide/pyodide.js");
// import {disableSpinner} from "./main.js";
var citySize = 16;
var vehicleCount = 32;
var baseDemand = 2;
var frameIndex = 0;
const colors = new Map();
var mapFrameCount = 20;
var mapTimeout = 1000;
var statsFrameCount = 10;
var statsTimeout = 1000;
colors.set("WITH_RIDER", "rgba(60, 179, 113, 0.4)");
colors.set("DISPATCHED", "rgba(255, 165, 0, 0.4)");
colors.set("IDLE", "rgba(0, 0, 255, 0.4)");

// duplicate from main.js to get around module problems for now
const ChartType = {
  map: "map",
  stats: "stats"
};

async function loadPyodideAndPackages() {
  self.pyodide = await loadPyodide({
    // indexURL: "https://cdn.jsdelivr.net/pyodide/v0.19.0/full/",
    indexURL: "./pyodide/",
  });
  await self.pyodide.loadPackage(["numpy", "micropip"]);
  await pyodide.runPythonAsync(`
      import micropip
      micropip.install('../dist/ridehail-0.0.1-py3-none-any.whl')
  `);
  await pyodide.runPythonAsync(`
      from pyodide.http import pyfetch
      response = await pyfetch("./worker.py")
      with open("worker.py", "wb") as f:
         f.write(await response.bytes())
   `);
  workerPackage = pyodide.pyimport("worker");
}
let pyodideReadyPromise = loadPyodideAndPackages();
//disableSpinner();

function runSimulation() {
  try {
    vehicleCount = vehicleCount + 1;
    let results = workerPackage.simulate(vehicleCount).toJs();
    self.postMessage([vehicleCount, results]);
    setTimeout("runSimulation()", 100);
  } catch (error) {
    self.postMessage({ error: error.message });
  }
};

function runStatsSimulationStep() {
  try {
    let results = workerPackage.sim.next_frame();
    results = results.toJs();
    self.postMessage([frameIndex, results]);
    frameIndex += 1;
    if (frameIndex < statsFrameCount){
      setTimeout(runStatsSimulationStep, statsTimeout);
    };
  } catch (error) {
    console.log("Error in runStatsSimulationStep: ", error.message);
    self.postMessage({error: error.message});
  }
}

function runMapSimulationStep() {
  try {
    let results = workerPackage.sim.next_frame();
    results = results.toJs();
    vehicleLocations = [];
    vehicleColors = [];
    results.forEach((vehicle, index) => {
      vehicleColors.push(colors.get(vehicle[0]));
      vehicleLocations.push({x: vehicle[1][0], y: vehicle[1][1]});
    });
    console.log("ww: vehicleLocations[0]=", vehicleLocations[0]);
    self.postMessage([frameIndex, vehicleColors, vehicleLocations]);
    frameIndex += 1;
    if (frameIndex < mapFrameCount){
      setTimeout(runMapSimulationStep, mapTimeout);
    };
    //    results.destroy();
  } catch (error) {
    console.log("Error in runSimulationStep: ", error.message);
    self.postMessage({error: error.message});
  }
}

// await pyodideReadyPromise;
  // self.onmessage = async (event) => {
self.onmessage = async (event) => {
  // make sure loading is done
  try {
    await pyodideReadyPromise;
    console.log("ww onmessage: ", event.data);
    config = event.data
    frameIndex = 0;
    if (event.data.action == "play_arrow") {
      if (event.data.chart_type == "Map"){
      workerPackage.init_map_simulation(config.city_size, config.vehicle_count, config.request_rate);
        runMapSimulationStep();
      } else if (event.data.chart_type == "Stats"){
        workerPackage.init_stats_simulation(config.city_size, config.vehicle_count, config.request_rate);
        runStatsSimulationStep();
      } else {
        console.log("unknown chart type ", event.data);
      }
    } else if (event.data.action == "pause" ){
      // We don't know the actual timeout, but they are incrementing integers.
      // Set a new one to get the max value and then clear them all, 
      // as in https://stackoverflow.com/questions/8860188/javascript-clear-all-timeouts
      let id = setTimeout(function() {}, 0);
      while (id--) {
        clearTimeout(id); // will do nothing if no timeout with id is present
      }
      console.log("Cleared timeout");
    }
  } catch (error) {
    self.postMessage({ error: error.message});
  }
};

