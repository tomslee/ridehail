#!/usr/bin/env python3
"""
Benchmark the DEFAULT dispatch search (ridehail/dispatch.py).

Each trip is matched to an idle vehicle by one of two searches, chosen per
trip by Dispatch._use_sparse_search:

  sparse  loop over the idle vehicles still in the pool (~ m per trip)
  dense   ring-search outward from the trip origin (~ city_size^2 / m)

This script times the real dispatcher on identical states with the choice
left to the rule ("default", optionally at several SPARSE_SEARCH_FACTOR
values) or forced to one search for the whole block ("sparse", "dense"). The
best of the two forced runs ("block-best") is the best a once-per-block rule
could do. Background: claude/dispatch-changeover-criterion.md.

Subcommands
  list        registered scenarios
  synthetic   uniform random states over a grid of city size x P1 x load
  capture     run scenarios, saving every dispatch state to a pickle
  replay      time strategies on saved states
  scenarios   capture + replay in one go
  simulate    end-to-end simulation time and the share spent in dispatch

Examples (from the repository root)
  uv run python benchmarks/bench_dispatch.py synthetic --quick
  uv run python benchmarks/bench_dispatch.py scenarios game-big-busy --factors 1 1.5
  uv run python benchmarks/bench_dispatch.py capture -o benchmarks/results/s.pkl
  uv run python benchmarks/bench_dispatch.py replay benchmarks/results/s.pkl
  uv run python benchmarks/bench_dispatch.py simulate my_city.config

Timing noise between runs on one machine is about 10%; treat smaller
differences as noise, and compare strategies within a run.
"""

import argparse
import json
import random
import sys
import time
from collections import defaultdict
from contextlib import contextmanager
from pathlib import Path

from harness import (
    RESULTS_DIR,
    SCENARIOS,
    DispatchState,
    environment,
    load_states,
    resolve_scenarios,
    run_scenario,
    save_states,
    uniform_state,
)

from ridehail.atom import City, VehiclePhase
from ridehail.dispatch import Dispatch

DEFAULT_STATES = RESULTS_DIR / "dispatch_states.pkl"


# ---------------------------------------------------------------------------
# Strategies
# ---------------------------------------------------------------------------


@contextmanager
def strategy(name, factor=None):
    """Patch Dispatch for one strategy: "default" (the rule, at `factor` if
    given), "sparse" or "dense" (forced for every trip)."""
    saved_rule = Dispatch.__dict__["_use_sparse_search"]
    saved_factor = Dispatch.SPARSE_SEARCH_FACTOR
    if name in ("sparse", "dense"):
        forced = name == "sparse"
        Dispatch._use_sparse_search = classmethod(lambda cls, m, c: forced)
    elif name != "default":
        raise ValueError(name)
    if factor is not None:
        Dispatch.SPARSE_SEARCH_FACTOR = factor
    try:
        yield
    finally:
        Dispatch._use_sparse_search = saved_rule
        Dispatch.SPARSE_SEARCH_FACTOR = saved_factor


def time_state(state, repeats, seed=0):
    """Best-of-repeats seconds for one dispatch call on fresh stubs, under the
    currently patched strategy. Also returns the number of vehicles assigned."""
    city = City(state.city_size)
    best, assigned = float("inf"), 0
    for _ in range(repeats):
        vehicles, trips = state.materialize()
        dispatcher = Dispatch()
        random.seed(seed)
        start = time.perf_counter()
        dispatcher._dispatch_vehicles_default(trips, city, vehicles)
        best = min(best, time.perf_counter() - start)
        assigned = sum(1 for v in vehicles if v.phase == VehiclePhase.P2)
    return best, assigned


def strategy_columns(factors):
    """Column names: default@factor for each factor, then sparse, dense."""
    return [f"default@{f:g}" for f in factors] + ["sparse", "dense"]


def time_strategies(state, factors, repeats):
    """{column: seconds} for one state, plus "block-best"."""
    times = {}
    for f in factors:
        with strategy("default", f):
            times[f"default@{f:g}"] = time_state(state, repeats)[0]
    for name in ("sparse", "dense"):
        with strategy(name):
            times[name] = time_state(state, repeats)[0]
    times["block-best"] = min(times["sparse"], times["dense"])
    return times


def auto_repeats(state, repeats):
    # Large states are slow and their timings stable: one repeat is enough
    return 1 if state.p1 * state.trips > 300_000 else repeats


# ---------------------------------------------------------------------------
# Subcommands
# ---------------------------------------------------------------------------


