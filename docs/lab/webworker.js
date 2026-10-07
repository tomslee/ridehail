/**
 * ES Module Web Worker for Pyodide ridehail simulation
 *
 * This worker loads Pyodide and runs Python simulation code,
 * communicating results back to the main thread via postMessage.
 */

import {
  CHART_TYPES,
  SimulationActions,
  framesPerBlock,
} from "./js/constants.js";

// Pyodide CDN configuration
const PYODIDE_CDN = "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/";
const LOCAL_PYODIDE = "./pyodide/";
const ridehailLocation = "./dist/";

// Worker state
let pyodide = null;
let workerPackage = null;
let simulationTimeoutId = null;
let currentSimSettings = null;
// The frame the play loop will run next, and what it is waiting for, or null
// when the loop is stopped (paused, reset, finished, or superseded):
//   { settings, runId, waitingFor: "ack" | "offer" }
//
// "ack" - backpressure. The worker self-paces on a timer (see
// scheduleNextFrame), but previously did so unconditionally, with no regard
// for whether the main thread had even started rendering the last frame.
// Since postMessage is fire-and-forget with no built-in flow control, that let
// the worker (the producer) run arbitrarily far ahead of the renderer (the
// consumer) whenever rendering took longer than animationDelay - worst case at
// animationDelay=0, where the worker had no throttle at all. Gating the *next*
// frame on an ack for the *current* one caps the worker at most one frame
// ahead, always.
//
// "offer" - the Game tab. While an offer is on screen the world is frozen: the
// frame that carries the offer is posted as usual, but its ack does not resume
// the loop; the player's GameDecision does.
//
// runId is the run the frame belongs to - see activeRunId below.
let nextFrame = null;

// Only one simulation loop can run in this worker at a time (single global
// `sim` plus the currentSimSettings/nextFrame/simulationTimeoutId
// state above - there's no per-tab state). The Experiment tab, the What If
// Baseline run, and the What If Comparison run all share it.
//
// Nothing pauses the Experiment loop when the user switches tabs or starts a
// What If run, so a getNextFrame call belonging to it can still be in flight
// - already scheduled via scheduleNextFrame()'s setTimeout, or (per Pyodide's
// FFI, which can yield to the microtask queue inside what looks like a
// synchronous call) genuinely concurrent with a Reset/Play/Pause message -
// when a different run takes over. Without a way to recognize that, such a
// call finishes by overwriting currentSimSettings/nextFrame back
// to the stale run and re-posting under its name, silently orphaning the run
// that superseded it - e.g. the What If block counter stays stuck at 0
// forever because every frame that arrives is still labelled "labSimSettings"
// and gets routed to the Experiment tab's counter instead (see
// updateBlockCounters in app.js).
//
// activeRunId is bumped every time something takes exclusive ownership of the
// shared loop (Reset/Done, Pause, or the start of a fresh Play/SingleStep -
// see self.onmessage and resetSimulation). Every getNextFrame call carries the
// runId that was active when it was scheduled; if activeRunId has moved on by
// the time it actually runs, it's stale and bails out immediately instead of
// touching any shared state. This is a generation counter, not a timing fix -
// it makes staleness self-evident regardless of *why* the call ended up
// running late.
let activeRunId = 0;

// Frame-pacing compensation: scheduleNextFrame's setTimeout(animationDelay)
// only covers the *wait*, but getNextFrame() then still spends real time on
// the Python simulation step, Pyodide marshalling, and postMessage before the
// frame actually reaches the renderer. Left unaccounted for, that work lands
// entirely on top of animationDelay, so the true gap between frame arrivals
// is animationDelay + computeTime while map.js's chart animation only glides
// for animationDelay - the difference shows up as a visible freeze at every
// frame boundary (worse at city sizes/vehicle counts where compute time is
// non-trivial, e.g. Town scale). Map mode alternates real simulation frames
// (even frame_index, expensive: full block step + vehicle deep-copy) with
// interpolated midpoint frames (odd frame_index, cheap: a position nudge), so
// track the measured cost per parity and use it to predict - and subtract -
// the cost of the *next* frame, keeping the actual cadence close to
// animationDelay regardless of which kind of frame is coming up.
let frameDurationByParity = [0, 0];
let lastFrameParity = 0;

// Game tab time warp: while the player has nothing to decide (on a trip, or idle in a
// slow market) the game runs faster. Scales both the wait before the next
// frame and the frame's own glide duration (its animationDelay), so map.js
// animations still finish exactly as the next frame arrives.
let frameDelayFactor = 1;

// The name of the settings (e.g. "labSimSettings") that the current `sim`
// was initialized from, so that a FollowVehicle message from the Experiment
// tab cannot act on a What If or Game simulation that has taken over.
let simName = null;

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
          "   See: https://github.com/pyodide/pyodide/releases/tag/314.0.7"
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
    // no-cache: always revalidate with the server. The manifest names the
    // current wheel, and old wheels are removed on deploy, so a stale cached
    // manifest (servers that send no Cache-Control let browsers keep files
    // for a heuristic period) points at a wheel that no longer exists and
    // micropip fails. worker.py must match the installed package, so it is
    // revalidated for the same reason.
    const manifestResponse = await fetch(`${ridehailLocation}manifest.json`, {
      cache: "no-cache",
    });
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
    const workerPyResponse = await fetch("./worker.py", { cache: "no-cache" });
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

