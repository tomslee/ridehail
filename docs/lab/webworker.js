/**
 * ES Module Web Worker for Pyodide ridehail simulation
 *
 * This worker loads Pyodide and runs Python simulation code,
 * communicating results back to the main thread via postMessage.
 */

import { CHART_TYPES, SimulationActions } from "./js/constants.js";

// Pyodide CDN configuration
const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v0.28.3/full/";
const LOCAL_PYODIDE = "./pyodide/";
const ridehailLocation = "./dist/";

// Worker state
let pyodide = null;
let workerPackage = null;
let simulationTimeoutId = null;
let currentSimSettings = null;

/**
 * Attempt to load Pyodide from a given source
 * @param {string} indexURL - URL to load Pyodide from
 * @returns {Promise<object>} Loaded Pyodide instance
 */
async function attemptLoadPyodide(indexURL) {
  console.log("webworker.js: attempting to load Pyodide from", indexURL);

  // Dynamically import Pyodide based on source (local or CDN)
  const pyodideModule = await import(`${indexURL}pyodide.mjs`);
  const loadPyodide = pyodideModule.loadPyodide;

  // Initialize Pyodide
  const pyodideInstance = await loadPyodide({
    indexURL: indexURL,
  });

  return pyodideInstance;
}

/**
 * Load Pyodide with automatic fallback from local to CDN
 * For localhost: try local files first, fall back to CDN if not available
 * For production: use CDN directly
 */
async function loadPyodideAndPackages() {
  try {
    const isLocalhost =
      location.hostname === "localhost" || location.hostname === "127.0.0.1";

    if (isLocalhost) {
      // Development: Try local files first, fall back to CDN
      try {
        pyodide = await attemptLoadPyodide(LOCAL_PYODIDE);
        console.log("Pyodide loaded from local files at", LOCAL_PYODIDE);
      } catch (localError) {
        console.warn(
          "Local Pyodide not found, falling back to CDN:",
          localError.message
        );
        console.log(
          "💡 Tip: Download Pyodide locally for faster offline development"
        );
        console.log(
          "   See: https://github.com/pyodide/pyodide/releases/tag/0.28.3"
        );

        pyodide = await attemptLoadPyodide(PYODIDE_CDN);
        console.log("Pyodide loaded from CDN at", PYODIDE_CDN);
      }
    } else {
      // Production: Use CDN directly
      pyodide = await attemptLoadPyodide(PYODIDE_CDN);
      console.log("Pyodide loaded from CDN");
    }

    // Load micropip (bundled with Pyodide)
    await pyodide.loadPackage("micropip");

    // Install ridehail wheel using micropip's Python API
    // Load manifest to get current wheel filename (version-independent loading)
    const manifestResponse = await fetch(`${ridehailLocation}manifest.json`);
    const manifest = await manifestResponse.json();

    const micropip = pyodide.pyimport("micropip");
    await micropip.install(`${ridehailLocation}${manifest.wheel}`);

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
      stack: error.stack,
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
      depth: 10, // Reasonable depth for simulation data structures
      create_proxies: false, // Force full conversion, no lazy proxies
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

function getNextFrame(simSettings) {
  // The next frame may be a simulation step (and always is for stats
  // or may be an interpolation frame (for map). Ideally we would
  // handle the interpolation here, so that worker.py does not have
  // to know anything about frames, but so it goes...
  try {
    // Update current settings to latest values (for animationDelay changes mid-simulation)
    currentSimSettings = simSettings;

    // Run a frame of the simulation (in worker.py) and collect the results.
    var pyResults;
    if (simSettings.chartType == CHART_TYPES.MAP) {
      pyResults = workerPackage.sim.next_frame_map();
    } else if (simSettings.chartType == CHART_TYPES.STATS) {
      pyResults = workerPackage.sim.next_block_stats();
    } else if (simSettings.chartType == CHART_TYPES.WHAT_IF) {
      pyResults = workerPackage.sim.next_block_stats();
    } else {
      console.log(
        "getNextFrame: unrecognize chart type",
        simSettings.chartType
      );
    }
    // convert the results to a suitable format.
    // See https://pyodide.org/en/stable/usage/type-conversions.html
    // let results = pyResults.toJs();
    pyResults.set("name", currentSimSettings.name);
    pyResults.set("animationDelay", currentSimSettings.animationDelay);
    pyResults.set("chartType", currentSimSettings.chartType);
    const frameLimit =
      currentSimSettings.chartType == CHART_TYPES.MAP
        ? 2 * currentSimSettings.timeBlocks
        : currentSimSettings.timeBlocks;
    if (
      (pyResults.get("frame") < frameLimit &&
        currentSimSettings.action == SimulationActions.Play) ||
      (currentSimSettings.timeBlocks == 0 &&
        currentSimSettings.action == SimulationActions.Play) ||
      (pyResults.get("frame") == 0 &&
        currentSimSettings.action == SimulationActions.SingleStep)
    ) {
      // special case: do one extra step on first single-step action to avoid
      // resetting each time
      // Use currentSimSettings.animationDelay to pick up real-time changes
      simulationTimeoutId = setTimeout(
        getNextFrame,
        currentSimSettings.animationDelay,
        currentSimSettings
      );
    }
    const results = convertPyodideToJS(pyResults);
    pyResults.destroy();
    // console.log("getNextFrame: results=", results);
    // In newer pyodide, results is a Map, which cannot be cloned for posting.
    // post message to front end
    self.postMessage(results);
  } catch (error) {
    console.error("Error in getNextFrame: ", error.message);
    console.error("-- stack trace:", error.stack);

    // Propagate error to main thread
    self.postMessage({
      error: "simulation",
      message: error.message,
      stack: error.stack,
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
        // initialize only if it is a new simulation
        workerPackage.init_simulation(simSettings);
      }
      getNextFrame(simSettings);
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
      getNextFrame(simSettings);
    } else if (
      simSettings.action == SimulationActions.Reset ||
      simSettings.action == SimulationActions.Done
    ) {
      resetSimulation(simSettings);
    } else if (simSettings.action == SimulationActions.GetResults) {
      // Get simulation results for config download
      const pyResults = workerPackage.sim.get_simulation_results();
      const results = convertPyodideToJS(pyResults);
      pyResults.destroy();
      self.postMessage({
        action: "results",
        results: results,
      });
    }
  } catch (error) {
    console.error("Error in onmessage: ", error.message);
    console.error("Stack trace:", error.stack);

    // Propagate error to main thread
    self.postMessage({
      error: "simulation",
      message: error.message,
      stack: error.stack,
    });
  }
};
