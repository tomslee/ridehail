# Big city strategy scan across supply and demand (2026-10-09, rerun 2026-10-13)

A first step towards using Just One More Shift as an analytical tool: how
the four bot strategies fare in the big city as the supply/demand balance
changes. Also logged as Part 17 of `claude/game-mode.md`. Chart and table:
https://claude.ai/artifact/LdaQwucMdQMQUVvgUUHDb3

The results below are the 2026-10-13 rerun, after two changes to the game
(see "Follow-up" below): the player and bots are seated at random after the
warm-up, and a trip under way when the shift starts is paid for the rest.
The first run (2026-10-09) gave the bots a head start; its numbers are kept
in `out/game_environment_scan_summary.csv`, and this run's in
`out/game_environment_scan_2026-10-13_summary.csv`.

## Method

- **Environment:** the big city (48 blocks, 6000 cars), with the fleet fixed
  and demand varied over 100, 130, 160, 200, 240, 250, 260, 270, 280, 285,
  330, 365 and 400 requests/min (250-280 added the same day).
  The game's markets were Slow 130, Normal 240 and Busy 330; Busy is now
  265 (game-mode.md 17.9).
- **Held at game settings:** idle cars move in half of idle minutes
  (`IDLE_VEHICLES_MOVING` 0.5) and head for a sampled request origin with
  p = 0.25 (`IDLE_VEHICLES_RETURNING`). Also the 10-minute rider wait limit,
  current offer pricing, a 60-minute warm-up and a 180-minute shift.
- **Strategies:** the four bots, Takes $33/hr or more, Takes $22/hr or more,
  Takes trips to the City Centre and Takes every offer, plus the fleet mean
  (every other car, all of which take every offer).
- **Seats:** each shift seats 40 cars per bot (10 in the first run) in cars
  chosen at random when the warm-up ends. Simulating the 6000-car fleet is
  almost all of a shift's cost (about 11-18 s), so extra seats are almost
  free. The 160 seats are under 3% of the fleet.
- **Samples:** 20 shifts per demand level, 280 shifts in all, the same shift
  codes as the first run. With 2 workers at nice 10 the first nine levels
  took about 22 minutes. Standard errors are across shifts (each shift's mean over its 40
  cars), $0.08-0.37/hr.
- **Metric:** net $/hr, meaning earnings minus running costs over the
  180-minute shift.

## Results: net $/hr

Best in each row in bold, with any bot within $0.30 of it; ± $0.1-0.4.

| Demand (requests/min) | Fleet P1 / P2 / P3 | Riders giving up | $33/hr | $22/hr | City Centre | Every offer | Fleet mean |
|---|---|---|---|---|---|---|---|
| 100 | 0.71 / 0.04 / 0.26 | 0 | **1.56** | 1.47 | **1.77** | 1.12 | 1.27 |
| 130 (Slow) | 0.60 / 0.07 / 0.33 | 0 | 4.32 | 3.93 | **7.29** | 3.64 | 3.35 |
| 160 | 0.49 / 0.10 / 0.40 | 0 | 7.44 | 6.36 | **9.08** | 5.48 | 5.47 |
| 200 | 0.34 / 0.16 / 0.50 | 0 | **11.83** | 9.90 | 11.06 | 7.99 | 8.27 |
| 240 (Normal) | 0.17 / 0.23 / 0.61 | 0 | **16.67** | 14.12 | 14.46 | 11.13 | 11.14 |
| 250 | 0.13 / 0.24 / 0.63 | 0 | **18.39** | 15.18 | 14.64 | 11.71 | 11.87 |
| 260 | 0.08 / 0.26 / 0.66 | 0 | **20.02** | 16.75 | 15.71 | 12.62 | 12.59 |
| 265 (Busy) | 0.06 / 0.27 / 0.67 | 0 | **21.09** | 16.85 | 15.88 | 12.97 | 12.93 |
| 270 | 0.02 / 0.30 / 0.68 | 0 | **22.89** | 17.94 | 16.37 | 13.32 | 13.19 |
| 280 | 0.01 / 0.31 / 0.68 | 2.0% | **23.74** | 18.53 | 16.54 | 13.23 | 13.32 |
| 285 | 0.00 / 0.31 / 0.69 | 3.6% | **23.95** | 18.36 | 16.75 | 13.38 | 13.36 |
| 330 (old Busy) | 0.00 / 0.31 / 0.69 | 17.5% | **23.80** | 18.62 | 16.84 | 13.59 | 13.57 |
| 365 | 0.00 / 0.31 / 0.69 | 25.9% | **23.78** | 18.47 | 16.89 | 13.47 | 13.59 |
| 400 | 0.00 / 0.31 / 0.69 | 32.4% | **23.90** | 18.57 | 16.90 | 13.57 | 13.62 |