function getNextFrame(simSettings, runId) {
  if (runId !== activeRunId) {
    // Stale: a different run has taken over the shared loop since this call
    // was scheduled (see activeRunId above). Drop it before it can touch
    // currentSimSettings/nextFrame or post a mislabelled frame.
    return;
  }
  // The next frame may be a simulation step (and always is for stats
  // or may be an interpolation frame (for map). Ideally we would
  // handle the interpolation here, so that worker.py does not have
  // to know anything about frames, but so it goes...
  const frameStartTime = performance.now();
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

    // Re-check staleness: the Python call above is the yield point flagged
    // in the activeRunId comment - a Reset/Play/Pause for a different run
    // can be processed by the worker while it's suspended. The entry check
    // above can't catch that, since it only ran *before* the yield. Without
    // this second check, a call that went stale mid-flight would still fall
    // through to overwrite the shared nextFrame
    // with its own (now stale) values below - clobbering whatever the
    // newer run had already set up there - and post its results under its
    // own (now stale) name. That silently orphans the newer run: its next
    // scheduled getNextFrame call inherits the clobbered, stale runId, so
    // it self-aborts at its own entry check, and its block counter/results
    // table simply stop receiving frames with no visible error.
    if (runId !== activeRunId) {
      pyResults.destroy();
      return;
    }

    // convert the results to a suitable format.
    // See https://pyodide.org/en/stable/usage/type-conversions.html
    // let results = pyResults.toJs();
    pyResults.set("name", currentSimSettings.name);
    pyResults.set("animationDelay", currentSimSettings.animationDelay);
    pyResults.set("chartType", currentSimSettings.chartType);
    // Map mode normally takes 2 frames per block (real + interpolated
    // midpoint), but worker.py skips the interpolated frame for big cities
    // (see Simulation.interpolate_frames there) - match that here so the play
    // loop stops at the right point. Stats charts take one frame per block.
    const frameLimit =
      currentSimSettings.chartType == CHART_TYPES.MAP
        ? framesPerBlock(currentSimSettings.citySize) *
          currentSimSettings.timeBlocks
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
      nextFrame = { settings: currentSimSettings, runId, waitingFor: "ack" };
    } else {
      nextFrame = null;
    }
    const results = pyResultToJs(pyResults);
    pyResults.destroy();
    if (simSettings.game && nextFrame !== null) {
      // Game: an offer freezes the world until the player decides (see
      // nextFrame), and the end of the shift ends the run.
      if (results.game.shift_over) {
        nextFrame = null;
      } else if (results.game.offer) {
        nextFrame.waitingFor = "offer";
      }
    }
    if (simSettings.game) {
      const busy = results.game.player_phase !== "P1";
      frameDelayFactor = busy
        ? simSettings.gameWarpBusy ?? 1
        : simSettings.gameWarpIdle ?? 1;
      results.animationDelay = simSettings.animationDelay * frameDelayFactor;
    } else {
      frameDelayFactor = 1;
    }
    // console.log("getNextFrame: results=", results);
    // In newer pyodide, results is a Map, which cannot be cloned for posting.
    // post message to front end
    self.postMessage(results);
    lastFrameParity = results.frame % 2;
    frameDurationByParity[lastFrameParity] = performance.now() - frameStartTime;
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
    nextFrame = null;
  }
}

/**
 * Resume the play loop once the main thread has acked the last frame sent.
 * Called from the FrameAck handler in self.onmessage, and after a game
 * offer is resolved. A no-op unless the loop is waiting for an ack - e.g. the
 * simulation was paused/reset/finished between sending the last frame and
 * receiving its ack, or a game offer is still on screen.
 */
function scheduleNextFrame() {
  if (nextFrame === null || nextFrame.waitingFor !== "ack") {
    return;
  }
  const { settings: simSettings, runId } = nextFrame;
  nextFrame = null;
  // animationDelay still applies as the minimum pacing between frames -
  // backpressure only adds a floor of "wait for the renderer", it doesn't
  // remove the deliberate slow-down used for small-scale legibility.
  //
  // The upcoming frame will itself take frameDurationByParity[nextParity] ms
  // to compute/marshal/post (see getNextFrame), so only wait the remainder of
  // animationDelay here - otherwise that cost lands on top of animationDelay
  // and the renderer sees a gap after each glide finishes (see the
  // frameDurationByParity comment above for the full explanation).
  const nextParity = (lastFrameParity + 1) % 2;
  const wait = Math.max(
    0,
    simSettings.animationDelay * frameDelayFactor -
      frameDurationByParity[nextParity]
  );
  simulationTimeoutId = setTimeout(getNextFrame, wait, simSettings, runId);
}

