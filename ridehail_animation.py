#!/usr/bin/python3
"""
Ridehail animations: for amusement only
"""

# -------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------
import argparse
import configparser
import logging
import random
import os
import copy
import numpy as np
from scipy.optimize import curve_fit
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
GARBAGE_COLLECTION_INTERVAL = 10
FIRST_REQUEST_OFFSET = 3
SUPPLY_DEMAND_RANGE = [0.8, 1.2]
CHART_X_RANGE = 200
EQUILIBRIUM_BLUR = 0.01
DEFAULT_RESULT_WINDOW = 100
DEFAULT_TIME_PERIODS = 1001
DEFAULT_REQUEST_RATE = 0.2
DEFAULT_INTERPOLATION_POINTS = 4
DEFAULT_CITY_SIZE = 10
DEFAULT_DRIVER_COUNT = 1
MAX_REQUESTS_PER_PERIOD = 10

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


class History(Enum):
    CUMULATIVE_DRIVER_TIME = "Cumulative driver time"
    CUMULATIVE_WAIT_TIME = "Cumulative wait time"
    CUMULATIVE_TRIP_COUNT = "Cumulative completed trips"
    CUMULATIVE_TRIP_DISTANCE = "Cumulative distance"
    CUMULATIVE_REQUESTS = "Cumulative requests"
    DRIVER_COUNT = "Driver count"
    REQUEST_RATE = "Request rate"


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


class RequestModel(Enum):
    THRESHOLD_GLOBAL = 0
    THRESHOLD_PER_DRIVER = 1


class Draw(Enum):
    NONE = "none"
    MAP = "map"
    STATS = "stats"
    ALL = "all"
    DRIVER = "driver"
    TRIP = "trip"
    SUMMARY = "summary"
    EQUILIBRATION = "equilibration"


class Equilibration(Enum):
    SUPPLY = 0
    DEMAND = 1
    FULL = 2


# ------------------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Classes
# ------------------------------------------------------------------------------
class Config():
    """
    Hold the configuration parameters for the simulation, which come from three
    places:
    - default values, unless overridden by
    - a configuration file, unless overridden by
    - command line arguments
    """
    def __init__(self, args=None):
        """
        Read the configuration file  to set up the parameters
        """
        self.config_file = None
        self.log_level = logging.INFO
        if args is not None:
            self.config_file = args.config_file
            try:
                if args.verbose:
                    self.log_level = logging.DEBUG
                else:
                    self.log_level = logging.INFO
            except Exception:
                self.log_level = logging.INFO
        config = configparser.ConfigParser()
        if self.config_file is None:
            # The default config file is username.config
            # look for username.config on both Windows (USERNAME)
            # and Linux (USER)
            if os.name == "nt":
                username = os.environ['USERNAME']
            else:
                username = os.environ['USER']
            self.config_file = username + ".config"
            logger.info(f"Reading configuration file {self.config_file}")
            if not os.path.isfile(self.config_file):
                logger.error(
                    f"Configuration file {self.config_file} not found.")
        config.read(self.config_file)

        # Fill in individual configuration values
        # City size
        self.city_size = int(args.city_size if args.
                             city_size else config["DEFAULT"]["city_size"])
        logger.info(f"City size = {self.city_size}")
        # Driver count
        driver_counts = (args.driver_count if args.driver_count else
                         config["DEFAULT"]["driver_count"])
        self.driver_count = [int(x) for x in driver_counts.split(",")]
        logger.info(f"Driver counts = {self.driver_count}")
        # Request rate
        request_rates = (args.request_rate if args.request_rate else
                         config["DEFAULT"]["request_rate"])
        self.request_rate = [float(x) for x in request_rates.split(",")]
        logger.info(f"Request rate = {self.request_rate}")
        # Time periods
        self.time_periods = int(args.time_periods if args.time_periods else
                                config["DEFAULT"]["time_periods"])
        logger.info(f"Time periods = {self.time_periods}")
        # Log file TODO not sure if this works
        self.log_file = str(
            args.log_file if args.log_file else config["DEFAULT"]["log_file"])
        logger.info(f"Log file = {self.log_file}")
        # Verbose output
        self.verbose = bool(
            args.verbose if args.verbose else config["DEFAULT"]["verbose"])
        logger.info(f"Verbose = {self.verbose}")
        # Quiet output
        self.quiet = bool(
            args.quiet if args.quiet else config["DEFAULT"]["quiet"])
        logger.info(f"Quiet = {self.quiet}")
        # Draw maps or charts
        self.draw = str(args.draw if args.draw else config["DEFAULT"]["draw"])
        for draw_option in list(Draw):
            if self.draw == draw_option.value:
                self.draw = draw_option
                break
        logger.info(f"Draw = {self.draw}")
        # Draw update period
        self.draw_update_period = int(
            args.draw_update_period if args.
            draw_update_period else config["DEFAULT"]["draw_update_period"])
        logger.info(f"Draw update period = {self.draw_update_period}")
        # Interpolation points
        self.interpolate = int(args.interpolate if args.interpolate else
                               config["DEFAULT"]["interpolate"])
        logger.info(f"Interpolation points = {self.interpolate}")
        # Equilibrate
        self.equilibrate = str(args.equilibrate if args.equilibrate else
                               config["DEFAULT"]["equilibrate"])
        logger.info(f"Equilibration = {self.equilibrate}")
        # Rolling window
        self.rolling_window = int(args.rolling_window if args.rolling_window
                                  else config["DEFAULT"]["rolling_window"])
        logger.info(f"Rolling window = {self.rolling_window}")
        # Output file for charts
        self.output = str(
            args.output if args.output else config["DEFAULT"]["output"])
        logger.info(f"Output file for charts = {self.output}")
        # ImageMagick directory
        self.imagemagick_dir = str(args.imagemagick_dir if args.imagemagick_dir
                                   else config["DEFAULT"]["imagemagick_dir"])
        logger.info(f"ImageMagick_Dir = {self.imagemagick_dir}")
        # Available drivers moving
        self.available_drivers_moving = bool(
            args.available_drivers_moving if args.available_drivers_moving else
            config["DEFAULT"]["available_drivers_moving"])
        logger.info(
            f"Available drivers moving = {self.available_drivers_moving}")
        if self.equilibrate:
            for option in list(Equilibration):
                if self.equilibrate.lower()[0] == option.name.lower()[0]:
                    self.equilibrate = option
                    logger.info(f"Equilibration method is {option.name}")
                    break
            if self.equilibrate not in list(Equilibration):
                logger.error(f"equilibrate must start with s, d, or f")
            # Price
            self.price = float(
                args.price if args.price else config["EQUILIBRATION"]["price"])
            logger.info(f"Price = {self.price}")
            # Driver cost
            self.driver_cost = float(args.driver_cost if args.driver_cost else
                                     config["EQUILIBRATION"]["driver_cost"])
            logger.info(f"Driver cost = {self.driver_cost}")
            # Ride utility
            self.ride_utility = float(
                args.ride_utility if args.
                ride_utility else config["EQUILIBRATION"]["ride_utility"])
            logger.info(f"Ride utility = {self.ride_utility}")
            # Wait cost
            self.wait_cost = float(args.wait_cost if args.wait_cost else
                                   config["EQUILIBRATION"]["wait_cost"])
            logger.info(f"Wait cost = {self.wait_cost}")
            # Equilibration interval
            self.equilibration_interval = int(
                args.equilibration_interval if args.equilibration_interval else
                config["EQUILIBRATION"]["equilibration_interval"])
            logger.info(
                f"Equilibration interval = {self.equilibration_interval}")


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


