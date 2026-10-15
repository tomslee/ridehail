"""
The end-of-run results (ridehail/results.py, claude/results-output-review.md):
the end state and the [RESULTS] section are built from one layout, report a
result only where it is relevant, and give city-scale results in consistent
units.
"""

import configparser

import pytest

from ridehail.config import RideHailConfig
from ridehail.results import RESULTS_LAYOUT, RideHailSimulationResults
from ridehail.simulation import RideHailSimulation


def run(blocks=300, **values):
    """Run a small city for blocks blocks; return its results."""
    config = RideHailConfig(use_config_file=False)
    settings = {
        "animation": "none",
        "random_number_seed": 7,
        "city_size": 12,
        "vehicle_count": 40,
        "base_demand": 2.0,
        "time_blocks": blocks,
        "results_window": 100,
        **values,
    }
    for name, value in settings.items():
        getattr(config, name).value = value
    config._convert_config_values_to_enum()
    sim = RideHailSimulation(config)
    for _ in range(blocks):
        sim.next_block()
    return RideHailSimulationResults(sim)


def results_section(results):
    """The [RESULTS] section's keys and values, as a config file reader sees them."""
    parser = configparser.RawConfigParser()
    parser.optionxform = str
    parser.read_string(results.format_results_section())
    return dict(parser["RESULTS"])


def reported(results):
    """The end state's (section, key) pairs."""
    return {
        (section, key)
        for section, values in results.get_end_state().items()
        for key in values
    }


def assert_outputs_agree(results):
    """The end state and [RESULTS] list the same results."""
    end_state = results.get_end_state()
    names = {
        row.name
        for section in RESULTS_LAYOUT
        if section.key in end_state
        for row in section.rows
        if row.key in end_state[section.key]
    }
    extras = {"SIM_TIMESTAMP", "SIM_RIDEHAIL_VERSION"}
    assert set(results_section(results)) == names | extras


def test_plain_run_reports_no_optional_results():
    results = run()
    keys = reported(results)
    sections = {section for section, _ in keys}
    assert sections == {
        "simulation",
        "vehicles",
        "trips",
        "income_and_costs",
        "validation",
    }
    assert ("vehicles", "fraction_parked") not in keys
    assert ("trips", "completed_fraction") not in keys
    assert_outputs_agree(results)


@pytest.mark.parametrize("advanced", [True, False])
def test_forward_dispatch_needs_advanced_dispatch(advanced):
    results = run(use_advanced_dispatch=advanced, dispatch_method="forward_dispatch")
    end_state = results.get_end_state()
    assert ("dispatch" in end_state) == advanced
    assert ("TRIP_FORWARD_DISPATCH_FRACTION" in results_section(results)) == advanced
    assert_outputs_agree(results)


def test_cancellations_and_parking_reported_when_possible():
    results = run(max_wait_time=5, idle_vehicles_moving=0.5)
    keys = reported(results)
    assert ("trips", "completed_fraction") in keys
    assert ("vehicles", "fraction_parked") in keys
    assert results.get_end_state()["vehicles"]["fraction_parked"] > 0
    assert_outputs_agree(results)


def test_city_scale_units_agree():
    """
    With two minutes per block: times in minutes (twice the blocks), the
    request rate per minute (as base_demand), so the checks stay near 1.
    """
    results = run(
        use_city_scale=True,
        minutes_per_block=2.0,
        mean_vehicle_speed=30.0,
        base_demand=1.0,
    )
    trips = results.get_end_state()["trips"]
    sim = results.sim
    assert trips["mean_request_rate"] == pytest.approx(sim.display_base_demand)
    blocks = results.measures
    assert trips["mean_ride_time"] == pytest.approx(
        2.0 * blocks["TRIP_DISTANCE_FRACTION"] * sim.city_size, abs=1e-2
    )
    # mean and median wait in the same units: the median is a whole number
    # of blocks, so an even number of minutes
    assert trips["median_wait_time"] % 2 == 0
    validation = results.get_end_state()["validation"]
    assert validation["check_np3_over_rl"] == pytest.approx(1.0, abs=0.15)
    assert validation["check_np2_over_rw"] == pytest.approx(1.0, abs=0.15)
    assert results.unit_label("time") == "minutes"
    assert "times in minutes" in results.format_results_section()


def test_no_results_without_a_full_window():
    results = run(blocks=100, results_window=100)
    assert not results.available()
    assert results.get_end_state() == {}
    assert results.format_results_section() == ""


def test_web_download_uses_the_same_section(monkeypatch):
    """worker.py returns the [RESULTS] text that the desktop writes."""
    import sys
    from pathlib import Path

    lab = Path(__file__).resolve().parent.parent / "docs" / "lab"
    monkeypatch.syspath_prepend(str(lab))
    monkeypatch.setattr(sys, "argv", ["worker.py"])
    import worker
    from test_lab_worker import Proxy, lab_settings

    w = worker.Simulation(Proxy(lab_settings()))
    assert w.get_simulation_results() == ""
    for _ in range(w.sim.results_window + 1):
        w.next_block_stats()
    text = w.get_simulation_results()
    assert text.startswith("[RESULTS]")
    assert "VEHICLE_FRACTION_PARKED" not in text
    assert "TRIP_FORWARD_DISPATCH_FRACTION" not in text
