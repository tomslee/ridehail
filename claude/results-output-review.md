# Results output review (2026-10-15)

A review of the end-of-run results: `RideHailSimulationResults`
(`ridehail/results.py`) and everything that consumes it. Prompted by
`forward_dispatch_fraction` being reported without advanced dispatch (fixed
in `get_end_state`, 2026-10-15). The principle: report a result only where
it is relevant, and group results the way the config file groups the
settings that make them relevant (`use_strategy` -> `[STRATEGY]` -> the
`strategy` section).

Status: implemented 2026-10-15 (section 8). Decisions taken: strategy keys
renamed to match the fleet's; no equilibration section for now;
`fraction_parked` hidden when no car can park; the request rate per minute
under city scale (as `base_demand`).

## 1. The output paths

There are four presentations of the same end-of-run numbers, built along
two separate selection paths:

| Output | Built from | Selection / layout defined in |
| --- | --- | --- |
| Screen table (`-a text`) | `get_end_state()` | `results.py` (dict literal) |
| JSONL `end_state` record, sequence CSV row (`-o`) | `get_end_state()` (CSV via `flatten_end_state`) | `results.py` |
| `[RESULTS]` in the config file (Python) | `get_result_measures()` + `STRATEGY` | `config.py::_format_results_section` key lists |
| `[RESULTS]` in a web lab download | `worker.py::get_simulation_results` -> `get_result_measures()` | `docs/lab/js/config-file.js::formatResultsSection` key lists |

Other consumers of `get_end_state()`: `sequence.py::_collect_sim_results`,
`terminal_sequence.py::_collect_sim_results`, `sequence.py` strategy points
(via `get_result_measures`). Per-block frames (`worker.py` `FRAME_SETTINGS`
+ every `Measure`) are live measures, not end-of-run results, but share
`compute_measures()`, so the units findings (section 3) reach them too.

So the selection of results is written three times (end_state literal,
Python key lists, JS key lists) and they have drifted.

## 2. Consistency between the outputs