class RideHailSimulationResults():
    """
    Hold the results of a RideHailSimulation.
    Usually it just writes it out, but now we can do things like
    plot sequences of simulations
    """
    def __init__(self, simulation):
        self.sim = simulation

    def write(self):
        """
        Print the results to CSV files. The final results are computed over
        a different (longer) window than the rolling averages used for display
        or equilibrating purposes
        """
        # Log final state
        lower_bound = max((self.sim.time_periods - DEFAULT_RESULT_WINDOW), 0)
        driver_time = (
            self.sim.stats[History.CUMULATIVE_DRIVER_TIME][-1] -
            self.sim.stats[History.CUMULATIVE_DRIVER_TIME][lower_bound])
        trip_count = (
            (self.sim.stats[History.CUMULATIVE_TRIP_COUNT][-1] -
             self.sim.stats[History.CUMULATIVE_TRIP_COUNT][lower_bound]))
        driver_fraction_available = (
            (self.sim.stats[DriverPhase.AVAILABLE][-1] -
             self.sim.stats[DriverPhase.AVAILABLE][lower_bound]) / driver_time)
        driver_fraction_picking_up = (
            (self.sim.stats[DriverPhase.PICKING_UP][-1] -
             self.sim.stats[DriverPhase.PICKING_UP][lower_bound]) /
            driver_time)
        driver_fraction_with_rider = (
            (self.sim.stats[DriverPhase.WITH_RIDER][-1] -
             self.sim.stats[DriverPhase.WITH_RIDER][lower_bound]) /
            driver_time)
        driver_mean_count = (
            sum(self.sim.stats[History.DRIVER_COUNT][lower_bound:]) /
            (len(self.sim.stats[History.DRIVER_COUNT]) - lower_bound))
        # trip stats
        trip_mean_wait_time = (
            (self.sim.stats[History.CUMULATIVE_WAIT_TIME][-1] -
             self.sim.stats[History.CUMULATIVE_WAIT_TIME][lower_bound]) /
            trip_count)
        trip_mean_distance = (
            (self.sim.stats[History.CUMULATIVE_TRIP_DISTANCE][-1] -
             self.sim.stats[History.CUMULATIVE_TRIP_DISTANCE][lower_bound]) /
            trip_count)
        # trip_mean_count = (
        # (self.sim.stats[History.CUMULATIVE_TRIP_COUNT][-1] -
        # self.sim.stats[History.CUMULATIVE_TRIP_COUNT][lower_bound]) /
        # (len(self.sim.stats[History.CUMULATIVE_TRIP_COUNT]) - lower_bound))
        rl_over_nb = (trip_mean_distance * self.sim.request_rate /
                      (self.sim.driver_count * driver_fraction_with_rider))
        logger.info((f"End: {{'drivers': {self.sim.driver_count:02}, "
                     f"'wait': "
                     f"{trip_mean_wait_time:.02f}, "
                     f"'riding': "
                     f"{driver_fraction_with_rider:.02f}, "
                     f"'pickup': "
                     f"{driver_fraction_picking_up:.02f}, "
                     f"'available': "
                     f"{driver_fraction_available:.02f}, "
                     f"}}"))
        if not os.path.exists(self.sim.csv_summary):
            with open(self.sim.csv_summary, mode="w") as f:
                f.write(("request_rate, <drivers>, <distance>, "
                         "<wait_time>, with_rider, rl_over_nb\n"))
        with open(self.sim.csv_summary, mode="a+") as f:
            f.write((f"{self.sim.request_rate:>12.02f},"
                     f"{driver_mean_count:>9.02f}, "
                     f"{trip_mean_distance:>10.02f}, "
                     f"{trip_mean_wait_time:>11.02f}, "
                     f"{driver_fraction_with_rider:>10.02f}, "
                     f"{rl_over_nb:>10.02f}\n"))
        with open(self.sim.csv_driver, mode="w") as f:
            f.write(("period, available, picking_up, with_rider, "
                     "driver_time, frac_avail, "
                     "frac_pick, frac_with\n"))
            for i in range(self.sim.time_periods):
                f.write((
                    f"{i:>07}, "
                    f"{self.sim.stats[DriverPhase.AVAILABLE][i]:>08}, "
                    f"{self.sim.stats[DriverPhase.PICKING_UP][i]:>09}, "
                    f"{self.sim.stats[DriverPhase.WITH_RIDER][i]:>09},   "
                    f"{self.sim.stats[History.CUMULATIVE_DRIVER_TIME][i]:>09},  "
                    f"{self.sim.stats[PlotStat.DRIVER_AVAILABLE_FRACTION][i]:>9.02f}, "
                    f"{self.sim.stats[PlotStat.DRIVER_PICKUP_FRACTION][i]:>9.02f}, "
                    f"{self.sim.stats[PlotStat.DRIVER_PAID_FRACTION][i]:>9.02f}\n"
                ))
        with open(self.sim.csv_trip, mode="w") as f:
            f.write(("period, inactive, unassigned, "
                     "waiting, riding, finished, "
                     "trips, wait, <distance>, <wait>\n"))
            for i in range(self.sim.time_periods):
                f.write((
                    f"  {i:04}, "
                    f"    {self.sim.stats[TripPhase.INACTIVE][i]:04}, "
                    f"      {self.sim.stats[TripPhase.UNASSIGNED][i]:04}, "
                    f"   {self.sim.stats[TripPhase.WAITING][i]:04}, "
                    f"  {self.sim.stats[TripPhase.RIDING][i]:04}, "
                    f"    {self.sim.stats[TripPhase.FINISHED][i]:04}, "
                    f"{self.sim.stats[History.CUMULATIVE_TRIP_COUNT][i]:04}, "
                    f"{self.sim.stats[History.CUMULATIVE_WAIT_TIME][i]:04}, "
                    f"    {self.sim.stats[PlotStat.TRIP_MEAN_LENGTH][i]:.2f}, "
                    f"    {self.sim.stats[PlotStat.TRIP_MEAN_WAIT_TIME][i]:.2f}\n"
                ))


