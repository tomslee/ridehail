"""
Tests for idle_vehicles_returning: with a given probability at each
intersection, idle (P1) vehicles head towards a place requests come from,
drawn as a trip origin is (so mostly in the city core).
"""

import math
import random
import statistics

import pytest

from ridehail.atom import City, Equilibration, Vehicle, VehiclePhase
from ridehail.config import RideHailConfig
from ridehail.game import market
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


def _expected_approach(returning, moving, blocks):
    """
    Expected fall in the distance from an idle car to a far-off return
    target over a number of blocks. The car steps towards the target with
    probability `returning` at each intersection, and otherwise turns at
    random: one of four directions, drawn again once if it is a U-turn, so
    it keeps its direction with probability 5/16, reverses with 1/16 and
    turns each way with 5/16. With the target off both axes, a random turn
    after a step towards the target is towards it with probability 10/16
    and after a step away with probability 6/16, so random turns carry
    some drift of their own (q below is the chance that the car's current
    direction is towards the target). The direction is chosen every block,
    and the car moves in a block with probability `moving`, before that
    block's choice.
    """
    q = 0.5
    approach = 0.0
    for _ in range(blocks):
        approach += moving * (2 * q - 1)
        q = returning + (1 - returning) * (6 + 4 * q) / 16
    return approach


def _approach_to_target(returning, moving, blocks=12, vehicles=4000, seed=5):
    """
    Mean fall in the distance from idle cars to their return target over a
    number of blocks, with no requests. Each car starts 16 blocks from its
    target on both axes in a 64-block city, so it cannot reach the target,
    get level with it on an axis, or cross the far side of the torus (where
    any step brings it closer) in 12 blocks.
    """
    config = RideHailConfig(use_config_file=False)
    config.animation.value = "none"
    config.random_number_seed.value = seed
    config.city_size.value = 64
    config.vehicle_count.value = vehicles
    config.base_demand.value = 0.0
    config.equilibration.value = Equilibration.NONE
    config.inhomogeneity.value = 0.5
    config.idle_vehicles_returning.value = returning
    config.idle_vehicles_moving.value = moving
    config.time_blocks.value = blocks
    sim = RideHailSimulation(config)
    start, target = [16, 16], [32, 32]
    for vehicle in sim.vehicles:
        vehicle.location = start.copy()
        vehicle.return_target = target.copy()
    for block in range(blocks):
        sim.next_block(block=block, return_values=None)
    falls = [
        sim.city.distance(start, target) - sim.city.distance(v.location, target)
        for v in sim.vehicles
    ]
    for vehicle in sim.vehicles:
        assert vehicle.phase == VehiclePhase.P1
        assert vehicle.return_target == target
    return statistics.mean(falls), statistics.stdev(falls) / math.sqrt(len(falls))


@pytest.mark.parametrize(
    "returning, moving",
    [
        (0.0, 1.0),
        (0.25, 1.0),
        (1.0, 1.0),
        # The game's settings
        (market.IDLE_VEHICLES_RETURNING, market.IDLE_VEHICLES_MOVING),
    ],
)
def test_drift_towards_return_target(returning, moving):
    blocks = 12
    expected = _expected_approach(returning, moving, blocks)
    mean, standard_error = _approach_to_target(returning, moving, blocks)
    # Within five standard errors of the expected drift (about 0.35 blocks)
    assert abs(mean - expected) < 5 * standard_error, (mean, expected)


def test_drift_rate_at_game_settings():
    # A quarter of a block towards the target each move from the returning
    # turns, about 0.31 with the drift of the random turns that follow
    # them, and half that per minute as idle cars move half the time
    p = market.IDLE_VEHICLES_RETURNING
    per_move = _expected_approach(p, 1.0, 1000) / 1000
    assert per_move == pytest.approx(4 * p / (3 + p), abs=1e-3)
    per_minute = _expected_approach(p, market.IDLE_VEHICLES_MOVING, 1000) / 1000
    assert per_minute == pytest.approx(market.IDLE_VEHICLES_MOVING * per_move, 1e-2)


def test_return_targets_are_drawn_like_request_origins():
    # A return target is in the core (a quarter of the area) with
    # probability inhomogeneity + (1 - inhomogeneity) / 4: 0.625 at the
    # game's inhomogeneity of 0.5, not always
    random.seed(9)
    inhomogeneity = 0.5
    city = City(32, inhomogeneity=inhomogeneity, idle_vehicles_returning=1.0)
    draws = 20000
    in_core = 0
    for i in range(draws):
        vehicle = Vehicle(i, city)
        # Off the grid, so no draw is where the car already is
        vehicle.location = [-1, -1]
        in_core += city.zone(vehicle._return_target()) == "core"
    expected = inhomogeneity + (1 - inhomogeneity) / 4
    standard_error = math.sqrt(expected * (1 - expected) / draws)
    assert abs(in_core / draws - expected) < 5 * standard_error
