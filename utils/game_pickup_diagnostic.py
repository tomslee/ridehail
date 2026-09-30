"""
Diagnose the game markets' time split: why pickups (P2) take so much of
drivers' time compared with the City of Toronto's 2026 data (idle ~30%,
pickup ~15% of which ~3% is waiting at the pickup, with a rider ~55%).

For each configuration it reports, over the measured blocks (after warm-up):

- P1 / P2 / P3: the fleet's time split (idle / pickup / with rider)
- stop, drive: P2 split into the pickup stop (pickup_time blocks per trip)
  and driving to the pickup
- pickup: mean dispatch distance (blocks), against ideal: the expected
  nearest-idle distance if the idle cars were spread evenly,
  sqrt(pi / (8 * density)) for the Manhattan metric, averaged over dispatches
- P2/P1: pickup time over idle time
- core req / core idle: the share of new requests, and of idle cars, in the
  downtown core (a quarter of the area)
- gave up: the share of requests cancelled after max_wait_time

Scenarios scale the market with city size: a city of size S gets
(S / 24)^2 times the cars and requests of the size-24 game, and trips keep
their length (mean_trip_distance in blocks). The simulation is the plain one
(no game controller); dispatch is recorded through Dispatch.offer_filter,
which accepts everything (byte-identical dispatch, see
test/test_dispatch_offer_filter.py).

Note: with the game's GAMMA trip distances, a destination is placed at the
drawn distance from its origin, so inhomogeneous_destinations has no effect
(only the UNIFORM distribution uses it). Inhomogeneity concentrates origins
only, and cars drain out of the core (see claude/game-mode.md, Part 5).

    uv run python utils/game_pickup_diagnostic.py
    uv run python utils/game_pickup_diagnostic.py --city-size 48 --seeds 2
"""

import argparse
import logging
import math
import statistics

from ridehail.atom import TripPhase, VehiclePhase
from ridehail.dispatch import OfferDecision
from ridehail.game import make_game_config
from ridehail.simulation import RideHailSimulation

WARMUP = 60
MEASURE = 180
BASE_CITY = 24

# City of Toronto, 2026 hourly operating data (vehicle time shares)
CITY_TARGET = "City 2026: idle 0.30, pickup 0.15 (stop ~0.03), rider 0.55; P2/P1 ~0.5"


def run(
    city_size,
    vehicles,
    demand,
    inhomogeneity,
    pickup_time,
    seed,
    trip_blocks,
):
    config = make_game_config("normal", seed, MEASURE, WARMUP)
    config.city_size.value = city_size
    config.vehicle_count.value = vehicles
    config.base_demand.value = demand
    config.inhomogeneity.value = inhomogeneity
    config.pickup_time.value = pickup_time
    config.mean_trip_distance.value = trip_blocks
    config.time_blocks.value = WARMUP + MEASURE
    sim = RideHailSimulation(config)
    sim.max_wait_time = 10
    city = sim.city
    low = int((city.city_size - city.two_zone_size) / 2.0)
    high = int((city.city_size + city.two_zone_size) / 2.0)

    def in_core(location):
        return all(low <= c < high for c in location)

    area = city_size * city_size
    stats = {"dispatch": [], "ideal": []}
    idle_now = {"n": 0}

    def record(trip, vehicle, dispatch_distance):
        if measuring["on"]:
            stats["dispatch"].append(dispatch_distance)
            if idle_now["n"] > 0:
                stats["ideal"].append(math.sqrt(math.pi / (8 * idle_now["n"] / area)))
        return OfferDecision.ACCEPT

    sim._dispatcher.offer_filter = record
    measuring = {"on": False}
    phase_counts = {"P1": 0, "P2": 0, "P3": 0}
    seen, cancelled, core_requests = set(), set(), 0
    idle_core = idle_total = 0
    for block in range(WARMUP + MEASURE):
        measuring["on"] = block >= WARMUP
        # Idle cars available to this block's dispatch
        idle_now["n"] = sum(1 for v in sim.vehicles if v.phase == VehiclePhase.P1)
        sim.next_block()
        if block < WARMUP:
            seen.update(sim.trips.keys())
            continue
        for v in sim.vehicles:
            phase_counts[v.phase.name] += 1
            if v.phase == VehiclePhase.P1:
                idle_total += 1
                idle_core += in_core(v.location)
        for index, trip in sim.trips.items():
            if index not in seen:
                seen.add(index)
                core_requests += in_core(trip.origin)
                stats.setdefault("requests", 0)
                stats["requests"] = stats.get("requests", 0) + 1
            if trip.phase == TripPhase.CANCELLED:
                cancelled.add(index)
    total = sum(phase_counts.values())
    shares = {p: phase_counts[p] / total for p in phase_counts}
    pickups = len(stats["dispatch"])
    stop = pickups * pickup_time / total
    requests = stats.get("requests", 0) or 1
    return {
        **shares,
        "stop": stop,
        "drive": shares["P2"] - stop,
        "pickup": statistics.mean(stats["dispatch"]) if pickups else float("nan"),
        "ideal": statistics.mean(stats["ideal"]) if stats["ideal"] else float("nan"),
        "core_req": core_requests / requests,
        "core_idle": idle_core / idle_total if idle_total else float("nan"),
        "gave_up": len(cancelled) / requests,
    }


