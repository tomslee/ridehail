"""
Performance regression tests for the dispatch search-strategy selection.

WHAT THIS VALIDATES
===================
The trip->vehicle assignment in ``ridehail/dispatch.py`` chooses, once per
block, between two searches:

  * sparse (vehicle-loop)  -- cost ~ O(trips * P1)
  * dense  (location-ring) -- cost ~ O(P1 + trips * city_size^2 / P1)

where P1 is the number of idle (dispatchable) vehicles.

A previous cost rule (``trips * P1  vs  0.5 * city_size^2``) could select the
*dense* search when P1 was tiny but the unassigned-trip backlog was large -- a
deeply undersupplied run. In that regime the dense search ring-searches a
near-empty grid thousands of times per block, which was the source of a
reported "slows down when the boundary is crossed" performance bug. The fix
adds the omitted dense per-trip term so the decision reduces to roughly
"sparse when P1 < city_size" (see ``Dispatch._use_sparse_search`` and
``utils/benchmark_dispatch.py``).

WHY THIS DOES NOT ASSERT WALL-CLOCK TIME
========================================
Raw timing is too dependent on the machine, CI load, and Python build to be a
reliable gate -- a timing threshold would either be so loose it catches
nothing or so tight it flakes. What actually regressed is the *algorithmic
decision*, so that is what these tests pin down:

Part A (fast, runs by default)
    Unit tests of the pure decision function ``Dispatch._use_sparse_search`` at
    representative ``(trips, P1, city_size)`` points -- including the
    pathological tiny-P1 / large-backlog point -- plus the crossover property
    that the choice flips from sparse to dense exactly once, near P1 ==
    city_size, as P1 grows. A contrast check against the old rule documents the
    bug and guards against an accidental revert.

Part B (marked ``regression``, slower)
    Drives the ``test/perf/perf_*.config`` scenarios through a real,
    animation-free simulation and records which search was actually selected
    each block, then asserts the selection matches each regime. The key guard:
    in the boundary scenario, NO block whose unassigned-trip backlog is large
    may select the dense search.
"""

import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest

from ridehail.dispatch import Dispatch


PERF_CONFIG_DIR = Path(__file__).parent / "perf"

# A backlog this large, with the supply in perf_boundary.config (P1 <= 110 in a
# 64x64 city), is squarely in the regime where the OLD rule chose dense and the
# corrected rule must choose sparse. Used as the boundary-scenario guard.
LARGE_BACKLOG = 300


# ---------------------------------------------------------------------------
# Part A: unit tests of the decision function (fast; run by default)
# ---------------------------------------------------------------------------

def _old_rule_use_sparse(trip_count, vehicle_count, city_size):
    """The pre-fix decision rule, kept here only to document the regression."""
    return trip_count * vehicle_count <= 0.5 * city_size**2


class TestDispatchStrategySelection:
    """Pin the sparse/dense crossover implemented by _use_sparse_search."""

    @pytest.mark.parametrize(
        "trips, p1, city_size",
        [
            (300, 3, 64),     # large backlog, almost no idle vehicles
            (5000, 3, 64),    # the extreme backlog seen in perf_boundary
            (1000, 10, 48),   # backlog >> supply in a mid-size city
            (2000, 30, 100),  # large city, modest supply, heavy backlog
        ],
    )
    def test_large_backlog_tiny_supply_stays_sparse(self, trips, p1, city_size):
        """The pathological regime that caused the slowdown must pick sparse.

        This is the core regression guard: if the cost model reverts to the old
        form, the heavy-backlog points below flip to dense and the test fails.
        """
        assert Dispatch._use_sparse_search(trips, p1, city_size) is True

    @pytest.mark.parametrize(
        "trips, p1, city_size",
        [
            (5000, 3, 64),    # the extreme backlog seen in perf_boundary
            (3000, 20, 64),   # heavy backlog, scarce supply
            (2000, 30, 100),  # large city, modest supply, heavy backlog
        ],
    )
    def test_contrast_old_rule_chose_dense_here(self, trips, p1, city_size):
        """Document the bug: at these points the OLD rule chose the dense search
        (because trips*P1 exceeds 0.5*city_size^2) while the corrected rule
        keeps them on sparse. Guards against an accidental revert of the model.
        """
        assert _old_rule_use_sparse(trips, p1, city_size) is False
        assert Dispatch._use_sparse_search(trips, p1, city_size) is True

    @pytest.mark.parametrize(
        "trips, p1, city_size",
        [
            (30, 800, 32),    # the perf_dense regime: P1 >> city_size
            (100, 200, 64),   # P1 ~ 3 * city_size
            (10, 400, 48),    # few trips, abundant supply
        ],
    )
    def test_dense_regime_uses_dense(self, trips, p1, city_size):
        assert Dispatch._use_sparse_search(trips, p1, city_size) is False

    @pytest.mark.parametrize(
        "trips, p1, city_size",
        [
            (8, 40, 64),      # the perf_sparse regime: P1 << city_size
            (1, 5, 64),       # a single trip, a handful of vehicles
            (64, 50, 64),     # P1 just below city_size under heavy load
        ],
    )
    def test_sparse_regime_uses_sparse(self, trips, p1, city_size):
        assert Dispatch._use_sparse_search(trips, p1, city_size) is True

    def test_zero_vehicles_is_safe_and_sparse(self):
        # No idle vehicles: must not divide by zero, and must avoid the
        # pointless dense grid build.
        assert Dispatch._use_sparse_search(100, 0, 64) is True

    @pytest.mark.parametrize("city_size", [16, 32, 64, 100])
    def test_crossover_is_monotonic_and_near_city_size(self, city_size):
        """For fixed (heavy) load, growing P1 flips sparse->dense exactly once.

        The flip should sit in a band around P1 == city_size: clearly sparse
        well below it, clearly dense well above it.
        """
        trips = city_size  # balanced heavy load
        choices = [
            Dispatch._use_sparse_search(trips, p1, city_size)
            for p1 in range(1, 8 * city_size + 1)
        ]
        # Sparse (True) for small P1, then dense (False) for large P1, with a
        # single transition and no flip back.
        transitions = sum(
            1 for a, b in zip(choices, choices[1:]) if a != b
        )
        assert transitions == 1, "strategy choice should flip exactly once"
        assert choices[0] is True, "should be sparse at the smallest P1"
        assert choices[-1] is False, "should be dense at the largest P1"

        # Locate the crossover P1 and check it is near city_size.
        crossover = next(
            p1 for p1, sparse in enumerate(choices, start=1) if not sparse
        )
        assert 0.5 * city_size <= crossover <= 2.0 * city_size


