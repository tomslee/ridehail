# Upfront pricing for the individual strategy

Status: **implemented 2026-10-15** on the `strategy` branch. It extends the
individual strategy (`claude/strategy-config-spec.md`) so that a strategy
can choose among offers by what they pay per engaged hour.

## 1. The idea

Platforms quote each trip a price upfront, and two trips of the same length
can pay quite differently. The game models this with the offers fitted to
Toronto driver offer cards (`ridehail/game/offer_model.py`): a baseline
curve in Toronto dollars and kilometres, times a per-trip "luck" factor.
Only the luck factor is generic: it has no units. So the strategy's offers
are:

    offer = rate card × m

- **Rate card:** the core's fare for the trip,
  `price × (1 − platform_commission) × trip blocks` (with `use_city_scale`,
  `price` is built from the base fare, per-km and per-minute fares). Its
  level and shape are set by the configuration, not by Toronto.
- **m:** a per-trip factor, lognormal with mean 1:
  `m = exp(ε)`, `ε ~ Normal(−σ²/2, σ)`.

## 2. Why these choices

- **Lognormal, not 1 + normal.** Offers are right-skewed: relative to the
  median offer, the offer study's 10th, 25th, 75th and 90th percentiles are
  0.72, 0.83, 1.24 and 1.55. A lognormal with σ = 0.31 gives 0.67, 0.81,
  1.23 and 1.49; 1 + normal with the same spread gives 0.59, 0.79, 1.21 and
  1.41, with too many very poor offers and too few very good ones, and it
  can go negative.
- **Mean 1.** Upfront pricing moves pay between trips but leaves the average
  at the rate card. A car that takes every offer earns, on average, what the
  core's formulas say, so the fleet's `income_and_costs` stay correct.
- **One constant spread.** In the offer study (4,976 Uber offers to
  2026-10-08, weighted to Toronto's trip-length mix) the spread of
  log(offer / fitted curve) is about 0.28-0.33 for trips of every length
  and pickups under 3 km, narrowing to about 0.23-0.25 for the few pickups
  over 5 km (4% of offers). Too small, and too tied to Toronto kilometres,
  to model. Overall σ = 0.31.
- **What it leaves out.** The study shows how much offers vary, not why:
  time of day, surge, the rider. The factor is independent noise, so
  strategies that exploit patterns in offers can't be studied with it.

## 3. Parameter

| Name | Section | Short | Type | Default | Meaning |
|---|---|---|---|---|---|
| `offer_variability` | STRATEGY | `-sov` | float, 0 to 2 | 0 | σ, the spread of log offers around the rate card. 0 is the flat fare; 0.31 matches the offer study. |

It is in [STRATEGY] because only the seated car's offers and income use it.
The game presets (`--preset game`, `game-big`) set it to 0.31.

## 4. Every trip has a price

Each trip's factor is a fixed function of the trip's index and the run's
seed (`random_number_seed`, or a seed drawn when there is none): a
generator seeded with both draws ε. So:

- every trip has its price, whoever is offered it, and in whatever order;
- a declined trip keeps its price when it is offered to another car, as in
  the game;
- the simulation's own random stream is untouched, so `offer_variability`
  changes nothing but the seated car's decisions and income;
- runs with the same seed give the same trips the same factors (until the
  cities diverge).

The fleet's results are not recomputed from the prices: every fleet car
takes every offer, and with a mean of 1 its expected income is the core's.

## 5. The seated car

- **Offers:** the strategy sees `offer = rate card × m`; the offer's rate
  (per hour with `use_city_scale`, otherwise per block) is the offer over
  pickup plus trip blocks, so `rate:N` filters by pay per engaged hour.
- **Income:** in each block it has a rider, the car earns its trip's
  `price × (1 − commission) × m`, so over a trip it earns about the offer.
  Gross income is those earnings over the shift's blocks; net and surplus
  follow as before (net = gross − running cost on blocks driven; surplus =
  net − reservation wage).
- With `offer_variability` = 0, m = 1 and the car's income is exactly the
  core's formula, as before.

## 6. Code and tests

- `ridehail/game/strategy.py`: `StrategyController.offer_factor(trip_index)`,
  `describe_offer()`, the per-block earnings in `after_block()`, `summary()`.
- `ridehail/config.py`: `offer_variability`; `ridehail/presets.py`.
- `test/test_strategy.py`: the factor's mean and spread, its independence
  of order, σ = 0 equal to the formula, and a `rate:N` car earning more per
  rider block than the rate card when offers vary.