class RideHailSimulation():
    """
    Simulate a ride-hail environment, with drivers and trips
    """
    def __init__(self, config):
        """
        Initialize the class variables and call what needs to be called.
        The dataframe "data" has a row for each case.
        It must have the following columns:
        - "date_report": the date a case is reported
        """
        self.driver_count = config.driver_count
        self.equilibrate = config.equilibrate
        self.driver_cost = config.driver_cost
        self.wait_cost = config.wait_cost
        self.ride_utility = config.ride_utility
        self.price = config.price
        self.request_rate = config.request_rate
        self.city = City(config.city_size)
        self.time_periods = config.time_periods
        self.draw_update_period = config.draw_update_period
        self.interpolation_points = config.interpolate
        self.frame_count = config.time_periods * self.interpolation_points
        self.rolling_window = config.rolling_window
        self.output = config.output
        self.draw = config.draw
        self.equilibration_interval = config.equilibration_interval
        self.available_drivers_moving = config.available_drivers_moving
        self.drivers = [
            Driver(i, self.city, self.available_drivers_moving)
            for i in range(config.driver_count)
        ]
        self.trips = []
        self.color_palette = sns.color_palette()
        self.stats = {}
        for phase in list(DriverPhase):
            self.stats[phase] = []
        for phase in list(TripPhase):
            self.stats[phase] = []
        for total in list(History):
            self.stats[total] = []
        for stat in list(PlotStat):
            self.stats[stat] = []
        self.csv_driver = "driver.csv"
        self.csv_trip = "trip.csv"
        self.csv_summary = "ridehail.csv"
        logger.debug("-" * 72)
        logger.debug((f"Simulation: {{'rr': {self.request_rate}, "
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
        if self.draw in (Draw.NONE, Draw.SUMMARY):
            for starting_period in range(self.time_periods):
                self._next_period(starting_period)
        else:
            self._animate()
        results = RideHailSimulationResults(self)
        return results

    def _next_period(self, starting_period):
        """
        Call all those functions needed to simulate the next period
        """
        logger.debug(f"------- Period {starting_period} -----------")
        self._prepare_stat_lists()
        if self.equilibrate is not None:
            # Using the stats from the previous period,
            # equilibrate the supply and/or demand of rides
            if self.equilibrate in (Equilibration.SUPPLY, Equilibration.FULL):
                self._equilibrate_supply(starting_period)
            if self.equilibrate in (Equilibration.DEMAND, Equilibration.FULL):
                self._equilibrate_demand(starting_period)
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
                    # The driver has arrived at the dropoff and the trip ends.
                    # Update trip-related stats with this completed
                    # trip's information
                    self._update_aggregate_trip_stats(trip)
                    # Update driver and trip to reflect the completion
                    driver.phase_change()
                    trip.phase_change()
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
        if period < FIRST_REQUEST_OFFSET:
            return
        trips_this_period = 0
        trip_capital = self.stats[History.CUMULATIVE_REQUESTS][-1]
        self.stats[History.CUMULATIVE_REQUESTS][-1] += self.request_rate
        trips_this_period = (int(self.stats[History.CUMULATIVE_REQUESTS][-1]) -
                             int(trip_capital))
        for trip in range(trips_this_period):
            trip = Trip(len(self.trips), self.city)
            self.trips.append(trip)
            # the trip has a random origin and destination
            # and is ready to make a request.
            # This sets the trip to TripPhase.UNNASSIGNED
            # as no driver is assigned here
            trip.phase_change()
        if trips_this_period > 0:
            logger.debug((f"Period {period}: "
                          f"rate {self.request_rate:.02f}: "
                          f"{trips_this_period} trip request(s)."))

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
        for key, value in self.stats.items():
            # create a place to hold stats from this period
            if len(value) > 0:
                # Copy the previous value into it as the default action
                value.append(value[-1])
            else:
                value.append(0)

    def _update_period_stats(self, period):
        """
        Called after each frame to update system-wide statistics
        """
        # Update base stats
        self.stats[History.DRIVER_COUNT][-1] = self.driver_count
        self.stats[History.REQUEST_RATE][-1] = self.request_rate
        if self.drivers:
            for driver in self.drivers:
                self.stats[driver.phase][-1] += 1
                self.stats[History.CUMULATIVE_DRIVER_TIME][-1] += 1
                # driver count and request rate are filled in anew each period
        if self.trips:
            for trip in self.trips:
                trip.phase_time[trip.phase] += 1

        # Compute aggregate stats for plotting
        # For Plot stats, using a rolling window, the lower bound
        # of which cannot be less than zero
        lower_bound = max((period - self.rolling_window), 0)
        # driver plot
        driver_time = (self.stats[History.CUMULATIVE_DRIVER_TIME][-1] -
                       self.stats[History.CUMULATIVE_DRIVER_TIME][lower_bound])
        trip_count = ((self.stats[History.CUMULATIVE_TRIP_COUNT][-1] -
                       self.stats[History.CUMULATIVE_TRIP_COUNT][lower_bound]))
        if driver_time == 0:
            self.stats[PlotStat.DRIVER_AVAILABLE_FRACTION][-1] = 0
            self.stats[PlotStat.DRIVER_PICKUP_FRACTION][-1] = 0
            self.stats[PlotStat.DRIVER_PAID_FRACTION][-1] = 0
            self.stats[PlotStat.DRIVER_MEAN_COUNT][-1] = self.driver_count
        else:
            self.stats[PlotStat.DRIVER_AVAILABLE_FRACTION][-1] = (
                (self.stats[DriverPhase.AVAILABLE][-1] -
                 self.stats[DriverPhase.AVAILABLE][lower_bound]) / driver_time)
            self.stats[PlotStat.DRIVER_PICKUP_FRACTION][-1] = (
                (self.stats[DriverPhase.PICKING_UP][-1] -
                 self.stats[DriverPhase.PICKING_UP][lower_bound]) /
                driver_time)
            self.stats[PlotStat.DRIVER_PAID_FRACTION][-1] = (
                (self.stats[DriverPhase.WITH_RIDER][-1] -
                 self.stats[DriverPhase.WITH_RIDER][lower_bound]) /
                driver_time)
            self.stats[PlotStat.DRIVER_MEAN_COUNT][-1] = (
                sum(self.stats[History.DRIVER_COUNT][lower_bound:]) /
                (len(self.stats[History.DRIVER_COUNT]) - lower_bound))
            self.stats[PlotStat.DRIVER_UTILITY][-1] = (self._utility_supply(
                self.stats[PlotStat.DRIVER_PAID_FRACTION][-1]))
        # trip stats
        if trip_count == 0:
            self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][-1] = 0
            self.stats[PlotStat.TRIP_MEAN_LENGTH][-1] = 0
            self.stats[PlotStat.TRIP_LENGTH_FRACTION][-1] = 0
        else:
            self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][-1] = (
                (self.stats[History.CUMULATIVE_WAIT_TIME][-1] -
                 self.stats[History.CUMULATIVE_WAIT_TIME][lower_bound]) /
                trip_count)
            self.stats[PlotStat.TRIP_MEAN_LENGTH][-1] = (
                (self.stats[History.CUMULATIVE_TRIP_DISTANCE][-1] -
                 self.stats[History.CUMULATIVE_TRIP_DISTANCE][lower_bound]) /
                trip_count)
            self.stats[PlotStat.TRIP_LENGTH_FRACTION][-1] = (
                self.stats[PlotStat.TRIP_MEAN_LENGTH][-1] /
                self.city.city_size)
            self.stats[PlotStat.TRIP_WAIT_FRACTION][-1] = (
                self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][-1] /
                (self.stats[PlotStat.TRIP_MEAN_LENGTH][-1] +
                 self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][-1]))
            self.stats[PlotStat.TRIP_COUNT][-1] = (
                (self.stats[History.CUMULATIVE_TRIP_COUNT][-1] -
                 self.stats[History.CUMULATIVE_TRIP_COUNT][lower_bound]) /
                (len(self.stats[History.CUMULATIVE_TRIP_COUNT]) - lower_bound))
            self.stats[PlotStat.TRIP_UTILITY][-1] = (self._utility_demand(
                self.stats[PlotStat.TRIP_WAIT_FRACTION][-1]))

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
        self.stats[History.CUMULATIVE_TRIP_COUNT][-1] += 1
        self.stats[History.CUMULATIVE_TRIP_DISTANCE][-1] += trip.distance
        # Bad naming: CUMULATIVE_WAIT_TIME includes both WAITING and UNASSIGNED
        self.stats[History.CUMULATIVE_WAIT_TIME][-1] += trip.phase_time[
            TripPhase.UNASSIGNED]
        self.stats[History.CUMULATIVE_WAIT_TIME][-1] += trip.phase_time[
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
        plot_size = 5
        if self.draw in (Draw.DRIVER, Draw.STATS, Draw.TRIP, Draw.MAP):
            ncols = 1
        elif self.draw in (Draw.ALL, ):
            ncols = 2
        elif self.draw in (Draw.EQUILIBRATION, ):
            ncols = 3
        fig, axes = plt.subplots(ncols=ncols,
                                 figsize=(ncols * plot_size, plot_size))
        if self.draw == Draw.EQUILIBRATION:
            suptitle = (f"U_S = p.B - {self.driver_cost:.02f}; "
                        f"U_D = {self.ride_utility:.02f} - p - "
                        f"{self.wait_cost:.02f} * W; "
                        f"p = {self.price}")
        else:
            suptitle = (f"Simulation with "
                        f"{self.driver_count} drivers, "
                        f"{self.request_rate} requests per period")
        fig.suptitle(suptitle)
        if ncols == 1:
            axes = [axes]
        # Position the display window on the screen
        thismanager = plt.get_current_fig_manager()
        thismanager.window.wm_geometry("+10+10")

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

    def _equilibrate_supply(self, period):
        """
        Change the driver count and request rate
        to move the system towards equilibrium. The condition is:
        If utility or income is positive, add drivers; if negative
        drivers will leave. For a single driver:
            busy ~ request_rate * trip_length / driver_count
        Total utility = utility * driver_count, so 
            du/dn = - cost
        """
        if ((period % self.equilibration_interval == 0)
                and period >= self.rolling_window):
            # only update at certain time_periods
            # compute equilibrium condition D_0(L/S_0(W_0 + L) - B
            driver_increment = 0
            busy_fraction = self.stats[PlotStat.DRIVER_PAID_FRACTION][-1]
            utility = self._utility_supply(busy_fraction)
            # supply = busy_fraction
            damping_factor = 1
            driver_increment = round(utility /
                                     (self.driver_cost * damping_factor))
            if driver_increment > 0:
                self.drivers += [
                    Driver(i, self.city, self.available_drivers_moving)
                    for i in range(self.driver_count, self.driver_count +
                                   driver_increment)
                ]
            elif driver_increment < 0:
                for i, driver in enumerate(self.drivers):
                    driver_removed = False
                    if driver.phase == DriverPhase.AVAILABLE:
                        del self.drivers[i]
                        driver_removed = True
                        # break
                if not driver_removed:
                    logger.info("No drivers without ride assignments. "
                                "Cannot remove any drivers")
            self.driver_count = len(self.drivers)
            logger.info((f"Supply - period: {period}, "
                         f"utility: {utility:.02f}, "
                         f"busy: {busy_fraction:.02f}, "
                         f"increment: {driver_increment}, "
                         f"drivers now: {self.driver_count}"))

    def _equilibrate_demand(self, period):
        """
        At a fixed price, adjust the request rate
        """
        if ((period % self.equilibration_interval == 0)
                and period >= self.rolling_window):
            # only update at certain time_periods
            # compute equilibrium condition D_0(L/S_0(W_0 + L) - B
            wait_fraction = self.stats[PlotStat.TRIP_WAIT_FRACTION][-1]
            utility = self._utility_demand(wait_fraction)
            damping_factor = 20
            increment = 1.0 / damping_factor
            if utility > EQUILIBRIUM_BLUR:
                # Still some slack in the system: add requests
                self.request_rate = self.request_rate + increment
            elif utility < -EQUILIBRIUM_BLUR:
                # Too many rides: cut some out
                self.request_rate = max(self.request_rate - increment, 0.1)
            logger.info((f"Demand - period: {period}, "
                         f"utility: {utility:.02f}, "
                         f"wait_fraction: {wait_fraction:.02f}, "
                         f"increment: {increment:.02f}, "
                         f"request rate: {self.request_rate:.02f}: "))

    def _utility_supply(self, busy_fraction):
        """
        Utility function for drivers (supply)
            utility = price * busy - cost;
        """
        utility = self.price * busy_fraction - self.driver_cost
        return utility

    def _utility_demand(self, wait_fraction):
        """

        Utility = u_0 - P - D W'
        where W' = W/(W+L)
        """
        utility = (self.ride_utility - self.price -
                   self.wait_cost * wait_fraction)
        return utility

    def _next_frame(self, i, axes):
        """
        Function called from animator to generate frame i of the animation.
        """
        starting_period = 0
        if i % self.interpolation_points == 0:
            # A "real" time point. Update the system
            starting_period = int(i / self.interpolation_points)
            self._next_period(starting_period)
        axis_index = 0
        if self.draw in (Draw.ALL, Draw.MAP):
            self._draw_map(i, axes[axis_index])
            axis_index += 1
        if starting_period > 0:
            if starting_period % self.draw_update_period != 0:
                return
        if self.draw in (Draw.ALL, Draw.STATS, Draw.DRIVER, Draw.TRIP):
            plotstat_list = []
            if self.draw in (Draw.ALL, Draw.STATS, Draw.DRIVER):
                plotstat_list.append(PlotStat.DRIVER_AVAILABLE_FRACTION)
                plotstat_list.append(PlotStat.DRIVER_PICKUP_FRACTION)
                plotstat_list.append(PlotStat.DRIVER_PAID_FRACTION)
            if self.draw in (Draw.ALL, Draw.STATS, Draw.TRIP):
                plotstat_list.append(PlotStat.TRIP_WAIT_FRACTION)
                plotstat_list.append(PlotStat.TRIP_LENGTH_FRACTION)
            self._draw_fractional_stats(i, axes[axis_index], plotstat_list)
            axis_index += 1
        if self.draw in (Draw.EQUILIBRATION, ):
            self._draw_equilibration_plot(i,
                                          axes[axis_index],
                                          History.DRIVER_COUNT,
                                          History.REQUEST_RATE,
                                          xlim=[0],
                                          ylim=[0])
            axis_index += 1
            self._draw_equilibration_plot(i,
                                          axes[axis_index],
                                          PlotStat.TRIP_WAIT_FRACTION,
                                          PlotStat.DRIVER_PAID_FRACTION,
                                          ylim=[0, 1])
            axis_index += 1
            self._draw_equilibration_plot(i,
                                          axes[axis_index],
                                          PlotStat.DRIVER_UTILITY,
                                          PlotStat.TRIP_UTILITY,
                                          xlim=[-0.5, 0.5],
                                          ylim=[-0.5, 0.5])
            axis_index += 1

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
                        or self.available_drivers_moving):
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

    def _draw_fractional_stats(self,
                               i,
                               ax,
                               plotstat_list,
                               draw_line_chart=True):
        """
        For a list of PlotStats arrays that describe fractional properties,
        draw them on a plot with vertical axis [0,1]
        """
        if i % self.interpolation_points == 0:
            ax.clear()
            period = int(i / self.interpolation_points)
            lower_bound = max((period - CHART_X_RANGE), 0)
            x_range = list(
                range(lower_bound,
                      len(self.stats[PlotStat.DRIVER_AVAILABLE_FRACTION])))
            ax.set_title(f"Fractional properties, "
                         f"rolling {self.rolling_window}-period average")
            if draw_line_chart:
                for index, fractional_property in enumerate(plotstat_list):
                    ax.plot(x_range,
                            self.stats[fractional_property][lower_bound:],
                            color=self.color_palette[index],
                            label=fractional_property.value,
                            lw=3,
                            alpha=0.7)
                ax.set_ylim(bottom=0, top=1)
                ax.set_xlabel("Time (periods)")
                ax.set_ylabel("Fractional property values")
                ax.legend()
            else:
                x = []
                height = []
                labels = []
                colors = []
                for fractional_property in plotstat_list:
                    x.append(fractional_property.value)
                    height.append(self.stats[fractional_property][-1])
                    labels.append(fractional_property.value)
                    colors.append(
                        self.color_palette[fractional_property.value])
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

    def _draw_equilibration_plot(self,
                                 i,
                                 ax,
                                 plotstat_x,
                                 plotstat_y,
                                 xlim=None,
                                 ylim=None):
        """
        Plot wait time against busy fraction, to watch equilibration
        """
        if i % self.interpolation_points == 0:
            x = self.stats[plotstat_x]
            y = self.stats[plotstat_y]
            period = int(i / self.interpolation_points)
            most_recent_equilibration = max(
                1,
                self.equilibration_interval *
                int(period / self.equilibration_interval))
            ax.clear()
            ax.set_title(f"Period {period}: {self.driver_count} drivers, "
                         f"{self.request_rate:.02f} requests per period")
            ax.plot(x[:most_recent_equilibration],
                    y[:most_recent_equilibration],
                    lw=3,
                    color=self.color_palette[1],
                    alpha=0.2)
            ax.plot(x[most_recent_equilibration - 1:],
                    y[most_recent_equilibration - 1:],
                    lw=3,
                    color=self.color_palette[1],
                    alpha=0.6)
            ax.plot(x[-1],
                    y[-1],
                    marker='o',
                    markersize=8,
                    color=self.color_palette[2],
                    alpha=0.9)
            if xlim:
                ax.set_xlim(left=min(xlim))
                if len(xlim) > 1:
                    ax.set_xlim(right=max(xlim))
            if ylim:
                ax.set_ylim(bottom=min(ylim))
                if len(ylim) > 1:
                    ax.set_ylim(top=max(ylim))
            ax.set_xlabel(f"{plotstat_x.value}")
            ax.set_ylabel(f"{plotstat_y.value}")


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
    def __init__(self,
                 i,
                 city,
                 available_drivers_moving=False,
                 location=[0, 0]):
        """
        Create a driver at a random location.
        Grid has edge self.city.city_size, in blocks spaced 1 apart
        """
        self.index = i
        self.city = city
        self.available_drivers_moving = available_drivers_moving
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
            if self.available_drivers_moving:
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
                and not self.available_drivers_moving):
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
    parser.add_argument("-@",
                        "--config_file",
                        metavar="config_file",
                        action="store",
                        type=str,
                        default=None,
                        help="""Configuration file""")
    parser.add_argument("-adm",
                        "--available_drivers_moving",
                        metavar="available_drivers_moving",
                        action="store",
                        type=bool,
                        default=False,
                        help="""True if drivers should drive around looking for
                        a ride; False otherwise.""")
    parser.add_argument("-cs",
                        "--city_size",
                        metavar="city_size",
                        action="store",
                        type=int,
                        default=None,
                        help="""Length of the city grid, in blocks.""")
    parser.add_argument("-d",
                        "--driver_count",
                        metavar="driver_count",
                        action="store",
                        type=int,
                        default=None,
                        help="number of drivers")
    parser.add_argument("-du",
                        "--draw_update_period",
                        metavar="draw_update_period",
                        action="store",
                        type=int,
                        default=1,
                        help="How often to update charts")
    parser.add_argument("-ei",
                        "--equilibration_interval",
                        metavar="equilibration_interval",
                        type=int,
                        default=None,
                        action="store",
                        help="""Interval at which to adjust supply and/or
                        demand""")
    parser.add_argument("-eq",
                        "--equilibrate",
                        metavar="equilibrate",
                        type=str,
                        default=None,
                        action="store",
                        help="""Change driver count  or request rate, or both,
                        to equilibrate""")
    parser.add_argument("-dc",
                        "--driver_cost",
                        metavar="driver_cost",
                        action="store",
                        type=float,
                        default=None,
                        help="""Driver cost per unit time""")
    parser.add_argument("-i",
                        "--interpolate",
                        metavar="interpolate",
                        action="store",
                        type=int,
                        default=None,
                        help="""Number of interpolation points when updating
                        the map display""")
    parser.add_argument("-img",
                        "--imagemagick_dir",
                        metavar="imagemagick_dir",
                        action="store",
                        type=str,
                        default=None,
                        help="""ImageMagick Directory""")
    parser.add_argument("-l",
                        "--log_file",
                        metavar="log_file",
                        action="store",
                        type=str,
                        default=None,
                        help=("Logfile name. By default, log messages "
                              "are written to the screen only"))
    parser.add_argument(
        "-o",
        "--output",
        metavar="output",
        action="store",
        type=str,
        default=None,
        help="""filename: output to the display or as a file; gif or mp4""")
    parser.add_argument("-p",
                        "--price",
                        action="store",
                        type=float,
                        default=None,
                        help="Fixed price")
    parser.add_argument("-q",
                        "--quiet",
                        action="store_true",
                        default=False,
                        help="log only warnings and errors")
    parser.add_argument(
        "-ur",
        "--ride_utility",
        metavar="ride_utility",
        action="store",
        type=float,
        default=None,
        help="utility of a trip, per period, for the passenger")
    parser.add_argument("-r",
                        "--request_rate",
                        metavar="request_rate",
                        action="store",
                        type=float,
                        default=None,
                        help="requests per period")
    parser.add_argument("-dr",
                        "--draw",
                        metavar="draw",
                        action="store",
                        type=str,
                        default=None,
                        help="""draw 'all', 'none', 'driver', 'wait',
                        'stats', 'equilibration', ['map']""")
    parser.add_argument("-t",
                        "--time_periods",
                        metavar="time_periods",
                        action="store",
                        type=int,
                        default=None,
                        help="numberof time time periods")
    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        default=False,
                        help="log all messages, including debug")
    parser.add_argument("-rw",
                        "--rolling_window",
                        metavar="rolling_window",
                        action="store",
                        type=int,
                        default=None,
                        help="""rolling window for computing averages""")
    parser.add_argument("-wc",
                        "--wait_cost",
                        metavar="wait_cost",
                        action="store",
                        type=float,
                        default=None,
                        help="""Passenger cost per unit wait fraction""")
    args = parser.parse_args()
    return args


