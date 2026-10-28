"""
Memory that a long run, or a long session, must not accumulate.

- A simulation's memory stays flat once its buffers have filled: finished
  trips are dropped (_collect_garbage) and every history is a fixed-size
  buffer.
- A simulation that is replaced (the next run of a sequence, a Reset in the
  web lab) is freed: nothing module-level keeps it.
- webworker.js holds the current simulation in one PyProxy and never reads
  it as workerPackage.sim, which in Pyodide kept every simulation of the
  session alive.

The long measurements, including the web lab under Pyodide, are in
benchmarks/bench_memory.py and benchmarks/bench_memory_pyodide.mjs.
"""

import gc
import logging
import re
import sys
import tracemalloc
import weakref
from pathlib import Path

from ridehail.config import RideHailConfig
from ridehail.presets import get_preset
from ridehail.simulation import GARBAGE_COLLECTION_INTERVAL, RideHailSimulation

logging.disable(logging.CRITICAL)

ROOT = Path(__file__).resolve().parent.parent
LAB = ROOT / "docs" / "lab"


def make_config(preset, **values):
    """A validated config from a preset plus overrides (as in test_strategy.py)."""
    config = RideHailConfig(use_config_file=False)
    config.animation.value = "none"
    for name, value in {**get_preset(preset), **values}.items():
        item = getattr(config, name)
        item.value = value
        item.explicitly_set = True
    config._convert_config_values_to_enum()
    config._set_parameter_defaults()
    config._validate_all_config_parameters()
    return config


def traced_after(sim, blocks):
    """Run blocks more blocks; the traced memory just after the next trip
    garbage collection, so the trip dict is at the bottom of its sawtooth."""
    for _ in range(blocks):
        sim.next_block()
    while sim.block_index % GARBAGE_COLLECTION_INTERVAL != 1:
        sim.next_block()
    gc.collect()
    return tracemalloc.get_traced_memory()[0]


def test_open_ended_simulation_memory_is_flat():
    """1500 Town blocks after warm-up add (almost) nothing."""
    tracemalloc.start()
    try:
        sim = RideHailSimulation(make_config("town", time_blocks=0))
        start = traced_after(sim, 500)
        end = traced_after(sim, 1500)
    finally:
        tracemalloc.stop()
    # Measured 2026-10-28: about 2 bytes a block
    assert end - start < 64 * 1024


def test_finished_simulations_are_freed():
    """Short simulations one after another, as in a sequence."""
    refs = []
    for _ in range(3):
        sim = RideHailSimulation(make_config("village", time_blocks=60))
        sim.simulate()
        refs.append(weakref.ref(sim))
        del sim
    gc.collect()
    assert [ref() for ref in refs] == [None, None, None]


class Proxy:
    """Stands in for the Pyodide JsProxy of the settings."""

    def __init__(self, values):
        self.values = values

    def to_py(self):
        return dict(self.values)


def test_lab_reset_frees_the_previous_simulation(monkeypatch):
    """worker.py keeps only the current simulation (its module global sim)."""
    monkeypatch.syspath_prepend(str(LAB))
    monkeypatch.setattr(sys, "argv", ["worker.py"])
    import worker
    from test_lab_worker import lab_settings

    w = worker.init_simulation(Proxy(lab_settings()))
    for _ in range(40):
        w.next_frame_map()
    w.follow_vehicle("random")
    refs = (weakref.ref(w), weakref.ref(w.sim))
    del w
    worker.init_simulation(Proxy(lab_settings()))
    gc.collect()
    assert [ref() for ref in refs] == [None, None]


def test_lab_game_shift_is_freed(monkeypatch):
    monkeypatch.syspath_prepend(str(LAB))
    monkeypatch.setattr(sys, "argv", ["worker.py"])
    import worker

    settings = {"market": "normal", "code": "practice", "card": "helper"}
    w = worker.init_game(Proxy(settings))
    for _ in range(60):
        results = w.next_frame_map()
        if results["game"].get("offer"):
            w.resolve_offer(True, False)
    refs = (weakref.ref(w), weakref.ref(w.sim), weakref.ref(w.game))
    del w, results
    worker.init_game(Proxy(settings))
    gc.collect()
    assert [ref() for ref in refs] == [None, None, None]


def test_webworker_never_reads_the_simulation_from_the_module():
    """
    In Pyodide, every attribute read of the module proxy (workerPackage.sim)
    returns a proxy that the module proxy keeps, so each simulation read that
    way stayed in memory for the session. webworker.js holds the current one
    in its own `sim` (newSimulation).
    """
    source = (LAB / "webworker.js").read_text()
    code = "\n".join(
        line for line in source.splitlines() if not line.lstrip().startswith("//")
    )
    assert not re.search(r"workerPackage\.sim\b", code)