| # | Finding | Where |
| --- | --- | --- |
| 2.1 | `TRIP_FORWARD_DISPATCH_FRACTION` is always written to `[RESULTS]` (as `0.000`) whatever the dispatch method: `compute_measures` initialises every Measure to 0, and both writers print every listed key that is present. Same bug as the one just fixed, in the other path. | `config.py` trip_keys, `config-file.js` tripKeys |
| 2.2 | Web `[RESULTS]` omits `VEHICLE_FRACTION_PARKED`, the whole income section, and `STRATEGY_*` (the worker never adds the strategy summary). | `config-file.js`, `worker.py:776` |
| 2.3 | Section comments differ between Python and web (`# Vehicle metrics` vs `# Vehicle metrics (averaged over results window)`, different validation comment, Python's units comment for income absent on the web). | both writers |
| 2.4 | Order differs: end_state lists trips as wait, wait fraction, ride; `[RESULTS]` as ride, wait. Validation: end_state puts the residual first, `[RESULTS]` last. | `results.py`, `config.py` |
| 2.5 | Rounding differs: `max_rms_residual` 4 places on screen, 3 in `[RESULTS]`. `median_wait_time` is an int on screen (`7`), `7.000` in `[RESULTS]`. | |
| 2.6 | Naming: strategy keys differ from the fleet's for the same quantity (`p1` vs `fraction_p1`, `surplus` vs `vehicle_mean_surplus`, `gross_income` vs `vehicle_gross_income`), on screen and as `STRATEGY_P1` vs `VEHICLE_FRACTION_P1` in `[RESULTS]`. The point of the strategy section is comparison with the fleet, so the names should match. | `game/strategy.py::summary`, `CarLedger.measures` |
| 2.7 | Results availability rules differ: end_state is `{}` unless `block_index > results_window` (and `None` at block 0); the worker returns `{}` unless `block_index >= results_window`; the Python `[RESULTS]` writer has no threshold at all. The end_state warning names `smoothing_window` but tests `results_window`. | `results.py:282`, `worker.py:798`, `simulation_runner.py:23` |

## 3. Units (city scale) - real bugs, latent at `minutes_per_block = 1`

Every preset and the game use `minutes_per_block = 1.0`, which hides these.
Reproduced with `test/city_scale.config` and `minutes_per_block = 2.0`.

| # | Finding |
| --- | --- |
| 3.1 | `TRIP_MEAN_WAIT_TIME` and `TRIP_MEAN_RIDE_TIME` are converted with `PER_BLOCK -> PER_MINUTE`, a *rate* conversion (divides by `minutes_per_block`). They are durations and need `BLOCK -> MINUTE` (multiplies). With mpb = 2 they come out 4x too small. (`measures.py:151-160`.) Affects the screen, `[RESULTS]`, and the web lab's live trip chart and What If? bars. |
| 3.2 | `TRIP_MEDIAN_WAIT_TIME` is not converted at all, so mean and median are in different units (run above: mean 2.319 "minutes", median 3 blocks). |
| 3.3 | `TRIP_MEAN_REQUEST_RATE` is not converted: it is per block while the config's `base_demand` (and `display_base_demand`) is per minute under city scale. Run above: `base_demand = 135` per minute, `mean_request_rate = 270`. |
| 3.4 | Because of 3.1 and 3.3, `check_np3_over_rl` and `check_np2_over_rw` mix units under city scale and read ~mpb instead of ~1 (run above: 1.991, 2.068). The checks should be computed in blocks, before any conversion. |
| 3.5 | `terminal_sequence.py:93` divides `mean_ride_time` (minutes under city scale) by `city_size` (blocks). `TRIP_DISTANCE_FRACTION` already is this ratio, computed in blocks. |
| 3.6 | `PLATFORM_MEAN_INCOME` is the platform's total income per block (or hour), while the vehicle incomes are per vehicle. Run above: `platform_mean_income 28210.475` next to `vehicle_gross_income 12.089`. Correct, but nothing says so: needs a name or a label that says "total". |
| 3.7 | No output states its units except the `[RESULTS]` income comment ("INCOME per hour, PRICE per minute"), which leaves out that wait and ride times are in minutes too. The screen table has no units. |

## 4. Relevance (completeness the other way: what is missing or extra)

Mapping results onto the config sections that make them relevant:

| Config | Result | Today | Proposal |
| --- | --- | --- | --- |
| `use_advanced_dispatch` + `dispatch_method = forward` | forward dispatch fraction | end_state gated (fixed); `[RESULTS]` always | gate everywhere (2.1) |
| `use_strategy` / `[STRATEGY]` | strategy section | end_state + Python `[RESULTS]`; not web | consistent (web has no strategy, so only the Python side matters) |
| `max_wait_time` set | `TRIP_COMPLETED_FRACTION` (share not cancelled) | **computed, never reported** | add to trips when `max_wait_time` is set |
| `idle_vehicles_moving < 1` (or strategy `park`) | `fraction_parked` | always reported (0.0 when no car can park) | report only when parking is possible? (question 3) |
| `use_city_scale` / `[CITY_SCALE]` | units of the times, rates, incomes | no indication | units in the labels (3.7) |
| `equilibration != none` / `[EQUILIBRATION]` | what the equilibration settled on (final fleet size for supply, price for price) | only implicitly (`mean_count`, `trip_mean_price`) | see question 2 |
| `platform_commission = 0` | `platform_mean_income` | always (0.0) | keep: income section is always meaningful (price and costs always exist; see memory on price/wage sections) |

## 5. Dead and stale code

- `RideHailSimulationResults.__init__` builds `self.results["config"] =
  self.get_current_config()`, which nothing reads (checked Python, web, and
  tests). `get_current_config` is itself out of step with the config sections:
  `base_demand` both top-level and under equilibration, `price` and
  `platform_commission` only when equilibrating, `request_rate` (internal
  units) outside any section, and many settings missing
  (`inhomogeneous_destinations`, `trip_distance_distribution`, `pickup_time`,
  `per_block_ops_cost`, `random_number_seed`, `use_strategy` and `[STRATEGY]`,
  `base_fare`, `wait_fraction`, the sequence settings). The JSONL output
  already writes the full config via `WritableConfig`. Recommend deleting it.
- Stale text: "Phase 1 enhancement" (`results.py`, `simulation_runner.py`),
  "hieratchy", "Cnfig"; `text.py`'s docstrings say it prints JSON (it prints a
  table).
- `text.py` iterates `end_state`, which is `None` at block 0 (e.g. quit before
  the first block) - TypeError.
- `sequence.py` and `terminal_sequence.py` index `end_state["vehicles"]`,
  which is `{}` when `time_blocks <= results_window` - KeyError.
- Cosmetic: the per-block line is ~95 characters; `rich.print` wraps it at
  80 columns when stdout is not a wide terminal, so `rmsr=` lands on the next
  line and the in-place `\r` update breaks.

## 6. Proposed plan

The root cause of section 2 is three hand-kept lists. So, structurally:

**Step A - one declarative layout (results.py).** A single table of sections,
each with a relevance predicate on the sim and its rows (end-state key,
Measure, decimals, unit). `get_end_state()` builds from it. Sections follow
the config sections: `simulation`, `vehicles`, `trips`, `income_and_costs`,
`validation`, plus gated `dispatch` (forward dispatch fraction, gated on
`ADVANCED_DISPATCH`), `strategy` (gated on `use_strategy`). Units come from
the layout (one place for 3.7).

