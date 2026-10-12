# Big city strategy scan across supply and demand (2026-10-09)

A first step towards using Just One More Shift as an analytical tool: how
the four bot strategies fare in the big city as the supply/demand balance
changes. Also logged as Part 17 of `claude/game-mode.md`. Chart and table:
https://claude.ai/artifact/LdaQwucMdQMQUVvgUUHDb3

## Method

- **Environment:** the big city (48 blocks, 6000 cars), with the fleet fixed
  and demand varied over 100, 130, 160, 200, 240, 285, 330, 365 and 400
  requests/min. The game's markets are Slow 130, Normal 240 and Busy 330.
- **Held at game settings:** idle cars move in half of idle minutes
  (`IDLE_VEHICLES_MOVING` 0.5) and head for a sampled request origin with
  p = 0.25 (`IDLE_VEHICLES_RETURNING`). Also the 10-minute rider wait limit,
  current offer pricing, a 60-minute warm-up and a 180-minute shift.
- **Strategies:** the four bots, Takes $33/hr or more, Takes $22/hr or more,
  Takes trips to the City Centre and Takes every offer, plus the fleet mean
  (every other car, all of which take every offer).
- **Seats:** each shift seats 10 cars per bot instead of one. Simulating the
  6000-car fleet is almost all of a shift's cost (about 10-18 s), so extra
  seats are almost free. The 40 seats are under 1% of the fleet.
