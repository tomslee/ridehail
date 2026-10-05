# Game Mode: "Just One More Shift…" — current design

The game as it stands, in one place. Start here.
`claude/game-mode.md` is the dated **log**: why each decision was made, what
was measured and what was tried and dropped. Section references below
("log 13.7") point into it. Keep this file current when the game changes; add
the story of the change to the log.

Last brought up to date: 2026-10-05.

## 1. The game

The player drives one car for a three-hour evening shift in a simulated city
with a fixed fleet. When the dispatcher picks the player's car for a trip,
the world freezes and an **offer card** appears: an upfront price, the
pickup and the trip. The player accepts or declines within 8 seconds (a
timeout declines). At the end of the shift a debrief compares the player's
**net earnings per hour of shift** (fares minus running costs, idle time
included) with four rule-following bots and with the rest of the fleet, who
take every offer.

The lesson: **a good trip is not the same as a good hour.** Whether an offer
is worth taking depends on the pickup, the trip, and how soon the next offer
will come, and that depends on the market. The markets are contrasts that
bring out these factors, not a predetermined answer (log 13.7).

## 2. Where the code is

| Layer | Files |
|---|---|
| Game logic (Python, ships in the wheel) | `ridehail/game/`: `params.py` (units, `GameParams`, `CARDS`), `market.py` (markets, cities, `make_game_config`, `shift_seed`), `bots.py`, `offer_model.py` (generated), `pricing.py` (`OfferPricing`), `controller.py` (`GameController`, `Ledger`), `report.py` (the debrief's data); `create_game()` in `__init__.py` |
| Core hooks it uses | `ridehail/dispatch.py` (`offer_filter`, `OfferDecision`, `commit_dispatch`, `offline`), `sim.dispatcher`, config `max_wait_time`, `idle_vehicles_moving`, `idle_vehicles_returning`, `City.core_bounds()` |
| Worker bridge | `docs/lab/worker.py` (`init_game`, `GameSimulation`), `docs/lab/webworker.js` (offer hold, time warp) |
| Browser | `docs/lab/game-tab.js` (`GameTab`), `modules/game-setup.js` (markets, cards, city sizes, shift length), `modules/game-offer.js`, `modules/game-debrief.js`, `modules/game-leaderboard.js`, `modules/game-map-overlay.js`, `modules/metrics-sparkline.js`, `components/game-tab.html`, the `/* Game tab */` section of `style.css` |
| Leaderboard server | `docs/lab/api/leaderboard.php` (PHP 8.1 + SQLite on tomslee.net) |
| Calibration (headless) | `utils/game_calibrate.py` (bot rows), `utils/game_strategy.py` (threshold sweeps), `utils/game_market_search.py` (market time splits), `utils/game_pickup_diagnostic.py`, `utils/fit_offer_model.py` (writes `offer_model.py`) |
| Tests | `test/test_game.py`, `test/test_dispatch_offer_filter.py`, `test/test_web_lab_constants.py` |

## 3. A shift

1. **Setup screen.** Choose a **market** (Busy Friday, Normal, Slow
   Tuesday), an **offer screen** (Rate helper: the card also shows $/km and
   $/hr, pickup included, as a third-party app would; or Platform only), and
   a **shift code** (a seed: same code, market and city = same city, demand
   and starting seat). The last offer screen is remembered; a link
   `#game?market=…&code=…&card=…[&city=big]` presets the screen but doesn't
   start. A top-5 leaderboard preview sits next to the code. The hidden
   **big city** is toggled with "+", three quick taps on the title (phones),
   or `city=big` (log Part 7, 15).
2. **Warm-up**: 60 blocks run unseen, with the player and bots logged off
   (`Dispatch.offline`), so the market is at steady state and they start idle.
3. **Get ready**: the first frame is held, the city dimmed and the car
   labelled "Your car" and pulsing, until the player presses Start (or any
   key / a tap), then a 3-2-1 countdown. The clock doesn't run meanwhile
   (log Part 14).
4. **Driving.** Sidebar: shift time left, earned, running costs, net per
   hour so far, offers accepted; a status box that fills as a pickup or trip
   progresses; on desktop a sidebar chart
   of the whole fleet's P1/P2/P3 and riders' wait fraction (log Part 12).
   **Time warp**: frames take 0.3× as long while the player is on a pickup or
   trip and 0.75× while idle (400 ms base per frame; doubled in the big city,
   which draws one frame per minute).
5. **Offers.** The world freezes (the worker holds its loop); the route
   player → pickup → drop-off is drawn over a dimmed map; the card can be
   dragged on desktop. Keys: → / Enter accept, ← / Esc decline. Pausing during
   an offer stops only the countdown, and marks the shift so it can't go on
   the leaderboard. A declined trip goes to another car and is never offered
   to the player again.
6. **End of shift** after 180 minutes. Trips in progress count for the
   share completed, for everyone.
7. **Debrief**, in order: score and share line; **How you compare** (you, the
   bots, the fleet average and percentile, share of fares); the
   **leaderboard** (where the server exists); **Where your time went** (your
   and all drivers' idle / pickup / with-rider split, pay per hour in three
   steps against Ontario's platform-worker minimum, **What your riders
   paid**); **Three things about your shift**; **Your offers** (each offer,
   its rate-card comparison and what happened to declined trips); **How real
   is this?** (sources, simplifications and an FAQ; log Part 15).

## 4. Scale, markets and money

**Scale.** One block = one minute = 0.37 km (22 km/h, typical of Toronto
trips under 12 km). Time and distance are proportional (no traffic). Money
is computed in the game layer; the simulation runs in Simple mode with a
fixed fleet (`equilibration = NONE`). (Log 5.8.)

**Simulation settings** (`ridehail/game/market.py`, `make_game_config`):

| | Standard city | Big city (hidden) |
|---|---|---|
| Size | 32 blocks (11.8 km) | 48 blocks (17.8 km) |
| Fleet | 215 | 6000 (drawn as a heatmap) |
| Demand per minute: Busy / Normal / Slow | 11 / 9 / 5 | 330 / 240 / 130 |

Both: GAMMA trip distances with mean 16 blocks (matches Toronto's trips up
to 12 km), inhomogeneity 0.5 (requests concentrated in the City Centre),
destinations not concentrated, pickup stop 1 minute, riders give up after
10 minutes unassigned, idle cars move in half of the minutes
(`IDLE_VEHICLES_MOVING = 0.5`) and head towards a sampled request origin
with probability 0.25 at each intersection (`IDLE_VEHICLES_RETURNING`).
Markets differ in **demand only**; the fleet is the same (log Part 8).

**Offers** (`pricing.py`; log Part 3). `offer = F(trip_km, pickup_km) ×
e^luck`, rounded to $0.05, at least $3.06. F is fitted to 4,945 Uber offer
cards (Toronto pickups, no airport, trips ≤ 15 km), weighted to Toronto's
mix of trip lengths: pay per km falls with trip length, and long pickups
raise the offer. The luck is drawn once per trip from the offer study's
residual quantiles, so every driver offered a trip shares it, but each
driver's offer depends on their own pickup. The **rate card** ($2.50 +
$0.75/km + $0.18/min, trip only) is a reference for the debrief; it doesn't
set offers.

