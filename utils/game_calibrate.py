"""
Calibrate game mode (ridehail/game.py) by playing many headless shifts.

Each shift seats the four bots, so one shift measures every strategy; the
player seat plays a chosen strategy too (accept-all by default). Averaging
over seeds takes out the luck of a single shift. The design target
(claude/game-mode.md 1.6) is that the strategy ranking flips between markets:
picky bots win when Busy, Yes-to-Everything wins when Slow.

Usage:
    uv run python utils/game_calibrate.py                 # 40 seeds, all markets
    uv run python utils/game_calibrate.py --seeds 100 --market busy
    uv run python utils/game_calibrate.py --set multiplier_sigma=0.35 \
        --demand busy=12,slow=6
"""

import argparse
import logging
import statistics
import time

from ridehail import game as game_module
from ridehail.game import BOTS, GameParams, MARKETS, create_game

logging.disable(logging.CRITICAL)


def mean_se(values):
    mean = statistics.fmean(values)
    se = statistics.stdev(values) / len(values) ** 0.5 if len(values) > 1 else 0.0
    return mean, se


def run_market(market, seeds, params_overrides, player_rule):
    rows = {bot.name: [] for bot in BOTS}
    acceptance = {bot.name: [] for bot in BOTS}
    rows["Player"] = []
    rows["Fleet mean"] = []
    phases = {"P1": [], "P2": [], "P3": []}
    idle_per_offer = []
    offers_per_shift = []
    player_bot = next(b for b in BOTS if b.key == player_rule)
    for seed in range(seeds):
        params = GameParams(**params_overrides)
        sim, game = create_game(market, f"calibrate-{seed}", params=params)
        while not game.shift_over:
            game.step(player_bot.accepts)
        results = game.results()
        rows["Player"].append(results["player"]["net_per_hour"])
        rows["Fleet mean"].append(results["fleet_mean_net_per_hour"])
        for bot in results["bots"]:
            rows[bot["name"]].append(bot["net_per_hour"])
            if bot["acceptance_rate"] is not None:
                acceptance[bot["name"]].append(bot["acceptance_rate"])
        minutes = sum(game.ledgers[0].minutes.values())
        for phase in phases:
            phases[phase].append(
                statistics.fmean(ledger.minutes[phase] for ledger in game.ledgers)
                / minutes
            )
        yes_index = next(i for i, b in game.bots.items() if b.key == "yes")
        yes = game.ledgers[yes_index]
        if yes.offers:
            idle_per_offer.append(yes.minutes["P1"] / yes.offers)
        offers_per_shift.append(results["player"]["offers"])
    return rows, acceptance, phases, idle_per_offer, offers_per_shift


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--seeds", type=int, default=40)
    parser.add_argument("--market", choices=list(MARKETS), action="append")
    parser.add_argument(
        "--player",
        default="yes",
        choices=[b.key for b in BOTS],
        help="strategy for the player seat",
    )
    parser.add_argument(
        "--set",
        action="append",
        default=[],
        metavar="PARAM=VALUE",
        help="override a GameParams field, e.g. multiplier_sigma=0.35",
    )
    parser.add_argument(
        "--demand",
        default="",
        metavar="MARKET=D,...",
        help="override demand (requests per minute), e.g. busy=12,slow=6",
    )
    parser.add_argument(
        "--shared",
        default="",
        metavar="KEY=VALUE,...",
        help="override MARKET_SHARED, e.g. vehicle_count=250,city_size=20",
    )
    args = parser.parse_args()

    overrides = {}
    for item in args.set:
        key, value = item.split("=")
        overrides[key] = type(getattr(GameParams(), key))(float(value))
    for item in filter(None, args.demand.split(",")):
        market, demand = item.split("=")
        MARKETS[market]["base_demand"] = float(demand)
    for item in filter(None, args.shared.split(",")):
        key, value = item.split("=")
        current = game_module.MARKET_SHARED[key]
        game_module.MARKET_SHARED[key] = type(current)(float(value))

    print(f"shared: {game_module.MARKET_SHARED}  overrides: {overrides}")
    for market in args.market or list(MARKETS):
        start = time.time()
        rows, acceptance, phases, idle, offers = run_market(
            market, args.seeds, overrides, args.player
        )
        print(
            f"\n== {MARKETS[market]['label']} ({MARKETS[market]['base_demand']:g} "
            f"requests/min, {args.seeds} seeds, {time.time() - start:.0f}s)"
        )
        print(
            "   fleet phases: "
            + "  ".join(f"{p} {statistics.fmean(v):.2f}" for p, v in phases.items())
        )
        print(
            f"   Yes bot idle minutes per offer: {statistics.fmean(idle):.1f}"
            f" (90th pct {sorted(idle)[int(0.9 * len(idle))]:.1f})"
            f";  player offers per shift: {statistics.fmean(offers):.1f}"
        )
        ranked = sorted(rows.items(), key=lambda kv: -statistics.fmean(kv[1]))
        for name, values in ranked:
            mean, se = mean_se(values)
            rate = acceptance.get(name)
            rate_text = f"  accepts {statistics.fmean(rate):.0%}" if rate else ""
            print(f"   {name:<20} net ${mean:6.2f}/hr ± {se:4.2f}{rate_text}")


if __name__ == "__main__":
    main()
