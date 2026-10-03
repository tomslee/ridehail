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

## Adding a benchmark

Put a `bench_<area>.py` script here, importing `harness` for scenarios and
timing. Add new reusable scenarios to `harness.SCENARIOS`. Keep each script
runnable as a CLI with `--json` output, and add a line to the results log
above when a change is measured.
