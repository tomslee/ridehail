"""
docs/lab/worker.py, the web lab's bridge to the simulation, run under CPython.
worker.py is imported directly; a small stand-in replaces the Pyodide proxy
for the settings the browser sends.
"""

import logging
import sys
from pathlib import Path

import pytest

logging.disable(logging.CRITICAL)

LAB = Path(__file__).resolve().parent.parent / "docs" / "lab"


@pytest.fixture
def worker(monkeypatch):
    monkeypatch.syspath_prepend(str(LAB))
    # In the browser sys.argv is empty; RideHailConfig() would otherwise read
    # pytest's arguments as a config file name
    monkeypatch.setattr(sys, "argv", ["worker.py"])
    import worker

    return worker


class Proxy:
    """Stands in for a Pyodide JsProxy of a JS object."""

    def __init__(self, values):
        self.values = values

    def to_py(self):
        return dict(self.values)


def lab_settings(**overrides):
    """A complete set of web settings, as js/sim-settings.js sends them."""
    settings = {
        "citySize": 16,
        "vehicleCount": 60,
        "requestRate": 3.0,
        "meanTripDistance": 8,
        "minTripDistance": 0,
        "inhomogeneity": 0.0,
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
        "perHourOpportunityCost": 13.0,
        "timeBlocks": 0,
        "smoothingWindow": 20,
        "animationDelay": 0,
        "pickupTime": 1,
    }
    settings.update(overrides)
    return settings


def torus_distance(a, b, size):
    return sum(min(abs(x - y) % size, size - abs(x - y) % size) for x, y in zip(a, b))


def test_midpoints_follow_each_car_when_the_fleet_shrinks(worker):
    """
    An interpolated (odd) frame puts each car half way along its last move,
    so within half a block of where the previous real frame showed it, even
    on the frame after vehicles were removed.
    """
    size = 16
    w = worker.Simulation(Proxy(lab_settings(citySize=size)))
    previous = None
    for frame in range(80):
        if frame == 41:
            w.sim.target_state["vehicle_count"] = 40
        results = w.next_frame_map()
        if results["frame"] % 2 == 1 and previous is not None:
            ids = [v.index for v in w.sim.vehicles]
            for vehicle_id, car in zip(ids, results["vehicles"]):
                if vehicle_id in previous:
                    assert torus_distance(car[1], previous[vehicle_id], size) <= 0.5
        else:
            ids = [v.index for v in w.sim.vehicles]
            previous = {i: car[1] for i, car in zip(ids, results["vehicles"])}
    assert len(w.sim.vehicles) == 40


def test_live_request_rate_in_city_scale_units(worker):
    """A live update keeps the slider's trips/minute in city-scale mode."""
    settings = lab_settings(useCostsAndIncomes=True, minutesPerBlock=2.0)
    w = worker.Simulation(Proxy(settings))
    assert w.sim.display_base_demand == pytest.approx(3.0)
    w.update_options(Proxy(settings))
    w.next_block_stats()
    assert w.sim.display_base_demand == pytest.approx(3.0)


def test_settings_defaults_and_legacy_values(worker):
    """Older saved sessions: no optional settings, the equilibrate boolean."""
    from ridehail.atom import Equilibration, TripDistribution

    settings = lab_settings(equilibrate=True, meanTripDistance=None, title="")
    for name in ("equilibration", "minTripDistance", "pickupTime", "baseFare"):
        del settings[name]
    sim = worker.Simulation(Proxy(settings)).sim
    assert sim.equilibration == Equilibration.PRICE
    assert sim.pickup_time == 1
    assert sim.base_fare == 0.0
    assert sim.title is None
    assert sim.trip_distance_distribution == TripDistribution.UNIFORM
    assert sim.animation_delay == 0.0


def test_unknown_names_fall_back(worker):
    from ridehail.atom import Equilibration, TripDistribution

    settings = lab_settings(equilibration="wobble", tripDistanceDistribution="zipf")
    sim = worker.Simulation(Proxy(settings)).sim
    assert sim.equilibration == Equilibration.NONE
    assert sim.trip_distance_distribution == TripDistribution.UNIFORM


def test_gamma_trip_distance_distribution(worker):
    from ridehail.atom import TripDistribution

    settings = lab_settings(tripDistanceDistribution="gamma")
    sim = worker.Simulation(Proxy(settings)).sim
    assert sim.trip_distance_distribution == TripDistribution.GAMMA


def test_help_stops_before_the_values_table(worker):
    from ridehail.config import VALUES_HEADER

    lines = worker.get_slider_help()["tripDistanceDistribution"]
    assert lines and VALUES_HEADER not in lines
    assert any(line.startswith("- gamma") for line in lines)


