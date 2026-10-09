# Game Mode: "Just One More Shift…" — design and calibration log

**This is the dated log.** For the game as it is now, read
`claude/game-design.md` first; it points back into this file for the
reasoning behind each decision. Entries here are kept as written, so early
parts describe designs that were later changed (see game-design.md section
11 for which). Code comments cite this file by part and section number, so
keep the numbering when adding to it: new work goes in a new part at the end.

Original status line (2026-09-30): Part 1 reviewed 2026-09-29 (decisions in
1.11). Part 2 drafted 2026-09-29. Phases A–E implemented 2026-09-29; see the
progress log in 2.10. Part 3 (realistic offer prices from the offer study
and Toronto trip data) is a spec, 2026-09-30.

**Code layout (2026-10-05):** `ridehail/game.py` was split into the package
`ridehail/game/`, with no change in behaviour, and `ridehail/game_offer_model.py`
moved to `ridehail/game/offer_model.py`. The dated sections below still name
`ridehail/game.py`; its contents are now in `params.py` (`GameParams`, units,
`CARDS`), `market.py` (markets, cities, `make_game_config`, `shift_seed`),
`bots.py`, `pricing.py` (`OfferPricing`: rate card, luck, offer price, rider
fare; reached from the controller as `game.pricing`), `controller.py`
(`GameController`, `Ledger`) and `report.py` (`results()`, the debrief).
Everything is still importable from `ridehail.game`. The worker's
`offerHeldSettings`/`offerHeldRunId` (Part 2) are now `nextFrame` with
`waitingFor: "offer"`.

The web lab already has a hidden placeholder tab (`#tab-game`,
`docs/lab/components/game-tab.html`, toggled with `g` via `toggle_game` in
`js/keyboard-handler.js`). The game will take that tab.

---

## Part 1: Game design

### 1.1 Premise in one paragraph

You drive for a ridehail platform for one shift in a small simulated city. Your
car is one of about a hundred on the map. When the platform's dispatcher picks
you for a trip, the world freezes and an **offer card** pops up: a fixed
upfront price, how far away the pickup is, and how long the trip is. You have a
few seconds to **Accept** or **Decline**. When the shift ends you see what you
actually earned per hour, after expenses and counting every unpaid minute, and
how that compares with automated drivers who followed simple rules, and with the
rest of the fleet.

The lesson we are after is one drivers learn the hard way: **a good trip is not
the same as a good hour.** Whether a $9 offer is worth taking depends on how
long the pickup is, where the trip leaves you, and how soon the next offer will
come. Upfront pricing hides the rate card behind a single number.

### 1.2 What changes from the sketch, and why

| Sketch | Adjusted design | Reason |
|---|---|---|
| "Periodically" gets an offer | Offers come **from the dispatcher itself**: when the nearest-vehicle dispatch picks the player's car, that becomes an offer | Offer frequency then comes out of the market (busy vs slow), which is the core lesson. No separate offer generator to calibrate. |
| 5 seconds to decide | **World freezes** while the card is up; countdown of 8 s (5 s for the retired Pro); timeout = decline | At about 1 block per second of real time, 5 s would be 5 sim-minutes of driving. Freezing keeps the decision clean and fair. |
| Offers above/below a rate card | Every trip gets an upfront **driver offer = rate card × multiplier**, multiplier drawn from a lognormal fitted to the offer study | Grounded in real data (see 1.5). The comparison with the rate card is **never shown on the card**, because real drivers don't see it; the debrief reveals it afterwards (revised 2026-09-29). |
| Earnings at the end | **Net earnings per hour of shift**: fares minus per-km running costs, divided by *all* shift time (idle and pickup included) | Accounting for idle time, pickup time and running costs is most of what the game teaches. |
| Compare to automated drivers | Four **named bot drivers** with simple, visible strategies, plus a **fleet percentile** (the other ~100 cars accept everything) | Competitive, and it shows which rules of thumb work in which market. |
| Simple mode, 1 block ≈ 1 minute | Yes: 1 block = 1 minute = 0.5 km (30 km/h). Money is computed in the game layer, not by the sim's Costs & Incomes mode | Keeps the sim in Simple mode. The game adds the money on top. |
| Non-equilibrating | Yes, fixed fleet (`equilibration = NONE`) | As sketched. |

### 1.3 A shift, step by step

