"""
Regression tests for ridehail simulation.

Tests run simulations with known configurations and compare results to expected values
stored in the [RESULTS] section of config files.

Usage:
    # Run all regression tests
    pytest test/test_regression.py

    # Run specific config test
    pytest test/test_regression.py -k city

    # Update expected results (after intentional simulation changes)
    pytest test/test_regression.py --update-expected

    # Verbose output showing all comparisons
    pytest test/test_regression.py -v
"""

import configparser
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple

import pytest


# Test directory containing config files
TEST_DIR = Path(__file__).parent


def collect_test_configs() -> List[Path]:
    """
    Discover all .config files in the test directory.

    Returns:
        List of Path objects for each config file found
    """
    config_files = list(TEST_DIR.glob("*.config"))
    # Sort for consistent test ordering
    return sorted(config_files)


def extract_results_section(config_path: Path) -> Dict[str, str]:
    """
    Extract the [RESULTS] section from a config file.

    Args:
        config_path: Path to the config file

    Returns:
        Dictionary mapping result keys to values (only uppercase metric keys)
    """
    # Read with case-sensitive keys
    config = configparser.RawConfigParser()
    config.read(config_path)

    if "RESULTS" not in config:
        return {}

    # Only extract keys that are actual metrics
    # ConfigParser lowercases all keys, so we check for known prefixes
    results = {}
    for key, value in config["RESULTS"].items():
        # Only include keys that start with known metric prefixes
        if (
            key.startswith("sim_")
            or key.startswith("vehicle_")
            or key.startswith("trip_")
            or key.startswith("check_")
        ):
            results[key] = value

    return results


def run_simulation_to_temp(config_path: Path) -> Path:
    """
    Copy config file to temporary location and run simulation on the copy.

    Args:
        config_path: Path to the original config file

    Returns:
        Path to the temporary config file with simulation results
    """
    # Create a temporary file with the same name
    temp_dir = Path(tempfile.mkdtemp(prefix="ridehail_test_"))
    temp_config = temp_dir / config_path.name

    # Copy the config file
    shutil.copy2(config_path, temp_config)

    # Run the simulation with no animation and no delay
    cmd = [
        "python",
        "-m",
        "ridehail",
        str(temp_config),
        "-as",
        "none",
        "-ad",
        "0",
    ]

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=300,  # 5 minute timeout
    )

    if result.returncode != 0:
        # Clean up and raise error
        shutil.rmtree(temp_dir)
        raise RuntimeError(
            f"Simulation failed for {config_path.name}:\n"
            f"STDOUT: {result.stdout}\n"
            f"STDERR: {result.stderr}"
        )

    return temp_config


def get_metric_type(key: str) -> str:
    """
    Determine the type of metric for comparison purposes.

    Args:
        key: Metric key from RESULTS section (lowercase from ConfigParser)

    Returns:
        One of: 'exclude', 'exact', 'float', 'version'
    """
    # Metrics to exclude from comparison (always different)
    if key in [
        "sim_timestamp",
        "sim_duration_seconds",
    ]:
        return "exclude"

    # Version should warn but not fail if different
    if key == "sim_ridehail_version":
        return "version"

    # Integer metrics that should match exactly
    if key in [
        "sim_blocks_simulated",
        "sim_blocks_analyzed",
    ]:
        return "exact"

    # All other metrics are floating-point
    return "float"


