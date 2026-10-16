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


# Video output (-aof): frames per second, and the file types we can write.
# Browsers (and so Quarto/HTML pages) play H.264 .mp4 and VP9 .webm natively;
# .gif needs no ffmpeg but is many times larger.
OUTPUT_FPS = 10
OUTPUT_FILE_TYPES = (".mp4", ".webm", ".gif")


def make_output_writer(output_file, fps=OUTPUT_FPS):
    """Return a matplotlib writer for an animation output file.

    The ffmpeg writers pipe frames straight to ffmpeg (FFMpegWriter), rather
    than writing a temporary PNG per frame (FFMpegFileWriter). GIFs use
    Pillow, so ImageMagick is not needed.
    """
    from matplotlib import animation

    suffix = output_file.lower()
    if suffix.endswith(".mp4"):
        # yuv420p (added by matplotlib for h264) and faststart (metadata at
        # the front of the file) let browsers play it while it downloads
        return animation.FFMpegWriter(
            fps=fps, codec="h264", extra_args=["-movflags", "+faststart"]
        )
    if suffix.endswith(".webm"):
        # Constant quality (-crf with -b:v 0) rather than a fixed bitrate
        return animation.FFMpegWriter(
            fps=fps,
            codec="libvpx-vp9",
            extra_args=["-b:v", "0", "-crf", "33", "-pix_fmt", "yuv420p"],
        )
    if suffix.endswith(".gif"):
        return animation.PillowWriter(fps=fps)
    raise ValueError(
        f"animation output file {output_file} must end in one of "
        f"{', '.join(OUTPUT_FILE_TYPES)}"
    )


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
    elif animation == Animation.TERMINAL_WAIT:
        try:
            from .terminal_wait import TextualWaitAnimation

            return TextualWaitAnimation(sim)
        except ImportError:
            logging.warning(
                "Textual wait animation not available, falling back to matplotlib"
            )
            from .matplotlib import MatplotlibAnimation

            return MatplotlibAnimation(sim)
    elif animation == Animation.TERMINAL_STRATEGY:
        try:
            from .terminal_strategy import TextualStrategyAnimation

            return TextualStrategyAnimation(sim)
        except ImportError:
            logging.warning(
                "Textual strategy animation not available, falling back to text"
            )
            from .text import TextAnimation

            return TextAnimation(sim)
    elif animation == Animation.TERMINAL_LENGTH:
        try:
            from .terminal_length import TextualLengthAnimation

            return TextualLengthAnimation(sim)
        except ImportError:
            logging.warning(
                "Textual length animation not available, falling back to matplotlib"
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
