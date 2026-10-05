# Idle vehicles returning to the core (October 2026)

## Why

With inhomogeneity > 0, trip origins concentrate in the city core but (with
sampled trip distances) destinations do not (game-mode.md 5.7), so cars
drain out of the core. Idle cars then cruise at random, so they stay in the
outskirts: only 3-5% of idle cars are in the core (25% of the area) against
63% of requests at inhomogeneity 0.5. Real drivers reposition towards
demand. Of the options considered (deterministic return, biased random
walk, head for a sampled origin, return after waiting, follow a demand
field), the biased random walk was chosen to keep the model simple.

## The rule (changed 2026-10-04: sampled request origin)

Since 2026-10-04 an idle car heads for a **sampled request origin**, not the
nearest point of the core: with probability `idle_vehicles_returning` at
each intersection it takes a step (`_navigate_towards`) towards its
`Vehicle.return_target`, drawn by `City.set_location()` as a trip origin is
(so mostly in the core, some outside) and kept until reached or dispatched;
otherwise it turns at random. This applies inside the core too.
`Vehicle._return_target()` replaced `_core_return_target()`, and
`City.nearest_core_location` was removed. Contrary to the hope, idle cars
do not end up distributed like demand: nearest-car dispatch takes them
wherever demand is, so the stock of idle cars still sits where demand is
thin; the rule changes how they reposition, not where they pile up.
Why, and what it did: claude/game-mode.md 16.11. The measured table below
is for the old rule.

## The rule as first built (nearest core point, superseded)

`idle_vehicles_returning` (float in [0, 1], default 0, `-ivr`, DEFAULT
section). At each intersection, a P1 vehicle **outside** the core turns
towards the nearest point of the core with this probability, and otherwise
picks a random direction as before (no U-turn). Inside the core it always
cruises at random.

- p = 0 is the old model (no random numbers are drawn, so seeded runs are
  unchanged); p = 1 is "always head back".
- Ignored when inhomogeneity is 0: the core is not special then.
- A turn towards the core may be a U-turn (a driver deciding to go back).
- Independent of `idle_vehicles_moving` (which decides whether the car
  moves this block at all).

## Code

- `City.core_bounds()`: the core is `low <= x < high` on both axes. Now the
  single definition, used by `City.set_location` and `game.py`
  `_core_range`. `City.two_zone_size` became a property so the core follows
  `city_size` if it changes mid-run.
- `City.nearest_core_location(location)`: nearest core point measured
  around the torus, per axis; None if already inside.
- `Vehicle._core_return_target()` and the P1 branch of
  `Vehicle.update_direction` (`ridehail/atom.py`), which uses the existing
  `_navigate_towards`.
- The probability lives on the `City` (set at construction, synced in
  `_init_block` like `inhomogeneity`), so it is live-updatable via
  `target_state` without touching every `Vehicle`.
- Recorded in `state_dict`, results config, and the config file writer.
- Tests: `test/test_idle_vehicles_returning.py`.
- **Not yet exposed in the web lab** (`ridehail/lab/worker.py`,
  `config-mapping.js`, UI control) or the game.

## Measured effect

City 32, inhomogeneity 0.5, mean trip distance 16, demand 4/block, 1200
blocks (first 300 discarded), 3 seeds:

| Fleet | p | Idle cars in core | P1 / P2 / P3 | Mean wait |
|---|---|---|---|---|
| 150 | 0 | 0.03 | 0.42 / 0.15 / 0.43 | 5.7 |
| 150 | 0.1 | 0.08 | 0.44 / 0.13 / 0.43 | 4.7 |
| 150 | 0.25 | 0.31 | 0.47 / 0.10 / 0.43 | 3.7 |
| 150 | 0.5 | 0.57 | 0.48 / 0.09 / 0.43 | 3.6 |
| 150 | 1.0 | 0.75 | 0.47 / 0.10 / 0.43 | 3.7 |
| 220 | 0 | 0.04 | 0.63 / 0.08 / 0.29 | 4.4 |
| 220 | 0.1 | 0.21 | 0.65 / 0.06 / 0.29 | 3.0 |
| 220 | 0.25 | 0.51 | 0.66 / 0.05 / 0.29 | 2.8 |
| 220 | 0.5 | 0.72 | 0.65 / 0.06 / 0.29 | 3.1 |
| 220 | 1.0 | 0.84 | 0.65 / 0.06 / 0.29 | 3.3 |

Pickup time and waits fall by a third to a half; the minimum wait is around
p = 0.25-0.5, and p = 1 over-concentrates (outer requests wait longer). The
idle share in core passes the request share (63%) around p = 0.25-0.5.
With no idle cars (saturated market) the setting has no effect.
