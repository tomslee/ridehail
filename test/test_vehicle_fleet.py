"""
Vehicles as the fleet grows and shrinks: indexes stay unique, and removing
vehicles keeps the others in order.
"""

import logging
from collections import Counter

from ridehail.atom import Equilibration
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation

logging.disable(logging.CRITICAL)


def make_sim(vehicle_count=60, **extra):
    config = RideHailConfig(use_config_file=False)
    config.animation.value = "none"
    config.time_blocks.value = 0
    config.random_number_seed.value = 7
    config.city_size.value = 16
    config.vehicle_count.value = vehicle_count
    config.base_demand.value = 3.0
    for key, value in extra.items():
        getattr(config, key).value = value
    return RideHailSimulation(config)


def assert_unique_indexes(sim):
    shared = [i for i, n in Counter(v.index for v in sim.vehicles).items() if n > 1]
    assert not shared, f"vehicle indexes used twice: {shared}"


def test_indexes_unique_after_shrink_and_grow():
    sim = make_sim()
    for block in range(60):
        if block == 20:
            sim.target_state["vehicle_count"] = 40
        if block == 40:
            sim.target_state["vehicle_count"] = 60
        sim.next_block()
        assert_unique_indexes(sim)
    assert len(sim.vehicles) == 60


def test_indexes_unique_under_equilibration():
    sim = make_sim(
        vehicle_count=40,
        equilibration=Equilibration.PRICE,
        equilibration_interval=5,
    )
    sizes = set()
    for _ in range(300):
        sim.next_block()
        assert_unique_indexes(sim)
        sizes.add(len(sim.vehicles))
    assert len(sizes) > 1  # the fleet really did change size


def test_remove_vehicles_keeps_order():
    sim = make_sim()
    for _ in range(10):
        sim.next_block()
    before = list(sim.vehicles)
    removed = sim._remove_vehicles(5)
    assert removed == 5
    kept = [v for v in before if v in set(sim.vehicles)]
    assert sim.vehicles == kept
    assert len(sim.vehicles) == len(before) - 5
