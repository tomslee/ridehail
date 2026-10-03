# Dispatch sparse/dense changeover: measurement and a per-trip criterion

October 2026. Follows the June 2026 fix (`Dispatch._use_sparse_search`,
"sparse when P1 < city_size").

**Status: IMPLEMENTED 2026-10-03.** `Dispatch._use_sparse_search(m, city_size)`
is now a per-trip test, `m <= SPARSE_SEARCH_FACTOR * city_size` (factor 1.0),
applied in `_dispatch_vehicles_default`. Tests:
`test/test_dispatch_performance.py`. Benchmarks: `benchmarks/bench_dispatch.py`
(see `benchmarks/README.md`). The `sparse` digest in
`test/test_dispatch_offer_filter.py` was re-recorded.

## The two searches (DEFAULT dispatch)

- **Sparse** (`_dispatch_vehicle_sparse`): each trip scans the remaining idle
  (P1) list. Cost per trip ~ `k_s * m`, where `m` = idle vehicles *remaining*.
- **Dense** (`_dispatch_vehicle_dense`): build a dict grid of idle vehicles
  (O(P1)), then each trip ring-searches outward. Cost per trip ~
  `k_d * C^2 / m` (C = city_size), up to a whole-city scan as `m -> 1`.

The per-trip costs are equal at `m* = C * sqrt(k_d' / k_s)`, which we measure
at about `1.0-1.5 * C`. That is the threshold the current rule uses.

## What is wrong with the current rule

The rule is evaluated **once per block, with the initial P1**. But every
successful dispatch removes a vehicle, so `m` falls during the block. When the
backlog is at least the idle pool (T >= P1, so every undersupplied block), the
pool drains to zero:

- dense total ~ `k_d * C^2 * (1/P1 + 1/(P1-1) + ... + 1/1)` ~ `k_d * C^2 * ln P1`.
  The tail (the last few vehicles, found only after scanning most of the city)
  dominates.
- sparse total ~ `k_s * P1^2 / 2`.

So when T >= P1 the block-level crossover moves out to P1 ~ 2-3 C, and it
depends on T as well. Whichever search the block picks, it is the wrong one for
part of the block: dense is wasteful at the end, and sparse at the start.

## Measurements (CPython, real `Dispatch` code on stub vehicles and trips)

Reproduce with `benchmarks/bench_dispatch.py` (`synthetic`, and `scenarios`
with `--factors`). It times the real `_dispatch_vehicles_default` on identical
states, with the decision forced or left to the rule.

**Synthetic uniform states** (C = 16-96, P1 = 2-3072, T = 1, 0.1, 0.5, 1 and 4 x P1).
Observed block-level crossover (first P1 at which dense wins):

| T / P1 | C=16 | C=32 | C=48 | C=64 | C=96 |
| --- | --- | --- | --- | --- | --- |
| 0.1 | 24 | 24 | 48 | 64 | 96 |
| 0.5 | 32 | 48 | 64 | 96 | 128 |
| 1   | 64 | 128 | 192 | 192 | 384 |
| 4   | 64 | 128 | 192 | 192 | 384 |

With small T, the current rule matches the measured crossover. When T >= P1 it
switches to dense too early: up to 5.7x slower than the better search (C=96,
P1=128: 29 ms vs 5 ms per block). The drained cases total 1125 ms with the
current rule, against 1054 ms if every block picked the faster search.

**Real simulation states**: every dispatch call was captured from the game
markets (standard and big city, busy/normal/slow, seed 7, 240 blocks) and
the `test/perf` configs, then replayed with each search forced. Total dispatch
time:

| run | current rule | best block-level choice | per-trip hybrid (alpha = 1) |
| --- | --- | --- | --- |
| game big busy | 3806 ms | 3776 ms | **1753 ms** |
| game big normal | 2006 | 2006 | 2058 |
| game big slow | 1480 | 1480 | 1444 |
| game standard (3 markets) | 135 | 125 | 131 |
| perf_boundary / dense / sparse | 70 | 70 | 71 |

The current rule is already close to the best block-level choice on real runs.
In other words, no once-per-block criterion can fix big-city busy. There
P1 ~ 250-300 (about 6C) and T >> P1, and both searches cost 15-25 ms per block
because of the drain. Repeated runs vary by about 10%, so differences under
about 5% are noise.

## Criterion: decide per trip, from the remaining pool

```
m* = ALPHA * city_size            # ALPHA = 1.0 (flat optimum 1.0-1.5)
if P1 > m*:
    build grid + set
    dense-dispatch trips while len(pool) > m*
    lst = [v for v in shuffled_list if v in pool]   # keep shuffled order
sparse-dispatch the remaining trips while lst is non-empty
```

- The choice is monotone. `m` only falls, so it goes dense -> sparse at most
  once per block. Sparse -> dense never happens.
- T drops out of the criterion. Its only role was as a proxy for the drain,
  and the drain is now handled directly. The grid build (O(P1), cheap) needs
  no separate term, because dense only runs while `m > m*`.
- Once the pool is empty, the trip loop stops. This is behaviour-neutral:
  neither search uses the RNG on an empty pool.
- Nearest-vehicle correctness was checked on sampled real states (every
  assignment is at the true minimum distance over the remaining pool).
- ALPHA sweep (0.5-3.0): totals are flat between 1.0 and 1.5 and get worse
  outside that range. We pick 1.0 because it keeps the existing, already
  validated threshold. Only *where* it is applied changes.

Results: big-busy dispatch -54%, synthetic drained cases -45% (below even
the best block-level choice), and no measurable loss elsewhere.

## Consequences

- Not bit-identical: within a block, trips switch search at a different point,
  so random tie-breaking draws differ (`random.choice` in dense, shuffle order
  in sparse). The two are statistically equivalent. Regression baselines and
  game shift codes change, so bump `MIN_SCORING_VERSION`.
- `offer_filter` / `offline` still work: both find functions take the declined
  set, and the switch only rebuilds the list from the pool set.
- `test/test_dispatch_performance.py` was rewritten. Part A tests the
  threshold and drives a drained block through the real dispatcher (dense,
  then sparse, switching once; stops at an empty pool; nearest-vehicle check).
  Part B (`-m regression`) records the pool size at every per-trip search in
  the perf configs.
- FORWARD_DISPATCH always uses the dense grid and has the same drain tail, but
  it is out of scope here.

## What remains in big-busy

About 7 ms per block remains. It is mostly dense ring searches while
200+ idle cars are clustered in the outskirts and trips start in the core,
where `C^2/m` underestimates the search. Further gains would come from cheaper
dense steps rather than a better criterion: precomputed ring offsets, and
dropping the per-cell `set([y_lower, y_upper])`, which is only kept to stay
bit-identical.