**Rider fares** (log Part 4): $8.11 + $1.018/km (City of Toronto open data,
2026-01 to 2026-07, fees and 13% HST included, no tips), scaled by the
trip's luck and normalised so the average is unchanged.

**Costs and earnings.** Running costs are $0.56 per km actually driven
(2024 report to the City of Toronto), so a parked idle minute costs
nothing. Earnings accrue per minute with the rider aboard, the remainder at
drop-off. Every driver is measured from their first idle moment in the
shift; the fleet comparison leaves out cars on shift for under 60 minutes
(log 2.10).

## 5. The bots

| Key | Name | Accepts |
|---|---|---|
| `yes` | Takes every offer | everything |
| `hourly_low` | Takes $22/hr or more | offers paying ≥ $22/hr, pickup included |
| `hourly_high` | Takes $33/hr or more | offers paying ≥ $33/hr, pickup included |
| `centre` | Takes trips to the City Centre | drop-offs in the core |

Bots play by the player's rules: one offer a block, and a declined trip
waits for the next block (`DEFER`; log 10.5–10.6). $22 and $33 sit either
side of the best price threshold, which is about $27–33/hr in every market
(log 10.2, 11.4).

## 6. What the markets show (last calibrated 2026-10-03, log 13.7)

Standard city, time split P1 / P2 / P3 and the strategy result:

| Market | Split | Riders giving up | Result |
|---|---|---|---|
| Busy | 0.00 / 0.45 / 0.55 | ~15% | Being picky pays a lot: the $33/hr bot nets $20.0/hr, taking every offer $11.6 |
| Normal | 0.22 / 0.25 / 0.53 | 0 | The best threshold ($30/hr) beats taking every offer by about $5/hr |
| Slow | 0.63 / 0.07 / 0.29 | 0 | Taking every offer is within about $0.30/hr of the best threshold; fussier thresholds lose. The fleet nets about $3.2/hr |

