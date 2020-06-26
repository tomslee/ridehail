#!/usr/bin/python3
import logging
from enum import Enum
from matplotlib.animation import ImageMagickFileWriter, FFMpegFileWriter

logger = logging.getLogger(__name__)


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
