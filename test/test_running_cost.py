"""
Tests for running costs separated from the reservation wage
(claude/running-cost-spec.md): per_block_ops_cost in Simple mode,
per_km_ops_cost with use_city_scale, charged on every block except idle
blocks spent parked.
"""

import pytest

from ridehail.atom import CityScaleUnit, Measure
from ridehail.config import RideHailConfig
from ridehail.results import RideHailSimulationResults
from ridehail.simulation import RideHailSimulation


def run(blocks=400, **values):
    """Run a small city for blocks blocks; return the sim and its results."""
    config = RideHailConfig(use_config_file=False)
    settings = {
        "animation": "none",
        "random_number_seed": 7,
        "city_size": 12,
        "vehicle_count": 40,
        "base_demand": 2.0,
        "time_blocks": blocks,
        "results_window": 200,
        **values,
    }
    for name, value in settings.items():
        getattr(config, name).value = value
    config._convert_config_values_to_enum()
    sim = RideHailSimulation(config)
    for _ in range(blocks):
        sim.next_block()
    return sim, RideHailSimulationResults(sim).get_result_measures()


def test_defaults_charge_no_running_cost():
    sim, measures = run()
    assert sim.ops_cost == 0.0
    assert measures[Measure.VEHICLE_FRACTION_PARKED.name] == 0.0
    gross = measures[Measure.VEHICLE_GROSS_INCOME.name]
    assert measures[Measure.VEHICLE_NET_INCOME.name] == gross
    assert measures[Measure.VEHICLE_MEAN_SURPLUS.name] == pytest.approx(
        gross - sim.reservation_wage
    )


def test_simple_mode_net_and_surplus():
    sim, measures = run(per_block_ops_cost=0.1, idle_vehicles_moving=0.5)
    parked = measures[Measure.VEHICLE_FRACTION_PARKED.name]
    assert 0.0 < parked < measures[Measure.VEHICLE_FRACTION_P1.name] + 0.05
    gross = measures[Measure.VEHICLE_GROSS_INCOME.name]
    net = measures[Measure.VEHICLE_NET_INCOME.name]
    assert net == pytest.approx(gross - 0.1 * (1.0 - parked))
    assert measures[Measure.VEHICLE_MEAN_SURPLUS.name] == pytest.approx(
        net - sim.reservation_wage
    )


def test_moving_idle_cars_are_never_parked():
    _, measures = run(per_block_ops_cost=0.1, idle_vehicles_moving=1.0)
    assert measures[Measure.VEHICLE_FRACTION_PARKED.name] == 0.0


def test_parked_flag_only_for_idle_cars_standing_still():
    sim, _ = run(blocks=50, idle_vehicles_moving=0.0)
    for vehicle in sim.vehicles:
        before = list(vehicle.location)
        phase = vehicle.phase
        vehicle.update_location()
        assert vehicle.parked == (phase.name == "P1")
        if vehicle.parked:
            assert vehicle.location == before


def test_city_scale_separates_the_two_costs():
    sim, measures = run(
        use_city_scale=True,
        per_km_ops_cost=0.3,
        per_hour_opportunity_cost=10.0,
        idle_vehicles_moving=0.5,
    )
    # The reservation wage is the opportunity cost alone
    assert sim.reservation_wage == pytest.approx(
        round(
            sim.convert_units(10.0, CityScaleUnit.PER_HOUR, CityScaleUnit.PER_BLOCK),
            2,
        )
    )
    assert sim.ops_cost == pytest.approx(
        sim.convert_units(0.3, CityScaleUnit.PER_KM, CityScaleUnit.PER_BLOCK)
    )
    parked = measures[Measure.VEHICLE_FRACTION_PARKED.name]
    assert parked > 0.0
    per_hour = sim.convert_units(1.0, CityScaleUnit.PER_BLOCK, CityScaleUnit.PER_HOUR)
    gross = measures[Measure.VEHICLE_GROSS_INCOME.name]
    net = measures[Measure.VEHICLE_NET_INCOME.name]
    assert net == pytest.approx(gross - sim.ops_cost * (1.0 - parked) * per_hour)
    assert measures[Measure.VEHICLE_MEAN_SURPLUS.name] == pytest.approx(
        net - sim.reservation_wage * per_hour
    )


def test_utility_counts_running_cost_only_when_driven():
    sim, _ = run(blocks=10, per_block_ops_cost=0.2, reservation_wage=0.3)
    p = sim.price * (1.0 - sim.platform_commission)
    assert sim.vehicle_utility(0.5) == pytest.approx(p * 0.5 - 0.2 - 0.3)
    assert sim.vehicle_utility(0.5, 0.25) == pytest.approx(p * 0.5 - 0.15 - 0.3)


def test_parking_raises_the_equilibrium_fleet():
    """Price equilibration: cheaper idle time supports more vehicles."""
    common = {
        "equilibration": "price",
        "per_block_ops_cost": 0.2,
        "reservation_wage": 0.1,
        "blocks": 800,
    }
    moving, _ = run(idle_vehicles_moving=1.0, **common)
    parking, _ = run(idle_vehicles_moving=0.0, **common)
    assert len(parking.vehicles) > len(moving.vehicles)


def test_end_state_reports_parked_share():
    sim, _ = run(per_block_ops_cost=0.1, idle_vehicles_moving=0.5)
    end_state = RideHailSimulationResults(sim).get_end_state()
    assert end_state["vehicles"]["fraction_parked"] > 0.0
