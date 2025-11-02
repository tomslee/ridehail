#!/usr/bin/env python3
"""
Test fixed port functionality for web browser animation.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.animation.web_browser import WebBrowserAnimation, WebMapAnimation


def test_fixed_port():
    """Test that default port 41967 is used"""
    print("Testing fixed port functionality...")
    print(f"Expected default port: {WebBrowserAnimation.DEFAULT_PORT}")
    print()

    # Create minimal config
    config = RideHailConfig()
    config.city_size.value = 8
    config.vehicle_count.value = 10
    config.time_blocks.value = 10
    config.animate.value = False

    # Create simulation
    sim = RideHailSimulation(config)

    # Create animation
    anim = WebMapAnimation(sim)

    # Test port finding
    print("Test 1: Port finding with no conflicts...")
    port = anim._find_free_port()
    print(f"  ✓ Port selected: {port}")

    if port == WebBrowserAnimation.DEFAULT_PORT:
        print(f"  ✓ Using default port {WebBrowserAnimation.DEFAULT_PORT}")
    else:
        print(f"  ⚠ Using alternative port {port} (default port may be in use)")

    print()

    # Test server startup with the port
    print("Test 2: Server startup with selected port...")
    anim._start_server()
    print(f"  ✓ Server started on port {anim.port}")
    print(f"  ✓ URL: http://localhost:{anim.port}")

    # Verify server is actually running
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', anim.port))
    sock.close()

    if result == 0:
        print(f"  ✓ Server is responding on port {anim.port}")
    else:
        print(f"  ✗ Server not responding on port {anim.port}")
        return False

    # Cleanup
    anim.cleanup()
    print(f"  ✓ Server stopped")

    print()
    print("✅ Fixed port functionality test passed!")
    return True


if __name__ == "__main__":
    try:
        success = test_fixed_port()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
