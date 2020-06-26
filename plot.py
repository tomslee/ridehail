#!/usr/bin/python3
import logging
from enum import Enum
import matplotlib as mpl
import seaborn as sns
from matplotlib.animation import ImageMagickFileWriter, FFMpegFileWriter

logger = logging.getLogger(__name__)

# TODO: IMAGEMAGICK_EXE is hardcoded here. Put it in a config file.
IMAGEMAGICK_DIR = "/Program Files/ImageMagick-7.0.9-Q16"
# IMAGEMAGICK_DIR = "/Program Files/ImageMagick-7.0.10-Q16"
# For ImageMagick configuration, see
# https://stackoverflow.com/questions/23417487/saving-a-matplotlib-animation-with-imagemagick-and-without-ffmpeg-or-mencoder/42565258#42565258
# -------------------------------------------------------------------------------
# Set up graphicself.color_palette['figure.figsize'] = [7.0, 4.0]
mpl.rcParams['figure.dpi'] = 90
mpl.rcParams['savefig.dpi'] = 100
mpl.rcParams['animation.convert_path'] = IMAGEMAGICK_DIR + "/magick.exe"
mpl.rcParams['animation.ffmpeg_path'] = IMAGEMAGICK_DIR + "/ffmpeg.exe"
# mpl.rcParams['font.size'] = 12
# mpl.rcParams['legend.fontsize'] = 'large'
# mpl.rcParams['figure.titlesize'] = 'medium'
sns.set()
sns.set_palette("muted")


class PlotStat(Enum):
    DRIVER_AVAILABLE_FRACTION = "Available fraction"
    DRIVER_PICKUP_FRACTION = "Picking up fraction"
    DRIVER_PAID_FRACTION = "Paid fraction"
    DRIVER_MEAN_COUNT = "Mean driver count"
    DRIVER_UTILITY = "Driver utility"
    TRIP_MEAN_WAIT_TIME = "Mean wait time"
    TRIP_MEAN_LENGTH = "Mean trip distance"
    TRIP_WAIT_FRACTION = "Wait fraction"
    TRIP_LENGTH_FRACTION = "Trip length fraction"
    TRIP_COUNT = "Trips completed"
    TRIP_UTILITY = "Trip utility"


class Draw(Enum):
    NONE = "none"
    MAP = "map"
    STATS = "stats"
    ALL = "all"
    DRIVER = "driver"
    TRIP = "trip"
    SUMMARY = "summary"
    EQUILIBRATION = "equilibration"


class Plot():
    """
    Generic Plot class.
    There's nothing much here yet, but it will probably fill up as more plots
    are added
    """
    def output(self, anim, plt, dataset, output):
        """
        Generic output functions
        """
        logger.info(f"Writing output to {output}...")
        if output.endswith("mp4"):
            writer = FFMpegFileWriter(fps=10, bitrate=1800)
            anim.save(output, writer=writer)
        elif output.endswith("gif"):
            writer = ImageMagickFileWriter()
            anim.save(output, writer=writer)
        else:
            plt.show()
