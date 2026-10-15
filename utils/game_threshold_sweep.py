"""
Sweep the price bots' $/hr threshold, and profile the offers drivers see.

Each shift seats several cars at each of a ladder of thresholds (0 = takes
every offer), in place of the game's four bots, and records the $/hr of every
offer each seat is shown ($/hr of engaged time: the offer over pickup plus
trip minutes, as the bots and the rate helper compute it). The fleet and
markets are the game's (ridehail/game/market.py).

Usage:
    uv run python utils/game_threshold_sweep.py                 # big city
    uv run python utils/game_threshold_sweep.py --city standard --demand 5,9,9.6
"""

import argparse
import csv
import logging
import os
import statistics
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass, field
from pathlib import Path

import ridehail.game.controller as controller_module
from ridehail.game import (
    MIN_FLEET_MINUTES,
    Bot,
    GameController,
    GameParams,
    make_game_config,
    shift_seed,
)
from ridehail.game.params import MINUTES_PER_HOUR
from ridehail.simulation import RideHailSimulation

logging.disable(logging.CRITICAL)

DEFAULT_THRESHOLDS = "0,15,22,27,33,40,50,60,75"


@dataclass
class ThresholdBot(Bot):
    threshold: float = 0.0
    seen: list = field(default_factory=list)

    def accepts(self, offer):
        rate = offer["per_min"] * MINUTES_PER_HOUR
        self.seen.append(rate)
        return rate >= self.threshold


def play_shift(city, demand, seed_index, thresholds, cars_per_bot):
    """One shift. Returns (rows, offers): offers maps threshold -> $/hr seen."""
    start = time.time()
    bots = [ThresholdBot(f"t{t:g}", f"${t:g}/hr", threshold=t) for t in thresholds]
    controller_module.BOTS = bots
    params = GameParams()
    seed = shift_seed(f"sweep-{seed_index}", "normal", city)
    config = make_game_config(
        "normal",
        seed,
        params.shift_blocks,
        params.warmup_blocks,
        city,
        params.max_wait_minutes,
    )
    config.base_demand.value = float(demand)
    sim = RideHailSimulation(config)
    game = GameController(sim, params, seed=seed, cars_per_bot=cars_per_bot)
    game.warm_up()
    while not game.shift_over:
        game.step(lambda offer: True)

    fleet = [
        game.ledgers[i]
        for i in game.on_shift
        if i != game.player
        and i not in game.bots
        and sum(game.ledgers[i].minutes.values()) >= MIN_FLEET_MINUTES
    ]
    fleet_minutes = sum(sum(ledger.minutes.values()) for ledger in fleet)
    shared = {
        "city": city,
        "demand": demand,
        "seed": seed_index,
        "fleet_p1": sum(ledger.minutes["P1"] for ledger in fleet) / fleet_minutes,
        "fleet_net": statistics.fmean(
            ledger.summary(params)["net_per_hour"] for ledger in fleet
        ),
        "seconds": round(time.time() - start, 1),
    }
    rows = []
    for bot in bots:
        ledgers = [game.ledgers[i] for i, b in game.bots.items() if b is bot]
        summaries = [ledger.summary(params) for ledger in ledgers]
        minutes = sum(sum(ledger.minutes.values()) for ledger in ledgers)
        rows.append(
            {
                **shared,
                "threshold": bot.threshold,
                "cars": len(ledgers),
                "net_per_hour": statistics.fmean(s["net_per_hour"] for s in summaries),
                "gross_per_hour": statistics.fmean(
                    s["earnings"] / (sum(s["minutes"].values()) / MINUTES_PER_HOUR)
                    for s in summaries
                ),
                "offers": sum(ledger.offers for ledger in ledgers),
                "accepts": sum(ledger.accepts for ledger in ledgers),
                "p1": sum(ledger.minutes["P1"] for ledger in ledgers) / minutes,
                "p2": sum(ledger.minutes["P2"] for ledger in ledgers) / minutes,
                "p3": sum(ledger.minutes["P3"] for ledger in ledgers) / minutes,
            }
        )
    return rows, {bot.threshold: bot.seen for bot in bots}