**Not recalibrated since 2026-10-04**, when idle cars started heading to a
sampled request origin instead of the nearest City Centre edge (log 16.11).
The bot rows and market demands may have moved.

## 7. How the pieces fit (web lab)

- **Protocol** (`game-tab.js` header): Play with `game: true` → `init_game`;
  frames carry `results.game` (HUD, overlay, offer); an offer makes the
  worker hold (`nextFrame.waitingFor = "offer"`) until `GameDecision`;
  `shift_over` stops the loop; `GetGameResults` → `"gameResults"`.
- **Offer timing**: a block runs on an odd (interpolated) frame and is shown
  on the next even frame; the offer and `shift_over` travel only on
  real-block frames, so the card appears when the car visibly reaches the
  intersection. Accepting updates the player's direction for the next
  midpoint frame (`GameSimulation.resolve_offer`).
- **Identity**: inside Python, drivers are `vehicle.index`; the frame
  payload converts to positions in the frame's vehicle list
  (`GameController.position`).
- **Big city**: heatmap above 576 cars, with the player's car drawn and
  glided on top (`map.js`; log 7.4).
- **Duplicated values are tested**: `game-setup.js` and the setup screen's
  labels against `ridehail.game` (`test_web_lab_setup_matches_the_game`);
  the interpolation threshold in `worker.py` against `js/constants.js`.
  Not yet tested: `leaderboard.php`'s `KM_PER_MINUTE`, `OPS_COST_PER_KM` and
  shift length.

## 8. Leaderboard

A board is shift code × market × offer screen, standard city only (big-city
shifts keep personal bests in `localStorage` only). Named top scores, no
sign-in, each name's best counts. The server re-checks a submission's
consistency (minutes, km, costs, net) and rejects builds older than
`MIN_SCORING_VERSION` (now `2026.10.4.1`). Ended-early shifts and shifts
paused during an offer can't be submitted. Moderation is by an admin token.
(Log 2.10, 2026-09-30.) Entries are disposable: reset boards freely.

## 9. Checklist when changing the game

- **Python changed** → `./build.sh` before testing in the browser:
  `worker.py` is fetched fresh, but the game logic comes from the wheel.
- **Shifts play out differently** (any change to random draws, markets,
  prices, bots or the simulation) → raise `MIN_SCORING_VERSION` in
  `leaderboard.php` to the next build's version.
- **Markets, prices or bots** → re-run `game_calibrate.py` and
  `game_strategy.py`, and check the Busy / Slow contrast still holds; update
  section 6 here and the setup screen's market descriptions.
- **Offer model** → `uv run --with duckdb --with pandas python
  utils/fit_offer_model.py [--validate N]`; it rewrites `offer_model.py`.
- **Running cost or km per block** → also `leaderboard.php`.
- **Ontario's minimum wage** changes → `ONTARIO_MINIMUM_WAGE` in
  `game-debrief.js`.
- Browser checks are done by the user (we have no browser access).

## 10. Open questions and postponed work

- **Destinations ignore inhomogeneity** for sampled trip distances, so trips
  drain the City Centre (log 5.7, 5.10). Fix would give origins and
  destinations separate concentration settings.
- **Earnings compared with the City-commissioned report**: the game's net
  per in-app hour (~$10 in Normal) is well above the report's median ($5.97,
  2024), and its drivers' share of fares (74–78%) is far above the report's
  (40–60%). Leads in `claude/game-reality-references.md` (log 5.9, 13.8).
- **Recalibration after log 16.11** (section 6).
- **Where to wait** (steering the idle car): built, measured and postponed;
  close to a single answer (log Part 16). Rebuild from log 16.2–16.3.
- **"How real is this?" next steps**: Toronto reference figures beside the
  headline numbers; each offer's percentile among real offers (log Part 15).
- **Smaller ideas**: Busy Friday fares by time of week (log 4.6), the
  player's own time split beside the fleet's (log 12.3), other games (log
  16.9).
- Not run: the big city's threshold sweep.

## 11. Superseded in the log

When reading the log, note that these early sections no longer describe the
game: 1.4–1.5 (prices: now log Part 3), 1.6 and 9 (bots: now Part 10), 1.8
and Pro/difficulty (now offer screens, Part 6), 1.9 and 5.x market tables
(now Parts 8, 11, 13), Part 2's file names (`ridehail/game.py`, now the
package) and worker variables (`offerHeldSettings`, now `nextFrame`), "no
map on phones" (reversed in Part 14), and 0.5 km / 30 km/h blocks (now
0.37 km, log 5.8).
