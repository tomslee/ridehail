"""
Scan game-mode bot strategies across supply/demand in the big city.

The fleet is fixed (the big city's 6000 cars) and demand varies, as the
game's markets do (ridehail/game/market.py). Each shift seats several cars
per bot strategy rather than one: the cost of a shift is simulating the
fleet, so extra seats are almost free, and averaging over them takes out
much of a single car's luck. The seats are a small fraction of the fleet
(160 of 6000 by default), so they barely change the market. The player seat
takes every offer and is left out of the results; the fleet mean is every
other car (bots and player excluded).

Each shift writes one row per strategy to a CSV as it finishes, so a long run
can be stopped and summarised from what it has (--summarise-only).

Usage:
    uv run python utils/game_environment_scan.py                # default scan
    uv run python utils/game_environment_scan.py --demand 240 --seeds 1
    uv run python utils/game_environment_scan.py --summarise-only
"""

import argparse
import csv
import json
import logging
import os
import statistics
import time
from collections import defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from ridehail.atom import TripPhase
from ridehail.game import (
    BOTS,
    MIN_FLEET_MINUTES,
    GameController,
    GameParams,
    make_game_config,
    shift_seed,
)
from ridehail.simulation import RideHailSimulation

logging.disable(logging.CRITICAL)

CITY = "big"
DEFAULT_DEMAND = "100,130,160,200,240,285,330,365,400"
FIELDS = [
    "demand",
    "seed",
    "strategy",
    "cars",
    "net_per_hour",
    "acceptance",
    "idle_min_per_trip",
    "fleet_p1",
    "fleet_p2",
    "fleet_p3",
    "give_up",
    "seconds",
]


def play_shift(demand, seed_index, cars_per_bot):
    """One big-city shift at the given demand. Returns a list of CSV rows."""
    start = time.time()
    params = GameParams()
    seed = shift_seed(f"scan-{seed_index}", "normal", CITY)
    config = make_game_config(
        "normal",
        seed,
        params.shift_blocks,
        params.warmup_blocks,
        CITY,
        params.max_wait_minutes,
    )
    config.base_demand.value = float(demand)
    sim = RideHailSimulation(config)
    game = GameController(sim, params, seed=seed, cars_per_bot=cars_per_bot)
    game.warm_up()

    cancelled = completed = 0
    while not game.shift_over:
        game.step(lambda offer: True)
        for trip in sim.trips.values():
            if trip.phase == TripPhase.CANCELLED:
                cancelled += 1
            elif trip.phase == TripPhase.COMPLETED:
                completed += 1

    fleet = [
        game.ledgers[i]
        for i in game.on_shift
        if i != game.player
        and i not in game.bots
        and sum(game.ledgers[i].minutes.values()) >= MIN_FLEET_MINUTES
    ]
    fleet_minutes = sum(sum(ledger.minutes.values()) for ledger in fleet)
    shared = {
        "demand": demand,
        "seed": seed_index,
        "fleet_p1": sum(ledger.minutes["P1"] for ledger in fleet) / fleet_minutes,
        "fleet_p2": sum(ledger.minutes["P2"] for ledger in fleet) / fleet_minutes,
        "fleet_p3": sum(ledger.minutes["P3"] for ledger in fleet) / fleet_minutes,
        "give_up": cancelled / (cancelled + completed) if cancelled + completed else 0,
        "seconds": round(time.time() - start, 1),
    }
    rows = []
    for bot in BOTS:
        ledgers = [game.ledgers[i] for i, b in game.bots.items() if b is bot]
        summaries = [ledger.summary(params) for ledger in ledgers]
        offers = sum(ledger.offers for ledger in ledgers)
        accepts = sum(ledger.accepts for ledger in ledgers)
        idle = sum(ledger.minutes["P1"] for ledger in ledgers)
        rows.append(
            {
                **shared,
                "strategy": bot.key,
                "cars": len(ledgers),
                "net_per_hour": statistics.fmean(s["net_per_hour"] for s in summaries),
                "acceptance": accepts / offers if offers else "",
                "idle_min_per_trip": idle / accepts if accepts else "",
            }
        )
    rows.append(
        {
            **shared,
            "strategy": "fleet",
            "cars": len(fleet),
            "net_per_hour": statistics.fmean(
                ledger.summary(params)["net_per_hour"] for ledger in fleet
            ),
            "acceptance": 1.0,
            "idle_min_per_trip": "",
        }
    )
    return rows


def _worker_init(niceness):
    if niceness:
        os.nice(niceness)


def mean_se(values):
    mean = statistics.fmean(values)
    se = statistics.stdev(values) / len(values) ** 0.5 if len(values) > 1 else 0.0
    return mean, se


