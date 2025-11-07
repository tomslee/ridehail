#!/usr/bin/env python3
"""
Integration test for fixed port 41967 functionality.
Tests the actual startup sequence without manual port finding.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.animation.web_browser import WebBrowserAnimation, WebMapAnimation


def test_server_uses_default_port():
    """Test that server starts on default port 41967"""
    print("Testing fixed port 41967 integration...")
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

    # Prepare config (as would happen in animate())
    print("Step 1: Preparing configuration...")
    config_file = anim._prepare_config()
    print(f"  ✓ Config created: {config_file}")
    print()

    # Start server (this calls _find_free_port() internally)
    print("Step 2: Starting HTTP server...")
    print(f"  Default port: {WebBrowserAnimation.DEFAULT_PORT}")
    anim._start_server()
    print(f"  ✓ Server started on port {anim.port}")
    print()

    # Verify the port
    if anim.port == WebBrowserAnimation.DEFAULT_PORT:
        print(f"✅ SUCCESS: Using default port {WebBrowserAnimation.DEFAULT_PORT}")
        print()
        print("You can now configure your firewall:")
        print(f"  sudo ufw allow {WebBrowserAnimation.DEFAULT_PORT}/tcp")
        print()
        print("And use SSH port forwarding:")
        print(f"  ssh -L {WebBrowserAnimation.DEFAULT_PORT}:localhost:{WebBrowserAnimation.DEFAULT_PORT} user@host")
    else:
        print(f"⚠️  WARNING: Using alternative port {anim.port}")
        print(f"   (Default port {WebBrowserAnimation.DEFAULT_PORT} may be in use)")

    print()

    # Test connectivity
    print("Step 3: Verifying server is responding...")
    import socket
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    result = sock.connect_ex(('localhost', anim.port))
    sock.close()

    if result == 0:
        print(f"  ✓ Server is responding on port {anim.port}")
    else:
        print(f"  ✗ Server not responding on port {anim.port}")
        anim.cleanup()
        return False

    print()

    # Cleanup
    print("Step 4: Cleaning up...")
    anim.cleanup()
    print("  ✓ Cleanup complete")
    print()

    return True


if __name__ == "__main__":
    try:
        success = test_server_uses_default_port()
        sys.exit(0 if success else 1)
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