/**
 * Claim the shared loop for a new run, or stop it: invalidate any in-flight
 * getNextFrame call from whatever run was previously using it (see
 * activeRunId above), cancel its timer, and drop the frame it was waiting to
 * run (including a held game offer).
 */
function claimLoop() {
  activeRunId += 1;
  // Clear only our tracked simulation timeout
  if (simulationTimeoutId !== null) {
    clearTimeout(simulationTimeoutId);
    simulationTimeoutId = null;
  }
  nextFrame = null;
}

function resetSimulation(simSettings) {
  claimLoop();
  frameDelayFactor = 1;
  // Discard duration estimates from any previous (possibly differently
  // sized/loaded) simulation so pacing isn't mispredicted for the new one.
  frameDurationByParity = [0, 0];
  lastFrameParity = 0;
  workerPackage.init_simulation(simSettings);
  simName = simSettings.name;
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
  // Surface the package version as soon as it's known (the worker has
  // already imported it to install the wheel), so the header can show it
  // immediately instead of waiting for the first simulation frame, which
  // is the only other place worker.py attaches a "version" field.
  const helpProxy = workerPackage.get_slider_help();
  const sliderHelp = helpProxy.toJs({ dict_converter: Object.fromEntries });
  helpProxy.destroy();
  const configProxy = workerPackage.get_slider_config();
  const sliderConfig = configProxy.toJs({ dict_converter: Object.fromEntries });
  configProxy.destroy();
  // Preset starting values (Village/Town/City), sourced from ridehail/presets.py
  // so the browser doesn't keep a second hand-maintained copy. Nested dict, so
  // toJs recurses with the same dict_converter.
  const presetsProxy = workerPackage.get_presets();
  const presetValues = presetsProxy.toJs({ dict_converter: Object.fromEntries });
  presetsProxy.destroy();
  self.postMessage({
    text: "Pyodide loaded",
    version: workerPackage.__version__,
    sliderHelp: sliderHelp,
    sliderConfig: sliderConfig,
    presetValues: presetValues,
  });
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
        //
        // Claim the shared loop for this run - see activeRunId above. A
        // different simulation (e.g. the Experiment tab) may still be
        // actively playing, since nothing pauses it when switching tabs or
        // starting a What If run; bumping activeRunId here means any
        // getNextFrame call it still has in flight will recognize itself as
        // stale and no-op instead of overwriting currentSimSettings/
        // nextFrame back to the old simulation - e.g. the What If
        // block counter appears stuck at 0.
        claimLoop();
        frameDelayFactor = 1;
        if (simSettings.game) {
          workerPackage.init_game(simSettings);
        } else {
          workerPackage.init_simulation(simSettings);
        }
        simName = simSettings.name;
      }
      getNextFrame(simSettings, activeRunId);
    } else if (simSettings.action == SimulationActions.FrameAck) {
      scheduleNextFrame();
    } else if (simSettings.action == SimulationActions.Pause) {
      // Claim the shared loop so any frame still in flight for this run is
      // recognized as stale and dropped - otherwise it could still complete,
      // re-arm nextFrame, and keep the loop alive despite the pause (see
      // activeRunId above).
      claimLoop();
    } else if (simSettings.action == SimulationActions.GameDecision) {
      // Only the run that is holding for this offer may resolve it: a
      // decision arriving after a Reset/Pause (stale run id) is dropped.
      if (
        nextFrame !== null &&
        nextFrame.waitingFor === "offer" &&
        nextFrame.runId === activeRunId
      ) {
        workerPackage.sim.resolve_offer(
          Boolean(simSettings.accept),
          Boolean(simSettings.timedOut)
        );
        nextFrame.waitingFor = "ack";
        scheduleNextFrame();
      }
    } else if (simSettings.action == SimulationActions.GetGameResults) {
      const pyResults = workerPackage.sim.game_results();
      const results = pyResultToJs(pyResults);
      pyResults.destroy();
      self.postMessage({ action: "gameResults", results: results });
    } else if (simSettings.action == SimulationActions.FollowVehicle) {
      // Frames carry the followed car from now on; the reply shows it on the
      // frame already on screen (e.g. while paused). Not part of the play
      // loop, so no runId check, but only for the simulation the message is
      // about. A reset starts with no car followed.
      if (workerPackage.sim && simName === simSettings.name) {
        // undefined, not null, for "stop": Pyodide passes JS null to Python
        // as jsnull, and only undefined as None
        const pyFollowed = workerPackage.sim.follow_vehicle(
          simSettings.choice ?? undefined
        );
        let followed = null;
        if (pyFollowed) {
          followed = pyResultToJs(pyFollowed);
          pyFollowed.destroy();
        }
        self.postMessage({ action: "followed", followed });
      }
    } else if (simSettings.action == SimulationActions.Update) {
      updateSimulation(simSettings);
    } else if (simSettings.action == SimulationActions.UpdateDisplay) {
      claimLoop();
      simSettings.action = SimulationActions.Play;
      getNextFrame(simSettings, activeRunId);
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
