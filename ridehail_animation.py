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
import sys
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
FRAME_INTERVAL = 50
MAX_PERIODS = 1000
AVAILABLE_DRIVERS_MOVING = True
GARBAGE_COLLECTION_INTERVAL = 10
ROLLING_WINDOW = 20
FIRST_REQUEST_OFFSET = 3

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


class TripPhase(Enum):
    INACTIVE = 0
    UNASSIGNED = 1
    WAITING = 2
    RIDING = 3
    FINISHED = 4


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


class TotalStat(Enum):
    DRIVER_TIME = 0
    WAIT_TIME = 1
    TRIP_COUNT = 2


class PlotStat(Enum):
    DRIVER_FRACTION_AVAILABLE = "Available"
    DRIVER_FRACTION_PICKING_UP = "Picking Up"
    DRIVER_FRACTION_WITH_RIDER = "With Rider"
    TRIP_MEAN_WAIT_TIME = "Mean wait time"


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


class City():
    """
    Location-specific stuff
    """
    def __init__(self, city_size, display_fringe=0.25):
        self.city_size = city_size
        self.display_fringe = display_fringe

    def set_random_location(self):
        location = [None, None]
        for i in [0, 1]:
            location[i] = random.randint(0, self.city_size - 1)
        return location


class RideHailSimulation():
    """
    Simulate a ride-hail environment, with drivers and trips
    """
    def __init__(self,
                 driver_count,
                 request_interval,
                 interpolate=0,
                 period_count=MAX_PERIODS,
                 city_size=10,
                 output=None,
                 show="all"):
        """
        Initialize the class variables and call what needs to be called.
        The dataframe "data" has a row for each case.
        It must have the following columns:
        - "date_report": the date a case is reported
        """
        self.driver_count = driver_count
        self.request_interval = request_interval
        self.city = City(city_size)
        self.period_count = period_count
        self.interpolation_points = interpolate
        self.frame_count = period_count * self.interpolation_points
        self.output = output
        self.show = show
        self.drivers = [Driver(i, self.city) for i in range(driver_count)]
        self.trips = []
        self.color_palette = sns.color_palette()
        self.stats = {}
        for phase in list(DriverPhase):
            self.stats[phase] = []
        for phase in list(TripPhase):
            self.stats[phase] = []
        for total in list(TotalStat):
            self.stats[total] = []
        for stat in list(PlotStat):
            self.stats[stat] = []
        self.csv_driver = "driver.csv"
        self.csv_trip = "trip.csv"

    # (todays_date-datetime.timedelta(10), periods=10, freq='D')

    def simulate(self):
        """
        Plot the trend of cumulative cases, observed at
        earlier days, evolving over time.
        """
        # initial plot
        if self.show == "none":
            for starting_period in range(self.period_count):
                self._next_period(starting_period)
        else:
            self._animate()
        self._write_results()

    def _next_period(self, starting_period):
        """
        Call all those functions needed to simulate the next period
        """
        logger.debug(f"------- Period {starting_period} -----------")
        self._prepare_stat_lists()
        for driver in self.drivers:
            driver.update_location()
            driver.update_direction()
            if driver.trip_index is not None:
                trip = self.trips[driver.trip_index]
            if (driver.phase == DriverPhase.PICKING_UP
                    and driver.location == driver.pickup):
                # the driver has arrived at the pickup spot and picks up
                # the rider
                driver.phase_change()
                trip.phase_change()
            elif (driver.phase == DriverPhase.WITH_RIDER
                  and driver.location == driver.dropoff):
                # the driver has arrived at the dropoff point and the trip ends
                driver.phase_change()
                trip.phase_change()
                self._update_aggregate_trip_stats(trip)
                # self._collect_garbage()
        self._request_rides(starting_period)
        self._update_period_stats(starting_period)

    def _request_rides(self, period):
        """
        Periodically initiate a request from an inactive rider
        For requests not assigned a driver, repeat the request.
        """
        if (period + FIRST_REQUEST_OFFSET) % self.request_interval == 0:
            trip = Trip(len(self.trips), self.city)
            self.trips.append(trip)
            # the trip has a random origin and destination
            # and is ready to make a request.
            # This sets the trip to TripPhase.UNNASSIGNED
            # as no driver is assigned here
            trip.phase_change()

        # All trips without an assigned driver make a request
        # Randomize the order just in case there is some problem
        unassigned_trips = [
            trip for trip in self.trips if trip.phase == TripPhase.UNASSIGNED
        ]
        if unassigned_trips:
            random.shuffle(unassigned_trips)
            logger.debug(f"There are {len(unassigned_trips)} unassigned trips")
            for trip in unassigned_trips:
                # Make a ride request
                # If a driver is assigned, update the trip phase
                assigned_driver = self._assign_driver(trip)
                if assigned_driver:
                    assigned_driver.phase_change(trip=trip)
                    trip.phase_change()
                else:
                    logger.debug(f"No driver assigned for trip {trip.index}")

    def _assign_driver(self, trip):
        """
        Find the nearest driver to a ridehail call at x, y
        Set that driver's phase to PICKING_UP
        """
        logger.debug("Assigning a driver to a request...")
        min_distance = self.city.city_size * 100  # Very big
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
                distance = abs(driver.location[0] -
                               trip.origin[0]) + abs(driver.location[1] -
                                                     trip.origin[1])
                if distance < min_distance:
                    min_distance = distance
                    assigned_driver = driver
        return assigned_driver

    def _prepare_stat_lists(self):
        """
        Add an item to the end of each stats list
        to hold this period's statistics.
        """
        # create a place to hold stats from this period
        for key, value in self.stats.items():
            if len(value) > 0:
                # totals get the previous number
                # stats for the driver phases are summed totals
                value.append(value[-1])
            else:
                value.append(0)

    def _update_period_stats(self, period):
        """
        Called after each frame to update system-wide statistics
        """
        # Update base stats
        if self.drivers:
            for driver in self.drivers:
                self.stats[driver.phase][-1] += 1
                self.stats[TotalStat.DRIVER_TIME][-1] += 1
        if self.trips:
            for trip in self.trips:
                trip.phase_time[trip.phase] += 1
        if self.stats[TotalStat.TRIP_COUNT][-1] > 0:
            self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][-1] = (
                self.stats[TotalStat.WAIT_TIME][-1] /
                self.stats[TotalStat.TRIP_COUNT][-1])
        else:
            self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][-1] = 0
        # Compute aggregate stats for plotting
        self.stats[PlotStat.DRIVER_FRACTION_AVAILABLE][-1] = (
            self.stats[DriverPhase.AVAILABLE][-1] /
            self.stats[TotalStat.DRIVER_TIME][-1])
        self.stats[PlotStat.DRIVER_FRACTION_PICKING_UP][-1] = (
            self.stats[DriverPhase.PICKING_UP][-1] /
            self.stats[TotalStat.DRIVER_TIME][-1])
        self.stats[PlotStat.DRIVER_FRACTION_WITH_RIDER][-1] = (
            self.stats[DriverPhase.WITH_RIDER][-1] /
            self.stats[TotalStat.DRIVER_TIME][-1])

    def _update_aggregate_trip_stats(self, trip):
        """
        Update trip stats.
        This may be recorded on the period before the driver stats
        are updated.
        """
        self.stats[TripPhase.UNASSIGNED][-1] += trip.phase_time[
            TripPhase.UNASSIGNED]
        self.stats[TripPhase.WAITING][-1] += trip.phase_time[TripPhase.WAITING]
        self.stats[TripPhase.RIDING][-1] += trip.phase_time[TripPhase.RIDING]
        self.stats[TotalStat.TRIP_COUNT][-1] += 1
        # Bad naming: the WAIT_TIME includes both WAITING and UNASSIGNED
        self.stats[TotalStat.WAIT_TIME][-1] += trip.phase_time[
            TripPhase.UNASSIGNED]
        self.stats[TotalStat.WAIT_TIME][-1] += trip.phase_time[
            TripPhase.WAITING]

    def _collect_garbage(self):
        """
        Garbage collect the list of trips to get rid of the finished ones
        Requires that driver trip_index values be re-assigned
        """
        self.trips = [
            trip for trip in self.trips if trip.phase != TripPhase.FINISHED
        ]
        for i, trip in enumerate(self.trips):
            for driver in self.drivers:
                driver.trip_index = (i if driver.trip_index == trip.index else
                                     driver.trip_index)
            trip.index = i

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
        if i % self.interpolation_points == 0:
            # A "real" time point. Update the system
            starting_period = int(i / self.interpolation_points)
            self._next_period(starting_period)
        axis_index = 0
        if self.show in ("all", "map"):
            self._draw_map(i, axes[axis_index])
            axis_index += 1
        if self.show in ("all", "stats"):
            self._draw_driver_phases(i, axes[axis_index])
            axis_index += 1
            self._draw_trip_wait_times(i, axes[axis_index])

    def _draw_map(self, i, ax):
        """
        Draw the map, with drivers and trips
        """
        ax.clear()
        # Get the interpolation point
        interpolation = i % self.interpolation_points
        distance_increment = interpolation / self.interpolation_points
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
                x = (driver.location[i] +
                     distance_increment * driver.direction.value[i])
                x = ((x + self.city.display_fringe) % self.city.city_size -
                     self.city.display_fringe)
                # Make the displayed-position fit on the map, with
                # fringe city.display_fringe around the edges
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
                       color=color[direction.name],
                       alpha=0.7)

        x_origin = []
        y_origin = []
        x_destination = []
        y_destination = []
        for trip in self.trips:
            if trip.phase in (TripPhase.UNASSIGNED, TripPhase.WAITING):
                x_origin.append(trip.origin[0])
                y_origin.append(trip.origin[1])
            if trip.phase == TripPhase.RIDING:
                x_destination.append(trip.destination[0])
                y_destination.append(trip.destination[1])
        ax.scatter(x_origin,
                   y_origin,
                   s=80,
                   marker='o',
                   color=self.color_palette[7],
                   alpha=0.7,
                   label="Ride request")
        ax.scatter(x_destination,
                   y_destination,
                   s=120,
                   marker='*',
                   color=self.color_palette[6],
                   label="Ride destination")

        # Draw the map: the second term is a bit of wrapping
        # so that the outside road is shown properly
        ax.set_xlim(-self.city.display_fringe,
                    self.city.city_size - self.city.display_fringe)
        ax.set_ylim(-self.city.display_fringe,
                    self.city.city_size - self.city.display_fringe)
        ax.xaxis.set_major_locator(MultipleLocator(1))
        ax.yaxis.set_major_locator(MultipleLocator(1))
        ax.grid(True, which="major", axis="both", lw=7)
        ax.set_xticklabels([])
        ax.set_yticklabels([])

    def _draw_driver_phases(self, i, ax):
        """
        Display a chart with driver time spent in each phase
        """
        # period = int(i / self.interpolation_points)
        if i % self.interpolation_points == 0:
            ax.clear()
            draw_barchart = False
            if draw_barchart:
                x = []
                height = []
                labels = []
                colors = []
                for phase in list(PlotStat):
                    if phase != PlotStat.TRIP_MEAN_WAIT_TIME:
                        x.append(phase.value)
                        height.append(self.stats[phase][-1])
                        labels.append(phase.name)
                        colors.append(self.color_palette[phase.value])
                caption = "\n".join(
                    (f"This simulation has {self.driver_count} drivers",
                     f"and one trip every {self.request_interval} periods"))
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
                for index, phase in enumerate(list(PlotStat)):
                    if phase != PlotStat.TRIP_MEAN_WAIT_TIME:
                        ax.plot(self.stats[phase],
                                color=self.color_palette[index],
                                label=phase.name)

                # ax.set_ylim(bottom=0, top=1)
                ax.set_xlabel("Time (periods)")
                ax.set_ylabel("Fraction of driver time in phase")
                ax.legend()

    def _draw_trip_wait_times(self, i, ax):
        """
        Display a chart with the average trip wait time
        """
        if i % self.interpolation_points == 0:
            ax.clear()
            ax.plot(self.stats[PlotStat.TRIP_MEAN_WAIT_TIME])
            ax.set_xlabel("Time (periods)")
            ax.set_ylabel("Mean wait time (periods)")
            # ax.set_xlim(0, self.period_counte
            # ax.set_ylim(0, self.city.city_size)

    def _write_results(self):
        """
        Print the results to CSV files
        """
        with open(self.csv_driver, mode="w") as f:
            f.write(("period, available, picking_up, with_rider, "
                     "driver_time, frac_avail, "
                     "frac_pick, frac_with\n"))
            for i in range(self.period_count):
                f.write((
                    f"  {i:04}, "
                    f"     {self.stats[DriverPhase.AVAILABLE][i]:04}, "
                    f"      {self.stats[DriverPhase.PICKING_UP][i]:04}, "
                    f"      {self.stats[DriverPhase.WITH_RIDER][i]:04}, "
                    f"       {self.stats[TotalStat.DRIVER_TIME][i]:04}, "
                    f"     {self.stats[PlotStat.DRIVER_FRACTION_AVAILABLE][i]:.3f}, "
                    f"    {self.stats[PlotStat.DRIVER_FRACTION_PICKING_UP][i]:.3f}, "
                    f" {self.stats[PlotStat.DRIVER_FRACTION_WITH_RIDER][i]:.3f}\n"
                ))
        with open(self.csv_trip, mode="w") as f:
            f.write(("period, inactive, unassigned, "
                     "waiting, riding, finished, "
                     "trips, wait, mean wait\n"))
            for i in range(self.period_count):
                f.write(
                    (f"  {i:04}, "
                     f"    {self.stats[TripPhase.INACTIVE][i]:04}, "
                     f"      {self.stats[TripPhase.UNASSIGNED][i]:04}, "
                     f"   {self.stats[TripPhase.WAITING][i]:04}, "
                     f"  {self.stats[TripPhase.RIDING][i]:04}, "
                     f"    {self.stats[TripPhase.FINISHED][i]:04}, "
                     f"{self.stats[TotalStat.TRIP_COUNT][i]:04}, "
                     f"{self.stats[TotalStat.WAIT_TIME][i]:04}, "
                     f"    {self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][i]:.3f}\n"
                     ))


