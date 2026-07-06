#!/usr/bin/env python3
"""
Tests for the mean_trip_distance constraint (must be no greater than
city_size // 2).

The rule is defined once, in MEAN_TRIP_DISTANCE_MAX_RELATION, and consumed by
config.py::_validate_mean_trip_distance, the simulation, and the web UI. These
tests pin down that:

  1. The ConfigItem validator caps an out-of-range value at city_size // 2.
  2. The simulation-level RideHailSimulation._validate_options defers to that
     same rule rather than applying its own (previously city_size // 4) clamp.
  3. A value already within range is left untouched by the simulation.
  4. The constraint metadata exported to the web UI (via the ConfigItem
     max_relation and docs/lab/worker.py::get_slider_config) matches the rule
     the validator actually enforces.

Item 2 guards against regressing to the earlier state where the two code paths
disagreed (config capped at // 2, the simulation clamped to // 4). Item 4
guards against the Python and web-UI constraints drifting apart.
"""

import sys
from pathlib import Path

from ridehail.config import RideHailConfig, MEAN_TRIP_DISTANCE_MAX_RELATION
from ridehail.simulation import RideHailSimulation

# docs/lab/worker.py is the web bridge; it imports cleanly outside Pyodide.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "docs" / "lab"))


def _minimal_config(city_size):
    config = RideHailConfig(use_config_file=False)
    config.animation.value = "none"
    config.time_blocks.value = 1
    config.random_number_seed.value = 42
    config.city_size.value = city_size
    config.vehicle_count.value = 4
    config.base_demand.value = 1.0
    return config


def test_validator_caps_at_half_city_size():
    """The ConfigItem validator caps a value in (city_size // 2, city_size]."""
    config = _minimal_config(city_size=16)
    is_valid, validated_value, _ = config.mean_trip_distance.validate_value(12, config)
    assert is_valid
    assert validated_value == 8  # 16 // 2, not 16 // 4


def test_validator_rejects_value_above_city_size():
    """A value larger than city_size itself is rejected outright."""
    config = _minimal_config(city_size=16)
    is_valid, _validated_value, message = config.mean_trip_distance.validate_value(
        20, config
    )
    assert not is_valid
    assert "city_size" in message


def test_simulation_caps_at_half_city_size():
    """
    _validate_options must cap a mean_trip_distance in the band
    (city_size // 2, city_size] at city_size // 2, matching the ConfigItem
    validator (and NOT city_size // 4).

    Setting the value after config construction skips the config-time
    validation, so the simulation is the thing doing the capping here.
    """
    config = _minimal_config(city_size=16)
    config.mean_trip_distance.value = 12  # in band, bypasses validation
    sim = RideHailSimulation(config)
    assert sim.mean_trip_distance == 8  # 16 // 2


def test_simulation_clamps_value_above_city_size():
    """
    A value above city_size (which the config validator rejects rather than
    caps) is defensively clamped to city_size // 2 by the simulation, not left
    out of range.
    """
    config = _minimal_config(city_size=16)
    config.mean_trip_distance.value = 20  # above city_size, bypasses validation
    sim = RideHailSimulation(config)
    assert sim.mean_trip_distance == 8  # 16 // 2


def test_simulation_preserves_in_range_value():
    """A mean_trip_distance already within range is left unchanged."""
    config = _minimal_config(city_size=16)
    config.mean_trip_distance.value = 6  # <= 16 // 2
    sim = RideHailSimulation(config)
    assert sim.mean_trip_distance == 6


def test_configitem_exposes_max_relation():
    """The ConfigItem carries the declarative constraint used by the web UI."""
    config = _minimal_config(city_size=16)
    assert config.mean_trip_distance.max_relation is MEAN_TRIP_DISTANCE_MAX_RELATION
    assert MEAN_TRIP_DISTANCE_MAX_RELATION["param"] == "city_size"


def test_exported_constraint_matches_enforced_cap():
    """
    The cap the validator enforces equals the one derived from the exported
    relation, so the web UI and Python agree. This is the invariant that keeps
    the two constraints from drifting apart.
    """
    config = _minimal_config(city_size=16)
    city_size = config.city_size.value
    derived_cap = int(city_size * MEAN_TRIP_DISTANCE_MAX_RELATION["fraction"])
    # A value in the cap..city_size band gets capped by the validator.
    _is_valid, enforced_value, _msg = config.mean_trip_distance.validate_value(
        city_size, config
    )
    assert enforced_value == derived_cap == 8


def test_get_slider_config_payload():
    """
    docs/lab/worker.py::get_slider_config exports the structural constraints in
    the camelCase shape the browser consumes: the mean_trip_distance relation
    plus the integer/even flags the Python config enforces.
    """
    import worker

    payload = worker.get_slider_config()
    assert payload["meanTripDistance"] == {
        "integer": True,
        "maxRelativeTo": "citySize",
        "maxFraction": MEAN_TRIP_DISTANCE_MAX_RELATION["fraction"],
    }
    # city_size is an even integer; the browser must impose both.
    assert payload["citySize"] == {"integer": True, "even": True}
    # A plain integer parameter carries just the integer flag.
    assert payload["vehicleCount"] == {"integer": True}
    # Float parameters carry no structural constraint and are omitted.
    assert "price" not in payload


if __name__ == "__main__":
    test_validator_caps_at_half_city_size()
    test_validator_rejects_value_above_city_size()
    test_simulation_caps_at_half_city_size()
    test_simulation_clamps_value_above_city_size()
    test_simulation_preserves_in_range_value()
    test_configitem_exposes_max_relation()
    test_exported_constraint_matches_enforced_cap()
    test_get_slider_config_payload()
    print("All mean_trip_distance validation tests passed.")
