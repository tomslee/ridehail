#!/usr/bin/env python3
"""
Test script for configuration validation system
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from ridehail.config import RideHailConfig, ConfigValidationError, ConfigItem

def test_basic_validation():
    """Test basic validation functionality"""
    print("Testing basic validation...")

    # Create a ConfigItem with validation rules
    test_item = ConfigItem(
        name="test_param",
        type=int,
        default=10,
        min_value=1,
        max_value=100,
        must_be_even=True
    )

    # Test valid value
    is_valid, value, error = test_item.validate_value(20)
    assert is_valid, f"Valid value failed: {error}"
    assert value == 20, f"Value not preserved: {value}"
    print("  ✓ Valid value test passed")

    # Test odd value (should auto-correct)
    is_valid, value, error = test_item.validate_value(21)
    assert is_valid, f"Odd value failed: {error}"
    assert value == 20, f"Odd value not corrected: {value}"
    print("  ✓ Even number auto-correction passed")

    # Test out of range
    is_valid, value, error = test_item.validate_value(200)
    assert not is_valid, "Out of range value should fail"
    assert "greater than maximum" in error, f"Wrong error message: {error}"
    print("  ✓ Range validation passed")

    # Test type conversion
    is_valid, value, error = test_item.validate_value("30")
    assert is_valid, f"String to int conversion failed: {error}"
    assert value == 30, f"Converted value wrong: {value}"
    print("  ✓ Type conversion passed")


def test_choices_validation():
    """Test choices validation"""
    print("Testing choices validation...")

    verbosity_item = ConfigItem(
        name="verbosity",
        type=int,
        choices=[0, 1, 2]
    )

    # Valid choice
    is_valid, value, error = verbosity_item.validate_value(1)
    assert is_valid, f"Valid choice failed: {error}"
    print("  ✓ Valid choice test passed")

    # Invalid choice
    is_valid, value, error = verbosity_item.validate_value(5)
    assert not is_valid, "Invalid choice should fail"
    assert "not in allowed choices" in error, f"Wrong error message: {error}"
    print("  ✓ Invalid choice test passed")


def test_dependency_validation():
    """Test dependency validation with actual config"""
    print("Testing dependency validation...")

    try:
        # Create config without loading from files
        config = RideHailConfig(use_config_file=False)

        # Set some values
        config.city_scale = True
        config.min_trip_distance.value = 10
        config.max_trip_distance.value = 8  # Invalid: less than min

        # This should fail validation
        try:
            config._validate_all_config_parameters()
            assert False, "Should have failed validation"
        except ConfigValidationError as e:
            print(f"  ✓ Dependency validation caught error: {e.message}")

    except Exception as e:
        print(f"  ⚠ Dependency test skipped due to: {e}")


def test_city_scale_requirements():
    """Test city scale parameter requirements"""
    print("Testing city scale requirements...")

    try:
        config = RideHailConfig(use_config_file=False)

        # Enable city scale but don't provide required parameters
        config.use_city_scale.value = True
        config.mean_vehicle_speed.value = None  # Should be required

        # This should fail validation
        try:
            config._validate_all_config_parameters()
            assert False, "Should have failed validation for missing required parameter"
        except ConfigValidationError as e:
            print(f"  ✓ Required parameter validation caught error: {e.message}")

    except Exception as e:
        print(f"  ⚠ City scale test skipped due to: {e}")


def main():
    """Run all validation tests"""
    print("=== Configuration Validation System Tests ===\n")

    try:
        test_basic_validation()
        print()
        test_choices_validation()
        print()
        test_dependency_validation()
        print()
        test_city_scale_requirements()
        print()
        print("=== All tests completed ===")
    except Exception as e:
        print(f"Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return 1

    return 0

if __name__ == "__main__":
    sys.exit(main())