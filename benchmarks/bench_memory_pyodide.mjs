// Memory growth in the web lab's worker, under Pyodide in Node.
//
// Loads the local Pyodide copy (docs/lab/pyodide/) and the lab's wheel
// (docs/lab/dist/, as named in its manifest.json), imports docs/lab/worker.py,
// and makes the same calls per frame as webworker.js's getNextFrame: through
// workerPackage.sim, then set/get on the result, toJs, destroy. It samples:
//
// - wasm: the WebAssembly memory. It only ever grows (it is never returned
//   to the system), so a run whose wasm size keeps stepping up is leaking,
//   inside Python or in proxies the JS side never released.
// - traced: bytes held by Python objects inside Pyodide (tracemalloc).
// - pyobjects: objects the Python cycle collector tracks.
// - jsheap: the JS heap after a forced collection.
//
//   node --expose-gc benchmarks/bench_memory_pyodide.mjs [scenario ...] [--blocks N] [--sync]
//
// Each step yields to the event loop, as the browser worker does between
// frames; --sync never yields, the worst case for releasing proxies.
// --via-module reads the simulation as workerPackage.sim on every call, as
// webworker.js did before 2026-10-28 (each Reset kept the old simulation).
//
// Run from the repository root after ./build.sh (the wheel must match
// worker.py). Scenarios: map, map-big, stats, reset, game (see SCENARIOS).

import { readFileSync } from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const LAB = path.join(ROOT, "docs", "lab");

// Web settings as js/sim-settings.js sends them (a Town-like run, as in
// bench_memory.py's lab_settings)
function labSettings(overrides = {}) {
  return {
    name: "labSimSettings",
    citySize: 24,
    vehicleCount: 120,
    requestRate: 5.0,
    meanTripDistance: 12,
    minTripDistance: 0,
    inhomogeneity: 0.5,
    inhomogeneousDestinations: false,
    idleVehiclesMoving: 1.0,
    randomNumberSeed: 7,
    verbosity: 0,
    equilibration: "none",
    equilibrationInterval: 5,
    demandElasticity: 0.0,
    useCostsAndIncomes: false,
    meanVehicleSpeed: 30.0,
    minutesPerBlock: 1.0,
    reservationWage: 0.35,
    platformCommission: 0.25,
    price: 1.2,
    perKmPrice: 0.8,
    perMinutePrice: 0.18,
    baseFare: 3.0,
    perKmOpsCost: 0.3,
    perHourOpportunityCost: 6.0,
    timeBlocks: 0,
    smoothingWindow: 20,
    animationDelay: 0,
    pickupTime: 1,
    chartType: "map",
    action: "play",
    ...overrides,
  };
}

// The current simulation's proxy, held and released as webworker.js does
// (newSimulation there). With --via-module every call reads it afresh as
// workerPackage.sim instead, as webworker.js did before 2026-10-28, which
// kept every simulation of the session alive.
let viaModule = false;
let held = null;

function newSim(wp, init, settings) {
  const previous = held;
  held = init(settings);
  if (previous) previous.destroy();
}

const simOf = (wp) => (viaModule ? wp.sim : held);

// One frame, as webworker.js getNextFrame makes it
function frame(wp, settings) {
  const sim = simOf(wp);
  const pyResults =
    settings.chartType === "map"
      ? sim.next_frame_map()
      : sim.next_block_stats();
  pyResults.set("name", settings.name);
  pyResults.set("animationDelay", settings.animationDelay);
  pyResults.set("chartType", settings.chartType);
  pyResults.get("frame");
  const results = pyResults.toJs({ dict_converter: Object.fromEntries });
  pyResults.destroy();
  return results;
}

