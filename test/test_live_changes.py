"""
Live changes to a running simulation: target_state holds pending changes
only, city-scale prices, and the keyboard / UI controls (ridehail.keyboard).
"""

import logging

import pytest

from ridehail.atom import Equilibration
from ridehail.config import ConfigValidationError, RideHailConfig
from ridehail.keyboard import (
    ANIMATION_DELAY_ACTIONS,
    STEPPED_ACTIONS,
    KeyboardHandler,
    SimulationControls,
)
from ridehail.keyboard_mappings import get_mapping_for_action, get_mapping_for_key
from ridehail.simulation import RideHailSimulation

logging.disable(logging.CRITICAL)


def make_sim(**extra):
    config = RideHailConfig(use_config_file=False)
    config.animation.value = "none"
    config.time_blocks.value = 0
    config.random_number_seed.value = 7
    config.city_size.value = 16
    config.vehicle_count.value = 30
    config.base_demand.value = 2.0
    for key, value in extra.items():
        getattr(config, key).value = value
    return RideHailSimulation(config)


class TestTargetState:
    def test_starts_empty(self):
        assert make_sim().target_state == {}

    def test_pending_change_is_applied_then_cleared(self):
        sim = make_sim()
        sim.request_change("vehicle_count", 20)
        sim.next_block()
        assert len(sim.vehicles) == 20
        assert sim.target_state == {}

    def test_direct_change_is_not_reverted(self):
        sim = make_sim()
        sim.base_demand = 3.0
        sim.next_block()
        assert sim.base_demand == 3.0

    def test_impulse_applies_at_its_block(self):
        sim = make_sim(impulse_list=[{"block": 5, "base_demand": 4.0}])
        for _ in range(5):
            sim.next_block()
        assert sim.base_demand == 2.0
        sim.next_block()
        assert sim.base_demand == 4.0


class TestRequestChange:
    def test_value_is_converted(self):
        sim = make_sim()
        assert sim.request_change("vehicle_count", "40") == 40
        assert sim.request_change("equilibration", "pri") == Equilibration.PRICE

    def test_setting_that_is_not_live(self):
        with pytest.raises(ConfigValidationError):
            make_sim().request_change("mean_trip_distance", 4)

    def test_attribute_that_is_not_a_setting(self):
        with pytest.raises(ConfigValidationError):
            make_sim().request_change("vehicles", [])

    def test_value_out_of_range_is_brought_inside(self):
        sim = make_sim()
        assert sim.request_change("inhomogeneity", 1.5) == 1.0
        assert sim.request_change("price", 4.0000000001) == 4.0

    def test_value_of_the_wrong_type(self):
        with pytest.raises(ConfigValidationError):
            make_sim().request_change("inhomogeneity", "high")

    def test_city_size_made_even(self):
        assert make_sim().request_change("city_size", 7) == 6

    def test_pending(self):
        sim = make_sim()
        assert sim.pending("vehicle_count") == 30
        sim.request_change("vehicle_count", 20)
        assert sim.pending("vehicle_count") == 20
        sim.next_block()
        assert sim.pending("vehicle_count") == 20

    def test_applied_changes_are_recorded_for_one_block(self):
        sim = make_sim()
        sim.request_change("vehicle_count", 20)
        sim.request_change("base_demand", 2.0)  # unchanged
        sim.next_block()
        assert sim.applied_changes == {"vehicle_count": (30, 20)}
        sim.next_block()
        assert sim.applied_changes == {}

    def test_city_size_change_moves_vehicles_inside(self):
        sim = make_sim()
        for _ in range(5):
            sim.next_block()
        sim.request_change("city_size", 4)
        sim.next_block()
        assert sim.city.city_size == 4
        assert all(0 <= c < 4 for v in sim.vehicles for c in v.location)

    def test_switching_equilibration_off_keeps_the_fleet(self):
        sim = make_sim(equilibration="price")
        sim._remove_vehicles(5)  # as equilibration would
        sim.request_change("equilibration", Equilibration.NONE)
        sim.next_block()
        assert sim.vehicle_count == 25
        assert len(sim.vehicles) == 25

    def test_switching_equilibration_off_with_a_new_fleet_size(self):
        sim = make_sim(equilibration="price")
        sim.request_change("equilibration", Equilibration.NONE)
        sim.request_change("vehicle_count", 40)
        sim.next_block()
        assert len(sim.vehicles) == 40


