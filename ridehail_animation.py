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
from enum import Enum
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
FRAME_INTERVAL = 50
SPEED = 1

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
# Enumerations
# ------------------------------------------------------------------------------
class Direction(Enum):
    NORTH = 0
    EAST = 1
    SOUTH = 2
    WEST = 3


class RiderPhase(Enum):
    INACTIVE = 0
    UNASSIGNED = 1
    WAITING = 2
    RIDING = 3


class DriverPhase(Enum):
    """
    Insurance commonly uses these phases
    Phase 0: App is off. Your personal policy covers you.
    Phase 1: App is on, you're waiting for ride request. ...
    Phase 2: Request accepted, and you're en route to pick up a passenger. ...
    Phase 3: You have passengers in the car.


    """
    AVAILABLE = 0
    PICKING_UP = 1
    WITH_RIDER = 2


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
    def __init__(self, driver_count, rider_count, frame_count, output):
        """
        Initialize the class variables and call what needs to be called.
        The dataframe "data" has a row for each case.
        It must have the following columns:
        - "date_report": the date a case is reported
        """
        self.output = None
        self.speed = SPEED
        self.fps = 4
        self.driver_count = driver_count
        self.drivers = []
        for i in range(driver_count):
            self.drivers.append(Driver(i))
            logger.debug((f"Driver {i}: ({self.drivers[i].location[0]}, "
                          f"{self.drivers[i].location[1]})"))
        self.rider_count = rider_count
        self.riders = []
        for i in range(rider_count):
            self.riders.append(Rider(i))
        self.frame_count = frame_count
        self.total_driver_time = 0
        self.driver_phase_time = [0, 0, 0]
        self.output = output
        self.mean_wait_times = []
        self.total_wait_phases = 0
        self.total_wait_time = 0

    def plot(self):
        """
        Plot the trend of cumulative cases, observed at
        earlier days, evolving over time.
        """
        # initial plot
        logger.info("Plotting...")
        fig, axes = plt.subplots(ncols=3, figsize=(18, 6))
        anim = FuncAnimation(fig,
                             self._next_frame,
                             frames=self.frame_count,
                             fargs=[axes],
                             interval=FRAME_INTERVAL,
                             repeat=False,
                             repeat_delay=3000)
        Plot().output(anim, plt, self.__class__.__name__, self.output)

    def _next_frame(self, i, axes):
        """
        Function called from animator to generate frame i of the animation.
        """
        for driver in self.drivers:
            self._move(driver, self.speed)
        self._animate_map(i, axes[0])
        self._display_driver_phases(i, axes[1])
        self._display_wait_times(i, axes[2])

    def _animate_map(self, i, ax):
        """
        Update driver and rider states and draw the map
        """
        ax.clear()
        # Plot the drivers
        x = [[] for i in list(Direction)]
        y = [[] for i in list(Direction)]
        size = [[] for i in list(Direction)]
        color = [[] for i in list(Direction)]

        # driver markers:
        markers = ('^', '>', 'v', '<')
        sizes = (60, 100, 100)
        for driver in self.drivers:
            x[driver.direction.value].append(driver.location[0])
            y[driver.direction.value].append(driver.location[1])
            size[driver.direction.value].append(sizes[driver.phase.value])
            color[driver.direction.value].append(
                sns.color_palette()[driver.phase.value])
        logger.debug(f"Frame {i}")
        for direction in list(Direction):
            ax.scatter(x[direction.value],
                       y[direction.value],
                       s=size[direction.value],
                       marker=markers[direction.value],
                       color=color[direction.value])

        # Periodically initiate a call from a rider
        if random.random() > 0.9:
            inactive_riders = []
            for rider in self.riders:
                if rider.phase == RiderPhase.INACTIVE:
                    inactive_riders.append(rider)
            if len(inactive_riders) > 0:
                # choose a rider at random
                rider = random.choice(inactive_riders)
                # rider has a random origin and destination
                # and is ready to make a request
                rider.phase = RiderPhase.UNASSIGNED
                rider.set_random_origin()
                rider.set_random_destination()
        unnasigned_riders = [
            rider for rider in self.riders
            if rider.phase == RiderPhase.UNASSIGNED
        ]
        for rider in unnasigned_riders:
            # Make a ride request
            # If a previous request was unassigned, repeat
            # assign a driver to the request
            assigned = self._assign_driver(rider.index, rider.origin,
                                           rider.destination)
            if assigned:
                logger.debug(f"Driver {assigned} assigned request")
            else:
                logger.debug(f"No driver assigned for request")
        for rider in self.riders:
            if rider.phase in (RiderPhase.UNASSIGNED, RiderPhase.WAITING):
                rider.wait_time += 1
            if rider.phase == RiderPhase.RIDING:
                rider.travel_time += 1
        x_origin = []
        y_origin = []
        x_destination = []
        y_destination = []
        for rider in self.riders:
            if rider.phase in (RiderPhase.UNASSIGNED, RiderPhase.WAITING):
                x_origin.append(rider.origin[0])
                y_origin.append(rider.origin[1])
            if rider.phase == RiderPhase.RIDING:
                x_destination.append(rider.destination[0])
                y_destination.append(rider.destination[1])
        ax.scatter(x_origin,
                   y_origin,
                   s=80,
                   marker='o',
                   color=sns.color_palette()[7],
                   label="Ride request")
        ax.scatter(x_destination,
                   y_destination,
                   s=100,
                   marker='*',
                   color=sns.color_palette()[9],
                   label="Ride destination")

        # Draw the map
        ax.set_xlim(-MAP_SIZE / 2, +MAP_SIZE / 2)
        ax.set_ylim(-MAP_SIZE / 2, +MAP_SIZE / 2)
        ax.xaxis.set_major_locator(MultipleLocator(BLOCK_SIZE))
        ax.yaxis.set_major_locator(MultipleLocator(BLOCK_SIZE))
        ax.grid(True, which="major", axis="both", lw=7)
        ax.set_xticklabels([])
        ax.set_yticklabels([])
        # ax.legend()

    def _display_wait_times(self, i, ax):
        rider_count = 0
        mean_wait_time = 0
        for rider in self.riders:
            logger.debug((f"{rider.index}, {rider.phase.name}, "
                          f"{rider.travel_time}, {rider.wait_time}"))
            if rider.phase == RiderPhase.RIDING and rider.travel_time == 1:
                logger.debug("Rider finished waiting")
                # Just got in the car
                rider_count += 1
                self.total_wait_time += rider.wait_time
                self.total_wait_phases += 1
                rider.wait_time = 0
        if self.total_wait_phases > 0:
            mean_wait_time = self.total_wait_time / self.total_wait_phases
        else:
            mean_wait_time = 0
        self.mean_wait_times.append(mean_wait_time)
        ax.clear()
        ax.plot(range(len(self.mean_wait_times)), self.mean_wait_times)
        ax.set_xlabel("Time (periods)")
        ax.set_ylabel("Mean wait time (periods)")

    def _display_driver_phases(self, i, ax):
        """
        Update and plot the statistics
        """
        ax.clear()
        for driver in self.drivers:
            self.total_driver_time += 1
            self.driver_phase_time[driver.phase.value] += 1
        x = []
        height = []
        labels = []
        colors = []
        for i, phase in enumerate(list(DriverPhase)):
            x.append(i)
            height.append(self.driver_phase_time[i] / self.total_driver_time)
            labels.append(phase.name)
            colors.append(sns.color_palette()[i])
        ax.bar(x, height, color=colors, tick_label=labels)
        ax.set_ylim(bottom=0, top=1)
        caption = "\n".join(
            (f"This simulation has {self.driver_count} drivers",
             f"and {self.rider_count} riders"))
        ax.text(0.85,
                0.85,
                caption,
                bbox={
                    "facecolor": sns.color_palette()[4],
                    'alpha': 0.2,
                    'pad': 8
                },
                fontsize=12,
                alpha=0.8)

    def _assign_driver(self, index, origin, destination):
        """
        Find the nearest driver to a ridehail call at x, y
        Set that driver's phase to PICKING_UP
        """
        min_distance = MAP_SIZE * 10
        assigned_driver = None
        for driver in self.drivers:
            if driver.phase == DriverPhase.AVAILABLE:
                distance = abs(driver.location[0] -
                               origin[0]) + abs(driver.location[1] - origin[1])
                if distance < min_distance:
                    min_distance = distance
                    assigned_driver = driver
        if assigned_driver:
            self.riders[index].phase = RiderPhase.WAITING
            assigned_driver.phase = DriverPhase.PICKING_UP
            assigned_driver.rider_index = index
            assigned_driver.pickup = origin
            assigned_driver.dropoff = destination
            return assigned_driver.index
        else:
            return None

    def _move(self, driver, speed):
        """
        Compute an updated position for a driver
        """
        logger.debug(f"{driver.index}, {driver.phase}, {driver.rider_index}")
        if driver.at_intersection():
            # For a driver on the way to pick up a rider, turn towards the
            if driver.phase == DriverPhase.PICKING_UP:
                direction = driver._navigate_towards(driver.location,
                                                     driver.pickup)
                if direction:
                    driver.direction = direction
                else:
                    # arrived at pickup
                    # do not move
                    driver.phase = DriverPhase.WITH_RIDER
                    rider = self.riders[driver.rider_index]
                    rider.phase = RiderPhase.RIDING
                    rider.travel_time = 0
                    logger.debug((f"Rider {rider.index} picked up: "
                                  f"wait time = {rider.wait_time}"))
                    return
            elif driver.phase == DriverPhase.WITH_RIDER:
                direction = driver._navigate_towards(driver.location,
                                                     driver.dropoff)
                if direction:
                    driver.direction = direction
                else:
                    # arrived at destination
                    # do not move
                    driver.phase = DriverPhase.AVAILABLE
                    self.riders[driver.rider_index].phase = RiderPhase.INACTIVE
                    driver.rider_index = None
                    driver.pickup = []
                    driver.dropoff = []
                    return
            elif driver.phase == DriverPhase.AVAILABLE:
                new_direction = random.choice(list(Direction))
                if abs(driver.direction.value - new_direction.value) != 2:
                    driver.direction = new_direction
                    logger.debug(
                        f"Driver {driver.index} now going {driver.direction}")
        for i, _ in enumerate(driver.location):
            driver.location[i] += speed * driver.delta()[i]
        logger.debug((f"Driver {driver.index}: "
                      f"({driver.location[0]}, {driver.location[1]})"))
        if driver.location[0] > (MAP_SIZE / 2):
            remainder = abs(driver.location[0]) % (MAP_SIZE / 2)
            logger.debug((f"Driver {driver.index} at x edge: "
                          f"remainder = {remainder}, "
                          f"{driver.location[0]} -> {remainder - MAP_SIZE/2}"))
            driver.location[0] = remainder - MAP_SIZE / 2
        elif driver.location[0] < -(MAP_SIZE / 2):
            remainder = abs(driver.location[0]) % (MAP_SIZE / 2)
            logger.debug((f"Driver {driver.index} at x edge: "
                          f"remainder = {remainder}, "
                          f"{driver.location[0]} -> {remainder - MAP_SIZE/2}"))
            driver.location[0] = remainder + MAP_SIZE / 2
        # Check for going off the top or bottom
        if driver.location[1] > (MAP_SIZE / 2):
            remainder = abs(driver.location[1]) % (MAP_SIZE / 2)
            logger.debug((f"Driver {driver.index} at y edge: "
                          f"remainder = {remainder}, "
                          f"{driver.location[1]} -> {remainder - MAP_SIZE/2}"))
            driver.location[1] = remainder - MAP_SIZE / 2
        elif driver.location[1] < -(MAP_SIZE / 2):
            remainder = abs(driver.location[1]) % (MAP_SIZE / 2)
            logger.debug((f"Driver {driver.index} at y edge: "
                          f"remainder = {remainder}, "
                          f"{driver.location[1]} -> {remainder - MAP_SIZE/2}"))
            driver.location[1] = remainder + MAP_SIZE / 2


