# Advanced Dispatch / Forward Dispatch: Spec and Test Plan (2026-10-03)

Status: spec written, defects found and fixed, unit tests in
`test/test_forward_dispatch.py`. Behavioural (economic) validation is still
open; see "Open questions" at the end.

## 1. Parameters

| Parameter | Section | Type / default | Meaning |
| --- | --- | --- | --- |
| `use_advanced_dispatch` (`-uad`) | DEFAULT | bool, False | Master switch. When False the simulation uses `default` dispatch, whatever `dispatch_method` says. |
| `dispatch_method` (`-dm`) | ADVANCED_DISPATCH | `DispatchMethod`, `default` | `default`, `forward_dispatch`, `p1_legacy`, `random` |
| `forward_dispatch_bias` (`-fdb`) | ADVANCED_DISPATCH | int >= 0, 0 | Blocks added to a P1 vehicle's dispatch distance under forward dispatch, so a larger value favours engaged (P3) vehicles. |

### Gating rules

- G1. Config file: the ADVANCED_DISPATCH section is read only when
  `use_advanced_dispatch = True`.
- G2. Whatever the source (config file, `-dm` on the CLI, preset,
  programmatic config), the dispatch method **in effect** is
  `dispatch_method` if `use_advanced_dispatch` is True, otherwise `default`.
  (`RideHailSimulation.__init__` enforces this.)
- G3. `forward_dispatch_bias` < 0 is invalid (`min_value=0`; as with other
  config-file values, a warning is logged and the default 0 used). A negative bias
  could push a P1 vehicle's effective distance to <= 0, and dispatch treats
  that as "not a candidate", so nearby idle vehicles would never be sent.
- G4. Results: `config.advanced_dispatch` is written only when
  `use_advanced_dispatch`; `end_state.trips.forward_dispatch_fraction` is
  always written (0 unless forward dispatch is in effect).

## 2. Forward dispatch behaviour

Each block, after trip requests, the unassigned trips are shuffled and
dispatched one at a time (greedy, as in `default`).

- F1. **Pool.** Dispatchable vehicles are all P1 vehicles plus P3 vehicles
  that do not already hold a forward-dispatch trip. P2 vehicles are never
  dispatchable. A P3 vehicle holds at most one forward trip.
- F2. **Effective distance** from vehicle to trip origin O:
  - P1: `d(location, O) + forward_dispatch_bias`, excluded if
    `d(location, O) == 0` (the existing "minimum dispatch distance is 1"
    rule).
  - P3: `d(location, dropoff) + d(dropoff, O)`. This is always > 0 for a P3
    vehicle (it would already have dropped off if location == dropoff), so
    a P3 vehicle standing on O is still a candidate.
  - `d` is torus Manhattan distance; its maximum is `city_size`.
- F3. **Choice.** The trip goes to the vehicle with the smallest effective
  distance; ties are broken uniformly at random, and each vehicle counts
  once.
- F4. **Search completeness.** If any vehicle is in the pool, the trip is
  dispatched, including when the only vehicle is antipodal (distance
  `city_size`).
- F5. **Assignment to P1.** As in default: trip goes UNASSIGNED to WAITING and
  the vehicle goes P1 to P2.
- F6. **Assignment to P3.** The trip goes to WAITING with
  `trip.forward_dispatch = True`. The vehicle stays P3 with
  `forward_dispatch_trip_index`, `_pickup_location` and `_dropoff_location`
  set, and `vehicle.forward_dispatches` is incremented. The vehicle leaves
  the pool for the rest of the block.
- F7. **Handover.** When a P3 vehicle holding a forward trip reaches its
  dropoff, the current trip is COMPLETED and the vehicle goes **directly to
  P2** for the forward trip (no P1 block). Its `trip_index`, pickup and
  dropoff become those of the forward trip, and the forward fields are
  cleared. This must work for **every** trip index, including 0.
- F8. **Wait accounting.** A forward-dispatched trip is in WAITING from
  assignment until pickup, so the rest of the current ride counts as wait
  time. Forward trips are never cancelled by `max_wait_time`, because only
  UNASSIGNED trips are.
- F9. **Measure.** `TRIP_FORWARD_DISPATCH_FRACTION` is the number of completed
  trips with `forward_dispatch = True` divided by the number of completed
  trips, over the results window.
- F10. **Bias limits.** With bias 0 and no P3 vehicle closer than the nearest
  P1, behaviour matches nearest-vehicle dispatch. As bias grows, the share
  of forward dispatches rises towards 1 in an oversupplied market.
