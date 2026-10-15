# terminal_strategy: a live display of the seated car

Status: **spec, 2026-10-15; not yet built.** A terminal animation for the
individual strategy (`claude/strategy-config-spec.md`): how the seated car
is doing against the fleet, and the offers it sees and what it does with
them. A highlighted seated car on `terminal_map` is a later bonus
(section 8).

## 1. What it shows

One screen, three parts:

```
+-- Relative performance --------------------+-- Settings ----+
|                    gross   net  surplus    |  (ConfigPanel, |
|  Takes $30/hr...   19.52  9.71    -0.49    |   when the     |
|  Fleet (215 cars)  20.61  9.27    -0.93    |   terminal is  |
|  Car vs fleet, net: +$0.44/hr (+5%)        |   >= 100 wide) |
|  P1/P2/P3/parked  car 0.39/0.08/0.53/0.00  |                |
|                 fleet 0.18/0.26/0.56/0.00  |                |
|  Offers 52, accepted 14%, idle 17.5 min/trip                |
+-- Net income over the shift (line chart) ------------------+
|  car (cumulative)  ----    fleet (cumulative) ----          |
+-- Offers the car has seen (histogram) ---------------------+
|  offered rate ($/hr, pickup included), accepted vs declined |
|  bars, with the rate:N threshold marked                    |
+------------------------------------------------------------+
```

- **Relative performance panel** (text): the car and the fleet over the
  same blocks, gross / net / surplus in the rate unit (per hour with
  `use_city_scale`, otherwise per block), the car's lead or lag in net
  income, absolute and as a percentage, coloured by its sign, the time
  split (P1 / P2 / P3 / parked), and offers, acceptance and idle time per
  trip.
- **Net income over the shift** (plotext line chart): the cumulative net
  income per hour (or block) of the car and of the fleet, block by block.
  One car's income is noisy block to block. Cumulative figures settle as
  the shift goes on and show who is ahead, and how firmly.
- **Offers histogram** (plotext bar chart): every offer the car has seen
  this shift, binned by its rate (the offer over pickup plus trip time,
  the quantity `rate:N` tests), split into accepted and declined. For a
  `rate:N` strategy the threshold is marked, and every bar left of it is
  declined. For `centre` the split is by drop-off zone instead. With
  `offer_variability` the histogram shows the spread the strategy chooses
  from; without it, offers differ only by pickup share.

## 2. The option

- `Animation.TERMINAL_STRATEGY = "terminal_strategy"`, "terminal display of
  the seated car's performance and the offers it sees". Declared in
  `ridehail/atom.py`, built in `ridehail/animation/utils.py` with the usual
  fallback.
- It needs `use_strategy`: validation reports an error without it, rather
  than switching it on silently.
- With `-a terminal_strategy` and a game preset, `time_blocks` and
  `results_window` keep the preset's values unless the user changes them.

## 3. Shift and window for a live display

The end-of-run results keep their meaning: the shift is the last
`results_window` blocks. For a live display:

- **The car is seated from the start of the shift.** It is drawn at random
  from the fleet when the shift starts, wherever that car is (done
  2026-10-15; section 9). For an open-ended run
  (`time_blocks = 0`) the shift starts at block 0 and has no end, and the
  validation that requires `time_blocks` above `results_window` applies
  only when `time_blocks` is set.
- **The panel and the chart are cumulative over the shift so far.** The
  fleet's figures must cover the same blocks, so the controller keeps the
  fleet's block counts too: P1 / P2 / P3 / parked vehicle-blocks and the
  vehicle count, the same sums `_update_history` adds, from the shift's
  start. The fleet row then uses the core's formulas on those sums, and at
  the end of a run of `results_window` blocks it equals the end state's
  `income_and_costs`. (The end state's rolling `history_results` window is
  not used for the live view: before the window fills, it covers blocks the
  car was not on shift for.)
- The chart's series are the car's and the fleet's cumulative net income
  after each block of the shift: one number each per block, kept by the
  controller (two lists, as long as the shift).

## 4. Data the controller provides

All of it is built without Textual, so it can be tested directly:

- `StrategyController.offer_log`: one entry per offer in the shift:
  `rate`, `accepted`, `dropoff_zone`. It is a list as long as the number of
  offers (at most one a block).
- `StrategyController.fleet_counts`: the fleet's cumulative block counts
  (section 3), and `fleet_summary()`: the fleet row of the panel, from the
  core's formulas.
- `StrategyController.net_series`: the car's and the fleet's cumulative net
  income after each block.
- `strategy_display.offer_histogram(offer_log, threshold=None,
  max_bins=12)`: bin edges and accepted / declined counts. A pure function
  in a module with no Textual import, like the panel's text.

## 5. Live changes

- **Keyboard changes to the fleet** (`n` / `N` and friends) must never remove
  the seated car: `RideHailSimulation._remove_vehicles` skips it (a set of
  protected vehicle indexes the controller registers). The fleet row
  follows the fleet as it changes.
- Changes to price, commission, costs or demand take effect at once; the
  cumulative figures then mix the before and after, as a shift would.
- `r` (restart) reseats the car and clears the shift.
- Equilibration stays excluded with `use_strategy`.

## 6. Colours and layout

- Car: P3 sea green (`P3_RGB`, its with-rider colour); fleet: a neutral
  gray, so the car stands out. Accepted offers: P3 green; declined: P1
  cornflower blue. The threshold line: waiting-rider pink. All from
  `ridehail/animation/palette.py`; no new palette entries.
- The panel's lead/lag uses Textual's `$success` / `$error`.
- Layout and conventions follow `terminal_wait.py`: a Textual app on
  `RidehailTextualApp`, the `ConfigPanel` when the terminal is at least 100
  columns wide, `q` quit and space pause.

## 7. Tests

Claude does not run Textual tests (CLAUDE.md); the user runs those.
Tested without Textual:

- `offer_log`, `fleet_counts`, `fleet_summary()` and `net_series` over a
  game shift: the fleet row equals the end state's `income_and_costs` when
  the shift is the results window; the last point of `net_series` equals
  the summary's `net_income`.
- `offer_histogram()`: counts add up to the number of offers; with a
  `rate:N` strategy every accepted offer is at or above N.
- The seated car survives `_remove_vehicles`.
- Open-ended runs (`time_blocks = 0`) validate with `use_strategy`.

For the user: `python -m ridehail --preset game -a terminal_strategy -so
rate:30`, and the same with `-b 0` (open-ended) and with `n` / `N` pressed
during the run.

## 8. Bonus: the seated car on terminal_map

- Draw the seated car in a distinct style (bold, or a ring glyph) in its
  phase colour, and its pickup and drop-off markers.
- A one-line strip under the map with the panel's key figures (net, car vs
  fleet, acceptance).
- Optional: follow the car, as the web lab's `i` does.

`terminal_map.py`'s rendering is delicate (CLAUDE.md, the native animation
notes), so this is a separate step after `terminal_strategy`.

## 9. Order of work

1. Seat the car at the start of the shift (no offline period), and protect
   it from removal. **Done 2026-10-15** with the game simplification.
2. The controller data of section 4, open-ended runs, and their tests.
3. `terminal_strategy` itself.
4. The `terminal_map` bonus.
