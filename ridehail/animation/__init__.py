"""
Animation package for ridehail simulation.

This package provides various animation modes for visualizing ridehail simulations:
- TextualConsoleAnimation: Interactive Textual-based terminal animation (default for console)
- TextualMapAnimation: Interactive Textual-based Unicode map with real-time vehicle tracking (default for terminal_map)
- TextualStatsAnimation: Interactive Textual-based real-time line charts using plotext (default for terminal_stats)
- TextualSequenceAnimation: Interactive Textual-based parameter sweep visualization using plotext (default for terminal_sequence)
- MatplotlibAnimation: Full matplotlib-based plotting and animation

Note: Textual is required for terminal animations. Rich-based fallbacks have been removed.

Usage:
    from ridehail.animation import create_animation

    # Create animation using factory (Textual-based)
    animation = create_animation(animation, sim)
    animation.animate()
"""

# Import key classes and functions for public API
from .base import RideHailAnimation, HistogramArray
from .utils import (
    create_animation_factory as create_animation,
    setup_matplotlib_for_animation,
)


# Conditional imports to avoid importing heavy dependencies unless needed


def get_matplotlib_animation():
    """Lazy import for MatplotlibAnimation"""
    from .matplotlib import MatplotlibAnimation

    return MatplotlibAnimation


def get_textual_console_animation():
    """Lazy import for TextualConsoleAnimation"""
    try:
        from .terminal_console import TextualConsoleAnimation

        return TextualConsoleAnimation
    except ImportError:
        return None


def get_textual_map_animation():
    """Lazy import for TextualMapAnimation"""
    try:
        from .terminal_map import TextualMapAnimation

        return TextualMapAnimation
    except ImportError:
        return None


def get_textual_stats_animation():
    """Lazy import for TextualStatsAnimation"""
    try:
        from .terminal_stats import TextualStatsAnimation

        return TextualStatsAnimation
    except ImportError:
        return None


def get_textual_sequence_animation():
    """Lazy import for TextualSequenceAnimation"""
    try:
        from .terminal_sequence import TextualSequenceAnimation

        return TextualSequenceAnimation
    except ImportError:
        return None


def get_sequence_animation():
    """Lazy import for SequenceAnimation"""
    try:
        from .sequence_animation import SequenceAnimation

        return SequenceAnimation
    except ImportError:
        return None


def get_text_animation():
    """Lazy import for TextAnimation"""
    from .text import TextAnimation

    return TextAnimation


# Export public API
__all__ = [
    "RideHailAnimation",
    "HistogramArray",
    "create_animation",
    "setup_matplotlib_for_animation",
    "get_matplotlib_animation",
    "get_text_animation",
]
