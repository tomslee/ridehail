"""
Fixed-choice options (enums such as --animation, and --preset): unique-prefix
matching, helpful errors, and "-<option> help" listings, on the command line
and in config files.
"""

import os
import subprocess
import sys
from pathlib import Path

import pytest

from ridehail.atom import Animation, DispatchMethod, Equilibration
from ridehail.config import RideHailConfig, ConfigItem, find_option, match_choice

REPO_ROOT = Path(__file__).resolve().parent.parent


def _run_cli(args, timeout=120):
    return subprocess.run(
        [sys.executable, "-m", "ridehail", *args],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        timeout=timeout,
    )


class TestMatchChoice:
    CHOICES = ["stats", "stats_bar", "terminal_map", "terminal_stats", "text"]

    def test_exact_match_beats_prefix(self):
        assert match_choice("stats", self.CHOICES) == "stats"

    def test_unique_prefix(self):
        assert match_choice("terminal_m", self.CHOICES) == "terminal_map"

    def test_case_and_space_insensitive(self):
        assert match_choice("  Stats_Bar ", self.CHOICES) == "stats_bar"

    def test_ambiguous_prefix_lists_candidates(self):
        with pytest.raises(ValueError, match="ambiguous.*terminal_map, terminal_stats"):
            match_choice("terminal", self.CHOICES)

    def test_typo_suggests_and_lists_all(self):
        with pytest.raises(ValueError) as e:
            match_choice("termnal_map", self.CHOICES)
        assert "Did you mean terminal_map?" in str(e.value)
        assert "Valid values: stats, stats_bar" in str(e.value)

    def test_empty_is_invalid(self):
        with pytest.raises(ValueError):
            match_choice("", self.CHOICES)


class TestConfigItem:
    def test_parse_choice_returns_enum(self):
        item = RideHailConfig.equilibration
        assert item.parse_choice("p") == Equilibration.PRICE
        assert item.parse_choice("W") == Equilibration.WAIT_FRACTION

    def test_every_enum_value_described(self):
        for enum_class in (Animation, DispatchMethod, Equilibration):
            for member in enum_class:
                assert member.description

    def test_help_listing_marks_default(self):
        text = RideHailConfig.animation.format_value_descriptions()
        assert "terminal_map" in text
        assert "text" in text and "[default]" in text


class TestFindOption:
    ITEMS = [
        item
        for item in vars(RideHailConfig).values()
        if isinstance(item, ConfigItem) and item.active
    ]

    def test_long_name_and_short_form(self):
        assert find_option("city_size", self.ITEMS).name == "city_size"
        assert find_option("cs", self.ITEMS).name == "city_size"
        assert find_option("--city-size", self.ITEMS).name == "city_size"

    def test_negated_flag(self):
        assert find_option("--no-use_city_scale", self.ITEMS).name == "use_city_scale"

    def test_unique_prefix(self):
        assert find_option("inhomogeneous", self.ITEMS).name == (
            "inhomogeneous_destinations"
        )

    def test_exact_name_beats_prefix(self):
        assert find_option("inhomogeneity", self.ITEMS).name == "inhomogeneity"

    def test_ambiguous_prefix_lists_candidates(self):
        with pytest.raises(ValueError, match="ambiguous.*inhomogeneity_max"):
            find_option("inhomog", self.ITEMS)

    def test_typo_suggests(self):
        with pytest.raises(ValueError, match="Did you mean dispatch_method"):
            find_option("dispatch_metod", self.ITEMS)


class TestLongHelp:
    def test_includes_help_description_and_range(self):
        text = RideHailConfig.city_size.format_long_help()
        assert "-cs, --city_size" in text
        assert RideHailConfig.city_size.help in text
        assert "The grid is a square" in text
        assert "Range: 2 to 200" in text

    def test_enum_values_listed_once_with_default(self):
        text = RideHailConfig.animation.format_long_help()
        assert text.count("terminal_map") == 1
        assert "[default]" in text