## Results: acceptance and idle minutes per accepted trip

| Demand | $33/hr | $22/hr | City Centre | Every offer |
|---|---|---|---|---|
| 100 | 51% / 49.9 | 88% / 44.4 | 46% / 33.8 | 100% / 44.5 |
| 130 | 44% / 33.5 | 83% / 29.5 | 46% / 13.3 | 100% / 27.4 |
| 160 | 39% / 23.0 | 78% / 19.9 | 46% / 9.9 | 100% / 18.8 |
| 200 | 36% / 14.1 | 75% / 11.3 | 45% / 6.6 | 100% / 10.8 |
| 240 | 34% / 7.9 | 71% / 5.0 | 45% / 3.3 | 100% / 4.5 |
| 250 | 33% / 6.2 | 70% / 3.9 | 45% / 3.1 | 100% / 3.2 |
| 260 | 33% / 4.8 | 71% / 2.4 | 45% / 2.2 | 100% / 2.0 |
| 265 | 33% / 4.0 | 69% / 2.0 | 45% / 1.9 | 100% / 1.3 |
| 270 | 32% / 2.8 | 68% / 1.0 | 46% / 1.7 | 100% / 0.5 |
| 280 | 32% / 2.2 | 68% / 0.6 | 46% / 1.3 | 100% / 0.1 |
| 285 | 31% / 2.2 | 69% / 0.5 | 45% / 1.3 | 100% / 0.1 |
| 330 | 32% / 2.1 | 68% / 0.5 | 45% / 1.2 | 100% / 0.0 |
| 365 | 32% / 2.1 | 68% / 0.5 | 46% / 1.2 | 100% / 0.0 |
| 400 | 32% / 2.1 | 69% / 0.5 | 45% / 1.2 | 100% / 0.0 |

## Findings

- **Taking every offer now matches the fleet mean** at every demand level
  (within $0.3/hr), as it should: both take every offer. In the first run
  it was $0.1-1.2/hr ahead, because seated cars started the shift better
  placed (see "Follow-up").
- **There are three regimes.**
  - **Slack (up to about 160):** P1 is half the fleet's time or more,
    everyone earns little, and the City Centre rule is best (at 100 it ties
    with $33/hr).
  - **Middle (200-240):** the $33/hr threshold has passed the City Centre
    rule by 200. In the first run that crossing came between 200 and 240.
  - **Saturated (from about 280):** P1 falls fast above 240: 0.13 at 250,
    0.08 at 260, 0.02 at 270 and under 0.01 at 280. From
    285 to 400 every strategy's earnings stay the same and only the share of
    riders giving up rises, from 4% to 32%.
- **The old Busy (330) was well inside the saturated regime,** so more
  demand there changed nothing for drivers. All the variety is between
  about 100 and 285, so Busy is now 265, where P1 is about 0.05
  (game-mode.md 17.9).
- **Taking every offer never wins, even at 100 requests/min.** At Slow the
  game's design aim, that taking every offer does about as well as any
  threshold, still fails in the big city because of the City Centre rule
  ($7.29 against $3.64). The $33/hr threshold is now only $0.7 ahead of
  taking every offer at Slow (it was $1.9).
- **The City Centre rule wins on idle time.** At 130 it waits 13.3 idle
  minutes per accepted trip, against 27 for taking every offer and 34 for
  $33/hr. Its acceptance stays near 45% at every demand, because it depends
  on where trips end, not on prices.
- **The $22/hr threshold is never best.** It always sits between taking every
  offer and the stronger rules.
- **When the fleet is saturated, declining costs almost nothing.** The
  $33/hr bot waits about 2 minutes per accepted trip, so being choosy is
  worth about $10/hr over taking every offer.
- **Change from the first run:** the fleet mean rose about $0.4/hr (cars
  busy at the start are now paid for the rest of their trip), and the
  choosy bots fell, by up to $3/hr ($33/hr at 240, City Centre at 200),
  having lost their head start. Rankings are unchanged except at 200 and at
  100.

## Next steps

1. Sample 200-300 requests/min more finely, where the ranking changes and
   the fleet saturates; drop 365 and 400.
2. Add a sweep across $/hr thresholds as extra seats in the same shifts,
   which costs little extra run time.
