"""
Search for good driver strategies in game mode (ridehail/game.py).

The player's choice is an accept/decline decision on each offer, which makes
this an average-reward problem whose optimal policy is (close to) a threshold:

    accept if  paid_offer + delta * (dropoff_in_core - now_in_core)
                   >= lam * time_used

- lam is the value of the driver's time in $/minute: the best achievable
  earnings rate. The "Hourly Thinker" bot is this rule with lam = 0.55.
- delta is how much more it is worth to become idle in the core than in the
  outskirts, in $.
- With --horizon (the "horizon" variant below), paid_offer and time_used are
  cut at the end of the shift: earnings accrue per minute of riding, so a
  trip that runs past the end pays pro rata, and time after the end is free.

Running costs are left out of the rule: idle cars keep cruising
(idle_vehicles_moving = 1), so the player drives one block (0.37 km) every minute
whatever they decide and the cost is not affected by the decision.

The script runs in two stages for each market:

1. sweep: play the threshold rule for a grid of lam values (delta = 0, no
   horizon) over the same set of shift codes, so every lam faces the same
   cities and riders (common random numbers). Picks the best lam.
2. refine (one step of policy iteration): play the best lam on separate
   shift codes and estimate delta from what happened after each drop-off
   (net earnings over the next --window minutes, core vs outskirts). Then
   compare, on held-out codes and paired by code:
       base     best lam
       horizon  best lam + end-of-shift cut
       zone     best lam + end-of-shift cut + estimated delta

Outputs go to --out (default out/game_strategy/):
    shifts.csv   one row per shift: stage, policy, player and bot net $/hr
    offers.csv   every offer the player saw, the decision, and (for accepted
                 offers) the drop-off time and net earnings in the window
                 after it: the raw material for fitting other rules
    sweep.png    net $/hr against lam, per market (needs matplotlib)
    summary.txt  the printed summary

Usage:
    uv run python utils/game_strategy.py                    # everything
    uv run python utils/game_strategy.py --market busy --seeds 40
    uv run python utils/game_strategy.py --lam-max 0.8 --lam-step 0.1
    uv run python utils/game_strategy.py --skip-refine
    uv run python utils/game_strategy.py --difficulty pro   # acceptance rule on
"""

import argparse
import csv
import logging
import multiprocessing
import os
import statistics
import sys
import time
from pathlib import Path

from ridehail.atom import VehiclePhase
from ridehail.game import BOTS, MARKETS, create_game

logging.disable(logging.CRITICAL)

OFFER_FIELDS = [
    "market",
    "stage",
    "policy",
    "lam",
    "delta",
    "horizon",
    "code",
    "block",
    "offer",
    "rate_card",
    "pickup_minutes",
    "trip_minutes",
    "per_min",
    "vehicle_zone",
    "dropoff_zone",
    "vehicle_x",
    "vehicle_y",
    "pickup_x",
    "pickup_y",
    "dropoff_x",
    "dropoff_y",
    "decision",
    "idle_block",
    "window_net",
]


# ----------------------------------------------------------------------
# The policy
# ----------------------------------------------------------------------


def threshold_decider(game, lam, delta=0.0, horizon=False):
    shift_blocks = game.params.shift_blocks

    def decide(offer):
        pickup = offer["pickup_minutes"]
        trip = offer["trip_minutes"]
        paid = offer["offer"]
        used = pickup + trip
        remaining = shift_blocks - offer["block"]
        if horizon:
            paid_minutes = min(max(remaining - pickup, 0.0), trip)
            paid = paid * paid_minutes / trip if trip else 0.0
            used = min(used, remaining)
        bonus = 0.0
        # A zone is worth something only if there is shift left to use it
        if delta and pickup + trip < remaining:
            now_core = game.zone(offer["vehicle_location"]) == "core"
            drop_core = offer["dropoff_zone"] == "core"
            bonus = delta * (drop_core - now_core)
        return paid + bonus >= lam * used

    return decide


# ----------------------------------------------------------------------
# One shift (runs in a worker process)
# ----------------------------------------------------------------------


