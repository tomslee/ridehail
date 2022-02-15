// JavaScript webworker.js
// from https://pyodide.org/en/stable/usage/webworker.html

// Setup your project to serve `webworker.js`. You should also serve
// `pyodide.js`, and all its associated `.asm.js`, `.data`, `.json`,
// and `.wasm` files as well:
importScripts("./pyodide/pyodide.js");
var workerPackage;
var vehicleCount = 0;
var citySize = 8;
var blockIndex = 0;
const colors = new Map();
colors.set("WITH_RIDER", "rgba(60, 179, 113, 0.4)");
colors.set("DISPATCHED", "rgba(255, 165, 0, 0.4)");
colors.set("IDLE", "rgba(0, 0, 255, 0.4)");

async function loadPyodideAndPackages() {
  self.pyodide = await loadPyodide({
    // indexURL: "https://cdn.jsdelivr.net/pyodide/v0.19.0/full/",
    indexURL: "./pyodide/",
  });
  await self.pyodide.loadPackage(["numpy", "micropip"]);
  // await pyodide.runPythonAsync(`
      // from pyodide.http import pyfetch
      // response = await pyfetch("./dist/ridehail.tar.gz")
      // await response.unpack_archive()
   // `);
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


function runSimulationStep(previousLocations) {
  try {
    let blockResults = workerPackage.next_block(blockIndex).toJs();
    let vehicleLocations = [];
    let vehicleColors = [];
    if (previousLocations != null){
      blockResults.forEach((vehicle, index) => {
        vehicleColors.push(colors.get(vehicle[0]));
        vehicleLocations.push({x: (0.5 * (vehicle[1][0] + previousLocations[index][0])) % citySize,
          y: (0.5 * (vehicle[1][1] + previousLocations[index][1])) % citySize});
      });
      self.postMessage([blockIndex, vehicleColors, vehicleLocations]);
      setTimeout(function(){
      //sleep
      }, 500);
    };
    vehicleLocations = [];
    vehicleColors = [];
    blockResults.forEach((vehicle, index) => {
      vehicleColors.push(colors.get(vehicle[0]));
      vehicleLocations.push({x: vehicle[1][0], y: vehicle[1][1]});
    });
    self.postMessage([blockIndex, vehicleColors, vehicleLocations]);
    blockIndex = blockIndex + 1;
    setTimeout(function(){runSimulationStep(vehicleLocations)}, 500);
  } catch (error) {
    self.postMessage({ error: error.message });
  }
}

self.onmessage = async (event) => {
  // make sure loading is done
  try {
    await pyodideReadyPromise;
    vehicleCount = 8;
    citySize = 8;
    workerPackage.setup_simulation(citySize, vehicleCount);
    // runSimulation();
    runSimulationStep(null)
  } catch (error) {
    self.postMessage({ error: error.message});
  }
};

