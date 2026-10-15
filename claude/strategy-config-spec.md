# [STRATEGY] configuration section: one car, one strategy

Status: **option A implemented 2026-10-15** on the `strategy` branch.
`use_strategy` seats one car in an ordinary simulation and has it play an
explicit strategy (an offer rule and an idle rule). The car is measured
with the core's own formulas, over the core's own results window, so its
results compare directly with the fleet's `vehicles` and `income_and_costs`
sections of the end state.

History.

- **2026-10-10:** designed to run the game's research scans
  (`claude/game-environment-scan.md`, `claude/game-mode.md` Part 17) from
  the command line.
- **2026-10-11:** narrowed from several seats (the game's bots, threshold
  ranges) to a single car with a single strategy. Strategies are compared
  by running once per strategy; multi-seat scans stay in
  `utils/game_environment_scan.py`.
- **2026-10-12:** the `offer/idle` spec split into `strategy_offer` and
  `strategy_idle`; settings and redundant measures taken out of the
  results.
- **2026-10-12, paused:** the car kept its own books (the game's ledgers,
  `strategy_ops_cost`, `offer_model` pricing), whose results differed in
  subtle ways from the core's. The options were A (measure the car the
  core's way), B (separate running cost from the reservation wage in the
  core), C (keep the game's accounting, labelled as such) and D (drop it).
- **2026-10-15:** B done on `dev` (`claude/running-cost-spec.md`), merged
  here, then A: the ledgers, `strategy_ops_cost`, `strategy_pricing`
  (`offer_model`), `MIN_FLEET_SHARE` and `fleet_net_rate` removed. The
  game's upfront offers (the `offer_study` fits) are left out for now; see
  section 10.
- **2026-10-15, later:** generic upfront pricing, `offer_variability`
  (`claude/upfront-pricing-spec.md`): each trip's offer is the rate card
  times a lognormal factor with mean 1, whose log spread (0.31) is the one
  part of the Toronto offer fit with no units.

## 1. What it does

- One car, drawn at random from the fleet (part of `vehicle_count`), takes
  or declines each offer dispatch makes it by its strategy. It plays by the
  game's rules: one offer a block, and a declined trip waits for the next
  block (`DEFER`, game-mode.md 10.5); it is not offered that trip again.
  Every other car takes every offer.
- **The shift is the last `results_window` blocks**, the blocks the core
  results are averaged over. The car is drawn at random from the fleet when
  the shift starts, busy or idle, as the game seats its player and bots; a
  trip under way is paid for its blocks in the shift. (Until 2026-10-15 the
  car was logged off before the shift and started it idle. The game found
  that such cars drift undispatched towards the City Centre and start about
  $1/hr ahead of the fleet: `claude/game-environment-scan.md`, "Follow-up".)
- The seated car is never removed when the fleet shrinks
  (`RideHailSimulation.protected_vehicles`, used by `_remove_vehicles`).
- Over the shift the car's blocks are counted as the core's history counts
  the fleet's: each block's phase after the block, and whether the car
  stayed parked while idle (`Vehicle.parked`).

## 2. Parameters

| Name | Section | Short | Type | Default | Meaning |
|---|---|---|---|---|---|
| `use_strategy` | DEFAULT | `-us` | bool | False | Seat one car with the strategy and report it. |
| `strategy_offer` | STRATEGY | `-so` | rule (section 3) | `all` | Which offers the car takes: `all`, `rate:N` or `centre`. Stored in canonical form. |
| `strategy_idle` | STRATEGY | `-si` | rule (section 3) | `cruise` | What the car does while idle: `cruise`, `park` or `moving:P`. Stored in canonical form. |
| `offer_variability` | STRATEGY | `-sov` | float, 0 to 2 | 0 | Upfront pricing: the log spread of offers around the rate card (`claude/upfront-pricing-spec.md`). 0 is the flat fare; 0.31 matches the offer study. |

Money comes from the core's parameters: `price` or the City-scale fares,
`platform_commission`, the running cost (`per_block_ops_cost`, or
`per_km_ops_cost` with `use_city_scale`) and the reservation wage.

Companion `[SEQUENCE]` items (general, not strategy-specific):

| Name | Short | Type | Default | Meaning |
|---|---|---|---|---|
| `request_rate_values` | `-srv` | number list | none | An explicit demand list (`100,130,160`), instead of `base_demand`…`request_rate_max` by `request_rate_increment`. |
| `sequence_repeats` | `-sr` | int ≥ 1 | 1 | Runs per point; with `random_number_seed` set, repeat k uses seed + k. Repeats are the outer loop. Animated sequences ignore it. |

## 3. Rules

Rule names take a unique prefix (`-so r:22 -si p`); the rules and their
descriptions are `OfferRule` and `IdleRule` in `ridehail/atom.py`, so
`ridehail -h strategy_offer` and `ridehail -h strategy_idle` list them. A
rule with a value (`rate`, `moving`) takes it after a colon.

| Parameter | Rule | Meaning |
|---|---|---|
| `strategy_offer` | `all` | take every offer |
| `strategy_offer` | `rate:N` | take offers paying at least N per hour (City scale) or per block (Simple), pickup included |
| `strategy_offer` | `centre` | take offers whose drop-off is in the City Centre (`City.core_bounds()`) |
| `strategy_idle` | `cruise` | the fleet's idle behaviour (default) |
| `strategy_idle` | `park` | never move while idle |
| `strategy_idle` | `moving:P` | move in a fraction P of idle blocks |

An idle rule other than `cruise` sets the car's own
`Vehicle.idle_vehicles_moving` when the shift starts.

## 4. Offers and income: the core's formulas

- **Offer** for a trip: `price × (1 − platform_commission) × trip blocks`,
  the core's per-block fare (with `use_city_scale`, `price` is the per-block
  price built from the per-km and per-minute fares and the base fare spread
  over the mean trip), times the trip's upfront-pricing factor `m` (1 when
  `offer_variability` is 0). Pickups are unpaid, so the offer's rate, over
  pickup and trip, varies with the pickup's share.
