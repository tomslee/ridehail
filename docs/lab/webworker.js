/* global pyodide, loadPyodide */
/*
 * This is the JavaScript side of the JavaScript - Python
 * interface.
 *
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
 *
 * webworker.js gets results from pyodide and the posts the results
 * (postMessage) or simple strings (status and error messages),
 * which are then received by message-handler.js.
 * It also listens to messages from app.js and sends them on to pyodide.
 */

/*
import { CHART_TYPES } from "./js/config.js";
*/
const CHART_TYPES = {
  MAP: "map",
  STATS: "stats",
  WHAT_IF: "whatif",
};

/**
 * @enum
 * TODO: This is duplicate from main.js. When I can use this file as a module,
 * import it
 * possible simulation actions and sim_states, for the fabButton
 */
const SimulationActions = {
  Play: "play_arrow",
  Pause: "pause",
  Reset: "reset",
  SingleStep: "single-step",
  Update: "update",
  UpdateDisplay: "updateDisplay",
};

// Set one of these to load locally or from the CDN
var indexURL = "https://cdn.jsdelivr.net/pyodide/v0.28.2/full/";
const ridehailLocation = "./dist/";
if (
  location.hostname === "localhost" ||
  location.hostname === "127.0.0.1" ||
  location.hostname === "th2"
) {
  indexURL = "./pyodide/";
}
console.log("webworker.js: importing pyodide from", indexURL);
importScripts(`${indexURL}pyodide.js`);
var workerPackage;

/*
 * From pyodide v 0.28.0,  JavaScript null is no longer converted to
 * None by default, so that "undefined" can be distinguished from "null".
 * In the short term, I've added the convertNullToNone argument
 * to preserve the old behaviour.
 */
async function loadPyodideAndPackages() {
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

function runStatsSimulationStep(simSettings) {
  try {
    let pyResults = workerPackage.sim.next_frame_stats();
    pyResults.set("name", simSettings.name);
    pyResults.set("frameTimeout", simSettings.frameTimeout);
    pyResults.set("chartType", simSettings.chartType);
    if (
      (pyResults.get("block") < simSettings.timeBlocks &&
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
    const results = convertPyodideToJS(pyResults);
    pyResults.destroy();
    self.postMessage(results);
  } catch (error) {
    console.log("Error in runStatsSimulationStep: ", error.message);
    self.postMessage({ error: error.message });
  }
}

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

function runMapSimulationStep(simSettings) {
  try {
    // Collect the results of this frame from next_frame_map
    let pyResults = workerPackage.sim.next_frame_map();
    // convert the results to a suitable format.
    // See https://pyodide.org/en/stable/usage/type-conversions.html
    // let results = pyResults.toJs();
    pyResults.set("name", simSettings.name);
    pyResults.set("frameTimeout", simSettings.frameTimeout);
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
      setTimeout(runMapSimulationStep, simSettings.frameTimeout, simSettings);
    }
    const results = convertPyodideToJS(pyResults);
    pyResults.destroy(); // console.log("runMapSimulationStep: results=", results);
    // Post the results to the user interface
    // In newer pyodide, results is a Map, which cannot be cloned for posting.
    // Object.fromEntries does a conversion to an Object so it can be posted
    // self.postMessage({ dict_converter: Object.fromEntries(results) });
    // console.log("Posting results: ", results);
    self.postMessage(results);
  } catch (error) {
    console.error("Error in runMapSimulationStep: ", error.message);
    console.error("-- stack trace:", error.stack);
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
      if (simSettings.chartType == CHART_TYPES.MAP) {
        runMapSimulationStep(simSettings);
      } else if (simSettings.chartType == CHART_TYPES.STATS) {
        runStatsSimulationStep(simSettings);
      } else if (simSettings.chartType == CHART_TYPES.WHAT_IF) {
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
    self.postMessage({ error: error.message });
  }
};