class TestCommandLine:
    def test_help_option_describes_one_option(self):
        result = _run_cli(["-h", "cs"])
        assert result.returncode == 0
        assert "The grid is a square" in result.stdout
        assert "--vehicle_count" not in result.stdout

    def test_plain_help_unchanged(self):
        result = _run_cli(["-h"])
        assert result.returncode == 0
        assert "--vehicle_count" in result.stdout
        assert "ridehail -h OPTION" in result.stdout

    def test_help_option_unknown_errors(self):
        result = _run_cli(["--help", "citysize"])
        assert result.returncode == 2
        assert "Did you mean city_size?" in result.stderr

    def test_help_lists_values(self):
        result = _run_cli(["-a", "help"])
        assert result.returncode == 0
        for member in Animation:
            assert member.value in result.stdout

    def test_ambiguous_prefix_errors(self):
        result = _run_cli(["-a", "terminal"])
        assert result.returncode == 2
        assert "ambiguous" in result.stderr
        assert "-a help" in result.stderr

    def test_prefix_accepted(self, tmp_path):
        config_file = tmp_path / "out.config"
        result = _run_cli(["-wc", str(config_file), "-e", "pr", "-a", "terminal_m"])
        assert result.returncode == 0, result.stderr
        text = config_file.read_text()
        assert "equilibration = price" in text
        assert "animation = terminal_map" in text


class TestConfigFile:
    def _write(self, tmp_path, **values):
        config_file = tmp_path / "test.config"
        assert (
            _run_cli(["-wc", str(config_file), "-cs", "8", "-vc", "6"]).returncode == 0
        )
        lines = []
        for line in config_file.read_text().splitlines():
            key = line.split("=")[0].strip()
            if key in values:
                line = f"{key} = {values[key]}"
            lines.append(line)
        config_file.write_text("\n".join(lines) + "\n")
        return config_file

    def test_prefix_in_config_file(self, tmp_path):
        config_file = self._write(tmp_path, equilibration="WAIT", animation="none")
        out_file = tmp_path / "resolved.config"
        result = _run_cli([str(config_file), "-wc", str(out_file)])
        assert result.returncode == 0, result.stderr
        assert "equilibration = wait_fraction" in out_file.read_text()

    def test_invalid_value_in_config_file_errors(self, tmp_path):
        config_file = self._write(tmp_path, animation="terminal_mpa")
        result = _run_cli([str(config_file)])
        assert result.returncode == 1
        assert "Did you mean terminal_map?" in result.stderr
        assert "in the config file" in result.stderr


class TestShellCompletion:
    """Simulate the request a registered shell hook makes (argcomplete protocol)."""

    def _complete(self, tmp_path, line, shell="bash"):
        out_file = tmp_path / "completions"
        env = {
            **os.environ,
            "_ARGCOMPLETE": "1",
            "_ARGCOMPLETE_SHELL": shell,
            "_ARGCOMPLETE_IFS": "\n",
            "_ARGCOMPLETE_STDOUT_FILENAME": str(out_file),
            "COMP_LINE": line,
            "COMP_POINT": str(len(line)),
        }
        subprocess.run(
            [sys.executable, "-m", "ridehail"],
            cwd=str(REPO_ROOT),
            env=env,
            capture_output=True,
            timeout=60,
        )
        return out_file.read_text().split("\n")

    def test_completes_enum_prefix(self, tmp_path):
        completions = self._complete(tmp_path, "ridehail -a terminal_s")
        assert sorted(c.strip() for c in completions) == [
            "terminal_sequence",
            "terminal_stats",
        ]

    def test_completes_help_option_names(self, tmp_path):
        completions = self._complete(tmp_path, "ridehail -h city_")
        assert [c.strip() for c in completions] == ["city_size"]

    def test_zsh_gets_descriptions(self, tmp_path):
        completions = self._complete(tmp_path, "ridehail -e ", shell="zsh")
        assert f"price:{Equilibration.PRICE.description}" in completions
