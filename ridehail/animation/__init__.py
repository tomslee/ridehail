"""
Animation package for ridehail simulation.

This package provides various animation modes for visualizing ridehail simulations:
- ConsoleAnimation: Rich-based terminal animation with progress bars
- TerminalMapAnimation: Unicode map display with real-time vehicle tracking
- MatplotlibAnimation: Full matplotlib-based plotting and animation

Usage:
    from ridehail.animation import create_animation, ConsoleAnimation

    # Create animation using factory
    animation = create_animation(animation_style, sim)
    animation.animate()

    # Or create directly
    animation = ConsoleAnimation(sim)
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