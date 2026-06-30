#!/usr/bin/env python3
"""
Standalone micro-benchmark for the trip->vehicle assignment search in
ridehail/dispatch.py.

It isolates the *search* cost of the two strategies used inside
`_dispatch_vehicles_default`:

  - sparse: loop over P1 vehicles, keep nearest (early-terminate at dist 1)
  - dense : build a city_size x city_size grid, ring-search outward per trip

and a proposed variant:

  - dense_dict: same ring search but the location grid is a dict keyed by
    occupied (x, y) only, so build is O(P1) instead of O(city_size^2).

We use lightweight stub Vehicle/Trip objects so we measure the search itself,
not the full phase-update machinery. The search reads only:
  vehicle.location, vehicle.direction, vehicle.phase, vehicle.index
  trip.origin
and mutates the candidate containers exactly as the real code does.

No Textual / no full simulation, so this is safe to run in any console.
"""

import random
import time
import statistics

from ridehail.atom import Direction, VehiclePhase
from ridehail.atom import City


# --- Stubs -----------------------------------------------------------------

class StubVehicle:
    __slots__ = ("index", "location", "direction", "phase")

    def __init__(self, index, location):
        self.index = index
        self.location = location
        self.direction = random.choice(list(Direction))
        self.phase = VehiclePhase.P1

    def update_phase(self, trip=None, to_phase=None):
        # The real method changes phase to P2 and records the trip; for the
        # search benchmark we only need it to not be P1 any more.
        self.phase = VehiclePhase.P2


class StubTrip:
    __slots__ = ("origin",)

    def __init__(self, origin):
        self.origin = origin

    def update_phase(self, to_phase=None):
        pass


# --- Scenario construction -------------------------------------------------

def build_scenario(city_size, p1_count, trip_count, seed):
    """Return (city, vehicles_by_index, p1_list, trips)."""
    rng = random.Random(seed)
    city = City(city_size)
    vehicles = []
    for i in range(p1_count):
        loc = [rng.randint(0, city_size - 1), rng.randint(0, city_size - 1)]
        vehicles.append(StubVehicle(i, loc))
    trips = []
    for _ in range(trip_count):
        origin = [rng.randint(0, city_size - 1), rng.randint(0, city_size - 1)]
        trips.append(StubTrip(origin))
    return city, vehicles, trips


# --- The three search strategies (lifted from dispatch.py) -----------------

def run_sparse(city, p1_list, trips):
    veh_list = list(p1_list)
    for trip in trips:
        if not veh_list:
            break
        current_minimum = city.city_size * 100
        dispatch_vehicle = None
        for vehicle in veh_list:
            d = city.dispatch_distance(
                location_from=vehicle.location,
                current_direction=vehicle.direction,
                location_to=trip.origin,
                vehicle_phase=vehicle.phase,
                threshold=current_minimum,
            )
            if 0 < d < current_minimum:
                current_minimum = d
                dispatch_vehicle = vehicle
            if d == 1:
                break
        if dispatch_vehicle:
            veh_list.remove(dispatch_vehicle)


def _build_dense_grid(city, p1_list):
    import numpy as np
    cs = city.city_size
    grid = np.empty(shape=(cs, cs), dtype=object)
    for i in range(cs):
        for j in range(cs):
            grid[i][j] = []
    for v in p1_list:
        grid[v.location[0]][v.location[1]].append(v.index)
    return grid


def run_dense(city, p1_list, trips, vehicles_by_index):
    cs = city.city_size
    grid = _build_dense_grid(city, p1_list)
    veh_set = set(p1_list)
    for trip in trips:
        if not veh_set:
            break
        current_minimum = cs * 100
        candidates = []
        for distance in range(0, cs):
            for x_offset in range(-distance, distance + 1):
                y_offset = distance - abs(x_offset)
                x = (trip.origin[0] + x_offset) % cs
                y_lower = (trip.origin[1] - y_offset) % cs
                y_upper = (trip.origin[1] + y_offset) % cs
                for y in set([y_lower, y_upper]):
                    for vehicle_index in grid[x][y]:
                        vehicle = vehicles_by_index[vehicle_index]
                        if vehicle not in veh_set:
                            continue
                        d = city.dispatch_distance(
                            location_from=vehicle.location,
                            current_direction=vehicle.direction,
                            location_to=trip.origin,
                            vehicle_phase=vehicle.phase,
                        )
                        if 0 < d < current_minimum:
                            current_minimum = d
                            candidates = []
                        if 0 < d <= current_minimum:
                            candidates.append(vehicle_index)
            if current_minimum <= distance and candidates:
                break
        if candidates:
            chosen = vehicles_by_index[random.choice(candidates)]
            veh_set.discard(chosen)
            grid[chosen.location[0]][chosen.location[1]].remove(chosen.index)


