# Running costs separated from the reservation wage

Status: **implemented 2026-10-15** (dev branch): the Python core, and the
web lab's Simple-mode control and Driver income chart (section 6), which
still need a wheel rebuild and a check in the browser. This is option B from
`claude/strategy-config-spec.md` section 11, done on its own because it is a
core change. The strategy work (option A) builds on it.

## 1. The problem

A driver has two kinds of cost:

- **Opportunity cost:** what the driver could earn elsewhere. It applies to
  every block on shift, moving or not.
- **Running cost:** fuel, wear and so on. It applies only when the car is
  driven.

City-scale mode has both as inputs (`per_hour_opportunity_cost`,
`per_km_ops_cost`), but before this change it added them into one
per-block `reservation_wage` and charged the sum on every block. Simple mode
had only the sum, entered directly as `reservation_wage`. So in Simple mode
net income equalled gross income, and nothing in either mode rewarded an
idle car for parking (`idle_vehicles_moving` < 1).

## 2. Parameters

| Name | Section | Short | Default | Meaning |
|---|---|---|---|---|
| `per_block_ops_cost` | DEFAULT | `-pbops` | 0 | **New.** Simple mode: running cost per block driven. Ignored with `use_city_scale`, where `per_km_ops_cost` sets it. |
| `reservation_wage` | EQUILIBRATION | `-erw` | 0.35 | Simple mode: the opportunity cost per block, now **excluding** running costs. With `use_city_scale` it is set from `per_hour_opportunity_cost` alone. |

The defaults leave every existing Simple-mode result unchanged: an old
`reservation_wage` was the whole cost, and it still is when
`per_block_ops_cost` is 0.

`reservation_wage` stays in [EQUILIBRATION] for now. Moving it and `price`
to [DEFAULT] is a separate open item.

## 3. Which blocks are driven

Running cost is charged on **every block except an idle block in which the
car stayed parked** (`Vehicle.update_location()`: P1 and not moving this
block). A car standing at a pickup (`pickup_time`) is engaged, and is
charged. With the default `idle_vehicles_moving` = 1 every block is
charged, so the default results equal "every block".

The count is a new history item, `History.VEHICLE_TIME_PARKED` (one per
vehicle per parked block), and its share of vehicle time is the new measure
`VEHICLE_FRACTION_PARKED`.

## 4. Measures and utility

In the simulation, per block: `ops_cost` is `per_block_ops_cost`, or
`per_km_ops_cost` per block with `use_city_scale`; `reservation_wage` is the
opportunity cost per block.

- gross = `price × (1 − platform_commission) × P3`
- net = gross − `ops_cost × (1 − parked)`
- surplus = net − `reservation_wage`

`vehicle_utility(p3, parked=0)` is the surplus, and drives price
equilibration, which now passes the parked share from its own history
window. With `use_city_scale` the three are converted to per hour, as
before.

City-scale results are unchanged when no car parks: before, net was gross
less running cost for every block, and surplus was gross less
(opportunity + running) cost. The one visible change there is the reported
`reservation_wage` (state dict and the end state's equilibration section),
which is now the opportunity cost alone.

The end state's `vehicles` section adds `fraction_parked`.

## 5. Left as they were

The matplotlib and terminal stats animations compute their own surplus line
from P3 alone (`vehicle_utility(p3)`), so with parked cars they overstate
running costs. They are legacy displays; fix them if they are used with
parking.

## 6. The web lab

- **Running cost** slider (`perBlockOpsCost`, 0 to 1 in steps of 0.05,
  default 0) in More settings, Economics group, after Reservation wage. It
  is a Simple-mode card (`ui-mode-simple`), hidden in Advanced mode, where
  Operations cost ($/km) sets the running cost. It is a live control
  (`requiresReset: false`, in `worker.py::update_options`). Its help popover
  is the config description, through `PARAM_NAME_MAP`.
- Wired like `reservationWage`: `js/config.js` (slider range and settings
  source), `js/dom-elements.js`, `js/input-handlers.js`,
  `js/sim-settings.js`, `js/session-storage.js`, `js/config-mapping.js`
  ([DEFAULT] `per_block_ops_cost`), `js/slider-direct-edit.js`, `app.js`
  (`updateAllUIControls`), `experiment-tab.js` (`setLabConfigControls`), and
  `worker.py` (`PARAM_NAME_MAP`, `OPTIONAL_WEB_SETTINGS` with default 0 for
  older saved sessions, `FRAME_SETTINGS`, `update_options`).
- **Driver income chart** (`modules/stats.js`): both modes now stack Net,
  Expenses and Unpaid, to the on-the-clock income. Expenses are gross less
  net, so they reflect parked blocks; in Advanced mode they were speed ×
  per-km cost, which charged parked cars. Empty segments have no label, so
  Simple mode with no running cost shows Net and Unpaid as before (but Net
  in place of the old "Paid" label).
- The earnings key below the charts describes Expenses, and Surplus as net
  income above the reservation wage.
- Not changed: the What If? tab, which has no running-cost control and
  still computes its own Advanced-mode expenses (`modules/whatif.js`).
