"""
Keyboard mappings configuration - single source of truth for all keyboard shortcuts.

This module defines keyboard shortcuts used across different interfaces:
- Desktop terminal (termios-based)
- Desktop Textual UI
- Browser web interface

Each action can have multiple key bindings and specifies which platforms support it.
"""

from typing import List, Dict, Any
from dataclasses import dataclass, asdict


@dataclass
class KeyMapping:
    """Represents a keyboard shortcut mapping."""
    action: str
    keys: List[str]
    description: str
    platforms: List[str]  # ["terminal", "textual", "browser"]
    shift_modifier: bool = False  # True if requires Shift key
    value: Any = None  # Optional value for increment/decrement actions


# Canonical keyboard mappings
KEYBOARD_MAPPINGS = [
    # Core simulation controls (all platforms)
    KeyMapping(
        action="pause",
        keys=["space", "p"],
        description="Pause/Resume simulation",
        platforms=["terminal", "textual", "browser"],
    ),
    KeyMapping(
        action="quit",
        keys=["q"],
        description="Quit simulation",
        platforms=["terminal", "textual"],
    ),
    KeyMapping(
        action="step",
        keys=["s"],
        description="Single step forward (when paused)",
        platforms=["terminal", "textual", "browser"],
    ),
    KeyMapping(
        action="restart",
        keys=["r"],
        description="Restart simulation from beginning",
        platforms=["terminal", "textual", "browser"],
    ),

    # Vehicle adjustments (all platforms)
    KeyMapping(
        action="decrease_vehicles",
        keys=["n"],
        description="Decrease vehicles by 1",
        platforms=["terminal", "textual", "browser"],
        value=1,
    ),
    KeyMapping(
        action="increase_vehicles",
        keys=["N"],
        description="Increase vehicles by 1",
        platforms=["terminal", "textual", "browser"],
        shift_modifier=True,
        value=1,
    ),

    # Demand adjustments (all platforms)
    KeyMapping(
        action="decrease_demand",
        keys=["k"],
        description="Decrease demand by 0.1",
        platforms=["terminal", "textual", "browser"],
        value=0.1,
    ),
    KeyMapping(
        action="increase_demand",
        keys=["K"],
        description="Increase demand by 0.1",
        platforms=["terminal", "textual", "browser"],
        shift_modifier=True,
        value=0.1,
    ),

    # Animation delay adjustments (all platforms)
    KeyMapping(
        action="decrease_animation_delay",
        keys=["d"],
        description="Decrease animation delay by 0.05s",
        platforms=["terminal", "textual", "browser"],
        value=0.05,
    ),
    KeyMapping(
        action="increase_animation_delay",
        keys=["D"],
        description="Increase animation delay by 0.05s",
        platforms=["terminal", "textual", "browser"],
        shift_modifier=True,
        value=0.05,
    ),

    # Zoom/Config Panel toggle (all platforms)
    KeyMapping(
        action="toggle_config_panel",
        keys=["z"],
        description="Toggle config panel (zoom to main display)",
        platforms=["terminal", "textual", "browser"],
    ),

    # Help
    KeyMapping(
        action="show_help",
        keys=["?", "h"],
        description="Show keyboard shortcuts help",
        platforms=["terminal", "textual", "browser"],
    ),
]


def get_mappings_for_platform(platform: str) -> List[KeyMapping]:
    """Get all keyboard mappings for a specific platform."""
    return [m for m in KEYBOARD_MAPPINGS if platform in m.platforms]


def get_mapping_for_key(key: str, platform: str = None) -> KeyMapping:
    """
    Find the mapping for a specific key.

    Args:
        key: The keyboard key to look up
        platform: Optional platform filter

    Returns:
        KeyMapping if found, None otherwise
    """
    for mapping in KEYBOARD_MAPPINGS:
        if key in mapping.keys:
            if platform is None or platform in mapping.platforms:
                return mapping
    return None


def get_mapping_for_action(action: str) -> KeyMapping:
    """Find the mapping for a specific action."""
    for mapping in KEYBOARD_MAPPINGS:
        if mapping.action == action:
            return mapping
    return None


def generate_textual_bindings(platform: str = "textual") -> List[tuple]:
    """
    Generate Textual BINDINGS list from mappings.

    Returns list of tuples: (key, action, description)
    """
    bindings = []
    for mapping in get_mappings_for_platform(platform):
        # Generate bindings for ALL keys in the mapping (not just the first)
        for key in mapping.keys:
            bindings.append((key, mapping.action, mapping.description))
    return bindings


def generate_help_text(platform: str) -> str:
    """Generate formatted help text for keyboard shortcuts."""
    mappings = get_mappings_for_platform(platform)

    lines = ["=" * 60]
    lines.append("KEYBOARD SHORTCUTS:")
    lines.append("=" * 60)

    for mapping in mappings:
        # Format keys (show all alternatives)
        keys_str = "/".join(mapping.keys)
        # Pad to align descriptions
        lines.append(f"  {keys_str:<12} - {mapping.description}")

    lines.append("=" * 60)
    return "\n".join(lines)


def export_to_json() -> Dict[str, Any]:
    """
    Export mappings to JSON-serializable format for browser.

    Returns dictionary suitable for JSON serialization.
    """
    return {
        "version": "1.0",
        "mappings": [asdict(m) for m in KEYBOARD_MAPPINGS],
        "platforms": ["terminal", "textual", "browser"],
    }


# Quick lookup dictionaries for performance
_KEY_TO_ACTION_CACHE = {}
_ACTION_TO_MAPPING_CACHE = {}


def _build_caches():
    """Build lookup caches for performance."""
    global _KEY_TO_ACTION_CACHE, _ACTION_TO_MAPPING_CACHE

    for mapping in KEYBOARD_MAPPINGS:
        _ACTION_TO_MAPPING_CACHE[mapping.action] = mapping
        for key in mapping.keys:
            _KEY_TO_ACTION_CACHE[key] = mapping


# Build caches on module import
_build_caches()