def run_dense_dict(city, p1_list, trips, vehicles_by_index):
    """Proposed variant: dict-of-lists grid, O(P1) build, no cs^2 allocation."""
    cs = city.city_size
    grid = {}
    for v in p1_list:
        grid.setdefault((v.location[0], v.location[1]), []).append(v.index)
    veh_set = set(p1_list)
    for trip in trips:
        if not veh_set:
            break
        ox, oy = trip.origin[0], trip.origin[1]
        current_minimum = cs * 100
        candidates = []
        for distance in range(0, cs):
            for x_offset in range(-distance, distance + 1):
                y_offset = distance - abs(x_offset)
                x = (ox + x_offset) % cs
                # set() matches the shipped dense path: dedup + fixed order so
                # dispatch outcomes are identical to the pre-dict-grid code.
                for y in set([(oy - y_offset) % cs, (oy + y_offset) % cs]):
                    cell = grid.get((x, y))
                    if not cell:
                        continue
                    for vehicle_index in cell:
                        vehicle = vehicles_by_index[vehicle_index]
                        if vehicle not in veh_set:
                            continue
                        d = city.dispatch_distance(
                            location_from=vehicle.location,
                            current_direction=vehicle.direction,
                            location_to=trip.origin,
                            vehicle_phase=vehicle.phase,
                        )
                        if 0 < d < current_minimum:
                            current_minimum = d
                            candidates = []
                        if 0 < d <= current_minimum:
                            candidates.append(vehicle_index)
            if current_minimum <= distance and candidates:
                break
        if candidates:
            chosen = vehicles_by_index[random.choice(candidates)]
            veh_set.discard(chosen)
            cell = grid.get((chosen.location[0], chosen.location[1]))
            if cell:
                cell.remove(chosen.index)


# --- Timing harness --------------------------------------------------------

def time_strategy(fn, city, p1_list, trips, vehicles_by_index, needs_index,
                  repeats):
    times = []
    for r in range(repeats):
        # fresh copies because each run mutates the candidate containers
        p1_copy = list(p1_list)
        for v in p1_copy:
            v.phase = VehiclePhase.P1
        t0 = time.perf_counter()
        if needs_index:
            fn(city, p1_copy, trips, vehicles_by_index)
        else:
            fn(city, p1_copy, trips)
        times.append(time.perf_counter() - t0)
    return min(times)  # min = least noisy estimate of pure compute


def current_model_choice(city_size, p1_count, trip_count, factor=0.5):
    sparse_cost = trip_count * p1_count
    dense_cost = city_size ** 2 * factor
    return "sparse" if sparse_cost <= dense_cost else "dense"


def proposed_model_choice(city_size, p1_count, trip_count):
    """
    Compare the two *dominant per-trip* cost terms, assuming the dict-grid
    dense build (O(P1), negligible vs the searches):

      sparse total ~ trips * P1
      dense  total ~ P1 (build) + trips * cs^2 / P1   (ring search to nearest)

    Choose sparse when its total is smaller. The trips factor nearly cancels,
    so this reduces to roughly P1 < city_size, but we keep the full form so the
    build term still tips very-low-trip blocks toward dense.
    """
    if p1_count <= 0:
        return "sparse"
    sparse_cost = trip_count * p1_count
    dense_cost = p1_count + trip_count * (city_size ** 2) / p1_count
    return "sparse" if sparse_cost <= dense_cost else "dense"