def summarise(path):
    """Per (demand, strategy): mean and SE over shifts. Writes *_summary.csv."""
    groups = defaultdict(list)
    with open(path) as f:
        for row in csv.DictReader(f):
            groups[(float(row["demand"]), row["strategy"])].append(row)
    out_rows = []
    for (demand, strategy), rows in sorted(groups.items()):
        net_mean, net_se = mean_se([float(r["net_per_hour"]) for r in rows])

        def avg(key):
            values = [float(r[key]) for r in rows if r[key] != ""]
            return statistics.fmean(values) if values else ""

        out_rows.append(
            {
                "demand": demand,
                "strategy": strategy,
                "shifts": len(rows),
                "cars": round(statistics.fmean(float(r["cars"]) for r in rows)),
                "net_per_hour": round(net_mean, 2),
                "net_se": round(net_se, 2),
                **{
                    key: round(avg(key), 3) if avg(key) != "" else ""
                    for key in (
                        "acceptance",
                        "idle_min_per_trip",
                        "fleet_p1",
                        "fleet_p2",
                        "fleet_p3",
                        "give_up",
                        "seconds",
                    )
                },
            }
        )
    summary_path = path.with_name(path.stem + "_summary.csv")
    with open(summary_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(out_rows[0]))
        writer.writeheader()
        writer.writerows(out_rows)

    names = {bot.key: bot.name for bot in BOTS} | {"fleet": "Fleet mean"}
    for demand in sorted({r["demand"] for r in out_rows}):
        rows = [r for r in out_rows if r["demand"] == demand]
        first = rows[0]
        print(
            f"\n== demand {demand:g}/min ({first['shifts']} shifts)  "
            f"P1 {first['fleet_p1']:.2f}  P2 {first['fleet_p2']:.2f}  "
            f"P3 {first['fleet_p3']:.2f}  give up {first['give_up']:.1%}"
        )
        for r in sorted(rows, key=lambda r: -r["net_per_hour"]):
            accept = f"  accepts {r['acceptance']:.0%}" if r["acceptance"] != "" else ""
            print(
                f"   {names[r['strategy']]:<32} ${r['net_per_hour']:6.2f}/hr"
                f" ± {r['net_se']:.2f}{accept}"
            )
    print(f"\nsummary: {summary_path}")
    write_page(path, out_rows)


def write_page(path, summary_rows):
    """
    Fill utils/game_environment_scan_page.html with the summary, plus any
    notes written by hand in <out>_notes.html, as <out>.html.
    """
    template = Path(__file__).with_name("game_environment_scan_page.html")
    notes_path = path.with_name(path.stem + "_notes.html")
    notes = notes_path.read_text() if notes_path.exists() else ""
    page = template.read_text()
    page = page.replace("__DATA__", json.dumps(summary_rows))
    page = page.replace("__NOTES__", json.dumps(notes))
    page_path = path.with_suffix(".html")
    page_path.write_text(page)
    print(f"page: {page_path}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--demand", default=DEFAULT_DEMAND, help="requests/min list")
    parser.add_argument("--seeds", type=int, default=20, help="shifts per demand")
    parser.add_argument("--cars-per-bot", type=int, default=40)
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--nice", type=int, default=10, help="worker niceness")
    parser.add_argument("--out", default="out/game_environment_scan.csv")
    parser.add_argument(
        "--summarise-only", action="store_true", help="summarise an existing CSV"
    )
    args = parser.parse_args()

    path = Path(args.out)
    if not args.summarise_only:
        path.parent.mkdir(parents=True, exist_ok=True)
        done = set()
        if path.exists():
            with open(path) as f:
                done = {(float(r["demand"]), int(r["seed"])) for r in csv.DictReader(f)}
        demands = [float(d) for d in args.demand.split(",")]
        # Seeds outermost, so a partial run covers every demand evenly
        jobs = [
            (d, s) for s in range(args.seeds) for d in demands if (d, s) not in done
        ]
        print(
            f"{len(jobs)} shifts to play ({len(done)} already in {path}), "
            f"{args.workers} workers"
        )
        new_file = not path.exists()
        with open(path, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=FIELDS)
            if new_file:
                writer.writeheader()
            with ProcessPoolExecutor(
                args.workers, initializer=_worker_init, initargs=(args.nice,)
            ) as pool:
                futures = {
                    pool.submit(play_shift, d, s, args.cars_per_bot): (d, s)
                    for d, s in jobs
                }
                for n, future in enumerate(as_completed(futures), 1):
                    rows = future.result()
                    writer.writerows(rows)
                    f.flush()
                    d, s = futures[future]
                    print(
                        f"[{n}/{len(jobs)}] demand {d:g} seed {s}: "
                        f"{rows[0]['seconds']}s",
                        flush=True,
                    )
    summarise(path)


if __name__ == "__main__":
    main()
