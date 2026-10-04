# Game debrief: candidate Toronto reference figures (2026-10-04)

Step 1 of the "How real is this?" plan (claude/game-mode.md, Part 15): a
Toronto figure beside each headline number on the debrief, where the
definitions match. This file lists the candidates for a decision. Nothing
is implemented yet.

## Sources

- **The report**: Young, Farber and Rahman, *On the Road: Analysis of Driver
  Earnings in Toronto's Vehicle-for-Hire Industry*, final report to the City
  of Toronto (MLS), 2024. Attachment 1 to the Executive Committee item;
  https://www.toronto.ca/legdocs/mmis/2024/ex/bgrd/backgroundfile-251343.pdf
  (48 pages; page numbers below are the printed ones). Every PTC trip
  starting in Toronto, 2023-01-01 to 2024-05-01 (84M records, Uber and
  Lyft), with time overlapping across apps removed.
- **City open data**: `operating_hours` and `trips` from the City's PTC
  open data (claude/game-mode.md 4.2 and 5.3), 2026-01 to 2026-07.
- **Offer study**: 4,945 Uber offer cards shown to Toronto drivers,
  2026-01 to 2026-08 (claude/game-mode.md 1.5, Part 3).

### How the report gets its numbers (pp. 19-22, 35-37)

This matters for every comparison:
- **Earnings are estimated, not observed.** Pay is computed from the
  January 2024 Uber driver rate card (Table 4) and the Lyft Standard card
  (Table 6), applied to each trip's distance and time. The platforms gave no
  pay data. The study period is the rate-card era; upfront offers (which the
  game models) came later.
- **Tips are added**: an assumed $0.80 a trip (from US studies). The game
  has no tips.
- **Surge is patched**: trips whose rate-card pay is under 40% of the fare
  are assumed to be surge trips and reset to 50% of the fare.
- **Costs**: Vincentric per-vehicle costs (fuel, repairs, maintenance,
  depreciation, insurance, financing, fees and taxes). Fixed costs are
  shared with an assumed 20,000 km a year of personal driving. Pre-tax.
  Excludes phone, cleaning, parking, tickets and leasing (the authors say
  costs are therefore more likely under- than overestimated).
- **Time**: P1 waiting / P2 en route (P2.5 waiting at the pickup is
  counted in P2) / P3 with a rider. Engaged = P2 + P3; in-app =
  P1 + P2 + P3. These are the game's definitions: engaged = pickup + trip,
  and the game's shift is its in-app time.
- **Caveats the authors list**: P1 may include drivers declining requests
  or doing food delivery (both would make in-app pay look lower), and
  Lyft Priority Mode is unknown.

## Candidates

Game figures are fleet averages, standard city, idle-moving p = 0.5
(claude/game-mode.md 13.3 and 13.7) unless noted.

### A. Gross pay per engaged hour (first row of "Where your time went")

| Source | Figure | Definition |
|---|---|---|
| Report, Table 8 (p. 25) | median **$33.18** (2024), $33.52 (2023); IQR $30.70-36.76 | rate-card pay + $0.80 tips ÷ (P2 + P3) |
| Offer study (game-mode 1.5) | median **$29.50**; IQR $24.50-37.00 | upfront offer ÷ (pickup + trip), no tips |
| Game, Normal | about $29 (derived: net per engaged hour with engaged costs only, $16.70 in 5.3, plus $12.32/hr running costs at 22 km/h) | offer ÷ (pickup + trip) |

**Assessment: strong.** The definitions match. The offer study is the
closer reference (same era and pay model, no tips). The report's
$33 is about $4 higher, and its $0.80 tips (about $2-3 an hour) explain
most of that. Suggested wording: "Toronto drivers: about $30 per engaged
hour (2026 offer cards); $33 in 2024 with tips (City report)."

### B. Net per hour of shift (the score)

| Source | Figure | Definition |
|---|---|---|
| Report, Table 12 (p. 27) | median **$5.97** (2024), $7.94 (2023); IQR $1.84-9.56 (2024) | (rate-card pay + tips − costs) ÷ in-app hours |
| Report, Table 13 (p. 28; method 2) | median $5.19 (2024), $7.35 (2023) | as above, Lyft estimated from the UberX ratio |
| Game | Normal $10.40, Busy $9.81, Slow $3.18 | (offers − $0.56/km) ÷ shift hours |

