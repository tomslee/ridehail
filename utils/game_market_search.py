"""
Search game market settings (ridehail/game/) for a target time split.

Each case is a fleet size and a demand (requests per minute); the script
runs the plain simulation (no game controller) for several seeds and prints
the fleet's time split (P1 / P2 / P3), the mean pickup distance (blocks)
and the share of riders who gave up. It reuses
utils/game_pickup_diagnostic.run, so it uses that script's 60-block warm-up,
180 measured blocks and 10-minute cancellation. Trip length and
inhomogeneity are the game's (mean trip 16 blocks, inhomogeneity 0.5).

The markets differ in demand around a fixed fleet (claude/game-mode.md,
Part 8). For example:

    uv run python utils/game_market_search.py 215:6.5 215:9 215:11
    uv run python utils/game_market_search.py --city-size 48 --seeds 3 \
        6000:170 6000:240 6000:330
"""

import argparse
import logging
import statistics
from multiprocessing import Pool

from game_pickup_diagnostic import run

INHOMOGENEITY = 0.5
PICKUP_TIME = 1
TRIP_BLOCKS = 16


def one(job):
    city_size, cars, demand, seed = job
    return (cars, demand), run(
        city_size, cars, demand, INHOMOGENEITY, PICKUP_TIME, seed, TRIP_BLOCKS
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("cases", nargs="+", metavar="CARS:DEMAND")
    parser.add_argument("--city-size", type=int, default=32)
    parser.add_argument("--seeds", type=int, default=6)
    parser.add_argument("--first-seed", type=int, default=2)
    parser.add_argument("--workers", type=int, default=4)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)

    cases = []
    for case in args.cases:
        cars, demand = case.split(":")
        cases.append((int(cars), float(demand)))
    seeds = range(args.first_seed, args.first_seed + args.seeds)
    jobs = [(args.city_size, c, d, s) for c, d in cases for s in seeds]
    with Pool(args.workers) as pool:
        results = pool.map(one, jobs)
    print(f"city {args.city_size}, seeds {seeds.start}-{seeds.stop - 1}")
    for cars, demand in cases:
        rows = [r for key, r in results if key == (cars, demand)]
        a = {k: statistics.mean(r[k] for r in rows) for k in rows[0]}
        print(
            f"cars {cars:5} demand {demand:6g} | "
            f"P1 {a['P1']:.2f} P2 {a['P2']:.2f} P3 {a['P3']:.2f} | "
            f"pickup {a['pickup']:.1f} | gave up {a['gave_up']:.3f}",
            flush=True,
        )


if __name__ == "__main__":
    main()
