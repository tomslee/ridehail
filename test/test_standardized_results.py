#!/usr/bin/env python3
"""
Test the get_standardized_results() method in RideHailSimulationResults.

This test verifies that:
1. The method returns a flat dictionary with standardized keys
2. History enum names are used where applicable
3. Metadata fields are populated correctly
4. Values match those in the hierarchical end_state
"""

import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import unittest
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.atom import History


class TestStandardizedResults(unittest.TestCase):
    def setUp(self):
        """Create a simple simulation and run it to get results."""
        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 4
        config.vehicle_count.value = 2
        config.base_demand.value = 0.2
        config.time_blocks.value = 100
        config.results_window.value = 50
        config.animate.value = False
        config.random_number_seed.value = 42

        sim = RideHailSimulation(config)
        self.results = sim.simulate()

    def test_standardized_results_structure(self):
        """Test that get_standardized_results() returns a flat dictionary."""
        standardized = self.results.get_standardized_results(
            timestamp="2025-10-15T14:30:45", duration_seconds=10.5
        )

        # Should be a dictionary
        self.assertIsInstance(standardized, dict)

        # Should be flat (no nested dicts)
        for key, value in standardized.items():
            self.assertNotIsInstance(
                value, dict, f"Key '{key}' has nested dict value, should be flat"
            )

    def test_metadata_fields(self):
        """Test that metadata fields are present and correct."""
        standardized = self.results.get_standardized_results(
            timestamp="2025-10-15T14:30:45", duration_seconds=10.5
        )

        # Check metadata fields exist
        self.assertIn("SIMULATION_TIMESTAMP", standardized)
        self.assertIn("RIDEHAIL_VERSION", standardized)
        self.assertIn("SIMULATION_DURATION_SECONDS", standardized)
        self.assertIn("BLOCKS_SIMULATED", standardized)
        self.assertIn("BLOCKS_ANALYZED", standardized)

        # Check metadata values
        self.assertEqual(standardized["SIMULATION_TIMESTAMP"], "2025-10-15T14:30:45")
        self.assertEqual(standardized["SIMULATION_DURATION_SECONDS"], 10.5)
        self.assertEqual(standardized["BLOCKS_SIMULATED"], 100)

    def test_history_enum_keys(self):
        """Test that History enum names are used as keys where applicable."""
        standardized = self.results.get_standardized_results()

        # These keys should use History enum names
        self.assertIn(History.VEHICLE_COUNT.name, standardized)
        self.assertIn(History.TRIP_REQUEST_RATE.name, standardized)
        self.assertIn(History.TRIP_DISTANCE.name, standardized)
        self.assertIn(History.TRIP_WAIT_TIME.name, standardized)
        self.assertIn(History.CONVERGENCE_MAX_RMS_RESIDUAL.name, standardized)

        # Verify actual key strings
        self.assertIn("VEHICLE_COUNT", standardized)
        self.assertIn("TRIP_REQUEST_RATE", standardized)
        self.assertIn("TRIP_DISTANCE", standardized)
        self.assertIn("TRIP_WAIT_TIME", standardized)
        self.assertIn("CONVERGENCE_MAX_RMS_RESIDUAL", standardized)

    def test_computed_metric_keys(self):
        """Test that computed metrics (without History enum) are present."""
        standardized = self.results.get_standardized_results()

        # These are computed metrics without History enum equivalents
        self.assertIn("VEHICLE_FRACTION_P1", standardized)
        self.assertIn("VEHICLE_FRACTION_P2", standardized)
        self.assertIn("VEHICLE_FRACTION_P3", standardized)
        self.assertIn("TRIP_MEAN_WAIT_FRACTION", standardized)

        # Validation metrics
        self.assertIn("CHECK_P1_P2_P3", standardized)
        self.assertIn("CHECK_NP3_OVER_RL", standardized)
        self.assertIn("CHECK_NP2_OVER_RW", standardized)

    def test_values_match_end_state(self):
        """Test that standardized values match hierarchical end_state values."""
        standardized = self.results.get_standardized_results()

        # Vehicle metrics
        self.assertEqual(
            standardized[History.VEHICLE_COUNT.name],
            self.results.end_state["vehicles"]["mean_count"],
        )
        self.assertEqual(
            standardized["VEHICLE_FRACTION_P1"],
            self.results.end_state["vehicles"]["fraction_p1"],
        )
        self.assertEqual(
            standardized["VEHICLE_FRACTION_P3"],
            self.results.end_state["vehicles"]["fraction_p3"],
        )

        # Trip metrics
        self.assertEqual(
            standardized[History.TRIP_REQUEST_RATE.name],
            self.results.end_state["trips"]["mean_request_rate"],
        )
        self.assertEqual(
            standardized[History.TRIP_DISTANCE.name],
            self.results.end_state["trips"]["mean_distance"],
        )

        # Convergence
        self.assertEqual(
            standardized[History.CONVERGENCE_MAX_RMS_RESIDUAL.name],
            self.results.end_state["simulation"]["max_rms_residual"],
        )

    def test_wait_time_calculation(self):
        """Test that TRIP_WAIT_TIME is correctly calculated from wait_fraction and distance."""
        standardized = self.results.get_standardized_results()

        expected_wait_time = round(
            self.results.end_state["trips"]["mean_wait_fraction"]
            * self.results.end_state["trips"]["mean_distance"],
            3,
        )

        self.assertEqual(standardized[History.TRIP_WAIT_TIME.name], expected_wait_time)

    def test_automatic_timestamp(self):
        """Test that timestamp is auto-generated if not provided."""
        standardized = self.results.get_standardized_results()

        # Should have timestamp even though we didn't provide one
        self.assertIn("SIMULATION_TIMESTAMP", standardized)
        self.assertIsInstance(standardized["SIMULATION_TIMESTAMP"], str)
        # Should be ISO format (contains 'T' and maybe ':')
        self.assertIn("T", standardized["SIMULATION_TIMESTAMP"])

if __name__ == "__main__":
    unittest.main()