def cmd_list(args):
    for scenario in SCENARIOS.values():
        print(f"{scenario.name:22} {scenario.description}")


LOADS = {"0.1": 0.1, "0.5": 0.5, "1": 1.0, "4": 4.0}


def cmd_synthetic(args):
    if args.quick:
        city_sizes, p1s = [32, 64], [8, 16, 32, 64, 128, 256, 512]
    else:
        city_sizes = args.city_sizes
        p1s = [
            2, 4, 8, 16, 24, 32, 48, 64, 96, 128, 192, 256, 384,
            512, 768, 1024, 1536, 2048, 3072,
        ]  # fmt: skip
    columns = strategy_columns(args.factors)
    rows = []
    print(f"# synthetic uniform states; {environment()}")
    print("# load = unassigned trips / P1; times in ms")
    header = f"{'C':>4} {'P1':>5} {'trips':>6} " + " ".join(
        f"{c:>12}" for c in columns + ["block-best"]
    )
    print(header)
    for load in args.loads:
        for city_size in city_sizes:
            for p1 in p1s:
                if p1 > min(args.max_p1, 2 * city_size**2):
                    continue
                trips = max(1, round(load * p1))
                if trips > args.max_trips:
                    continue
                state = uniform_state(city_size, p1, trips)
                times = time_strategies(
                    state, args.factors, auto_repeats(state, args.repeats)
                )
                rows.append(dict(C=city_size, P1=p1, trips=trips, load=load, **times))
                print(
                    f"{city_size:4} {p1:5} {trips:6} "
                    + " ".join(f"{times[c] * 1e3:12.2f}" for c in columns)
                    + f" {times['block-best'] * 1e3:12.2f}",
                    flush=True,
                )
    print("\n# Block-level crossover: first P1 at which forced dense beats sparse")
    for load in args.loads:
        for city_size in city_sizes:
            first = next(
                (
                    r["P1"]
                    for r in rows
                    if r["load"] == load
                    and r["C"] == city_size
                    and r["dense"] < r["sparse"]
                ),
                None,
            )
            print(f"load {load:<4g} C={city_size:<4} crossover P1={first}")
    print("\n# Totals by load (ms); worst = largest ratio to block-best")
    for load in args.loads:
        selected = [r for r in rows if r["load"] == load]
        print(f"load {load:<4g}", end="")
        for c in columns + ["block-best"]:
            total = sum(r[c] for r in selected) * 1e3
            measurable = [r for r in selected if r["block-best"] > 5e-4]
            worst = max((r[c] / r["block-best"] for r in measurable), default=1)
            print(f"  {c} {total:.0f} ({worst:.1f}x)", end="")
        print()
    write_json(args, dict(kind="synthetic", rows=rows))


def capture(scenarios):
    """Run each scenario, recording every DEFAULT dispatch call's state."""
    states = []
    original = Dispatch._dispatch_vehicles_default
    label, block = None, 0

    def recording(self, unassigned_trips, city, vehicles):
        nonlocal block
        locations = [
            tuple(v.location)
            for v in vehicles
            if v.phase == VehiclePhase.P1 and v.index not in self.offline
        ]
        origins = [tuple(t.origin) for t in unassigned_trips]
        start = time.perf_counter()
        result = original(self, unassigned_trips, city, vehicles)
        states.append(
            DispatchState(
                label,
                city.city_size,
                locations,
                origins,
                time.perf_counter() - start,
                block,
            )
        )
        block += 1
        return result

    Dispatch._dispatch_vehicles_default = recording
    try:
        for scenario in scenarios:
            label, block = scenario.name, 0
            seconds = run_scenario(scenario)
            mine = [s for s in states if s.label == scenario.name]
            dispatch = sum(s.measured for s in mine)
            print(
                f"captured {scenario.name:22} {len(mine):5} dispatch calls; "
                f"simulation {seconds:6.2f}s, of which dispatch {dispatch:6.2f}s",
                flush=True,
            )
    finally:
        Dispatch._dispatch_vehicles_default = original
    return states


def cmd_capture(args):
    states = capture(resolve_scenarios(args.scenarios))
    save_states(states, args.output)
    print(f"saved {len(states)} states to {args.output}")


