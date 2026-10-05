"""
The Textual apps' controls, without running an app (no terminal output):
they act through SimulationControls and never create a KeyboardHandler,
which would switch the terminal to cbreak mode underneath Textual.
"""

import logging

import pytest

pytest.importorskip("textual")

from ridehail.config import RideHailConfig  # noqa: E402
from ridehail.keyboard import KeyboardHandler  # noqa: E402
from ridehail.simulation import RideHailSimulation  # noqa: E402

logging.disable(logging.CRITICAL)


@pytest.fixture
def app(monkeypatch):
    def no_terminal(self, *args, **kwargs):
        raise AssertionError("a Textual app created a KeyboardHandler")

    monkeypatch.setattr(KeyboardHandler, "__init__", no_terminal)
    from ridehail.animation.terminal_base import RidehailTextualApp

    config = RideHailConfig(use_config_file=False)
    config.animation.value = "none"
    config.vehicle_count.value = 10
    config.base_demand.value = 1.0
    return RidehailTextualApp(RideHailSimulation(config))


def test_live_changes(app):
    app.action_increase_vehicles()
    app.action_increase_demand()
    assert app.sim.target_state == {"vehicle_count": 11, "base_demand": 1.1}


def test_pause_and_step(app):
    app.action_pause()
    assert app.is_paused and app.controls.is_paused
    app.controls.handle_ui_action("step")
    assert app.controls.should_step
