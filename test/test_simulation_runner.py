"""
SimulationRunner and SimulationOutput (ridehail/simulation_runner.py), and
sequences of simulations. Runs in a temporary directory, since output files
go to ./out and results are written back into the config file.
"""

import json
import logging
import shutil
from pathlib import Path

import pytest

from ridehail.atom import Animation
from ridehail.config import RideHailConfig
from ridehail.sequence import RideHailSimulationSequence
from ridehail.simulation import RideHailSimulation
from ridehail.simulation_runner import SimulationRunner

logging.disable(logging.CRITICAL)

TEST_DIR = Path(__file__).parent


@pytest.fixture
def config_file(tmp_path, monkeypatch):
    """A copy of a test config in an empty working directory."""
    monkeypatch.chdir(tmp_path)
    path = tmp_path / "small.config"
    shutil.copy(TEST_DIR / "city_size_16_simple.config", path)
    return path


def make_config(config_file=None, time_blocks=12, **extra):
    config = RideHailConfig(use_config_file=False)
    config.animation.value = Animation.NONE
    config.time_blocks.value = time_blocks
    config.random_number_seed.value = 5
    config.city_size.value = 8
    config.vehicle_count.value = 10
    config.base_demand.value = 1.0
    config.animation_delay.value = 0.0
    if config_file:
        config.config_file.value = str(config_file)
        config.write_output_files.value = True
    for key, value in extra.items():
        getattr(config, key).value = value
    return config


def test_runs_time_blocks_blocks():
    sim = RideHailSimulation(make_config())
    blocks = []
    SimulationRunner(sim).run(
        display_callback=lambda state, block: blocks.append(block)
    )
    assert blocks == list(range(12))
    assert sim.block_index == 12


def test_restart_is_reported():
    sim = RideHailSimulation(make_config(time_blocks=10))
    calls = []

    def display(state, block):
        calls.append(block)
        if block == 5 and calls.count(5) == 1:
            sim._restart_simulation()

    SimulationRunner(sim).run(display_callback=display)
    assert calls == list(range(6)) + [-1] + list(range(10))


def test_output_files(config_file):
    sim = RideHailSimulation(make_config(config_file))
    sim.simulate()
    (jsonl,) = Path("out").glob("*.jsonl")
    types = [json.loads(line)["type"] for line in jsonl.read_text().splitlines()]
    assert types == ["metadata", "config"] + ["block"] * 12 + ["end_state"]
    (csv,) = Path("out").glob("*.csv")
    assert len(csv.read_text().splitlines()) == 1 + 12  # header and one row a block
    assert "[RESULTS]" in config_file.read_text()


def test_no_output_files_without_write_output_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    RideHailSimulation(make_config()).simulate()
    assert list(tmp_path.iterdir()) == []


def test_sequence_order_and_csv(config_file):
    config = make_config(
        config_file,
        run_sequence=True,
        vehicle_count_increment=5,
        vehicle_count_max=15,
        request_rate_increment=0.5,
        request_rate_max=1.5,
        # End-state measures need at least results_window blocks
        results_window=10,
        smoothing_window=5,
    )
    sequence = RideHailSimulationSequence(config)
    assert list(sequence.parameters()) == [
        (rate, count, config.inhomogeneity.value, config.platform_commission.value)
        for rate in (1.0, 1.5)
        for count in (10, 15)
    ]
    sequence.run_sequence(config)
    assert len(sequence.vehicle_p1_fraction) == 4
    (csv,) = Path("out").glob("*.csv")
    assert len(csv.read_text().splitlines()) == 1 + 4  # header and one row a run
