"""The parameter values a sequence sweeps (ridehail.sequence.sequence_values)."""

from ridehail.config import RideHailConfig
from ridehail.sequence import sequence_values, value_range


def test_value_range_includes_stop_and_no_more():
    assert value_range(1.0, 2.0, 0.5) == [1.0, 1.5, 2.0]
    assert value_range(0.0, 0.3, 0.1) == [0.0, 0.1, 0.2, 0.3]
    assert value_range(0.29, 0.31, 0.01) == [0.29, 0.3, 0.31]
    assert value_range(2.0, 1.0, 0.5) == []


def test_sequence_values():
    config = RideHailConfig(use_config_file=False)
    config.vehicle_count.value = 10
    config.vehicle_count_increment.value = 5
    config.vehicle_count_max.value = 20
    config.base_demand.value = 1.0
    config.request_rate_increment.value = 0.5
    config.request_rate_max.value = 2.0
    vehicles, rates, inhomogeneities, commissions = sequence_values(config)
    assert vehicles == [10, 15, 20]
    assert rates == [1.0, 1.5, 2.0]
    assert inhomogeneities == [config.inhomogeneity.value]
    assert commissions == [config.platform_commission.value]