3. Done 2026-10-13 (see the follow-up below). Check the warm-up placement explanation, for example by measuring seated
   and fleet cars' distance to the core at the start of the shift.
4. Later: vary the idle-car settings (`IDLE_VEHICLES_MOVING`,
   `IDLE_VEHICLES_RETURNING`).

## Follow-up: why the every-offer bot beats the fleet mean (2026-10-13)

**Answer: where the bots start the shift.** Seated cars sit out the 60-minute
warm-up without being dispatched, so they drift towards request origins and
start the shift nearer the City Centre than idle fleet cars, which settle
where demand is thin. The bot code does not favour them: the same bot,
seated after the warm-up on fleet cars that are idle at the start, earns
what those fleet cars earn.

**Method:** a one-off script (`warmup_check.py`, in the session's scratch
directory, not the repository). It ran 10 shifts at each of 130, 240 and 330
requests/min in the big city. Each shift had 40 every-offer bots seated
before the warm-up as now ("seated"), 40 seated after it on fleet cars idle
at the start ("late"), and the other three bots at 10 seats each. Fleet cars
are split by phase at the start. Distance is from the city centre (torus,
blocks; about 24 for a random location).

| Demand | Group | Cars | Net $/hr | vs fleet mean | Gross $/min, first 30 min | Gross $/min, later | Start distance |
|---|---|---|---|---|---|---|---|
| 130 | seated | 40 | 3.94 | **+1.02 ± 0.20** | 0.182 | 0.213 | 17.6 |
| 130 | late | 40 | 2.86 | −0.06 ± 0.34 | 0.145 | 0.193 | 21.2 |
| 130 | fleet idle at start | 3620 | 2.97 | +0.05 | 0.150 | 0.196 | 20.8 |
| 130 | fleet, all | 5889 | 2.92 | 0 | 0.145 | 0.195 | 20.5 |
| 240 | seated | 40 | 11.68 | **+0.98 ± 0.24** | 0.378 | 0.377 | 16.9 |
| 240 | late | 40 | 10.13 | −0.58 ± 0.24 | 0.216 | 0.372 | 29.3 |
| 240 | fleet idle at start | 1555 | 10.05 | −0.66 | 0.222 | 0.368 | 29.1 |
| 240 | fleet, all | 5889 | 10.71 | 0 | 0.286 | 0.370 | 22.5 |
| 330 | seated | 40 | 13.14 | +0.03 ± 0.19 | 0.410 | 0.417 | 17.8 |
| 330 | fleet, all | 5929 | 13.12 | 0 | 0.368 | 0.422 | 20.3 |

(At 330 almost no fleet car is idle at the start, so there is no "late"
group.)

- **Seated bots beat the fleet mean by about $1/hr at Slow and Normal and
  not at Busy,** as in the scan.
- **Late-seated bots match their fleet counterparts** (−0.06 against +0.05
  at 130; −0.58 against −0.66 at 240). The bot path through the offer filter
  is not the cause.
- **The head start is location.** Seated cars start about 17 blocks from the
  centre against 29 for idle fleet cars at Normal. At Normal the advantage
  is spent in the first 30 minutes (0.378 against 0.216 $/min, then level).
  At Slow, when cars stay idle longer, it lasts longer (later rate 0.213
  against 0.193).
- **Which fleet cars you compare with matters too.** At Normal, fleet cars
  idle at the start are $0.66/hr below the fleet mean, and cars on a pickup
  at the start are $0.56 above it.

**Consequences:**
- Rankings among bots are unaffected: every bot gets the same head start.
- In the game itself the player also sits out the warm-up, so the player's
  comparison with "All drivers" in the debrief carries the same head start
  of about $1/hr at Slow and Normal.
- Possible remedies, not chosen: seat the cars after the warm-up on random
  fleet cars, joining when any current trip ends, which matches the fleet
  exactly but means the player may log on mid-trip; keep the seated cars in
  the warm-up but out of dispatch only for its last few minutes; or keep the
  current behaviour and say in the debrief that the player logs on well
  placed.

**Adopted 2026-10-13: seat after the warm-up (remedy 1).**
`GameController.warm_up()` now runs the warm-up with nobody logged off, then
seats the player and the bots in cars chosen at random from the whole fleet
(`_take_seats`). A seated car on a pickup or trip finished it unpaid and
joined when it ended (superseded the same day; see below). The debrief's unpaid and pickup shares now divide by the
player's own minutes on shift. `GameController(..., cars_per_bot=N)` replaces
the scan script's re-seating. Check run: 10 shifts each, 40 cars per bot,
same shift codes as the scan; net $/hr before (the scan, 10 cars per bot)
and after:

