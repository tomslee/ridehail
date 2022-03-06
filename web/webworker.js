/* global pyodide, loadPyodide */
/*
 * JavaScript webworker.js
 * from https://pyodide.org/en/stable/usage/webworker.html
 *
 * Setup your project to serve `webworker.js`. You should also serve
 * `pyodide.js`, and all its associated `.asm.js`, `.data`, `.json`,
 * and `.wasm` files as well:
 */

// Set one of these to load locally or from the CDN
const indexURL = "./pyodide/";
// const indexURL = "https://cdn.jsdelivr.net/pyodide/v0.19.0/full/";
importScripts(`${indexURL}pyodide.js`);
var workerPackage;

async function loadPyodideAndPackages() {
  self.pyodide = await loadPyodide({
    indexURL: indexURL,
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

/*
function runSimulation() {
  try {
    vehicleCount = vehicleCount + 1;
    let results = workerPackage.simulate(vehicleCount).toJs();
    self.postMessage([vehicleCount, results]);
    setTimeout("runSimulation()", 100);
  } catch (error) {
    self.postMessage({ error: error.message });
  }
}
  */

function runStatsSimulationStep(simSettings) {
  try {
    let pyResults = workerPackage.sim.next_frame_stats(simSettings);
    let results = pyResults.toJs();
    pyResults.destroy();
    self.postMessage(results);
    if (
      (results.get("block") < simSettings.timeBlocks &&
        simSettings.action == "play_arrow") ||
      (results.get("block") == 0 && simSettings.action == "single-step")
    ) {
      // special case: do one step on first single-step action to avoid
      // resetting each time
      setTimeout(runStatsSimulationStep, simSettings.frameTimeout, simSettings);
    }
  } catch (error) {
    console.log("Error in runStatsSimulationStep: ", error.message);
    self.postMessage({ error: error.message });
  }
}

function runMapSimulationStep(simSettings) {
  try {
    let pyResults = workerPackage.sim.next_frame_map(simSettings);
    let results = pyResults.toJs();
    pyResults.destroy();
    // console.log("ww: trips=", results.get("trips"));
    self.postMessage(results);
    if (
      (results.get("block") < 2 * simSettings.timeBlocks &&
        simSettings.action == "play_arrow") ||
      (results.get("block") == 0 && simSettings.action == "single-step")
    ) {
      // special case: do one step on first single-step action to avoid
      // resetting each time
      setTimeout(runMapSimulationStep, simSettings.frameTimeout, simSettings);
    }
  } catch (error) {
    console.log("Error in runSimulationStep: ", error.message);
    self.postMessage({ error: error.message });
  }
}

function resetSimulation(simSettings) {
  // clear all the timeouts
  let id = setTimeout(function () {}, 0);
  while (id--) {
    clearTimeout(id); // will do nothing if no timeout with id is present
  }
  workerPackage.init_simulation(simSettings);
}

function updateSimulation(simSettings) {
  workerPackage.sim.update_options(simSettings);
}

async function handlePyodideReady() {
  await pyodideReadyPromise;
  let message = new Map();
  message.set("text", "Pyodide loaded");
  self.postMessage(message);
}
handlePyodideReady();

// await pyodideReadyPromise;
// self.onmessage = async (event) => {
self.onmessage = async (event) => {
  // make sure loading is done
  try {
    await pyodideReadyPromise;
    let simSettings = event.data;
    if (
      (Object.prototype.hasOwnProperty.call(simSettings, "action") &&
        simSettings.action == "play_arrow") ||
      simSettings.action == "single-step"
    ) {
      if (simSettings.chartType == "map") {
        if (simSettings.frameIndex == 0) {
          // initialize only if it is a new simulation (frameIndex 0)
          workerPackage.init_simulation(simSettings);
        }
        runMapSimulationStep(simSettings);
      } else if (simSettings.chartType == "stats") {
        if (simSettings.frameIndex == 0) {
          // initialize only if it is a new simulation (frameIndex 0)
          workerPackage.init_simulation(simSettings);
        }
        runStatsSimulationStep(simSettings);
      } else {
        console.log("Error: unknown chart type - ", event.data);
      }
    } else if (simSettings.action == "pause") {
      // We don't know the actual timeout, but they are incrementing integers.
      // Set a new one to get the max value and then clear them all,
      // as in https://stackoverflow.com/questions/8860188/javascript-clear-all-timeouts
      let id = setTimeout(function () {}, 0);
      while (id--) {
        clearTimeout(id); // will do nothing if no timeout with id is present
      }
    } else if (simSettings.action == "updateSim") {
      updateSimulation(simSettings);
    } else if (simSettings.action == "updateDisplay") {
      let id = setTimeout(function () {}, 0);
      while (id--) {
        await clearTimeout(id); // will do nothing if no timeout with id is present
      }
      simSettings.action = "play_arrow";
      if (simSettings.chartType == "map") {
        runMapSimulationStep(simSettings);
      } else if (simSettings.chartType == "stats") {
        runStatsSimulationStep(simSettings);
      }
    } else if (simSettings.action == "reset") {
      resetSimulation(simSettings);
    }
  } catch (error) {
    self.postMessage({ error: error.message });
  }
};