- **Samples:** 20 shifts per demand level, 180 shifts in all. With 2
  workers at nice 10 the run took about 25 minutes. Standard errors are
  across shifts (each shift's mean over its 10 cars), about $0.15-0.6/hr.
- **Metric:** net $/hr, meaning earnings minus running costs over time on
  shift.

## Results: net $/hr

Best in each row in bold; ± about $0.2-0.6.

| Demand (requests/min) | Fleet P1 / P2 / P3 | Riders giving up | $33/hr | $22/hr | City Centre | Every offer | Fleet mean |
|---|---|---|---|---|---|---|---|
| 100 | 0.72 / 0.04 / 0.24 | 0 | **2.08** | 0.85 | **2.07** | 1.31 | 0.90 |
| 130 (Slow) | 0.62 / 0.07 / 0.31 | 0 | 5.38 | 3.53 | **7.45** | 3.49 | 2.95 |
| 160 | 0.51 / 0.11 / 0.39 | 0 | 9.30 | 7.09 | **11.21** | 5.65 | 5.03 |
| 200 | 0.35 / 0.17 / 0.48 | 0 | 13.14 | 10.75 | **14.15** | 8.62 | 7.82 |
| 240 (Normal) | 0.18 / 0.23 / 0.59 | 0 | **19.66** | 14.80 | 16.34 | 11.94 | 10.72 |
| 285 | 0.00 / 0.33 / 0.67 | 3.8% | **24.49** | 18.56 | 17.76 | 13.46 | 13.02 |
| 330 (Busy) | 0.00 / 0.33 / 0.68 | 17.7% | **24.64** | 19.11 | 17.69 | 13.34 | 13.16 |
| 365 | 0.00 / 0.33 / 0.67 | 26.0% | **24.59** | 19.30 | 16.88 | 13.76 | 13.15 |
| 400 | 0.00 / 0.33 / 0.67 | 32.7% | **24.78** | 18.77 | 18.11 | 13.25 | 13.15 |

## Results: acceptance and idle minutes per accepted trip

| Demand | $33/hr | $22/hr | City Centre | Every offer |
|---|---|---|---|---|
| 100 | 54% / 44.3 | 87% / 47.1 | 48% / 33.2 | 100% / 40.6 |
| 130 | 47% / 30.1 | 83% / 28.6 | 46% / 12.4 | 100% / 26.2 |
| 160 | 39% / 19.1 | 80% / 17.4 | 47% / 7.0 | 100% / 17.7 |
| 200 | 37% / 11.9 | 77% / 9.7 | 49% / 3.4 | 100% / 8.9 |
| 240 | 36% / 5.4 | 70% / 4.2 | 48% / 2.1 | 100% / 3.4 |
| 285 | 34% / 2.0 | 68% / 0.5 | 50% / 1.1 | 100% / 0.0 |
| 330 | 33% / 2.0 | 71% / 0.4 | 48% / 1.1 | 100% / 0.0 |
| 365 | 34% / 1.9 | 69% / 0.5 | 47% / 1.1 | 100% / 0.0 |
| 400 | 33% / 2.0 | 68% / 0.5 | 49% / 1.0 | 100% / 0.0 |

## Findings

- **There are three regimes.**
  - **Slack (up to about 160):** P1 is half the fleet's time or more,
    everyone earns little, and the City Centre rule is best.
  - **Middle (200-240):** the $33/hr threshold catches up and passes the City
    Centre rule near Normal.
  - **Saturated (from about 285):** P1 reaches 0 between 240 and 285. From
    285 to 400 every strategy's earnings stay the same and only the share of
    riders giving up rises, from 4% to 33%.
- **Busy (330) is well inside the saturated regime,** so more demand there
  changes nothing for drivers. All the variety is between about 100 and 285.
- **Taking every offer never wins, even at 100 requests/min.** At Slow the
  game's design aim, that taking every offer does about as well as any
  threshold, fails in the big city: City Centre $7.45, $33/hr $5.38, every
  offer $3.49. This fits the note in `claude/game-design.md` section 6 that
  the markets have not been recalibrated since idle cars started heading to
  a sampled request origin (game-mode.md 16.11).
- **The City Centre rule wins on idle time.** At 130 it waits 12.4 idle
  minutes per accepted trip, against 26 for taking every offer and 30 for
  $33/hr. Its acceptance stays near 48% at every demand, because it depends
  on where trips end, not on prices.
- **The $22/hr threshold is never best.** It always sits between taking every
  offer and the stronger rules.
- **When the fleet is saturated, declining costs almost nothing.** The
  $33/hr bot waits about 2 minutes per accepted trip, so being choosy is
  worth about $11/hr over taking every offer.
- **The take-every-offer bot beats the fleet mean by $0.1-1.2/hr,** though
  both take every offer. A likely cause, not yet checked: seated cars are
  offline during warm-up, so they drift towards request origins without
  being dispatched and start the shift better placed than fleet cars, which
  settle where demand is thin (game-mode.md 16.10). The gap is largest when
  idle time matters and vanishes at saturation. It affects comparisons with
  the fleet mean, not the ranking among bots.

## Next steps

1. Sample 200-300 requests/min more finely, where the ranking changes and
   the fleet saturates; drop 365 and 400.
2. Add a sweep across $/hr thresholds as extra seats in the same shifts,
   which costs little extra run time.
3. Check the warm-up placement explanation, for example by measuring seated
   and fleet cars' distance to the core at the start of the shift.
4. Later: vary the idle-car settings (`IDLE_VEHICLES_MOVING`,
   `IDLE_VEHICLES_RETURNING`).

## Reproducing

```bash
uv run python utils/game_environment_scan.py              # full scan (resumable)
uv run python utils/game_environment_scan.py --summarise-only
uv run python utils/game_environment_scan.py --demand 240 --seeds 1 --workers 1
```

Options: `--demand` (comma-separated list), `--seeds` (shifts per demand,
default 20), `--cars-per-bot` (default 10), `--workers` (default 2),
`--nice` (default 10), `--out` (default `out/game_environment_scan.csv`).

Outputs, none tracked by git:
- `out/game_environment_scan.csv`: one row per shift and strategy.
- `out/game_environment_scan_summary.csv`: the summary by demand and strategy.
- `out/game_environment_scan.html`: the page, built from
  `utils/game_environment_scan_page.html`, with notes from
  `out/game_environment_scan_notes.html`.
