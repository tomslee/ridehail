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
SPEED = 2
REQUEST_THRESHOLD = 0.9  # the higher the threshold, the fewer requests

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
    There's nothing much here yet, but it will probably fill up as more plots
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


class RideHailSimulation():
    """
    Simulate a ride-hail environment, with drivers, riders, and trips
    """
    def __init__(self,
                 driver_count,
                 rider_count,
                 frame_count,
                 output=None,
                 show="all"):
        """
        Initialize the class variables and call what needs to be called.
        The dataframe "data" has a row for each case.
        It must have the following columns:
        - "date_report": the date a case is reported
        """
        self.driver_count = driver_count
        self.rider_count = rider_count
        self.frame_count = frame_count
        self.output = output
        self.show = show
        self.speed = SPEED
        self.drivers = [Driver(i) for i in range(driver_count)]
        self.riders = [Rider(i) for i in range(rider_count)]
        self.stats_total_driver_time = 0
        self.stats_driver_phase_time = [0, 0, 0]
        self.stats_mean_wait_times = []
        self.stats_total_wait_phases = 0
        self.stats_total_wait_time = 0

    def simulate(self):
        """
        Plot the trend of cumulative cases, observed at
        earlier days, evolving over time.
        """
        # initial plot
        logger.info("Plotting...")
        if self.show == "all":
            fig, axes = plt.subplots(ncols=3, figsize=(18, 6))
        elif self.show == "graphs":
            fig, axes = plt.subplots(ncols=2, figsize=(12, 6))
        elif self.show == "map":
            fig, ax = plt.subplots(figsize=(6, 6))
            axes = [ax]
        anim = FuncAnimation(fig,
                             self._next_frame,
                             frames=self.frame_count,
                             fargs=[axes],
                             interval=FRAME_INTERVAL,
                             repeat=False,
                             repeat_delay=3000)
        Plot().output(anim, plt, self.__class__.__name__, self.output)

    def _request_rides(self):
        """
        Periodically initiate a request from an inactive rider
        For riders whose request was no assigned a driver,
        make a new request.
        """
        if random.random() > REQUEST_THRESHOLD:
            # An inactive rider gets ready to make a request
            inactive_riders = [
                rider for rider in self.riders
                if rider.phase == RiderPhase.INACTIVE
            ]
            if inactive_riders:
                logger.debug(
                    f"There are {len(inactive_riders)} inactive riders")
                # choose a rider at random
                rider = random.choice(inactive_riders)
                # rider has a random origin and destination
                # and is ready to make a request
                rider.phase_change()
                logger.debug(
                    (f"Rider {rider.index} is now {rider.phase.name}"))

        # All riders without an assigned driver make a request
        # Randomize the order just in case there is some problem
        unassigned_riders = [
            rider for rider in self.riders
            if rider.phase == RiderPhase.UNASSIGNED
        ]
        if unassigned_riders:
            random.shuffle(unassigned_riders)
            logger.debug(
                f"There are {len(unassigned_riders)} unassigned riders")
            for rider in unassigned_riders:
                # Make a ride request
                # If a driver is assigned, update the rider phase
                # Driver phase is handled inside _assign_driver
                driver_index = self._assign_driver(rider)
                if driver_index:
                    rider.phase_change()
                    logger.debug(f"Driver {driver_index} assigned request")
                else:
                    logger.debug(f"No driver assigned for request")
        # Update the rider stats
        for rider in self.riders:
            if rider.phase in (RiderPhase.UNASSIGNED, RiderPhase.WAITING):
                rider.wait_time += 1
            if rider.phase == RiderPhase.RIDING:
                rider.travel_time += 1

    def _assign_driver(self, rider):
        """
        Find the nearest driver to a ridehail call at x, y
        Set that driver's phase to PICKING_UP
        """
        logger.debug("Assigning a driver to a request...")
        min_distance = MAP_SIZE * 10  # Very big
        assigned_driver = None
        # randomize the driver list to prevent early drivers
        # having an advantage in the case of equality
        available_drivers = [
            driver for driver in self.drivers
            if driver.phase == DriverPhase.AVAILABLE
        ]
        if available_drivers:
            random.shuffle(available_drivers)
            for driver in available_drivers:
                if driver.phase == DriverPhase.AVAILABLE:
                    distance = abs(driver.location[0] -
                                   rider.origin[0]) + abs(driver.location[1] -
                                                          rider.origin[1])
                    if distance < min_distance:
                        min_distance = distance
                        assigned_driver = driver
            if assigned_driver:
                assigned_driver.phase_change(rider=rider)
                return assigned_driver.index
        return None

    def _move_drivers(self, speed):
        """
        Compute an updated position for a driver
        """
        for driver in self.drivers:
            # logger.debug((f"Driver {driver.index}, "
            # f"phase={driver.phase.name}, "
            # f"with rider {driver.rider_index}"))
            if driver.at_intersection():
                # For a driver on the way to pick up a rider, turn towards the
                if driver.phase == DriverPhase.PICKING_UP:
                    direction = driver._navigate_towards(
                        driver.location, driver.pickup)
                    if direction:
                        driver.direction = direction
                    else:
                        # arrived at pickup
                        # do not move
                        driver.phase_change()
                        rider = self.riders[driver.rider_index]
                        rider.phase_change()
                        return
                elif driver.phase == DriverPhase.WITH_RIDER:
                    direction = driver._navigate_towards(
                        driver.location, driver.dropoff)
                    if direction:
                        driver.direction = direction
                    else:
                        # arrived at destination
                        # do not move
                        rider = self.riders[driver.rider_index]
                        driver.phase_change()
                        rider.phase_change()
                        return
                elif driver.phase == DriverPhase.AVAILABLE:
                    new_direction = random.choice(list(Direction))
                    if abs(driver.direction.value - new_direction.value) != 2:
                        driver.direction = new_direction
                        logger.debug((f"Driver {driver.index} "
                                      f"now going {driver.direction}"))
            for i, _ in enumerate(driver.location):
                driver.location[i] += speed * driver._delta()[i]
            logger.debug((f"Driver {driver.index} is at "
                          f"({driver.location[0]}, {driver.location[1]})"))
            if driver.location[0] > (MAP_SIZE / 2):
                remainder = abs(driver.location[0]) % (MAP_SIZE / 2)
                logger.debug(
                    (f"Driver {driver.index} at x edge: "
                     f"remainder = {remainder}, "
                     f"{driver.location[0]} -> {remainder - MAP_SIZE/2}"))
                driver.location[0] = remainder - MAP_SIZE / 2
            elif driver.location[0] < -(MAP_SIZE / 2):
                remainder = abs(driver.location[0]) % (MAP_SIZE / 2)
                logger.debug(
                    (f"Driver {driver.index} at x edge: "
                     f"remainder = {remainder}, "
                     f"{driver.location[0]} -> {remainder - MAP_SIZE/2}"))
                driver.location[0] = remainder + MAP_SIZE / 2
            # Check for going off the top or bottom
            if driver.location[1] > (MAP_SIZE / 2):
                remainder = abs(driver.location[1]) % (MAP_SIZE / 2)
                logger.debug(
                    (f"Driver {driver.index} at y edge: "
                     f"remainder = {remainder}, "
                     f"{driver.location[1]} -> {remainder - MAP_SIZE/2}"))
                driver.location[1] = remainder - MAP_SIZE / 2
            elif driver.location[1] < -(MAP_SIZE / 2):
                remainder = abs(driver.location[1]) % (MAP_SIZE / 2)
                logger.debug(
                    (f"Driver {driver.index} at y edge: "
                     f"remainder = {remainder}, "
                     f"{driver.location[1]} -> {remainder - MAP_SIZE/2}"))
                driver.location[1] = remainder + MAP_SIZE / 2

    def _next_frame(self, i, axes):
        """
        Function called from animator to generate frame i of the animation.
        """
        self._move_drivers(self.speed)
        self._request_rides()
        axis_index = 0
        if self.show in ("all", "map"):
            self._display_map(i, axes[axis_index])
            axis_index += 1
        if self.show in ("all", "graphs"):
            self._display_driver_phases(i, axes[axis_index])
            axis_index += 1
            self._display_wait_times(i, axes[axis_index])

    def _display_map(self, i, ax):
        """
        Draw the map, with drivers and riders
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

    def _display_wait_times(self, i, ax):
        """
        Display a chart with the average rider wait time
        """
        rider_count = 0
        mean_wait_time = 0
        for rider in self.riders:
            logger.debug((f"Rider {rider.index}, {rider.phase.name}, "
                          f"Travel time={rider.travel_time},"
                          f"Wait time={rider.wait_time}"))
            if rider.phase == RiderPhase.RIDING and rider.travel_time == 1:
                logger.debug("Rider finished waiting")
                # Just got in the car
                rider_count += 1
                self.stats_total_wait_time += rider.wait_time
                self.stats_total_wait_phases += 1
                rider.wait_time = 0
        if self.stats_total_wait_phases > 0:
            mean_wait_time = (self.stats_total_wait_time /
                              self.stats_total_wait_phases)
        else:
            mean_wait_time = 0
        self.stats_mean_wait_times.append(mean_wait_time)
        ax.clear()
        ax.plot(range(len(self.stats_mean_wait_times)),
                self.stats_mean_wait_times)
        ax.set_xlabel("Time (periods)")
        ax.set_ylabel("Mean wait time (periods)")

    def _display_driver_phases(self, i, ax):
        """
        Display a chart with driver time spent in each phase
        """
        ax.clear()
        for driver in self.drivers:
            self.stats_total_driver_time += 1
            self.stats_driver_phase_time[driver.phase.value] += 1
        x = []
        height = []
        labels = []
        colors = []
        for i, phase in enumerate(list(DriverPhase)):
            x.append(i)
            height.append(self.stats_driver_phase_time[i] /
                          self.stats_total_driver_time)
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

    def phase_change(self, to_phase=None):
        """
        A rider changes phase from one phase to the next.
        For now, to_phase is not used as the sequence is
        fixed
        """
        if not to_phase:
            to_phase = RiderPhase(
                (self.phase.value + 1) % len(list(RiderPhase)))
            logger.debug(
                f"Rider from_phase = {self.phase}, to_phase = {to_phase.name}")
        if self.phase == RiderPhase.INACTIVE:
            self.set_random_origin()
            self.set_random_destination()
        elif self.phase == RiderPhase.UNASSIGNED:
            self.travel_time = 0
            logger.debug((f"Rider {self.index} picked up: "
                          f"wait time={self.wait_time}"))
        elif self.phase == RiderPhase.WAITING:
            pass
        elif self.phase == RiderPhase.RIDING:
            pass
        self.phase = to_phase


class Driver():
    """
    A driver and its state

    """
    def __init__(self, i, x=None, y=None):
        """
        Create a driver at a random location.
        Grid has edge MAP_SIZE, in blocks spaced BLOCK_SIZE apart
        """
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
        """
        Check if the driver is at an intersection.

        Pickups, dropoffs, and direction changes all happen 
        at intersections.
        """
        if self.location[0] % BLOCK_SIZE == 0 and self.location[
                1] % BLOCK_SIZE == 0:
            return True
        else:
            return False

    def _delta(self):
        """
        Utility function for representing moves in the current direction
        """
        if self.direction == Direction.NORTH:
            delta = (0, 1)
        elif self.direction == Direction.EAST:
            delta = (1, 0)
        if self.direction == Direction.SOUTH:
            delta = (0, -1)
        elif self.direction == Direction.WEST:
            delta = (-1, 0)
        return delta

    def phase_change(self, to_phase=None, rider=None):
        """
        Driver phase change

        In the routine, self.phase is the *from* phase
        """
        if not to_phase:
            to_phase = DriverPhase(
                (self.phase.value + 1) % len(list(DriverPhase)))
            logger.debug(
                f"Driver from_phase = {self.phase}, to_phase = {to_phase.name}"
            )
        if self.phase == DriverPhase.AVAILABLE:
            self.rider_index = rider.index
            self.pickup = rider.origin
            self.dropoff = rider.destination
        elif self.phase == DriverPhase.PICKING_UP:
            pass
        elif self.phase == DriverPhase.WITH_RIDER:
            # Clear out information about previous trip
            self.rider_index = None
            self.pickup = []
            self.dropoff = []
        self.phase = to_phase

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
    parser = argparse.ArgumentParser(
        description="Simulate ride-hail drivers and riders.",
        usage="%(prog)s [options]",
        fromfile_prefix_chars='@')
    parser.add_argument("-d",
                        "--drivers",
                        metavar="drivers",
                        action="store",
                        type=int,
                        default=20,
                        help="number of drivers")
    parser.add_argument("-f",
                        "--frames",
                        metavar="frames",
                        action="store",
                        type=int,
                        default=None,
                        help="number of frames (periods)")
    parser.add_argument(
        "-o",
        "--output",
        metavar="output",
        action="store",
        type=str,
        default="",
        help="output to the display or as a file; gif or mp4",
    )
    parser.add_argument("-r",
                        "--riders",
                        metavar="riders",
                        action="store",
                        type=int,
                        default=10,
                        help="number of riders")
    parser.add_argument("-s",
                        "--show",
                        metavar="show",
                        action="store",
                        type=str,
                        default="all",
                        help="show 'graphs', 'map', ['all'] or 'none'")
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
    simulation = RideHailSimulation(args.drivers, args.riders, args.frames,
                                    args.output, args.show)
    simulation.simulate()


if __name__ == '__main__':
    main()