class Agent():
    """
    Properties and methods that are common to trips and drivers
    """
    pass


class Trip(Agent):
    """
    A rider places a request and is taken to a destination
    """
    def __init__(self, i, city, location=[0, 0]):
        self.index = i
        self.city = city
        self.origin = self.city.set_random_location()
        self.destination = self.city.set_random_location()
        # Don't allow the origin and destination to be the same
        while self.destination == self.origin:
            self.destination = self.city.set_random_location()
        self.phase = TripPhase.INACTIVE
        self.phase_time = {}
        for phase in list(TripPhase):
            self.phase_time[phase] = 0

    def phase_change(self, to_phase=None):
        """
        A trip changes phase from one phase to the next.
        On calling this function, the trip is in phase
        self.phase. It will change to the next phase.
        For now, the "to_phase" argument is not used as
        the sequence is fixed.
        """
        if not to_phase:
            to_phase = TripPhase((self.phase.value + 1) % len(list(TripPhase)))
        logger.debug(
            (f"Trip {self.index}: {self.phase.name} -> {to_phase.name}"))
        self.phase = to_phase


class Driver(Agent):
    """
    A driver and its state

    """
    def __init__(self, i, city, location=[0, 0]):
        """
        Create a driver at a random location.
        Grid has edge self.city.city_size, in blocks spaced 1 apart
        """
        self.index = i
        self.city = city
        self.location = self.city.set_random_location()
        self.direction = random.choice(list(Direction))
        self.phase = DriverPhase.AVAILABLE
        self.trip_index = None
        self.pickup = []
        self.dropoff = []

    def phase_change(self, to_phase=None, trip=None):
        """
        Driver phase change
        In the routine, self.phase is the *from* phase
        """
        if not to_phase:
            # The usual case: move to the next phase in sequence
            to_phase = DriverPhase(
                (self.phase.value + 1) % len(list(DriverPhase)))
        logger.debug(
            f"Driver from_phase = {self.phase}, to_phase = {to_phase.name}")
        if self.phase == DriverPhase.AVAILABLE:
            # Driver is assigned to a new trip
            self.trip_index = trip.index
            self.pickup = trip.origin
            self.dropoff = trip.destination
        elif self.phase == DriverPhase.PICKING_UP:
            pass
        elif self.phase == DriverPhase.WITH_RIDER:
            # Driver has arrived at the destination and the trip
            # is finishing.
            # Clear out information about the now-finished trip
            # from the driver's state
            self.trip_index = None
            self.pickup = []
            self.dropoff = []
        logger.debug((f"Driver {self.index} for {self.trip_index}: "
                      f"{self.phase.name} "
                      f"-> {to_phase.name}"))
        self.phase = to_phase

    def update_direction(self):
        """
        Decide which way to turn, and change phase if needed
        """
        original_direction = self.direction
        if self.phase == DriverPhase.PICKING_UP:
            # For a driver on the way to pick up a trip, turn towards the
            # pickup point
            new_direction = self._navigate_towards(self.city, self.location,
                                                   self.pickup)
        elif self.phase == DriverPhase.WITH_RIDER:
            new_direction = self._navigate_towards(self.city, self.location,
                                                   self.dropoff)
        elif self.phase == DriverPhase.AVAILABLE:
            new_direction = random.choice(list(Direction))
            # No u turns: is_opposite is -1 for opposite,
            # in which case keep on going
            is_opposite = 0
            for i in [0, 1]:
                is_opposite += (new_direction.value[i] *
                                self.direction.value[i])
            if is_opposite == -1:
                new_direction = original_direction
        if not new_direction:
            # arrived at destination (pickup or dropoff)
            new_direction = original_direction
        self.direction = new_direction

    def update_location(self):
        """
        Update the driver's location
        """
        location = self.location
        if (self.phase == DriverPhase.AVAILABLE
                and not AVAILABLE_DRIVERS_MOVING):
            # this driver does not move
            pass
        else:
            for i, _ in enumerate(self.location):
                # Handle going off the edge
                location[i] = ((location[i] + self.direction.value[i]) %
                               self.city.city_size)
            logger.debug((f"Driver {self.index} from "
                          f"({self.location[0]}, {self.location[1]}) "
                          f"to ({location[0]}, {location[1]})"))
            self.location = location

    def _navigate_towards(self, city, location, destination):
        """
        At an intersection turn towards a destination
        (perhaps a pickup, perhaps a dropoff).
        The direction is chosen based on the quadrant
        relative to destination
        Values of zero are on the borders
        """
        delta = [location[i] - destination[i] for i in (0, 1)]
        quadrant_length = city.city_size / 2
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
        logger.debug((f"Location = ({location[0]}, {location[1]}), "
                      f"destination = ({destination[0]}, {destination[1]}), "
                      f"direction = {direction}"))
        return direction