const SCENARIOS = {
  map: {
    description: "map frames, Town settings, open-ended",
    blocks: 20000,
    start: (wp) => {
      const s = labSettings();
      newSim(wp, wp.init_simulation, s);
      const frames = s.citySize <= 24 ? 2 : 1;
      return () => {
        for (let i = 0; i < frames; i++) frame(wp, s);
      };
    },
  },
  "map-price": {
    description: "map frames, costs and incomes, price equilibration",
    blocks: 20000,
    start: (wp) => {
      const s = labSettings({
        useCostsAndIncomes: true,
        equilibration: "price",
      });
      newSim(wp, wp.init_simulation, s);
      return () => {
        frame(wp, s);
        frame(wp, s);
      };
    },
  },
  "map-big": {
    description: "map frames, City settings (48 blocks, 1200 cars)",
    blocks: 3000,
    start: (wp) => {
      const s = labSettings({
        citySize: 48,
        vehicleCount: 1200,
        requestRate: 24,
        meanTripDistance: 24,
      });
      newSim(wp, wp.init_simulation, s);
      return () => frame(wp, s);
    },
  },
  stats: {
    description: "stats frames, Town settings",
    blocks: 20000,
    start: (wp) => {
      const s = labSettings({ chartType: "stats" });
      newSim(wp, wp.init_simulation, s);
      return () => frame(wp, s);
    },
  },
  reset: {
    description: "Reset every 50 blocks (a new settings object each time)",
    blocks: 20000,
    start: (wp) => {
      let n = 0;
      let s = null;
      return () => {
        if (n % 50 === 0) {
          s = labSettings();
          newSim(wp, wp.init_simulation, s);
        }
        n += 1;
        frame(wp, s);
        frame(wp, s);
      };
    },
  },
  game: {
    description: "game shifts, standard city, one after another",
    blocks: 6000,
    start: (wp) => {
      const s = labSettings({ game: true });
      let over = true;
      return () => {
        if (over) {
          newSim(wp, wp.init_game, {
            market: "normal",
            code: "practice",
            card: "helper",
            city: "standard",
          });
        }
        const results = frame(wp, s);
        if (results.game.offer) {
          // Accept every offer, as a player tapping through would
          simOf(wp).resolve_offer(true, false);
        }
        over = Boolean(results.game.shift_over);
      };
    },
  },
};

async function loadLab() {
  const { loadPyodide } = await import(
    path.join(LAB, "pyodide", "pyodide.mjs")
  );
  const pyodide = await loadPyodide({
    indexURL: path.join(LAB, "pyodide") + "/",
  });
  await pyodide.loadPackage(["micropip", "numpy"], {
    messageCallback: () => {},
  });
  const manifest = JSON.parse(
    readFileSync(path.join(LAB, "dist", "manifest.json")),
  );
  const wheelPath = `/tmp/${manifest.wheel}`;
  pyodide.FS.writeFile(
    wheelPath,
    readFileSync(path.join(LAB, "dist", manifest.wheel)),
  );
  const micropip = pyodide.pyimport("micropip");
  await micropip.install.callKwargs(`emfs:${wheelPath}`, { deps: false });
  micropip.destroy();
  pyodide.FS.writeFile(
    "/home/pyodide/worker.py",
    readFileSync(path.join(LAB, "worker.py"), "utf8"),
  );
  pyodide.runPython(`
import logging, sys, tracemalloc, gc
logging.disable(logging.CRITICAL)
sys.argv = ["worker.py"]
`);
  return {
    pyodide,
    workerPackage: pyodide.pyimport("worker"),
    version: manifest.version,
  };
}

// Let the event loop run: Pyodide releases the Python object behind an
// unreachable PyProxy from a FinalizationRegistry callback, which only runs
// between tasks (the browser worker yields between frames: setTimeout)
const yieldTask = () => new Promise((resolve) => setImmediate(resolve));

async function sample(pyodide, block) {
  for (let i = 0; i < 3; i++) {
    if (global.gc) global.gc();
    await yieldTask();
  }
  const [traced, objects] = pyodide
    .runPython(
      "gc.collect(); (tracemalloc.get_traced_memory()[0], len(gc.get_objects()))",
    )
    .toJs();
  return {
    block,
    wasm: pyodide._module.HEAP8.buffer.byteLength,
    traced,
    pyobjects: objects,
    jsheap: process.memoryUsage().heapUsed,
  };
}

function slope(xs, ys) {
  const n = xs.length;
  const mx = xs.reduce((a, b) => a + b, 0) / n;
  const my = ys.reduce((a, b) => a + b, 0) / n;
  let sxx = 0;
  let sxy = 0;
  for (let i = 0; i < n; i++) {
    sxx += (xs[i] - mx) ** 2;
    sxy += (xs[i] - mx) * (ys[i] - my);
  }
  return sxx ? sxy / sxx : 0;
}