def test_reindexed_marks_the_first_frame_after_a_shift(worker):
    """
    "reindexed" is set on the first frame showing a vehicle list in which
    cars have moved along (vehicles removed ahead of them), and only there:
    the map then snaps rather than glide each point from another car's place.
    """
    for size, frames_per_block in ((16, 2), (40, 1)):
        w = worker.Simulation(Proxy(lab_settings(citySize=size)))
        flagged = []
        shown = None
        for frame in range(80):
            if frame == 41:
                w.sim.target_state["vehicle_count"] = 40
            results = w.next_frame_map()
            ids = [v.index for v in w.sim.vehicles]
            shifted = shown is not None and any(a != b for a, b in zip(shown, ids))
            assert results["reindexed"] == shifted
            if results["reindexed"]:
                flagged.append(results["frame"])
            shown = ids
        # Only idle cars are removed, so a shrink can take more than one
        # block, but the next frame of an interpolated pair is never flagged
        assert flagged
        if frames_per_block == 2:
            assert all(frame % 2 == 1 for frame in flagged)
        assert len(w.sim.vehicles) < 60


def follow(w):
    """Follow a random car and return the vehicle followed."""
    payload = w.follow_vehicle("random")
    vehicle = w.sim.vehicles[payload["position"]]
    assert vehicle.index == payload["index"] == w.followed_index
    return vehicle


def test_follow_prefers_an_idle_car_and_switches_car(worker):
    w = worker.Simulation(Proxy(lab_settings()))
    for _ in range(20):
        w.next_frame_map()
    first = follow(w)
    assert first.phase.name == "P1"
    second = follow(w)
    assert second is not first
    assert w.follow_vehicle(None) is None
    assert w.next_frame_map()["followed"] is None


def test_followed_trip_and_position_each_frame(worker):
    """
    Each frame names the followed car's position in its vehicle list and its
    trip: on real-block frames as the car is now, on interpolated frames as
    on the previous real frame (as the car's colour is).
    """
    w = worker.Simulation(Proxy(lab_settings()))
    w.next_frame_map()
    w.next_frame_map()
    vehicle = follow(w)
    phases = set()
    previous = None
    for _ in range(200):
        results = w.next_frame_map()
        followed = results["followed"]
        assert followed["position"] == w.sim.vehicles.index(vehicle)
        if results["frame"] % 2 == 1:
            assert {k: followed[k] for k in previous} == previous
            continue
        previous = {
            "phase": vehicle.phase.name,
            "pickup": list(vehicle.pickup_location) or None,
            "dropoff": list(vehicle.dropoff_location) or None,
        }
        assert {k: followed[k] for k in previous} == previous
        assert results["vehicles"][followed["position"]][0] == vehicle.phase.name
        phases.add(vehicle.phase.name)
    assert phases == {"P1", "P2", "P3"}


def test_followed_car_kept_when_the_fleet_shrinks(worker):
    """Cars ahead of the followed one are removed: it is still followed."""
    w = worker.Simulation(Proxy(lab_settings()))
    w.next_frame_map()
    w.next_frame_map()
    vehicle = w.sim.vehicles[-1]
    w.follow_vehicle(vehicle.index)
    w.sim.target_state["vehicle_count"] = 40
    positions = set()
    for _ in range(20):
        results = w.next_frame_map()
        assert results["followed"]["index"] == vehicle.index
        assert w.sim.vehicles[results["followed"]["position"]] is vehicle
        positions.add(results["followed"]["position"])
    assert max(positions) == 59
    assert min(positions) == len(w.sim.vehicles) - 1 < 59


def test_followed_car_leaving_the_fleet(worker):
    """A removed car is reported once as left, then no longer followed."""
    w = worker.Simulation(Proxy(lab_settings()))
    w.next_frame_map()
    w.next_frame_map()
    # The first idle car is the first to go when the fleet shrinks
    vehicle = next(v for v in w.sim.vehicles if v.phase.name == "P1")
    w.follow_vehicle(vehicle.index)
    w.sim.target_state["vehicle_count"] = 10
    payloads = [w.next_frame_map()["followed"] for _ in range(6)]
    assert vehicle not in w.sim.vehicles
    assert payloads.count({"index": vehicle.index, "left": True}) == 1
    assert payloads[-1] is None
    assert w.followed_index is None


def test_following_does_not_change_the_run(worker):
    """Following draws on its own random generator, not the simulation's."""
    runs = []
    for following in (False, True):
        w = worker.Simulation(Proxy(lab_settings()))
        for frame in range(120):
            if following and frame % 15 == 0:
                w.follow_vehicle("random")
            results = w.next_frame_map()
        runs.append(results["vehicles"])
    assert runs[0] == runs[1]