- F11. **Live change.** Changing `dispatch_method` or `forward_dispatch_bias`
  through `target_state` (impulses) takes effect at the next block. Switching
  away from forward dispatch mid-run lets vehicles that already hold forward
  trips complete them normally.
- F12. Forward dispatch does not support `offer_filter` or `offline` (game
  mode), and the game forces `default`.

### Invariants (must hold after every block, any method)

- I1. No trip index is held by two vehicles (`trip_index` or
  `forward_dispatch_trip_index`).
- I2. Every WAITING or RIDING trip is held by exactly one vehicle.
- I3. `forward_dispatch_trip_index` is set only on P3 vehicles.
- I4. A vehicle in P2/P3 has a `trip_index`; a P1 vehicle has none.

## 3. Defects found (2026-10-03) and fixes

| # | Defect | Effect | Fix |
| --- | --- | --- | --- |
| D1 | `--no-use_advanced_dispatch` (or `-dm` without `-uad`) left `dispatch_method` in force | G2 violated: forward dispatch ran when switched off | `RideHailSimulation.__init__` forces DEFAULT unless `use_advanced_dispatch` |
| D2 | `Vehicle.update_phase` tested `if not self.forward_dispatch_trip_index` | Trip index 0 forward-dispatched: vehicle went P1 and trip 0 was left WAITING for ever (breaks I2) | `is None` / `is not None` |
| D3 | `City.dispatch_distance` returned 0 when `location == origin` before checking phase | P3 vehicle standing on the origin was never a candidate | zero shortcut applies to P1 only |
| D4 | Ring search covered distances `0..city_size-1` | Antipodal vehicle never found (F4); forward has no sparse fallback | search `0..city_size` (forward and dense default) |
| D5 | Location grid stored `vehicle.index` and looked it up as `vehicles[index]`, but `_remove_vehicles` (equilibration, `vehicle_count` changes) keeps indexes while compacting the list | **Affects default too.** After any fleet shrink, dense dispatch sent a non-nearest vehicle ~95% of the time (measured); forward dispatch "dispatched" P2 vehicles, leaving trips WAITING with no vehicle and logging "dispatched vehicle not in list(s)" | grid stores vehicle objects; positions no longer matter |
| D6 | Forward search added candidates without checking pool membership, and could add one vehicle twice at ring distances > city_size/2 | Biased tie-breaks; non-dispatchable vehicles chosen (with D5) | O(1) pool-set check before scoring; each vehicle scored once |
| D7 | Negative `forward_dispatch_bias` accepted | Nearby P1 vehicles undispatchable | `min_value=0` |
| D8 | `_dispatcher` built once in `__init__` | Live/impulse changes of method/bias ignored (F11) | rebuilt in `_init_block` when either changes |

Not fixed (noted):

- After `_remove_vehicles`, new vehicles get `index = len(vehicles) + d`, so
  vehicle indexes can be duplicated. Dispatch no longer depends on them. Game
  mode keys on `vehicle.index` but runs a fixed fleet.
- `-dm` on the CLI needs the exact enum value (`forward_dispatch`), but the
  config file accepts a 2-character prefix.
- `docs/configuration/parameters.md` / `examples.md` list obsolete method
  names (`IMMEDIATE_BATCH_NEAREST`, ...).
- Forward dispatch has no sparse fallback, so it is slower than default
  with few dispatchable vehicles and large cities (performance only).

## 4. Test plan

Unit tests (`test/test_forward_dispatch.py`, hand-built vehicles and trips,
no animation):

| Test | Covers |
| --- | --- |
| gating: config file with/without `use_advanced_dispatch`; CLI `--no-use_advanced_dispatch`; programmatic | G1, G2, D1 |
| negative bias rejected (falls back to 0) | G3, D7 |
| P1 nearer than P3 (bias 0) -> P1 chosen | F2, F3 |
| P3 effective distance < P1 -> P3 chosen; trip WAITING + flagged; vehicle stays P3 | F6 |
| bias tips the choice to P3 | F2, F10 |
| P2 vehicle never chosen; P3 already holding a forward trip never chosen | F1 |
| P3 vehicle standing on trip origin is a candidate | F2, D3 |
| antipodal-only vehicle is dispatched (forward and default) | F4, D4 |
| handover to P2 at dropoff, including trip index 0 | F7, D2 |
| full lifecycle in a running sim: forward trip completes, counted in fraction | F7-F9 |
| invariants I1-I4 over seeded runs: under/over-supplied, bias 0/2/10, pickup_time 0/2, fleet shrink and grow mid-run, equilibration | I1-I4, D5, D6 |
| fleet shrink: dense default still picks the nearest vehicle | D5 |
| live change of method via target_state | F11, D8 |
| default-method regression digests unchanged (existing `test_dispatch_offer_filter.py`) | no collateral change |