def play_shift(task):
    """Play one shift; return (shift row, offer rows)."""
    market = task["market"]
    code = task["code"]
    sim, game = create_game(market, code, difficulty=task["difficulty"])
    decide = threshold_decider(game, task["lam"], task["delta"], task["horizon"])
    ops_cost = game.params.ops_cost_per_km
    player = game.ledgers[game.player]
    vehicle = sim.vehicles[game.player]
    # net[t]: player's net earnings after t blocks of the shift
    net = [0.0]
    phases = []
    while not game.shift_over:
        game.step(decide)
        net.append(player.earnings - player.km * ops_cost)
        phases.append(vehicle.phase)
    results = game.results()

    window = task["window"]
    offers = []
    for entry in results["offer_log"]:
        row = {
            "market": market,
            "stage": task["stage"],
            "policy": task["policy"],
            "lam": task["lam"],
            "delta": task["delta"],
            "horizon": int(task["horizon"]),
            "code": code,
            "block": entry["block"],
            "offer": entry["offer"],
            "rate_card": entry["rate_card"],
            "pickup_minutes": entry["pickup_minutes"],
            "trip_minutes": entry["trip_minutes"],
            "per_min": entry["per_min"],
            "vehicle_zone": game.zone(entry["vehicle_location"]),
            "dropoff_zone": entry["dropoff_zone"],
            "vehicle_x": entry["vehicle_location"][0],
            "vehicle_y": entry["vehicle_location"][1],
            "pickup_x": entry["pickup"][0],
            "pickup_y": entry["pickup"][1],
            "dropoff_x": entry["dropoff"][0],
            "dropoff_y": entry["dropoff"][1],
            "decision": entry["decision"],
            "idle_block": "",
            "window_net": "",
        }
        if entry["decision"] == "accept":
            # The offer is answered after block `block`; the player is idle
            # again at the first later block that ends in P1 (the drop-off).
            idle = next(
                (
                    t
                    for t in range(entry["block"] + 1, len(phases))
                    if phases[t] == VehiclePhase.P1
                ),
                None,
            )
            if idle is not None:
                row["idle_block"] = idle
                # net index t+1 is the state after the block phases[t]
                start = idle + 1
                if start + window < len(net):
                    row["window_net"] = round(net[start + window] - net[start], 2)
        offers.append(row)

    shift = {
        "market": market,
        "stage": task["stage"],
        "policy": task["policy"],
        "lam": task["lam"],
        "delta": task["delta"],
        "horizon": int(task["horizon"]),
        "code": code,
        "player_net_per_hour": results["player"]["net_per_hour"],
        "player_offers": results["player"]["offers"],
        "player_accepts": results["player"]["accepts"],
        "fleet_mean_net_per_hour": results["fleet_mean_net_per_hour"],
    }
    for bot in results["bots"]:
        shift[f"bot_{bot['key']}"] = bot["net_per_hour"]
    return shift, offers


def init_worker():
    logging.disable(logging.CRITICAL)


# ----------------------------------------------------------------------
# Running batches and summarising
# ----------------------------------------------------------------------


class Runner:
    def __init__(self, args, out_dir):
        self.args = args
        self.pool = multiprocessing.Pool(args.workers, initializer=init_worker)
        out_dir.mkdir(parents=True, exist_ok=True)
        self.shift_file = open(out_dir / "shifts.csv", "w", newline="")
        self.offer_file = open(out_dir / "offers.csv", "w", newline="")
        self.shift_writer = None
        self.offer_writer = csv.DictWriter(self.offer_file, OFFER_FIELDS)
        self.offer_writer.writeheader()

    def run(self, tasks, label):
        start = time.time()
        shifts, offers = [], []
        for i, (shift, rows) in enumerate(
            self.pool.imap_unordered(play_shift, tasks, chunksize=4), 1
        ):
            shifts.append(shift)
            offers.extend(rows)
            if self.shift_writer is None:
                self.shift_writer = csv.DictWriter(self.shift_file, list(shift))
                self.shift_writer.writeheader()
            self.shift_writer.writerow(shift)
            self.offer_writer.writerows(rows)
            if i % 50 == 0 or i == len(tasks):
                print(
                    f"\r   {label}: {i}/{len(tasks)} shifts, {time.time() - start:.0f}s",
                    end="",
                    file=sys.stderr,
                    flush=True,
                )
        print(file=sys.stderr)
        self.shift_file.flush()
        self.offer_file.flush()
        return shifts, offers

    def close(self):
        self.pool.close()
        self.pool.join()
        self.shift_file.close()
        self.offer_file.close()