| Demand | $33/hr | $22/hr | City Centre | Every offer | Fleet mean | Every offer − fleet |
|---|---|---|---|---|---|---|
| 130 before | 5.38 | 3.53 | 7.45 | 3.49 | 2.95 | +0.54 |
| 130 after | 3.53 ± 0.27 | 3.60 ± 0.24 | 7.22 ± 0.49 | 3.24 ± 0.38 | 2.92 | +0.32 ± 0.38 |
| 240 before | 19.66 | 14.80 | 16.34 | 11.94 | 10.72 | +1.22 |
| 240 after | 16.91 ± 0.32 | 13.45 ± 0.28 | 13.97 ± 0.31 | 10.48 ± 0.26 | 10.66 | −0.18 ± 0.26 |

- The every-offer bot is now level with the fleet, within one standard
  error.
- The choosier bots lost more than $1/hr: $33/hr fell by $1.9 (Slow) and
  $2.8 (Normal), City Centre by $2.4 at Normal. They spend more of the
  shift idle, so a start near the centre was worth more to them.
- At Slow, $33/hr is now level with taking every offer, closer to the
  game's design aim, though the City Centre rule is still far ahead.
- The first full scan predated this change and overstated every bot; it
  was rerun on 2026-10-13 (the tables above).

**Adopted 2026-10-13, later: pay for trips under way at the start.**
Instead of joining when a trip under way ends, every car is now on shift
from the first block (`ShiftBase.start_shift`). A car on a pickup is paid
the whole offer; one carrying a rider has its running total started at the
share of the trip already driven, so it is paid for the distance still to
drive. This mirrors the end of the shift, where a trip still under way is
paid for the part driven. Everyone has the full 180 minutes. Same check (10
shifts, 40 cars per bot, same codes):

| Demand | $33/hr | $22/hr | City Centre | Every offer | Fleet mean | Every offer − fleet |
|---|---|---|---|---|---|---|
| 130 join at drop-off | 3.53 ± 0.27 | 3.60 ± 0.24 | 7.22 ± 0.49 | 3.24 ± 0.38 | 2.92 | +0.33 ± 0.38 |
| 130 pay the rest | 4.01 ± 0.24 | 4.03 ± 0.26 | 7.61 ± 0.49 | 3.70 ± 0.37 | 3.35 | +0.35 ± 0.37 |
| 240 join at drop-off | 16.91 ± 0.32 | 13.45 ± 0.28 | 13.97 ± 0.31 | 10.48 ± 0.26 | 10.66 | −0.18 ± 0.26 |
| 240 pay the rest | 17.12 ± 0.30 | 13.81 ± 0.30 | 14.37 ± 0.31 | 10.94 ± 0.23 | 11.13 | −0.19 ± 0.24 |

- Every row rises by $0.2–0.5/hr. Cars idle at the start (about 60% of the
  fleet at 130, 17% at 240) are unaffected. A car busy at the start used to
  be measured from its first idle moment, so its window always opened idle;
  now it opens with the paid rest of the trip. The gaps between strategies
  and the every-offer gap are unchanged.
- At 130, 20 shifts give every offer − fleet +0.28 ± 0.21. A first run with
  10 cars per bot gave +1.12 ± 0.23 on codes 0–9 but −0.29 ± 0.44 on codes
  10–19: an unlucky draw, not a bias.

## Reproducing

```bash
uv run python utils/game_environment_scan.py              # full scan (resumable)
# the 2026-10-13 rerun:
uv run python utils/game_environment_scan.py --out out/game_environment_scan_2026-10-13.csv
uv run python utils/game_environment_scan.py --summarise-only
uv run python utils/game_environment_scan.py --demand 240 --seeds 1 --workers 1
```

Options: `--demand` (comma-separated list), `--seeds` (shifts per demand,
default 20), `--cars-per-bot` (default 40; with 10, 10 shifts gave a
misleading $1/hr gap), `--workers` (default 2),
`--nice` (default 10), `--out` (default `out/game_environment_scan.csv`).

Outputs, none tracked by git:
- `out/game_environment_scan.csv`: one row per shift and strategy.
- `out/game_environment_scan_summary.csv`: the summary by demand and strategy.
- `out/game_environment_scan.html`: the page, built from
  `utils/game_environment_scan_page.html`, with notes from
  `out/game_environment_scan_notes.html`.
