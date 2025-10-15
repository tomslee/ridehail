#!/usr/bin/env python3
"""
Test config file handling of [RESULTS] section.

This test verifies that:
1. Config files can be written with [RESULTS] sections
2. [RESULTS] sections are ignored when reading config files
3. Multiple simulation runs replace (not append) results sections
4. Results writing is graceful when config file is not writable
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

import unittest
import tempfile
from ridehail.config import RideHailConfig


class TestConfigResultsSection(unittest.TestCase):
    def setUp(self):
        """Create a temporary directory for test config files."""
        self.test_dir = tempfile.mkdtemp()
        self.test_config_path = os.path.join(self.test_dir, "test.config")

    def tearDown(self):
        """Clean up temporary test files."""
        import shutil
        shutil.rmtree(self.test_dir)

    def test_write_results_section_to_config(self):
        """Test that results can be written to config file as [RESULTS] section."""
        # Create a simple config file first
        with open(self.test_config_path, 'w') as f:
            f.write("[DEFAULT]\ncity_size = 8\n")

        # Create mock standardized results
        standardized_results = {
            "SIMULATION_TIMESTAMP": "2025-10-15T14:30:45",
            "RIDEHAIL_VERSION": "0.1.0",
            "VEHICLE_COUNT": 10,
            "TRIP_REQUEST_RATE": 0.5,
            "TRIP_DISTANCE": 3.5
        }

        # Write results to config file
        config = RideHailConfig(use_config_file=False)
        success = config.write_results_section(self.test_config_path, standardized_results)
        self.assertTrue(success)

        # Verify file contains [RESULTS] section
        with open(self.test_config_path, 'r') as f:
            content = f.read()
            self.assertIn("[RESULTS]", content)
            self.assertIn("SIMULATION_TIMESTAMP = 2025-10-15T14:30:45", content)
            self.assertIn("VEHICLE_COUNT", content)
            self.assertIn("TRIP_REQUEST_RATE", content)

    def test_ignore_results_section_when_reading(self):
        """Test that [RESULTS] section is ignored when reading config file."""
        # Create a config file with [RESULTS] section
        config_content = """
[DEFAULT]
city_size = 8
vehicle_count = 4
base_demand = 0.3
time_blocks = 100
results_window = 50
animate = False
random_number_seed = 42

[RESULTS]
SIMULATION_TIMESTAMP = 2025-10-15T10:00:00
VEHICLE_COUNT = 4.5
TRIP_REQUEST_RATE = 0.3
"""
        with open(self.test_config_path, 'w') as f:
            f.write(config_content)

        # Read config file (should ignore RESULTS section)
        config = RideHailConfig(use_config_file=False)
        config.config_file.value = self.test_config_path
        config._set_options_from_config_file(self.test_config_path)

        # Verify config values are from DEFAULT section, not RESULTS
        self.assertEqual(config.city_size.value, 8)
        self.assertEqual(config.vehicle_count.value, 4)
        self.assertEqual(config.base_demand.value, 0.3)

    def test_replace_results_section_on_second_run(self):
        """Test that results section is replaced (not appended) on subsequent runs."""
        # Create initial config file
        with open(self.test_config_path, 'w') as f:
            f.write("[DEFAULT]\ncity_size = 8\n")

        # First results write
        standardized_results1 = {
            "SIMULATION_TIMESTAMP": "2025-10-15T14:00:00",
            "VEHICLE_COUNT": 10
        }
        config = RideHailConfig(use_config_file=False)
        config.write_results_section(self.test_config_path, standardized_results1)

        # Read file and verify first results
        with open(self.test_config_path, 'r') as f:
            content1 = f.read()
            self.assertIn("SIMULATION_TIMESTAMP = 2025-10-15T14:00:00", content1)
            # Count occurrences of [RESULTS] section
            self.assertEqual(content1.count("[RESULTS]"), 1)

        # Second results write (different timestamp)
        standardized_results2 = {
            "SIMULATION_TIMESTAMP": "2025-10-15T15:00:00",
            "VEHICLE_COUNT": 12
        }
        config.write_results_section(self.test_config_path, standardized_results2)

        # Read file and verify second results replaced first
        with open(self.test_config_path, 'r') as f:
            content2 = f.read()
            # Should have new timestamp
            self.assertIn("SIMULATION_TIMESTAMP = 2025-10-15T15:00:00", content2)
            # Should NOT have old timestamp
            self.assertNotIn("SIMULATION_TIMESTAMP = 2025-10-15T14:00:00", content2)
            # Should still only have one [RESULTS] section
            self.assertEqual(content2.count("[RESULTS]"), 1)

    def test_write_results_to_nonexistent_file(self):
        """Test that writing results to nonexistent file returns False."""
        config = RideHailConfig(use_config_file=False)
        fake_path = os.path.join(self.test_dir, "nonexistent.config")

        results_dict = {"VEHICLE_COUNT": 10, "TRIP_REQUEST_RATE": 0.5}
        success = config.write_results_section(fake_path, results_dict)

        self.assertFalse(success)

    def test_write_results_to_readonly_file(self):
        """Test that writing results to read-only file returns False."""
        # Create a config file
        with open(self.test_config_path, 'w') as f:
            f.write("[DEFAULT]\ncity_size = 8\n")

        # Make it read-only
        os.chmod(self.test_config_path, 0o444)

        config = RideHailConfig(use_config_file=False)
        results_dict = {"VEHICLE_COUNT": 10, "TRIP_REQUEST_RATE": 0.5}
        success = config.write_results_section(self.test_config_path, results_dict)

        self.assertFalse(success)

        # Restore write permission for cleanup
        os.chmod(self.test_config_path, 0o644)

    def test_results_section_grouping(self):
        """Test that results are organized into logical groups with comments."""
        # Create simple config file
        with open(self.test_config_path, 'w') as f:
            f.write("[DEFAULT]\ncity_size = 8\n")

        standardized_results = {
            "SIMULATION_TIMESTAMP": "2025-10-15T14:00:00",
            "VEHICLE_COUNT": 10,
            "TRIP_REQUEST_RATE": 0.5,
            "CHECK_P1_P2_P3": 1.0,
            "CONVERGENCE_MAX_RMS_RESIDUAL": 0.01
        }

        config = RideHailConfig(use_config_file=False)
        config.write_results_section(self.test_config_path, standardized_results)

        # Read and verify grouping comments exist
        with open(self.test_config_path, 'r') as f:
            content = f.read()
            self.assertIn("# Simulation metadata", content)
            self.assertIn("# Vehicle metrics", content)
            self.assertIn("# Trip metrics", content)
            self.assertIn("# Validation metrics", content)
            self.assertIn("# Convergence metrics", content)


if __name__ == "__main__":
    unittest.main()
