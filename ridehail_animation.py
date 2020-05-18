#!/usr/bin/python3
"""
Ridehail animations: for amusement only
"""

# -------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------
import argparse
# import configparser
import logging
import random
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib.ticker import MultipleLocator
from matplotlib.animation import FuncAnimation
from matplotlib.animation import ImageMagickFileWriter, FFMpegFileWriter
import seaborn as sns
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)-15s %(levelname)-8s%(message)s')
logger = logging.getLogger('animate_covid')

# -------------------------------------------------------------------------------
# Parameters
# -------------------------------------------------------------------------------
MAP_SIZE = 100
BLOCK_SIZE = 10
VEHICLE_COUNT = 20
RIDER_COUNT = 10
FRAME_INTERVAL = 50

# TODO: IMAGEMAGICK_EXE is hardcoded here. Put it in a config file.
IMAGEMAGICK_DIR = "/Program Files/ImageMagick-7.0.9-Q16"
# IMAGEMAGICK_DIR = "/Program Files/ImageMagick-7.0.10-Q16"
# For ImageMagick configuration, see
# https://stackoverflow.com/questions/23417487/saving-a-matplotlib-animation-with-imagemagick-and-without-ffmpeg-or-mencoder/42565258#42565258

# -------------------------------------------------------------------------------
# Set up graphics
# ------------------------------------------------------------------------------
plt.style.use("ggplot")
mpl.rcParams['figure.figsize'] = [7.0, 4.0]
mpl.rcParams['figure.dpi'] = 90
mpl.rcParams['savefig.dpi'] = 100
mpl.rcParams['animation.convert_path'] = IMAGEMAGICK_DIR + "/magick.exe"
mpl.rcParams['animation.ffmpeg_path'] = IMAGEMAGICK_DIR + "/ffmpeg.exe"

# mpl.rcParams['font.size'] = 12
# mpl.rcParams['legend.fontsize'] = 'large'
# mpl.rcParams['figure.titlesize'] = 'medium'
sns.set()
sns.set_palette("muted")

# ------------------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Classes
# ------------------------------------------------------------------------------
class Plot():
    """
    Generic Plot class.
    There's nothing here yet, but it will probably fill up as more plots
    are added
    """
    def output(self, anim, plt, dataset, output):
        """
        Generic output functions
        """
        logger.info("Writing output...")
        filename = "ridehail_{}.{}".format(dataset.lower(), output)
        if output == "mp4":
            writer = FFMpegFileWriter(fps=10, bitrate=1800)
            anim.save(filename, writer=writer)
        elif output == "gif":
            writer = ImageMagickFileWriter()
            anim.save(filename, writer=writer)
        else:
            plt.show()


class RideHailAnimation():
    """
    Plot cumulative cases
    """
    def __init__(self, vehicle_count, rider_count):
        """
        Initialize the class variables and call what needs to be called.
        The dataframe "data" has a row for each case.
        It must have the following columns:
        - "date_report": the date a case is reported
        """
        self.output = None
        self.speed = 1
        self.fps = 4
        self.vehicle_count = vehicle_count
        self.vehicles = []
        for i in range(vehicle_count):
            self.vehicles.append(Vehicle(i))
            logger.debug(
                f"Vehicle {i}: ({self.vehicles[i].x}, {self.vehicles[i].y})")
        self.rider_count = rider_count
        self.riders = []

    def plot(self):
        """
        Plot the trend of cumulative cases, observed at
        earlier days, evolving over time.
        """
        # initial plot
        logger.info("Plotting...")
        fig, ax = plt.subplots(figsize=(8, 8))
        anim = FuncAnimation(fig,
                             self.next_frame,
                             frames=None,
                             fargs=[ax],
                             interval=FRAME_INTERVAL,
                             repeat=False,
                             repeat_delay=3000)
        Plot().output(anim, plt, self.__class__.__name__, self.output)

    def next_frame(self, i, ax):
        """
        Function called from animator to generate frame i of the animation.
        """
        # Get the objects we are going to update
        ax.clear()
        x = []
        y = []
        for vehicle in self.vehicles:
            vehicle.move(self.speed)
            x.append(vehicle.x)
            y.append(vehicle.y)
        logger.debug(f"Frame {i}")
        ax.scatter(x, y, s=20, marker='s', color=sns.color_palette()[0])

        if random.random() > 0.9 and len(self.riders) < self.rider_count:
            self.riders.append(Rider(len(self.riders)))
        x = []
        y = []
        for rider in self.riders:
            x.append(rider.x)
            y.append(rider.y)
        ax.scatter(x, y, s=80, marker='o', color=sns.color_palette()[1])
        ax.set_xlim(-MAP_SIZE / 2, +MAP_SIZE / 2)
        ax.set_ylim(-MAP_SIZE / 2, +MAP_SIZE / 2)
        ax.xaxis.set_major_locator(MultipleLocator(BLOCK_SIZE))
        ax.yaxis.set_major_locator(MultipleLocator(BLOCK_SIZE))
        ax.grid(True, which="major", axis="both", lw=7)
        ax.get_xaxis().set_ticklabels([])
        ax.get_yaxis().set_ticklabels([])


