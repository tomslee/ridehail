"""
Animation package for ridehail simulation.

This package provides various animation modes for visualizing ridehail simulations:
- TextualConsoleAnimation: Interactive Textual-based terminal animation (default for console)
- TextualMapAnimation: Interactive Textual-based Unicode map with real-time vehicle tracking (default for terminal_map)
- TextualStatsAnimation: Interactive Textual-based real-time line charts using plotext (default for terminal_stats)
- MatplotlibAnimation: Full matplotlib-based plotting and animation
- ConsoleAnimation: Rich-based terminal animation (fallback only)
- TerminalMapAnimation: Rich-based Unicode map display (fallback only)

Usage:
    from ridehail.animation import create_animation

    # Create animation using factory (Textual is default for terminal animations)
    animation = create_animation(animation_style, sim)
    animation.animate()
"""

# Import key classes and functions for public API
from .base import RideHailAnimation, HistogramArray
from .console import ConsoleAnimation
from .utils import create_animation_factory as create_animation, setup_matplotlib_for_animation

# Conditional imports to avoid importing heavy dependencies unless needed
def get_terminal_map_animation():
    """Lazy import for TerminalMapAnimation"""
    from .terminal_map import TerminalMapAnimation
    return TerminalMapAnimation

def get_matplotlib_animation():
    """Lazy import for MatplotlibAnimation"""
    from .matplotlib import MatplotlibAnimation
    return MatplotlibAnimation

def get_textual_console_animation():
    """Lazy import for TextualConsoleAnimation"""
    try:
        from .textual_console import TextualConsoleAnimation
        return TextualConsoleAnimation
    except ImportError:
        return None

def get_textual_map_animation():
    """Lazy import for TextualMapAnimation"""
    try:
        from .textual_map import TextualMapAnimation
        return TextualMapAnimation
    except ImportError:
        return None

def get_textual_stats_animation():
    """Lazy import for TextualStatsAnimation"""
    try:
        from .textual_stats import TextualStatsAnimation
        return TextualStatsAnimation
    except ImportError:
        return None

# Export public API
__all__ = [
    'RideHailAnimation',
    'HistogramArray',
    'ConsoleAnimation',
    'create_animation',
    'setup_matplotlib_for_animation',
    'get_terminal_map_animation',
    'get_matplotlib_animation',
]