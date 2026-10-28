"""
Memory growth in long simulations: does what a run holds keep growing?

Each scenario advances one kind of long-running work a step at a time (a
simulation block, a pair of web lab map frames, or a whole short simulation)
and samples memory as it goes:

- traced: bytes held by Python objects (tracemalloc), the leak signal. It
  does not include memory the allocator keeps after objects are freed.
- rss: the process's resident set size, what the system sees. It moves in
  steps and rarely shrinks, so read it alongside traced.
- objects: the number of objects the cycle collector tracks.

After a warm-up (the simulation's buffers fill, the fleet settles), the
traced memory should stay flat. The slope of a least-squares line through
the samples, in bytes per step, says how fast it grows, and the sites that
grew most between the first and last samples say where.

    uv run python benchmarks/bench_memory.py list
    uv run python benchmarks/bench_memory.py run                  # all, quick
    uv run python benchmarks/bench_memory.py run city lab-map --steps 20000
    uv run python benchmarks/bench_memory.py run toronto --no-trace --steps 5000

Samples are taken just after the simulation drops finished trips (every
GARBAGE_COLLECTION_INTERVAL blocks), so the per-block churn of trips does not
show as a sawtooth. tracemalloc slows Python by about 2x; --no-trace measures
RSS only, for very long runs.

The web lab's browser side (Pyodide's WebAssembly heap and the JS proxies)
is measured by bench_memory_pyodide.mjs, which drives worker.py through the
same calls as webworker.js.
"""

import argparse
import gc
import json
import logging
import os
import sys
import time
import tracemalloc
from dataclasses import dataclass, field

from harness import REPO_ROOT, RESULTS_DIR, environment

from ridehail.simulation import GARBAGE_COLLECTION_INTERVAL

LAB_DIR = REPO_ROOT / "docs" / "lab"
PAGE_SIZE = os.sysconf("SC_PAGE_SIZE")


def rss_bytes():
    with open("/proc/self/statm") as f:
        return int(f.read().split()[1]) * PAGE_SIZE


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


def make_config(preset=None, **values):
    """A validated config from an optional preset plus overrides (as in
    test/test_strategy.py), run open-ended (time_blocks 0) unless given."""
    from ridehail.config import RideHailConfig
    from ridehail.presets import get_preset

    values.setdefault("time_blocks", 0)
    config = RideHailConfig(use_config_file=False)
    config.animation.value = "none"
    for name, value in {**(get_preset(preset) if preset else {}), **values}.items():
        item = getattr(config, name)
        item.value = value
        item.explicitly_set = True
    config._convert_config_values_to_enum()
    config._set_parameter_defaults()
    config._validate_all_config_parameters()
    return config


@dataclass
class Scenario:
    name: str
    description: str
    # Returns step(): advance one step. Called once per measurement.
    make_stepper: object = field(repr=False)
    # Blocks per step, to report growth per block
    blocks_per_step: int = 1
    # Default number of steps and warm-up steps
    steps: int = 5000
    warmup: int = 1000


def sim_stepper(preset=None, **values):
    def make():
        from ridehail.simulation import RideHailSimulation

        sim = RideHailSimulation(make_config(preset, **values))
        return sim.next_block

    return make


def jsonl_stepper(preset, **values):
    """Write the per-block JSONL record, as a long command-line run with an
    output file does (the file goes to the null device)."""

    def make():
        from ridehail.simulation import RideHailSimulation

        sim = RideHailSimulation(make_config(preset, **values))
        sim.jsonl_file = os.devnull
        handle = open(os.devnull, "w")

        def step():
            sim.next_block(jsonl_file_handle=handle)

        return step

    return make


def lab_settings(**overrides):
    """Web lab settings, as js/sim-settings.js sends them (a Town-like run)."""
    settings = {
        "citySize": 24,
        "vehicleCount": 120,
        "requestRate": 5.0,
        "meanTripDistance": 12,
        "minTripDistance": 0,
        "inhomogeneity": 0.5,
        "inhomogeneousDestinations": False,
        "idleVehiclesMoving": 1.0,
        "randomNumberSeed": 7,
        "verbosity": 0,
        "equilibration": "none",
        "equilibrationInterval": 5,
        "demandElasticity": 0.0,
        "useCostsAndIncomes": False,
        "meanVehicleSpeed": 30.0,
        "minutesPerBlock": 1.0,
        "reservationWage": 0.35,
        "platformCommission": 0.25,
        "price": 1.2,
        "perKmPrice": 0.8,
        "perMinutePrice": 0.18,
        "baseFare": 3.0,
        "perKmOpsCost": 0.3,
        "perHourOpportunityCost": 6.0,
        "timeBlocks": 0,
        "smoothingWindow": 20,
        "animationDelay": 0,
        "pickupTime": 1,
    }
    settings.update(overrides)
    return settings