def average(rows):
    return {k: statistics.mean(r[k] for r in rows) for k in rows[0]}


def main():
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--city-size", type=int, action="append")
    parser.add_argument("--seeds", type=int, default=3)
    parser.add_argument("--trip-blocks", type=int, default=12)
    args = parser.parse_args()
    logging.disable(logging.CRITICAL)

    print(CITY_TARGET)
    header = (
        f"{'city':>4} {'cars':>5} {'req':>4} {'inh':>4} {'stop':>4} | "
        f"{'P1':>5} {'P2':>5} {'P3':>5} | {'stop':>5} {'drive':>5} | "
        f"{'pickup':>6} {'ideal':>5} | {'P2/P1':>5} | {'core req':>8} {'idle':>5} | "
        f"{'gave up':>7}"
    )
    for city_size in args.city_size or [24, 48]:
        scale = (city_size / BASE_CITY) ** 2
        print(f"\n== city {city_size} (market scaled x{scale:g})")
        print(header)
        markets = [("busy", 80, 5), ("normal", 96, 5), ("slow", 130, 5)]
        cases = []
        # The current markets
        for _, cars, req in markets:
            cases.append((cars, req, 0.5, 1))
        # Normal: inhomogeneity sweep, and without the pickup stop
        for inh in (0.0, 0.25, 0.4, 0.75):
            cases.append((96, 5, inh, 1))
        cases.append((96, 5, 0.5, 0))
        # Normal at twice the density
        for inh in (0.0, 0.4):
            cases.append((192, 10, inh, 1))
        for cars, req, inh, stop in cases:
            n = round(cars * scale)
            d = req * scale
            rows = [
                run(
                    city_size,
                    n,
                    d,
                    inh,
                    stop,
                    seed,
                    args.trip_blocks,
                )
                for seed in range(1, args.seeds + 1)
            ]
            r = average(rows)
            p2p1 = r["P2"] / r["P1"] if r["P1"] > 0.005 else float("inf")
            print(
                f"{city_size:>4} {n:>5} {d:>4g} {inh:>4g} {stop:>4} | "
                f"{r['P1']:5.2f} {r['P2']:5.2f} {r['P3']:5.2f} | "
                f"{r['stop']:5.2f} {r['drive']:5.2f} | "
                f"{r['pickup']:6.1f} {r['ideal']:5.1f} | {p2p1:5.2f} | "
                f"{r['core_req']:8.2f} {r['core_idle']:5.2f} | {r['gave_up']:7.2f}",
                flush=True,
            )


if __name__ == "__main__":
    main()