def make_tasks(args, market, stage, policy, lam, delta=0.0, horizon=False, seeds=None):
    return [
        {
            "market": market,
            "stage": stage,
            "policy": policy,
            "lam": lam,
            "delta": delta,
            "horizon": horizon,
            "code": f"{stage}-{i}",
            "difficulty": args.difficulty,
            "window": args.window,
        }
        for i in range(seeds or args.seeds)
    ]


def mean_se(values):
    values = list(values)
    mean = statistics.fmean(values)
    se = statistics.stdev(values) / len(values) ** 0.5 if len(values) > 1 else 0.0
    return mean, se


def lam_grid(args):
    count = int(round((args.lam_max - args.lam_min) / args.lam_step)) + 1
    return [round(args.lam_min + i * args.lam_step, 4) for i in range(count)]


def sweep(runner, args, market, say):
    tasks = []
    for lam in lam_grid(args):
        tasks += make_tasks(args, market, "sweep", "threshold", lam)
    shifts, _ = runner.run(tasks, f"{market} sweep")
    by_lam = {}
    for row in shifts:
        by_lam.setdefault(row["lam"], []).append(row)
    table = []
    for lam in sorted(by_lam):
        rows = by_lam[lam]
        mean, se = mean_se(r["player_net_per_hour"] for r in rows)
        accepts = sum(r["player_accepts"] for r in rows)
        offers = sum(r["player_offers"] for r in rows)
        table.append((lam, mean, se, accepts / offers if offers else 0.0))
    best = max(table, key=lambda r: r[1])
    # Paired check: the best lam against its neighbours on the same codes
    say(f"\n   sweep ({args.seeds} codes per lam; lam in $/min, net in $/hr)")
    say("      lam    net/hr    ±se   accepts")
    for lam, mean, se, rate in table:
        mark = "  <- best" if lam == best[0] else ""
        say(f"     {lam:5.2f}   {mean:6.2f}   {se:4.2f}   {rate:5.0%}{mark}")
    references = {}
    for key in [f"bot_{b.key}" for b in BOTS] + ["fleet_mean_net_per_hour"]:
        references[key] = mean_se(r[key] for r in shifts)
    say(
        "   references (mean over all sweep shifts): "
        + ", ".join(f"{bot.name} {references[f'bot_{bot.key}'][0]:.2f}" for bot in BOTS)
        + f", fleet {references['fleet_mean_net_per_hour'][0]:.2f}"
    )
    return best[0], table, references


def estimate_delta(offers, window, say):
    """Net earnings in the window after becoming idle: core minus outskirts."""
    values = {"core": [], "outskirts": []}
    for row in offers:
        if row["window_net"] != "":
            values[row["dropoff_zone"]].append(row["window_net"])
    if min(len(v) for v in values.values()) < 2:
        say("   too few drop-offs to estimate delta; using 0")
        return 0.0
    core, core_se = mean_se(values["core"])
    out, out_se = mean_se(values["outskirts"])
    delta = core - out
    se = (core_se**2 + out_se**2) ** 0.5
    say(
        f"   net in the {window} min after drop-off: core ${core:.2f}"
        f" (n={len(values['core'])}), outskirts ${out:.2f}"
        f" (n={len(values['outskirts'])})  ->  delta = ${delta:.2f} ± {se:.2f}"
    )
    return round(delta, 2)


