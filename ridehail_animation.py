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

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------------
# Parameters
# -------------------------------------------------------------------------------
MAP_SIZE = 10
FRAME_INTERVAL = 50
MAX_PERIODS = 1000
INTERPOLATION_POINTS = 10  # Actually one more than the interpolations
REQUEST_THRESHOLD = 0.1  # the higher the threshold, the fewer requests
AVAILABLE_DRIVERS_MOVING = True
GLOBAL_REQUEST_THRESHOLD = True

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


# ------------------------------------------------------------------------------
# Enumerations
# ------------------------------------------------------------------------------
class Direction(Enum):
    NORTH = [0, 1]
    EAST = [1, 0]
    SOUTH = [0, -1]
    WEST = [-1, 0]


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


class RequestModel(Enum):
    THRESHOLD_GLOBAL = 0
    THRESHOLD_PER_DRIVER = 1


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
                 period_count=MAX_PERIODS,
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
        self.period_count = period_count
        self.frame_count = period_count * INTERPOLATION_POINTS
        self.output = output
        self.show = show
        self.drivers = [Driver(i) for i in range(driver_count)]
        self.riders = [Rider(i) for i in range(rider_count)]
        self.stats_total_driver_time = 0
        self.stats_driver_phase_time = [0, 0, 0]
        self.stats_mean_wait_times = []
        self.stats_driver_phase_fractions = [[], [], []]
        self.stats_total_wait_phases = 0
        self.stats_total_wait_time = 0
        self.color_palette = sns.color_palette()
        if GLOBAL_REQUEST_THRESHOLD:
            self.request_model = RequestModel.THRESHOLD_GLOBAL
        else:
            self.request_model = RequestModel.THRESHOLD_PER_DRIVER

    def simulate(self):
        """
        Plot the trend of cumulative cases, observed at
        earlier days, evolving over time.
        """
        # initial plot
        if self.show == "none":
            for period in range(self.period_count):
                self._move_drivers()
                self._update_driver_directions()
                self._request_rides(self.request_model)
                self._update_stats(period)
        else:
            self._animate()
        if (self.drivers and self.riders
                and len(self.stats_mean_wait_times) > 0):
            print((f"{self.driver_count}, "
                   f"{self.rider_count}, "
                   f"{self.stats_driver_phase_fractions[0][-1]:.2f}, "
                   f"{self.stats_driver_phase_fractions[1][-1]:.2f}, "
                   f"{self.stats_driver_phase_fractions[2][-1]:.2f}, "
                   f"{self.stats_mean_wait_times[-1]:.2f}"))

    def _request_rides(self, request_model):
        """
        Periodically initiate a request from an inactive rider
        For riders whose request was no assigned a driver,
        make a new request.
        """
        inactive_riders = [
            rider for rider in self.riders
            if rider.phase == RiderPhase.INACTIVE
        ]
        if not inactive_riders:
            return
        if request_model == RequestModel.THRESHOLD_GLOBAL:
            if random.random() > REQUEST_THRESHOLD:
                logger.debug(
                    f"There are {len(inactive_riders)} inactive riders")
                # choose a rider at random
                rider = random.choice(inactive_riders)
                # rider has a random origin and destination
                # and is ready to make a request
                rider._phase_change()
                logger.debug(
                    (f"Rider {rider.index} is now {rider.phase.name}"))
        elif request_model == RequestModel.THRESHOLD_PER_DRIVER:
            for rider in inactive_riders:
                if random.random() > REQUEST_THRESHOLD:
                    # choose a rider at random
                    # rider has a random origin and destination
                    # and is ready to make a request
                    rider._phase_change()
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
                assigned_driver = self._assign_driver(rider)
                if assigned_driver:
                    assigned_driver._phase_change(rider=rider)
                    rider._phase_change()
                    logger.debug(
                        f"Driver {assigned_driver.index} assigned request")
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
        min_distance = MAP_SIZE * 100  # Very big
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
        return assigned_driver

    def _move_drivers(self):
        """
        Compute an updated position for a driver
        """
        if AVAILABLE_DRIVERS_MOVING:
            moving_drivers = [driver for driver in self.drivers]
        else:
            moving_drivers = [
                driver for driver in self.drivers
                if driver.phase != DriverPhase.AVAILABLE
            ]
        for driver in moving_drivers:
            # logger.debug((f"Driver {driver.index}, "
            # f"phase={driver.phase.name}, "
            # f"with rider {driver.rider_index}"))
            quadrant_length = MAP_SIZE / 2
            for i, _ in enumerate(driver.location):
                driver.location[i] += driver.direction.value[i]
                # Handle going off the edge
                driver.location[i] = (
                    (driver.location[i] + quadrant_length) % MAP_SIZE -
                    quadrant_length)
                if abs(driver.location[i]) == quadrant_length:
                    driver.location[i] = abs(driver.location[i])
            logger.debug((f"Driver {driver.index} is at "
                          f"({driver.location[0]}, {driver.location[1]})"))

    def _update_driver_directions(self):
        """
        Decide which way to turn, and change phase if needed
        """
        for driver in self.drivers:
            original_direction = driver.direction
            if driver.phase == DriverPhase.PICKING_UP:
                # For a driver on the way to pick up a rider, turn towards the
                # pickup point
                driver.direction = driver._navigate_towards(
                    driver.location, driver.pickup)
                if not driver.direction:
                    # arrived at pickup
                    # do not move
                    driver._phase_change()
                    rider = self.riders[driver.rider_index]
                    rider._phase_change()
                    driver.direction = original_direction
            elif driver.phase == DriverPhase.WITH_RIDER:
                driver.direction = driver._navigate_towards(
                    driver.location, driver.dropoff)
                if not driver.direction:
                    # arrived at destination
                    # do not move
                    rider = self.riders[driver.rider_index]
                    driver._phase_change()
                    rider._phase_change()
                    driver.direction = original_direction
            elif driver.phase == DriverPhase.AVAILABLE:
                new_direction = random.choice(list(Direction))
                # No u turns: is_opposite is -1 for opposite,
                # in which case keep on going
                is_opposite = 0
                for i in [0, 1]:
                    is_opposite += (new_direction.value[i] *
                                    driver.direction.value[i])
                if is_opposite > -1:
                    driver.direction = new_direction
                logger.debug((f"Driver {driver.index} "
                              f"now going {driver.direction.name}"))

    def _update_driver_stats(self, period):
        """
        Record the phase for each driver
        """
        for driver in self.drivers:
            self.stats_total_driver_time += 1
            self.stats_driver_phase_time[driver.phase.value] += 1
        for phase in list(DriverPhase):
            fraction = (self.stats_driver_phase_time[phase.value] /
                        self.stats_total_driver_time)
            self.stats_driver_phase_fractions[phase.value].append(fraction)
        logger.info((f"Driver phase fractions: "
                     f"{DriverPhase(0).name}: "
                     f"{self.stats_driver_phase_fractions[0][-1]:.2f}, "
                     f"{DriverPhase(1).name}: "
                     f"{self.stats_driver_phase_fractions[1][-1]:.2f}, "
                     f"{DriverPhase(2).name}: "
                     f"{self.stats_driver_phase_fractions[2][-1]:.2f}"))

    def _update_rider_stats(self, period):
        """
        Mean wait times for riders
        Rider stats: we get the wait time for those drivers who
        have just got in a car, and so have a completed wait
        """
        just_picked_up_riders = [
            rider for rider in self.riders
            if rider.phase == RiderPhase.RIDING and rider.travel_time == 1
        ]
        for rider in just_picked_up_riders:
            logger.debug((f"Rider {rider.index}, {rider.phase.name}, "
                          f"Travel time={rider.travel_time},"
                          f"Wait time={rider.wait_time}"))
            self.stats_total_wait_time += rider.wait_time
            self.stats_total_wait_phases += 1
        # update the mean wait time
        mean_wait_time = 0
        if self.stats_total_wait_phases > 0:
            mean_wait_time = (self.stats_total_wait_time /
                              self.stats_total_wait_phases)
        else:
            mean_wait_time = 0
        self.stats_mean_wait_times.append(mean_wait_time)
        logger.info((f"Mean rider wait time: "
                     f"{self.stats_mean_wait_times[-1]:.2f}"))

    def _update_stats(self, period):
        """
        Called after each frame to update system-wide statistics
        """
        if self.drivers:
            self._update_driver_stats(period)
        if self.riders:
            self._update_rider_stats(period)

    def _animate(self):
        """
        Do the simulation but with displays
        """
        if self.show == "all":
            fig, axes = plt.subplots(ncols=3, figsize=(18, 6))
        elif self.show == "stats":
            fig, axes = plt.subplots(ncols=2, figsize=(12, 6))
        elif self.show == "map":
            fig, ax = plt.subplots(figsize=(6, 6))
            axes = [ax]
        animation = FuncAnimation(fig,
                                  self._next_frame,
                                  frames=(self.frame_count),
                                  fargs=[axes],
                                  interval=FRAME_INTERVAL,
                                  repeat=False,
                                  repeat_delay=3000)
        Plot().output(animation, plt, self.__class__.__name__, self.output)

    def _next_frame(self, i, axes):
        """
        Function called from animator to generate frame i of the animation.
        """
        if i % INTERPOLATION_POINTS == 0:
            # A "real" time point. Update the system
            self._move_drivers()
            self._update_driver_directions()
            self._request_rides(self.request_model)
            self._update_stats(int(i / INTERPOLATION_POINTS))
        axis_index = 0
        if self.show in ("all", "map"):
            self._draw_map(i, axes[axis_index])
            axis_index += 1
        if self.show in ("all", "stats"):
            self._draw_driver_phases(i, axes[axis_index])
            axis_index += 1
            self._draw_rider_wait_times(i, axes[axis_index])

    def _draw_map(self, i, ax):
        """
        Draw the map, with drivers and riders
        """
        ax.clear()
        # Get the interpolation point
        interpolation = i % INTERPOLATION_POINTS
        distance_increment = interpolation / INTERPOLATION_POINTS
        # Plot the drivers: one set of arrays for each direction
        # as each direction has a common marker
        x_dict = {}
        y_dict = {}
        color = {}
        size = {}
        markers = ('^', '>', 'v', '<')
        # driver markers:
        sizes = (60, 100, 100)
        for direction in list(Direction):
            x_dict[direction.name] = []
            y_dict[direction.name] = []
            color[direction.name] = []
            size[direction.name] = []
        locations = [x_dict, y_dict]

        for driver in self.drivers:
            for i in [0, 1]:
                # Position, including edge correction
                x_prime = (driver.location[i] + MAP_SIZE / 2 +
                           distance_increment * driver.direction.value[i])
                x = (x_prime % MAP_SIZE) - MAP_SIZE / 2
                locations[i][driver.direction.name].append(x)
            size[driver.direction.name].append(sizes[driver.phase.value])
            color[driver.direction.name].append(
                self.color_palette[driver.phase.value])
        logger.debug(f"Frame {i}")
        for i, direction in enumerate(list(Direction)):
            ax.scatter(locations[0][direction.name],
                       locations[1][direction.name],
                       s=size[direction.name],
                       marker=markers[i],
                       color=color[direction.name])

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
                   color=self.color_palette[7],
                   alpha=0.5,
                   label="Ride request")
        ax.scatter(x_destination,
                   y_destination,
                   s=120,
                   marker='*',
                   color=self.color_palette[6],
                   label="Ride destination")

        # Draw the map: the second term is a bit of wrapping
        # so that the outside road is shown properly
        display_limit = MAP_SIZE / 2 + 0.25
        ax.set_xlim(-display_limit, display_limit)
        ax.set_ylim(-display_limit, display_limit)
        ax.xaxis.set_major_locator(MultipleLocator(1))
        ax.yaxis.set_major_locator(MultipleLocator(1))
        ax.grid(True, which="major", axis="both", lw=7)
        ax.set_xticklabels([])
        ax.set_yticklabels([])

    def _draw_driver_phases(self, i, ax):
        """
        Display a chart with driver time spent in each phase
        """
        period = int(i / INTERPOLATION_POINTS)
        if i % INTERPOLATION_POINTS == 0:
            ax.clear()
            draw_barchart = False
            if draw_barchart:
                x = []
                height = []
                labels = []
                colors = []
                for phase in list(DriverPhase):
                    x.append(phase.value)
                    height.append(self.stats_driver_phase_time[phase.value] /
                                  self.stats_total_driver_time)
                    labels.append(phase.name)
                    colors.append(self.color_palette[phase.value])
                caption = "\n".join(
                    (f"This simulation has {self.driver_count} drivers",
                     f"and {self.rider_count} riders"))
                ax.bar(x, height, color=colors, tick_label=labels)
                ax.set_ylim(bottom=0, top=1)
                ax.text(0.75,
                        0.85,
                        caption,
                        bbox={
                            "facecolor": self.color_palette[4],
                            'alpha': 0.2,
                            'pad': 8
                        },
                        fontsize=12,
                        alpha=0.8)
            else:
                for phase in list(DriverPhase):
                    ax.plot(self.stats_driver_phase_fractions[phase.value],
                            color=self.color_palette[phase.value],
                            label=phase.name)

                ax.set_ylim(bottom=0, top=1)
                ax.set_xlabel("Time (periods)")
                ax.set_ylabel("Fraction of driver time in phase")
                # caption = "Drivers"
                # ax.text(0.05,
                # 0.85,
                # caption,
                # bbox={
                # "facecolor": self.color_palette[4],
                # 'alpha': 0.2,
                # 'pad': 8
                # },
                # fontsize=12,
                # alpha=0.8)
                ax.legend()

    def _draw_rider_wait_times(self, i, ax):
        """
        Display a chart with the average rider wait time
        """
        period = int(i / INTERPOLATION_POINTS)
        if i == 0:
            ax.plot(self.stats_mean_wait_times)
            ax.set_xlabel("Time (periods)")
            ax.set_ylabel("Mean wait time (periods)")
            ax.set_xlim(0, self.period_count)
            ax.set_ylim(0, 5)
            lines = ax.get_lines()
        if i > 0:  # and i % INTERPOLATION_POINTS == 0:
            # lines[0].set_data(range(len(self.stats_mean_wait_times)))
            lines = ax.get_lines()
            logging.info((f"Frame {i}, lines = {len(lines)}"))
            plt.setp(lines, [self.stats_mean_wait_times])
        return lines
        # caption = "Riders"
        # ax.text(0.05,
        # 0.85,
        # caption,
        # bbox={
        # "facecolor": self.color_palette[4],
        # 'alpha': 0.2,
        # 'pad': 8
        # },
        # fontsize=12,
        # alpha=0.8)