class Rider():
    """
    A rider places a request and is taken to a destination
    """
    def __init__(self, i, x=None, y=None):
        self.index = i
        self.origin = []
        self.destination = []
        self.phase = RiderPhase.INACTIVE
        # wait time includes unassigned
        self.wait_time = 0
        self.travel_time = 0

    def set_random_origin(self):
        self.origin = [(MAP_SIZE / BLOCK_SIZE) *
                       (random.randint(-(MAP_SIZE / (2 * BLOCK_SIZE)),
                                       (MAP_SIZE / (2 * BLOCK_SIZE)))),
                       (MAP_SIZE / BLOCK_SIZE) *
                       (random.randint(-(MAP_SIZE / (2 * BLOCK_SIZE)),
                                       (MAP_SIZE / (2 * BLOCK_SIZE))))]

    def set_random_destination(self):
        self.destination = [(MAP_SIZE / BLOCK_SIZE) *
                            (random.randint(-(MAP_SIZE / (2 * BLOCK_SIZE)),
                                            (MAP_SIZE / (2 * BLOCK_SIZE)))),
                            (MAP_SIZE / BLOCK_SIZE) *
                            (random.randint(-(MAP_SIZE / (2 * BLOCK_SIZE)),
                                            (MAP_SIZE / (2 * BLOCK_SIZE))))]