1. **Choose a shift** (setup card on the Game tab):
   - **Market**: *Slow Tuesday* (oversupplied, long idle), *Normal*, or *Busy
     Friday* (undersupplied, offers come fast). Only the fleet size relative
     to demand changes.
   - **Offer screen** (replaced *Difficulty*, 2026-10-01; see Part 6): *Rate
     helper* ($/km and $/hr incl. pickup shown on the card, as a third-party
     app would) or *Platform only* (the platform's card alone). That is the
     only difference: both have 8 s and no acceptance rule, and neither shows
     the rate card. Each has its own leaderboard.
   - **Shift code** (optional): a seed. The same code gives everyone the same
     city, demand stream and your starting point, so friends can compare
     scores. There is a default "Shift of the day" code derived from the date.
2. **Warm-up** (invisible, ~60 blocks run without rendering) so the market is
   at steady state when your shift starts.
3. **Drive**. The map is the familiar lab map. Your car is enlarged and
   outlined, and it keeps its phase colour (P1 blue / P2 amber / P3 green, from
   the unified palette). A HUD strip shows: shift clock (e.g. "1:42 left"),
   earnings so far, current $/hr, acceptance rate, and (dormant acceptance
   rule only) a warning when you are close to the acceptance limit.
4. **Offer**. The world dims and freezes. The pickup and dropoff are
   highlighted on the map with a line from your car → pickup → dropoff. The
   card shows (generic styling, *not* Uber/Lyft branding):
   ```
   ┌──────────────────────────────────┐
   │  $11.40                      ⏱ 5 │
   │                        ┌───────┐ │
   │  o 4 mins (2.0 km) away │ $/km  │ │
   │  | 16 mins (8.0 km) trip│ $1.14 │ │
   │  □                      │ $/hr  │ │
   │  Drop-off: Downtown     │ $34.2 │ │
   │                        └───────┘ │
   │  [ Decline ]          [ Accept ] │
   └──────────────────────────────────┘
   ```
   The legs are worded as on a real platform card ("13 mins (10.8 km)
   away", "2 hr 1 min (141.7 km) trip"). The boxed column appears with the
   rate helper only: it stands for the third-party apps some drivers run,
   which overlay the offer per km and per hour (pickup included) on the
   platform's card. Platform only shows the platform's card alone. Unlike real cards, there's no map
   inset, no rider rating, and there is a Decline button (the platforms
   have only Accept and a close ×).
   Keys: `→`/`Enter` accept, `←`/`Esc` decline. Big tap targets on phone.
   The card does **not** compare the offer with the rate card. Drivers
   receiving upfront offers aren't told this, and the uncertainty is part of
   what makes the decision hard. They could in principle work it out from
   the published rate card and the trip's distance and time, but not in a
   few seconds. The debrief's offer log reveals it afterwards.
5. **Consequences**:
   - *Accept*: you drive to the pickup (unpaid), then the trip (paid on
     drop-off).
   - *Decline or timeout*: the trip goes back to the dispatcher and goes to
     the next-nearest car, never back to you. The rider waits longer (we
     count that, see the debrief).
6. **Time warp**: while you are on a trip there is nothing to decide, so the
   sim runs about 3× faster until you are idle again. This keeps a 3-hour shift
   to about 3–4 minutes of play.
7. **End of shift** at the chosen length (default 3 sim-hours = 180 blocks).
   A trip in progress is credited pro rata for the distance covered, for the
   player and the bots alike.
8. **Debrief** (see 1.7).

### 1.4 Economics (all in the game layer)

The sim stays in Simple mode. Constants below are starting values to calibrate
in Part 2.

- **Scale**: 1 block = 1 min = 0.5 km. Trip time and distance are therefore
  exactly proportional (no traffic). This is a deliberate simplification: on
  the card, $/km and $/min carry the same information, so we show only one
  derived rate (per minute, including pickup).
- **Driver rate card** (the "old" time + distance card):
  `$2.50 + $0.75/km + $0.18/min`. For the median offer-study trip (6.9 km,
  14 min) that gives $10.20.
- *(Superseded 2026-09-30 by Part 3: offers now come from a model fitted to
  the offer study.)* **Driver offer** = rate card × `m`, `m ~ LogNormal(median 0.92, σ 0.30)`,
  clipped to [0.45, 2.2], rounded to $0.05. Median offer for a median trip is
  about $9.40, which matches the offer-study median fare ($9.39), and a
  10–90% spread of about 0.63–1.35× matches the observed Lyft fare/fit ratio
  (0.65–1.48). The price is fixed per trip: if you decline, the next driver
  sees the same price.
- **Rider price**: not modelled in v1 (see 1.10 v2).
- **Running cost**: $0.56 per km actually driven, idle cruising and pickups
  included: the median cost per km driven in a 2024 report to the City of
  Toronto (backgroundfile-251343.pdf, p. 26; fixed and variable expenses,
  mostly variable). Until 2026-09-30 it was $0.30, taken from the lab
  presets' `per_km_ops_cost`, which has no documented source.
- **Score** = net earnings over the shift = Σ fares − running costs.
  Headline: **net $/hr of shift**.

Sanity check (Normal market, accept everything): P3 ≈ 0.5 gives about 2.5
trips/hr × ~$9.40 ≈ $23/hr gross, minus about $9/hr running cost (30 km/hr if
idle cars keep moving), so about **$14/hr net**. That is realistic, and low
enough that players will want to beat it.

### 1.5 Grounding in the offer study

From `~/src/uberdriver/offer_study` (18,969 extracted Toronto offer cards,
Uber/Lyft/Hopp):

| Quantity | 5% | 25% | median | 75% | 95% |
|---|---|---|---|---|---|
| Fare ($) | 3.68 | 5.99 | 9.39 | 15.61 | 27.28 |
| Trip km | 1.4 | 3.2 | 6.9 | 16.7 | 32.2 |
| Trip min | 5 | 9 | 14 | 22 | 37 |
| Pickup min | 1 | 3 | 4 | 6 | 10 |
| Fare/km incl. pickup | 0.52 | 0.73 | 0.98 | 1.37 | 2.27 |
| Fare per engaged hour | 19.5 | 24.5 | 29.5 | 37.0 | 53.6 |

- Trip lengths are strongly right-skewed. The game should use the sim's
  `GAMMA` trip-distance distribution rather than `UNIFORM`, so players see a
  real mix of short trips and long airport-style trips.
- Short trips pay a little less per engaged hour (median ~$27.5/hr for trips
  under 15 min vs ~$33/hr for 25–40 min). A small positive tilt of `m` with
  trip length could reproduce this. Optional, and low priority.
- The debrief cites the dataset (decision 6, and debrief item 8).

### 1.6 The bots (and the fleet)

Every non-player car is an automated driver. Most accept everything, which is
the sim's normal behaviour. Four cars are named bots whose rule is shown in
the debrief. They receive offers from the same dispatcher and price model and
decide instantly:

| Bot | Rule | Teaches |
|---|---|---|
| **Yes-to-Everything** | accept all | the baseline. Its score also defines the fleet |
| **Rate-Card Loyalist** | accept only if offer ≥ rate card | cherry-picking on price alone. This bot works out the rate card exactly, which a human can't do in the time allowed |
| **Dollar-a-Km** | accept if offer ÷ (pickup km + trip km) ≥ $1.00 | the drivers' folk rule (the study's mean is $1.05/km) |
| **Hourly Thinker** | accept if offer ÷ (pickup min + trip min) ≥ $0.55/min (≈ $33/engaged hr) | a reservation rate on engaged time |

Bot names are functional, so we do not have to pick personal names or
genders. Each bot's result is a single run, so it includes luck. The debrief
says so ("one shift; luck matters, try another shift code").

**Fleet percentile**: "You out-earned 78% of drivers in this shift" is
computed over all cars' net $/hr using the same accounting.

**Market-dependent ranking (the key lesson)**: in *Busy Friday* the picky bots
tend to win, because a declined offer is replaced within a minute or two. In
*Slow Tuesday*, Yes-to-Everything tends to win, because each declined offer
costs a long idle wait. We should confirm during calibration that the bot
ranking actually flips between the markets. If it doesn't, the market
parameters need adjusting until it does.

### 1.7 End-of-shift debrief

1. **Score card**: net earnings, net $/hr, and a rank table (you + 4 bots),
   with the fleet percentile. Personal best per market/difficulty is kept in
   `localStorage` (a convenience; there is no server leaderboard because the
   lab is static on GitHub Pages).
2. **Share line**, Wordle-style, copied to the clipboard:
   `Ridehail shift 2026-09-29 · Busy · Pro — $19.80/hr, beat 83% of drivers, 2nd of 5`.
   The shift code makes this comparable between friends.
3. **Where your time went**: a single stacked bar of idle / to pickup / with
   rider (P1/P2/P3 palette colours), with *unpaid* marked over idle + pickup.
   Since 2026-10-04 an "All drivers" bar sits beneath it (results
   `fleet_minutes`: the pooled phase minutes of the drivers in the "How you
   compare" average) and the legend gives both shares. (A minute-by-minute
   chart of the fleet's P1/P2/P3 lines with a strip of the player's phase
   beneath was tried the same day and dropped: it added little.)
4. **Offer log**: one row per offer with price, % vs rate card (labelled as
   what the card didn't show), $/min incl.
   pickup, decision, and (for declined offers) what happened next ("taken by a
   car 2 min further away"). Sortable. Rows colour-coded above/below the rate
   card.
5. **Three auto-generated insights**, chosen from a small rule set, e.g.
   - "You declined 4 offers that paid above the rate card."
   - "Pickups were 19% of your shift, all unpaid."
   - "Your best trip paid $0.92/min; your worst $0.31/min."
   - "In this market the average wait between offers was 3.1 min, so each
     decline cost you about $1.20 of expected earnings."
6. **Engaged vs total time**: "Paid-trip time was 52% of your shift. Your
   earnings per *engaged* hour were $31.20; per *shift* hour, $17.40." A
   one-line note that some minimum-pay laws (e.g. Ontario's Digital Platform
   Workers' Rights Act) count only engaged time. The exact current rate should
   be looked up and checked before we publish.
7. **Rider impact**: "Your declines added a total of N minutes of rider
   waiting." This is a small nudge about the effect declines have on the
   system.
8. **Data note**: "Offer prices are drawn to match about 19,000 real Toronto
   offer cards collected by drivers (the offer study)," with a link or
   citation.
9. Buttons: **Same shift again** (same code), **New shift**, **Try another
   market**.

### 1.8 The platform pushes back (dormant)

Retired with Pro (Part 6): `GameParams.acceptance_rule` still works, and is
tested, but no offer screen turns it on.

Pro turns on an **acceptance-rate rule**: if you accept fewer than 4 of your
last 10 offers, you are put in a **10-minute timeout** with no offers (the car
greys out on the map). The HUD shows acceptance rate with a warning band. This
means you cannot simply decline everything to stop the platform setting the
terms. The debrief notes that platforms have used acceptance thresholds and
tier programmes this way, and that some now label offers "declining won't
affect your acceptance rate" (a badge that appears on 681 cards in the study).

Bots are exempt: their rules are fixed and they would rarely hit the limit.
This is noted in the debrief.

### 1.9 Market settings (original starting points; calibrated values are in 2.10)

Based on the Town preset (city 24 → 12 km square, inhomogeneity 0.5 so the
centre is busier), GAMMA trip distances, mean 12 blocks (6 km),
`pickup_time = 1`, `idle_vehicles_moving = 1.0`, equilibration NONE, fixed
demand:

| Market | Vehicles | Demand (req/block) | Target P1 | Rough gap between offers when idle |
|---|---|---|---|---|
| Busy Friday | ~95 | 5 | ~0.15 | ~1–2 min |
| Normal | 120 | 5 | ~0.30 | ~3–5 min |
| Slow Tuesday | ~160 | 5 | ~0.45 | ~8–12 min |

Inhomogeneity adds strategy: a long trip to the edge pays well but can strand
you where offers are rare, and the Drop-off line on the card hints at this.

### 1.10 Scope

**v1 (the playable game)**: setup card; three markets, two difficulties,
shift code; freeze-and-offer card with countdown and keyboard/tap; highlighted
player car and offer route; HUD; time warp while busy; four bots + fleet
percentile; debrief sections 1–9; personal bests; share line; Pro
acceptance rule; phone layout (offer card as a bottom sheet over the
maximised map).

**v2 candidates** (explicitly out of v1):
- **Rider price and platform-take reveal**: a second price model, rider rate
  card × an independent multiplier, so the platform's cut varies from trip to
  trip. Deferred until it can be calibrated against figures we have on rider
  prices and take rates.
- **Repositioning**: while idle, tap the map to drive toward a spot (e.g.
  downtown). This adds real agency but needs a new "idle with destination"
  behaviour in the sim.
- Demand that varies over the shift (rush hour, then a lull), reusing the
  hour-of-day machinery.
- Surge / "offer price rises after declines" as a scenario, framed as a
  hypothesis.
- Per-driver price discrimination as an explicit scenario ("the platform
  learns your reservation price"), again framed as a what-if, not a claim.
- Rider rating, badges, stacked (forward-dispatch) offers.
- A server leaderboard (needs a backend, which the lab doesn't have).

### 1.11 Decisions (reviewed 2026-09-29)

1. **The world freezes during offers.** Agreed.
2. **Acceptance-rate penalty in Pro only.** Agreed. Pro itself is low priority,
   so it goes in the last phase of the plan.
3. **No rider-price / platform-take reveal in v1.** It moves to v2 and needs
   calibrating against real figures first.
4. **Repositioning deferred to v2.** Agreed.
5. **Shift length 3 sim-hours** (180 blocks). Agreed.
6. **Cite the offer-study dataset** in the debrief. Agreed.

---


## Part 2: Implementation plan

### 2.1 Architecture in one picture

```
 Game tab (main thread)                     webworker.js                 Python (Pyodide)
 ─────────────────────                      ────────────                 ────────────────
 game-tab.js  ── Play(gameSimSettings) ──▶  init_game(settings) ──────▶  worker.py GameSimulation
   setup card                                                               └─ RideHailSimulation
   HUD                                      getNextFrame loop                  └─ Dispatch.offer_filter
   offer card  ◀── frame {vehicles,trips,   (paused while an offer   ◀──    ridehail/game.py
   debrief          game:{...,offer}} ───── is pending)                       GameController
               ── GameDecision(accept) ──▶  resolve_offer() ─────────▶        (prices, bots, ledger,
               ── GetGameResults ────────▶  game_results() ──────────▶         offer log, results)
 modules/map.js plotMap(results) + game overlay (player ring, offer route)
```

Principles:

- **All game logic is in Python, in a new core module `ridehail/game.py`.**
  That covers the price model, bot rules, the per-vehicle ledger, the offer
  log, the acceptance rule and the end-of-shift results. It ships in the
  wheel, is unit-tested with pytest, and can be driven headless by a
  calibration script. JS only renders it and forwards decisions.
- **The core simulation changes in one place.** An optional
  `offer_filter` hook in `Dispatch`. When the hook is `None` (every non-game
  run), dispatch behaves byte-for-byte as it does now.
- **The world freezes in the worker, not in the renderer.** When an offer is
  pending, the worker does not schedule the next frame. The main thread
  shows the card and sends a decision, which resumes the loop. This reuses
  the existing backpressure and `activeRunId` machinery unchanged.
- **The game gets its own settings object** (`appState.gameSimSettings`,
  name `"gameSimSettings"`). It shares the single worker loop with the other
  tabs, as What If does, and entering or leaving the Game tab resets it.

### 2.2 Core simulation change: the offer hook (`ridehail/dispatch.py`)

Refactor each single-trip dispatch function into **find** and **commit**
steps, without changing behaviour:

- `_find_vehicle_sparse(trip, city, candidates)` and
  `_find_vehicle_dense(trip, city, grid, candidate_set, vehicles)` return
  `(vehicle, dispatch_distance)` or `None`, and change nothing.
- `commit_dispatch(trip, vehicle)` (public, static) does what the tail of
  each function does now: `trip.update_phase(WAITING)`,
  `vehicle.update_phase(trip=trip)`. The caller removes the vehicle from the
  candidate structures.
- `Dispatch.__init__` gains `self.offer_filter = None`.
- With `offer_filter is None`, `_dispatch_vehicles_default` runs the current
  code path exactly (find → commit), including the random tie-break order,
  so seeded runs are unchanged.
- With a filter set, each trip loops as follows:
  ```
  excluded = set()
  loop:
      found = find(trip, candidates − excluded)      # skip excluded vehicles
      if not found: break                            # trip stays UNASSIGNED
      decision = offer_filter(trip, vehicle, dispatch_distance)
      ACCEPT  → commit, remove vehicle from pool, break
      DECLINE → excluded.add(vehicle); continue      # next-nearest, same block
      DEFER   → remove vehicle from pool this block; break   # player offer held
  ```
  For the dense search, excluded vehicles are skipped with the same
  set-membership test that already exists (`vehicle not in
  dispatchable_vehicles_set`). The check becomes `... or vehicle in excluded`.
- Only `DispatchMethod.DEFAULT` supports the hook. The game always uses
  DEFAULT, and the hook raises on other methods if it is set.
- Tests: extend `test/test_dispatch_performance.py` or add
  `test/test_dispatch_offer_filter.py`:
  1. With a fixed seed and `offer_filter=None`, trip→vehicle assignments
     match the current implementation over N blocks, for both sparse and dense
     searches. Record them from the pre-refactor code as a fixture first.
  2. DECLINE gives the trip to the next-nearest vehicle in the same block.
  3. DEFER leaves the trip UNASSIGNED and the vehicle in P1.
  4. A vehicle that declined a trip is never offered it again (the
     `declined_by` set lives on the trip; see 2.3).

### 2.3 `ridehail/game.py`

```python
class OfferDecision(Enum): ACCEPT, DECLINE, DEFER

@dataclass
class GameParams:            # all calibratable constants from Part 1
    km_per_block = 0.5; min_per_block = 1.0
    rate_base = 2.50; rate_per_km = 0.75; rate_per_min = 0.18
    mult_median = 0.92; mult_sigma = 0.30; mult_clip = (0.45, 2.2)
    ops_cost_per_km = 0.30
    shift_blocks = 180; warmup_blocks = 60
    offer_seconds = 8                       # Rookie; 5 for Pro (JS uses it)
    acceptance_rule = None | (min_accepts=4, window=10, timeout_blocks=10)

MARKETS = {"slow": {...}, "normal": {...}, "busy": {...}}   # 1.9 table
BOT_RULES = {"yes": ..., "loyalist": ..., "per_km": ..., "hourly": ...}

class GameController:
    def __init__(self, sim, params, seed)
        # picks player + 4 bot vehicle indexes with its own random.Random(seed)
        # installs self._offer_filter on sim.dispatcher.offer_filter
    def warm_up()                    # runs warmup_blocks with the filter as
                                     # accept-all, ledger off, then resets
                                     # sim.block_index bookkeeping for the shift
    def before_block()               # applies a resolved player decision
    def after_block(block)           # ledger update: see below
    def pending_offer() -> dict|None # for the frame payload
    def resolve_offer(accept: bool)  # commit, or mark declined; recompute
                                     # the player's direction if accepted
    def frame_payload() -> dict      # HUD numbers + player/bot indexes + offer
    def results() -> dict            # the debrief (Part 1 §1.7)
```

Details:

- **Prices** are drawn lazily the first time a trip is offered to anyone,
  from the controller's own `random.Random`. They are stored in
  `self.prices[trip_id] = (rate_card, offer)`; trip ids are permanent dict
  keys in `sim.trips`. A separate RNG means the price draws don't disturb
  the sim's global `random` stream more than the player's own decisions do.
- **The offer filter** is the hot path, since it runs for every dispatch. It
  returns ACCEPT immediately for any vehicle that is not the player or a
  bot. For bots it applies `BOT_RULES`. For the player it returns DEFER and
  records `self.pending = {trip_id, vehicle_index, pickup_blocks, ...}`,
  unless the player is in a Pro timeout, in which case it returns DECLINE
  silently. Declines are logged per trip (`trip.declined_by`, set lazily with
  `getattr`) so the same vehicle is never offered that trip again.
- **Resolving an offer** happens at a block boundary. On accept:
  `Dispatch.commit_dispatch(trip, player)` then `player.update_direction()`,
  because the direction was chosen at the end of the block while the car was
  still P1. On decline or timeout: add to `declined_by`, log it, and the
  trip is re-dispatched normally in the next block. The log records what
  happened next ("taken by a car N min further away") when the trip is next
  dispatched.
- **Ledger** (`after_block`), per vehicle, vectorised simply over the ~120
  cars:
  - km: +0.5 if the location changed since the last block. Wrap-around
    counts as a move.
  - minutes by phase: +1 in P1/P2/P3.
  - earnings: when a vehicle's tracked trip id reaches `COMPLETED`, credit
    `offer` (or `rate_card` for non-bot fleet cars, drawn the same way so
    fleet earnings are comparable).
  - offers seen / accepted, for the player and bots.
  - To see which trip a vehicle was on, snapshot `vehicle.trip_index` before
    the block. Completion clears it in `Vehicle.update_phase`.
- **End of shift / pro rata**: in `results()`, a trip in progress (P3) is
  credited `offer × blocks ridden / trip.distance`. For that, the ledger
  records the block at which each P3 trip started.
- **Results**: player summary, bot rows, fleet net-$/hr list (for the
  percentile), time split, offer log, and insight inputs (declined
  above-rate-card count, unpaid pickup share, best and worst $/min, mean gap
  between offers). The JS side picks and phrases the insights.
- **Acceptance rule** (Pro, last phase): a rolling window of the player's
  decisions. Crossing the threshold sets `timeout_until = block + 10`.

Tests (`test/test_game.py`, plain pytest, no Textual):
- The price model: median and quantiles of `offer/rate_card` over 10k draws
  fall within tolerance of the targets, and clipping works.
- Each bot rule accepts and declines the right synthetic offers.
- The ledger: a scripted trip credits exactly once, km and minutes add up to
  the number of blocks, and pro rata is correct at the shift end.
- End to end: a seeded headless shift with a scripted player (accept all)
  runs 180 blocks, and results are internally consistent (Σ phase minutes =
  180 per car).
- Offer determinism: the same seed and the same decision sequence give the
  same offer sequence.

### 2.4 Calibration script (before any UI): `utils/game_calibrate.py`

This runs headless shifts: 20 seeds × 3 markets, with the player seat played
by each bot rule in turn plus accept-all. It reports, per market:
- P1/P2/P3 fractions, and the mean and 90th-percentile gap between offers
  for an idle car.
- Net $/hr per strategy (mean ± sd over seeds) and each bot's acceptance rate.
- **The key check (§1.6)**: whether the strategy ranking flips between *Busy*
  and *Slow*.

Tune `MARKETS` (vehicle count, mostly) and, if needed, the bot thresholds
until the flip is clear and accept-all nets roughly $12–16/hr in Normal.
Record the final numbers in this document. This is Python-only, so we can run
it directly (no Textual, no browser).

### 2.5 Worker bridge

**`docs/lab/worker.py`**
- `init_game(settings)`: builds the `RideHailConfig` from the market preset
  (Town geometry, GAMMA trips, `equilibration=NONE`, `use_city_scale=False`,
  `idle_vehicles_moving=1.0`, `pickup_time=1`, seed from the shift code; seed
  must be non-zero, since `simulation.py` only seeds if it's truthy). Then it
  creates a `GameSimulation(Simulation)` and runs `warm_up()`. It sets the
  global `sim` like `init_simulation` does.
- `GameSimulation` subclasses the existing `Simulation` so it inherits
  `next_frame_map()` and its midpoint logic. It overrides
  `_get_block_results` to call `controller.before_block()` / `after_block()`
  around `next_block`, and attaches `results["game"] =
  controller.frame_payload()`.
- **Offer timing and interpolation** (this is the delicate part; see the
  memory note on care with map interpolation): a block runs on an *odd*
  frame, and its real positions are shown on the next *even* frame. So:
  - the `offer` goes into `pending_results["game"]` (the even frame), not
    the midpoint frame. The card appears when the car visibly arrives at the
    intersection where it was dispatched.
  - `resolve_offer(accept)` must also update `self.prev_directions[player]`
    when an accept changes the player's direction. Otherwise the next
    midpoint frame shows the car facing its old random direction.
  - When interpolation is off (city > 32), the offer rides on the single
    frame. Game markets are city 24, so interpolation is always on, but both
    paths should be handled.
- `resolve_offer(accept)` and `game_results()` are thin wrappers that return
  plain dicts.

**`docs/lab/webworker.js`**
- New `SimulationActions`: `GameDecision`, `GetGameResults` (in
  `js/constants.js`).
- In `getNextFrame`, after conversion: if `results.game?.offer` is set, do
  **not** arm `pendingFrameSettings`. Keep them in a new
  `offerHeldSettings`/`offerHeldRunId` pair. The frame is posted and the loop
  stops.
- On `GameDecision`: call `workerPackage.sim.resolve_offer(accept)`, then, if
  `offerHeldRunId === activeRunId`, move the held settings into
  `pendingFrameSettings` and call `scheduleNextFrame()`. A stale decision
  (the tab was reset in the meantime) is ignored.
- **Time warp**: when `results.game.player_phase` is P2 or P3, the wait in
  `scheduleNextFrame` uses `animationDelay / 3`. This is done worker-side, so
  there is no round-trip lag.
- **Frame limit**: game settings carry `timeBlocks = 180`, and the existing
  `frameLimit` stops the loop at the shift end. The final frame carries
  `game.shift_over = true`.
- On `GetGameResults`: post `{action: "gameResults", results}`, mirroring
  `GetResults`.

### 2.6 Main thread

New files:
- `docs/lab/game-tab.js`: a `GameTab` class, following the `WhatIfTab`
  pattern (constructed in `app.js`, `setupEventHandlers()`,
  `resetUIAndSimulation()`). Its state machine is
  `setup → warming → driving ⇄ offer → debrief`.
- `docs/lab/components/game-tab.html`: replaces the placeholder with the
  setup card, map canvas, HUD strip, offer-card `<dialog>`, and debrief
  section.
- `docs/lab/modules/game-offer.js`: renders the offer card and runs the
  countdown (a `requestAnimationFrame` ring). Timeout sends a decline.
- `docs/lab/modules/game-debrief.js`: score table, time-split bar, offer log,
  insights, share line, and personal bests in `localStorage` (wrapped in
  try/catch).
- Styles in `style.css` under a `/* Game */` section, using the palette
  constants and legible sizes (≥16px, per the font-size preference).

Changes to existing files:
- `app.js`: construct `GameTab`, add `case "tab-game":
  app.gameTab.resetUIAndSimulation()` to the tab switch, and pause or reset
  the game when leaving its tab. The existing `window.chart.destroy()` on tab
  switch already frees the map.
- `js/app-state.js`: add `gameSimSettings`.
- `js/message-handler.js`: route frames whose `name === "gameSimSettings"`
  to `plotMap(results)` and then `app.gameTab.onFrame(results)` (HUD, offer
  card, shift end). Route `action === "gameResults"` to the debrief.
- `modules/map.js`: a small, optional **game overlay**, active only when
  `eventData.get("game")` exists:
  - player car: the same icon at 1.6× radius with a dark outline ring (an
    extra dataset, index 2, drawn above the vehicles; this keeps
    datasets 0/1 and their caches untouched).
  - while an offer is shown: a dashed polyline player → pickup → dropoff
    (dataset 3, `showLine: true`), plus a dimming layer over the rest of the
    map, done with a CSS class on the canvas wrapper rather than inside
    Chart.js.
  - bots: optionally a small letter badge. This can come later.
  - `initMap` only needs the extra empty datasets when the game initialises
    it (an `options.game` flag).
- `js/keyboard-handler.js`: while the Game tab is active, the global
  shortcuts (space = pause, etc.) are suspended except `g`. While the offer
  card is up, `→`/`Enter` accept and `←`/`Esc` decline. The `d`/`a` letter
  keys are avoided because `d` is already a global mapping. Pause is allowed
  between offers but not during one.
- `index.html`: remove `tab-hidden` from `#tab-game` once v1 is ready. Until
  then the tab stays behind the `g` toggle.
- Phone (`js/phone.js`, `body.is-phone`): the offer card becomes a bottom
  sheet with two half-width buttons at least 56px tall, and the HUD collapses
  to clock + earnings.

Shift code: the default is `YYYY-MM-DD` (today). Seed =
`fnv1a(code + market) | 1`, so it is never zero. The code is shown in the
setup card and in the share line, and it can be edited. `?game=CODE&market=busy`
in the URL deep-links straight into the Game tab.

### 2.7 Phasing

Each phase ends in something the user can check.

| Phase | Scope | Verified by |
|---|---|---|
| **A. Core** | 2.2 dispatch hook + refactor; 2.3 `game.py`; tests | `pytest test/`; seeded dispatch regression unchanged |
| **B. Calibration** | 2.4 script; tune `MARKETS` and bots; write the numbers into this doc | the ranking flip between Busy and Slow |
| **C. Bridge** | 2.5 worker.py + webworker.js; `./build.sh` | the user plays a shift in the browser with the game driven from the console (a temporary debug hook: `w.postMessage({action:"gameDecision",accept:true})`) |
| **D. Playable** | 2.6 tab, setup card, map overlay, HUD, offer card, keyboard, time warp | the user plays a Rookie shift end to end |
| **E. Debrief** | results, time split, offer log, insights, citation, share line, personal bests | the user reviews the debrief across all three markets |
| **F. Polish** | phone layout, Pro difficulty + acceptance rule, URL deep link, unhide the tab | the user tests on a phone |

Browser checks are manual by the user (Apache serves `docs/lab`; we have no
browser access). Every phase that touches Python needs `./build.sh` so the
wheel in `docs/lab/dist/` is current.

### 2.8 Risks and mitigations

- **Dispatch regression.** The refactor touches the hottest code path. The
  seeded-assignment fixture (2.2 test 1) and the existing
  `test_dispatch_performance.py` guard it. The `None` filter path adds only
  one attribute check per block.
- **Interpolation and direction glitches when resuming after an offer.**
  Handled in 2.5 (offer on the even frame, `prev_directions` patched). The
  change is kept isolated so it's easy to bisect, as the memory note asks.
- **Shared worker loop races.** The game uses a distinct settings name and
  the existing `activeRunId` claim. A decision arriving after a reset is
  dropped by the run-id check.
- **Offer droughts in the Slow market**, where the game gets boring. Time
  warp also applies while idle for more than N blocks with no offer
  (optional, decided after calibration), and calibration caps the 90th
  percentile offer gap.
- **Bot results are noisy from a single shift.** The debrief says so, and
  the fleet percentile is the steadier measure.
- **Scope creep from v2 ideas.** v2 items stay in §1.10 until v1 has shipped.

### 2.9 Files at a glance

New: `ridehail/game.py`, `test/test_game.py`,
`test/test_dispatch_offer_filter.py`, `utils/game_calibrate.py`,
`docs/lab/game-tab.js`, `docs/lab/modules/game-offer.js`,
`docs/lab/modules/game-debrief.js`.

Changed: `ridehail/dispatch.py`, `docs/lab/worker.py`,
`docs/lab/webworker.js`, `docs/lab/js/constants.js`, `docs/lab/app.js`,
`docs/lab/js/app-state.js`, `docs/lab/js/message-handler.js`,
`docs/lab/modules/map.js`, `docs/lab/js/keyboard-handler.js`,
`docs/lab/js/phone.js`, `docs/lab/components/game-tab.html`,
`docs/lab/style.css`, `docs/lab/index.html` (unhide, phase F).

### 2.10 Progress log

**2026-09-29: Phase A (core) done.**
- `ridehail/dispatch.py`: `OfferDecision` enum, `Dispatch.offer_filter` hook,
  single-trip dispatch split into `_find_vehicle_sparse/_dense` (pure) and
  `commit_dispatch` (public). Only the DEFAULT method supports the hook.
- `test/test_dispatch_offer_filter.py`: seeded full-state digests recorded
  from the pre-refactor code for three scenarios (dense Town geometry, dense,
  sparse with backlog). They still match, so dispatch is unchanged when no
  filter is installed. Plus hook semantics (accept-all equivalence, decline
  → next-nearest, decline-all, defer) on both search paths.
- `ridehail/game.py`: `GameParams`, `MARKETS`, `DIFFICULTIES`, four `BOTS`,
  `Ledger`, `GameController`, `create_game()`, `shift_seed()`. A whole shift
  runs headless in ~0.3 s. `test/test_game.py` has 13 tests.
- The full suite has 5 failures that also fail on the untouched HEAD. They
  are not caused by this work: `test_regression.py` (city.config takes about
  9 minutes against a 5-minute timeout; the other configs' expected results
  predate newer metrics) and `test_web_animation_quick.py` (uses the removed
  `config.animate`).

**2026-09-29: Phase B (calibration) done.** `utils/game_calibrate.py`,
80 seeds per market:

| Market | Cars | P1 | Idle min / offer | Accept-all | Hourly Thinker | Dollar-a-Km | Rate-Card Loyalist |
|---|---|---|---|---|---|---|---|
| Busy Friday | 80 | 0.00 | ~0 | $14.0 | **$28.0** | $25.7 | $18.1 |
| Normal | 96 | 0.20 | 4.0 | $14.8 | **$16.8** | $16.3 | $16.9 |
| Slow Tuesday | 130 | 0.48 | 12.1 | **$9.8** | $8.6 | $9.1 | $5.9 |

(net $/hr; standard errors ≈ $0.3–0.7). The ranking flips in steps: being
picky roughly doubles earnings when Busy, helps a little in Normal, and
costs money when Slow. Shared market: city 24, demand 5/block, mean trip 12
blocks (GAMMA), inhomogeneity 0.5.

What calibration changed in the design:
1. **Riders cancel after 10 minutes unassigned**
   (`GameParams.max_wait_minutes`). An undersupplied market otherwise has a
   backlog that grows without limit: below ~92 cars, 70–130 riders were still
   stranded at the end of the shift. This needed a small core change:
   `RideHailSimulation.max_wait_time` (default `None`, so nothing changes)
   passed to the existing `_cancel_requests()` stub. With it, Busy holds
   ~20 waiting riders and about 15% of requests are abandoned. The player is
   never offered a rider who is about to give up.
   (2026-10-03: `max_wait_time` is now a regular config parameter, `-mwt`,
   in blocks, default None. `make_game_config` sets it from
   `GameParams.max_wait_minutes`; a game shift plays out identically.)
2. **Fair comparison: each driver is measured from their first idle
   moment.** The player and bots are logged off during warm-up, so they
   start idle. A fleet car on a trip when the shift starts joins when that
   trip ends, and the pre-shift trip doesn't count. Net $/hr is computed over
   each car's own window; the fleet group leaves out cars with windows under
   60 minutes. Without this, accept-all trailed the fleet by ~$2/hr. With it,
   accept-all, Yes-to-Everything and the fleet mean agree to within $0.3/hr
   in every market.
3. **Earnings accrue per block with the rider aboard** (offer ÷ trip
   blocks, with the remainder at drop-off). This replaces the planned
   pro-rata at shift end, and a trip in progress when the shift ends is
   handled the same way for everyone. The ledger keeps its own reference to
   each paying trip, because the sim's garbage collection can drop a
   completed trip in the very block it completes. This was a real bug,
   caught by a test.

Observations for the UI phases:
- **Luck.** A single shift's net $/hr has sd ≈ $3 (Busy) to $5 (Slow). In
  Busy, strategy dominates luck. In Normal and Slow, one shift is mostly
  luck. The debrief should say so, and the shift code (same city, same
  demand) matters for comparing with friends.
- **Decisions per shift.** An accept-all player sees only ~7–10 offers per
  3-hour shift, since each trip plus its pickup takes ~20 minutes. A picky
  player in Busy sees 50+ offers. Time warp should apply while idle in Slow
  as well as while on a trip, so the waits between offers stay short in
  real time. To be tuned in Phase D.
- **Pickups are long when Busy** (P2 ≈ 0.5, ~8 min per pickup). This is
  realistic, and it gives the pickup line on the card real weight.

**2026-09-29: Phases C (bridge), D (playable) and E (debrief) implemented,
not yet browser-tested.** C, D and E were done together, so the first
browser test is the real game rather than a console-driven shift.
- `docs/lab/worker.py`: `init_game()` and `GameSimulation(Simulation)`.
  Wrapper state setup was factored out of `Simulation.__init__` into
  `_init_frame_state()`. An offer and `shift_over` travel only on real-block
  frames, and interpolated frames repeat the previous real block's payload.
  Accepting an offer updates `prev_directions[player]`. Checked headless
  with a fake Pyodide proxy: no offer ever lands on an odd frame, the card's
  car position equals the drawn car, and the shift ends on frame 358. The
  Experiment path was smoke-tested after the refactor.
- `docs/lab/webworker.js`: `game` settings flag → `init_game`;
  `offerHeldSettings/RunId` (the offer freeze); `GameDecision` resumes only
  the run that is holding; `GetGameResults` → `{action: "gameResults"}`;
  time warp via `frameDelayFactor`, which scales both the wait and the
  frame's `animationDelay` so map glides still finish on time.
- `docs/lab/modules/game-map-overlay.js`: a Chart.js plugin, registered in
  `initMap` and inert unless `setGameOverlay()` has set state (`initMap`
  clears it). It draws the player's ring at the car's *animated* position,
  the offer route (unpaid leg amber, paid leg green, torus-aware) over a
  dimming wash, and a guide line to the current pickup or drop-off.
- `docs/lab/game-tab.js` (`GameTab`), `modules/game-offer.js` (card,
  countdown, → / Enter / ← / Esc), `modules/game-debrief.js` (score, rank
  table, fleet percentile, time split, insights, offer log, share line,
  personal best in `localStorage`, data citation),
  `components/game-tab.html`, and a `/* Game tab */` section at the end of
  `style.css`.
- Wiring: `app.js` (construct; leaving the tab stops a game;
  `gameSimSettings` counter no-op), `js/message-handler.js` (game frames →
  `onFrame` outside the render try/catch; `gameResults` → debrief;
  `_simSettingsFor`), `js/keyboard-handler.js` (global shortcuts suspended
  on the Game tab except `g`, because `space` would otherwise start the
  Experiment sim on the shared worker loop).
- Pacing constants (game-tab.js): 400 ms per frame, time warp 0.3× while
  busy and 0.75× while idle. Tune after playing.
- The debrief renderer was run under Node with real Python results: no
  `undefined`/`NaN`.
- `./build.sh` run; the version moved to 2026.9.29.0.

**2026-09-29: Released.** After the user's browser test, the tab was
unhidden (`tab-hidden` removed from `#tab-game` in `index.html`); `g` still
toggles it. Two refinements from that test: the `g` toggle had been broken
since commit `84deb61` (the mapping existed only in the generated
`keyboard-mappings.json`; `ridehail/keyboard_mappings.py` is now the full
source again, and browser and terminal mappings were checked against
before), and the offer card no longer compares the offer with the rate card
(see 1.3). `build.sh` now also strips the Game tab from the PyPI package's
copy of the lab (`ridehail/lab/`, "Experiment + What If only"), and
`GameTab.setupEventHandlers()` does nothing when the markup is absent.

**2026-09-29: Links to tabs (the Phase F deep link, generalised).**
Every tab now has a URL hash (`#what-if`, `#read`, `#toronto`, `#game`;
Experiment, the default, has none). `app.js` keeps the hash in step with
the tab being viewed (`history.replaceState`, so there's no history clutter
and no `hashchange` loop), opens the linked tab on load (showing it even if
it's hidden), and follows later hash changes. The Game tab accepts
`#game?market=busy&code=friday&difficulty=pro` to pre-select its setup
screen. It does not auto-start, so a first-time visitor still sees the
setup and "How it works". Starting a shift writes that link into the address
bar, and the debrief's share line ends with it ("Play the same shift: …").
Phones: a link is the only way into the Game tab (no tab bar). While it's
active the Experiment's phone chrome (hint, speed hint, sheet, action bar)
is hidden and the panel scrolls, and the setup screen has a phone-only
"Explore the full simulation in the Lab" link (`#experiment`). The phone
autoplay demo now runs only when the Experiment tab is showing; otherwise a
`#game` link would start it unseen, holding the worker loop.

**2026-09-29: Downtown shading (all maps).** When inhomogeneity > 0, every
lab map (Experiment and Game) shades the city core in `MAP_CORE`
(first `#d5dce6`, a slightly darker grey; the user then chose steel blue
`#7facca` to match the lab's primary button colour). The game legend's
downtown swatch takes its fill from `MAP_CORE` at runtime, so it can't
drift from the map. `mapCorePlugin` in
`modules/map.js` runs after the land background and before the road grid,
and follows the live inhomogeneity value frame by frame. Its bounds use the
simulation's own arithmetic (`CITY_CORE_FRACTION` mirrors
`City.TWO_ZONE_LENGTH`). This was cross-checked for city sizes 4–200, and it
matches the offer card's "Downtown" label. The game sidebar legend has a
"Downtown" entry.
Also fixed: a phone had failed to load the engine because it used a stale
cached `manifest.json` that named a wheel `deploy.sh --delete` had removed.
`webworker.js` now revalidates `manifest.json` and `worker.py` (`cache:
"no-cache"`).

**2026-09-29: Pro hidden; footnote reworded.** The user decided against a
visible difficulty choice: on a real platform every driver gets the same
time to decide. The Difficulty fieldset on the setup screen is `hidden`, so
every shift is "rookie" (8 s, pay per minute shown). Pro (5 s, no pay per
minute, acceptance-rate timeouts) is kept intact under the hood:
`ridehail/game.py` `DIFFICULTIES`, the JS path, and a hidden link switch
`#game?…&difficulty=pro`. Share links carry `difficulty` only when it isn't
the default, and the debrief names the difficulty only for Pro. The price
footnote now says the rate card and the spread were "calibrated with the aid
of" the offer study. That's accurate: only the median fare for the median
trip and the 10–90% spread of the Lyft cards' fare/fit ratio were used (see
1.4, 1.5). Not reproduced: the study's short-trip discount, the long-trip
tail beyond the 12 km city, platform differences, surge/bonus, and the
empirical shape of the spread. Fitting those (a robust rate-card
regression, and sampling the empirical fare/rate-card ratios by trip-length
band) is a possible next step, and it would need re-calibration of the
markets.

**2026-09-29: No map on phones** (reversed 2026-10-04, Part 14). At phone width (the lab's phone tier,
`body.is-phone`, ≤600px) the map was too small to add much, so on phones
the Game tab hides the map and its legend. The status pane (clock, earnings,
status line) comes first, and the offer card follows it in the page flow
(not a fixed bottom sheet), scrolled into view when it appears.
`message-handler.js` skips `plotMap` for game frames in the phone tier.
The simulation and game logic are unchanged. Tablets (601–800px) keep the
map with the bottom-sheet offer card.

**2026-09-30: Leaderboard (option B: named top scores, plus consistency
checks).** tomslee.net runs PHP 8.1.34 with pdo_sqlite.
- `docs/lab/api/leaderboard.php`: GET a board (`?code=&market=[&difficulty=]`
  → `{count, top}`), POST a score (`{code, market, difficulty, name, version,
  player}` → `{count, top, rank, best, name}`). A board is shift code ×
  market × difficulty. Each name's best counts; names are case-insensitive,
  with no sign-in, so any name can be used by anyone. Standings are computed
  in PHP from the sorted rows, not with SQL grouping, which has
  version-dependent rules; the first SQL version got ranks wrong because
  PDO binds numbers as text.
- Checks: names 1–20 characters (letters, digits, space, `. _ ' -`), a
  built-in blocked-word list plus an optional `blocked-words.txt`; a full,
  consistent 180-minute shift (minutes sum, km ≤ 90, costs = km × $0.30,
  net = earnings − costs, net/hr = net ÷ 3, accepts ≤ offers, trips ≤
  accepts, earnings ≤ $300). A carefully faked but consistent result is
  still accepted: that is the limit of option C, and replay verification
  (option D) would close it. 30 submissions per hour per address; only a
  salted address hash is stored, and it is erased after a day.
- Storage: SQLite in `RIDEHAIL_DATA_DIR`, else `ridehail-data` three levels
  above the script's real path (on the host
  `/home/tomslee/domains/tomslee.net/ridehail-data`, because `~/public_html`
  is a link to `~/domains/tomslee.net/public_html`; outside
  `public_html`, so it's never served and never touched by `deploy.sh`'s
  `rsync --delete`). Created by PHP on first use.
- Moderation: put a long random `admin-token` file in the data directory,
  then `GET …?admin=TOKEN&code=…&market=…` lists entries with ids and
  `POST {action:"delete", token, id}` deletes one.
- Client: `modules/game-leaderboard.js`, a section in the debrief after
  "How you compare". It shows the top 10, the count and a name form (name
  remembered in `localStorage`); ended-early shifts can't be submitted. It
  stays hidden wherever the endpoint doesn't answer with JSON (GitHub Pages
  serves the .php as text; servers without PHP), so the static copies are
  unaffected. `build.sh` excludes `api/` from the PyPI package's copy of
  the lab, and `.gitignore` has `ridehail-data/` (a local Apache setup puts
  the data dir at the repo root).
- Tested in the official `php:8.1-cli` container (the host's version):
  ranks and ties, best-per-name and its displayed spelling, admin list and
  delete, blocklist, rate limit, and rejections (tampered net/hr, short
  shift, bad or blocked names, bad market or code, wrong method). The
  client module was driven in jsdom against it.

Known gaps (Phase F): the game layout on a real phone is untested.
Previously: phones can't reach the tab, because the phone tier
hides the tab bar (needs the URL deep link). Pressing `g` while on the Game
tab hides the tab button but leaves the panel showing. The offer-study
citation has no link yet.

**2026-09-30: Offer card closer to a real one.** Compared with an Uber
card and a third-party overlay app's screenshot. The pickup and trip lines
are now worded as the platform words them ("6 mins (3.0 km) away", "10 mins
(5.0 km) trip", with hours as "2 hr 1 min"), with the platform's
circle-line-square route marker. "(unpaid)" is gone from the pickup line, as
it isn't on real cards; the sidebar legend still says it. The drop-off zone
line stays, as our stand-in for the addresses. The Rookie-only
"$0.55 a minute…" line became a boxed right-hand column of $/km and $/hr
(pickup included), like a third-party overlay app. Pro still shows no
rates. `describe_offer()` now includes `per_km` (the Dollar-a-Km bot uses
it). The rate card is still not shown, and there's still no map inset or
rider rating.

**2026-09-30: Status box shows progress.** The status box in the shift
pane (Idle / Driving to the pickup / Rider on board) is now tinted in the
phase colour instead of only its left border. During a pickup or trip it
fills left to right as a progress bar. `GameController.leg_progress()`
supplies the fraction (in `frame_payload()` as `leg_progress`): the
remaining torus distance to the target, measured against the pickup
distance when the leg is first seen, or against the trip's own distance.
While idle there's no end to show, so the fill sweeps every 2.4 s (none
with reduced motion). The sweep stops while the game is paused or an offer
is up, when the world is frozen. The status box is also full width on
phones (the phone column had kept the grid's `align-items: start`).

**2026-09-30: Pause works with an offer showing.** For teaching use, a
player can pause (button or space) while an offer is up to study it. Only
the card's countdown stops (`OfferCard.pause()/resume()`). The card stays
readable, its buttons and keys are disabled, and the timer shows a pause
sign. Nothing is sent to the worker: it is already holding its loop for the
decision, and a `Pause` message would clear `offerHeldSettings`, so the
decision that followed would be dropped. Resuming doesn't move focus to
Accept, because the space bar's key-up could then press it. Such a shift
sets `shift.pausedOnOffer`: the debrief kicker says "offers paused", and
the leaderboard shows the standings but no name form (like ended-early
shifts). Pauses between offers gain nothing (no decision is pending), so
they don't disqualify a shift. The personal best is unaffected. The flag is
set in the browser, so it's honour-level, like the leaderboard's other
checks. We decided against a separate untimed "Practice" mode for now; a
`#game?…&untimed=1` link switch would be cheap to add later.

**2026-09-30: Running costs $0.56/km, with a source.** `ops_cost_per_km`
went from $0.30 (the presets' undocumented `per_km_ops_cost`) to $0.56, the
median cost per km driven in a 2024 report to the City of Toronto
(https://www.toronto.ca/legdocs/mmis/2024/ex/bgrd/backgroundfile-251343.pdf,
p. 26). It includes fixed and variable expenses, mostly variable. (A driver
the user knows estimates $0.46.) An info button (the lab's
`app-info-popover`, with game-sized text) next to "Running costs" in the
sidebar explains it and links the report. The debrief footnote cites it,
and "How it works" says $0.56. The debrief has the same kind of button after
"running costs (… km)" near the top. Its panel adds the shift's own figures
(cost, km, cost per hour), and it hangs below the whole line
(`.game-info--below`) so it stays on screen wherever the line wraps.

Re-calibration (40 seeds): every net figure falls by about $7.50-8/hr
(0.5 km/min × 60 × $0.26), and the ranking in each market is unchanged,
since the cost barely depends on decisions:

| Market | Accept-all | Hourly Thinker | Dollar-a-Km | Rate-Card Loyalist | Fleet mean |
|---|---|---|---|---|---|
| Busy Friday | $6.7 | **$20.1** | $18.2 | $10.5 | $6.7 |
| Normal | $7.5 | $8.7 | **$9.7** | $8.9 | $7.6 |
| Slow Tuesday | **$1.7** | $0.8 | $1.3 | −$1.9 | $1.1 |

Slow Tuesday now nets about $1/hr on average, and a picky player can end a
shift in the red. The bots' thresholds ($1.00/km, $0.55/min gross) were not
changed.

Leaderboard: `OPS_COST_PER_KM` is 0.56 in `api/leaderboard.php`, and
the new `MIN_SCORING_VERSION` ('2026.9.30.2', the first build with $0.56)
keeps older scores out of the standings (they stay in the database). A
submission from an older page is refused (409, "please reload") before the
cost check, so its error makes sense. Raise the constant whenever a game
change makes old scores incomparable. Tested in `php:8.1-cli`.

**2026-09-30: Pay per hour in three steps.** In the debrief's "Where your
time went", the sentence "per engaged hour … you grossed $X; per hour of
your whole shift you netted $Y" changed two things at once (idle time and
costs). It is now a three-row table (`hourlyStepsHtml` in
`modules/game-debrief.js`): fares per engaged hour → fares per hour of the
shift (idle included; earnings ÷ shift hours, worked out in JS) → after
running costs (the score). A note says Ontario's platform-worker minimum is
the general minimum wage, $17.95/hr from 2026-10-01 (`ONTARIO_MINIMUM_WAGE`),
for engaged time and before expenses, i.e. the first row. It links to
ontario.ca's digital platform workers page and the ESA minimum wage page,
and says whether the player's first row was above it (and, if so, whether
their net fell below it). Update the constant when Ontario's minimum wage
changes.

**2026-09-30: Bots named for their rules.** The informal names
(Yes-to-Everything, Hourly Thinker, Dollar-a-Km, Rate-Card Loyalist) and
their second-line rule text are gone. Each bot is now named for its rule:
"Accept every offer", "Accept only offers of at least $33 per hour",
"… at least $1.00 per km", "… at least the rate card". The hourly one is
stated per hour, not per minute ($0.55), to match the $/hr the offer card
shows. The names are built from `BOT_MIN_PER_KM` / `BOT_MIN_PER_MIN` in
`ridehail/game.py`, the thresholds the bots use, so they can't drift apart.
`Bot.rule` and the results' `rule` field were removed. A note under "How you
compare" says pay per km and per hour include the pickup. The rate-card row
has an info button (`rateCardInfoHtml`) giving the rate card from
`results.params` and saying that offers are the rate card times a random
factor. `.game-table-scroll:has(details[open])` lets the panel escape the
scroll wrapper while it's open. Older entries in this log still use the old
names.
Later the same day the names were shortened to "Takes every offer", "Takes
$33/hr or more", "Takes $1.00/km or more" and "Takes the rate card or more".
"… or more" says which side of the line is accepted, and "/hr" and "/km"
match the offer card's box. We avoided "threshold" (jargon) and "Minimum"
(it could be read as a pay guarantee next to the Ontario minimum wage).

**2026-09-30: Leaderboard on the setup screen.** Next to the shift code, a
preview (`renderBoardPreview` in `modules/game-leaderboard.js`,
`#game-setup-board`) shows the top 5 of the board for the chosen market,
code and difficulty, and "Top 5 of N drivers". The player's remembered name
is highlighted; an empty board says "No scores yet…". It refreshes when the
setup screen is shown, when the market changes, 400 ms after the code is
edited, and after a link sets the fields. Only the latest request is drawn.
It stays hidden where there's no leaderboard endpoint, and the code field
then takes the whole row. On phones the preview sits below the code field.

---

## Part 3: Realistic offer prices (spec, 2026-09-30)

Status: **implemented 2026-09-30** (see 3.11). The answers to the open
questions (3.10): Uber only; keep the invented rate card (published rate
cards describe rider fares only); keep long-pickup pay (with upfront pricing
it's no longer true that drivers are paid only while a rider is aboard);
leave `mean_trip_distance` as it is. Trips stay within the 12 km city.

### 3.1 Goal and principle

Make the distribution of offers as realistic as possible, while keeping it
cheap to compute in the browser. There are two data sources, and each is
good for a different thing:

- **Which trips happen** (the trip mix): the Toronto FOIA trip records
  (`~/src/ridehail-toronto/duckdb/toronto.duckdb`, view
  `uberx_completed_trips`, 123M+ trips 2023-01 to 2024-10). This is the
  population. In the game the trip mix comes from the simulation, so we
  match the simulation to this.
- **What a given trip pays the driver** (the price given the trip): the
  offer study (`~/src/uberdriver/duckdb/uberdriver.duckdb`, schema `offer`,
  view `offers_included`, 18,421 offer cards). Its trip mix is biased (too
  many airport and long trips), but the price of a given trip should be much
  less biased, provided the features that are over-represented are modelled
  and then left out of the game.

So: **trip mix from the city's data, price given the trip from the offer
study.** The game gets a small fitted price model (a few coefficients and a
residual quantile table), not data.

### 3.2 Evidence (queried 2026-09-30)

Trip mix:

| | Offer study (Uber) | Toronto FOIA (UberX, 2% sample, 1.8M) |
|---|---|---|
| Median trip | 7.9 km | 6.2 km (mean 10.3) |
| Share over 12 km | 38% | 28% |
| Pearson pickups | ~12% of all offers (2,157) | ~6% (0.1° cell, an upper bound) |

Toronto trips of 12 km or less: quartiles 2.6 / 4.3 / 6.9 km, 10–90% 1.7–9.5
km, mean 5.0 km. **The game's trips are already close to this**: from played
Normal shifts, quartiles 3.0 / 4.8 / 7.5 km, 10–90% 1.5–9.5 km, mean 5.2 km.
At most a small tweak of `mean_trip_distance` is needed (see 3.5).

Price given the trip (offer study, all platforms, median offer by trip
length):

| Trip km (median) | 1.4 | 2.9 | 4.8 | 6.8 | 8.9 | 10.9 | 13.8 | 17.9 | 24.8 | 37.4 |
|---|---|---|---|---|---|---|---|---|---|---|
| Trip min (median) | 5 | 8 | 11 | 14 | 17 | 18 | 20 | 21 | 25 | 35 |
| Median offer | $4.09 | $5.56 | $7.20 | $8.62 | $10.14 | $11.18 | $13.00 | $15.05 | $19.01 | $25.60 |
| Median $/km | 3.00 | 1.96 | 1.51 | 1.27 | 1.15 | 1.04 | 0.94 | 0.84 | 0.76 | 0.65 |

1. **Pay per km falls steeply with trip length.** Our rate card × a
   lognormal factor (median 0.92) is too flat. Relative to the real median
   offer it pays about right on the shortest trips and about 10–20% too
   much from about 5 km up.
2. **Long pickups are partly paid.** Uber, Toronto pickups, no airport
   (6,174 offers). Offers were compared within cells of trip km (20 bins)
   × trip minutes (10 bins), then averaged by pickup distance:

   | Pickup km | ≤0.5 | 0.5–1 | 1–2 | 2–3 | 3–5 | 5–8 | >8 |
   |---|---|---|---|---|---|---|---|
   | Offer relative to the cell mean | 0.95 | 0.96 | 1.00 | 1.03 | 1.06 | 1.24 | 1.33 |
   | n | 1,106 | 1,444 | 1,983 | 904 | 539 | 152 | 46 |

   This is consistent with a long-pickup payment. The game currently
   treats every pickup as unpaid.
3. **The spread around the typical price is steady.** A log-linear fit
   (log fare on log trip km, log trip min, log(1 + pickup km), airport,
   platform; all offers) has R² 0.82 and residual sd 0.265. The sd is
   0.23–0.29 in every trip-length band, and the residuals are skewed to
   the right (10/50/90%: −0.29 / −0.04 / +0.36). In that fit, airport
   pickups pay +24% and Hopp −20%; Lyft is the same as Uber.
4. Real speed varies with trip length (1.4 km takes 5 min, i.e. 17 km/h;
   37 km takes 35 min, i.e. 64 km/h). Game speed is fixed at 30 km/h.

### 3.3 The price model

    offer = F(trip_km, pickup_km) × ε_trip,  rounded to $0.05

- **F**, the typical offer, depends on **km only**. Time is left out
  because game minutes are always 2 × km; in the fit, the real
  km-to-minutes relation is absorbed into the km terms. Proposed form, to
  be settled by the fitting script:
  `log F = a + b·log(km) + c·log(km)² + g(pickup_km)`, with `g` either
  `d·log(1 + pickup_km)` or piecewise linear with a knee near 4–5 km,
  whichever fits better. `g` is centred so that a typical pickup gives a
  factor of about 1.
- **ε**, the trip's price luck, is drawn from the **empirical residual
  distribution**, stored as about 41 quantiles (2.5% to 97.5%) and sampled
  by inverse CDF with linear interpolation, using the game's own RNG. This
  replaces the assumed lognormal and keeps the real right skew. If the
  spread turns out to depend on trip length, store quantiles for two or
  three km bands instead.
- **Per trip and per driver.** The pickup distance differs for each driver
  who is offered a trip, so the offer does too (as on real platforms). Draw
  ε once per trip, so the trip's "luck" is shared, and evaluate F for each
  driver's own pickup. This changes the bookkeeping in `game.py`:
  - `prices[trip]` becomes the trip's ε and rate card, and each offer is
    computed at dispatch (`describe_offer`).
  - Fleet cars take the fast path in `_offer_filter`, but their pay still
    has to be recorded at dispatch. That's one evaluation of F per fleet
    dispatch, which is cheap.
  - The ledger accrues the **accepted** driver's offer, keyed by (driver,
    trip), not by trip.
  - "If you decline, the next driver sees the same price" is no longer
    true, and the design text (1.4) must change.

Fit sample (proposed): offers not excluded, **Uber only** (10,472; its
pricing is the one the card imitates, and it avoids platform effects in the
residuals), pickup in Toronto, **no Pearson pickups or drop-offs**, trip ≤
15 km (a little beyond 12 so the curve is steady at the edge), `fare`
without `bonus` (see 3.9). **Weights**: each offer is weighted by
Toronto's share of trips in its km band (≤12 km, 1 km bands) divided by the
offer study's share, so the fit concentrates where Toronto's trips are.

### 3.4 The rate card

It is kept as a reference: for the rate-card driver ("Takes the rate card
or more"), the debrief's "vs rate card" column and the rate-card info
button. It no longer generates offers. With a curved F, comparisons with a
straight rate card become realistic: short trips often beat it, long trips
usually don't. Option: replace the invented $2.50 + $0.75/km + $0.18/min
with a documented card. For example, the Toronto effective rate card
(`trip_model` in `toronto_opendata.duckdb`) is a rider-fare card, so it
would have to be scaled to the driver's share, or we'd use Uber's
published Toronto driver rates if we can find them. To be decided (3.10).

### 3.5 Trip mix

Keep GAMMA with the 12 km city (decided). Check the game's trip lengths
against Toronto's trips of 12 km or less (3.2), and if needed nudge
`mean_trip_distance` (now 12 blocks) so the medians match. The game is
currently about 0.5 km long at the median. Trips over 12 km (28% of Toronto
trips) are left out; the debrief footnote should say so.

### 3.6 Implementation

1. `utils/fit_offer_model.py`: reads both DuckDB files (paths as options,
   defaulting to the sibling repos), applies the filters and weights, fits
   F (comparing the forms of `g`) and the residual quantiles, prints
   diagnostics (3.7a), and **writes `ridehail/game_offer_model.py`**. That
   is a generated module of constants: the coefficients, the quantile
   table, and provenance (date, row counts, filters, the offer study's
   latest `sync_run` and git commit, the FOIA months used). No data ships
   in the wheel. The script needs `duckdb`, which is a dev-only dependency
   (not in Pyodide).
2. `ridehail/game.py`: `price()` / `describe_offer()` use the model (3.3).
   The ledger is keyed per (driver, trip), and fleet dispatches are priced
   at dispatch. The `GameParams` multiplier fields go; `price_step` stays.
3. Tests (`test/test_game.py`): replace the lognormal-multiplier test with
   checks that the median offer by km band and the residual quantiles
   reproduce the model; offers rise with pickup distance; ε is shared by
   the drivers offered one trip; earnings still match completed trips.
4. Re-run `utils/game_calibrate.py` and `utils/game_strategy.py`. Check that
   the market flip still holds (picky pays when Busy, not when Slow), and
   re-tune the bots' thresholds ($33/hr, $1.00/km) if the new prices make
   them degenerate.
5. `./build.sh`; raise `MIN_SCORING_VERSION` in `api/leaderboard.php` to
   the new build.

### 3.7 Validation

a. **Fit diagnostics** (printed by the script): residual median and spread
   by km band and by pickup band (flat means F has the right shape), and
   the weighted and unweighted fits side by side.
b. **Game against data**: offers generated by played Normal shifts (the
   game's own trips and pickups) against the reweighted offer study,
   trips ≤12 km. Compare quantiles of offer, $/km and $/hr (pickup
   included), and the median offer by km band. Target: medians within
   about 5%, 10–90% spreads within about 10%.
c. **Markets**: the calibration table (as in 2.10) before and after.

### 3.8 Text and UI knock-ons

- "Unpaid" pickups: the sidebar legend "To a pickup (unpaid)", the status
  line "Driving to the pickup (unpaid)", "How it works" ("The drive to the
  pickup is unpaid"), and the debrief time split and "Three things". Pickup
  *time* is still not paid as such, but long pickups raise the offer.
  Proposed wording: "not paid by the minute; long pickups raise the offer".
- The debrief footnote "About the prices" (now "a rate card times a random
  factor") describes the new model and its sources, and says trips over
  12 km are left out.
- The rate-card info panel ("Each upfront offer is the rate card times a
  random factor") needs rewording.
- Design text 1.4 and 1.5 are superseded by this part.

### 3.9 Left out for now

- **Surge and time of day.** The offers have timestamps (`captured_at`), so
  a "Busy Friday" premium could be estimated later.
- **Airport trips, trips over 12 km, platform differences** (Hopp −20%).
- **Speed varying with trip length** (fixed 30 km/h).
- **`bonus`** (shown on some cards): to check how often it's non-zero and
  whether it should be added to the fare.
- **Selection in the offer study.** The capture tool is assumed to have
  saved offers regardless of price; if it saved some offers selectively,
  the price model inherits that.

### 3.10 Open questions

1. Uber only, or Uber + Lyft pooled (a larger sample, but Lyft's pricing
   differs in shape)?
2. Keep the invented rate card, or move to a documented one (3.4)?
3. Should long-pickup pay be in the model now? It's realistic, but it
   changes the game's "pickups are unpaid" lesson (3.8).
4. Nudge `mean_trip_distance` to match Toronto's median, or leave the game's
   trip mix as it is (0.5 km long at the median)?

### 3.11 Progress log

**2026-09-30: implemented.**

- `utils/fit_offer_model.py` (`uv run --with duckdb --with pandas python
  utils/fit_offer_model.py [--validate N]`) fits the model and writes
  `ridehail/game_offer_model.py`, a generated module of constants with
  provenance. The fit sample is 4,945 Uber offers: Toronto pickup, no
  Pearson, trips ≤ 15 km. Each is weighted by Toronto's share of trips in
  its 1 km band (a 2% sample of 2023-01 to 2024-10, 1.4M trips ≤ 15 km),
  over the study's share. The Toronto sample is seeded, so refits are
  repeatable.
- The chosen form is `log F = 1.3995 + 0.3777 L + 0.0451 L² + 0.0132 p +
  0.0187 max(0, p − 4)`, with L = log trip km and p = pickup km. The
  piecewise-linear pickup term just beats log(1 + p); knees at 3–6 km are
  indistinguishable. An 8 km pickup raises F by about 20%. The weighted
  residual sd is 0.31, wider than the 0.265 of the fit with minutes,
  because speed variation is now part of the luck. The residual medians
  are flat (within ±0.06) across trip and pickup bands. The luck tables
  (99 quantiles, bands <2, 2–6, >6 km) have 10/50/90% about −0.36 / −0.04 /
  +0.40. The minimum offer is $3.06.
- `ridehail/game.py`: `price(trip)` is now (rate_card, luck), drawn once per
  trip. `offer_price(trip, dispatch_distance)` is F × e^luck for that
  driver's pickup, rounded to $0.05. `agreed[(driver, trip)]` records the
  price at dispatch for every taker (the fleet's fast path, bots and the
  player), and earnings accrue from it. The `GameParams` multiplier fields
  were removed. The results' `params` gain `offer_study_offers`.
- Validation (20 Normal shifts, 18,397 game offers, against the reweighted
  study ≤ 12 km):
  - The median offer by 2 km band is within 4% in every band.
  - The offer quantiles 25–90% are within 3%; the 10th percentile is 6% low
    ($4.10 against $4.37).
  - $/km (pickup included) is about 12% low, because game pickups are
    longer (median 2.0 km against 1.2).
  - $/hr is higher (median $35 against $30), because game cars do 30 km/h,
    faster than real short trips.
- Markets (`game_calibrate.py`, 40 seeds). Earnings rose (fleet mean: Busy
  $6.7 → $11.3, Normal $7.6 → $10.6, Slow $1.1 → $3.2), because offers for
  typical trips pay more than the old model did. The sweep
  (`game_strategy.py --skip-refine`, 40 codes, same seat per code) confirms
  the flip still holds:

  | Market | Best $/min threshold | Net at best | Takes every offer |
  |---|---|---|---|
  | Busy Friday | $0.60 ($36/hr) | $19.5 | $10.8 |
  | Normal | $0.50 ($30/hr) | $12.8 | $10.9 |
  | Slow Tuesday | none (accept all) | $3.3 | $3.3 |

  The bot comparison in `game_calibrate.py` has the $33/hr bot ahead of
  accept-all in Slow ($5.4 against $3.7). The bots sit in different seats,
  so that is within the seat-to-seat noise; the same-seat sweep is the one
  to trust. The bots' thresholds are unchanged.
- Wording: "(unpaid)"/"(paid)" was removed from the status box and the
  legend. "How it works", the hourly-steps note and the pickup insight now
  say an offer is a fixed price for pickup and trip together, a long pickup
  raises it a little, and idle time is never paid. The price footnote
  describes the model (Uber only, 4,945 cards, weighted to Toronto's trip
  lengths, no airport, no trips over 12 km, rate card for comparison only).
  The rate-card info panel says offers aren't set from it.
- The leaderboard's `MIN_SCORING_VERSION` is 2026.9.30.5.
- Tests: the lognormal test was replaced by tests of the luck quantiles,
  the shape of F (per km falls, rises with pickup) and shared luck across
  drivers (16 game tests).

**2026-10-08: Validation re-run at the current scale (22 km/h, mean trip 16
blocks).** The 2026-09-30 validation was done at 30 km/h with a 12-block
mean trip. The offer study hasn't synced since 2026-09-28, and a refit
reproduces the stored coefficients exactly, so `offer_model.py` was left
unchanged (`--no-write`). `fit_offer_model.py --validate` gained `--city
big`, which validates in the big city against study trips ≤ 15 km (the
fit's limit) and leaves out the game's longer trips (2%).

Standard city (20 Normal shifts, 33,196 offers, against 4,590 study offers ≤
12 km, weighted):

| | | 10% | 25% | 50% | 75% | 90% |
|---|---|---|---|---|---|---|
| Offer $ | game | 4.15 | 5.60 | 7.85 | 10.75 | 14.05 |
| | data | 4.37 | 5.69 | 7.79 | 10.84 | 13.99 |
| $/km (pickup incl.) | game | 0.79 | 0.95 | 1.22 | 1.62 | 2.13 |
| | data | 0.84 | 1.03 | 1.34 | 1.78 | 2.31 |
| $/hr | game | 17.48 | 21.19 | 27.00 | 36.00 | 47.25 |
| | data | 21.43 | 24.23 | 28.45 | 34.83 | 45.45 |

Big city (10 Normal shifts, 423,178 offers ≤ 15 km, against 4,945 study
offers ≤ 15 km, weighted):

| | | 10% | 25% | 50% | 75% | 90% |
|---|---|---|---|---|---|---|
| Offer $ | game | 4.20 | 5.70 | 8.10 | 11.20 | 14.80 |
| | data | 4.44 | 5.84 | 8.24 | 11.59 | 15.24 |
| $/km (pickup incl.) | game | 0.79 | 1.00 | 1.32 | 1.82 | 2.48 |
| | data | 0.81 | 1.00 | 1.31 | 1.74 | 2.27 |
| $/hr | game | 17.59 | 22.15 | 29.36 | 40.31 | 55.09 |
| | data | 21.56 | 24.36 | 28.68 | 35.05 | 45.79 |

Median offer by trip km band (data, then standard game, then big game):
0–2 km $4.45 / 4.25 / 4.25; 2–4 $6.34 / 6.35 / 6.40; 4–6 $8.41 / 8.25 /
8.25; 6–8 $10.04 / 9.85 / 9.90; 8–10 $11.59 / 11.50 / 11.40; 10–12 $12.73 /
12.90 / 12.90; 12–15 (big only) $14.05 / – / 14.50.

Pickup km, median / 90%: data 1.2 / 3.3 (1.3 / 3.3 at ≤ 15 km); standard
1.9 / 3.7; big 0.7 / 4.4.

Findings:

- **Offers match in both cities.** The median offer by band is within 5%
  everywhere (the worst is 0–2 km, 4–5% low). The offer quantiles are within
  1–5%, a little low at the short end. The F shape is fine: the residual
  medians are flat (−0.06 to +0.02) across trip and pickup bands.
- **$/km depends on pickups.** The standard city's longer pickups make its
  $/km 6–9% low. The big city's pickups are shorter at the median, and its
  $/km matches from the 10th percentile to the median, then runs high in the
  upper tail (+9% at 90%), where short trips with short pickups sit.
- **$/hr is too spread out in both cities, which points to the fixed
  speed.** At 30 km/h the game's $/hr was about 15% high. At 22 km/h the
  median is right (−5% standard, +2% big), but the bottom quarter is 9–18%
  low in both cities, and the top is 3–4% high (standard) or 15–20% high
  (big). Real short trips are slow (about 17 km/h) and long ones are fast,
  so real $/hr is flatter across trip lengths than $/km. In the game every
  km takes the same time, so $/hr follows $/km's steep fall with trip
  length. The big city's pickups are shorter than the standard city's, yet
  its $/hr spread is wider still. So the spread doesn't come from pickup
  length.
- The offer model doesn't need changing. The remaining gaps come from the
  game's mechanics (pickup length and fixed speed), not from F.

**2026-10-08: Long trips (15–18 km) in the big city.** The fit stops at 15
km, but big-city trips reach 17.8 km. Uber cards beyond the fit (same
filters), log(offer / F) with the current F:

| Trip km | ≤ 6 | 6–12 | 12–15 | 15–16 | 16–17 | 17–18 | 18–20 | 20–25 | 25–30 |
|---|---|---|---|---|---|---|---|---|---|
| n | 3,260 | 1,330 | 355 | 85 | 83 | 93 | 134 | 274 | 215 |
| Median | −0.034 | −0.032 | −0.050 | −0.065 | −0.036 | −0.086 | −0.120 | −0.122 | −0.107 |
| 90% | +0.43 | +0.41 | +0.37 | +0.28 | +0.45 | +0.27 | +0.28 | +0.25 | +0.25 |

- **The extrapolation holds to 18 km.** Over 15–18 km the median residual
  is about 2–3% below the in-fit level of about −0.035, within the noise of
  about 85 cards per band. A fit extended to 18 km (5,206 cards) moves F by
  1.3% or less anywhere in 0–18 km, so a refit isn't worth a scoring reset.
  Beyond 18 km, F's L² term makes it overshoot by about 9% (slope in log km
  0.49 in the data against F's 0.63 at 16.5 km). No game city reaches that
  far.
- The upper tail of the luck is narrower on long trips (90% about +0.28,
  against +0.39 in the > 6 km luck table), so the game's long trips get a
  little too much upside. The samples are small.
- Game against data (5 big-city Normal shifts), median offer: 12–15 km
  $14.45 / $14.17; 15–16 $15.85 / $15.29; 16–17 $16.25 / $16.69; 17–18
  $17.10 / $16.39. Within ±4%.
- **The game has too few long trips.** Share of trips ≤ 17.8 km (FOIA)
  against share of big-city offers: 12–15 km 7.2% / 4.8%; 15–17.8 km 5.0% /
  2.1%. (A further 18% of all Toronto trips are over 17.8 km.) The cause is
  the GAMMA shape, not the city size: Gamma(2, 8 blocks) puts only 1.7% of
  draws beyond 48 blocks (rejected and redrawn), and its tail is thinner
  than Toronto's (P(> 12 km) is 9% for the Gamma against 28% in Toronto).
  GAMMA matches Toronto's shape up to 12 km (3.2), but not the tail.
  Fixing that means changing the trip-length distribution, which would
  change the market calibration. **Decided: leave it.** The shape stays
  GAMMA; chasing the tail would be endless tinkering for an accuracy beyond
  the game's goals.

---

## Part 4: What riders paid (2026-09-30)

Status: **implemented 2026-09-30.** Busy Friday fares (4.6) are written up
but not implemented.

### 4.1 Goal

Say what riders probably paid for the trips a driver took, and how much of it
reached the driver, using City of Toronto data limited to 2026.

### 4.2 Source

`~/src/ridehail-toronto/duckdb/toronto_opendata.duckdb`, table `trips`: the
City's PTC open data
(https://open.toronto.ca/dataset/private-transportation-companies-summary-and-trip-data/).
The rows are hourly origin-destination cells (ward to ward) with the mean
fare, distance and duration of `trips_total` trips, from 2018 to 2026-07.
The fare is trip fare + City of Toronto fees + HST, excluding tips and
promotional discounts, for all platforms and products together (no
breakdown). The offer study's Uber offers date from 2026-01 to 2026-08
(median March), so the two sources line up in time.

### 4.3 The fare model

`fare = base + per_km × km`, fitted by weighted least squares (weight =
trips) on 2026 cells, Toronto to Toronto, averaging ≤ 15 km: **$8.11 +
$1.018/km** (2026-01 to 2026-07, 40.4M trips, cell rse $3.39). The fixed $8
absorbs the booking fee, minimum fares and City fees. Distance only: game
minutes are always 2 × km, and a model that is linear in km is unbiased on
cell means if fares are linear within a cell. Adding duration fits cells
better ($4.42 + $0.25/km + $0.57/min), but it needs realistic minutes, which
the game doesn't have. Month to month, the fitted 5 km fare ranged from
$12.35 (March) to $14.16 (January). The project's own check against the
FOIA UberX-only data (2023-24) found the blended typical fares within 1–4%
of UberX, so the product mix is a small effect.

### 4.4 Per-trip fares share the trip's luck

A first version used the typical fare for every trip. Picky strategies then
showed driver shares over 100% (the $1.00/km bot: 123%), because they select
trips whose offers came out high while the rider fare stayed typical. On
real trips the two move together: the uberdriver pay-statement analysis
(`~/src/uberdriver/analysis_upfront_pay.md`, US data) found the platform's
take at 16% ± 7% per trip, far steadier than offers (luck sd ≈ 0.31). So
each trip's rider fare is the typical fare × e^luck / mean(e^luck in its
band). The trip's luck is the one its offer uses, and the normalisation
keeps the average fare equal to the City's. The driver's share then varies
with trip length and pickup, not with luck.

### 4.5 Implementation

- `utils/fit_offer_model.py` also fits the fare (`fit_rider_fare`,
  `--opendata-db`) and writes `RIDER_FARE_BASE`, `RIDER_FARE_PER_KM`,
  `RIDER_FARE_MONTHS` and `RIDER_FARE_TRIPS` into
  `ridehail/game_offer_model.py`.
- `ridehail/game.py`:
  - `typical_rider_fare(km)`, `rider_fare(trip)` (4.4) and `HST_RATE = 0.13`.
  - Every offer dict has `rider_fare`.
  - `Ledger.rider_fares` accrues per block alongside earnings (with
    `accrued_fare`), so a trip in progress at the end of the shift counts
    the same share of both.
  - The summaries add `rider_fares`, `rider_hst` and `driver_share`
    (earnings ÷ pre-HST rider fares).
  - `results.params` adds the fare model and months.
- Debrief (`modules/game-debrief.js`):
  - a "Share of fares" column in "How you compare", with a note;
  - a "What your riders paid" section after the hourly steps (total, HST,
    your earnings, your share, "the rest went to the platform, apart from
    the City's per-trip fees");
  - a "Rider paid†" column in "Your offers";
  - "About the prices" cites the open data for the fare estimate, with the
    months, and explains 4.4.
- The offer card doesn't show the rider fare: drivers don't see it when
  deciding.
- Scoring is unchanged, so `MIN_SCORING_VERSION` stays. The leaderboard
  ignores the new fields.
- Tests: rider fares match completed trips plus the part in progress; the
  typical fare is linear; the average fare over many trips equals the
  typical fare; the per-trip driver share varies < 5% between its 10th and
  90th percentiles (18 game tests).

Results: fleet drivers receive 74% (Normal, Slow) to 78% (Busy, longer paid
pickups) of what riders paid before HST. In one Busy shift, the strategies
ranged from 71% to 82%.

### 4.6 Later: Busy Friday fares (not implemented)

Rider fares vary with the time of day and the day of the week, and the open
data has hourly cells. Fit the fare model (or just its level) for Friday
evenings, e.g. 18:00–02:00, and use it for the Busy market, and a quiet
weekday slot for Slow. The offer study's timestamps (`captured_at`) could
give the same by-time scaling for driver offers, so fares and offers would
move together. The market descriptions on the setup screen would then
describe a real time of week, not just the balance of supply and demand.

---

## Part 5: How realistic are the markets? Diagnosis (2026-09-30)

Status: **diagnosis done. Option (a) was tried on 2026-09-30 and reverted (5.6): the markets are unchanged (80 / 96 / 130 cars, 5 requests/min, inhomogeneity 0.5). Still open: the simulation-core fix (5.7), the 30 km/h speed (5.8) and the comparison with the City-commissioned report (5.9).**

### 5.1 The question

Players net about $11–12/hr (Busy, Normal), which seemed high next to the
City-commissioned report. Is idle time underestimated?

### 5.2 How the markets were set

`MARKET_SHARED` sets city 24, 5 requests/min, mean trip 12 blocks (GAMMA),
inhomogeneity 0.5 and a 1-minute pickup stop. The markets differ only in
fleet size: Busy 80, Normal 96, Slow 130. The fleet sizes were tuned with
`game_calibrate.py` to game-design targets (P1 ≈ 0 / 0.2 / 0.5 and the
strategy flip), never to real time shares.

### 5.3 The City's 2026 time split

From `operating_hours` (hourly, per vehicle, 2026-01 to 2026-07, Toronto
time):

- Idle: from 11% (weekday 8 am) to 46% (Tuesday 1 am); 30% on average.
- Pickup (en route plus waiting): 13–16% at nearly every hour, of which
  waiting at the pickup is about 3%.
- With a rider: 43–56%.
- Slices: Fri/Sat 19–01h 0.31 / 0.13 / 0.56; weekday 10–15h 0.33 / 0.13 /
  0.54; Tue/Wed 01–05h 0.40 / 0.16 / 0.43.

The game has Busy 0.00 / 0.50 / 0.50, Normal 0.19 / 0.30 / 0.51 and Slow
0.46 / 0.16 / 0.38. Busy is unrealistic, and Normal's pickups are twice the
City's. The City's unpaid share (idle plus pickup, about 45%) is close to
the game's Normal (49%), but it's mostly idle time rather than pickups. The
price side agrees with the offer study: net per engaged hour (engaged costs
only) is $16.70 in the game's Normal, against the workbook's $15.60.

### 5.4 Diagnostic (`utils/game_pickup_diagnostic.py`)

City 24, Normal (96 cars, 5 requests/min) unless noted; 3 seeds, 180
measured blocks.

| Case | P1 / P2 / P3 | Pickup (blocks) vs ideal | Core: requests / idle cars |
|---|---|---|---|
| inh 0.5 (now) | 0.19 / 0.30 / 0.51 | 4.8 vs 3.7 | 0.63 / **0.05** |
| inh 0 | 0.27 / 0.22 / 0.52 | 3.2 vs 3.0 | 0.25 / 0.25 |
| inh 0.4 | 0.22 / 0.26 / 0.51 | 4.1 vs 3.4 | 0.54 / 0.07 |
| inh 0.75 | 0.06 / 0.43 / 0.51 | 7.6 vs 5.3 | 0.82 / 0.03 |
| inh 0.5, no pickup stop | 0.27 / 0.21 / 0.51 | 4.1 vs 3.0 | |
| 2× density (192/10), inh 0 | 0.33 / 0.16 / 0.51 | 2.1 vs 1.9 | |
| 2× density, inh 0.2 | 0.31 / 0.17 / 0.51 | | 0.11 idle in core |
| 2× density, inh 0.25 | 0.30 / 0.18 / 0.51 | | 0.08 idle in core |
| 2× density, inh 0.4 | 0.28 / 0.21 / 0.51 | 3.0 vs 2.0 | 0.54 / 0.05 |

Findings:

1. **Cars drain out of the core.** Inhomogeneity concentrates *origins*
   only. With GAMMA (and EXPONENTIAL, RAYLEIGH) trip distances,
   `Trip._set_destination_sampled` places the destination at the drawn
   distance from the origin, in a random direction. So
   `inhomogeneous_destinations` has **no effect** for these distributions;
   only UNIFORM uses it, via `City.set_location`. Trips leave the core,
   idle cars collect in the outskirts (5% of idle cars are in the core,
   which is 25% of the area, against 63% of requests), and pickups come in
   from outside. Idle cars drift at random (`idle_vehicles_moving`) rather
   than returning towards demand. This is what makes P2/P1 depend so
   strongly on inhomogeneity. Also,
   `RideHailSimulation.__init__` sets `mean_trip_distance = city_size // 2`
   whenever `inhomogeneous_destinations` is on, whatever the distribution.
2. **Density.** At the same inhomogeneity, doubling cars and requests
   shortens pickups (ideal distance ∝ 1/√idle density).
3. **The pickup stop** (`pickup_time = 1`) is about 5% of all time, against
   the City's 3% waiting.
4. **City 48** at the same density (×4 cars and requests) overloads: P1
   0–4%, pickups 9–13 blocks, and 8–17% of riders give up. Trips are
   longer there because the GAMMA draw is cut off at the city size (24 or
   48 blocks), so the 24-block city loses more of the long trips (mean
   about 10.4 against about 12 blocks). The 24-block city's match to
   Toronto's trips ≤ 12 km (Part 3) partly depends on this cut-off. With
   520 cars (×1.35), city 48 has P1 0.36, P2 0.21, P3 0.44 (inh 0.5). At
   2× density (768/40), inh 0 gives 0.21 / 0.19 / 0.60; inh 0.4 gives
   0.06 / 0.38 / 0.57.

### 5.5 Options for step 2 (to decide)

a. **Keep city 24; double the density and lower inhomogeneity to about
   0.2–0.25.** This reproduces the City's average split (0.30 / 0.17 /
   0.51) with no core change. Busy and Slow would then be set as
   fleet-size variations around it, targeting the City's busy-hour and
   quiet-hour idle shares (about 15–20% and 40–45%), both with pickups
   near 15%. The web map has twice as many cars.
b. **Make destinations follow inhomogeneity for the sampled distributions**
   (a core change, e.g. rejection-sampling destinations towards the core at
   the drawn distance). This keeps a stronger downtown, and it would also
   fix the silent no-op for other users of those distributions. It needs
   care with the torus, and regression tests for existing configs.
c. **Move to city 48.** This needs `mean_trip_distance` re-checked against
   Toronto's trip mix, since the cut-off changes, and a fleet re-tuned for
   the longer trips. It's four times the cars to animate.
d. **Shorten the pickup stop** (0 blocks, or make it part of the block).
   This affects the animation timing, so it's small but not free.

Whatever is chosen, re-run `game_calibrate.py` and `game_strategy.py`: the
"picky pays when Busy" result depends on Busy's zero idle time and long
pickups.

### 5.6 Option (a): tried, then reverted

`MARKET_SHARED`: 10 requests/min (was 5) and inhomogeneity 0.25 (was 0.5);
city 24, trips as before. The fleet sizes come from a search (4 seeds per
size), targeting the City's 2026 split:

| Market | Cars (was) | Idle / pickup / with rider | City reference |
|---|---|---|---|
| Busy | 175 (80) | 0.20 / 0.24 / 0.56 | busier hours (11–25% idle) |
| Normal | 192 (96) | 0.30 / 0.18 / 0.51 | 2026 average 0.30 / 0.15 / 0.55 |
| Slow | 225 (130) | 0.43 / 0.14 / 0.43 | Tue/Wed 01–05h 0.40 / 0.16 / 0.43 |

The overload edge is sharp: 160 cars give 0.02 / 0.43 / 0.56 with 6% of
riders giving up, and 165 cars give 0.10 idle. So Busy stays at 175.
Nobody gives up at the three market sizes.

Strategy sweep (`game_strategy.py --skip-refine`, 40 codes, same seat, net
$/hr):

| Market | Takes every offer | Best threshold | Net at best |
|---|---|---|---|
| Busy | $13.51 | $0.50/min ($30/hr), accepts 77% | $15.07 (+$1.56) |
| Normal | $11.15 | $0.60/min, accepts 65% | $11.24 (flat) |
| Slow | $5.15 | $0.40/min, accepts 95% | $5.49 (flat) |

Fleet mean: Busy $13.20, Normal $10.35, Slow $6.19. **The game's lesson
changes.** With realistic idle and pickup times, being picky gains a little
only when it's busy, and nothing in normal or slow markets. High thresholds
cost money everywhere. The old "picky roughly doubles earnings when Busy"
came from the unrealistic Busy market (no idle time, pickups half of all
time). Earnings levels changed little (Normal $10.6 → $10.35), so the gap
to the City-commissioned report isn't explained by idle time. It lies in
the price side (offers, and the game's steady 30 km/h making paid minutes
productive) or in the report's definitions (still to compare).

**Decision (2026-09-30): reverted.** Earnings hardly moved, and with
realistic markets thresholds barely help, which removes most of the
strategy in the game. The user reverted the uncommitted changes: the
market values in `ridehail/game.py`, the setup screen's descriptions, the
leaderboard's `MIN_SCORING_VERSION` (back to 2026.9.30.5) and the version
bump. These notes and `utils/game_pickup_diagnostic.py` were kept. The
tuned values are here in case they're wanted later (for example, a
"realistic" market alongside the three game markets). Worth knowing: the
game's markets are deliberately not realistic in idle and pickup time;
Busy in particular has no idle time and half of all time spent on pickups.
If this is ever revisited, the names "Busy Friday" and "Slow Tuesday"
fit loosely. In the City's data Friday evenings are about 23–35%
idle, and Busy matches weekday rush hours and weekend afternoons better. See
also the Busy Friday fares idea (4.6).

### 5.7 Outstanding: destinations ignore inhomogeneity (simulation core)

With GAMMA, EXPONENTIAL or RAYLEIGH trip distances,
`Trip._set_destination_sampled` (`ridehail/atom.py`) places a destination
at the drawn distance from its origin, in a random direction.
`inhomogeneous_destinations` is silently ignored; only UNIFORM honours it,
via `City.set_location(is_destination=True)`. In addition,
`RideHailSimulation.__init__` resets `mean_trip_distance` to
`city_size // 2` whenever `inhomogeneous_destinations` is on, whatever the
distribution. The effect: inhomogeneity concentrates origins only, trips
carry cars out of the core, and idle cars collect in the outskirts (5% of
idle cars downtown against 63% of requests at inh 0.5). This inflates
pickups whenever inhomogeneity is high. A fix would draw destinations
towards the core at the sampled distance, for example by rejection
sampling among the candidates at that distance, weighted by core
membership. It would need regression tests for existing configs, and the
game's markets would need re-tuning afterwards (inhomogeneity could then go
back up).

*Correction (2026-10-05):* the reset of `mean_trip_distance` to
`city_size // 2` described above (and in 5.4) was in unreachable code after
a `return` in `RideHailSimulation.convert_units`, so it never ran; that code
has been removed.

### 5.8 To investigate: the fixed 30 km/h speed

The game runs at one block (0.5 km) per minute, 30 km/h, for every trip and
pickup. Real Toronto trips are much slower, and their speed depends on
length. From 2026 open-data cells (Toronto to Toronto, trip-weighted; cell
means, so approximate):

| Trip km (cell mean) | 1.9 | 2.5 | 3.5 | 4.4 | 5.5 | 6.5 | 7.5 | 8.4 | 9.5 | 10.5 | 11.5 |
|---|---|---|---|---|---|---|---|---|---|---|---|
| Minutes | 7.9 | 9.6 | 11.4 | 12.3 | 13.8 | 15.6 | 17.7 | 18.7 | 20.2 | 22.7 | 23.5 |
| km/h | 14 | 16 | 18 | 22 | 24 | 25 | 25 | 27 | 28 | 28 | 29 |

Most trips are 2.5–5.5 km, at 16–24 km/h, so a typical game trip takes
only about 55–80% of its real time. Offers are priced by km (Part 3), so
the game pays a real trip's money for fewer minutes. Paid time is too
productive, and $/hr is inflated (Part 3's validation: median $/hr $35 in
the game against $30 in the offer data). Pickups are also driven at 30
km/h, which shortens unpaid time too. This is the most likely reason the
game's earnings sit above the City-commissioned report's (5.6 shows idle
time isn't it).

Ideas, none tried yet:
- **A slower block.** Make one block about 0.35–0.4 km at one minute
  (21–24 km/h). Then the city is 8.4–9.6 km across, trips measured in
  blocks are shorter in km, and F(km) pays less per minute. This needs
  `km_per_block`, the offer model's km inputs, the running cost per km, the
  debrief's "12 km" wording and the trip-length match (Part 3.5: re-check
  `mean_trip_distance` against Toronto's km mix) to change together.
- **Price offers by minutes as well as km.** Refit F with the real trip
  minutes (the offer study has `trip_min`) and feed it realistic minutes
  for the game's km (from the table above), not the game's own. This
  changes pay without changing the map, but the card's minutes would still
  be the game's.
- **Length-dependent speed.** Short trips slow, long trips fast. The
  simulation moves every car one block per block, so this would be a core
  change. Probably not worth it.

Check any change with `fit_offer_model.py --validate` ($/hr against the
data), `game_calibrate.py` (earnings levels) and `game_strategy.py` (does
the strategy lesson survive?).

### 5.9 To do: compare with the City-commissioned report

The user noted that the report's driver earnings are lower than both the
game's (about $11–12/hr net in Busy and Normal) and the offer study's
($15.60/hr after costs, idle time excluded). We still need the report's
figure and its definition (per logged-in or engaged hour; which expenses)
to compare like with like.

*2026-10-04:* the report has been read; its figures, definitions and page
numbers are in `claude/game-reality-references.md`. Net per in-app hour:
median $5.97 (2024) against the game's ~$10 (Normal, Busy). A lead to
check: the report's median cost of $16.31/hr at $0.56/km implies ~29 km
driven per hour, against the game's ≤ 22. Also found: the report's driver
share of fares (40-60%) is far below the game's (74-78%).

### 5.10 Is draining the core realistic? Tidal flows in Toronto

The user asked whether the drain reflects a real effect: mornings bring
trips into the centre, and evenings take them out. From 2026 open data
(`trips`, the core taken as wards 10 Spadina–Fort York, 11
University–Rosedale and 13 Toronto Centre; local time):

| | Start downtown | End downtown | Net into the core |
|---|---|---|---|
| Weekday, all day | 29.0% | 27.5% | −1.5 points |
| Weekend, all day | 33.1% | 30.0% | −3.1 points |

Net by hour, in points (end share minus start share):

- Weekday: 06–10h +3 to +5 (inbound); 11–18h 0 to ±2; 19–23h −3 to −10;
  00–04h −11 to −15.
- Weekend: daytime about 0; 22–23h −3 to −6; 00–04h −11 to −23 (the
  peak is 03h).

The game (inhomogeneity 0.5, GAMMA distances; the core is 25% of the area)
starts 63% of trips in the core and ends 31% there: **−32 points at every
hour**. At inhomogeneity 0.25 it's 44% / 28%, −16 points.

So there is a real tidal effect: a mild inflow in the weekday morning, and
an outflow late at night, strongest when the bars close at weekends. But the
game's drain is stronger than Toronto's most extreme hour and runs all day.
It also can't be separated from how busy downtown is. In Toronto, downtown
attracts trips about as strongly as it generates them (29% / 27.5%, from a
small share of the city's area), and the model can't produce that with
sampled trip distances (5.7). Real pickups also stay at 13–16% of time even
in the hours with the strongest outflow, presumably because drivers
reposition towards demand, while idle cars in the model drift at random.

Implication for the 5.7 fix: give origins and destinations **separate
concentration settings** rather than one switch. Equal settings would give
a busy, balanced downtown (daytime); a little more on origins would give
the evening outflow; more on destinations the morning inflow. Markets
could then represent real times of day (compare 4.6), with a drain of
realistic size.

**5.8, continued (2026-09-30): variable speed, and slowing idle cars.**

- **"Time = distance" carries weight in the core model, beyond display.** City-scale
  pricing folds per-km and per-minute prices into one per-block price
  (`simulation.py`, around 533 and 1063). WAIT_FRACTION equilibration uses
  TRIP_DISTANCE as ride time (around 1336). The presets' Little's-law relation
  P3 = demand × trip length / vehicles assumes one block moved per block.
  Moving a P2/P3 car with a probability < 1 would be trivial in itself (as
  idle cars already do), but every consumer above would have to separate
  time from distance. Decision: keep uniform speed in the general model.
  If ever wanted, the most natural form is a **congested core** (a lower
  move probability downtown), which gives length-dependent average speeds
  without a speed-by-length rule.
- **Slowing idle cars is already supported:** `idle_vehicles_moving` is a
  probability (`Vehicle.update_location`); the game sets 1.0. City 2026
  (`summary_stats`, distance share ÷ time share) gives speeds relative to
  on-trip of: idle 0.45; en route 0.61 (0.48 including waiting). Game
  shifts, accept-all fleet, 8 codes, idle moving 1.0 → 0.45:

  | Market | Idle / pickup / rider | Net $/hr | km/hr |
  |---|---|---|---|
  | Busy | unchanged (no idle) | $10.79 → $10.85 | 28.5 → 28.5 |
  | Normal | 0.20/0.30/0.50 → 0.19/0.31/0.51 | $10.85 → $12.64 | 28.4 → 25.3 |
  | Slow | 0.48/0.16/0.36 → 0.45/0.18/0.37 | $3.14 → $7.44 | 28.8 → 21.4 |

  It barely changes the time split, and it raises earnings through lower
  idle running costs, away from the City-commissioned report. It's
  realistic for costs, and it makes declining cheaper in slow markets, so
  the strategy results would need re-checking.
- **Recommended experiment: a slower block**, with no change to the model.
  One block = one minute = about 0.37 km (22 km/h, typical of Toronto
  trips under 12 km), via `mean_vehicle_speed` / `minutes_per_block` and the
  game's `km_per_block`. Knock-ons in the game layer: offers (F by km),
  running costs per km, the city's size in km (24 blocks = 8.9 km; about 32
  blocks for 12 km trips, which needs more cars; see 5.4), `mean_trip_distance`
  to keep Toronto's km mix, the debrief's "12 km" text, then
  `fit_offer_model.py --validate`, `game_calibrate.py` and
  `game_strategy.py`. Probably combine it with idle moving at 0.45. Judge it
  as in 5.6: do earnings come down, and does the strategy lesson survive?

**5.8 experiment (2026-09-30): the slower block, implemented on `dev`.**
The model is unchanged: a block is still a minute and a distance. Only the
game's scale changed.

- `ridehail/game.py`:
  - `KM_PER_BLOCK = 0.37` (22 km/h), used by `GameParams.km_per_block` and
    `mean_vehicle_speed`.
  - `MARKET_SHARED`: city 32 (11.8 km, so "12 km" still holds),
    `mean_trip_distance` 16 blocks, demand 9/min (5 × area ratio),
    inhomogeneity 0.5.
  - `MARKETS`: Busy 180, Normal 215, Slow 300.
  - Trip lengths: 10/25/50/75/90% 1.5 / 2.6 / 4.4 / 7.0 / 9.2 km, mean 4.9
    (Toronto ≤ 12 km: 1.7 / 2.6 / 4.3 / 6.9 / 9.5, mean 5.0).
  - The fleets were searched (3 seeds) to keep the earlier split. Busy
    0.00 / 0.46 / 0.54 with 15% of riders giving up; Normal 0.19 / 0.26 /
    0.54; Slow 0.47 / 0.14 / 0.39.
- Other files: `game-tab.js` `GAME_CITY_SIZE = 32`; `leaderboard.php`
  `KM_PER_MINUTE = 0.37` and `MIN_SCORING_VERSION` 2026.9.30.10; the
  sidebar's idle cost "about $12 an hour" (was $17); the debrief footnote
  gives the 22 km/h; `fit_offer_model.py --validate` uses the game's minutes
  per km; tests use `km_per_block` rather than 0.5.
- Offer validation (20 Normal shifts): the median offer by km band is within
  about 5%. **$/hr (pickup included): median $27.21 in the game against
  $28.45 in the data** (before: $35 against $30). The spread is wider,
  because all trips run at 22 km/h.
- Calibration (40 seeds), fleet mean net $/hr: Busy $9.29 (was $11.25),
  Normal $9.14 (was $10.64), Slow $2.75 (was $3.16), about 15% lower.
  Offers per shift for an accept-all player: 8.1 / 8.1 / 5.6. Slow now
  averages 25 idle minutes per offer (was about 12).
- Same-seat sweep (40 codes): Busy $9.04 → $17.42 at $0.50/min (+$8.40,
  accepts 20%); Normal $10.09 → $11.39 at $0.50/min (+$1.30); Slow $4.12 →
  $4.53 at $0.40/min (flat, within noise). **The lesson survives**, as before
  (Busy +$8.70, Normal +$1.90). Net pay rises and then falls with the
  threshold in every market: a moderate threshold (declining the worst
  offers) pays when offers come quickly, and very high thresholds (declining
  nearly everything, e.g. Busy $0.90/min, 2% accepted, −$0.79/hr) lose
  everywhere, because idle time and its running costs outweigh the better
  trips.
- To check in the browser: the 32-block map with 180–300 cars (smoothness,
  worker frame time), and the longer idle waits in Slow. `WARP_IDLE` in
  `game-tab.js` could be lowered if they drag.

## Part 6: Rate helper vs Platform only (2026-10-01)

### 6.1 Decision

The dormant "Pro" difficulty is replaced by a visible choice of **offer
screen**, which differs from the default in one thing only: whether the
offer card carries the **rate helper**, the boxed $/km and $/hr (pickup
included, over the whole offer). In the real world that box comes only from
third-party apps such as GigU; a platform's own card doesn't have it. So the
choice is about information, not skill, and "Rookie/Pro" (which suggested a
skill ladder, and made the helper look like training wheels) is gone.

- Names: **Rate helper** (default) and **Platform only**. Internal key
  `card`, values `helper` / `platform` (`ridehail.game.CARDS`).
- Both have the 8 s timer and no acceptance-rate rule. Pro's 5 s timer and
  acceptance rule are retired; the rule stays in `GameParams` as a dormant
  option (1.8).
- The default stays Rate helper, so the existing scores (all made with it)
  stay on the default board.

### 6.2 Setup screen

After the market choice, a fieldset whose legend is the user's wording:
"Third-party apps help drivers by showing the pay rate. Use a helper app?"
with two options:
- *Rate helper*: "Each offer also shows what it pays per km and per hour,
  pickup included."
- *Platform only*: "Just the platform's card: the price, the pickup and the
  trip."

The last choice is remembered in `localStorage` (`ridehail.game.card`); a
link's `card=` overrides it. "How it works" adds to the offer bullet that
the rate helper shows pay per km and per hour, and that each choice has its
own leaderboard.

### 6.3 Offer card

With the rate helper, the box is styled as an add-on laid over the
platform's card, not part of it: a dashed border, a neutral background and a
"Rate helper" caption. With Platform only the box is hidden and the route
column takes the full width.

### 6.4 Leaderboards and labels

- **Separate boards**: a board is shift code × market × offer screen.
  Mixing would rank Platform-only players against players with more
  information. The setup preview follows the selected offer screen, and
  both board titles name it ("Normal · Platform only").
- The debrief kicker and share line always name the offer screen (the old
  Rookie label was empty). Shift links always carry `card=`, so a friend
  plays on the same board.
- Personal bests are keyed by market + card; a Rate-helper best falls back
  to the old `…<market>.rookie` key.

### 6.5 Debrief

- Platform only: a note above "Your offers" says the "Per hour*" column is
  what a rate helper app would have shown on each offer, so the information
  the player went without is shown afterwards.
- Platform only: a note under "How you compare" says the automated drivers
  that go by $/km or $/hr see what a rate helper would show (two of the
  four bots decide on those figures).

### 6.6 Implementation

- `ridehail/game.py`: `DIFFICULTIES` → `CARDS`; `create_game(..., card=)`
  validates it. `test/test_game.py`: `test_offer_screens`, and the
  acceptance-rule test now turns the rule on through `GameParams`.
- `docs/lab/worker.py`: reads `card` from the game settings.
- `docs/lab/game-tab.js`: `CARDS`, remembered choice, links (`card=`;
  old `difficulty=rookie|pro` links map to helper|platform).
- `modules/game-offer.js` (`show(offer, seconds, helper)`),
  `modules/game-debrief.js`, `modules/game-leaderboard.js`,
  `components/game-tab.html`, `style.css`.
- `api/leaderboard.php`: column `difficulty` → `card`, `CARDS`. On the
  first request after the update, `migrate_difficulty()` deletes the old Pro
  rows (their rules aren't comparable), sets the Rookie rows to `helper`,
  and renames the column. A request without `card` from a page loaded before
  the update counts as `helper`, unless it says `difficulty=pro`, which gets
  the 409 "please reload". Tested in `php:8.1-cli`: migration, board
  queries for both cards, legacy parameters. `MIN_SCORING_VERSION` is
  unchanged (Rate-helper scoring didn't change).
- Version 2026.10.1.0 (wheel rebuilt). The web needs the new wheel: the old
  `create_game()` doesn't accept `card`.

### 6.7 During the shift (2026-10-01)

Above the sidebar's "Shift time left", a line names the market and offer
screen being played, e.g. "Busy Friday · Rate helper" (`#game-shift-label`,
set in `GameTab.start()`). It has its own line because the 300px sidebar
can't fit it beside the clock label.

### 6.8 Your car's ring (2026-10-01)

On the bigger map the player's thin dark ring (2.5px, 1.7× the car's
radius) was hard to spot. It is now violet `#7c3aed` (a colour nothing else
on the map uses), 4px wide at 2× the radius, with an 8px white halo
underneath (`game-map-overlay.js` `RING_COLOR`, `--game-you` for the legend
swatch). "How it works" says "violet ring". The user found it an improvement.

**Pulse (kept, 2026-10-01).**
`pulseGameCar()` in `game-map-overlay.js` plays a "here you are" pulse: 3
violet rings, 250 ms apart, each growing from the ring's size to 3× and
fading over 1 s (1.5 s in all), drawn under the ring. `GameTab.onFrame()`
calls it on the shift's first frame and when an offer appears. While it
plays, a `requestAnimationFrame` loop calls `chart.draw()`; it does nothing
with reduced motion or without a map, and `setGameOverlay(null)` (game
stopped) cancels it.

### 6.9 To check in the browser

The setup fieldset (desktop and phone), the dashed helper box and the
full-width Platform-only card (desktop, tablet bottom sheet, phone), both
board previews, and the debrief notes for a Platform-only shift.


## Part 7: The big city (hidden, 2026-10-02)

### 7.1 Why

The 32-block (11.8 km) city caps trips at the city size, so about a tenth
of the GAMMA draws (mean 16 blocks) are rejected and Toronto's long trips
(28% of its trips are over 12 km) are cut off, though a long trip can be
valuable to a driver. Scaling the fleet *down* to declutter the map was
considered and rejected: pickup distance depends on idle-car density, not
on the trips-to-cars ratio, and mean trip 16 = city/2 already sits at the
torus limit. Instead, a hidden 48-block (17.8 km) city with a Toronto-sized
fleet, drawn as a heatmap with only the player's car on top.

### 7.2 Markets

(Superseded 2026-10-03 by Part 8: the markets now differ in demand, with
6000 cars in each. The table below is the original fleet-based version.)

`ridehail/game.py`: `CITIES = ("standard", "big")`, `BIG_CITY_SHARED`
(city 48, demand 240/min, mean trip 16, inhomogeneity 0.5),
`BIG_CITY_FLEETS`, and `market_settings(market, city)`. Fleets were
searched (`seed`s 2-4, 60-block warm-up + 180-block shift, 10-minute
cancellation) for the 32-block markets' time split:

| Market | Cars | P1 | P2 | P3 | Riders giving up |
|---|---|---|---|---|---|
| Busy | 4400 | 0.00 | 0.33 | 0.67 | ~15% |
| Normal | 6000 | 0.20 | 0.21 | 0.59 | 0 |
| Slow | 8500 | 0.47 | 0.11 | 0.42 | 0 |

Pickups are a little shorter than in the 32-block city (P2/P3 0.36 against
0.48 in Normal). Over 12 km the GAMMA tail gives about 9% of trips, still
well short of Toronto's 28%. The offer model is fitted to trips up to 15
km, so offers for the longest trips (to 17.8 km) extrapolate it; the
debrief's footnote says so (`results.params.city_km`).

`shift_seed(code, market, city)` keeps the standard city's seeds and adds
`|big` for the big one. `create_game(..., city=)`, and `worker.py` passes
the game settings' `city`.

### 7.3 Logged-off drivers leave the dispatch pool

`Dispatch.offline` (a frozenset of vehicle indexes, DEFAULT dispatch only)
is left out of the pool after the shuffle. `GameController.warm_up()` puts
the player and bots there, and clears it when the shift starts. Before,
they stayed in the pool and declined everything: once the fleet's idle cars
were used up within a block, every remaining trip searched the whole city
for each of them in turn. Big-city Busy warm-up took 24 s in CPython (it is
now 2 s). This changes the random draws, so standard-city shift codes give
different shifts from before 2026-10-02.

Timing (CPython, after the fix): big-city warm-up about 2 s; a shift block
(simulation, map payload, ledgers) 55-75 ms, against 2 ms for the standard
city. Pyodide is likely 2-3x slower.

### 7.4 Web lab

- Setup screen: "+" (not while typing in the code) toggles the big city,
  shown by `#game-big-city`; `city=big` in a link selects it and shift links
  carry it. The shift label and debrief labels start "Big city".
- No leaderboard for big-city shifts (the server's boards are the standard
  city's); personal bests are kept under `<market>.big`.
- Above `INTERPOLATE_MAX_CITY_SIZE` there is one frame per minute, so the
  big city's frame delay is doubled to keep the same game clock.
- `map.js`: in heatmap mode (auto above 576 cars), a frame's
  `game.player` is drawn as a car over the heatmap (at least
  `HIGHLIGHT_MIN_RADIUS` = 8px; it also stays in the heatmap). It glides
  between frames even where the fleet snaps. Dataset 0's `vehicleIndexes`
  maps its points back to vehicle indexes, which `game-map-overlay.js` uses
  to find the player's car.
- The player's glide recreates the mid-block frame's timing in JS
  (2026-10-04, `_glideHighlights` and friends in `map.js`), with no extra
  worker frames: the heading comes from the actual displacement (the
  frame's `direction` is the one chosen *at* the new intersection, so the
  car used to turn a block early and drive sideways); colour/size change on
  arrival, by a timer at the end of the glide (as the even frame does); and
  a torus wrap glides half a block off one edge and in from the other
  instead of snapping. Still on frame arrival (a block early, compared with
  the standard city): the game overlay's guide line/target switch at pickup,
  and the offer card, which appears as the car sets off for the
  intersection where it is offered.

### 7.5 To check in the browser

Frame rate and warm-up time in Pyodide (6000-8500 cars, ~5000 trips per
frame); whether the pink waiting-rider dots (about 1300 in Normal) clutter
the heatmap (a possible follow-up: only unassigned riders); the player's car
and ring over the heatmap, including a torus wrap; the offer route.

## Part 8: Markets differ in demand, not fleet (2026-10-03)

### 8.1 Why

Until now Busy / Normal / Slow differed in fleet size at a fixed demand, so
a Slow Tuesday had more cars on the road than a Busy Friday (300 against
180; 8500 against 4400 in the big city). That is backwards: it is demand,
varying through the day and the week, that shapes how many drivers are out,
not the other way round. The markets now keep Normal's fleet and change the
number of trip requests. Driver supply does respond to demand in reality
(more drivers log on when it is busy), so the most realistic version would
vary both, with the fleet moving less than demand. A fixed fleet is the
simple, clean pivot: Normal is unchanged, and the map shows the market
through riders and occupied cars, not through the number of cars.

### 8.2 Calibration

The plain simulation (no game controller), searched with
`utils/game_market_search.py` (it reuses `game_pickup_diagnostic.run`):
60-block warm-up, 180 measured blocks, 10-minute cancellation, `seed`s
2-7 (standard) and 2-4 (big). Targets were the old markets' time split.

Standard city, 215 cars:

| Market | Old (cars, demand) | Old P1/P2/P3, gave up | New demand | New P1/P2/P3, gave up |
|---|---|---|---|---|
| Busy | 180, 9 | 0.00/0.46/0.54, 16% | 11 | 0.00/0.45/0.55, 16% |
| Normal | 215, 9 | 0.20/0.26/0.54, 0 | 9 | unchanged |
| Slow | 300, 9 | 0.47/0.14/0.39, 0 | 6.5 | 0.46/0.14/0.40, 0 |

Big city, 6000 cars:

| Market | Old (cars, demand) | Old P1/P2/P3, gave up | New demand | New P1/P2/P3, gave up |
|---|---|---|---|---|
| Busy | 4400, 240 | 0.00/0.33/0.67, 16% | 330 | 0.00/0.31/0.69, 15% |
| Normal | 6000, 240 | 0.19/0.22/0.59, 0 | 240 | unchanged |
| Slow | 8500, 240 | 0.47/0.11/0.42, 0 | 170 | 0.46/0.12/0.42, 0 |

The new demands are close to scaling by the old fleet ratio (9 x 215/180
= 10.75; 9 x 215/300 = 6.45), and pickups barely change (Slow: 3.7 against
3.8 blocks). In an undersupplied market the time split saturates (standard
city: 0.45/0.55 from demand 10.5 up), so extra demand only adds riders who
give up; Busy's demand was set by the give-up share.

### 8.3 The strategy lesson (`game_calibrate.py`, 40 seeds)

| Market | Ranking before (fleet) | Ranking after (demand) |
|---|---|---|
| Busy | $33/hr 26.1 > $1/km 15.9 > rate card 12.6 > every offer 9.9 | $33/hr 25.7 > $1/km 15.8 > rate card 13.2 > every offer 10.6 |
| Normal | identical (same seeds, same config) | |
| Slow | $1/km 4.8 > $33/hr 4.6 > rate card 3.1 > every offer 3.0 | every offer 4.5 > $1/km 3.3 > $33/hr 2.2 > rate card 1.9 |

The flip is sharper: when Slow, "Takes every offer" now comes first (± ~$1
per row, so the Slow ordering below the top is noisy). Fleet means: Busy
$9.62 (was $9.32), Slow $2.88 (was $2.74). Not yet re-run:
`game_strategy.py` (best threshold per market) and the big city's bots.

### 8.4 Code and knock-ons

- `ridehail/game.py`: `MARKET_SHARED` holds `vehicle_count` 215; `MARKETS`
  holds each market's `base_demand` (11 / 9 / 6.5); `BIG_CITY_SHARED` holds
  6000 cars and `BIG_CITY_DEMAND` = 330 / 240 / 170 (replacing
  `BIG_CITY_FLEETS`).
- `utils/game_calibrate.py`: `--vehicles` became `--demand MARKET=D,...`;
  the fleet can be overridden with `--shared vehicle_count=N`.
  `utils/game_strategy.py` labels markets by demand.
- Shift codes: Normal's shifts are byte-identical; Busy and Slow shifts
  are new.
- `docs/lab/api/leaderboard.php`: `MIN_SCORING_VERSION_BY_MARKET` sets
  Busy and Slow to `2026.10.3.0` (the next `./build.sh` today), so their old
  scores drop out of the standings; Normal's boards are kept. If the build
  gets a different version, change it there.
- Setup screen (`components/game-tab.html`): Busy and Slow descriptions now
  talk about riders, not drivers.


## Part 9: A destination-driven bot (2026-10-03)

### 9.1 Why

Requests come mostly from the City Centre (inhomogeneity 0.5: about 62% of
requests from a quarter of the area), but destinations ignore it (5.7), so
idle cars collect in the outskirts: 3% of idle cars are downtown in the
standard city and 0% in the big one, in every market. A driver who ends
trips downtown gets the next offer quickly even when the city as a whole is
slow. In the big city this makes Normal play like Busy, and the strategy flip
disappears (a picky price threshold wins even when Slow). Rather than fix
this now, a fifth bot makes it visible: **"Takes trips to the City Centre"**
(`Bot("centre")`) accepts any offer whose `dropoff_zone` is `"core"`,
whatever the price. It complements the four price rules with a destination
rule.

The alternative fix the user wants to explore later: idle drivers head back
towards the busy area instead of cruising at random (the core sim's
`idle_vehicles_moving`), rather than drawing destinations towards the core
(5.7).

### 9.2 Results

(Superseded by 10.6: these numbers came from bots that could browse
several offers a block. Playing by the player's rules, the City Centre bot
no longer wins Slow.)

Standard city (`game_calibrate.py`, 40 seeds), net $/hr:

| Market | City Centre bot | Best price rule | Takes every offer |
|---|---|---|---|
| Busy | $9.79 (accepts 35%) | $33/hr: $25.29 | $8.81 |
| Normal | $11.51 (39%) | $33/hr: $12.36 | $8.58 |
| Slow | **$5.28** (39%), first | $1/km: $4.19 | $2.52 |

When Busy, location doesn't matter (there are no idle cars anywhere), so
declining on destination gains nothing, and the price rules win. When Slow,
it is the best rule: about 2 idle minutes per offer against 22 for the
accept-all bot. Big city (6 seeds, so rough): Slow $10.3 (2.0 idle minutes
per offer against the accept-all bot's 10.2, which made $6.4), Normal
$10.9, Busy $15.7; there the $33/hr rule is level or ahead in every market
(Slow $11.0, Normal $23.5, Busy $26.7).

### 9.3 Code and knock-ons

- `ridehail/game.py`: `Bot.accepts` handles `"centre"`; `BOTS` has five
  entries, so `GameController` seats six drivers. The extra seat (a fleet
  car that used to accept everything) and the extra random draw change
  every shift in every market.
- `docs/lab/api/leaderboard.php`: `MIN_SCORING_VERSION` raised to
  `2026.10.3.1` (the next `./build.sh` today, after `2026.10.3.0`), so all
  boards restart; `MIN_SCORING_VERSION_BY_MARKET` is now empty and only
  raises a market above the global minimum. If the build gets a different
  version, change it there.
- Setup screen "About the game": "five automated drivers". The debrief
  table lists `results.bots` generically, so it needed no change.
- `test/test_game.py`: the bot's rule, and `len(BOTS)` bots in the results.

## Part 10: Four bots, one price scale (2026-10-03)

### 10.1 Why

A car covers one block (0.37 km) a minute, pickup or trip, so an offer's
$/km and $/hr are in a fixed ratio: the "$1.00/km" bot was the "$33/hr"
rule with a lower bar ($0.37/min = $22/hr), and the two only looked
different. The rate-card bot (offer at or above the rate card, ignoring
the pickup) never led and added little. The bots are now:

| Key | Name | Rule |
|---|---|---|
| `yes` | Takes every offer | accepts everything |
| `hourly_low` | Takes $22/hr or more | `per_min` x 60 >= `BOT_HOURLY_LOW` |
| `hourly_high` | Takes $33/hr or more | `per_min` x 60 >= `BOT_HOURLY_HIGH` |
| `centre` | Takes trips to the City Centre | `dropoff_zone == "core"` (Part 9) |

### 10.2 Choosing the thresholds (`game_strategy.py`, sweep only, 40 codes)

The player seat accepting offers at or above a $/min threshold (pickup
included), net $/hr:

| $/min ($/hr) | Busy | Normal | Slow |
|---|---|---|---|
| 0.20 (12) | 9.2 | 8.7 | 2.3 |
| 0.35 (21) | 14.6 | 9.9 | 2.4 |
| 0.45 (27) | 17.1 | **12.3** | **3.4** |
| 0.50 (30) | **17.4** | 11.7 | 2.7 |
| 0.55 (33) | 17.3 | 10.1 | 1.1 |
| 0.70 (42) | 12.0 | 5.2 | −1.9 |

The best threshold is about $27–30/hr in every market. What changes is the
cost of missing it: when Busy, a fussy threshold costs little and taking
everything costs a lot; when Slow, fussiness costs more than it gains.
$22/hr and $33/hr sit either side of the best one, so the strong threshold
wins when Busy and loses when Slow. (Slow's ±$1 makes its lower rows noisy.)

### 10.3 Bot rows (`game_calibrate.py`, 40 seeds), net $/hr

| Market | $33/hr | $22/hr | City Centre | Every offer |
|---|---|---|---|---|
| Busy | **25.4** | 15.3 | 10.1 | 9.6 |
| Normal | 12.1 | 11.7 | **12.8** | 9.7 |
| Slow | 2.9 | 3.2 | **5.1** | 2.7 |

The bot seats overstate the size of the Busy effect: the $33/hr bot makes
$25/hr against $17 for the player seat at the same threshold in the sweep.
The direction agrees; the cause is not yet investigated (seat noise was the
earlier explanation, but this gap is large and consistent).

### 10.4 Code and knock-ons

- `ridehail/game.py`: `BOT_HOURLY_LOW` / `BOT_HOURLY_HIGH` replace
  `BOT_MIN_PER_KM` / `BOT_MIN_PER_MIN`; `BOTS` has four entries.
- Debrief (`game-debrief.js`): the rate-card info button hung on the
  rate-card bot's row; it is gone, and the offer log's "vs rate card"
  footnote points to "About the prices", which already defines the rate
  card. The "vs rate card" column and insights stay.
- `leaderboard.php`: `MIN_SCORING_VERSION` = `2026.10.3.2`, then `2026.10.3.3` for 10.6 (2026.10.3.1
  was built with five bots). Existing leaderboard entries don't matter.
- `utils/game_strategy.py`: the stale `--difficulty` option (difficulty
  levels were removed) is gone; it crashed `create_game`.
- Setup screen: "four automated drivers".

### 10.5 The bot / player gap, explained (2026-10-03)

Bots decide inside the dispatcher; the player's offer is deferred to
between blocks. Two consequences:

1. **Offers per minute.** A declining bot stays in the dispatch pool, so
   later in the same block it can be offered the next unassigned trip, and
   the next. A deferring player leaves the pool for the rest of the block:
   one offer a minute at most, and each decline costs a minute.
2. **Accept lag.** A bot's pickup starts in the block it accepts; the
   player's starts a block later.

Experiment (40 Busy shifts; a player seat playing the $33/hr rule beside
the $33/hr bot): bot $24.9, player $17.3; the bot saw 102 offers, the
player 51. With bots made to leave the pool after a decline, as the player
does (returning `DEFER`), the bot makes $17.6 and the player $18.1: the gap
is all (1), and the accept lag (2) doesn't matter. Normal and Slow show no
gap (there's no backlog to browse). The Busy bot is idle 0.5 minutes a shift:
each drop-off lands it among the backlog, and within that one minute it is
offered up to ~50 trips and takes the first at $33/hr or more.

Big city (4 seeds, too noisy to conclude): Normal's $33/hr bot falls from
$28 to $20 when limited the same way, so part of "big-city Normal plays
like Busy" (Part 9) was this artefact, though not all of it.

Options: (A) bots play by the player's rules: one offer a block, a decline
leaves the trip unassigned until the next block (a small change in
`_offer_filter`); (B) the player gets several offers a minute (the next
offer arrives straight after a decline), closer to a real app with a
backlog, but a change to the dispatch loop and the UI flow.

### 10.6 Option A implemented (2026-10-03)

`GameController._offer_filter`: a declining bot returns `DEFER` (after
recording the decline), so it leaves the pool for the rest of the block and
the trip waits for the next block, exactly as when the player declines. The
remaining difference is the player's one-block accept lag, which 10.5 showed
doesn't matter.

Parity check (40 shifts, a player seat playing the $33/hr rule beside the
$33/hr bot): Busy bot $18.2 / player $17.8 (offers 49.5 / 47.5); Normal
$11.9 / $10.8; Slow $3.2 / $4.5 (± about $1 in Normal and Slow).

Bot rows (`game_calibrate.py`, 40 seeds), net $/hr:

| Market | $33/hr | $22/hr | City Centre | Every offer |
|---|---|---|---|---|
| Busy | **18.8** | 15.2 | 9.8 | 10.4 |
| Normal | 11.3 | **11.3** | 10.0 | 9.6 |
| Slow | 4.5 | **5.4** | 2.2 | 4.0 |

The price lesson stands: the strong threshold's lead shrinks from Busy to
Normal and reverses in Slow (Slow's ±$0.8–1.3 makes its order uncertain).
The City Centre bot's earlier lead (Part 9) came mostly from browsing: idle
in the core, it was nearest to several requests a block and could wait for
one heading downtown. With one offer a block it declines about two thirds of
its offers and pays for each in idle minutes, so in Slow it does worse than
taking everything. The core drain (5.7) is still there, but a rule of "only
downtown destinations" doesn't exploit it at one offer a minute. Big-city
bot rows have not been re-run.


## Part 11: Idle drivers head back to the City Centre (2026-10-03)

### 11.1 Why

Part 9 and 5.7: requests start mostly in the City Centre but destinations
ignore it, and idle cars cruised at random, so they collected in the
outskirts (3% of idle cars downtown). The core model gained
`idle_vehicles_returning` (claude/idle-vehicles-returning.md): at each
intersection an idle car outside the core heads towards it with probability
p. The game uses **p = 0.25** (`IDLE_VEHICLES_RETURNING` in `game.py`, set
in `make_game_config`), where the share of idle cars downtown is about the
share of requests that start there, and waits are near their lowest.

### 11.2 Markets (`game_market_search.py`), demand unchanged

The demands were **not** re-searched: Busy is unchanged (no idle cars), and
in Normal and Slow returning cars turn pickup time into idle time, which
moves Normal towards the City 2026 split (0.30 / 0.15 / 0.55), the reason
for the change.

| City | Market | Before P1/P2/P3, gave up | After |
|---|---|---|---|
| 32 | Busy (11) | 0.00/0.45/0.55, 16% | 0.00/0.45/0.55, 15% |
| 32 | Normal (9) | 0.20/0.26/0.54 | 0.26/0.19/0.55 (pickup 3.6 blocks) |
| 32 | Slow (6.5) | 0.46/0.14/0.40 | 0.50/0.09/0.40 (pickup 2.1) |
| 48 | Busy (330) | 0.00/0.31/0.69, 15% | 0.00/0.32/0.68, 15% |
| 48 | Normal (240) | 0.19/0.22/0.59 | 0.27/0.14/0.59 |
| 48 | Slow (170) | 0.46/0.12/0.42 | 0.51/0.06/0.42 |

### 11.3 Bot rows (`game_calibrate.py`, 40 seeds), net $/hr

Same code and seeds, p = 0 (before) against p = 0.25 (after):

| Market | $33/hr | $22/hr | City Centre | Every offer | Fleet mean |
|---|---|---|---|---|---|
| Busy | 18.5 → **19.2** | 15.0 → 16.1 | 10.2 → 10.8 | 10.3 → 9.8 | 9.78 → 9.79 |
| Normal | 11.0 → **11.7** | **12.4** → 10.7 | 10.8 → 10.0 | 9.2 → 10.0 | 9.12 → 8.97 |
| Slow | 4.5 → 1.7 | **5.4** → 2.8 | 2.2 → −2.4 | 4.0 → **3.0** | 2.93 → 2.84 |

(± about $0.5 in Busy, $0.7 in Normal, $0.8–1.3 in Slow.)

- **Fleet earnings barely move.** Demand and fleet are fixed, so each car
  gets about as many trips; returning cars still drive (and pay running
  costs) while idle; shorter pickups turn into idle time, not extra trips.
  Accept-all idle minutes per offer: Normal 4.8 → 6.5, Slow 15.7 → 19.0.
- **The price lesson gets cleaner.** Before, the $22/hr bot led in Normal
  and Slow too. Now the strong threshold leads in Busy and (narrowly) in
  Normal, and in Slow taking every offer comes first and $33/hr is second
  to last. Declining is costlier when Slow because a car waiting downtown
  now competes with the other returning idle cars for the next request.
- **The City Centre bot loses money in Slow:** a downtown drop-off no longer
  means a quick next offer, and its declines (two thirds of offers) still
  cost idle minutes.

### 11.4 Threshold sweep (`game_strategy.py --skip-refine`, 40 codes)

Player seat accepting offers at or above a $/min threshold (pickup
included), net $/hr:

| $/min ($/hr) | Busy | Normal | Slow |
|---|---|---|---|
| 0.20 (12) | 11.0 | 9.6 | 2.2 |
| 0.35 (21) | 14.4 | 11.4 | 2.5 |
| 0.45 (27) | 17.8 | **12.9** | **2.6** |
| 0.50 (30) | 18.1 | 11.9 | 1.6 |
| 0.55 (33) | **19.1** | 11.5 | 0.5 |
| 0.70 (42) | 14.7 | 9.8 | −1.7 |

Compared with 10.2, the best threshold rises in Busy ($27–30 → $33/hr)
and stays at $27/hr in Normal and Slow, and in Slow every threshold up to
$27/hr is level with taking everything (±0.6), while fussier ones lose
fast. The $22/hr and $33/hr bots still sit either side of the best
threshold except in Busy, where $33/hr is now the best.

### 11.5 Code and knock-ons

- `ridehail/game.py`: `IDLE_VEHICLES_RETURNING = 0.25`, set in
  `make_game_config` (so `game_market_search.py`, `game_calibrate.py` and
  `game_strategy.py` all use it). `_core_range` now calls
  `City.core_bounds()`.
- Every shift changes in every market (extra random draws), so
  `leaderboard.php` `MIN_SCORING_VERSION` = `2026.10.3.10`, the next
  `./build.sh` today after 2026.10.3.9. If the build gets a different
  version, change it there.
- Setup screen running-costs popover: idle cars cruise "often back
  towards the City Centre".
- Big-city bots: 11.6. Not re-run: the big city's threshold sweep (about
  12 s a shift, so a full sweep is about 2 hours on 4 cores).

### 11.6 Big city bot rows (40 seeds), net $/hr

Same code and seeds (`calibrate-N`, accept-all player), p = 0 → p = 0.25:

| Market | $33/hr | $22/hr | City Centre | Every offer | Fleet mean |
|---|---|---|---|---|---|
| Busy | **23.5** → **24.9** | 18.3 → 19.3 | 16.8 → 17.3 | 13.3 → 14.2 | 13.29 → 13.29 |
| Normal | **18.4** → 14.2 | 11.2 → 11.9 | 15.1 → **15.8** | 9.7 → 9.3 | 9.30 → 9.11 |
| Slow | 3.9 → −0.8 | 3.6 → **4.1** | **9.9** → −0.9 | 4.1 → 3.7 | 2.60 → 2.66 |

(± about $0.5 in Busy, $0.6–1.2 in Normal, $0.7–1.7 in Slow.) Time split
P1 / P2 / P3: Normal 0.21 / 0.23 / 0.59 → 0.29 / 0.15 / 0.59; Slow 0.47 /
0.12 / 0.39 → 0.54 / 0.06 / 0.41. Accept-all idle minutes per offer:
Normal 6.1 → 7.1, Slow 20.4 → 20.4.

- **The big city's City Centre exploit is gone in Slow** ($9.9 → −$0.9),
  and with it the "big city plays like Busy" problem of Part 9: the strong
  threshold now loses in Slow ($33/hr −$0.8), as in the standard city.
- **Normal is still the odd one:** the City Centre bot ($15.8) is level with
  or ahead of $33/hr ($14.2), so in the big city a destination rule still
  pays when the market is middling. In the standard city it does not
  (11.3).
- Fleet earnings don't move, as in the standard city.


### 11.7 Open questions (hypotheses, not yet tested)

- **City Centre bot's collapse in Slow:** its edge was location (an empty
  core before returning); with the edge gone, only the cost of declining
  about two thirds of offers (~20 idle minutes each) remains.
- **City Centre bot still pays in Busy / big-city Normal:** a downtown
  drop-off shortens the next (unpaid) pickup; the big city's outskirts are
  farther from the core, so returning at 0.25 doesn't remove the benefit.
- **Every offer, Slow, lower:** mostly noise (fleet means unchanged); any
  real effect is small (shorter pickups earn slightly less, and the time
  saved is unpaid cruising).
- **$33/hr far behind $22/hr in Slow:** before, the $/hr rule was mostly
  screening out long pickups; with short, uniform pickups declining buys
  less but still costs ~20 idle minutes.
- **Check, if wanted (~15 min, big city):** per bot, at p = 0 and 0.25:
  acceptance, idle minutes per accepted trip, mean pickup of accepted and
  of declined offers.

## Part 12: Fleet chart in the sidebar (2026-10-03)

### 12.1 What

The play screen's sidebar (desktop and laptop; hidden on phones) shows
**"All drivers this shift"**, below the status box: the whole fleet's P1 / P2
/ P3 fractions and riders' wait fraction (`TRIP_MEAN_WAIT_FRACTION_TOTAL`,
dashed), one point per shift minute. The x-axis is the whole shift, so the
lines fill left to right as the clock bar does; the current values are
labelled at the line ends ("P1 26%", …, "Wait 10%"). Why: P1 is the number
that tells the markets apart (≈0 Busy, ≈0.25 Normal, ≈0.5 Slow), which is
what the strategy lesson turns on.

The legend keeps the chart's compact labels and links them to the map:
"P1 – Idle", "P2 – Picking up", "P3 – With a rider" down the left column,
the map-only markers (your car, waiting rider, City Centre) on the right.

### 12.2 Code

- `modules/metrics-sparkline.js` (new): `drawMetricsSparkline`, the line
  drawing that used to live in `map.js`'s `_drawSparkline`. The lab's map
  overlay calls it with its old settings (unchanged look); it gained a fixed
  time axis (`xMax`, points carry `x`), `scale` (device pixels) and `inset`.
- `game-tab.js`: `_recordFleet` (from `onFrame`; one point per
  `shift_block`, taken from its first frame, the real block: the
  interpolated frame after it carries the next block's measures) and
  `_drawFleetChart` (drawn at the canvas's CSS size × devicePixelRatio,
  colours from `--game-p1/p2/p3/wait`, label size capped so four labels fit
  the height; redrawn on window resize).
- `components/game-tab.html`: the `<figure class="game-fleet-chart">` and the
  legend. `style.css`: canvas 100 px tall, 64 px when the window is under
  760 px high (keeps Pause / End shift on screen); hidden under `is-phone`.
- The measures are smoothed over the default `smoothing_window` (20
  blocks), so the lines are steady, and the shift's first point already
  reflects the warm-up.

### 12.3 Later

- **The player's own split beside the fleet's**, e.g. "You: idle 41% · All
  drivers: 26%", from the player's ledger (`ledger.minutes`), to tie the
  player's choices to the market. Not built; wait to see whether the fleet
  chart earns its place first.

## Part 13: Idle cars that sometimes stand still (2026-10-03)

### 13.1 Question

The game sets `idle_vehicles_moving = 1.0`: every idle minute is a moving
minute, so it costs one block of running costs (0.37 km × $0.56 ≈ $0.21,
about $12.40/hr). Running costs accrue only when a car's location changes
(`game.py` ledger update), so at `idle_vehicles_moving = p` an idle minute
costs p of that. Declining an offer buys idle time, so a lower p should make
declining cheaper. Does it, and what happens to the contrast between markets
(1.6: picky drivers do well when Busy, taking everything when Slow)?

### 13.2 Method

Not a code change: a wrapper (scratchpad, not in the repo) patched
`game.make_game_config` to override `idle_vehicles_moving` and ran the Part
11 measurements unchanged (standard city, `idle_vehicles_returning` 0.25):
`game_calibrate.py --seeds 40` and `game_strategy.py --seeds 40
--skip-refine --lam-min 0.1 --lam-max 0.8 --lam-step 0.05`. The p = 1.0
runs reproduce 11.3 and 11.4 exactly.

### 13.3 Bot rows (`game_calibrate.py`, 40 seeds), net $/hr

| Market | p | $33/hr | $22/hr | City Centre | Every offer | Fleet mean |
|---|---|---|---|---|---|---|
| Busy | 1.0 | **19.2** | 16.1 | 10.8 | 9.8 | 9.79 |
| Busy | 0.75 | **18.7** | 15.9 | 11.3 | 10.9 | 9.77 |
| Busy | 0.5 | **20.0** | 16.1 | 10.7 | 11.6 | 9.81 |
| Normal | 1.0 | **11.7** | 10.7 | 10.0 | 10.0 | 8.97 |
| Normal | 0.75 | **13.3** | 11.8 | 12.0 | 9.6 | 9.78 |
| Normal | 0.5 | **15.1** | 12.9 | 12.5 | 10.2 | 10.40 |
| Slow | 1.0 | 1.7 | 2.8 | −2.4 | **3.0** | 2.84 |
| Slow | 0.75 | 4.8 | **5.0** | 1.5 | 4.1 | 4.47 |
| Slow | 0.5 | 6.0 | **7.6** | 6.4 | 6.7 | 5.98 |

(± about $0.5 in Busy, $0.6–0.7 in Normal, $0.6–0.8 in Slow.) Fleet phases
P1 / P2 / P3 at p = 1.0 → 0.5: Normal 0.26 / 0.20 / 0.53 → 0.22 / 0.25 /
0.53; Slow 0.52 / 0.10 / 0.38 → 0.51 / 0.11 / 0.38.

### 13.4 Threshold sweep (`game_strategy.py`), player net $/hr

| $/min ($/hr) | Busy 1.0 | Busy 0.5 | Normal 1.0 | Normal 0.5 | Slow 1.0 | Slow 0.75 | Slow 0.5 |
|---|---|---|---|---|---|---|---|
| ≤0.20 (take all) | 10.4 | 9.5 | 9.6 | 10.2 | 2.2 | 5.7 | 6.8 |
| 0.35 (21) | 14.4 | 15.0 | 11.4 | 11.9 | 2.5 | **6.3** | 7.8 |
| 0.45 (27) | 17.8 | 18.7 | **12.9** | 14.1 | **2.6** | 5.9 | 8.1 |
| 0.50 (30) | 18.1 | 19.6 | 11.9 | **15.2** | 1.6 | 4.9 | 7.7 |
| 0.55 (33) | **19.1** | **19.8** | 11.5 | 13.7 | 0.5 | 4.7 | **8.1** |
| 0.70 (42) | 14.7 | 16.8 | 9.8 | 12.9 | −1.7 | 1.9 | 4.6 |

(± about $0.4–0.7, rising to ~$0.9 for the fussiest thresholds. Busy 0.75
and Normal 0.75 sit between 1.0 and 0.5.)

### 13.5 Findings

- **Yes: a lower p pays drivers more to decline**, where there is idle time.
  In Slow the best threshold's lead over taking everything goes from
  $0.4/hr (p 1.0) to $1.3/hr (p 0.5), and the penalty for a fussy
  $42/hr threshold falls from −$3.9 to −$2.2. In Normal the best threshold
  rises from $27 to $30/hr and its lead over accept-all goes from $3.3 to
  $5.0/hr.
- **Busy doesn't change**: no idle time, so nothing to save (differences are
  noise).
- **Everyone earns more**, not just choosy drivers: fleet mean in Slow
  $2.84 → $5.98/hr, Normal $8.97 → $10.40/hr. That is about the expected
  saving (Slow: 52% idle × half of $12.40/hr ≈ $3.2/hr).
- **The Busy / Slow contrast fades at p = 0.5 (Slow demand 6.5).** In Slow,
  Yes-to-Everything is no longer first: the $22/hr bot leads and all four
  bots are within about $1.6/hr (roughly two standard errors), so taking
  everything no longer stands out when Slow. At p = 0.75 Slow is a muddle
  (Every offer 3rd of 4, behind both threshold bots but within noise).
- **The City Centre bot recovers in Slow** (−$2.4 → +$6.4): its declines
  cost idle minutes, which now cost half as much.
- **Cars return to the core more slowly**: a car standing still doesn't use
  its turn towards the core, so in Normal P2 (pickup) rises 0.20 → 0.25.

### 13.6 Options (option 2 chosen, 13.7)

1. Keep p = 1.0: keeps the 1.6 contrast; idle is expensive, which
   overstates the cost of waiting compared with drivers who park.
2. Lower p and recalibrate the markets: e.g. a slower Slow (lower demand) so
   that idle waits are long enough to restore the contrast. Every shift and
   leaderboard entry changes (`MIN_SCORING_VERSION`).
3. Make parking the player's choice ("wait here" vs "cruise") instead of a
   fleet-wide constant: turns the cost of idling into a decision the game
   can teach. Bigger design change; bots would need a rule too.

### 13.7 Adopted: p = 0.5, Slow demand lowered (2026-10-03)

Reasons for option 2: a car that sometimes waits where it is reflects real
driving at least qualitatively; a market where taking every trip does well
is a useful contrast with Busy, where picky drivers do; and the game stays
simple to play (no park / cruise choice, which might suggest the game is
closer to reality than it is).

**Standard city, Slow demand.** Threshold sweeps (`game_strategy.py`, 100
codes per threshold, paired) at p = 0.5, player net $/hr:

| Slow demand | Take all | Best threshold | $33/hr | $42/hr | Offers / shift |
|---|---|---|---|---|---|
| 6.5 (13.4) | 6.8 | 8.1 ($27–33/hr) | 8.1 | 4.6 | 5.8 |
| 5.5 | 4.8 | 5.0 ($21/hr) | 4.1 | 2.6 | 5.3 |
| **5.0** | 3.6 | 3.9 ($21/hr) | 2.8 | 1.4 | 4.2 |
| 4.5 | 2.5 | take all | 1.6 | 0.2 | 3.8 |
| *6.5 at p = 1.0 (11.4)* | 2.2 | 2.6 ($27/hr) | 0.5 | −1.7 | 5.8 |

(± about $0.4 per row; differences between thresholds are paired, so
tighter.) **Slow is now 5.0**: it has the same shape as the old Slow (taking
everything within about $0.30/hr of the best threshold, which turns down
only the worst tenth of offers; fussier thresholds lose), and keeps more
offers per shift than 4.5. Bot rows at 5.0 (`game_calibrate.py`, 100 seeds):
Every offer 3.7, $22/hr 4.2, $33/hr 2.9, City Centre 1.0, fleet 3.18 (±
about $0.4; the $22/hr bot accepts 91% of offers, so it is close to
accept-all). Time split 0.63 / 0.07 / 0.29.

Busy (11) and Normal (9) are unchanged: Busy has no idle time, and Normal is
the anchor market (fleet and demand). At p = 0.5 Normal's best threshold is
$30/hr (13.4) and its split is 0.22 / 0.25 / 0.53.

**Big city.** A paired threshold sweep takes hours there, and 40-seed bot
rows are too noisy to rank (the Player seat and the Every-offer bot play the
same rule and differ by up to $1.90/hr). So, as in Part 8, Slow was set by
the time split. Bot rows (40 seeds, p = 0.5):

| Slow demand | P1 / P2 / P3 | Fleet mean | Offers / shift |
|---|---|---|---|
| 170 | 0.52 / 0.08 / 0.41 | 5.82 | 5.3 |
| 140 | 0.62 / 0.06 / 0.34 | 3.71 | 4.5 |
| **130** | 0.65 / 0.05 / 0.31 | 3.01 | 3.5 |
| 120 | 0.67 / 0.04 / 0.28 | 2.30 | 3.2 |

**Big-city Slow is now 130**: the same cut as the standard city (×0.77),
and its P1 stays a little above the standard city's (0.65 against 0.63; it
was 0.54 against 0.51 before). Big-city Normal (240) and Busy (330) at
p = 0.5, net $/hr: Normal City Centre 17.8, $33/hr 16.4, $22/hr 14.3, every
offer 11.9, fleet 10.58 (split 0.23 / 0.19 / 0.57); Busy $33/hr 24.4,
$22/hr 18.3, City Centre 18.0, every offer 13.0, fleet 13.29. The City
Centre bot still leads in big-city Normal, as in 11.6.

**Code and knock-ons**

- `ridehail/game.py`: `IDLE_VEHICLES_MOVING = 0.5`, set in
  `make_game_config` (so the calibration utilities use it too); `MARKETS`
  Slow `base_demand` 5.0; `BIG_CITY_DEMAND` Slow 130.
- `docs/lab/api/leaderboard.php`: `MIN_SCORING_VERSION` = `2026.10.3.12`,
  the next `./build.sh` today after 2026.10.3.11. If the build gets a
  different version, change it there.
- Running-cost wording: the setup screen's popover (`game-tab.html`: about
  $12/hr driving, about $6/hr idle) and the debrief's popover
  (`modules/game-debrief.js`).
- `utils/game_strategy.py` docstring: running costs now depend a little on
  the decision (an engaged minute costs (1 − p) of a block more than an idle
  one); this only shifts the best lam, which the sweep finds.
- Not re-run: the big city's threshold sweep, and the refine stage of
  `game_strategy.py`.

### 13.8 Open question: is Slow's fleet average too low?

After this change the whole fleet nets about $3/hr in Slow ($3.18 standard
city, $3.01 big city; $2.84 before, and about $10–13/hr in Normal and
Busy), and a Slow shift brings about 4 offers in 3 hours. We don't know
whether that is within the range of real driving or a sign that the
simulation's Slow market is too far from a normal experience. Not
investigated; it belongs with the earnings comparison in 5.9 (the
City-commissioned report's figure and definitions). Things to check then: a
real slow period's idle share (Slow is now about 63% idle) and its offers per
hour, and whether real drivers log off when it is this slow (the game's fleet
is fixed, Part 8.1), which would keep the earnings of those still driving up.

## Part 14. Play-screen layout changes (2026-10-04)

**Draggable offer card (desktop and laptop).** Where the card floats over
the map (`position: absolute`, i.e. wider than 800px), it can be dragged by
any part except its buttons so it doesn't hide the route.
`modules/game-offer.js` keeps the offset (`--drag-x` / `--drag-y` on the
card, used in its `transform` and entry animation), holds it inside the map
area (`.game-map-wrap`), keeps it for later offers in the session, and
re-clamps it when each offer is shown (window resizes). Tablets keep the
fixed bottom sheet, which doesn't drag.

**Map back on phones** (reverses "No map on phones", 2026-09-29). In the
phone tier the play screen is a one-column grid: the map on top (square, at
most half the screen height, `50dvh`) and the status pane below it.
`.game-map-wrap` is `display: contents` there, so its children join the
grid: the loading pill and timeout banner sit over the top of the map, and
the offer card shares the status pane's cell, covering it except for Pause
and End shift (the card's bottom margin clears them; they are pinned to the
foot of the pane). The legend and fleet chart stay hidden for room.
`message-handler.js` no longer skips `plotMap` for game frames on phones.
The user checked both changes and confirmed they work better (2026-10-04).

**Get ready before the clock starts (2026-10-04).** Previously the shift
ran from the first frame, with no time to find your car. Now `game-tab.js`
has two more states, `ready` and `countdown`, between `starting` and
`playing`:
- On the first frame (`_getReady`) the city is drawn and held: the worker is
  sent a Pause (a stale frame that still arrives is dropped by
  `message-handler.js`). If that frame already carries an offer the worker is
  holding for the decision and a Pause would drop the hold, so nothing is
  sent and the offer is shown once the player starts.
- The map overlay (`ready: true`) dims the city and labels the player's car
  "Your car" in a violet pill. The car pulses every 2.5 s.
- A card where the offer card will appear (bottom of the map; over the
  status pane on phones) says "Ready to drive?", with a **Start driving**
  button. "or press any key" is shown only where there's a mouse
  (`@media (hover: none) and (pointer: coarse)` hides it), so phone users
  see just the button. A click or tap anywhere on the play screen except
  its controls also starts.
- Then 3, 2, 1 (0.7 s each) and `_go` resumes the worker (Play, frameIndex
  1) and shows the held frame as if just arrived (HUD, fleet chart, any
  offer). The shift clock doesn't run while the game waits, so scores are
  unaffected. End shift works while waiting; Pause does nothing.

## Part 15. "How real is this?" on the debrief (2026-10-04)

Players wonder how far the game reflects reality. The calibration was
explained in one long "About the prices" footnote at the foot of the
debrief. It is replaced by a "How real is this?" section
(`game-debrief.js` `aboutHtml`), still at the foot of the debrief:
- A notice that the game is in development and its calibration is a work
  in progress (`.game-wip`, amber-edged), then a one-line framing note,
  then two side-by-side cards (stacked on phones):
  **From Toronto data** (offer prices, trip-length mix, rider fares,
  running costs, speed, Ontario's pay rule) and **Simplified** (square grid
  with a City Centre, no traffic, steady demand, no tips/bonuses/quests or
  airport trips, a fixed set of drivers, other drivers take every offer).
- An FAQ of closed `<details>` items in the player's voice, holding the old
  footnote's content plus two new answers: "Are these real offers?", "What
  is the rate card?", "Does the platform really keep that much?", "Where
  do the running costs come from?", "Who are the other drivers?", "How are
  the markets different?". The figures still come from `results.params`.
- The offer log's footnote and "What your riders paid" now point to FAQ
  questions rather than "About the prices".

Planned next (the plan agreed 2026-10-04): (1) a Toronto reference figure,
with an (i) source note, beside the 3-4 headline debrief numbers that have
a source whose definition matches (net vs gross, engaged vs total hours);
later, (4) each offer's percentile among real offers of a similar length in
the offer log, and (5) one sourced fact on the loading and get-ready cards.

**Big city on phones (2026-10-04).** Phones have no "+" key, so three quick
taps (within 1.2 s) on the setup screen's title also switch between the
standard and big city (`game-tab.js`, `TITLE_TAPS_MS`). The title has no
text selection or double-tap zoom so the taps register. Still hidden: the
big-city note only mentions the taps once it is showing. A
`#game?city=big` link also works.

Step 1 research (2026-10-04): the candidate Toronto reference figures, with
definitions and an assessment of each, are in
`claude/game-reality-references.md`.

## Part 16. Where to wait: the player steers the idle car (plan, 2026-10-04)

**Postponed (2026-10-04).** Step 0 (16.10, 16.11) showed steering is
worth a lot only when Slow and has a near-single answer that depends on
details the deliberately simple model doesn't claim to get right; the user
chose to keep the game simple and postpone it. What came out of it: the
fleet's `idle_vehicles_returning` now heads for a sampled request origin
(16.11). The original plan follows, for if it is picked up again.

The plan agreed 2026-10-04 to give the driver a second
decision beside accept/decline: what to do while idle. The other ideas for
a better game (16.9) are noted, not planned.

### 16.1 The choice

While idle (P1), the player picks one of three modes:

- **Cruise** (the default, today's behaviour): the fleet's own idle
  behaviour, i.e. move in half of the minutes (IDLE_VEHICLES_MOVING = 0.5),
  head back to the City Centre with p = 0.25 at each intersection
  (IDLE_VEHICLES_RETURNING), otherwise a random turn.
- **Wait here**: park. No movement, so no running costs; offers come only
  from riders near where the car stands.
- **Go to**: tap an intersection on the map. The car drives there every
  minute (paying running costs), then parks and waits there.

Offers keep coming in every mode, dispatched from the car's current
position, so a car heading downtown can be offered a trip on the way.
Accepting an offer ends the mode: after the drop-off the car is back in the
default (whether "Go to" should be remembered across trips is open
question 1, 16.8).

The tradeoff the choice has to carry: downtown has more requests but more
idle cars competing for them (IDLE_VEHICLES_RETURNING draws idle cars
there); the outskirts have few requests but little competition and, because
destinations are drawn by distance from the origin, different trip lengths;
driving somewhere costs $/km now for an uncertain gain later. Part 10's
`game_strategy.py` refine stage already estimates `delta`, the value of
becoming idle in the core rather than the outskirts, so the position of an
idle car is known to matter; how much it can be *steered* profitably is the
question for step 0.

### 16.2 Changes to the ridehail package: small

The core needs one new hook; everything else is in `ridehail/game.py`.
This would be the third core touch point for the game, after
`Dispatch.offer_filter` and `max_wait_time`.

**`ridehail/atom.py`, `Vehicle`** (about 20 lines):

- A new attribute `idle_target` (a location or None, default None, so no
  other car and no other simulation changes behaviour).
- `update_direction`, P1 branch: compute the default direction exactly as
  now (the core-return draw and the random turn), then, if `idle_target` is
  set and not reached, override it with a step towards the target.
- The step towards the target is chosen **without a random draw** (for
  example, along the axis with the larger remaining distance, ties to x),
  unlike `_navigate_towards`, which draws between two candidate directions.
  Doing the default draws and then overriding keeps the random number
  stream the same whatever the player does, so the rest of the city plays
  out as it would have, and "same shift" stays as comparable as it is today
  (accepting and declining already change dispatch; steering adds no
  further divergence of its own).

Parking needs no core change: `Vehicle.idle_vehicles_moving` is already a
per-vehicle attribute, and `update_location` draws its random number before
comparing, so setting the player's car to 0 (Wait here) or 1 (Go to)
leaves the draws unchanged. The only place the simulation overwrites it is
when the global `idle_vehicles_moving` changes mid-run (`simulation.py`
target-state loop), which the game never does.

Considered and rejected: no core change at all, with `game.py` setting the
player's `direction` in `after_block`. It works for movement, but the
frame's `vehicles` state (built inside `next_block`, before `after_block`)
would carry the old direction, so in the standard city the interpolated
frame would show the car facing the wrong way on every turn. The direction
belongs where P2/P3 navigation already lives.

Tests (a new `test/test_idle_target.py`, alongside
`test/test_idle_vehicles_returning.py`): a car with `idle_target` reaches
it in exactly the Manhattan (torus) distance in minutes when moving every
minute; `idle_target = None` leaves a seeded run bit-for-bit unchanged
(regression on an existing baseline); the random number stream is the same
with and without a target (compare `random.getstate()` after N blocks).

### 16.3 `ridehail/game.py`

- `GameController.set_idle(mode, target=None)`: mode in
  `cruise | wait | goto`. Sets the player's `idle_target` and
  `idle_vehicles_moving` (cruise: None and IDLE_VEHICLES_MOVING; wait: None
  and 0; goto: target and 1).
- `after_block`: on reaching the target, switch goto to wait. On the
  player's dispatch (an accepted offer), reset to the default mode, unless
  the "remember" option of open question 1 is adopted.
- `frame_payload`: add `idle_mode` and `idle_target`.
- Ledger and results: minutes parked, idle km (already counted in `km`,
  but split idle from engaged for the debrief), and where the player's
  offers came from (core or outskirts), for insights such as "You drove
  6 km to get downtown, and your next offer came after 9 minutes".
- `step(decider, positioner=None)`: headless play gets a positioning policy
  next to the accept/decline decider, for step 0 and for bots.

### 16.4 Web lab

- **Worker**: a `GameIdle` action (`js/constants.js` SimulationActions),
  routed by `webworker.js` to `GameSimulation.set_idle` in `worker.py`.
  Unlike `GameDecision` it neither holds nor restarts the frame loop: it is
  applied before the next block, like a live `Update`.
- **Controls**: a three-way switch, Cruise / Wait here / Go to, in the
  sidebar under the status card (and in the phone's bottom action bar).
  Tapping the map while idle sets a Go to target at the nearest
  intersection (Chart.js `onClick`, `scales.x/y.getValueForPixel`, rounded,
  modulo the city size). Keyboard: one key per mode (check
  `js/keyboard-mappings.json` for free keys). Disabled, but showing the
  mode, while on a trip.
- **Map overlay** (`game-map-overlay.js`): while idle with a target, a
  guide line and flag to it in the player's violet, like the existing
  pickup/drop-off guide; `game-tab.js` `_overlayState` gets a P1 branch.
  A parked car could show a small "P" badge on its ring.
- **Big city**: nothing extra; the player's car is drawn individually and
  glides there too (7.4).

### 16.5 Step 0 first: is the choice a real decision? (headless, no UI)

Before any UI work, measure it with `utils/game_strategy.py`-style sweeps
(40 shift codes per market, paired by code, standard and big city):

| Policy | Rule |
| --- | --- |
| Cruise | today's behaviour (the baseline) |
| Park | wait wherever the car is |
| Downtown and park | go to the nearest City Centre intersection, then wait |
| Park outside | wait unless far out in the outskirts, then head in |
| Mixed | the best accept threshold for the market, combined with each of the above |

The choice is worth building only if the best policy **differs between
markets** (Busy against Slow), or depends on where the car is, and no
single policy beats the others in every market by a wide margin. If
"downtown and park" wins everywhere, steering is a chore, not a decision,
and the honest result is to report that rather than tune the city until it
isn't (see the "no predetermined lesson" principle). Write the table up as
16.6 either way.

### 16.6 Knock-ons

- **Bots**: today's bots cruise like the fleet. If steering pays, a
  steering player beats them more easily, so one bot (or each bot) should
  get a positioning policy from step 0, and the bot rows recalibrated
  (`game_calibrate.py`).
- **Scoring**: a new `MIN_SCORING_VERSION`; the leaderboards reset (fine,
  their entries are disposable).
- **Debrief**: "Where your time went" splits idle into parked and
  driving; one insight about positioning; the offer log could note the
  mode the car was in when each offer came.
- **"How real is this?"**: the "Simplified" card's "other drivers take
  every offer" gains a line on how the fleet waits.

### 16.7 Order of work

0. Core hook + tests, `set_idle` and the headless `positioner`, then the
   step 0 sweep and its write-up (16.5). Decide whether to go on.
1. Payload, worker action, the switch and map tap, the overlay.
2. Bots and recalibration, scoring version, debrief additions.
3. Browser check by the user (standard and big city, phone and desktop).

### 16.8 Open questions (decided 2026-10-04)

Decided: (1) Go to ends with each dispatch; (2) Cruise stays; (3) no
demand hint.

1. Does Go to persist across trips ("my spot", which the car returns to
   after each drop-off), or end with each dispatch? Persisting is closer to
   how drivers work and saves taps, but it is a standing strategy, not a
   decision made each time.
2. Is Cruise needed at all, or are Wait here and Go to enough (Cruise being
   what the fleet does)?
3. Should the player see more about demand than the waiting-rider markers
   and the City Centre shading (a "busy areas" hint, as driver apps show)?
   With the rate helper only, or for both offer screens?

### 16.9 Other ideas for a better game (noted, not planned)

From the 2026-10-04 discussion, in no order:

- **Driver: when to stop.** Let the player end the shift when they choose,
  with the score counting the value of their time or fatigue. Connects to
  the NYC cab drivers' income-targeting study (Camerer et al. 1997), and
  to the game's title.
- **Driver: when to work.** A week rather than a shift: choose which hours
  to drive (Busy Friday against Slow Tuesday) and live with how crowded
  they are.
- **Driver: multi-apping.** Offers from two platforms with different pay;
  accepting one takes the car off the other. Needs two platforms in the
  core.
- **Platform game.** The player sets price and commission. A single
  platform in a steady state is a static optimisation (the Experiment tab
  with equilibration on), so the strategy has to come from: slow,
  asymmetric driver entry and exit (riders react in minutes, drivers in
  weeks) over a long game clock; cash, runway and investor goals
  (subsidise to grow, then extract); regulator events (minimum pay, caps,
  congestion charges); demand that moves (rush hours, events, surge). The
  biggest addition is a **competitor platform**: shorter waits for the
  denser fleet make it winner-take-most, hence price wars and subsidies.
  Needs dispatch per platform, rider choice between platforms, and drivers
  on both: the largest core change of any idea here. Suggested path:
  play the Experiment tab with equilibration on from the platform's seat
  to see whether a lagged single-platform version has any tension, then
  build that, and add the competitor only if it is fun.
- **City game.** Play the regulator: set the rules (minimum pay, caps,
  congestion pricing), scored on rider waits, driver pay and congestion,
  against an AI platform that optimises within them.

### 16.10 Step 0 done: results (2026-10-04)

Built: the core hook (`Vehicle.idle_target` and `Vehicle.step_towards` in
`ridehail/atom.py`, `test/test_idle_target.py`); `GameController.set_idle`,
`idle_mode`/`idle_target` in the frame payload, reset to cruise on
dispatch, goto -> wait on arrival, and a `positioner` for headless `step`
(`ridehail/game.py`, tests at the end of `test/test_game.py`); the sweep
`utils/game_positioning.py`.

One plan item was dropped: keeping the random number stream independent
of the player's steering. The fleet's idle cars take a variable number of
draws depending on where they are (in or outside the City Centre, U-turn
redraws), so any change in the player's position changes the stream,
however the override is written. Accept/decline already does the same, so
"same shift" is as comparable as before, and no more.

Sweep, standard city, 40 shift codes per cell, paired by code; net $/hr,
difference from cruise ± standard error:

| Market | Offers taken | cruise | park | core (edge) | centre | near (4) |
| --- | --- | --- | --- | --- | --- | --- |
| Busy | all | 10.36 | +0.02 ± 0.08 | +0.06 ± 0.06 | −0.01 ± 0.09 | +0.02 ± 0.08 |
| Busy | ≥ $22/hr | 15.91 | +0.06 ± 0.52 | +0.59 ± 0.54 | −0.07 ± 0.57 | +0.65 ± 0.58 |
| Normal | all | 10.38 | +1.29 ± 0.54 | +1.89 ± 0.76 | +1.48 ± 0.75 | +1.16 ± 0.74 |
| Normal | ≥ $22/hr | 11.79 | +1.82 ± 0.61 | +3.15 ± 0.57 | +2.73 ± 0.66 | +2.24 ± 0.60 |
| Slow | all | 3.09 | +3.88 ± 0.79 | +3.25 ± 0.67 | +4.69 ± 0.77 | +2.73 ± 0.73 |
| Slow | ≥ $22/hr | 3.63 | +3.50 ± 0.79 | +3.09 ± 0.77 | +5.33 ± 0.76 | +2.77 ± 0.78 |

"nearby" (go to the middle if within R blocks, else park; R = 6, 10, 14)
never clearly beat always going to the middle: in Slow it was $0.2-1.9/hr
worse at every R; in Normal within one standard error either way.

Findings:
- **Busy**: where to wait makes no difference (8 idle minutes a shift).
- **Normal and Slow**: steering pays a lot, $1.5-5/hr, more than any
  offer threshold does. Parking alone is worth $1.3-3.9/hr in running
  costs (cruising drives ~22 idle km a shift when Slow).
- **One policy is best or near-best everywhere**: drive to the middle of
  the city and wait. Where the car is when it drops off doesn't change
  that. By 16.5's test, steering is a chore, not a decision: worth a lot
  once, then obvious.

Why the middle wins (`density.py`-style count, 6 shifts per market, idle
cars and new requests by distance from the middle of the city):

| Distance from the middle | Normal: idle cars | Normal: requests | Slow: idle cars | Slow: requests |
| --- | --- | --- | --- | --- |
| 0-7 blocks | 1% | 28% | 6% | 26% |
| 8-15 | 17% | 46% | 51% | 46% |
| 16-23 | 57% | 20% | 36% | 20% |
| 24+ | 25% | 7% | 7% | 7% |

Nearest-car dispatch takes any idle car near the middle almost at once, and
the fleet's return rule (IDLE_VEHICLES_RETURNING) heads for the *nearest*
City Centre intersection, i.e. its edge, a quarter of the time. So idle
cars sit where demand isn't, and a player who waits in the middle has
almost no competition. Real drivers learn where the work is; the fleet
here doesn't, which is what makes one answer dominant.

Decision needed (not taken): go on as planned (the contrast is then
"positioning is worthless when Busy, worth a lot otherwise", with a single
answer); or first make the fleet position itself more like real drivers
(for example, idle cars return to a sampled request origin rather than the
nearest core edge: the "sampled origin" option rejected for simplicity in
claude/idle-vehicles-returning.md), re-measure, and recalibrate the
markets and bots (Parts 11 and 13), in the hope that the best place to
wait then depends on where the other cars are; or shelve it.

### 16.11 Fleet returns to a sampled request origin (2026-10-04)

Decided after 16.10: `idle_vehicles_returning` now sends an idle car
towards a sampled request origin (`City.set_location()`, kept until reached
or dispatched) instead of the nearest City Centre edge
(claude/idle-vehicles-returning.md). Done in the core. `leaderboard.php`
`MIN_SCORING_VERSION` = `2026.10.4.1`, the next `./build.sh` today after
2026.10.4.0 (if the build gets a different version, change it there), so
the boards restart. **Not recalibrated** (left for later, by choice):
market demands and bot rows (Parts 11 and 13), e.g. whether taking every
offer is still about as good as any threshold when Slow. Cruise moved from
$10.38 to $9.88/hr (Normal) and $3.09 to $4.29/hr (Slow) in the 16.10/16.11
sweeps. The steering code built for step 0 (`Vehicle.idle_target`,
`step_towards`, `GameController.set_idle`, the headless `positioner`,
`utils/game_positioning.py`, their tests) and `City.nearest_core_location`
were removed when steering was postponed; rebuild from 16.2-16.3.

Re-measured (same sweep, 40 codes; difference from cruise, $/hr):

| Fleet p | Market | Offers | park | core (edge) | centre |
| --- | --- | --- | --- | --- | --- |
| 0.25 | Busy | ≥ $22/hr | +0.53 ± 0.37 | +0.15 ± 0.56 | +0.46 ± 0.45 |
| 0.25 | Normal | all / ≥ $22 | +0.85 / −0.69 | +1.63 / +1.05 | +1.36 / +1.54 |
| 0.25 | Slow | all / ≥ $22 | +2.37 / +1.64 | +6.02 / +5.33 | +4.89 / +5.26 |
| 0.5 | Normal | all / ≥ $22 | −0.09 / +0.56 | +0.28 / +1.19 | +0.37 / +0.89 |
| 0.5 | Slow | all / ≥ $22 | +1.85 / +1.90 | +5.33 / +5.39 | +4.69 / +5.04 |
| 1.0 | Normal | all / ≥ $22 | +0.12 / +0.37 | +0.48 / +0.94 | +0.39 / +0.67 |
| 1.0 | Slow | all / ≥ $22 | +2.50 / +1.97 | +4.36 / +3.89 | +2.81 / +2.73 |

(Standard errors ±0.65-0.9 except Busy.) Busy with every offer taken: no
difference at all.

Findings:
- The idle cars' geography hardly changed (density count at p = 0.25: still
  under 3% of idle cars within 11 blocks of the middle, against half the
  requests). 16.10's explanation was wrong: the cause is dispatch itself.
  Any idle car near demand is soon dispatched, so the stock of idle cars
  always sits where demand is thin, whatever the return rule.
- A fleet that heads back harder (p = 0.5, 1) shrinks the player's gain
  from steering in Normal to within about one standard error, and makes
  the middle a worse place to wait than the City Centre's edge when Slow.
- When Slow, "drive to the nearest City Centre edge, then wait" stays
  worth $4-6/hr at every fleet p. It is the best or tied-best policy in
  every cell, so steering is still close to a single answer, now a less
  obvious one ("the edge, not the middle").
