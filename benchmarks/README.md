# Performance benchmarks

Benchmarks that time the real `ridehail` code, kept apart from the test suite.
Tests assert *decisions* (for example, which dispatch search runs); wall-clock
numbers depend too much on the machine for that, so they are measured here.

Run from the repository root, so the working copy is what gets measured. No
Textual or animation is involved, so any console is fine:

```bash
uv run python benchmarks/bench_dispatch.py --help
```

## Layout

| File | Purpose |
| --- | --- |
| `harness.py` | Shared pieces: the scenario registry (game markets, `test/perf/*.config`, any `.config` path), stub vehicles/trips for replaying captured states through real code, best-of-N timing, environment string |
| `bench_dispatch.py` | DEFAULT dispatch search: sparse vs dense vs the per-trip rule, on synthetic or captured states |
| `results/` | Captured states and `--json` outputs (gitignored, machine-specific) |

## bench_dispatch.py

| Subcommand | What it does |
| --- | --- |
| `list` | registered scenarios |
| `synthetic [--quick]` | uniform random states over city size x P1 x load (trips / P1); prints per-state times, the block-level crossover, and totals |
| `capture [SCENARIO ...] [-o PATH]` | runs scenarios and pickles every dispatch call's input (`results/dispatch_states.pkl` by default) |
| `replay [PATH] [--every N]` | times the strategies on saved states |
| `scenarios [SCENARIO ...]` | capture + replay |
| `simulate [SCENARIO ...]` | end-to-end simulation time and the share spent in dispatch |

The strategy columns are:

- `default@F`: the dispatcher's rule, with `Dispatch.SPARSE_SEARCH_FACTOR = F`.
  Pass several values with `--factors` to sweep it.
- `sparse` / `dense`: one search forced for every trip in the block.
- `block-best`: the faster of those two, i.e. the best any once-per-block
  rule could do.

`--json PATH` saves the rows together with the environment, so you can compare
results across changes.

Capture once and then replay against code changes: the states stay fixed while
the code changes. A captured state records only what dispatch reads (idle
vehicle locations, trip origins), so a replay is valid while the dispatch
inputs stay the same.

## Reading the numbers

- Runs on one machine vary by about 10%. Compare columns within a run, and
  repeat before trusting a difference under about 10%.
- These figures are CPython. The web lab runs Pyodide, which is slower overall;
  ratios between pure-Python strategies should roughly carry over, but that
  has not been measured.

## Results log

Add a dated line when a change is measured (machine: the development box,
CPython 3.12).

- 2026-10-03, per-trip dense->sparse switch (claude/dispatch-changeover-criterion.md).
  `game-big-busy` replayed dispatch: 3806 ms with the per-block rule, 1753 ms
  with the per-trip rule (block-best 3776 ms). End to end the run took 14.3 s
  (4.55 s in dispatch) before and 12.3 s (2.06 s) after.
  Caveat: those game scenarios had no rider cancellation, so the busy backlog
  grew to ~11k trips.
- 2026-10-03, game scenarios now cancel after 10 blocks, as the real game does
  (`max_wait_time`, now a config parameter). `game-big-busy` replayed
  dispatch: per-trip rule 1779 ms (factor 1.5: 1570 ms) against block-best
  3451 ms and forced dense 3470 ms. End to end the run took 11.0 s, 2.0 s of
  it in dispatch. Other big-city markets are within noise of block-best.
- 2026-10-28, memory growth (bench_memory.py, bench_memory_pyodide.mjs; new).
  CPython: every core and worker.py scenario is flat (village to city at
  1-16 B/block, mostly noise; toronto-2026 flat within its block-to-block
  scatter of about 50 KB; lab Reset about 300 B per Reset, from argparse and
  config strings), except `strategy`: an open-ended `use_strategy` run keeps
  `net_series`, `offer_log` and `declined` for the whole run, +113 B/block
  (about 110 MB per million blocks). Runs with `time_blocks` set are bounded
  by the shift (`results_window`). Pyodide: webworker.js read the simulation
  as `workerPackage.sim`, and Pyodide kept those proxies for the session, so
  every Reset, What If run and game shift left its whole simulation behind
  (Town: about 0.57 MB per Reset, the wasm heap 52 -> 75 MiB over 80 Resets).
  Fixed by holding one proxy (`newSimulation`): reset and game are now flat
  (wasm 52 MiB throughout). Full Pyodide rerun after the fix: map 0.8,
  map-price 0.3, map-big (City, 1200 cars) 14, stats 0.2, reset -0.2, game
  8 B/block, wasm 51.94 MiB in every scenario.
- 2026-10-28, open-ended `use_strategy` records bounded (`OFFER_LOG_LIMIT`,
  `BlockSeries`, declined trips pruned). `strategy`, 15000 blocks after a
  15000-block warm-up: +39 B/block, all of it offer-log entries (about
  210 B an offer, 0.11 offers a block), which stops when the log fills at
  10,000 offers (about 2 MB, after about 90,000 blocks). With the limit set
  to 500 to reach it sooner: -4 B/block, flat.

## Memory growth: bench_memory.py and bench_memory_pyodide.mjs

Do long or big runs hold more and more memory? Each scenario repeats one
kind of long-running work (a block, a pair of web lab map frames, a whole
short simulation, a Reset) and samples memory after a warm-up. Memory should
stay flat.

```bash
uv run python benchmarks/bench_memory.py list
uv run python benchmarks/bench_memory.py run                    # all, ~15 min
uv run python benchmarks/bench_memory.py run city lab-reset --scale 4
uv run python benchmarks/bench_memory.py run toronto --no-trace --steps 20000
node --expose-gc benchmarks/bench_memory_pyodide.mjs            # all, ~5 min
node --expose-gc benchmarks/bench_memory_pyodide.mjs reset --via-module
```

`bench_memory.py` (CPython) reports tracemalloc's traced bytes (the leak
signal), RSS and the collector's object count, a least-squares slope per
block, and the source lines that grew most. The verdict is GROWING when the
slope is above 10 B/block (10 MB per million blocks) and the fitted growth
stands clear of the samples' scatter; trip counts and the completion history
wander from block to block, so short runs of big cities are noisy.

`bench_memory_pyodide.mjs` runs worker.py in Pyodide under Node, with the
same proxy calls as webworker.js, and reports the WebAssembly heap (it never
shrinks, so steady steps up mean a leak), Python's traced bytes and object
count inside Pyodide, and the JS heap. It needs the local Pyodide copy
(`docs/lab/pyodide/`) and a wheel in `docs/lab/dist/` built from the same
source as `docs/lab/worker.py` (`./build.sh`). Each frame yields to the event
loop, as the browser worker does; `--sync` never yields. `--via-module`
reproduces webworker.js's access to the simulation before 2026-10-28.

`test/test_memory_growth.py` keeps the cheap checks in the test suite.

## Adding a benchmark

Put a `bench_<area>.py` script here, importing `harness` for scenarios and
timing. Add new reusable scenarios to `harness.SCENARIOS`. Keep each script
runnable as a CLI with `--json` output, and add a line to the results log
above when a change is measured.
