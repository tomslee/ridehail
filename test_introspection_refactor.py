#!/usr/bin/env python3
"""
Test that the introspection-based config loading works correctly.
"""

import sys
from ridehail.config import RideHailConfig


def test_config_loading():
    """Test loading a config file with the refactored introspection approach"""
    print("Testing introspection-based config loading...")
    print("=" * 70)

    # Override sys.argv to simulate command line
    original_argv = sys.argv.copy()
    sys.argv = ["test", "test.config"]

    try:
        # Load config
        config = RideHailConfig()

        # Check that values were loaded from test.config
        print(f"\n✓ Config loaded successfully")
        print(f"  city_size: {config.city_size.value}")
        print(f"  vehicle_count: {config.vehicle_count.value}")
        print(f"  base_demand: {config.base_demand.value}")
        print(f"  pickup_time: {config.pickup_time.value}")
        print(f"  animation: {config.animation.value}")
        print(f"  equilibrate: {config.equilibrate.value}")

        # Verify some expected values from test.config
        assert config.city_size.value == 16, (
            f"Expected city_size=16, got {config.city_size.value}"
        )
        assert config.vehicle_count.value == 32, (
            f"Expected vehicle_count=32, got {config.vehicle_count.value}"
        )

        print(f"\n✓ All config values loaded correctly via introspection")
        print("=" * 70)
        print("SUCCESS: Introspection-based config loading works! ✓")
        return True

    except Exception as e:
        print(f"\n✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False
    finally:
        sys.argv = original_argv


if __name__ == "__main__":
    success = test_config_loading()
    sys.exit(0 if success else 1)
