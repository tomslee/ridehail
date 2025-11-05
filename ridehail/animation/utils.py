"""
Shared utilities and constants for ridehail animations.
"""

import logging

# Global configuration constant (no matplotlib dependency)
CHART_X_RANGE = 245

# Flag to track if matplotlib has been initialized
_matplotlib_initialized = False


def _initialize_matplotlib():
    """
    Initialize matplotlib and seaborn with default configuration.
    Only called when matplotlib-based animations are actually used.
    """
    global _matplotlib_initialized
    if _matplotlib_initialized:
        return

    try:
        import matplotlib as mpl
        import seaborn as sns

        # Matplotlib configuration
        mpl.rcParams["figure.dpi"] = 100
        mpl.rcParams["savefig.dpi"] = 100

        # Seaborn styling setup
        sns.set_theme()
        sns.set_style("darkgrid")
        sns.set_palette("muted")
        sns.set_context("talk")

        _matplotlib_initialized = True
        logging.info("Matplotlib and seaborn initialized successfully")
    except ImportError as e:
        logging.error(f"Failed to initialize matplotlib/seaborn: {e}")
        raise


def setup_matplotlib_for_animation(imagemagick_dir=None):
    """Configure matplotlib for animation output"""
    # Ensure matplotlib is initialized before configuring
    _initialize_matplotlib()

    import matplotlib as mpl

    if imagemagick_dir:
        mpl.rcParams["animation.convert_path"] = imagemagick_dir + "/magick"
        mpl.rcParams["animation.ffmpeg_path"] = imagemagick_dir + "/ffmpeg"
    else:
        mpl.rcParams["animation.convert_path"] = "magick"
        mpl.rcParams["animation.ffmpeg_path"] = "ffmpeg"
    mpl.rcParams["animation.embed_limit"] = 2**128


def create_animation_factory(animation, sim):
    """Factory function to create the appropriate animation instance

    Args:
        animation: The Animation enum value
        sim: The simulation instance
    """
    from ridehail.atom import Animation

    # Terminal animations require Textual (no fallbacks)
    if animation == Animation.CONSOLE:
        from .terminal_console import TextualConsoleAnimation

        return TextualConsoleAnimation(sim)
    elif animation == Animation.TERMINAL_MAP:
        from .terminal_map import TextualMapAnimation

        return TextualMapAnimation(sim)
    elif animation == Animation.TERMINAL_STATS:
        try:
            from .terminal_stats import TextualStatsAnimation

            return TextualStatsAnimation(sim)
        except ImportError:
            logging.warning(
                "Textual stats animation not available, falling back to matplotlib"
            )
            from .matplotlib import MatplotlibAnimation

            return MatplotlibAnimation(sim)
    elif animation == Animation.TERMINAL_SEQUENCE:
        try:
            from .terminal_sequence import TextualSequenceAnimation

            return TextualSequenceAnimation(sim)
        except ImportError:
            logging.warning(
                "Textual sequence animation not available, falling back to matplotlib"
            )
            from .matplotlib import MatplotlibAnimation

            return MatplotlibAnimation(sim)
    elif animation == Animation.TEXT:
        from .text import TextAnimation

        return TextAnimation(sim)
    elif animation == Animation.WEB_MAP:
        from .web_browser import WebMapAnimation

        return WebMapAnimation(sim)
    elif animation == Animation.WEB_STATS:
        from .web_browser import WebStatsAnimation

        return WebStatsAnimation(sim)
    elif animation in (
        Animation.MAP,
        Animation.STATS,
        Animation.BAR,
        Animation.ALL,
        Animation.SEQUENCE,
    ):
        # Initialize matplotlib before importing matplotlib-based animations
        _initialize_matplotlib()
        from .matplotlib import MatplotlibAnimation

        return MatplotlibAnimation(sim)
    else:
        raise ValueError(f"Unknown animation style: {animation}")
