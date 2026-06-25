"""
Tests for base_demand unit conversion between trips/minute (user-facing)
and trips/block (internal), governed by use_city_scale and minutes_per_block.
"""

import pytest
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation


def make_sim(base_demand, minutes_per_block, use_city_scale):
    config = RideHailConfig(use_config_file=False)
    config.animation.value = "none"
    config.time_blocks.value = 0
    config.random_number_seed.value = 42
    config.city_size.value = 10
    config.vehicle_count.value = 5
    config.base_demand.value = base_demand
    config.minutes_per_block.value = minutes_per_block
    config.use_city_scale.value = use_city_scale
    return RideHailSimulation(config)


class TestNoCityScale:
    """When use_city_scale=False, base_demand is in trips/block; no conversion applied."""

    def test_internal_value_unchanged(self):
        sim = make_sim(base_demand=2.0, minutes_per_block=2.0, use_city_scale=False)
        assert sim.base_demand == pytest.approx(2.0)

    def test_display_equals_internal(self):
        sim = make_sim(base_demand=2.0, minutes_per_block=2.0, use_city_scale=False)
        assert sim.display_base_demand == pytest.approx(2.0)

    def test_minutes_per_block_has_no_effect(self):
        sim1 = make_sim(base_demand=3.0, minutes_per_block=1.0, use_city_scale=False)
        sim2 = make_sim(base_demand=3.0, minutes_per_block=4.0, use_city_scale=False)
        assert sim1.base_demand == pytest.approx(sim2.base_demand)


class TestWithCityScale:
    """When use_city_scale=True, config value is trips/minute; internal is trips/block."""

    def test_internal_scaled_up(self):
        # 3 trips/min × 2 min/block = 6 trips/block internally
        sim = make_sim(base_demand=3.0, minutes_per_block=2.0, use_city_scale=True)
        assert sim.base_demand == pytest.approx(6.0)

    def test_display_recovers_config_value(self):
        sim = make_sim(base_demand=3.0, minutes_per_block=2.0, use_city_scale=True)
        assert sim.display_base_demand == pytest.approx(3.0)

    def test_unit_minutes_per_block_one_is_noop(self):
        # minutes_per_block=1 → internal == config value
        sim = make_sim(base_demand=2.5, minutes_per_block=1.0, use_city_scale=True)
        assert sim.base_demand == pytest.approx(2.5)
        assert sim.display_base_demand == pytest.approx(2.5)

    def test_round_trip(self):
        """display_base_demand must always equal the original config value."""
        for mpb in (0.5, 1.0, 2.0, 5.0):
            sim = make_sim(base_demand=4.0, minutes_per_block=mpb, use_city_scale=True)
            assert sim.display_base_demand == pytest.approx(4.0), (
                f"round-trip failed for minutes_per_block={mpb}"
            )

    def test_congestion_raises_internal_demand(self):
        """Doubling minutes_per_block (slower traffic) should double internal demand."""
        sim1 = make_sim(base_demand=2.0, minutes_per_block=1.0, use_city_scale=True)
        sim2 = make_sim(base_demand=2.0, minutes_per_block=2.0, use_city_scale=True)
        assert sim2.base_demand == pytest.approx(2 * sim1.base_demand)
