"""
Tests for idle_vehicles_returning: with a given probability at each
intersection, idle (P1) vehicles head towards a place requests come from,
drawn as a trip origin is (so mostly in the city core).
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
    assert full_share > 2 * random_share
    # Idle cars head where requests start, so they are no more concentrated
    # in the core than requests are (0.5 + 0.5 * a quarter of the area):
    # an idle car there is soon dispatched
    assert full_share < 0.5 + 0.5 * 0.25


def test_return_target_is_kept_until_reached():
    config = RideHailConfig(use_config_file=False)
    config.animation.value = "none"
    config.random_number_seed.value = 3
    config.city_size.value = 24
    config.vehicle_count.value = 1
    config.base_demand.value = 0.0
    config.inhomogeneity.value = 0.5
    config.idle_vehicles_returning.value = 1.0
    sim = RideHailSimulation(config)
    vehicle = sim.vehicles[0]
    sim.next_block(block=0, return_values=None)
    target = vehicle.return_target
    assert target is not None
    distance = sim.city.distance(vehicle.location, target)
    for block in range(1, distance + 1):
        assert vehicle.return_target == target
        sim.next_block(block=block, return_values=None)
    assert vehicle.location == target


def test_no_effect_when_homogeneous():
    # With inhomogeneity 0 the setting is ignored, so runs are identical
    assert _idle_core_share(0.0, inhomogeneity=0.0) == _idle_core_share(
        1.0, inhomogeneity=0.0
    )
