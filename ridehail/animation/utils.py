"""
Shared utilities and constants for ridehail animations.
"""
import matplotlib as mpl
import seaborn as sns
import logging

# Set interactive backend for WSL2/Linux environments
if mpl.get_backend() == "agg":
    # Try Qt5Agg first (better for animations), fall back to TkAgg
    logging.info("matplotlib using agg. Try changing...")
    try:
        mpl.use("Qt5Agg")
        logging.info("matplotlib using Qt5Agg")
    except ImportError:
        try:
            mpl.use("TkAgg")
            logging.info("matplotlib using TkAgg")
        except ImportError:
            logging.error(
                (
                    "No interactive backend available for matplotlib."
                    "Install python3-pyqt5 or python3-tk for interactive display."
                )
            )

# Global matplotlib configuration
CHART_X_RANGE = 245
mpl.rcParams["figure.dpi"] = 100
mpl.rcParams["savefig.dpi"] = 100

# Seaborn styling setup
sns.set_theme()
sns.set_style("darkgrid")
sns.set_palette("muted")
sns.set_context("talk")


def setup_matplotlib_for_animation(imagemagick_dir=None):
    """Configure matplotlib for animation output"""
    if imagemagick_dir:
        mpl.rcParams["animation.convert_path"] = imagemagick_dir + "/magick"
        mpl.rcParams["animation.ffmpeg_path"] = imagemagick_dir + "/ffmpeg"
    else:
        mpl.rcParams["animation.convert_path"] = "magick"
        mpl.rcParams["animation.ffmpeg_path"] = "ffmpeg"
    mpl.rcParams["animation.embed_limit"] = 2**128


def create_animation_factory(animation_style, sim):
    """Factory function to create the appropriate animation instance

    Args:
        animation_style: The Animation enum value
        sim: The simulation instance
    """
    from ridehail.atom import Animation

    # Terminal animations now default to Textual (no longer need use_textual flag)
    if animation_style == Animation.CONSOLE:
        try:
            from .textual_console import TextualConsoleAnimation
            return TextualConsoleAnimation(sim)
        except ImportError:
            logging.warning("Textual console animation not available, falling back to Rich")
            from .console import ConsoleAnimation
            return ConsoleAnimation(sim)
    elif animation_style == Animation.TERMINAL_MAP:
        try:
            from .textual_map import TextualMapAnimation
            return TextualMapAnimation(sim)
        except ImportError:
            logging.warning("Textual map animation not available, falling back to Rich")
            from .terminal_map import TerminalMapAnimation
            return TerminalMapAnimation(sim)
    elif animation_style == Animation.TERMINAL_STATS:
        try:
            from .textual_stats import TextualStatsAnimation
            return TextualStatsAnimation(sim)
        except ImportError:
            logging.warning("Textual stats animation not available, falling back to matplotlib")
            from .matplotlib import MatplotlibAnimation
            return MatplotlibAnimation(sim)
    elif animation_style in (Animation.MAP, Animation.STATS, Animation.BAR, Animation.ALL):
        from .matplotlib import MatplotlibAnimation
        return MatplotlibAnimation(sim)
    else:
        raise ValueError(f"Unknown animation style: {animation_style}")