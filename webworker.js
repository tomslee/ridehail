// JavaScript webworker.js
// from https://pyodide.org/en/stable/usage/webworker.html

// Setup your project to serve `webworker.js`. You should also serve
// `pyodide.js`, and all its associated `.asm.js`, `.data`, `.json`,
// and `.wasm` files as well:
importScripts("./pyodide/pyodide.js");
var citySize = 4;
var vehicleCount = 1;
var frameIndex = 0;
const colors = new Map();
var mapFrameCount = 20;
var mapTimeout = 1000;
var statsFrameCount = 100;
var statsTimeout = 100;
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
      micropip.install('./dist/ridehail-0.0.1-py3-none-any.whl')
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
    self.postMessage([frameIndex, [results[0].get("Trip wait fraction")]]);
    frameIndex += 1;
    if (frameIndex < statsFrameCount){
      setTimeout(runStatsSimulationStep, statsTimeout);
    };
  } catch (error) {
    console.log("Error in runSimulationStep: ", error.message);
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
    frameIndex = 0;
    if (event.data == ChartType.map){
      workerPackage.setup_map_simulation(citySize, vehicleCount);
      runMapSimulationStep();
    } else if (event.data == ChartType.stats){
      workerPackage.setup_stats_simulation(citySize, vehicleCount);
      runStatsSimulationStep();
    } else {
      console.log("unknown chart type ", event.data);
    }
  } catch (error) {
    self.postMessage({ error: error.message});
  }
};

