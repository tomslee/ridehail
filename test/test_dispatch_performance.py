"""
Performance regression tests for the dispatch search-strategy selection.

WHAT THIS VALIDATES
===================
The trip->vehicle assignment in ``ridehail/dispatch.py`` (DEFAULT dispatch)
uses one of two searches for each trip:

  * sparse (vehicle-loop)  -- per trip ~ m, the idle vehicles remaining
  * dense  (location-ring) -- per trip ~ city_size^2 / m, after an O(P1)
                              grid build once per block

``Dispatch._use_sparse_search(m, city_size)`` picks sparse once
m <= SPARSE_SEARCH_FACTOR * city_size. The choice is made per trip, so a block
that starts dense switches to sparse as its idle pool drains.

History. The original rule (``trips * P1  vs  0.5 * city_size^2``) chose
dense under a large backlog with almost no idle vehicles, ring-searching a
near-empty grid thousands of times per block (June 2026 fix). The June rule
("sparse when P1 < city_size", decided once per block from the initial P1)
still ignored the drain: when trips >= P1, a dense block paid whole-city scans
to find the last few vehicles. claude/dispatch-changeover-criterion.md has the
measurements, and benchmarks/bench_dispatch.py reproduces them.

WHY THIS DOES NOT ASSERT WALL-CLOCK TIME
========================================
Timing depends too much on the machine and its load to be a reliable gate
(use benchmarks/ for that). These tests pin down the algorithmic decisions:

Part A (fast, runs by default)
    The threshold function itself, and a drained block driven through the
    real dispatcher on stub vehicles: dense only while the pool is above the
    threshold, then sparse, switching once; no work once the pool is empty;
    every assignment is a nearest remaining vehicle.

Part B (marked ``regression``, slower)
    Drives the ``test/perf/perf_*.config`` scenarios through animation-free
    simulations, records the pool size at every per-trip search, and checks
    that no dense search ever runs on a pool at or below the threshold.
"""

import random
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest

from ridehail.atom import City, Direction, VehiclePhase
from ridehail.dispatch import Dispatch


PERF_CONFIG_DIR = Path(__file__).parent / "perf"

# A backlog this large, with the supply in perf_boundary.config (P1 <= 110 in a
# 64x64 city), is squarely in the regime that once chose dense wrongly.
LARGE_BACKLOG = 300


# ---------------------------------------------------------------------------
# Recording the per-trip search choice
# ---------------------------------------------------------------------------


@contextmanager
def _record_searches():
    """Record (method, pool size, trip) for each per-trip search call.

    The pool size is the number of idle vehicles left *before* the call.
    """
    calls = []
    original_dense = Dispatch._dispatch_vehicle_dense
    original_sparse = Dispatch._dispatch_vehicle_sparse

    def dense(self, trip, city, vehicles_at_location, pool):
        calls.append(("dense", len(pool), trip))
        return original_dense(self, trip, city, vehicles_at_location, pool)

    def sparse(self, trip, city, pool):
        calls.append(("sparse", len(pool), trip))
        return original_sparse(self, trip, city, pool)

    Dispatch._dispatch_vehicle_dense = dense
    Dispatch._dispatch_vehicle_sparse = sparse
    try:
        yield calls
    finally:
        Dispatch._dispatch_vehicle_dense = original_dense
        Dispatch._dispatch_vehicle_sparse = original_sparse


# ---------------------------------------------------------------------------
# Part A: the threshold and a drained block (fast; run by default)
# ---------------------------------------------------------------------------


class _StubVehicle:
    """Just what the DEFAULT dispatch search reads and changes."""

    def __init__(self, index, location):
        self.index = index
        self.location = location
        self.direction = Direction.NORTH
        self.phase = VehiclePhase.P1
        self.trip = None

    def update_phase(self, trip=None, to_phase=None):
        self.phase = VehiclePhase.P2
        self.trip = trip


class _StubTrip:
    def __init__(self, origin):
        self.origin = origin

    def update_phase(self, to_phase=None):
        pass


def _stub_block(city_size, p1, trips, seed=3):
    rng = random.Random(seed)

    def point():
        return [rng.randrange(city_size), rng.randrange(city_size)]

    vehicles = [_StubVehicle(i, point()) for i in range(p1)]
    return City(city_size), vehicles, [_StubTrip(point()) for _ in range(trips)]