def replay(states, args):
    states = [s for s in states if s.trip_origins][:: args.every]
    columns = strategy_columns(args.factors) + ["block-best"]
    totals = defaultdict(lambda: defaultdict(float))
    counts = defaultdict(int)
    rows = []
    for state in states:
        times = time_strategies(state, args.factors, auto_repeats(state, args.repeats))
        rows.append(
            dict(label=state.label, block=state.block, C=state.city_size,
                 P1=state.p1, trips=state.trips, **times)
        )  # fmt: skip
        counts[state.label] += 1
        for c in columns:
            totals[state.label][c] += times[c]
    print(f"\n# replayed dispatch states (every {args.every}); {environment()}")
    print("# total ms over the replayed calls")
    print(f"{'scenario':22} {'calls':>5} " + " ".join(f"{c:>12}" for c in columns))
    for label, total in totals.items():
        print(
            f"{label:22} {counts[label]:5} "
            + " ".join(f"{total[c] * 1e3:12.1f}" for c in columns)
        )
    write_json(args, dict(kind="replay", rows=rows))


def cmd_replay(args):
    replay(load_states(args.states), args)


def cmd_scenarios(args):
    replay(capture(resolve_scenarios(args.scenarios)), args)


def cmd_simulate(args):
    original = Dispatch.dispatch_vehicles
    spent = 0.0

    def timed(self, *a):
        nonlocal spent
        start = time.perf_counter()
        result = original(self, *a)
        spent += time.perf_counter() - start
        return result

    Dispatch.dispatch_vehicles = timed
    rows = []
    print(f"# end-to-end simulation; {environment()}")
    try:
        for scenario in resolve_scenarios(args.scenarios):
            spent = 0.0
            seconds = run_scenario(scenario)
            rows.append(dict(scenario=scenario.name, seconds=seconds, dispatch=spent))
            print(
                f"{scenario.name:22} {seconds:7.2f}s  dispatch {spent:7.2f}s "
                f"({spent / seconds:4.0%})",
                flush=True,
            )
    finally:
        Dispatch.dispatch_vehicles = original
    write_json(args, dict(kind="simulate", rows=rows))


def write_json(args, payload):
    if getattr(args, "json", None):
        payload["environment"] = environment()
        payload["argv"] = sys.argv[1:]
        Path(args.json).parent.mkdir(parents=True, exist_ok=True)
        with open(args.json, "w") as f:
            json.dump(payload, f, indent=1)
        print(f"wrote {args.json}")


# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)

    def timing_options(p):
        p.add_argument(
            "--factors", type=float, nargs="+",
            default=[Dispatch.SPARSE_SEARCH_FACTOR],
            help="SPARSE_SEARCH_FACTOR values to time the default rule at "
            "(default: the current value)",
        )  # fmt: skip
        p.add_argument("--repeats", type=int, default=3, help="best of N")
        p.add_argument("--json", help="also write results to this JSON file")

    sub.add_parser("list", help="registered scenarios").set_defaults(func=cmd_list)

    p = sub.add_parser("synthetic", help="uniform random states")
    timing_options(p)
    p.add_argument("--city-sizes", type=int, nargs="+", default=[16, 32, 48, 64, 96])
    p.add_argument(
        "--loads", type=float, nargs="+", default=[0.1, 0.5, 1.0, 4.0],
        help="unassigned trips per idle vehicle",
    )  # fmt: skip
    p.add_argument("--max-p1", type=int, default=3072)
    p.add_argument("--max-trips", type=int, default=6000)
    p.add_argument("--quick", action="store_true", help="a small grid (~1 min)")
    p.set_defaults(func=cmd_synthetic)

    p = sub.add_parser("capture", help="save dispatch states from scenarios")
    p.add_argument("scenarios", nargs="*", help="names or .config paths (default all)")
    p.add_argument("-o", "--output", default=str(DEFAULT_STATES))
    p.set_defaults(func=cmd_capture)

    p = sub.add_parser("replay", help="time strategies on saved states")
    p.add_argument("states", nargs="?", default=str(DEFAULT_STATES))
    p.add_argument("--every", type=int, default=1, help="replay every Nth state")
    timing_options(p)
    p.set_defaults(func=cmd_replay)

    p = sub.add_parser("scenarios", help="capture and replay")
    p.add_argument("scenarios", nargs="*", help="names or .config paths (default all)")
    p.add_argument("--every", type=int, default=1, help="replay every Nth state")
    timing_options(p)
    p.set_defaults(func=cmd_scenarios)

    p = sub.add_parser("simulate", help="end-to-end time and dispatch share")
    p.add_argument("scenarios", nargs="*", help="names or .config paths (default all)")
    p.add_argument("--json", help="also write results to this JSON file")
    p.set_defaults(func=cmd_simulate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