class Proxy:
    """Stands in for the Pyodide JsProxy of the settings (worker.py calls
    .to_py() on it)."""

    def __init__(self, values):
        self.values = values

    def to_py(self):
        return dict(self.values)


def import_worker():
    if str(LAB_DIR) not in sys.path:
        sys.path.insert(0, str(LAB_DIR))
    # In the browser sys.argv is empty; RideHailConfig() would otherwise read
    # this script's arguments as a config file name
    saved = sys.argv
    sys.argv = ["worker.py"]
    try:
        import worker
    finally:
        sys.argv = saved
    return worker


def lab_stepper(method, follow=False, **overrides):
    """worker.py's frame calls, one block per step (two map frames when the
    city is small enough to interpolate)."""

    def make():
        worker = import_worker()
        saved = sys.argv
        sys.argv = ["worker.py"]
        try:
            w = worker.init_simulation(Proxy(lab_settings(**overrides)))
        finally:
            sys.argv = saved
        if follow:
            w.follow_vehicle("random")
        call = getattr(w, method)
        frames = 2 if method == "next_frame_map" and w.interpolate_frames else 1

        def step():
            for _ in range(frames):
                call()

        return step

    return make


def lab_reset_stepper(blocks=50):
    """Reset and replay in the lab: a new worker Simulation each step, as the
    Reset button does, run for a few blocks. Anything a simulation leaves
    behind when it is replaced shows as growth per step."""

    def make():
        worker = import_worker()
        sys.argv = ["worker.py"]

        def step():
            w = worker.init_simulation(Proxy(lab_settings()))
            for _ in range(blocks):
                w.next_frame_map()

        return step

    return make


def repeated_sims_stepper(blocks=100):
    """Many short simulations in one process, as a sequence run does. Each
    simulation is discarded before the next."""

    def make():
        from ridehail.simulation import RideHailSimulation

        def step():
            sim = RideHailSimulation(make_config("town", time_blocks=blocks))
            sim.simulate()

        return step

    return make


def sequence_stepper():
    """One whole sequence run (several simulations), through RideHailSimulationSequence."""

    def make():
        from ridehail.sequence import RideHailSimulationSequence

        config = make_config(
            "village",
            time_blocks=100,
            run_sequence=True,
            vehicle_count=4,
            vehicle_count_increment=4,
            vehicle_count_max=8,
            request_rate_values=[0.4, 0.6],
        )

        def step():
            RideHailSimulationSequence(config).run_sequence(config)

        return step

    return make


SCENARIOS = {
    s.name: s
    for s in [
        Scenario("village", "village preset, open-ended", sim_stepper("village")),
        Scenario("town", "town preset, open-ended", sim_stepper("town")),
        Scenario(
            "city",
            "city preset (48 blocks, 1200 cars), open-ended",
            sim_stepper("city"),
            steps=3000,
            warmup=500,
        ),
        Scenario(
            "city-price",
            "city preset, costs and incomes, price equilibration (fleet churn)",
            sim_stepper("city", use_city_scale=True, equilibration="price"),
            steps=3000,
            warmup=1000,
        ),
        Scenario(
            "toronto",
            "toronto-2026 preset (48 blocks, 5757 cars, 173 trips/block)",
            sim_stepper("toronto-2026"),
            steps=1000,
            warmup=300,
        ),
        Scenario(
            "strategy",
            "game preset, open-ended: one seated car playing rate:30",
            sim_stepper("game", strategy_offer="rate:30"),
        ),
        Scenario(
            "jsonl",
            "town preset, writing the per-block JSONL record",
            jsonl_stepper("town"),
        ),
        Scenario(
            "lab-map",
            "web lab worker.py map frames, Town settings, open-ended",
            lab_stepper("next_frame_map"),
        ),
        Scenario(
            "lab-map-follow",
            "lab-map, following a car",
            lab_stepper("next_frame_map", follow=True),
        ),
        Scenario(
            "lab-map-price",
            "lab map frames, costs and incomes, price equilibration",
            lab_stepper(
                "next_frame_map", useCostsAndIncomes=True, equilibration="price"
            ),
            warmup=1500,
        ),
        Scenario(
            "lab-stats",
            "web lab worker.py stats frames, Town settings",
            lab_stepper("next_block_stats"),
        ),
        Scenario(
            "lab-reset",
            "web lab Reset: a new simulation every 50 blocks",
            lab_reset_stepper(),
            blocks_per_step=50,
            steps=200,
            warmup=20,
        ),
        Scenario(
            "repeated-sims",
            "100-block town simulations, one after another",
            repeated_sims_stepper(),
            blocks_per_step=100,
            steps=200,
            warmup=20,
        ),
        Scenario(
            "sequence",
            "a 4-simulation village sequence, again and again",
            sequence_stepper(),
            blocks_per_step=400,
            steps=60,
            warmup=10,
        ),
    ]
}


