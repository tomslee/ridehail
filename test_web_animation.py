#!/usr/bin/env python3
"""
Simple test script for web browser animation functionality.

Tests Phase 1 implementation:
1. Port finding works
2. Configuration conversion works
3. Classes instantiate correctly
"""

import sys
import json
from pathlib import Path

# Add project to path
sys.path.insert(0, str(Path(__file__).parent))

from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.animation.web_browser import (
    WebBrowserAnimation,
    WebMapAnimation,
    WebStatsAnimation
)


def test_port_finding():
    """Test that we can find a free port"""
    print("Test 1: Port finding...")

    # Create minimal config
    config = RideHailConfig()
    config.city_size.value = 8
    config.vehicle_count.value = 10
    config.time_blocks.value = 10
    config.animate.value = False

    # Create simulation
    sim = RideHailSimulation(config)

    # Create animation instance
    anim = WebMapAnimation(sim)

    # Test port finding
    port = anim._find_free_port()

    assert isinstance(port, int), "Port should be an integer"
    assert 1024 <= port <= 65535, f"Port {port} should be in valid range"

    print(f"  ✓ Found free port: {port}")
    return True


def test_config_conversion():
    """Test that configuration converts correctly to web format"""
    print("\nTest 2: Configuration conversion...")

    # Create config with specific values
    config = RideHailConfig()
    config.city_size.value = 12
    config.vehicle_count.value = 25
    config.base_demand.value = 6.5
    config.time_blocks.value = 10
    config.animate.value = False
    config.equilibrate.value = True
    config.price.value = 10.0
    config.platform_commission.value = 0.25

    # Create simulation
    sim = RideHailSimulation(config)

    # Create animation instance
    anim = WebMapAnimation(sim)

    # Prepare config (this creates the JSON file)
    config_file = anim._prepare_config()

    assert config_file.exists(), "Config file should be created"
    print(f"  ✓ Config file created: {config_file}")

    # Read and validate JSON
    with open(config_file, 'r') as f:
        web_config = json.load(f)

    # Check key parameters
    assert web_config['citySize'] == 12, "City size should match"
    assert web_config['vehicleCount'] == 25, "Vehicle count should match"
    assert web_config['requestRate'] == 6.5, "Request rate should match"
    assert web_config['equilibrate'] == True, "Equilibrate should match"
    assert web_config['price'] == 10.0, "Price should match"
    assert web_config['platformCommission'] == 0.25, "Platform commission should match"
    assert web_config['cliMode'] == True, "CLI mode flag should be set"

    print(f"  ✓ Config contains {len(web_config)} parameters")
    print(f"  ✓ Key parameters validated:")
    print(f"    - citySize: {web_config['citySize']}")
    print(f"    - vehicleCount: {web_config['vehicleCount']}")
    print(f"    - requestRate: {web_config['requestRate']}")
    print(f"    - equilibrate: {web_config['equilibrate']}")

    # Cleanup
    config_file.unlink()
    print(f"  ✓ Config file cleaned up")

    return True


def test_class_instantiation():
    """Test that animation classes instantiate correctly"""
    print("\nTest 3: Class instantiation...")

    # Create minimal config
    config = RideHailConfig()
    config.city_size.value = 8
    config.vehicle_count.value = 10
    config.time_blocks.value = 10
    config.animate.value = False

    # Create simulation
    sim = RideHailSimulation(config)

    # Test WebMapAnimation
    map_anim = WebMapAnimation(sim)
    assert map_anim.chart_type == "map", "Map animation should have chart_type='map'"
    assert map_anim.lab_dir.exists(), "Lab directory should exist"
    assert hasattr(map_anim, 'animate'), "Map animation should have animate() method"
    print(f"  ✓ WebMapAnimation instantiated (chart_type={map_anim.chart_type})")

    # Test WebStatsAnimation
    stats_anim = WebStatsAnimation(sim)
    assert stats_anim.chart_type == "stats", "Stats animation should have chart_type='stats'"
    assert stats_anim.lab_dir.exists(), "Lab directory should exist"
    assert hasattr(stats_anim, 'animate'), "Stats animation should have animate() method"
    print(f"  ✓ WebStatsAnimation instantiated (chart_type={stats_anim.chart_type})")

    return True


def test_animation_factory():
    """Test that animation factory creates correct instances"""
    print("\nTest 4: Animation factory integration...")

    from ridehail.animation.utils import create_animation_factory
    from ridehail.atom import Animation

    # Create minimal config
    config = RideHailConfig()
    config.city_size.value = 8
    config.vehicle_count.value = 10
    config.time_blocks.value = 10
    config.animate.value = False

    # Create simulation
    sim = RideHailSimulation(config)

    # Test factory with WEB_MAP
    map_anim = create_animation_factory(Animation.WEB_MAP, sim)
    assert isinstance(map_anim, WebMapAnimation), "Factory should create WebMapAnimation"
    assert map_anim.chart_type == "map"
    print(f"  ✓ Factory creates WebMapAnimation correctly")

    # Test factory with WEB_STATS
    stats_anim = create_animation_factory(Animation.WEB_STATS, sim)
    assert isinstance(stats_anim, WebStatsAnimation), "Factory should create WebStatsAnimation"
    assert stats_anim.chart_type == "stats"
    print(f"  ✓ Factory creates WebStatsAnimation correctly")

    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Web Browser Animation - Phase 1 Tests")
    print("=" * 60)

    tests = [
        test_port_finding,
        test_config_conversion,
        test_class_instantiation,
        test_animation_factory,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ✗ Test failed: {e}")
            failed += 1
            import traceback
            traceback.print_exc()

    print("\n" + "=" * 60)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 60)

    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