**Step B - `[RESULTS]` from the same layout.** `_format_results_section`
walks the layout instead of its own key lists, keeping the Measure-name keys
(`VEHICLE_FRACTION_P1 = ...`) so existing files still parse, one comment per
section with units. Strategy rows as now (`STRATEGY_*`), renamed per 2.6.

**Step C - web uses Python's formatter.** `worker.get_simulation_results`
returns the formatted `[RESULTS]` text (or the layout-ordered dict) from
Python, and `formatResultsSection` in `config-file.js` goes. Same pattern as
presets (Python is the single source, the web reads it). Fixes 2.2, 2.3.

**Step D - units (section 3).** Durations with `BLOCK -> MINUTE`, convert the
median wait and the request rate, compute the validation checks in blocks,
use `TRIP_DISTANCE_FRACTION` in `terminal_sequence.py`, label the platform
income as a total. Changes live web numbers only when mpb != 1.

**Step E - relevance additions/removals (section 4)** and the one shared
availability rule (2.7), and guards for empty end states.

**Step F - delete `get_current_config`, fix stale text.**

**Tests**: a test that the screen, `[RESULTS]` and web outputs list the same
keys for a plain run, a forward-dispatch run, a strategy run, a city-scale
run; a units test at `minutes_per_block = 2` (validation checks ~1, mean and
median wait in the same units). Regression baselines (`test/*.config`
`[RESULTS]`) need re-recording wherever keys are added or removed
(`TRIP_FORWARD_DISPATCH_FRACTION` disappears from all four) - the
regression test treats missing/extra keys as failures.

Order: D first (real bugs, small, independent), then A-C together, then E, F.

## 7. Questions for the user

1. **Renaming**: matching the strategy keys to the fleet's (2.6) and adding
   a `dispatch` section change the sequence CSV column names. Acceptable?
2. **Equilibration**: add an `equilibration` section (e.g. final vehicle
   count / price against the starting values) when equilibrating, or leave
   `mean_count` and `trip_mean_price` to carry it?
3. **Parked**: hide `fraction_parked` when no car can park
   (`idle_vehicles_moving = 1` and no strategy `park`), or always show it?
4. **Request rate under city scale**: per minute (matching `base_demand`) or
   per hour (matching the incomes)?

## 8. Implementation (2026-10-15)

- `ridehail/results.py`: `RESULTS_LAYOUT` (sections of `ResultRow`s, with
  units and relevance predicates) is the one source. `sections()` gives the
  relevant rows; `get_end_state()` and `format_results_section()` are built
  from it; `available()` is the one availability rule (`block_index >
  results_window`). `get_current_config` and `self.results` deleted.
- End-state sections: `simulation`, `vehicles`, `trips`, `dispatch` (forward
  dispatch only), `income_and_costs`, `validation`, `strategy`
  (use_strategy only). Renamed keys: `income_and_costs` `gross_income`,
  `net_income`, `surplus`, `mean_price`, `platform_total_income`
  (`[RESULTS]`: `PLATFORM_TOTAL_INCOME`); strategy `fraction_p1..3`
  (`STRATEGY_FRACTION_P1..3`). New: `trips.completed_fraction` with
  `max_wait_time`. `vehicles.fraction_parked` and
  `strategy.fraction_parked` only when some car can park.
- `[RESULTS]`: Measure-name keys as before; one comment per section, with
  units. `config.write_results_section` now takes the text;
  `_format_results_section` deleted.
- Web: `worker.get_simulation_results()` returns the `[RESULTS]` text;
  `formatResultsSection` deleted from `config-file.js`. Needs a wheel
  rebuild and a manual check of a config download.
- Units (`measures.py`): durations `BLOCK -> MINUTE` (mean wait, mean ride,
  median wait), request rate `PER_BLOCK -> PER_MINUTE`. The checks need no
  change: the units cancel. matplotlib's stats title labels the rate.
- Text table has a Units column; the per-block line uses plain `print`.
- `terminal_sequence.py` uses `TRIP_DISTANCE_FRACTION`.
- Tests: `test/test_results_output.py`; regression baselines re-recorded
  (only `TRIP_FORWARD_DISPATCH_FRACTION` had changed; values matched).

Not done / left alone:

- The What If? measures table (`whatif.js::fillWhatIfMeasuresTable`) lists
  every Measure of the live frame (smoothing_window), not end-of-run results,
  so it is outside this layout. It still shows irrelevant measures
  (`TRIP_FORWARD_DISPATCH_FRACTION`, `VEHICLE_FRACTION_PARKED`, ...) under
  raw Measure names. The unit fixes change its times and request rate when
  minutes_per_block is not 1.
- The Measure is still named `PLATFORM_MEAN_INCOME` (live frames, web
  charts); only the results call it a total.
- `plot/rhplotsequence.py` reads an older flat JSONL format
  (`vehicle_fraction_p1`, ...) and was already out of date.
