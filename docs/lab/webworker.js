/**
 * ES Module Web Worker for Pyodide ridehail simulation
 *
 * This worker loads Pyodide and runs Python simulation code,
 * communicating results back to the main thread via postMessage.
 */

import { CHART_TYPES, SimulationActions } from "./js/constants.js";

// Determine Pyodide source (local or CDN)
const indexURL = (location.hostname === "localhost" || location.hostname === "127.0.0.1")
  ? "./pyodide/"
  : "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";

const ridehailLocation = "./dist/";

console.log("webworker.js: loading Pyodide from", indexURL);

// Worker state
let pyodide = null;
let workerPackage = null;
let simulationTimeoutId = null;
let currentSimSettings = null;

/**
 * Load Pyodide and required packages using modern ES module approach
 */
async function loadPyodideAndPackages() {
  try {
    // Dynamically import Pyodide based on source (local or CDN)
    const pyodideModule = await import(`${indexURL}pyodide.mjs`);
    const loadPyodide = pyodideModule.loadPyodide;

    // Initialize Pyodide
    pyodide = await loadPyodide({
      indexURL: indexURL,
    });

    console.log("Pyodide initialized successfully");

    // Load micropip (bundled with Pyodide)
    await pyodide.loadPackage("micropip");

    // Install ridehail wheel using micropip's Python API
    // Load manifest to get current wheel filename (version-independent loading)
    const manifestResponse = await fetch(`${ridehailLocation}manifest.json`);
    const manifest = await manifestResponse.json();

    const micropip = pyodide.pyimport("micropip");
    await micropip.install(`${ridehailLocation}${manifest.wheel}`);

    // Note: micropip currently loads 'rich' as a transitive dependency because
    // the wheel includes animation modules (terminal_map.py, rich_base.py, etc.)
    // that have top-level 'from rich import ...' statements. This doesn't affect
    // functionality since those modules are never used in the web interface.

    console.log("Ridehail package installed");

    // Load worker.py using Pyodide's filesystem API
    const workerPyResponse = await fetch("./worker.py");
    if (!workerPyResponse.ok) {
      throw new Error(`Failed to fetch worker.py: ${workerPyResponse.status}`);
    }
    const workerPyCode = await workerPyResponse.text();
    pyodide.FS.writeFile("/home/pyodide/worker.py", workerPyCode);

    // Import worker module
    workerPackage = pyodide.pyimport("worker");

    console.log("Worker module loaded successfully");

    return pyodide;
  } catch (error) {
    console.error("Failed to initialize Pyodide:", error);
    // Propagate error to main thread for user-visible feedback
    self.postMessage({
      error: "initialization",
      message: error.message,
      stack: error.stack
    });
    throw error;
  }
}

const pyodideReadyPromise = loadPyodideAndPackages();

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
    // Convert objects to arrays [phase, location, direction, pickup_countdown]
    return vehicles.map((vehicle) => [
      vehicle.phase,
      vehicle.location,
      vehicle.direction,
      vehicle.pickup_countdown !== undefined ? vehicle.pickup_countdown : null,
    ]);
  }

  // If already in array format or unknown format, return as-is
  return vehicles;
}

/**
 * Convert Pyodide objects to JavaScript objects for postMessage
 *
 * Uses modern Pyodide toJs() with depth control to prevent infinite recursion
 * and improve performance by forcing full conversion instead of creating proxies.
 *
 * @param {*} obj - Pyodide object to convert
 * @returns {*} JavaScript-native object safe for postMessage
 */
function convertPyodideToJS(obj) {
  // Handle Pyodide objects with modern conversion options
  if (obj && typeof obj.toJs === "function") {
    // Convert with depth limit and no proxies for better performance
    obj = obj.toJs({
      depth: 10,              // Reasonable depth for simulation data structures
      create_proxies: false   // Force full conversion, no lazy proxies
    });
  }

  // Handle Maps (from Pyodide's dict.toJs())
  if (obj instanceof Map) {
    const converted = {};
    for (const [key, value] of obj) {
      // Special handling for vehicles key - ensure array format
      if (key === "vehicles" && Array.isArray(value)) {
        converted[key] = convertVehiclesToArrays(value);
      } else {
        // Recursively convert nested structures
        converted[key] = convertPyodideToJS(value);
      }
    }
    return converted;
  }

  // Handle Arrays/Lists (already converted by toJs)
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
    // Update current settings to latest values (for animationDelay changes mid-simulation)
    currentSimSettings = simSettings;

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
    pyResults.set("name", currentSimSettings.name);
    pyResults.set("animationDelay", currentSimSettings.animationDelay);
    pyResults.set("chartType", currentSimSettings.chartType);
    if (
      (pyResults.get("block") < 2 * currentSimSettings.timeBlocks &&
        currentSimSettings.action == SimulationActions.Play) ||
      (currentSimSettings.timeBlocks == 0 &&
        currentSimSettings.action == SimulationActions.Play) ||
      (pyResults.get("block") == 0 &&
        currentSimSettings.action == SimulationActions.SingleStep)
    ) {
      // special case: do one extra step on first single-step action to avoid
      // resetting each time
      // Use currentSimSettings.animationDelay to pick up real-time changes
      simulationTimeoutId = setTimeout(runSimulationStep, currentSimSettings.animationDelay, currentSimSettings);
    }
    const results = convertPyodideToJS(pyResults);
    pyResults.destroy(); // console.log("runSimulationStep: results=", results);
    // In newer pyodide, results is a Map, which cannot be cloned for posting.
    self.postMessage(results);
  } catch (error) {
    console.error("Error in runSimulationStep: ", error.message);
    console.error("-- stack trace:", error.stack);

    // Propagate error to main thread
    self.postMessage({
      error: "simulation",
      message: error.message,
      stack: error.stack
    });

    // Clear any pending timeouts to stop the simulation
    if (simulationTimeoutId !== null) {
      clearTimeout(simulationTimeoutId);
      simulationTimeoutId = null;
    }
  }
}

function resetSimulation(simSettings) {
  // Clear only our tracked simulation timeout
  if (simulationTimeoutId !== null) {
    clearTimeout(simulationTimeoutId);
    simulationTimeoutId = null;
  }
  workerPackage.init_simulation(simSettings);
}

function updateSimulation(simSettings) {
  // Update cached settings so animationDelay changes take effect immediately
  if (currentSimSettings) {
    currentSimSettings.animationDelay = simSettings.animationDelay;
  }
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
      // Clear only our tracked simulation timeout
      if (simulationTimeoutId !== null) {
        clearTimeout(simulationTimeoutId);
        simulationTimeoutId = null;
      }
    } else if (simSettings.action == SimulationActions.Update) {
      updateSimulation(simSettings);
    } else if (simSettings.action == SimulationActions.UpdateDisplay) {
      // Clear only our tracked simulation timeout
      if (simulationTimeoutId !== null) {
        clearTimeout(simulationTimeoutId);
        simulationTimeoutId = null;
      }
      simSettings.action = SimulationActions.Play;
      runSimulationStep(simSettings);
    } else if (
      simSettings.action == SimulationActions.Reset ||
      simSettings.action == SimulationActions.Done
    ) {
      resetSimulation(simSettings);
    }
  } catch (error) {
    console.error("Error in onmessage: ", error.message);
    console.error("Stack trace:", error.stack);

    // Propagate error to main thread
    self.postMessage({
      error: "simulation",
      message: error.message,
      stack: error.stack
    });
  }
};