class Agent():
    """
    Properties and methods that are common to riders and drivers
    """
    def _set_random_location(self):
        # Maximum absolute value is half the blocks
        max_abs_location = MAP_SIZE / 2
        location = [None, None]
        for i in [0, 1]:
            location[i] = random.randint(-max_abs_location, max_abs_location)
            if abs(location[i]) >= max_abs_location:
                location[i] = abs(location[i])
        return location


class Rider(Agent):
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

    def _phase_change(self, to_phase=None):
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
            self.origin = self._set_random_location()
            self.destination = self._set_random_location()
            self.wait_time = 0
        elif self.phase == RiderPhase.UNASSIGNED:
            self.travel_time = 0
            logger.debug((f"Rider {self.index} assigned a driver: "
                          f"this phase = {self.phase.name}, "
                          f"next phase = {to_phase.name}"))
        elif self.phase == RiderPhase.WAITING:
            pass
            logger.debug((f"Rider {self.index} picked up: "
                          f"this phase = {self.phase.name}, "
                          f"next phase = {to_phase.name}"))
        elif self.phase == RiderPhase.RIDING:
            logger.debug((f"Rider {self.index} dropped off: "
                          f"this phase = {self.phase.name}, "
                          f"next phase = {to_phase.name}"))
            pass
        logger.info((f"Rider: {self.phase.name} -> {to_phase.name}"))
        self.phase = to_phase