# ---------------------------------------------------------------------------
# Part B: end-to-end strategy selection on the perf_*.config scenarios
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


def _record_strategy_selections(config_path):
    """Run the config through an animation-free simulation, returning a list of
    (trip_count, vehicle_count, used_sparse) -- one entry per block in which a
    dispatch decision was made.

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

        records = []
        # Accessing a staticmethod via the class yields the plain function.
        original = Dispatch._use_sparse_search

        def recording(trip_count, vehicle_count, city_size):
            used_sparse = original(trip_count, vehicle_count, city_size)
            records.append((trip_count, vehicle_count, used_sparse))
            return used_sparse

        Dispatch._use_sparse_search = staticmethod(recording)
        try:
            with _patched_argv(["ridehail", str(temp_config)]):
                config = RideHailConfig(use_config_file=True)
            RideHailSimulation(config).simulate()
        finally:
            Dispatch._use_sparse_search = staticmethod(original)

        return records
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.mark.regression
class TestDispatchStrategyInSimulation:
    """Confirm each perf_*.config scenario actually exercises its regime."""

    def test_sparse_config_never_selects_dense(self):
        records = _record_strategy_selections(PERF_CONFIG_DIR / "perf_sparse.config")
        assert records, "no dispatch decisions were recorded"
        dense_blocks = [r for r in records if not r[2]]
        assert dense_blocks == [], (
            f"perf_sparse selected the dense search in "
            f"{len(dense_blocks)}/{len(records)} blocks: {dense_blocks[:5]}"
        )

    def test_dense_config_always_selects_dense(self):
        records = _record_strategy_selections(PERF_CONFIG_DIR / "perf_dense.config")
        assert records, "no dispatch decisions were recorded"
        sparse_blocks = [r for r in records if r[2]]
        assert sparse_blocks == [], (
            f"perf_dense selected the sparse search in "
            f"{len(sparse_blocks)}/{len(records)} blocks: {sparse_blocks[:5]}"
        )

    def test_boundary_config_large_backlog_never_selects_dense(self):
        """The regression: large-backlog blocks must use the sparse search.

        A few early blocks (before the backlog builds) may legitimately pick
        dense while supply is plentiful, so we restrict the assertion to blocks
        whose backlog is large -- exactly where the old rule went wrong.
        """
        records = _record_strategy_selections(
            PERF_CONFIG_DIR / "perf_boundary.config"
        )
        assert records, "no dispatch decisions were recorded"

        # The scenario must actually build a large backlog, or the test proves
        # nothing.
        max_backlog = max(trip_count for trip_count, _, _ in records)
        assert max_backlog >= LARGE_BACKLOG, (
            f"perf_boundary did not build a large backlog "
            f"(max unassigned trips = {max_backlog}); the fixture no longer "
            f"exercises the pathological regime"
        )

        offenders = [
            r for r in records if r[0] >= LARGE_BACKLOG and not r[2]
        ]
        assert offenders == [], (
            f"perf_boundary selected the dense search in "
            f"{len(offenders)} large-backlog block(s) "
            f"(backlog >= {LARGE_BACKLOG}); the slow dispatch path has "
            f"regressed. Examples (trips, P1, used_sparse): {offenders[:5]}"
        )
