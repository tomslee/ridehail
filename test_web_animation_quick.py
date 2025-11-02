#!/usr/bin/env python3
"""
Quick test to verify web animation starts without hanging.
Tests that the server starts and config is prepared correctly.
"""

import sys
import signal
import threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.animation.web_browser import WebMapAnimation


def test_server_startup():
    """Test that server starts and shuts down cleanly"""
    print("Testing web animation server startup...")

    # Create config
    config = RideHailConfig()
    config.city_size.value = 8
    config.vehicle_count.value = 10
    config.time_blocks.value = 10
    config.animate.value = False

    # Create simulation
    sim = RideHailSimulation(config)

    # Create animation
    anim = WebMapAnimation(sim)

    # Prepare config (this should work)
    print("  Preparing configuration...")
    config_file = anim._prepare_config()
    print(f"  ✓ Config created: {config_file}")

    # Start server (this should work)
    print("  Starting HTTP server...")
    anim._start_server()
    print(f"  ✓ Server started on port {anim.port}")
    print(f"  ✓ URL would be: http://localhost:{anim.port}/?chartType=map&autoLoad=cli_config.json")

    # Cleanup immediately
    print("  Cleaning up...")
    anim.cleanup()
    print("  ✓ Cleanup complete")

    print("\n✅ Server startup test passed!")
    return True


if __name__ == "__main__":
    try:
        success = test_server_startup()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