- **Income**, per block, from the car's own shares of the shift (`p3`, and
  `z` = blocks parked while idle):
  - gross = the car's earnings over the shift's blocks, where it earns
    `price × (1 − commission) × m` in each block with a rider; with no
    variability, `price × (1 − commission) × p3`
  - net = gross − `ops_cost × (1 − z)`
  - surplus = net − `reservation_wage`
- With `use_city_scale`, incomes and offer rates are per hour, and
  `idle_per_accept` is in minutes; otherwise per block and in blocks.

With no offer variability these are exactly the end state's formulas for
the fleet (`ridehail/measures.py`), so a car that takes every offer and
cruises measures, on average, like the fleet
(`test_take_every_offer_matches_the_fleet`). With variability it still does
on average, since the factor averages 1: over 24 seeds in the game city, a
take-every-offer car netted $9.42/hr (± 0.50) with flat fares and $9.45/hr
(± 0.68) with σ = 0.31, against the fleet's $9.17/hr.

## 5. Presets

`--preset game` (32 blocks, 215 cars, demand 9) and `--preset game-big` (48
blocks, 6000 cars, demand 240), command line only (the web lab keeps
`PRESET_NAMES`). They set the game's environment (GAMMA trips, mean 16,
inhomogeneity 0.5, idle moving 0.5 / returning 0.25, max wait 10, pickup
time 1, equilibration none, `time_blocks` 240, `results_window` 180) in
City-scale mode (1 minute and 22.2 km/h per block, `per_km_ops_cost` 0.56,
`demand_elasticity` 0), with `use_strategy` on. The fare is the game's
driver rate card (base $2.50, $0.75/km, $0.18/min) with no commission, so
a driver is paid the rate card for the trip, and `offer_variability` is
0.31, so offers vary around it as Toronto offers do. The game's own fitted
offer curve is not used. The strategy is left at its defaults: set it with `-so` and
`-si`. Markets are demand: `-bd 11` (or 330 in `game-big`) is Busy.
`game_preset()` builds the values from `ridehail/game/market.py` and
`GameParams`, so the presets can't drift from the game.

City-scale mode leaves the game's city unchanged (one minute per block, no
elasticity): `test_city_scale_leaves_the_game_city_unchanged`.

## 6. Validation

Errors with `use_strategy`: equilibration other than `none`; a dispatch
method other than the default (`offer_filter` support); a `time_blocks`
that is set but not above `results_window`; fewer than
2 vehicles; an offer or idle rule that doesn't parse (the message says
why).

`time_blocks = 0` (an open-ended run) is allowed: the shift starts at
block 0 and lasts the whole run. Impulses and keyboard changes to the fleet
size are allowed too: the seated car is never removed, and the fleet's
figures follow the fleet (both since 2026-10-15).

## 7. Outputs

`StrategyController.summary()` is a flat dict of the car's results:
`p1`/`p2`/`p3` and `fraction_parked` (shares of its shift), `gross_income`,
`net_income`, `surplus`, `offers`, `accepts`, `idle_per_accept`. Numbers
are rounded to 3 places; a measure with nothing to measure is None.