const mib = (n) => (n / (1024 * 1024)).toFixed(2);

async function main() {
  const args = process.argv.slice(2);
  let blocks = null;
  let samples = 20;
  // --sync: never yield between frames (the worst case for proxy release)
  let sync = false;
  const names = [];
  for (let i = 0; i < args.length; i++) {
    if (args[i] === "--blocks") blocks = Number(args[++i]);
    else if (args[i] === "--samples") samples = Number(args[++i]);
    else if (args[i] === "--sync") sync = true;
    else if (args[i] === "--via-module") viaModule = true;
    else names.push(args[i]);
  }
  for (const name of names) {
    if (!SCENARIOS[name]) {
      throw new Error(
        `Unknown scenario ${name}: ${Object.keys(SCENARIOS).join(", ")}`,
      );
    }
  }
  if (!global.gc)
    console.log("(run with node --expose-gc for a stable jsheap column)");
  const summary = [];
  for (const name of names.length ? names : Object.keys(SCENARIOS)) {
    // A fresh Pyodide per scenario, so each starts from the same state
    const { pyodide, workerPackage, version } = await loadLab();
    held = null;
    const scenario = SCENARIOS[name];
    const total = blocks ?? scenario.blocks;
    const warmup = Math.floor(total / 5);
    // Traced from the start: allocations made before tracemalloc starts
    // and freed later would otherwise never be subtracted
    pyodide.runPython("tracemalloc.start(1)");
    const step = scenario.start(workerPackage);
    const t0 = performance.now();
    const run = async (n) => {
      for (let i = 0; i < n; i++) {
        step();
        if (!sync) await yieldTask();
      }
    };
    await run(warmup);
    const every = Math.max(50, Math.floor(total / samples / 50) * 50);
    const rows = [];
    for (let b = 0; ; b += every) {
      rows.push(await sample(pyodide, b));
      if (b >= total) break;
      await run(every);
    }
    const seconds = (performance.now() - t0) / 1000;
    console.log(
      `\n== ${name}: ${scenario.description}\n   ridehail ${version}, Pyodide ${pyodide.version}, ` +
        `${warmup} warm-up + ${rows.at(-1).block} measured blocks, ${seconds.toFixed(0)} s`,
    );
    console.log(
      `   ${"block".padStart(8)} ${"wasm MiB".padStart(9)} ${"traced MiB".padStart(11)} ` +
        `${"pyobjects".padStart(10)} ${"jsheap MiB".padStart(11)}`,
    );
    const shown = rows.filter(
      (_, i) => i % Math.max(1, Math.floor(rows.length / 10)) === 0,
    );
    if (shown.at(-1) !== rows.at(-1)) shown.push(rows.at(-1));
    for (const r of shown) {
      console.log(
        `   ${String(r.block).padStart(8)} ${mib(r.wasm).padStart(9)} ${mib(r.traced).padStart(11)} ` +
          `${String(r.pyobjects).padStart(10)} ${mib(r.jsheap).padStart(11)}`,
      );
    }
    const xs = rows.map((r) => r.block);
    const per = {};
    for (const key of ["wasm", "traced", "pyobjects", "jsheap"]) {
      per[key] = slope(
        xs,
        rows.map((r) => r[key]),
      );
    }
    console.log(
      `   slope per block: wasm ${per.wasm.toFixed(1)} B, traced ${per.traced.toFixed(1)} B, ` +
        `pyobjects ${per.pyobjects.toFixed(3)}, jsheap ${per.jsheap.toFixed(1)} B`,
    );
    summary.push({ name, per, wasmGrowth: rows.at(-1).wasm - rows[0].wasm });
  }
  console.log(
    "\nsummary (slope per block; wasm growth over the measured blocks):",
  );
  for (const s of summary) {
    console.log(
      `   ${s.name.padEnd(10)} traced ${s.per.traced.toFixed(1).padStart(8)} B  ` +
        `jsheap ${s.per.jsheap.toFixed(1).padStart(8)} B  wasm +${mib(s.wasmGrowth)} MiB`,
    );
  }
}

await main();