def main():
    random.seed(0)
    repeats = 5

    # Parameter grid spanning sparse..dense regimes.
    city_sizes = [16, 32, 48, 64, 100]
    # express P1 as a fraction of city_size so we sweep across the crossover
    p1_per_row = [0.25, 0.5, 1.0, 2.0, 4.0, 8.0]
    trip_fracs = [0.25, 1.0]  # trips as fraction of P1 count

    header = (
        f"{'cs':>4} {'P1':>6} {'trips':>6} {'P1/cs':>6} "
        f"{'sparse_ms':>10} {'dense_ms':>10} {'ddict_ms':>10} "
        f"{'fastest':>8} {'curr_pick':>9} {'curr_ok':>7}"
    )
    print(header)
    print("-" * len(header))

    rows = []
    for cs in city_sizes:
        for ppr in p1_per_row:
            p1 = max(1, int(ppr * cs))
            for tf in trip_fracs:
                trips_n = max(1, int(tf * p1))
                city, vehicles, trips = build_scenario(cs, p1, trips_n, seed=cs * 7 + p1)
                vbi = vehicles  # index == position in list

                t_sparse = time_strategy(run_sparse, city, vehicles, trips, vbi,
                                         needs_index=False, repeats=repeats)
                t_dense = time_strategy(run_dense, city, vehicles, trips, vbi,
                                        needs_index=True, repeats=repeats)
                t_ddict = time_strategy(run_dense_dict, city, vehicles, trips, vbi,
                                        needs_index=True, repeats=repeats)

                best = min(
                    [("sparse", t_sparse), ("dense", t_dense), ("ddict", t_ddict)],
                    key=lambda kv: kv[1],
                )[0]
                # Which of the two CURRENT strategies is actually faster:
                actual_best_current = "sparse" if t_sparse <= t_dense else "dense"
                curr_pick = current_model_choice(cs, p1, trips_n)
                curr_ok = "ok" if curr_pick == actual_best_current else "MISS"

                print(
                    f"{cs:>4} {p1:>6} {trips_n:>6} {ppr:>6.2f} "
                    f"{t_sparse*1000:>10.3f} {t_dense*1000:>10.3f} {t_ddict*1000:>10.3f} "
                    f"{best:>8} {curr_pick:>9} {curr_ok:>7}"
                )
                rows.append((cs, p1, trips_n, t_sparse, t_dense, t_ddict,
                             curr_pick, actual_best_current))

    # Summary: how often does the current model mis-pick between the two
    # current strategies, and how much does it cost when it does?
    misses = [r for r in rows if r[6] != r[7]]
    print()
    print(f"Current model mispicks (sparse vs dense): {len(misses)}/{len(rows)}")
    for cs, p1, tn, ts, td, tdd, pick, best in misses:
        chosen_t = ts if pick == "sparse" else td
        best_t = min(ts, td)
        ratio = chosen_t / best_t if best_t else 1.0
        print(f"  cs={cs:>3} P1={p1:>5} trips={tn:>5}: model picked {pick:>6}, "
              f"best {best:>6}, {ratio:.1f}x slower than necessary")

    # How much does the dict grid help dense?
    print()
    speedups = [td / tdd for (_, _, _, _, td, tdd, _, _) in rows if tdd > 0]
    print(f"dense -> dense_dict speedup: median {statistics.median(speedups):.2f}x, "
          f"max {max(speedups):.2f}x")

    # Bottom line: total wall time if we always followed each decision rule,
    # given we ALSO adopt the dict grid (so "dense" == dense_dict cost).
    print()
    print("End-to-end total time by decision rule (dense uses dict grid):")
    oracle = curr = prop = 0.0
    prop_miss = 0
    for cs, p1, tn, ts, td, tdd, _, _ in rows:
        # cost of each strategy with dict grid as the dense implementation
        cost = {"sparse": ts, "dense": tdd}
        oracle += min(cost.values())
        curr += cost[current_model_choice(cs, p1, tn)]
        pchoice = proposed_model_choice(cs, p1, tn)
        prop += cost[pchoice]
        if cost[pchoice] > 1.01 * min(cost.values()):
            prop_miss += 1
    print(f"  oracle (always best):        {oracle*1000:8.2f} ms")
    print(f"  current model  (T*P1 vs cs^2): {curr*1000:8.2f} ms  "
          f"({curr/oracle:.2f}x oracle)")
    print(f"  proposed model (per-trip):     {prop*1000:8.2f} ms  "
          f"({prop/oracle:.2f}x oracle), mispicks={prop_miss}/{len(rows)}")
    print("  simple rule P1 < cs:           "
          + format(
              sum(min(ts, tdd) if (p1 < cs) == (ts <= tdd) else max(ts, tdd)
                  for cs, p1, tn, ts, td, tdd, _, _ in rows) * 1000,
              "8.2f") + " ms")


if __name__ == "__main__":
    main()
