"""
Shared pieces for the ridehail performance benchmarks.

- Scenarios: named, reproducible simulation setups (game markets, the
  test/perf fixtures, or any .config file) to run or capture states from.
- Stub vehicles and trips: just enough of Vehicle/Trip for the dispatch code,
  so a captured state can be replayed through the *real* dispatch methods
  without the rest of the simulation.
- Timing: best-of-N wall clock with perf_counter.

No Textual, no animation: safe to run in any console. Run benchmarks from the
repository root (``uv run python benchmarks/bench_dispatch.py ...``) so that
the working copy of ``ridehail`` is the one measured.
"""

import os
import pickle
import platform
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from ridehail import __version__  # noqa: E402
from ridehail.atom import Direction, VehiclePhase  # noqa: E402

RESULTS_DIR = Path(__file__).resolve().parent / "results"
PERF_CONFIG_DIR = REPO_ROOT / "test" / "perf"

_DIRECTIONS = list(Direction)


# ---------------------------------------------------------------------------
# Timing
# ---------------------------------------------------------------------------


def best_time(fn, repeats=3):
    """Best (minimum) wall-clock seconds of `repeats` calls of fn(). fn may
    return a value; the last one is returned with the time."""
    best, result = float("inf"), None
    for _ in range(repeats):
        start = time.perf_counter()
        result = fn()
        best = min(best, time.perf_counter() - start)
    return best, result


def environment():
    """A short description of where a result was measured."""
    return (
        f"ridehail {__version__}, {platform.python_implementation()} "
        f"{platform.python_version()}, {platform.machine()}"
    )


# ---------------------------------------------------------------------------
# Stub vehicles and trips for replaying dispatch
# ---------------------------------------------------------------------------


class StubVehicle:
    """What the DEFAULT dispatch search reads (index, location, direction,
    phase) and changes (phase, via update_phase)."""

    __slots__ = ("index", "location", "direction", "phase")

    def __init__(self, index, location):
        self.index = index
        self.location = list(location)
        self.direction = _DIRECTIONS[index % len(_DIRECTIONS)]
        self.phase = VehiclePhase.P1

    def update_phase(self, trip=None, to_phase=None):
        self.phase = VehiclePhase.P2


class StubTrip:
    __slots__ = ("origin",)

    def __init__(self, origin):
        self.origin = list(origin)

    def update_phase(self, to_phase=None):
        pass


@dataclass
class DispatchState:
    """The input to one dispatch call: the idle (P1) vehicles' locations and
    the unassigned trips' origins, in the order the simulation passed them."""

    label: str
    city_size: int
    vehicle_locations: list
    trip_origins: list
    # Wall-clock seconds the dispatch took in the simulation (0 if synthetic)
    measured: float = 0.0
    block: int = 0

    @property
    def p1(self):
        return len(self.vehicle_locations)

    @property
    def trips(self):
        return len(self.trip_origins)

    def materialize(self):
        """Fresh stub objects for one replay (dispatch changes them)."""
        vehicles = [StubVehicle(i, loc) for i, loc in enumerate(self.vehicle_locations)]
        trips = [StubTrip(origin) for origin in self.trip_origins]
        return vehicles, trips


def uniform_state(city_size, p1, trips, seed=1, label="uniform"):
    """Vehicles and trip origins drawn uniformly over the city."""
    rng = random.Random(seed)

    def point():
        return (rng.randrange(city_size), rng.randrange(city_size))

    return DispatchState(
        label,
        city_size,
        [point() for _ in range(p1)],
        [point() for _ in range(trips)],
    )


def save_states(states, path):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as f:
        pickle.dump(states, f)


def load_states(path):
    with open(path, "rb") as f:
        return pickle.load(f)


# ---------------------------------------------------------------------------
# Scenarios
# ---------------------------------------------------------------------------


@dataclass
class Scenario:
    name: str
    description: str
    # Returns a RideHailConfig ready to simulate (animation off)
    make_config: object = field(repr=False)


def _game_scenario(city, market, seed=7):
    def make():
        from ridehail.game import make_game_config

        return make_game_config(market, seed, 180, 60, city)

    return Scenario(
        f"game-{city}-{market}",
        f"game {city} city, {market} market, seed {seed}, 240 blocks",
        make,
    )


def config_file_scenario(path, name=None):
    """A scenario from a .config file. The config forgets its file name once
    loaded, so a benchmark run never writes results or output files."""
    path = Path(path)

    def make():
        from ridehail.config import RideHailConfig

        saved = sys.argv
        sys.argv = ["ridehail", str(path)]
        try:
            config = RideHailConfig(use_config_file=True)
        finally:
            sys.argv = saved
        config.config_file.value = None
        config.animation.value = "none"
        return config

    return Scenario(name or path.stem, f"config file {path}", make)


SCENARIOS = {
    s.name: s
    for s in (
        [
            _game_scenario(city, market)
            for city in ("standard", "big")
            for market in ("busy", "normal", "slow")
        ]
        + [
            config_file_scenario(PERF_CONFIG_DIR / f"{name}.config")
            for name in ("perf_boundary", "perf_dense", "perf_sparse")
        ]
    )
}


def resolve_scenarios(names):
    """Scenario objects for names, which may be registry names or paths to
    .config files. None or [] means all registered scenarios."""
    if not names:
        return list(SCENARIOS.values())
    scenarios = []
    for name in names:
        if name in SCENARIOS:
            scenarios.append(SCENARIOS[name])
        elif os.path.exists(name):
            scenarios.append(config_file_scenario(name))
        else:
            raise SystemExit(
                f"Unknown scenario '{name}'. Registered: {', '.join(SCENARIOS)}, "
                f"or give a path to a .config file."
            )
    return scenarios


def run_scenario(scenario):
    """Simulate the scenario to the end. Returns wall-clock seconds."""
    from ridehail.simulation import RideHailSimulation

    sim = RideHailSimulation(scenario.make_config())
    start = time.perf_counter()
    sim.simulate()
    return time.perf_counter() - start
