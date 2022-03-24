/* global pyodide, loadPyodide */
/*
 * JavaScript webworker.js
 * from https://pyodide.org/en/stable/usage/webworker.html
 *
 * Setup your project to serve `webworker.js`. You should also serve
 * `pyodide.js`, and all its associated `.asm.js`, `.data`, `.json`,
 * and `.wasm` files as well:
 *
 * Unfortunately I cannot get this to work as a module, which creates
 * problems for sharing definitions with other parts of the application.
 * So I reproduce some enums etc here, which is horrible.
 */

/**
 * @enum
 * TODO: This is duplicate from main.js. When I can use this file as a module,
 * import it
 * possible simulation actions and sim_states, for the fabButton
 */
var SimulationActions = {
  Play: "play_arrow",
  Pause: "pause",
  Reset: "reset",
  SingleStep: "single-step",
  Update: "update",
  UpdateDisplay: "updateDisplay",
};

/**
 * @enum
 * Different chart types that are active in the UI
 */
var ChartType = {
  Map: "map",
  Stats: "stats",
};

// Set one of these to load locally or from the CDN
var indexURL = "https://cdn.jsdelivr.net/pyodide/v0.19.0/full/";
var ridehailLocation = "./dist/";
if (location.hostname === "localhost" || location.hostname === "127.0.0.1") {
  indexURL = "./pyodide/";
}
importScripts(`${indexURL}pyodide.js`);
var workerPackage;

async function loadPyodideAndPackages() {
  self.pyodide = await loadPyodide({
    indexURL: indexURL,
  });
  await self.pyodide.loadPackage(["numpy", "micropip"]);
  await pyodide.runPythonAsync(`
      import micropip
      micropip.install('${ridehailLocation}ridehail-0.0.1-py3-none-any.whl')
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
    let pyResults = workerPackage.sim.next_frame_stats();
    let results = pyResults.toJs();
    pyResults.destroy();
    results.set("frameTimeout", simSettings.frameTimeout);
    self.postMessage(results);
    if (
      (results.get("block") < simSettings.timeBlocks &&
        simSettings.action == SimulationActions.Play) ||
      (simSettings.timeBlocks == 0 &&
        simSettings.action == SimulationActions.Play) ||
      (results.get("block") == 0 &&
        simSettings.action == SimulationActions.SingleStep)
    ) {
      // special case: do one extra step on first single-step action to avoid
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
    let pyResults = workerPackage.sim.next_frame_map();
    let results = pyResults.toJs();
    results.set("frameTimeout", simSettings.frameTimeout);
    pyResults.destroy();
    // console.log("ww: trips=", results.get("trips"));
    self.postMessage(results);
    if (
      (results.get("block") < 2 * simSettings.timeBlocks &&
        simSettings.action == SimulationActions.Play) ||
      (simSettings.timeBlocks == 0 &&
        simSettings.action == SimulationActions.Play) ||
      (results.get("block") == 0 &&
        simSettings.action == SimulationActions.SingleStep)
    ) {
      // special case: do one extra step on first single-step action to avoid
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
      simSettings.action == SimulationActions.Play ||
      simSettings.action == SimulationActions.SingleStep
    ) {
      if (simSettings.frameIndex == 0) {
        // initialize only if it is a new simulation (frameIndex 0)
        workerPackage.init_simulation(simSettings);
      }
      if (simSettings.chartType == ChartType.Map) {
        runMapSimulationStep(simSettings);
      } else if (simSettings.chartType == ChartType.Stats) {
        runStatsSimulationStep(simSettings);
      } else {
        console.log("Error: unknown chart type - ", event.data);
      }
    } else if (simSettings.action == SimulationActions.Pause) {
      // We don't know the actual timeout, but they are incrementing integers.
      // Set a new one to get the max value and then clear them all,
      // as in https://stackoverflow.com/questions/8860188/javascript-clear-all-timeouts
      let id = setTimeout(function () {}, 0);
      while (id--) {
        clearTimeout(id); // will do nothing if no timeout with id is present
      }
    } else if (simSettings.action == SimulationActions.Update) {
      updateSimulation(simSettings);
    } else if (simSettings.action == SimulationActions.UpdateDisplay) {
      let id = setTimeout(function () {}, 0);
      while (id--) {
        await clearTimeout(id); // will do nothing if no timeout with id is present
      }
      simSettings.action = SimulationActions.Play;
      if (simSettings.chartType == ChartType.Map) {
        runMapSimulationStep(simSettings);
      } else if (simSettings.chartType == ChartType.Stats) {
        runStatsSimulationStep(simSettings);
      }
    } else if (simSettings.action == SimulationActions.Reset) {
      resetSimulation(simSettings);
    }
  } catch (error) {
    self.postMessage({ error: error.message });
  }
};
