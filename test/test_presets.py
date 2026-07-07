"""
Tests for named presets (ridehail/presets.py) and the --preset command-line
option added to the config system.

Covers:
- get_preset() data: merge of shared + per-preset values, unknown-name error.
- _apply_preset(): sets ConfigItem values and marks them explicitly set.
- Precedence: command-line flags override preset values.
- End-to-end CLI: `python -m ridehail --preset ...` resolves and runs.
- Web bridge: docs/lab/worker.py::get_presets() exposes the same values to the
  browser (Phase 2 single-source-of-truth), keyed by JS camelCase name.
"""

import configparser
import importlib.util
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

from ridehail.config import RideHailConfig
from ridehail.presets import PRESET_NAMES, PRESET_SHARED, PRESETS, get_preset

REPO_ROOT = Path(__file__).resolve().parent.parent


def _load_worker_module():
    """Import docs/lab/worker.py directly (it is not on the package path)."""
    worker_path = REPO_ROOT / "docs" / "lab" / "worker.py"
    spec = importlib.util.spec_from_file_location("lab_worker", worker_path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


# ---------------------------------------------------------------------------
# get_preset() data
# ---------------------------------------------------------------------------
class TestGetPreset:
    def test_names(self):
        assert PRESET_NAMES == ["village", "town", "city"]

    @pytest.mark.parametrize("name", PRESET_NAMES)
    def test_merges_shared_and_specific(self, name):
        preset = get_preset(name)
        # Shared economics present
        for key, value in PRESET_SHARED.items():
            assert preset[key] == value
        # Per-preset geometry present
        for key, value in PRESETS[name].items():
            assert preset[key] == value

    def test_specific_overrides_shared(self):
        # No key should collide, but if one did, per-preset wins by construction.
        merged = get_preset("village")
        expected_keys = set(PRESET_SHARED) | set(PRESETS["village"])
        assert set(merged) == expected_keys

    def test_returns_new_dict(self):
        a = get_preset("town")
        a["city_size"] = -999
        b = get_preset("town")
        assert b["city_size"] == PRESETS["town"]["city_size"]

    def test_unknown_name_raises(self):
        with pytest.raises(ValueError, match="Unknown preset"):
            get_preset("metropolis")

    def test_village_geometry_matches_web(self):
        # Guards against silent drift from docs/lab/js/config.js.
        v = get_preset("village")
        assert v["city_size"] == 8
        assert v["vehicle_count"] == 6
        assert v["base_demand"] == 0.5
        assert v["inhomogeneity"] == 0.0
        assert v["per_hour_opportunity_cost"] == 13.0
        assert v["base_fare"] == 3.0


# ---------------------------------------------------------------------------
# _apply_preset() on a config object
# ---------------------------------------------------------------------------
class TestApplyPreset:
    def test_sets_values_and_marks_explicit(self):
        config = RideHailConfig(use_config_file=False)
        config._apply_preset("town")
        assert config.city_size.value == 24
        assert config.vehicle_count.value == 120
        assert config.base_demand.value == 5.0
        assert config.per_hour_opportunity_cost.value == 6.0
        assert config.city_size.explicitly_set is True

    def test_does_not_touch_mode_or_equilibration(self):
        # A preset only sets starting values; mode/equilibration stay at defaults
        # so they remain independent, composable flags.
        config = RideHailConfig(use_config_file=False)
        before_ucs = config.use_city_scale.value
        before_eq = config.equilibration.value
        config._apply_preset("city")
        assert config.use_city_scale.value == before_ucs
        assert config.equilibration.value == before_eq


# ---------------------------------------------------------------------------
# End-to-end CLI: resolution, precedence, and a real run
# ---------------------------------------------------------------------------
def _run_cli(args, timeout=120):
    return subprocess.run(
        [sys.executable, "-m", "ridehail", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def _resolved_config(args):
    """Run with -wc to dump the fully resolved config, return it parsed."""
    tmp = Path(tempfile.mkdtemp(prefix="preset_test_"))
    cfg = tmp / "resolved.config"
    result = _run_cli([*args, "-a", "none", "-wc", str(cfg)])
    assert result.returncode == 0, result.stderr
    parsed = configparser.RawConfigParser()
    parsed.read(cfg)
    return parsed


class TestCli:
    def test_invalid_preset_errors(self):
        result = _run_cli(["--preset", "bogus", "-a", "none"])
        assert result.returncode != 0
        assert "invalid choice" in result.stderr

    def test_resolves_preset_values(self):
        cfg = _resolved_config(["--preset", "village"])
        assert cfg["DEFAULT"].getint("city_size") == 8
        assert cfg["DEFAULT"].getint("vehicle_count") == 6
        assert cfg["DEFAULT"].getfloat("base_demand") == pytest.approx(0.5)
        assert cfg["CITY_SCALE"].getfloat("base_fare") == pytest.approx(3.0)

    def test_command_line_overrides_preset(self):
        # Precedence: defaults < preset < config file < command line.
        cfg = _resolved_config(["--preset", "city", "-cs", "40"])
        assert cfg["DEFAULT"].getint("city_size") == 40  # overridden
        assert cfg["DEFAULT"].getint("vehicle_count") == 1200  # from preset

    def test_preset_run_produces_valid_phases(self):
        # A short headless Village run: idle fraction stays positive (P1 > 0)
        # and phases sum to 1. Village is tiny, so this is fast.
        tmp = Path(tempfile.mkdtemp(prefix="preset_run_"))
        cfg = tmp / "v.config"
        write = _run_cli(
            [
                "--preset",
                "village",
                "-b",
                "200",
                "-rw",
                "100",
                "-rns",
                "307",
                "-a",
                "none",
                "-wc",
                str(cfg),
            ]
        )
        assert write.returncode == 0, write.stderr
        run = _run_cli([str(cfg), "-a", "none", "-ad", "0"])
        assert run.returncode == 0, run.stderr
        parsed = configparser.RawConfigParser()
        parsed.read(cfg)
        r = parsed["RESULTS"]
        p1 = float(r["VEHICLE_FRACTION_P1"])
        p2 = float(r["VEHICLE_FRACTION_P2"])
        p3 = float(r["VEHICLE_FRACTION_P3"])
        assert p1 > 0.0, "Village idle fraction P1 must stay positive"
        assert p1 + p2 + p3 == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------------
# Web bridge: docs/lab/worker.py::get_presets() (Phase 2 single source of truth)
# ---------------------------------------------------------------------------
class TestWebGetPresets:
    @pytest.fixture(scope="class")
    def presets(self):
        worker = _load_worker_module()
        return worker.get_presets(), worker.PARAM_NAME_MAP

    def test_has_all_scales(self, presets):
        result, _ = presets
        assert set(result) == set(PRESET_NAMES)

    def test_values_match_python_source(self, presets):
        # Every camelCase value the browser receives must equal the Python
        # get_preset() value, so the web app and CLI can never drift.
        result, param_map = presets
        for name in PRESET_NAMES:
            py = get_preset(name)
            for py_name, value in py.items():
                js_name = param_map.get(py_name)
                if js_name is None:
                    # No web control (e.g. minutes_per_block): must be omitted.
                    assert js_name not in result[name]
                    continue
                assert result[name][js_name] == value

    def test_village_camelcase(self, presets):
        result, _ = presets
        village = result["village"]
        assert village["citySize"] == 8
        assert village["vehicleCount"] == 6
        assert village["requestRate"] == 0.5
        assert village["inhomogeneity"] == 0.0
        assert village["perHourOpportunityCost"] == 13.0
        assert village["baseFare"] == 3.0

    def test_omits_params_without_web_control(self, presets):
        # minutes_per_block is in the preset but has no PARAM_NAME_MAP entry.
        result, _ = presets
        assert "minutesPerBlock" not in result["village"]
