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
import os
import matplotlib.pyplot as plt
import matplotlib as mpl
from enum import Enum
from matplotlib.ticker import MultipleLocator
from matplotlib.animation import FuncAnimation
from matplotlib.animation import ImageMagickFileWriter, FFMpegFileWriter
# from matplotlib.widgets import Slider
import seaborn as sns
from pandas.plotting import register_matplotlib_converters
register_matplotlib_converters()

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------------
# Parameters
# -------------------------------------------------------------------------------
FRAME_INTERVAL = 50
AVAILABLE_DRIVERS_MOVING = False
GARBAGE_COLLECTION_INTERVAL = 10
FIRST_REQUEST_OFFSET = 3
SUPPLY_DEMAND_RANGE = [0.8, 1.2]
CHART_X_RANGE = 200
DEFAULT_ROLLING_WINDOW = 20
SUPPLY_RESPONSE_TIME = 5
DEFAULT_RESULT_WINDOW = 100
DEFAULT_MAX_TIME_PERIODS = 1001
DEFAULT_REQUEST_RATE = 0.2
MAX_REQUESTS_PER_PERIOD = 3
DEFAULT_INTERPOLATION_POINTS = 4
DEFAULT_CITY_SIZE = 10

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


class Cumulative(Enum):
    DRIVER_TIME = 0
    WAIT_TIME = 1
    TRIP_COUNT = 2
    TRIP_DISTANCE = 4
    DRIVER_COUNT = 5


class PlotStat(Enum):
    DRIVER_FRACTION_AVAILABLE = "Available"
    DRIVER_FRACTION_PICKING_UP = "Picking Up"
    DRIVER_FRACTION_WITH_RIDER = "With Rider"
    DRIVER_MEAN_COUNT = "Mean driver count"
    TRIP_MEAN_WAIT_TIME = "Mean wait time"
    TRIP_MEAN_DISTANCE = "Mean trip distance"
    TRIP_COUNT = "Trips completed"


class RequestModel(Enum):
    THRESHOLD_GLOBAL = 0
    THRESHOLD_PER_DRIVER = 1


class ShowOption(Enum):
    NONE = "none"
    MAP = "map"
    STATS = "stats"
    ALL = "all"
    DRIVER = "driver"
    WAIT = "wait"


