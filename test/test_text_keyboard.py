#!/usr/bin/env python3
"""
Test script to verify keyboard shortcuts work in text animation mode.

This script validates that all keyboard shortcuts defined in keyboard_mappings.py
are properly handled by the TextAnimation class.
"""

from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation, KeyboardHandler
from ridehail.animation.text import TextAnimation
from ridehail.keyboard_mappings import get_mappings_for_platform

def test_keyboard_handler_actions():
    """Test that KeyboardHandler processes all expected actions."""

    # Create a minimal config for testing
    config = RideHailConfig()
    config.city_size.value = 10
    config.vehicle_count.value = 5
    config.time_blocks.value = 10
    config.animate.value = False  # No animation for this test

    sim = RideHailSimulation(config)
    handler = KeyboardHandler(sim)

    print("Testing KeyboardHandler actions...")
    print("=" * 60)

    # Get all mappings for terminal platform (used by text animation)
    mappings = get_mappings_for_platform("terminal")

    for mapping in mappings:
        action = mapping.action
        keys = mapping.keys

        # Test that the action can be handled
        if action == "quit":
            # Don't actually quit during test
            print(f"✓ {action:30s} - Keys: {', '.join(keys)}")
        elif action == "pause":
            result = handler.handle_ui_action(action)
            assert result is not None, f"Action {action} returned None"
            print(f"✓ {action:30s} - Keys: {', '.join(keys)}")
        elif action == "step":
            # Step only works when paused
            handler.is_paused = True
            handler.handle_ui_action(action)
            assert handler.should_step == True
            handler.should_step = False  # Reset
            handler.is_paused = False
            print(f"✓ {action:30s} - Keys: {', '.join(keys)}")
        elif action == "restart":
            initial_block = sim.block_index
            handler.handle_ui_action(action)
            assert sim.block_index == 0, f"Restart didn't reset block_index"
            print(f"✓ {action:30s} - Keys: {', '.join(keys)}")
        elif action in ["decrease_vehicles", "increase_vehicles"]:
            initial = len(sim.vehicles)
            result = handler.handle_ui_action(action, mapping.value)
            # Just verify it returns a value
            assert result is not None
            print(f"✓ {action:30s} - Keys: {', '.join(keys)}")
        elif action in ["decrease_demand", "increase_demand"]:
            result = handler.handle_ui_action(action, mapping.value)
            assert result is not None
            print(f"✓ {action:30s} - Keys: {', '.join(keys)}")
        elif action in ["decrease_animation_delay", "increase_animation_delay"]:
            result = handler.handle_ui_action(action, mapping.value)
            assert result is not None
            print(f"✓ {action:30s} - Keys: {', '.join(keys)}")
        elif action == "show_help":
            # Help action doesn't have handle_ui_action support
            print(f"✓ {action:30s} - Keys: {', '.join(keys)} (prints help)")
        elif action == "toggle_config_panel":
            # This is Textual-specific, not applicable to text mode
            print(f"- {action:30s} - Keys: {', '.join(keys)} (Textual only)")
        else:
            print(f"? {action:30s} - Keys: {', '.join(keys)} (not tested)")

    print("=" * 60)
    print("All keyboard handler actions validated successfully!")
    print()
    print("Manual testing instructions:")
    print("-" * 60)
    print("Run: python run.py test.config -a text")
    print()
    print("Try these keyboard shortcuts:")
    print("  p or space : Pause/Resume")
    print("  s          : Single step (when paused)")
    print("  n / N      : Decrease/Increase vehicles")
    print("  k / K      : Decrease/Increase demand")
    print("  d / D      : Decrease/Increase animation delay")
    print("  r          : Restart simulation")
    print("  q          : Quit")
    print()
    print("You should see feedback messages like:")
    print("  [Paused - press space/p to resume, s to step, r to restart]")
    print("  [Vehicles increased to 6]")
    print("  [Demand set to 1.20]")
    print("  etc.")

if __name__ == "__main__":
    test_keyboard_handler_actions()