def parse_args():
    """
    Define, read and parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Simulate ride-hail drivers and trips.",
        usage="%(prog)s [options]",
        fromfile_prefix_chars='@')
    parser.add_argument("-c",
                        "--city_size",
                        metavar="city_size",
                        action="store",
                        type=int,
                        default=10,
                        help="""Length of the city grid, in blocks.""")
    parser.add_argument("-d",
                        "--drivers",
                        metavar="drivers",
                        action="store",
                        type=int,
                        default=20,
                        help="number of drivers")
    parser.add_argument("-i",
                        "--interpolate",
                        metavar="interpolate",
                        action="store",
                        type=int,
                        default=9,
                        help="""number of interpolation points when updating
                        the map""")
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
    parser.add_argument("-p",
                        "--periods",
                        metavar="periods",
                        action="store",
                        type=int,
                        default=500,
                        help="numberof periods")
    parser.add_argument("-q",
                        "--quiet",
                        action="store_true",
                        help="log only warnings and errors")
    parser.add_argument("-r",
                        "--request_interval",
                        metavar="request_interval",
                        action="store",
                        type=int,
                        default=1,
                        help="periods between requests")
    parser.add_argument("-s",
                        "--show",
                        metavar="show",
                        action="store",
                        type=str,
                        default="map",
                        help="show 'stats', ['map'], 'all' or 'none'")
    parser.add_argument("-t",
                        "--threshold",
                        metavar="threshold",
                        action="store",
                        type=float,
                        default=0.9,
                        help="""random number threshold for requests.
                        Should be in the interval (0, 1)""")
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
    simulation = RideHailSimulation(args.drivers, args.request_interval,
                                    args.interpolate, args.periods,
                                    args.city_size, args.output, args.show)
    simulation.simulate()


if __name__ == '__main__':
    main()