def _worker_init(niceness):
    if niceness:
        os.nice(niceness)


def quantiles(values, n=10):
    return statistics.quantiles(values, n=n, method="inclusive")


def report(rows, offers):
    by_demand = defaultdict(list)
    for row in rows:
        by_demand[row["demand"]].append(row)
    for demand in sorted(by_demand):
        group = by_demand[demand]
        shifts = len({r["seed"] for r in group})
        p1 = statistics.fmean(r["fleet_p1"] for r in group)
        fleet = statistics.fmean(r["fleet_net"] for r in group)
        print(
            f"\n== demand {demand:g} ({shifts} shifts)  fleet P1 {p1:.2f}"
            f"  fleet net ${fleet:.2f}/hr"
        )
        everything = offers[demand][0.0]
        deciles = quantiles(everything)
        print(
            f"   offers to the every-offer seats: {len(everything)}, "
            f"mean ${statistics.fmean(everything):.1f}/hr"
        )
        print("   deciles $/hr: " + " ".join(f"{q:.0f}" for q in deciles))
        print(
            "   threshold  net$/hr   ± se  gross$/hr  accept  "
            "offers/car   P1    P2    P3   below-threshold share of offers"
        )
        for threshold in sorted({r["threshold"] for r in group}):
            these = [r for r in group if r["threshold"] == threshold]
            nets = [r["net_per_hour"] for r in these]
            se = statistics.stdev(nets) / len(nets) ** 0.5 if len(nets) > 1 else 0
            offers_n = sum(r["offers"] for r in these)
            accepts = sum(r["accepts"] for r in these)
            below = sum(rate < threshold for rate in everything) / len(everything)

            def avg(key, these=these):
                return statistics.fmean(r[key] for r in these)

            print(
                f"   ${threshold:>5g}    {statistics.fmean(nets):6.2f}  {se:5.2f}"
                f"    {avg('gross_per_hour'):6.2f}   {accepts / offers_n:5.0%}"
                f"     {offers_n / sum(r['cars'] for r in these):7.1f}  {avg('p1'):.2f}  "
                f"{avg('p2'):.2f}  {avg('p3'):.2f}   {below:5.0%}"
            )


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--city", default="big", choices=["big", "standard"])
    parser.add_argument("--demand", default="130,240,265")
    parser.add_argument("--thresholds", default=DEFAULT_THRESHOLDS)
    parser.add_argument("--seeds", type=int, default=12)
    parser.add_argument("--cars-per-bot", type=int, default=30)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--nice", type=int, default=10)
    parser.add_argument("--out", default="out/game_threshold_sweep.csv")
    args = parser.parse_args()

    thresholds = [float(t) for t in args.thresholds.split(",")]
    demands = [float(d) for d in args.demand.split(",")]
    jobs = [(d, s) for s in range(args.seeds) for d in demands]
    rows = []
    offers = defaultdict(lambda: defaultdict(list))
    with ProcessPoolExecutor(
        args.workers, initializer=_worker_init, initargs=(args.nice,)
    ) as pool:
        futures = {
            pool.submit(play_shift, args.city, d, s, thresholds, args.cars_per_bot): (
                d,
                s,
            )
            for d, s in jobs
        }
        for n, future in enumerate(as_completed(futures), 1):
            shift_rows, shift_offers = future.result()
            rows.extend(shift_rows)
            d, s = futures[future]
            for threshold, seen in shift_offers.items():
                offers[d][threshold].extend(seen)
            print(
                f"[{n}/{len(jobs)}] demand {d:g} seed {s}: {shift_rows[0]['seconds']}s",
                flush=True,
            )

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    offers_path = path.with_name(path.stem + "_offers.csv")
    with open(offers_path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["demand", "threshold", "per_hour"])
        for d, by_threshold in offers.items():
            for threshold, seen in by_threshold.items():
                writer.writerows([d, threshold, round(rate, 2)] for rate in seen)
    report(rows, offers)
    print(f"\nrows: {path}\noffers: {offers_path}")


if __name__ == "__main__":
    main()