class Rider():
    """
    A rider places a request and is taken to a destination
    """
    def __init__(self, i, x=None, y=None):
        self.index = i
        self.x = (MAP_SIZE / BLOCK_SIZE) * (random.randint(
            -(MAP_SIZE / (2 * BLOCK_SIZE)), (MAP_SIZE / (2 * BLOCK_SIZE))))
        self.y = (MAP_SIZE / BLOCK_SIZE) * (random.randint(
            -(MAP_SIZE / (2 * BLOCK_SIZE)), (MAP_SIZE / (2 * BLOCK_SIZE))))


class Vehicle():
    """
    A vehicle and its state

    direction: N=0, E=1, S=2, W=3
    grid has edge MAP_SIZE, in blocks spaced BLOCK_SIZE apart
    """
    def __init__(self, i, x=None, y=None):
        self.index = i
        self.x = (MAP_SIZE / BLOCK_SIZE) * (random.randint(
            -(MAP_SIZE / (2 * BLOCK_SIZE)), (MAP_SIZE / (2 * BLOCK_SIZE))))
        self.y = (MAP_SIZE / BLOCK_SIZE) * (random.randint(
            -(MAP_SIZE / (2 * BLOCK_SIZE)), (MAP_SIZE / (2 * BLOCK_SIZE))))
        self.direction = random.randint(0, 3)

    def at_intersection(self):
        if self.x % BLOCK_SIZE == 0 and self.y % BLOCK_SIZE == 0:
            return True
        else:
            return False

    def move(self, speed):
        if self.at_intersection():
            # Choose a direction at random. Better to
            # disallow u-turns and encourage straight
            new_direction = random.randint(0, 3)
            if abs(self.direction - new_direction) != 2:
                self.direction = new_direction
                logger.debug(
                    f"Vehicle {self.index} now going {self.direction}")
            pass
        if self.direction == 0:
            self.y += speed
        elif self.direction == 1:
            self.x += speed
        elif self.direction == 2:
            self.y -= speed
        elif self.direction == 3:
            self.x -= speed
        # Check for going off the sides
        logger.debug((f"Vehicle {self.index}: ({self.x}, {self.y})"))
        if self.x > (MAP_SIZE / 2):
            remainder = abs(self.x) % (MAP_SIZE / 2)
            logger.debug((f"Vehicle {self.index} at x edge: "
                          f"remainder = {remainder}, "
                          f"{self.x} -> {remainder - MAP_SIZE/2}"))
            self.x = remainder - MAP_SIZE / 2
        elif self.x < -(MAP_SIZE / 2):
            remainder = abs(self.x) % (MAP_SIZE / 2)
            logger.debug((f"Vehicle {self.index} at x edge: "
                          f"remainder = {remainder}, "
                          f"{self.x} -> {remainder - MAP_SIZE/2}"))
            self.x = remainder + MAP_SIZE / 2
        # Check for going off the top or bottom
        if self.y > (MAP_SIZE / 2):
            remainder = abs(self.y) % (MAP_SIZE / 2)
            logger.debug((f"Vehicle {self.index} at y edge: "
                          f"remainder = {remainder}, "
                          f"{self.y} -> {remainder - MAP_SIZE/2}"))
            self.y = remainder - MAP_SIZE / 2
        elif self.y < -(MAP_SIZE / 2):
            remainder = abs(self.y) % (MAP_SIZE / 2)
            logger.debug((f"Vehicle {self.index} at y edge: "
                          f"remainder = {remainder}, "
                          f"{self.y} -> {remainder - MAP_SIZE/2}"))
            self.y = remainder + MAP_SIZE / 2


def parse_args():
    """
    Define, read and parse command-line arguments.
    """
    parser = argparse.ArgumentParser(description="Animate some Covid-19 data.",
                                     usage="%(prog)s [options]",
                                     fromfile_prefix_chars='@')
    parser.add_argument(
        "-o",
        "--output",
        metavar="output",
        action="store",
        type=str,
        default="",
        help="output the animation to the window or as a file; [gif] or mp4",
    )
    parser.add_argument(
        "-d",
        "--dataset",
        metavar="dataset",
        action="store",
        type=str,
        default="cases",
        help="data set to plot; [cases] or growth or provinces")
    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="log debug messages")
    args = parser.parse_args()
    return args


def read_config(args):
    """
    Take the command line options and read a user-defined config file.
    Together these define how the program runs.
    """
    return "config"


def main():
    """
    Entry point.
    """
    logger.info("Starting...")
    args = parse_args()
    if args.verbose:
        logger.setLevel(logging.DEBUG)
    logger.debug("Logging debug messages...")
    # config = read_config(args)
    animation = RideHailAnimation(VEHICLE_COUNT, RIDER_COUNT)
    animation.plot()


if __name__ == '__main__':
    main()