class Driver():
    """
    A driver and its state

    grid has edge MAP_SIZE, in blocks spaced BLOCK_SIZE apart
    """
    def __init__(self, i, x=None, y=None):
        self.index = i
        self.location = [(MAP_SIZE / BLOCK_SIZE) *
                         (random.randint(-(MAP_SIZE / (2 * BLOCK_SIZE)),
                                         (MAP_SIZE / (2 * BLOCK_SIZE)))),
                         (MAP_SIZE / BLOCK_SIZE) *
                         (random.randint(-(MAP_SIZE / (2 * BLOCK_SIZE)),
                                         (MAP_SIZE / (2 * BLOCK_SIZE))))]
        self.direction = random.choice(list(Direction))
        self.phase = DriverPhase.AVAILABLE
        self.rider_index = None
        self.pickup = []
        self.dropoff = []

    def at_intersection(self):
        if self.location[0] % BLOCK_SIZE == 0 and self.location[
                1] % BLOCK_SIZE == 0:
            return True
        else:
            return False

    def delta(self):
        if self.direction == Direction.NORTH:
            delta = (0, 1)
        elif self.direction == Direction.EAST:
            delta = (1, 0)
        if self.direction == Direction.SOUTH:
            delta = (0, -1)
        elif self.direction == Direction.WEST:
            delta = (-1, 0)
        return delta

    def _navigate_towards(self, location, destination):
        """
        At an intersection turn towards a destination
        (perhaps a pickup, perhaps a dropoff)
        The direction is chose based on the quadrant
        relative to destination 
        Values of zero are on the borders
        """
        delta = [location[i] - destination[i] for i in (0, 1)]
        candidate_direction = []
        # go east or west?
        if (delta[0] > 0 and delta[0] < MAP_SIZE / 2) or (
                delta[0] < 0 and delta[0] <= -(MAP_SIZE / 2)):
            candidate_direction.append(Direction.WEST)
        elif delta[0] == 0:
            pass
        else:
            candidate_direction.append(Direction.EAST)
        # go north or south?
        if (delta[1] > 0 and delta[1] < MAP_SIZE / 2) or (
                delta[1] < 0 and delta[1] <= -(MAP_SIZE / 2)):
            candidate_direction.append(Direction.SOUTH)
        elif delta[1] == 0:
            pass
        else:
            candidate_direction.append(Direction.NORTH)
        if len(candidate_direction) > 0:
            direction = random.choice(candidate_direction)
        else:
            direction = None
        return direction


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
    parser.add_argument("-d",
                        "--drivers",
                        metavar="drivers",
                        action="store",
                        type=int,
                        default=20,
                        help="number of drivers")
    parser.add_argument("-r",
                        "--riders",
                        metavar="riders",
                        action="store",
                        type=int,
                        default=10,
                        help="number of riders")
    parser.add_argument("-f",
                        "--frames",
                        metavar="frames",
                        action="store",
                        type=int,
                        default=None,
                        help="number of riders")
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
    animation = RideHailAnimation(args.drivers, args.riders, args.frames,
                                  args.output)
    animation.plot()


if __name__ == '__main__':
    main()