class TestSparseSearchThreshold:
    """Pin the per-trip threshold implemented by _use_sparse_search."""

    @pytest.mark.parametrize("city_size", [16, 32, 48, 64, 100])
    def test_threshold_is_factor_times_city_size(self, city_size):
        threshold = Dispatch.SPARSE_SEARCH_FACTOR * city_size
        choices = [
            Dispatch._use_sparse_search(m, city_size)
            for m in range(0, 8 * city_size + 1)
        ]
        # Sparse up to the threshold, dense above it: one flip, no flip back
        assert all(choices[m] for m in range(0, int(threshold) + 1))
        assert not any(choices[m] for m in range(int(threshold) + 1, len(choices)))

    def test_factor_is_in_measured_flat_optimum(self):
        # claude/dispatch-changeover-criterion.md: totals are flat for 1.0-1.5
        assert 1.0 <= Dispatch.SPARSE_SEARCH_FACTOR <= 1.5

    @pytest.mark.parametrize(
        "p1, city_size",
        [(3, 64), (20, 64), (30, 100), (10, 48)],
    )
    def test_small_pool_is_sparse_whatever_the_backlog(self, p1, city_size):
        """The original June 2026 bug: tiny pool + huge backlog chose dense.

        The decision no longer takes the backlog at all, so a small pool is
        sparse however many trips are waiting.
        """
        assert Dispatch._use_sparse_search(p1, city_size) is True


class TestDrainedBlock:
    """A block whose backlog exceeds its idle pool, through the real code."""

    CITY_SIZE = 20
    P1 = 70  # well above the threshold, so the block starts dense
    TRIPS = 150  # more trips than vehicles, so the pool drains to zero

    def _run(self):
        city, vehicles, trips = _stub_block(self.CITY_SIZE, self.P1, self.TRIPS)
        random.seed(1)
        with _record_searches() as calls:
            Dispatch()._dispatch_vehicles_default(trips, city, vehicles)
        return city, vehicles, trips, calls

    def test_dense_then_sparse_switching_once(self):
        _, _, _, calls = self._run()
        threshold = Dispatch.SPARSE_SEARCH_FACTOR * self.CITY_SIZE
        methods = [method for method, _, _ in calls]
        switch = methods.index("sparse")
        assert switch > 0, "the block should start dense"
        assert set(methods[:switch]) == {"dense"}
        assert set(methods[switch:]) == {"sparse"}, "no switch back to dense"
        assert all(pool > threshold for method, pool, _ in calls if method == "dense")
        assert all(pool <= threshold for method, pool, _ in calls if method == "sparse")

    def test_stops_once_pool_is_empty(self):
        _, vehicles, _, calls = self._run()
        assert all(v.phase == VehiclePhase.P2 for v in vehicles), (
            "every idle vehicle should be dispatched in a drained block"
        )
        # No search runs on an empty pool: one call per vehicle, not per trip
        assert all(pool > 0 for _, pool, _ in calls)
        assert len(calls) == self.P1 < self.TRIPS

    def test_each_assignment_is_a_nearest_remaining_vehicle(self):
        city, vehicles, trips, _ = self._run()
        # Replay the assignments in trip order against the shrinking pool.
        # (A vehicle at the origin itself has distance 0 and is never a
        # candidate, as in the dispatcher.)
        remaining = set(vehicles)
        assigned = {id(v.trip): v for v in vehicles if v.trip is not None}
        for trip in trips:
            vehicle = assigned.get(id(trip))
            if vehicle is None:
                continue
            distances = [
                city.distance(v.location, trip.origin)
                for v in remaining
                if v.location != trip.origin
            ]
            assert city.distance(vehicle.location, trip.origin) == min(distances)
            remaining.discard(vehicle)

    def test_small_pool_never_builds_grid(self, monkeypatch):
        city, vehicles, trips = _stub_block(64, 30, 500)

        def fail(_):
            raise AssertionError("grid built for a pool below the threshold")

        monkeypatch.setattr(Dispatch, "_build_location_grid", staticmethod(fail))
        with _record_searches() as calls:
            Dispatch()._dispatch_vehicles_default(trips, city, vehicles)
        assert {method for method, _, _ in calls} == {"sparse"}