def refine(runner, args, market, lam, say):
    say(f"\n   refine at lam = {lam:.2f}")
    _, offers = runner.run(
        make_tasks(args, market, "estimate", "base", lam, seeds=args.refine_seeds),
        f"{market} estimate",
    )
    delta = estimate_delta(offers, args.window, say)
    variants = {
        "base": (0.0, False),
        "horizon": (0.0, True),
        "zone": (delta, True),
    }
    tasks = []
    for policy, (d, h) in variants.items():
        tasks += make_tasks(
            args, market, "refine", policy, lam, d, h, args.refine_seeds
        )
    shifts, _ = runner.run(tasks, f"{market} refine")
    by_code = {}
    for row in shifts:
        by_code.setdefault(row["code"], {})[row["policy"]] = row["player_net_per_hour"]
    say(f"   held-out comparison ({args.refine_seeds} codes, paired by code)")
    for policy in variants:
        mean, se = mean_se(r[policy] for r in by_code.values())
        line = f"     {policy:<8} net ${mean:6.2f}/hr ± {se:4.2f}"
        if policy != "base":
            diff, diff_se = mean_se(r[policy] - r["base"] for r in by_code.values())
            line += f"   vs base {diff:+5.2f} ± {diff_se:4.2f}"
        say(line)
    return delta


def plot(results, path):
    try:
        import matplotlib

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        return False
    colours = {"busy": "#ed6495", "normal": "#6495ed", "slow": "#3cb371"}
    fig, ax = plt.subplots(figsize=(8, 5))
    for market, (table, references) in results.items():
        lams = [r[0] for r in table]
        means = [r[1] for r in table]
        lows = [r[1] - r[2] for r in table]
        highs = [r[1] + r[2] for r in table]
        colour = colours.get(market)
        ax.plot(lams, means, marker="o", color=colour, label=MARKETS[market]["label"])
        ax.fill_between(lams, lows, highs, color=colour, alpha=0.2)
        ax.axhline(
            references["fleet_mean_net_per_hour"][0],
            color=colour,
            linestyle=":",
            linewidth=1,
        )
    ax.set_xlabel("threshold lam ($ per minute of pickup + trip)")
    ax.set_ylabel("player net $/hr (± 1 se)")
    ax.set_title("Threshold strategy by market (dotted: fleet mean)")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(path, dpi=120)
    return True


def main():
    parser = argparse.ArgumentParser(
        description=__doc__.split("\n\n")[0],
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--market", choices=list(MARKETS), action="append")
    parser.add_argument("--seeds", type=int, default=100, help="codes per lam")
    parser.add_argument(
        "--refine-seeds", type=int, default=200, help="codes per refine policy"
    )
    parser.add_argument("--lam-min", type=float, default=0.0)
    parser.add_argument("--lam-max", type=float, default=1.0)
    parser.add_argument("--lam-step", type=float, default=0.05)
    parser.add_argument(
        "--window", type=int, default=30, help="minutes after drop-off, for delta"
    )
    parser.add_argument("--difficulty", default="rookie", choices=["rookie", "pro"])
    parser.add_argument("--skip-refine", action="store_true")
    parser.add_argument("--workers", type=int, default=os.cpu_count())
    parser.add_argument("--out", default="out/game_strategy")
    args = parser.parse_args()

    out_dir = Path(args.out)
    runner = Runner(args, out_dir)
    lines = []

    def say(text=""):
        print(text)
        lines.append(text)

    say(
        f"difficulty {args.difficulty}; lam {args.lam_min}..{args.lam_max} step "
        f"{args.lam_step}; {args.workers} workers"
    )
    plotted = {}
    try:
        for market in args.market or list(MARKETS):
            say(
                f"\n== {MARKETS[market]['label']} "
                f"({MARKETS[market]['vehicle_count']} vehicles)"
            )
            best, table, references = sweep(runner, args, market, say)
            plotted[market] = (table, references)
            if not args.skip_refine:
                refine(runner, args, market, best, say)
    finally:
        runner.close()
    (out_dir / "summary.txt").write_text("\n".join(lines) + "\n")
    if plotted and plot(plotted, out_dir / "sweep.png"):
        say(f"\nplot: {out_dir / 'sweep.png'}")
    print(f"data: {out_dir}/shifts.csv, {out_dir}/offers.csv, summary.txt")


if __name__ == "__main__":
    main()