class RideHailSimulationSequence():
    """
    A sequence of simulations
    """
    def __init__(self, config):
        """
        """
        self.config = config
        self.driver_count = []
        self.request_rate = []
        self.trip_wait_fraction = []
        self.driver_busy_fraction = []
        self.driver_idle_fraction = []
        self.frame_count = (len(self.config.request_rate) *
                            len(self.config.driver_count))
        self.plot_count = len(set(self.config.request_rate))
        self.color_palette = sns.color_palette()

    def run_sequence(self):
        """
        Do the run
        """
        plot_size = 6
        fig, axes = plt.subplots(ncols=self.plot_count,
                                 figsize=(self.plot_count * plot_size,
                                          plot_size))
        axes = [axes] if self.plot_count == 1 else axes
        # Position the display window on the screen
        thismanager = plt.get_current_fig_manager()
        thismanager.window.wm_geometry("+10+10")
        animation = FuncAnimation(fig,
                                  self._next_frame,
                                  frames=self.frame_count,
                                  fargs=[axes],
                                  repeat=False,
                                  repeat_delay=3000)
        Plot().output(animation, plt, self.__class__.__name__,
                      self.config.output)
        logger.info("Sequence completed")

    def _next_sim(self, index):
        """
        Run a single simulation
        """
        runconfig = copy.deepcopy(self.config)
        request_rate_index = int(index / len(self.config.driver_count))
        driver_count_index = index % len(self.config.driver_count)
        request_rate = self.config.request_rate[request_rate_index]
        driver_count = self.config.driver_count[driver_count_index]
        logger.info((f"request_rate = "
                     f"{request_rate}, "
                     f"driver_count = "
                     f"{driver_count}"))
        runconfig.request_rate = request_rate
        runconfig.driver_count = driver_count
        simulation = RideHailSimulation(runconfig)
        results = simulation.simulate()
        self.driver_count.append(results.sim.driver_count)
        self.request_rate.append(results.sim.request_rate)
        self.driver_idle_fraction.append(
            results.sim.stats[PlotStat.DRIVER_AVAILABLE_FRACTION][-1])
        self.driver_busy_fraction.append(
            results.sim.stats[PlotStat.DRIVER_PAID_FRACTION][-1])
        self.trip_wait_fraction.append(
            results.sim.stats[PlotStat.TRIP_WAIT_FRACTION][-1])

    def _next_frame(self, i, axes):
        """
        Function called from sequence animator to generate frame i
        of the animation.
        """
        self._next_sim(i)
        ax = axes[0]
        ax.clear()
        # Fit with numpy
        x = self.driver_count
        driver_count_points = len(self.config.driver_count)
        ax.plot(x,
                self.driver_busy_fraction,
                lw=0,
                marker="o",
                markersize=6,
                color=self.color_palette[0],
                alpha=0.4,
                label=PlotStat.DRIVER_PAID_FRACTION.value)
        try:
            popt1, _ = curve_fit(self._fit, x, self.driver_busy_fraction)
            y1 = [self._fit(xval, *popt1) for xval in x[:driver_count_points]]
            ax.plot(x[:driver_count_points], y1, lw=2, alpha=0.7)
        except (RuntimeError, TypeError) as e:
            logger.warning(e)
        ax.plot(x,
                self.trip_wait_fraction,
                lw=0,
                marker="o",
                markersize=6,
                color=self.color_palette[1],
                alpha=0.4,
                label=PlotStat.TRIP_WAIT_FRACTION.value)
        try:
            popt2, _ = curve_fit(self._fit, x, self.trip_wait_fraction)
            y2 = [self._fit(xval, *popt2) for xval in x[:driver_count_points]]
            ax.plot(x[:driver_count_points], y2, lw=2, alpha=0.7)
        except (RuntimeError, TypeError) as e:
            logger.error(e)
        ax.plot(x,
                self.driver_idle_fraction,
                lw=0,
                marker="o",
                markersize=6,
                color=self.color_palette[2],
                alpha=0.4,
                label=PlotStat.DRIVER_AVAILABLE_FRACTION.value)
        try:
            popt3, _ = curve_fit(self._fit, x, self.driver_idle_fraction)
            y3 = [self._fit(xval, *popt3) for xval in x[:driver_count_points]]
            ax.plot(x[:driver_count_points], y3, lw=2, alpha=0.7)
        except (RuntimeError, TypeError) as e:
            logger.error(e)
        ax.set_xlim(left=0, right=max(self.config.driver_count))
        ax.set_ylim(bottom=0, top=1)
        ax.set_xlabel("Drivers")
        ax.legend()

    def _fit(self, x, a, b, c):
        return (a + b / (x + c))


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
    if args.log_file:
        logging.basicConfig(filename=args.log_file,
                            filemode='w',
                            level=getattr(logging, loglevel.upper()),
                            format='%(asctime)-15s %(levelname)-8s%(message)s')
    else:
        logging.basicConfig(level=getattr(logging, loglevel.upper()),
                            format='%(levelname)-8s%(message)s')
    logger.debug("Logging debug messages...")
    # config = read_config(args)
    config = Config(args)
    if config is False:
        exit(False)
    else:
        if config.draw == Draw.SUMMARY:
            sequence = RideHailSimulationSequence(config)
            sequence.run_sequence()
        else:
            runconfig = copy.deepcopy(config)
            for request_rate in config.request_rate:
                logger.info((f"config.request_rate = {config.request_rate}, "
                             f"config.driver_count = {config.driver_count}"))
                runconfig.request_rate = request_rate
                for driver_count in config.driver_count:
                    runconfig.driver_count = driver_count
                    simulation = RideHailSimulation(runconfig)
                    results = simulation.simulate()
                    results.write()


if __name__ == '__main__':
    main()