# ---------------------------------------------------------------------------
# Part B: per-trip choices in real simulations of the perf_*.config scenarios
# (slow; grouped with the other regression tests and run with -m regression)
# ---------------------------------------------------------------------------


@contextmanager
def _patched_argv(args):
    saved = sys.argv
    sys.argv = args
    try:
        yield
    finally:
        sys.argv = saved


def _record_simulation(config_path):
    """Run the config through an animation-free simulation. Returns
    (calls, blocks): the per-trip search calls as (method, pool size), and per
    dispatch call (unassigned trips, idle vehicles, first search call index).

    The config is copied to a temp dir first because simulate() writes a
    [RESULTS] section back into the config file, and we must not mutate the
    committed fixtures.
    """
    # Imported lazily so collecting Part A never pulls in the simulation stack.
    from ridehail.config import RideHailConfig
    from ridehail.simulation import RideHailSimulation

    temp_dir = Path(tempfile.mkdtemp(prefix="ridehail_perf_"))
    try:
        temp_config = temp_dir / config_path.name
        shutil.copy2(config_path, temp_config)
        blocks = []
        original = Dispatch._dispatch_vehicles_default

        with _record_searches() as calls:

            def recording(self, unassigned_trips, city, vehicles):
                p1 = sum(1 for v in vehicles if v.phase == VehiclePhase.P1)
                blocks.append((len(unassigned_trips), p1, len(calls)))
                return original(self, unassigned_trips, city, vehicles)

            Dispatch._dispatch_vehicles_default = recording
            try:
                with _patched_argv(["ridehail", str(temp_config)]):
                    config = RideHailConfig(use_config_file=True)
                RideHailSimulation(config).simulate()
            finally:
                Dispatch._dispatch_vehicles_default = original
            city_size = config.city_size.value
        return [(m, pool) for m, pool, _ in calls], blocks, city_size
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.regression
class TestDispatchStrategyInSimulation:
    """Confirm each perf_*.config scenario exercises its regime correctly."""

    @pytest.mark.parametrize("name", ["perf_sparse", "perf_dense", "perf_boundary"])
    def test_dense_only_above_threshold(self, name):
        calls, _, city_size = _record_simulation(PERF_CONFIG_DIR / f"{name}.config")
        assert calls, "no searches were recorded"
        threshold = Dispatch.SPARSE_SEARCH_FACTOR * city_size
        offenders = [c for c in calls if c[0] == "dense" and c[1] <= threshold]
        assert offenders == [], f"dense search on small pools: {offenders[:5]}"
        offenders = [c for c in calls if c[0] == "sparse" and c[1] > threshold]
        assert offenders == [], f"sparse search on large pools: {offenders[:5]}"

    def test_sparse_config_never_selects_dense(self):
        calls, _, _ = _record_simulation(PERF_CONFIG_DIR / "perf_sparse.config")
        assert all(method == "sparse" for method, _ in calls)

    def test_dense_config_mostly_selects_dense(self):
        calls, _, _ = _record_simulation(PERF_CONFIG_DIR / "perf_dense.config")
        dense = sum(1 for method, _ in calls if method == "dense")
        assert dense / len(calls) > 0.9

    def test_boundary_config_large_backlog_never_selects_dense(self):
        """The June 2026 regression: large-backlog blocks must search sparse."""
        calls, blocks, city_size = _record_simulation(
            PERF_CONFIG_DIR / "perf_boundary.config"
        )
        # The scenario must actually build a large backlog, or the test proves
        # nothing.
        max_backlog = max(trips for trips, _, _ in blocks)
        assert max_backlog >= LARGE_BACKLOG, (
            f"perf_boundary did not build a large backlog "
            f"(max unassigned trips = {max_backlog}); the fixture no longer "
            f"exercises the pathological regime"
        )
        ends = [start for _, _, start in blocks[1:]] + [len(calls)]
        offenders = [
            (trips, p1)
            for (trips, p1, start), end in zip(blocks, ends)
            if trips >= LARGE_BACKLOG
            and any(method == "dense" for method, _ in calls[start:end])
        ]
        assert offenders == [], (
            f"perf_boundary searched dense in {len(offenders)} large-backlog "
            f"block(s); examples (trips, P1): {offenders[:5]}"
        )
