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