# ---------------------------------------------------------------------------
# Measurement
# ---------------------------------------------------------------------------


def slope(xs, ys):
    """Least-squares slope of ys on xs."""
    n = len(xs)
    mean_x, mean_y = sum(xs) / n, sum(ys) / n
    sxx = sum((x - mean_x) ** 2 for x in xs)
    sxy = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys))
    return sxy / sxx if sxx else 0.0


def measure(scenario, steps, warmup, samples, trace, top):
    """Run the scenario; returns a result dict."""
    if trace:
        tracemalloc.start(1)
    step = scenario.make_stepper()
    start = time.perf_counter()
    for _ in range(warmup):
        step()
    # Sample right after the trip garbage collection, so the trip dict is at
    # the bottom of its sawtooth. Steps of whole simulations need no phase.
    phase = 0
    if scenario.blocks_per_step == 1:
        # Garbage collection runs in the block whose index is a multiple of
        # the interval, so sample when block_index is one past that
        phase = (1 - warmup) % GARBAGE_COLLECTION_INTERVAL
        for _ in range(phase):
            step()
    every = max(1, steps // samples)
    if scenario.blocks_per_step == 1:
        every = max(
            GARBAGE_COLLECTION_INTERVAL,
            every // GARBAGE_COLLECTION_INTERVAL * GARBAGE_COLLECTION_INTERVAL,
        )
    rows = []
    first_snapshot = None
    done = 0
    while True:
        gc.collect()
        traced = tracemalloc.get_traced_memory()[0] if trace else None
        rows.append(
            {
                "step": done,
                "traced": traced,
                "rss": rss_bytes(),
                "objects": len(gc.get_objects()),
            }
        )
        if trace and first_snapshot is None:
            first_snapshot = tracemalloc.take_snapshot()
        if done >= steps:
            break
        for _ in range(every):
            step()
        done += every
    elapsed = time.perf_counter() - start
    growth = []
    if trace:
        last_snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()
        filters = [
            tracemalloc.Filter(False, tracemalloc.__file__),
            tracemalloc.Filter(False, "<frozen importlib._bootstrap*>"),
        ]
        diff = last_snapshot.filter_traces(filters).compare_to(
            first_snapshot.filter_traces(filters), "lineno"
        )
        for stat in diff[:top]:
            if stat.size_diff <= 0:
                continue
            frame = stat.traceback[0]
            growth.append(
                {
                    "site": f"{os.path.relpath(frame.filename, REPO_ROOT)}:{frame.lineno}",
                    "size_diff": stat.size_diff,
                    "count_diff": stat.count_diff,
                }
            )
    steps_x = [r["step"] for r in rows]
    blocks = scenario.blocks_per_step
    result = {
        "scenario": scenario.name,
        "description": scenario.description,
        "warmup_steps": warmup + phase,
        "steps": done,
        "blocks_per_step": blocks,
        "seconds": elapsed,
        "samples": rows,
        "rss_slope_per_block": slope(steps_x, [r["rss"] for r in rows]) / blocks,
        "objects_slope_per_block": slope(steps_x, [r["objects"] for r in rows])
        / blocks,
        "growth_sites": growth,
    }
    if trace:
        result["traced_slope_per_block"] = (
            slope(steps_x, [r["traced"] for r in rows]) / blocks
        )
    return result


def mib(n):
    return n / (1024 * 1024)


# Growth this fast would add 10 MB per million blocks
GROWING_BYTES_PER_BLOCK = 10.0
# Fitted growth over the run below this is noise (allocator and cache churn)
NOISE_BYTES = 64 * 1024


def residual_sd(xs, ys):
    """Standard deviation of ys about their least-squares line on xs."""
    n = len(xs)
    b = slope(xs, ys)
    a = sum(ys) / n - b * sum(xs) / n
    return (sum((y - a - b * x) ** 2 for x, y in zip(xs, ys)) / max(n - 2, 1)) ** 0.5


def verdict(result):
    """GROWING if the fitted traced growth (RSS when not traced) is faster
    than GROWING_BYTES_PER_BLOCK and, over the measured span, more than both
    NOISE_BYTES and four times the samples' scatter about the line (the trip
    population and the completion history wander from block to block)."""
    key = "traced" if "traced_slope_per_block" in result else "rss"
    per_block = result[f"{key}_slope_per_block"]
    fitted = per_block * result["steps"] * result["blocks_per_step"]
    rows = result["samples"]
    scatter = residual_sd([r["step"] for r in rows], [r[key] for r in rows])
    if per_block > GROWING_BYTES_PER_BLOCK and fitted > max(NOISE_BYTES, 4 * scatter):
        return "GROWING"
    return "flat"


def report(result):
    rows = result["samples"]
    traced = "traced_slope_per_block" in result
    blocks = result["steps"] * result["blocks_per_step"]
    print(
        f"\n== {result['scenario']}: {result['description']}\n"
        f"   {result['warmup_steps']} warm-up + {result['steps']} measured steps "
        f"({blocks} blocks), {result['seconds']:.0f} s"
    )
    print(f"   {'step':>8} {'traced MiB':>11} {'RSS MiB':>9} {'objects':>10}")
    shown = rows if len(rows) <= 12 else rows[:: max(1, len(rows) // 10)] + [rows[-1]]
    seen = set()
    for r in shown:
        if r["step"] in seen:
            continue
        seen.add(r["step"])
        t = f"{mib(r['traced']):11.2f}" if traced else f"{'-':>11}"
        print(f"   {r['step']:>8} {t} {mib(r['rss']):9.1f} {r['objects']:>10}")
    parts = []
    if traced:
        per = result["traced_slope_per_block"]
        parts.append(f"traced {per:+.1f} B/block ({per:+.0f} MB per million blocks)")
    per = result["rss_slope_per_block"]
    parts.append(f"RSS {per:+.1f} B/block")
    parts.append(f"objects {result['objects_slope_per_block']:+.3f}/block")
    print("   slope: " + ", ".join(parts))
    print(f"   verdict: {verdict(result)}")
    if result["growth_sites"]:
        print("   largest growth between first and last sample:")
        for g in result["growth_sites"]:
            print(
                f"     {g['size_diff'] / 1024:+9.1f} KiB {g['count_diff']:+8d} blocks  "
                f"{g['site']}"
            )


def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("list", help="registered scenarios")
    run = sub.add_parser("run", help="measure scenarios")
    run.add_argument("scenarios", nargs="*", help="scenario names (default: all)")
    run.add_argument("--steps", type=int, help="measured steps (default: per scenario)")
    run.add_argument("--warmup", type=int, help="warm-up steps (default: per scenario)")
    run.add_argument(
        "--scale",
        type=float,
        default=1.0,
        help="multiply each scenario's default steps and warm-up",
    )
    run.add_argument("--samples", type=int, default=20, help="number of samples")
    run.add_argument("--top", type=int, default=8, help="growth sites to show")
    run.add_argument(
        "--no-trace",
        action="store_true",
        help="RSS and object counts only (no tracemalloc; faster)",
    )
    run.add_argument("--json", help="save the results to this path")
    args = parser.parse_args()

    if args.command == "list":
        for s in SCENARIOS.values():
            print(f"{s.name:<16} {s.description}")
        return
    logging.disable(logging.CRITICAL)
    names = args.scenarios or list(SCENARIOS)
    unknown = [n for n in names if n not in SCENARIOS]
    if unknown:
        raise SystemExit(
            f"Unknown scenario(s) {unknown}. Registered: {list(SCENARIOS)}"
        )
    print(environment())
    results = []
    for name in names:
        s = SCENARIOS[name]
        steps = args.steps or max(1, int(s.steps * args.scale))
        warmup = args.warmup if args.warmup is not None else int(s.warmup * args.scale)
        result = measure(s, steps, warmup, args.samples, not args.no_trace, args.top)
        report(result)
        results.append(result)
    print("\nsummary:")
    for r in results:
        per = r.get("traced_slope_per_block", r["rss_slope_per_block"])
        print(f"   {r['scenario']:<16} {verdict(r):<8} {per:+9.1f} B/block")
    if args.json:
        RESULTS_DIR.mkdir(exist_ok=True)
        with open(args.json, "w") as f:
            json.dump({"environment": environment(), "results": results}, f, indent=1)


if __name__ == "__main__":
    main()
