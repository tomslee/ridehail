/**
 * ES Module Web Worker for Pyodide ridehail simulation
 *
 * This worker loads Pyodide and runs Python simulation code,
 * communicating results back to the main thread via postMessage.
 */

import { CHART_TYPES, SimulationActions } from "./js/constants.js";

// Set one of these to load locally or from the CDN
var indexURL = "https://cdn.jsdelivr.net/pyodide/v0.28.2/full/";
const ridehailLocation = "./dist/";
if (
  location.hostname === "localhost" ||
  location.hostname === "127.0.0.1" 
) {
  indexURL = "./pyodide/";
}
console.log("webworker.js: importing pyodide from", indexURL);

var workerPackage;

/*
 * Load Pyodide script dynamically for ES module workers
 * Since Pyodide doesn't provide ES modules, we fetch and evaluate it
 */
async function loadPyodideScript() {
  try {
    const response = await fetch(`${indexURL}pyodide.js`);
    const scriptText = await response.text();

    // Evaluate the script in the worker's global scope
    eval(scriptText);

    if (typeof self.loadPyodide === 'function') {
      return self.loadPyodide;
    } else {
      throw new Error('loadPyodide not found after script evaluation');
    }
  } catch (error) {
    console.error('Failed to load Pyodide script:', error);
    throw error;
  }
}

/*
 * From pyodide v 0.28.0,  JavaScript null is no longer converted to
 * None by default, so that "undefined" can be distinguished from "null".
 * In the short term, I've added the convertNullToNone argument
 * to preserve the old behaviour.
 */
async function loadPyodideAndPackages() {
  const loadPyodide = await loadPyodideScript();

  self.pyodide = await loadPyodide({
    indexURL: indexURL,
    convertNullToNone: true,
  });
  await self.pyodide.loadPackage(["numpy", "micropip"]);
  await pyodide.runPythonAsync(`
      import micropip
      micropip.install('${ridehailLocation}ridehail-0.1.0-py3-none-any.whl')
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

function convertVehiclesToArrays(vehicles) {
  if (!Array.isArray(vehicles) || vehicles.length === 0) {
    return vehicles;
  }

  const firstVehicle = vehicles[0];

  // Check if vehicles are in object format with expected properties
  if (
    typeof firstVehicle === "object" &&
    firstVehicle !== null &&
    "phase" in firstVehicle &&
    "location" in firstVehicle &&
    "direction" in firstVehicle
  ) {
    // Convert objects to arrays [phase, location, direction]
    return vehicles.map((vehicle) => [
      vehicle.phase,
      vehicle.location,
      vehicle.direction,
    ]);
  }

  // If already in array format or unknown format, return as-is
  return vehicles;
}

function convertPyodideToJS(obj) {
  // Claude-generated recursive function to make Pyodide objects available for posting
  // Handle Pyodide objects
  if (obj && typeof obj.toJs === "function") {
    obj = obj.toJs();
  }

  // Handle Maps
  if (obj instanceof Map) {
    const converted = {};
    for (const [key, value] of obj) {
      // Special handling for vehicles key
      if (key === "vehicles" && Array.isArray(value)) {
        converted[key] = convertVehiclesToArrays(value);
      } else {
        converted[key] = convertPyodideToJS(value);
      }
    }
    return converted;
  }

  // Handle Arrays/Lists
  if (Array.isArray(obj)) {
    return obj.map((item) => convertPyodideToJS(item));
  }

  // Handle plain objects
  if (obj && typeof obj === "object" && obj.constructor === Object) {
    const converted = {};
    for (const [key, value] of Object.entries(obj)) {
      converted[key] = convertPyodideToJS(value);
    }
    return converted;
  }

  // Handle primitives (strings, numbers, booleans, null, undefined)
  return obj;
}

function runSimulationStep(simSettings) {
  try {
    // Run a frame of the simulation (in worker.py) and collect the results.
    var pyResults;
    if (simSettings.chartType == CHART_TYPES.MAP) {
      pyResults = workerPackage.sim.next_frame_map();
    } else if (simSettings.chartType == CHART_TYPES.STATS) {
      pyResults = workerPackage.sim.next_frame_stats();
    } else if (simSettings.chartType == CHART_TYPES.WHAT_IF) {
      pyResults = workerPackage.sim.next_frame_stats();
    } else {
      console.log(
        "runSimulationStep: unrecognize chart type",
        simSettings.chartType
      );
    }
    // convert the results to a suitable format.
    // See https://pyodide.org/en/stable/usage/type-conversions.html
    // let results = pyResults.toJs();
    pyResults.set("name", simSettings.name);
    pyResults.set("animationDelay", simSettings.animationDelay);
    pyResults.set("chartType", simSettings.chartType);
    if (
      (pyResults.get("block") < 2 * simSettings.timeBlocks &&
        simSettings.action == SimulationActions.Play) ||
      (simSettings.timeBlocks == 0 &&
        simSettings.action == SimulationActions.Play) ||
      (pyResults.get("block") == 0 &&
        simSettings.action == SimulationActions.SingleStep)
    ) {
      // special case: do one extra step on first single-step action to avoid
      // resetting each time
      setTimeout(runSimulationStep, simSettings.animationDelay, simSettings);
    }
    const results = convertPyodideToJS(pyResults);
    pyResults.destroy(); // console.log("runSimulationStep: results=", results);
    // In newer pyodide, results is a Map, which cannot be cloned for posting.
    self.postMessage(results);
  } catch (error) {
    console.error("Error in runSimulationStep: ", error.message);
    console.error("-- stack trace:", error.stack);
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
  self.postMessage({ text: "Pyodide loaded" });
}
handlePyodideReady();

self.onmessage = async (event) => {
  /*
   * Receive messages from the UI (app.js), and pass them on
   * to pyodide.
   *
   * The functions called here also post messages back
   * to the message-handler.js, for example after each step of the
   * simulation
   */
  try {
    // ensure that Pyodide is ready before passing anything on
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
      runSimulationStep(simSettings);
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
      if (simSettings.chartType == CHART_TYPES.MAP) {
        runMapSimulationStep(simSettings);
      } else if (simSettings.chartType == CHART_TYPES.STATS) {
        runStatsSimulationStep(simSettings);
      }
    } else if (
      simSettings.action == SimulationActions.Reset ||
      simSettings.action == SimulationActions.Done
    ) {
      resetSimulation(simSettings);
    }
  } catch (error) {
    console.error("Error in onmessage: ", error.message);
  }
};
