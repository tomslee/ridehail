"""
Tests for idle_vehicles_returning: idle (P1) vehicles outside the city core
head back towards it with a given probability at each intersection.
"""

from ridehail.atom import City, VehiclePhase
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation


def test_core_bounds_match_trip_origins():
    city = City(32, inhomogeneity=1.0)
    low, high = city.core_bounds()
    assert (low, high) == (8, 24)
    for _ in range(500):
        x, y = city.set_location()
        assert low <= x < high and low <= y < high


def test_nearest_core_location():
    city = City(32)  # core is [8, 24) on each axis
    assert city.nearest_core_location([10, 20]) is None
    # Outside on one axis only: move along that axis
    assert city.nearest_core_location([2, 12]) == [8, 12]
    assert city.nearest_core_location([28, 12]) == [23, 12]
    # Outside on both axes: nearest corner
    assert city.nearest_core_location([0, 31]) == [8, 23]
    # Measured around the torus: 31 is 9 from 8 (via the edge), 8 from 23
    assert city.nearest_core_location([31, 15]) == [23, 15]


def _idle_core_share(returning, inhomogeneity=0.5, blocks=300, seed=7):
    """Mean share of idle vehicles that are in the core, over the run."""
    config = RideHailConfig(use_config_file=False)
    config.animation.value = "none"
    config.random_number_seed.value = seed
    config.city_size.value = 24
    config.vehicle_count.value = 60
    config.base_demand.value = 2.0
    config.mean_trip_distance.value = 8
    config.inhomogeneity.value = inhomogeneity
    config.time_blocks.value = blocks
    config.idle_vehicles_returning.value = returning
    sim = RideHailSimulation(config)
    low, high = sim.city.core_bounds()
    in_core = idle = 0
    for block in range(blocks):
        sim.next_block(block=block, return_values=None)
        for vehicle in sim.vehicles:
            if vehicle.phase == VehiclePhase.P1:
                idle += 1
                x, y = vehicle.location
                in_core += low <= x < high and low <= y < high
    return in_core / idle


def test_returning_concentrates_idle_vehicles_in_core():
    random_share = _idle_core_share(0.0)
    partial_share = _idle_core_share(0.5)
    full_share = _idle_core_share(1.0)
    assert random_share < partial_share < full_share
    assert full_share > 0.6


def test_no_effect_when_homogeneous():
    # With inhomogeneity 0 the setting is ignored, so runs are identical
    assert _idle_core_share(0.0, inhomogeneity=0.0) == _idle_core_share(
        1.0, inhomogeneity=0.0
    )
