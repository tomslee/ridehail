"""
Backward compatibility layer for ridehail.animation module.

This module provides import forwarding to maintain compatibility with existing code
while the animation module has been refactored into a package structure.

DEPRECATED: This module is deprecated. Use the new animation package instead:
    from ridehail.animation import create_animation
"""

import warnings

# Issue deprecation warning when this module is imported
warnings.warn(
    "Importing from ridehail.animation is deprecated. "
    "Use 'from ridehail.animation import ...' instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Forward imports to new package structure
from ridehail.animation import (
    RideHailAnimation,
    HistogramArray,
    create_animation,
    setup_matplotlib_for_animation,
    get_matplotlib_animation,
)

# Create backward compatible class references
MatplotlibAnimation = get_matplotlib_animation()

# Re-export Measure for backward compatibility
from ridehail.atom import Measure

# Legacy constants that might be imported
CHART_X_RANGE = 245

__all__ = [
    "RideHailAnimation",
    "HistogramArray",
    "MatplotlibAnimation",
    "Measure",
    "CHART_X_RANGE",
]
