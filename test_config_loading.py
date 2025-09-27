#!/usr/bin/env python3
"""
Test that config loading works with validation
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "."))

from ridehail.config import RideHailConfig


def test_config_loading():
    """Test loading a real config file"""
    try:
        # Mock sys.argv for testing
        original_argv = sys.argv
        sys.argv = ["test", "test.config"]

        config = RideHailConfig()
        print(f"✓ Successfully loaded config file: test.config")
        print(f"  - city_size: {config.city_size.value}")
        print(f"  - vehicle_count: {config.vehicle_count.value}")
        print(f"  - base_demand: {config.base_demand.value}")
        print(f"  - inhomogeneity: {config.inhomogeneity.value}")

        return True

    except Exception as e:
        print(f"✗ Config loading failed: {e}")
        import traceback

        traceback.print_exc()
        return False

    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    print("=== Testing Config Loading with Validation ===")
    success = test_config_loading()
    sys.exit(0 if success else 1)