class TestImpulses:
    def test_unknown_setting_fails_at_the_start(self):
        with pytest.raises(ConfigValidationError):
            make_sim(impulse_list=[{"block": 5, "vehicle_cont": 5}])

    def test_bad_value_fails_at_the_start(self):
        with pytest.raises(ConfigValidationError):
            make_sim(impulse_list=[{"block": 5, "equilibration": "sideways"}])

    def test_impulse_needs_a_block(self):
        with pytest.raises(ConfigValidationError):
            make_sim(impulse_list=[{"base_demand": 4.0}])


class TestCityScalePrices:
    def test_price_is_set_from_the_start(self):
        sim = make_sim(use_city_scale=True)
        price, wage = sim.price, sim.reservation_wage
        sim.next_block()
        assert (sim.price, sim.reservation_wage) == (price, wage)

    def test_live_change_to_an_input_updates_the_price(self):
        sim = make_sim(use_city_scale=True)
        price = sim.price
        sim.request_change("per_km_price", sim.per_km_price * 1.5)
        sim.next_block()
        assert sim.price > price


class TestControls:
    def test_vehicle_steps(self):
        sim = make_sim()
        controls = SimulationControls(sim)
        assert controls.handle_ui_action("increase_vehicles", 10) == 40
        assert controls.handle_ui_action("decrease_vehicles", 5) == 35
        sim.next_block()
        assert len(sim.vehicles) == 35

    def test_animation_delay_changes_at_once(self):
        sim = make_sim(animation_delay=0.2)
        controls = SimulationControls(sim)
        controls.handle_ui_action("increase_animation_delay", 0.1)
        assert sim.animation_delay == pytest.approx(0.3)
        sim.next_block()
        assert sim.animation_delay == pytest.approx(0.3)

    def test_city_size_steps_within_its_range(self):
        sim = make_sim()
        controls = SimulationControls(sim)
        assert controls.handle_ui_action("increase_city_size") == 18
        assert controls.handle_ui_action("decrease_city_size") == 16
        assert controls.handle_ui_action("decrease_city_size", 100) == 2

    def test_default_steps_come_from_the_key_mappings(self):
        sim = make_sim()
        controls = SimulationControls(sim)
        assert controls.handle_ui_action("increase_vehicles") == 31
        assert controls.handle_ui_action("increase_demand") == pytest.approx(2.1)

    def test_vehicles_stop_at_the_minimum(self):
        sim = make_sim(vehicle_count=2)
        controls = SimulationControls(sim)
        assert controls.handle_ui_action("decrease_vehicles", 5) == 1

    def test_demand_steps_in_display_units(self):
        sim = make_sim(use_city_scale=True)
        controls = SimulationControls(sim)
        before = sim.display_base_demand
        target = controls.handle_ui_action("increase_demand", 1.0)
        assert sim.demand_to_display(target) == pytest.approx(before + 1.0)

    def test_unknown_action(self):
        assert SimulationControls(make_sim()).handle_ui_action("fly") is None

    def test_space_bar_pauses(self):
        handler = KeyboardHandler(make_sim())
        assert handler._handle_key(" ") is True
        assert handler.is_paused

    def test_help_key_is_handled(self, capsys):
        handler = KeyboardHandler(make_sim())
        assert handler._handle_key("h") is True
        assert "Press any key" in capsys.readouterr().out


class TestKeyMappings:
    def test_every_stepped_action_has_a_default_step(self):
        for action in STEPPED_ACTIONS | ANIMATION_DELAY_ACTIONS:
            assert get_mapping_for_action(action).value is not None

    def test_stepped_settings_are_live(self):
        config = RideHailConfig(use_config_file=False)
        for setting, _ in STEPPED_ACTIONS.values():
            assert getattr(config, setting).live

    def test_live_change_actions_are_for_live_settings(self):
        config = RideHailConfig(use_config_file=False)
        for setting in RideHailSimulation._LIVE_CHANGE_ACTIONS:
            assert getattr(config, setting).live

    def test_matplotlib_keys(self):
        assert get_mapping_for_key("ctrl+N", platform="matplotlib").value == 10
        assert get_mapping_for_key("c", platform="matplotlib").action == (
            "decrease_city_size"
        )
        assert get_mapping_for_key(" ", platform="matplotlib").action == "pause"