There is no separate fleet section in the end state: the fleet is the end
state's `vehicles` and `income_and_costs` sections, over the same blocks.
They include the seated car, one of `vehicle_count`. For live displays,
`StrategyController.fleet_summary()` gives the same figures over the shift
so far (the car's blocks), from the controller's own tallies (`Tally`); at
the end of a `results_window` shift they equal the end state's. The
controller also keeps `offer_log` (each offer's rate, decision and drop-off
zone) and `net_series` (the car's and fleet's net income after each
block); `ridehail/strategy_display.py` bins the offers
(`offer_histogram()`).

The summary is the **`strategy` section of the end state**, so it reaches
the existing outputs without separate files:

- the text animation's end-state table;
- the jsonl `end_state` record (`-o`);
- the sequence CSV (`-o`), flattened into `strategy_*` columns, one row per
  run;
- `[RESULTS]` in the config file: `STRATEGY_<KEY> = value` lines;
- with `-a none`: a comparison with the fleet (`format_summary`: gross,
  net, surplus, acceptance, idle per trip, P1/P2/P3) after a single run,
  and for a sequence each point's mean net income ± standard error over its
  runs, for the car and the fleet (`format_strategy_summary` in
  `sequence.py`).

`-o` also works from a preset with no config file: the files are named
after the preset (`out/game-<time>.csv`).

## 8. Examples

```bash
python -m ridehail --preset game -a none -so rate:33           # one shift
python -m ridehail --preset game -a none -s -sr 20 -rns 1 -o \
    -so centre -srv 5,7,9,11                                   # across demand
for s in all rate:25 rate:30 rate:35 centre; do                # several offer rules
  for i in cruise park; do                                     # x idle rules
    python -m ridehail --preset game -a none -s -sr 20 -rns 1 -srv 5,9,11 -so $s -si $i
  done
done
python -m ridehail -a none -us -si park -pbops 0.05 -b 400 -rw 300   # Simple mode
```

With the same `-rns`, runs of different strategies share their seeds, but
the car's decisions change dispatch, so the cities diverge after its first
decision: the comparison is paired only loosely. One car per run is noisy
(standard errors of $1.5-2/hr over 4 runs in the game city), so use plenty
of repeats.

## 9. Code

| Piece | Where |
|---|---|
| Rule parsing (`parse_offer`, `parse_idle`, `make_strategy`), `Strategy` (`offer`, `idle`, `label`, `name`, `accepts`, `apply_idle`) | `ridehail/strategy_spec.py` (depends only on `atom.py`) |
| Enums | `OfferRule`, `IdleRule` in `ridehail/atom.py` |
| `StrategyController`, `format_summary` | `ridehail/game/strategy.py` |
| Hook | `RideHailSimulation._set_strategy_controller()`; `next_block()` calls `before_block()` after `_init_block` and `after_block()` after `_collect_garbage`; `_restart_simulation()` reseats |
| Config | `config.py`: `use_strategy`, `[STRATEGY]` items, `_strategy_errors()`, `FloatList`, `request_rate_values`, `sequence_repeats` |
| Outputs | `results.py` (end-state section), `simulation_runner.py` (`[RESULTS]`), `__main__.py` / `run.py` (summary), `sequence.py` (`runs()`, summary) |
| Tests | `test/test_strategy.py` |

`ridehail/game/shift.py` (`Ledger`, `ShiftBase`) is now the game's own
bookkeeping (`GameController`); the strategy no longer uses it. The game's
bots are individual strategies (`ridehail/game/bots.py`: `Bot` holds a
`strategy_offer` rule and takes its name from `Strategy.name()`), and both
use `City.zone()` for the City Centre rule.

## 10. Open questions

1. **Upfront offers in the core.** `offer_variability` prices every trip,
   but only the seated car's income uses the prices; the fleet's is the
   core's expected income. Moving it to the core would let the fleet's
   results (and the web lab) use actual prices too. The variation is
   independent noise: offers that depend on time, surge or place are not
   modelled.
2. **Move the game itself to City-scale mode?** It would remove the game's
   private `KM_PER_BLOCK` units; the city is unchanged (section 5).
3. Possible later idle rules (Part 16): `returning:P`, and driving to a
   place to wait (`edge`, `middle`), which need the `Vehicle.idle_target`
   hook rebuilt.
4. The fleet figures include the seated car. With small fleets, a fleet
   excluding it might be wanted.