**Assessment: definitions match; the numbers don't yet (the open 5.9
question).** Game Normal and Busy are about $4 an hour above the 2024
median, inside the report's upper quartile. A likely cause, to check: the
report's median cost is **$16.31 an hour** (Table 11, p. 26), which at its
median $0.56/km implies about **29 km driven per hour**. The game drives at
most 22 km/h, and idle cars move only half the time, so its costs are
about $10-11 an hour. If Table 11's hours are in-app hours (the table
doesn't say), that difference alone is about the size of the gap. The
report's tips push the other way (about +$2/hr).

Recommendation: settle this before showing a reference, because a
reference here invites the player to compare their score directly. The
cheap check is the per-hour basis of Table 11 (ask the authors or the City,
or compare with Table 7's km and hours). Possible wording once settled:
"The median Toronto driver netted about $6 per hour in the app in 2024
(City report)."

### C. Time split (idle / pickup / with a rider)

| Source | Idle | Pickup | With a rider |
|---|---|---|---|
| Report, Table 7 (p. 25), 2024 | 34.5% | 11.1% (P2 7.9 + P2.5 3.2) | **54.4%** |
| Report, 2023 | 25.8% | 12.8% | 61.4% |
| City open data 2026, average (5.3) | about 30% | 13-16% | 43-56% by hour |
| Game Normal | 22% | 25% | 53% |
| Game Busy | ≈ 0% | ≈ 50% | ≈ 50% |
| Game Slow | 63% | 7% | 29% |

**Assessment: good match on definitions; mixed on values, by design.**
Normal's with-rider share is realistic but its pickups are twice the real
share (known since 5.3). Busy and Slow are deliberately the extremes:
Slow's 29% with a rider is below the quietest real slice (Tue/Wed 1-5 am,
43%). Showing "Toronto: 54% with a rider" beside a Slow shift would be
honest but would read as "unrealistic". Suggested: show the real range
with its time of week ("Toronto drivers spend 43-56% of their app time with
a rider, depending on the hour; City open data, 2026"), not a single
number.

### D. Share of fares ("How you compare")

| Source | Figure | Definition |
|---|---|---|
| Report, pp. 20 and 36 | **40-60%, average 50%**, before tips | rate-card driver pay ÷ passenger fare, from the Uber rate card (fees: Table 5, 25% service fee for drivers after Aug 2015, plus booking fee, City fees and HST in the fare) |
| US pay statements (game-mode 4.4) | platform take 16% ± 7% a trip | unclear fare basis |
| Game | fleet **74-78%** | offer ÷ rider fare before HST (rider fare from City open data, includes City fees) |

**Assessment: do not show yet; this needs investigation.** The report's
40-60% is far below the game's 74-78%. Even if the report's fare includes
13% HST, 50% of the fare is about 57% of the fare before HST. Possible
explanations: the report's ratio is the rate-card era (2023-24) while the
game's offers are 2026 upfront offers; the passenger fare may include
booking fees and surge; the report's ratio is a rule-of-thumb band used to
detect surge, not a measured average. But the debrief already shows "Share
of fares" and says the rest went to the platform, so a real gap here
matters more than a missing reference. A fair test: the offer study's own
cards, if any show the rider's fare (did the study record it?), or the
FOIA UberX data (game-mode 4.3) with the Jan 2024 rate card applied.

### E. Minimum wage context (beside the score or the hourly steps)

| Source | Figure |
|---|---|
| Report, Table 12 (p. 27), 2024 | **58%** of drivers netted below the minimum wage ($16.55) per engaged hour; **99%** per in-app hour (2023: 57% and 96%) |

**Assessment: strong as context, and clearly sourced.** It isn't a like-for-
like comparison with one player's shift, so it fits as a sentence in the
hourly-steps note ("In 2024, over 95% of Toronto drivers netted less than
the minimum wage per hour in the app") rather than a number beside the
score. Caveat: the report compares *net* pay with the minimum; Ontario's
rule applies to *gross* engaged pay, as the debrief explains. Wording must
keep the two apart.

### F. Running costs (already cited)

Report, Table 11 (p. 26): median **$0.56 a km** (fixed $0.10 + variable
$0.46; IQR of variable $0.39-0.55). The game's figure and its citation
(page 26) are correct. The FAQ's "most of the cost is variable" matches
(variable is over three-quarters).

## Summary for the decision

| Debrief number | Reference | Ready? |
|---|---|---|
| Gross per engaged hour | Offer study $29.50 (and report $33 with tips) | **Yes** |
| Minimum wage context | Report: 58% / 99% below | **Yes** (as a sentence) |
| Time split | City open data 2026 range | **Yes** (as a range) |
| Net per hour (score) | Report median $5.97 | **After** settling the cost-per-hour question (B) |
| Share of fares | Report 40-60% | **No**: the gap with the game needs investigating first (D) |