Behavioural checks (exploratory, not asserted; record in this file):

- B1. Oversupplied city: forward fraction rises monotonically with bias.
- B2. Undersupplied (P1 ~ 0): nearly all trips are forward dispatched.
  Compare P2 fraction and mean wait with default.
- B3. Equilibrating runs (`equilibration = price`) with forward dispatch reach
  a steady state.

## 5. Open questions for the user

- Q1. Should forward dispatch keep greedy *per-trip* matching in random
  order (current behaviour), or should a trip prefer a P1 vehicle within
  some absolute distance before considering P3 vehicles?
- Q2. Should the wait time of a forward-dispatched trip include the rest of
  the current ride (current behaviour, F8)? It seems right from the rider's
  point of view.
- Q3. Expose forward dispatch in the web lab? Not exposed today.

## 6. Behavioural results (2026-10-03, after fixes)

All runs are 600 blocks (1500 for B3), seed 11; fractions are over the
results window. Script: the `make_sim` helper in
`test/test_forward_dispatch.py`.

B1, oversupplied (city 24, 200 vehicles, demand 6):

| dispatch | P1 | P2 | P3 | mean wait | forward fraction |
| --- | --- | --- | --- | --- | --- |
| default | 0.554 | 0.083 | 0.363 | 2.55 | 0 |
| forward, bias 0 | 0.556 | 0.075 | 0.369 | 2.47 | 0.016 |
| forward, bias 1 | 0.557 | 0.075 | 0.368 | 2.60 | 0.087 |
| forward, bias 2 | 0.569 | 0.073 | 0.358 | 2.81 | 0.203 |
| forward, bias 4 | 0.546 | 0.084 | 0.369 | 3.97 | 0.517 |
| forward, bias 8 | 0.495 | 0.129 | 0.376 | 7.25 | 0.858 |

The forward fraction rises monotonically with bias (B1 holds). At bias 0,
forward dispatch is roughly neutral: it slightly cuts P2 time and wait.
Larger biases trade rider wait for fewer idle-to-pickup moves, and above
about 2 the wait cost dominates.

B2, undersupplied (city 16, 40 vehicles, demand 4): the forward fraction is
1.000, as expected, because P1 is about 0 and every dropoff hands over to a
forward trip. The backlog grows with either method, so the wait times
(133 vs 155) are not steady-state numbers.

B3, price equilibration (city 16, demand 3, bias 2): both methods settle
(67-68 vehicles, P3 0.35-0.36, wait about 2.8), with a forward fraction of
0.24. No instability was seen.

## 7. Effect of the D5 fix on default-dispatch results

`test/test_regression.py -m regression` already had 4 of 10 failures at
HEAD (f8640ff), and the same 4 fail after these changes, so its stored
baselines are stale. Running each config under HEAD and under the fixed code
(default dispatch throughout):

| config | equilibration | HEAD: P1 / P2 / wait / fleet | fixed: P1 / P2 / wait / fleet |
| --- | --- | --- | --- |
| city_size_16_simple | none | identical | identical |
| city | wait_fraction (fleet only grows) | identical | identical |
| city_scale | price | 0.337 / 0.227 / 10.5 / 6428 | 0.437 / 0.100 / 5.0 / 6981 |
| equilibration | wait_fraction (target 0.3) | 0.717 / 0.086 / 3.84 / 85.5 | 0.222 / 0.235 / 8.66 / 61.7 |

The changes appear only where the fleet shrinks. At HEAD, the
`equilibration` run combined 72% idle vehicles with a 0.32 wait fraction,
which is the signature of non-nearest dispatch. With nearest dispatch
restored, the equilibrator reaches the wait target with about 28% fewer
vehicles. Any earlier result from an equilibrating run whose fleet shrank
(supply/price/wait_fraction equilibration, or lowering `vehicle_count` in
the web lab mid-run) was affected. The regression baselines need
re-recording (`pytest test/test_regression.py -m regression
--update-expected`) once the user accepts the change.