class Equilibration(Enum):
    DEMAND = 0
    SUPPLY = 1


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
                 equilibrate=None,
                 driver_cost=1.0,
                 price=1.0,
                 request_rate=DEFAULT_REQUEST_RATE,
                 interpolate=DEFAULT_INTERPOLATION_POINTS,
                 time_periods=DEFAULT_MAX_TIME_PERIODS,
                 city_size=DEFAULT_CITY_SIZE,
                 rolling_window=DEFAULT_ROLLING_WINDOW,
                 output=None,
                 show=ShowOption.MAP):
        """
        Initialize the class variables and call what needs to be called.
        The dataframe "data" has a row for each case.
        It must have the following columns:
        - "date_report": the date a case is reported
        """
        self.driver_count = driver_count
        self.equilibrate = equilibrate
        self.driver_cost = driver_cost
        self.price = price
        self.request_rate = request_rate
        self.city = City(city_size)
        self.time_periods = time_periods
        self.interpolation_points = interpolate
        self.frame_count = time_periods * self.interpolation_points
        self.rolling_window = rolling_window
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
        for total in list(Cumulative):
            self.stats[total] = []
        for stat in list(PlotStat):
            self.stats[stat] = []
        self.csv_driver = "driver.csv"
        self.csv_trip = "trip.csv"
        self.csv_summary = "ridehail.csv"
        logger.info("-" * 72)
        logger.info((f"Simulation: {{'rr': {self.request_rate}, "
                     f"'city size': {self.city.city_size}, "
                     f"'driver_cost': {self.driver_cost}, "
                     f"}}"))
        self._print_description()

    # (todays_date-datetime.timedelta(10), time_periods=10, freq='D')

    def _print_description(self):
        pass

    def simulate(self):
        """
        Plot the trend of cumulative cases, observed at
        earlier days, evolving over time.
        """
        # initial plot
        if self.show == ShowOption.NONE:
            for starting_period in range(self.time_periods):
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
        if self.equilibrate is not None:
            # Using the stats from the previous period,
            # equilibrate the supply and demand of rides
            if self.equilibrate == Equilibration.SUPPLY:
                self._equilibrate_supply(starting_period)
        for driver in self.drivers:
            # Move drivers
            driver.update_location()
            driver.update_direction()
            # If the driver arrives at a pickup or dropoff location,
            # handle the phase changes
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
                    # the driver has arrived at the dropoff and the trip ends
                    driver.phase_change()
                    trip.phase_change()
                    # Update trip-related stats with this completed
                    # trip's information
                    self._update_aggregate_trip_stats(trip)
                    # Some arrays hold information for each trip:
                    # compress these as needed to avoid a growing set
                    # of completed (dead) trips
                    self._collect_garbage()
        # Customers make ride requests
        self._request_rides(starting_period)
        # Update stats for everything that has happened in this period
        self._update_period_stats(starting_period)

    def _request_rides(self, period):
        """
        Periodically initiate a request from an inactive rider
        For requests not assigned a driver, repeat the request.

        """
        # Given a request rate r, compute the number of requests this
        # period.
        trips_this_period = 0
        if period < FIRST_REQUEST_OFFSET:
            return
        for i in range(MAX_REQUESTS_PER_PERIOD):
            r = random.uniform(0, MAX_REQUESTS_PER_PERIOD)
            if self.request_rate > r:
                trips_this_period += 1
                trip = Trip(len(self.trips), self.city)
                self.trips.append(trip)
                # the trip has a random origin and destination
                # and is ready to make a request.
                # This sets the trip to TripPhase.UNNASSIGNED
                # as no driver is assigned here
                trip.phase_change()
        if trips_this_period > 0:
            logger.debug((f"Rate {self.request_rate}: {trips_this_period}"
                          f" trips in period {period}."))

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
        The value is carried over from the previous period,
        which works for Sum totals and is overwritten
        for others.
        """
        # create a place to hold stats from this period
        for key, value in self.stats.items():
            if len(value) > 0:
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
                self.stats[Cumulative.DRIVER_TIME][-1] += 1
                # driver count is filled in anew each period
                self.stats[Cumulative.DRIVER_COUNT][-1] = self.driver_count
        if self.trips:
            for trip in self.trips:
                trip.phase_time[trip.phase] += 1

        # Compute aggregate stats for plotting
        # For Plot stats, using a rolling window, the lower bound
        # of which cannot be less than zero
        lower_bound = max((period - self.rolling_window), 0)
        # driver plot
        driver_time = (self.stats[Cumulative.DRIVER_TIME][-1] -
                       self.stats[Cumulative.DRIVER_TIME][lower_bound])
        trip_count = ((self.stats[Cumulative.TRIP_COUNT][-1] -
                       self.stats[Cumulative.TRIP_COUNT][lower_bound]))
        if driver_time == 0:
            self.stats[PlotStat.DRIVER_FRACTION_AVAILABLE][-1] = 0
            self.stats[PlotStat.DRIVER_FRACTION_PICKING_UP][-1] = 0
            self.stats[PlotStat.DRIVER_FRACTION_WITH_RIDER][-1] = 0
            self.stats[PlotStat.DRIVER_MEAN_COUNT][-1] = self.driver_count
        else:
            self.stats[PlotStat.DRIVER_FRACTION_AVAILABLE][-1] = (
                (self.stats[DriverPhase.AVAILABLE][-1] -
                 self.stats[DriverPhase.AVAILABLE][lower_bound]) / driver_time)
            self.stats[PlotStat.DRIVER_FRACTION_PICKING_UP][-1] = (
                (self.stats[DriverPhase.PICKING_UP][-1] -
                 self.stats[DriverPhase.PICKING_UP][lower_bound]) /
                driver_time)
            self.stats[PlotStat.DRIVER_FRACTION_WITH_RIDER][-1] = (
                (self.stats[DriverPhase.WITH_RIDER][-1] -
                 self.stats[DriverPhase.WITH_RIDER][lower_bound]) /
                driver_time)
            self.stats[PlotStat.DRIVER_MEAN_COUNT][-1] = (
                sum(self.stats[Cumulative.DRIVER_COUNT][lower_bound:]) /
                (len(self.stats[Cumulative.DRIVER_COUNT]) - lower_bound))
        # trip stats
        if trip_count == 0:
            self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][-1] = 0
            self.stats[PlotStat.TRIP_MEAN_DISTANCE][-1] = 0
        else:
            self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][-1] = (
                (self.stats[Cumulative.WAIT_TIME][-1] -
                 self.stats[Cumulative.WAIT_TIME][lower_bound]) / trip_count)
            self.stats[PlotStat.TRIP_MEAN_DISTANCE][-1] = (
                (self.stats[Cumulative.TRIP_DISTANCE][-1] -
                 self.stats[Cumulative.TRIP_DISTANCE][lower_bound]) /
                trip_count)
            self.stats[PlotStat.TRIP_COUNT][-1] = (
                (self.stats[Cumulative.TRIP_COUNT][-1] -
                 self.stats[Cumulative.TRIP_COUNT][lower_bound]) /
                (len(self.stats[Cumulative.TRIP_COUNT]) - lower_bound))

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
        self.stats[Cumulative.TRIP_COUNT][-1] += 1
        self.stats[Cumulative.TRIP_DISTANCE][-1] += trip.distance
        # Bad naming: the WAIT_TIME includes both WAITING and UNASSIGNED
        self.stats[Cumulative.WAIT_TIME][-1] += trip.phase_time[
            TripPhase.UNASSIGNED]
        self.stats[Cumulative.WAIT_TIME][-1] += trip.phase_time[
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
        if self.show == ShowOption.ALL:
            fig, axes = plt.subplots(ncols=3, figsize=(18, 6))
        elif self.show == ShowOption.STATS:
            fig, axes = plt.subplots(ncols=2, figsize=(12, 6))
        elif self.show in (ShowOption.DRIVER, ShowOption.WAIT):
            fig, ax = plt.subplots(figsize=(6, 6))
            axes = [ax]
        elif self.show == ShowOption.MAP:
            fig, ax = plt.subplots(figsize=(6, 6))
            axes = [ax]
        fig.suptitle((f"Simulation with "
                      f"{self.request_rate} requests per period"))
        # Slider
        # slider = Slider(axes[0],
        # 'Drivers',
        # 0,
        # 2 * self.driver_count,
        # valinit=self.driver_count)

        animation = FuncAnimation(fig,
                                  self._next_frame,
                                  frames=(self.frame_count),
                                  fargs=[axes],
                                  interval=FRAME_INTERVAL,
                                  repeat=False,
                                  repeat_delay=3000)
        Plot().output(animation, plt, self.__class__.__name__, self.output)

    def _equilibrate_2(self, period):
        """
        Change the driver count and request rate
        to move the system towards equilibrium. The condition is:
            S_0 * (PlotStat.DRIVER_FRACTION_WITH_RIDER)
            = D_0 * PlotStat.TRIP_MEAN_DISTANCE /
            (PlotStat.TRIP_MEAN_WAIT_TIME + PlotStat.TRIP_MEAN_DISTANCE)
        """
        if ((period % SUPPLY_RESPONSE_TIME == 0)
                and period > self.rolling_window):
            # only update at certain time_periods
            # compute equilibrium condition D_0(L/S_0(W_0 + L) - B
            trip_distance = self.stats[PlotStat.TRIP_MEAN_DISTANCE][-1]
            trip_wait_time = self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][-1]
            busy_fraction = self.stats[PlotStat.DRIVER_FRACTION_WITH_RIDER][-1]

            logger.info((f"Period {period}: "
                         f"equilibrating with {self.equilibrate}"))
            # with S_0 = 1
            p_supply = busy_fraction * self.driver_count
            p_demand = (trip_distance / (trip_distance + trip_wait_time) -
                        (self.request_rate * trip_distance / self.driver_cost))
            driver_increment = 0
            if ((p_supply / p_demand) > SUPPLY_DEMAND_RANGE[1]):
                driver_increment = -1
            elif ((p_supply / p_demand) < SUPPLY_DEMAND_RANGE[0]):
                driver_increment = +1
            logger.info((f"Period {period}: supply price={p_supply}, "
                         f"demand price={p_demand}, "
                         f"driver increment {driver_increment}"))
            if driver_increment != 0:
                logger.debug((f"Changing driver count to "
                              f"{self.driver_count + driver_increment}"))
            if driver_increment > 0:
                self.drivers += [
                    Driver(i, self.city)
                    for i in range(self.driver_count, self.driver_count +
                                   driver_increment)
                ]
                self.driver_count += driver_increment
            elif driver_increment < 0:
                for i, driver in enumerate(self.drivers):
                    if driver.phase == DriverPhase.AVAILABLE:
                        del self.drivers[i]
                        self.driver_count += driver_increment
                        break
                    else:
                        logger.info("No drivers without ride assignments. "
                                    "Cannot remove any drivers")

    def _equilibrate_supply(self, period):
        """
        Change the driver count and request rate
        to move the system towards equilibrium. The condition is:
        (S = drivers * busy = price)
        If income = price * busy - cost
        """
        if ((period % SUPPLY_RESPONSE_TIME == 0)
                and period > self.rolling_window):
            # only update at certain time_periods
            # compute equilibrium condition D_0(L/S_0(W_0 + L) - B
            trip_distance = self.stats[PlotStat.TRIP_MEAN_DISTANCE][-1]
            trip_wait_time = self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][-1]
            busy_fraction = self.stats[PlotStat.DRIVER_FRACTION_WITH_RIDER][-1]
            driver_increment = 0
            # supply = busy_fraction
            demand_denominator = (trip_wait_time + trip_distance)
            driver_income = self.price * busy_fraction - self.driver_cost
            if demand_denominator == 0:
                return
            else:
                demand = (self.driver_cost * trip_distance /
                          demand_denominator)
                driver_increment = 0
            if demand == 0:
                driver_increment = 0
            elif driver_income < 0:
                driver_increment = -1
            elif driver_income > 0:
                driver_increment = +1
            if driver_increment != 0:
                logger.info((f"Period {period}: price = {self.price:.02f}, "
                             f"busy={busy_fraction:.02f}, "
                             f"cost={self.driver_cost:.02f}, "
                             f"income={driver_income:.02f}"))
                # logger.info(
                # (f"Supply =  {supply:.02f}, demand = {demand:.02f}: "
                # f"Driver count: {self.driver_count} ->  "
                # f"{self.driver_count + driver_increment}"))
            if driver_increment > 0:
                self.drivers += [
                    Driver(i, self.city)
                    for i in range(self.driver_count, self.driver_count +
                                   driver_increment)
                ]
                self.driver_count += driver_increment
            elif driver_increment < 0:
                for i, driver in enumerate(self.drivers):
                    driver_removed = False
                    if driver.phase == DriverPhase.AVAILABLE:
                        del self.drivers[i]
                        self.driver_count += driver_increment
                        driver_removed = True
                        break
                if not driver_removed:
                    logger.info("No drivers without ride assignments. "
                                "Cannot remove any drivers")

    def _next_frame(self, i, axes):
        """
        Function called from animator to generate frame i of the animation.
        """
        if i % self.interpolation_points == 0:
            # A "real" time point. Update the system
            starting_period = int(i / self.interpolation_points)
            self._next_period(starting_period)
        axis_index = 0
        if self.show in (ShowOption.ALL, ShowOption.MAP):
            self._draw_map(i, axes[axis_index])
            axis_index += 1
        if self.show in (ShowOption.ALL, ShowOption.STATS, ShowOption.DRIVER):
            self._draw_driver_phases(i, axes[axis_index])
            axis_index += 1
        if self.show in (ShowOption.ALL, ShowOption.STATS, ShowOption.WAIT):
            self._draw_trip_wait_times(i, axes[axis_index])

    def _draw_map(self, i, ax):
        """
        Draw the map, with drivers and trips
        """
        ax.clear()
        ax.set_title(f"City Map, {self.driver_count} drivers")
        # Get the interpolation point
        interpolation = i % self.interpolation_points
        distance_increment = interpolation / self.interpolation_points
        roadwidth = 60.0 / self.city.city_size
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
                x = driver.location[i]
                if (driver.phase != DriverPhase.AVAILABLE
                        or AVAILABLE_DRIVERS_MOVING):
                    x += distance_increment * driver.direction.value[i]
                x = ((x + self.city.display_fringe) % self.city.city_size -
                     self.city.display_fringe)
                # Make the displayed-position fit on the map, with
                # fringe city.display_fringe around the edges
                locations[i][driver.direction.name].append(x)
            size[driver.direction.name].append(sizes[driver.phase.value])
            color[driver.direction.name].append(
                self.color_palette[driver.phase.value])
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
        ax.grid(True, which="major", axis="both", lw=roadwidth)
        ax.set_xticklabels([])
        ax.set_yticklabels([])

    def _draw_driver_phases(self, i, ax):
        """
        Display a chart with driver time spent in each phase
        """
        period = int(i / self.interpolation_points)
        lower_bound = max((period - CHART_X_RANGE), 0)
        x_range = list(
            range(lower_bound,
                  len(self.stats[PlotStat.DRIVER_FRACTION_AVAILABLE])))
        if i % self.interpolation_points == 0:
            ax.clear()
            ax.set_title(
                f"Driver phases, rolling {self.rolling_window}-period average")
            draw_barchart = False
            if draw_barchart:
                x = []
                height = []
                labels = []
                colors = []
                for phase in list(PlotStat):
                    if phase not in (PlotStat.TRIP_MEAN_WAIT_TIME,
                                     PlotStat.TRIP_MEAN_DISTANCE,
                                     PlotStat.TRIP_COUNT,
                                     PlotStat.DRIVER_MEAN_COUNT):
                        x.append(phase.value)
                        height.append(self.stats[phase][-1])
                        labels.append(phase.value)
                        colors.append(self.color_palette[phase.value])
                caption = "\n".join(
                    (f"This simulation has {self.driver_count} drivers",
                     f"and {self.request_rate} requests per period"))
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
                    if phase not in (PlotStat.TRIP_MEAN_WAIT_TIME,
                                     PlotStat.TRIP_MEAN_DISTANCE,
                                     PlotStat.TRIP_COUNT,
                                     PlotStat.DRIVER_MEAN_COUNT):
                        ax.plot(x_range,
                                self.stats[phase][lower_bound:],
                                color=self.color_palette[index],
                                label=phase.value,
                                lw=3,
                                alpha=0.7)
                ax.set_ylim(bottom=0)
                ax.set_xlabel("Time (periods)")
                ax.set_ylabel("Fraction of driver time in phase")
                ax.legend()

    def _draw_trip_wait_times(self, i, ax):
        """
        Display a chart with the average trip wait time
        """
        period = int(i / self.interpolation_points)
        lower_bound = max((period - CHART_X_RANGE), 0)
        x_range = list(
            range(lower_bound,
                  len(self.stats[PlotStat.DRIVER_FRACTION_AVAILABLE])))
        if i % self.interpolation_points == 0:
            ax.clear()
            ax.set_title(
                f"Wait time, rolling {self.rolling_window}-period average")
            ax.plot(x_range,
                    self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][lower_bound:],
                    label=PlotStat.TRIP_MEAN_WAIT_TIME.value,
                    lw=3,
                    alpha=0.7)
            ax.plot(x_range,
                    self.stats[PlotStat.TRIP_MEAN_DISTANCE][lower_bound:],
                    label=PlotStat.TRIP_MEAN_DISTANCE.value,
                    lw=3,
                    alpha=0.7)
            ax.plot(x_range,
                    self.stats[PlotStat.DRIVER_MEAN_COUNT][lower_bound:],
                    label=PlotStat.DRIVER_MEAN_COUNT.value,
                    lw=3,
                    alpha=0.7)
            ax.set_ylim(bottom=0)
            ax.set_xlabel("Time (periods)")
            ax.set_ylabel("Mean wait time or trip distance (periods)")
            ax.legend()
            # ax.set_xlim(0, self.time_periods)
            # ax.set_ylim(0, self.city.city_size)

    def _write_results(self):
        """
        Print the results to CSV files. The final results are computed over
        a different (longer) window than the rolling averages used for display
        or equilibrating purposes
        """
        # Log final state
        lower_bound = (self.time_periods - DEFAULT_RESULT_WINDOW)
        driver_time = (self.stats[Cumulative.DRIVER_TIME][-1] -
                       self.stats[Cumulative.DRIVER_TIME][lower_bound])
        trip_count = ((self.stats[Cumulative.TRIP_COUNT][-1] -
                       self.stats[Cumulative.TRIP_COUNT][lower_bound]))
        driver_fraction_available = (
            (self.stats[DriverPhase.AVAILABLE][-1] -
             self.stats[DriverPhase.AVAILABLE][lower_bound]) / driver_time)
        driver_fraction_picking_up = (
            (self.stats[DriverPhase.PICKING_UP][-1] -
             self.stats[DriverPhase.PICKING_UP][lower_bound]) / driver_time)
        driver_fraction_with_rider = (
            (self.stats[DriverPhase.WITH_RIDER][-1] -
             self.stats[DriverPhase.WITH_RIDER][lower_bound]) / driver_time)
        driver_mean_count = (
            sum(self.stats[Cumulative.DRIVER_COUNT][lower_bound:]) /
            (len(self.stats[Cumulative.DRIVER_COUNT]) - lower_bound))
        # trip stats
        trip_mean_wait_time = (
            (self.stats[Cumulative.WAIT_TIME][-1] -
             self.stats[Cumulative.WAIT_TIME][lower_bound]) / trip_count)
        trip_mean_distance = (
            (self.stats[Cumulative.TRIP_DISTANCE][-1] -
             self.stats[Cumulative.TRIP_DISTANCE][lower_bound]) / trip_count)
        trip_mean_count = (
            (self.stats[Cumulative.TRIP_COUNT][-1] -
             self.stats[Cumulative.TRIP_COUNT][lower_bound]) /
            (len(self.stats[Cumulative.TRIP_COUNT]) - lower_bound))
        rl_over_nb = (trip_mean_distance * self.request_rate /
                      (self.driver_count * driver_fraction_with_rider))
        logger.info((f"End: {{'drivers': {self.driver_count:02}, "
                     f"'wait': "
                     f"{trip_mean_wait_time:.02f}, "
                     f"'riding': "
                     f"{driver_fraction_with_rider:.02f}, "
                     f"'pickup': "
                     f"{driver_fraction_picking_up:.02f}, "
                     f"'available': "
                     f"{driver_fraction_available:.02f}, "
                     f"}}"))
        if not os.path.exists(self.csv_summary):
            with open(self.csv_summary, mode="w") as f:
                f.write(("request_rate, distance, "
                         "wait_time, drivers, with_rider, rl_over_nb\n"))
        with open(self.csv_summary, mode="a+") as f:
            f.write((f"{self.request_rate:>12.02f},"
                     f"{trip_mean_distance:>9.02f}, "
                     f"{trip_mean_wait_time:>9.02f}, "
                     f"{driver_mean_count:>7.02f}, "
                     f"{driver_fraction_with_rider:>10.02f}, "
                     f"{rl_over_nb:>10.02f}\n"))
        with open(self.csv_driver, mode="w") as f:
            f.write(("period, available, picking_up, with_rider, "
                     "driver_time, frac_avail, "
                     "frac_pick, frac_with\n"))
            for i in range(self.time_periods):
                f.write((
                    f"  {i:04}, "
                    f"     {self.stats[DriverPhase.AVAILABLE][i]:04}, "
                    f"      {self.stats[DriverPhase.PICKING_UP][i]:04}, "
                    f"      {self.stats[DriverPhase.WITH_RIDER][i]:04}, "
                    f"       {self.stats[Cumulative.DRIVER_TIME][i]:04}, "
                    f" {self.stats[PlotStat.DRIVER_FRACTION_AVAILABLE][i]:.02f}, "
                    f" {self.stats[PlotStat.DRIVER_FRACTION_PICKING_UP][i]:.02f}, "
                    f" {self.stats[PlotStat.DRIVER_FRACTION_WITH_RIDER][i]:.02f}\n"
                ))
        with open(self.csv_trip, mode="w") as f:
            f.write(("period, inactive, unassigned, "
                     "waiting, riding, finished, "
                     "trips, wait, mean wait\n"))
            for i in range(self.time_periods):
                f.write(
                    (f"  {i:04}, "
                     f"    {self.stats[TripPhase.INACTIVE][i]:04}, "
                     f"      {self.stats[TripPhase.UNASSIGNED][i]:04}, "
                     f"   {self.stats[TripPhase.WAITING][i]:04}, "
                     f"  {self.stats[TripPhase.RIDING][i]:04}, "
                     f"    {self.stats[TripPhase.FINISHED][i]:04}, "
                     f"{self.stats[Cumulative.TRIP_COUNT][i]:04}, "
                     f"{self.stats[Cumulative.WAIT_TIME][i]:04}, "
                     f"    {self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][i]:.2f}\n"
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
        self.distance = 0
        for coord in [0, 1]:
            dist = abs(self.origin[coord] - self.destination[coord])
            dist = min(dist, self.city.city_size - dist)
            self.distance += dist
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
            if AVAILABLE_DRIVERS_MOVING:
                new_direction = random.choice(list(Direction))
            else:
                new_direction = self.direction
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
        elif (self.phase == DriverPhase.PICKING_UP
              and self.location == self.pickup):
            # the driver is at the pickup location
            # do not move. Usually this is handled
            # at the end of the previous period: this code
            # should be called only when the driver
            # is at the pickup location when called
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
                        default=DEFAULT_CITY_SIZE,
                        help="""Length of the city grid, in blocks.""")
    parser.add_argument("-d",
                        "--drivers",
                        metavar="drivers",
                        action="store",
                        type=int,
                        default=1,
                        help="number of drivers")
    parser.add_argument("-eq",
                        "--equilibrate",
                        metavar="equilibrate",
                        type=str,
                        default=None,
                        action="store",
                        help="Change driver count to equilibrate")
    parser.add_argument("-dc",
                        "--driver_cost",
                        metavar="cost",
                        action="store",
                        type=float,
                        default=1,
                        help="""Driver cost per unit time""")
    parser.add_argument("-i",
                        "--interpolate",
                        metavar="interpolate",
                        action="store",
                        type=int,
                        default=DEFAULT_INTERPOLATION_POINTS,
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
        help="""output to the display or as a file; gif or mp4""")
    parser.add_argument("-p",
                        "--price",
                        action="store",
                        type=float,
                        default=1.0,
                        help="Fixed price")
    parser.add_argument("-q",
                        "--quiet",
                        action="store_true",
                        help="log only warnings and errors")
    parser.add_argument("-r",
                        "--request_rate",
                        metavar="request_rate",
                        action="store",
                        type=float,
                        default=DEFAULT_REQUEST_RATE,
                        help="requests per period")
    parser.add_argument("-s",
                        "--show",
                        metavar="show",
                        action="store",
                        type=str,
                        default=ShowOption.MAP,
                        help="""show 'all', 'none', 'driver', 'wait',
                        'stats', ['map']""")
    parser.add_argument("-t",
                        "--time_periods",
                        metavar="time_periods",
                        action="store",
                        type=int,
                        default=DEFAULT_MAX_TIME_PERIODS,
                        help="numberof time time periods")
    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        help="log all messages, including debug")
    parser.add_argument("-w",
                        "--window",
                        metavar="window",
                        action="store",
                        type=int,
                        default=DEFAULT_ROLLING_WINDOW,
                        help="""rolling window for computing averages""")
    args = parser.parse_args()
    return args


def validate_args(args):
    """
    Check they are OK
    """
    for option in list(ShowOption):
        if args.show == option.value:
            args.show = option
            break
    for option in list(Equilibration):
        if args.equilibrate.lower()[0] == option.name.lower()[0]:
            args.equilibrate = option
            logger.info(f"Equilibration method is {option.name}")
            break
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
    args = validate_args(args)
    simulation = RideHailSimulation(args.drivers, args.equilibrate,
                                    args.driver_cost, args.price,
                                    args.request_rate, args.interpolate,
                                    args.time_periods, args.city_size,
                                    args.window, args.output, args.show)
    simulation.simulate()


if __name__ == '__main__':
    main()
