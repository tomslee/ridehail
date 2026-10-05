"""
Live changes to a running simulation: target_state holds pending changes
only, city-scale prices, and the keyboard / UI controls (ridehail.keyboard).
"""

import logging

import pytest

from ridehail.config import RideHailConfig
from ridehail.keyboard import KeyboardHandler, SimulationControls
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
        sim.target_state["vehicle_count"] = 20
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


class TestCityScalePrices:
    def test_price_is_set_from_the_start(self):
        sim = make_sim(use_city_scale=True)
        price, wage = sim.price, sim.reservation_wage
        sim.next_block()
        assert (sim.price, sim.reservation_wage) == (price, wage)

    def test_live_change_to_an_input_updates_the_price(self):
        sim = make_sim(use_city_scale=True)
        price = sim.price
        sim.target_state["per_km_price"] = sim.per_km_price * 2
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

    def test_city_size_stays_even(self):
        sim = make_sim()
        controls = SimulationControls(sim)
        assert controls.adjust_city_size(2) == 18
        assert controls.adjust_city_size(-2) == 16
        assert controls.adjust_city_size(-100) == 2

    def test_unknown_action(self):
        assert SimulationControls(make_sim()).handle_ui_action("fly") is None

    def test_help_key_is_handled(self, capsys):
        handler = KeyboardHandler(make_sim())
        assert handler._handle_key("h") is True
        assert "Press any key" in capsys.readouterr().out