def compare_results(
    expected: Dict[str, str],
    actual: Dict[str, str],
    rel_tol: float = 0.001,
    abs_tol: float = 0.001,
) -> Tuple[bool, List[str]]:
    """
    Compare expected and actual results with appropriate tolerances.

    Args:
        expected: Expected results from original config file
        actual: Actual results from simulation run
        rel_tol: Relative tolerance for floating-point comparison (default 0.1%)
        abs_tol: Absolute tolerance for floating-point comparison

    Returns:
        Tuple of (all_passed, failure_messages)
    """
    failures = []
    version_warnings = []

    # Check that we have results to compare
    if not expected:
        failures.append("No expected results found in config file [RESULTS] section")
        return False, failures

    if not actual:
        failures.append("No actual results found after simulation run")
        return False, failures

    # Check for missing or extra keys
    expected_keys = set(expected.keys())
    actual_keys = set(actual.keys())

    # Exclude keys we don't want to compare
    comparable_expected = {
        k for k in expected_keys if get_metric_type(k) != "exclude"
    }
    comparable_actual = {k for k in actual_keys if get_metric_type(k) != "exclude"}

    missing_keys = comparable_expected - comparable_actual
    extra_keys = comparable_actual - comparable_expected

    if missing_keys:
        failures.append(f"Missing metrics in actual results: {sorted(missing_keys)}")

    if extra_keys:
        # Extra keys are not a failure, just informational
        version_warnings.append(
            f"New metrics in actual results: {sorted(extra_keys)}"
        )

    # Compare each metric
    for key in sorted(comparable_expected):
        if key not in actual:
            continue  # Already reported as missing

        metric_type = get_metric_type(key)
        expected_val = expected[key]
        actual_val = actual[key]

        if metric_type == "version":
            if expected_val != actual_val:
                version_warnings.append(
                    f"Version mismatch (non-fatal): expected {expected_val}, "
                    f"got {actual_val}"
                )
            continue

        if metric_type == "exact":
            # Integer comparison - must match exactly
            try:
                exp_int = int(float(expected_val))
                act_int = int(float(actual_val))
                if exp_int != act_int:
                    failures.append(
                        f"{key}:\n"
                        f"  Expected: {exp_int}\n"
                        f"  Actual:   {act_int}\n"
                        f"  Diff:     {act_int - exp_int:+d}"
                    )
            except ValueError:
                failures.append(
                    f"{key}: Could not parse as integer "
                    f"(expected={expected_val}, actual={actual_val})"
                )
            continue

        if metric_type == "float":
            # Floating-point comparison with tolerance
            try:
                exp_float = float(expected_val)
                act_float = float(actual_val)

                # Check if values are close
                abs_diff = abs(act_float - exp_float)
                rel_diff = abs_diff / abs(exp_float) if exp_float != 0 else abs_diff

                if abs_diff > abs_tol and rel_diff > rel_tol:
                    rel_pct = rel_diff * 100
                    failures.append(
                        f"{key}:\n"
                        f"  Expected: {exp_float:.6g}\n"
                        f"  Actual:   {act_float:.6g}\n"
                        f"  Diff:     {act_float - exp_float:+.6g} "
                        f"({rel_pct:+.2f}%)"
                    )
            except ValueError:
                failures.append(
                    f"{key}: Could not parse as float "
                    f"(expected={expected_val}, actual={actual_val})"
                )
            continue

    # Print version warnings if any
    if version_warnings:
        for warning in version_warnings:
            print(f"\nWARNING: {warning}")

    return len(failures) == 0, failures


def update_expected_results(config_path: Path, new_results: Dict[str, str]) -> None:
    """
    Update the [RESULTS] section in a config file with new expected values.

    Args:
        config_path: Path to the config file to update
        new_results: Dictionary of new result values to write
    """
    # Read the entire config
    config = configparser.ConfigParser()
    config.read(config_path)

    # Update the RESULTS section
    if "RESULTS" not in config:
        config.add_section("RESULTS")

    # Clear existing results and add new ones
    config.remove_section("RESULTS")
    config.add_section("RESULTS")

    for key, value in sorted(new_results.items()):
        config.set("RESULTS", key, value)

    # Write back to the file
    with open(config_path, "w") as f:
        config.write(f)

    print(f"Updated expected results in {config_path.name}")


@pytest.mark.regression
@pytest.mark.parametrize("config_file", collect_test_configs())
def test_simulation_regression(config_file: Path, request):
    """
    Run simulation and compare results to expected values.

    This test:
    1. Extracts expected results from the original config file
    2. Copies the config to a temporary location
    3. Runs the simulation on the temporary config
    4. Extracts actual results from the temporary config
    5. Compares expected vs. actual results with appropriate tolerances
    6. Cleans up the temporary file

    Args:
        config_file: Path to the config file to test
        request: pytest request fixture (provides access to command-line options)
    """
    update_mode = request.config.getoption("--update-expected")

    if update_mode:
        # Update mode: run simulation and update original config
        print(f"\nUpdating expected results for {config_file.name}")
        temp_config = run_simulation_to_temp(config_file)

        try:
            new_results = extract_results_section(temp_config)
            update_expected_results(config_file, new_results)
        finally:
            # Clean up temporary files
            shutil.rmtree(temp_config.parent)

        # Test passes automatically in update mode
        return

    # Normal test mode: compare results
    print(f"\nTesting {config_file.name}")

    # Extract expected results
    expected_results = extract_results_section(config_file)

    if not expected_results:
        pytest.skip(
            f"No [RESULTS] section found in {config_file.name}. "
            f"Run with --update-expected to generate expected results."
        )

    # Run simulation on temporary copy
    temp_config = run_simulation_to_temp(config_file)

    try:
        # Extract actual results
        actual_results = extract_results_section(temp_config)

        # Compare results
        passed, failures = compare_results(expected_results, actual_results)

        if not passed:
            failure_msg = (
                f"\n{'=' * 60}\n"
                f"REGRESSION TEST FAILURE: {config_file.name}\n"
                f"{'=' * 60}\n"
            )
            failure_msg += "\n".join(failures)
            failure_msg += (
                f"\n{'=' * 60}\n"
                f"To update expected results, run:\n"
                f"  pytest test/test_regression.py --update-expected -k {config_file.stem}\n"
                f"{'=' * 60}\n"
            )
            pytest.fail(failure_msg, pytrace=False)

    finally:
        # Clean up temporary files
        shutil.rmtree(temp_config.parent)


if __name__ == "__main__":
    # Allow running directly for debugging
    import sys

    if "--update-expected" in sys.argv:
        print("Update mode enabled")

    pytest.main([__file__, "-v"] + sys.argv[1:])
