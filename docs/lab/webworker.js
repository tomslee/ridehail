/**
 * ES Module Web Worker for Pyodide ridehail simulation
 *
 * This worker loads Pyodide and runs Python simulation code,
 * communicating results back to the main thread via postMessage.
 */

import {
  CHART_TYPES,
  SimulationActions,
  INTERPOLATE_MAX_CITY_SIZE,
} from "./js/constants.js";

// Pyodide CDN configuration
const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v314.0.0/full/";
const LOCAL_PYODIDE = "./pyodide/";
const ridehailLocation = "./dist/";

// Worker state
let pyodide = null;
let workerPackage = null;
let simulationTimeoutId = null;
let currentSimSettings = null;
// Backpressure: settings to resume with once the main thread acks the frame
// most recently sent. The worker self-paces on a timer (see scheduleNextFrame),
// but previously did so unconditionally, with no regard for whether the main
// thread had even started rendering the last frame. Since postMessage is
// fire-and-forget with no built-in flow control, that let the worker (the
// producer) run arbitrarily far ahead of the renderer (the consumer) whenever
// rendering took longer than animationDelay - worst case at animationDelay=0,
// where the worker had no throttle at all. Gating the *next* frame on an ack
// for the *current* one caps the worker at most one frame ahead, always.
let pendingFrameSettings = null;

/**
 * Attempt to load Pyodide from a given source
 * @param {string} indexURL - URL to load Pyodide from
 * @returns {Promise<object>} Loaded Pyodide instance
 */
async function attemptLoadPyodide(indexURL) {
  console.log("webworker.js: loading Pyodide from", indexURL);

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
    // Hosts that serve a local ./pyodide/ copy (dev machine and the LAN Apache
    // host "th2"); these try local files first and fall back to the CDN.
    const LOCAL_HOSTS = ["localhost", "127.0.0.1", "th2"];
    const isLocalhost = LOCAL_HOSTS.includes(location.hostname);

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
          "   See: https://github.com/pyodide/pyodide/releases/tag/314.0.0"
        );

        pyodide = await attemptLoadPyodide(PYODIDE_CDN);
        console.log("Pyodide loaded from CDN at", PYODIDE_CDN);
      }
    } else {
      // Production: Use CDN directly
      pyodide = await attemptLoadPyodide(PYODIDE_CDN);
      console.log("Pyodide loaded from CDN");
    }

    // Report the runtime version actually loaded (more reliable than the CDN
    // string when a fallback path was taken) to aid debugging of user reports.
    console.log(`Pyodide version: ${pyodide.version}`);

    // Load micropip and numpy from Pyodide's bundled packages.
    // numpy is ridehail's only runtime dependency used in the browser; we load
    // it explicitly because the install below disables dependency resolution.
    await pyodide.loadPackage(["micropip", "numpy"]);

    // Install ridehail wheel using micropip's Python API
    // Load manifest to get current wheel filename (version-independent loading)
    const manifestResponse = await fetch(`${ridehailLocation}manifest.json`);
    const manifest = await manifestResponse.json();

    // Install with deps=false: the browser worker only imports the simulation
    // core (config/simulation/results/atom), which needs nothing beyond numpy.
    // Skipping resolution avoids pulling the terminal-only packages
    // (textual, textual-plotext, plotext, rich) from PyPI on every page load.
    const micropip = pyodide.pyimport("micropip");
    await micropip.install.callKwargs(`${ridehailLocation}${manifest.wheel}`, {
      deps: false,
    });

    console.log("Ridehail package installed (deps=false, numpy preloaded)");

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

/**
 * Convert a Pyodide PyProxy result (a Python dict) into a plain,
 * postMessage-safe JavaScript object.
 *
 * `dict_converter: Object.fromEntries` makes toJs emit plain Objects (not Maps),
 * recursively, in a single wasm-side pass; Python lists become Arrays. This
 * replaces the former two-pass approach (toJs -> Maps, then a recursive JS
 * rebuild) that walked the whole result a second time every frame.
 *
 * Option names verified against the Pyodide 314 type defs (pyodide/ffi.d.ts):
 * the correct key is `dict_converter`. (Note: the older code passed
 * `create_proxies: false`, which is not a real toJs option and was a no-op; our
 * all-primitive simulation data is fully convertible, so no PyProxies are
 * created and none need explicit destruction.)
 *
 * @param {object} pyResult - PyProxy of a Python dict
 * @returns {object} plain JS object safe for structured-clone / postMessage
 */
function pyResultToJs(pyResult) {
  return pyResult.toJs({ dict_converter: Object.fromEntries });
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
    // Map mode normally takes 2 frames per block (real + interpolated
    // midpoint), but worker.py skips the interpolated frame entirely above
    // INTERPOLATE_MAX_CITY_SIZE (see Simulation.interpolate_frames there) -
    // match that here so the play loop stops at the right point.
    const interpolating =
      currentSimSettings.chartType == CHART_TYPES.MAP &&
      currentSimSettings.citySize <= INTERPOLATE_MAX_CITY_SIZE;
    const frameLimit = interpolating
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
      // Don't schedule the next frame yet - wait for the main thread to ack
      // this one first (see scheduleNextFrame and the FrameAck handler below).
      pendingFrameSettings = currentSimSettings;
    } else {
      pendingFrameSettings = null;
    }
    const results = pyResultToJs(pyResults);
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
    pendingFrameSettings = null;
  }
}

/**
 * Resume the play loop once the main thread has acked the last frame sent.
 * Called from the FrameAck handler in self.onmessage. A no-op if nothing is
 * pending - e.g. the simulation was paused/reset/finished between sending
 * the last frame and receiving its ack.
 */
function scheduleNextFrame() {
  if (pendingFrameSettings === null) {
    return;
  }
  const simSettings = pendingFrameSettings;
  pendingFrameSettings = null;
  // animationDelay still applies as the minimum pacing between frames -
  // backpressure only adds a floor of "wait for the renderer", it doesn't
  // remove the deliberate slow-down used for small-scale legibility.
  simulationTimeoutId = setTimeout(
    getNextFrame,
    simSettings.animationDelay,
    simSettings
  );
}

function resetSimulation(simSettings) {
  // Clear only our tracked simulation timeout
  if (simulationTimeoutId !== null) {
    clearTimeout(simulationTimeoutId);
    simulationTimeoutId = null;
  }
  pendingFrameSettings = null;
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
    } else if (simSettings.action == SimulationActions.FrameAck) {
      scheduleNextFrame();
    } else if (simSettings.action == SimulationActions.Pause) {
      // Clear only our tracked simulation timeout
      if (simulationTimeoutId !== null) {
        clearTimeout(simulationTimeoutId);
        simulationTimeoutId = null;
      }
      pendingFrameSettings = null;
    } else if (simSettings.action == SimulationActions.Update) {
      updateSimulation(simSettings);
    } else if (simSettings.action == SimulationActions.UpdateDisplay) {
      // Clear only our tracked simulation timeout
      if (simulationTimeoutId !== null) {
        clearTimeout(simulationTimeoutId);
        simulationTimeoutId = null;
      }
      pendingFrameSettings = null;
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
      const results = pyResultToJs(pyResults);
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
