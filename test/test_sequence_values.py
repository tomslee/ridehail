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


def _sequence_config(time_blocks, results_window=50):
    config = RideHailConfig(use_config_file=False)
    config.time_blocks.value = time_blocks
    config.results_window.value = results_window
    return config


def test_sequence_needs_more_blocks_than_results_window():
    for time_blocks, results_window, valid in (
        (100, 50, True),
        (50, 50, False),
        (12, 50, False),
        (0, 50, False),
    ):
        config = _sequence_config(time_blocks, results_window)
        is_valid, _, message = config.run_sequence.validate_value(True, config)
        assert is_valid == valid, (time_blocks, results_window, message)
    # Not a sequence: no constraint
    config = _sequence_config(12)
    assert config.run_sequence.validate_value(False, config)[0]


def test_short_sequence_config_file_is_rejected(tmp_path, monkeypatch):
    import pytest

    from ridehail.config import ConfigValidationError

    path = tmp_path / "short.config"
    path.write_text("[DEFAULT]\nrun_sequence = True\ntime_blocks = 12\n")
    monkeypatch.setattr("sys.argv", ["ridehail", str(path)])
    with pytest.raises(ConfigValidationError):
        RideHailConfig()