class Driver(Agent):
    """
    A driver and its state

    """
    def __init__(self, i, x=None, y=None):
        """
        Create a driver at a random location.
        Grid has edge MAP_SIZE, in blocks spaced 1 apart
        """
        self.index = i
        self.location = self._set_random_location()
        self.direction = random.choice(list(Direction))
        self.phase = DriverPhase.AVAILABLE
        self.rider_index = None
        self.pickup = []
        self.dropoff = []

    def _phase_change(self, to_phase=None, rider=None):
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
        logger.info((f"Driver: {self.phase.name} -> {to_phase.name}"))
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
        quadrant_length = MAP_SIZE / 2
        candidate_direction = []
        # go east or west?
        if (delta[0] > 0 and delta[0] < quadrant_length):
            candidate_direction.append(Direction.WEST)
        elif (delta[0] < 0 and delta[0] <= -quadrant_length):
            candidate_direction.append(Direction.WEST)
        elif delta[0] == 0:
            pass
        else:
            candidate_direction.append(Direction.EAST)
        # go north or south?
        if (delta[1] > 0 and delta[1] < quadrant_length) or (
                delta[1] < 0 and delta[1] <= -quadrant_length):
            candidate_direction.append(Direction.SOUTH)
        elif delta[1] == 0:
            pass
        else:
            candidate_direction.append(Direction.NORTH)
        if len(candidate_direction) > 0:
            direction = random.choice(candidate_direction)
        else:
            direction = None
        logger.info((f"Location = ({location[0]}, {location[1]}), "
                     f"destination = ({destination[0]}, {destination[1]}), "
                     f"direction = {direction}"))
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
    parser.add_argument("-p",
                        "--periods",
                        metavar="periods",
                        action="store",
                        type=int,
                        default=500,
                        help="number of periods")
    parser.add_argument("-l",
                        "--logfile",
                        metavar="logfile",
                        action="store",
                        type=str,
                        default=None,
                        help=("logfile name. By default, log messages "
                              "are written to the screen only"))
    parser.add_argument(
        "-o",
        "--output",
        metavar="output",
        action="store",
        type=str,
        default="",
        help="output to the display or as a file; gif or mp4",
    )
    parser.add_argument("-q",
                        "--quiet",
                        action="store_true",
                        help="log only warnings and errors")
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
                        default="map",
                        help="show 'stats', ['map'], 'all' or 'none'")
    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="log all messages, including debug")
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
    args = parse_args()
    if args.verbose:
        loglevel = "DEBUG"
    elif args.quiet:
        loglevel = "WARN"
    else:
        loglevel = "INFO"
    if args.logfile:
        logging.basicConfig(filename=args.logfile,
                            filemode='w',
                            level=getattr(logging, loglevel.upper()),
                            format='%(asctime)-15s %(levelname)-8s%(message)s')
    else:
        logging.basicConfig(level=getattr(logging, loglevel.upper()),
                            format='%(asctime)-15s %(levelname)-8s%(message)s')
    logger.debug("Logging debug messages...")
    # config = read_config(args)
    simulation = RideHailSimulation(args.drivers, args.riders, args.periods,
                                    args.output, args.show)
    simulation.simulate()


if __name__ == '__main__':
    main()
