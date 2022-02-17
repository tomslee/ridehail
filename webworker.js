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
const timeOut = 1000;
var frameCount = 20;
colors.set("WITH_RIDER", "rgba(60, 179, 113, 0.4)");
colors.set("DISPATCHED", "rgba(255, 165, 0, 0.4)");
colors.set("IDLE", "rgba(0, 0, 255, 0.4)");

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


function runSimulationStep() {
  try {
    let results = workerPackage.next_frame().toJs();
    vehicleLocations = [];
    vehicleColors = [];
    results.forEach((vehicle, index) => {
      vehicleColors.push(colors.get(vehicle[0]));
      vehicleLocations.push({x: vehicle[1][0], y: vehicle[1][1]});
    });
    self.postMessage([frameIndex, vehicleColors, vehicleLocations]);
    frameIndex = frameIndex + 1;
    if (frameIndex < frameCount){
      setTimeout(function(){runSimulationStep()}, 500);
    };
    //    blockResults.destroy();
  } catch (error) {
    console.log("Error in runSimulationStep: ", error.message);
    self.postMessage({ error: error.message });
  }
}

self.onmessage = async (event) => {
  // make sure loading is done
  try {
    await pyodideReadyPromise;
    workerPackage.setup_simulation(citySize, vehicleCount);
    // runSimulation();
    frameIndex = 0;
    runSimulationStep(null);
  } catch (error) {
    self.postMessage({ error: error.message});
  }
};

