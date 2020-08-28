#!/usr/bin/python3
"""
A simulation
"""
import logging
import os
import matplotlib.pyplot as plt
import random
import json
from datetime import datetime
from time import sleep
from enum import Enum
import numpy as np
from matplotlib.ticker import MultipleLocator
from matplotlib.animation import FuncAnimation
from matplotlib.widgets import Button
import seaborn as sns
from ridehail.atom import City, Driver, Trip, DriverPhase, TripPhase, Direction, TripDistribution
from ridehail.plot import Plot, PlotStat, Draw

logger = logging.getLogger(__name__)

FRAME_INTERVAL = 50
FIRST_REQUEST_OFFSET = 0
EQUILIBRIUM_BLUR = 0.02
CHART_X_RANGE = 200
GARBAGE_COLLECTION_INTERVAL = 10
# Placeholder frame count for animation.  The
# actual frame count is managed with simulation.frame_count
FRAME_COUNT_UPPER_LIMIT = 10000000
# Log the period every PRINT_INTERVAL periods
PRINT_INTERVAL = 10


class History(str, Enum):
    CUMULATIVE_DRIVER_TIME = "Cumulative driver time"
    CUMULATIVE_WAIT_TIME = "Cumulative wait time"
    CUMULATIVE_TRIP_COUNT = "Cumulative completed trips"
    CUMULATIVE_TRIP_DISTANCE = "Cumulative distance"
    CUMULATIVE_REQUESTS = "Cumulative requests"
    DRIVER_COUNT = "Driver count"
    REQUEST_RATE = "Request rate"
    CUMULATIVE_DRIVER_P1_TIME = "Cumulative driver P1 time"
    CUMULATIVE_DRIVER_P2_TIME = "Cumulative driver P2 time"
    CUMULATIVE_DRIVER_P3_TIME = "Cumulative driver P3 time"
    CUMULATIVE_TRIP_UNASSIGNED_TIME = "Cumulative trip unassigned time"
    CUMULATIVE_TRIP_AWAITING_TIME = "Cumulative trip awaiting time"
    CUMULATIVE_TRIP_RIDING_TIME = "Cumulative trip riding time"
    DRIVER_UTILITY = "Driver utility"
    TRIP_UTILITY = "Trip utility"


class Equilibration(str, Enum):
    SUPPLY = "Supply"
    DEMAND = "Demand"
    FULL = "Full"
    NONE = "None"


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
        self.config = config
        self.config_file_root = (os.path.splitext(
            os.path.split(config.config_file)[1])[0])
        self.city = City(config.city_size,
                         trip_distribution=config.trip_distribution)
        self.available_drivers_moving = config.available_drivers_moving
        self.drivers = [
            Driver(i, self.city, self.available_drivers_moving)
            for i in range(config.driver_count)
        ]
        self.equilibrate = config.equilibrate
        if self.equilibrate and self.equilibrate != Equilibration.NONE:
            self.price = config.price
            self.driver_cost = config.driver_cost
            self.driver_price_factor = config.driver_price_factor
            self.ride_utility = config.ride_utility
            self.demand_slope = config.demand_slope
            self.wait_cost = config.wait_cost
            self.equilibration_interval = config.equilibration_interval
        self.request_rate = config.request_rate
        self.time_periods = config.time_periods
        self.draw_update_period = config.draw_update_period
        self.interpolation_points = config.interpolate
        self.frame_count = config.time_periods * self.interpolation_points
        self.frame_index = 0
        self.period_index = 0
        self.last_period_frame_index = 0
        self.pause_plot = False  # toggle for pausing
        self.rolling_window = config.rolling_window
        self.output = config.output
        self.draw = config.draw
        self.trips = []
        self.color_palette = sns.color_palette()
        self.stats = {}
        for total in list(History):
            self.stats[total] = np.empty(self.time_periods)
        for stat in list(PlotStat):
            self.stats[stat] = np.empty(self.time_periods)
        # self.state holds the current valus of parameters that may
        # change during the simulation. If we change one of these values
        # the new value is stored in self.state, and the new values of the
        # actual parameters are updated at the end of each perio.
        # This set is expanding as the program gets more complex.
        self.state = {}
        self.state["city_size"] = self.city.city_size
        self.state["interpolation_points"] = self.interpolation_points
        self.state["driver_count"] = len(self.drivers)
        self.state["request_rate"] = self.request_rate
        self.state["trip_distribution"] = self.city.trip_distribution

    # (todays_date-datetime.timedelta(10), time_periods=10, freq='D')

    def simulate(self):
        """
        Plot the trend of cumulative cases, observed at
        earlier days, evolving over time.
        """
        # initial plot
        if self.draw in (Draw.NONE, Draw.SUMMARY):
            for period in range(self.time_periods):
                self._next_period()
        else:
            self._animate()
        results = RideHailSimulationResults(self)
        return results

    def on_click(self, event):
        self.pause_plot ^= True

    def on_key_press(self, event):
        """
        Respond to a + or - key press
        """
        if event.key == "+":
            self.state["driver_count"] = max(
                int(self.state["driver_count"] * 1.1),
                self.state["driver_count"] + 1)
        elif event.key == "-":
            self.state["driver_count"] = min(
                int(self.state["driver_count"] * 0.9),
                (self.state["driver_count"] - 1))
        elif event.key == "ctrl++":
            self.state["request_rate"] = max(
                (self.state["request_rate"] * 1.1), 0.1)
        elif event.key == "ctrl+-":
            self.state["request_rate"] = max(
                (self.state["request_rate"] * 0.9), 0.1)
        elif event.key == "v":
            # TODO: This screws up statistics plots because % operator
            # assumes interpolation_points is constant over time
            self.state["interpolation_points"] = max(
                self.state["interpolation_points"] + 1, 1)
        elif event.key == "V":
            self.state["interpolation_points"] = max(
                self.state["interpolation_points"] - 1, 1)
        # elif event.key == "P":
        #     if self.draw == Draw.ALL:
        #         self.draw = Draw.STATS
        #     elif self.draw == Draw.MAP:
        #         self.draw = Draw.ALL
        # elif event.key == "p":
        #     if self.draw == Draw.ALL:
        #         self.draw = Draw.STATS
        #     elif self.draw == Draw.STATS:
        #         self.draw = Draw.MAP
        elif event.key == "c":
            self.state["city_size"] = max(self.state["city_size"] - 1, 2)
        elif event.key == "C":
            self.state["city_size"] = max(self.state["city_size"] + 1, 2)
        elif event.key == "ctrl+t":
            if self.state["trip_distribution"] == TripDistribution.UNIFORM:
                self.state["trip_distribution"] = TripDistribution.BETA
            elif self.state["trip_distribution"] == TripDistribution.BETA:
                self.state["trip_distribution"] = TripDistribution.UNIFORM

    def _next_period(self):
        """
        Call all those functions needed to simulate the next period
        """
        period = self.period_index
        if period % PRINT_INTERVAL == 0:
            logger.info(
                f"-------"
                f"Period {period} at"
                f" {datetime.now().strftime('%Y-%m-%d-%H:%M:%S.%f')[:-4]}"
                f"-----------")
        self._init_period(period)
        if self.equilibrate is not None:
            # Using the stats from the previous period,
            # equilibrate the supply and/or demand of rides
            if (self.equilibrate in (Equilibration.SUPPLY,
                                     Equilibration.FULL)):
                self._equilibrate_supply(period)
            if (self.equilibrate in (Equilibration.DEMAND,
                                     Equilibration.FULL)):
                self._equilibrate_demand(period)
        for driver in self.drivers:
            # Move drivers
            driver.update_location()
            driver.update_direction()
            if driver.trip_index is not None:
                # If the driver arrives at a pickup or dropoff location,
                # handle the phase changes
                trip = self.trips[driver.trip_index]
                if (driver.phase == DriverPhase.PICKING_UP
                        and driver.location == driver.pickup):
                    # the driver has arrived at the pickup spot and picks up
                    # the rider
                    driver.phase_change()
                    trip.phase_change(to_phase=TripPhase.RIDING)
                elif (driver.phase == DriverPhase.WITH_RIDER
                      and driver.location == driver.dropoff):
                    # The driver has arrived at the dropoff and the trip ends.
                    # Update trip-related stats with this completed
                    # trip's information
                    # Update trip stats in update_history_arrays instead
                    # Remove this call when proven correct
                    # self._update_trip_stats(trip, period)
                    # Update driver and trip to reflect the completion
                    driver.phase_change()
                    trip.phase_change(to_phase=TripPhase.FINISHED)
        # Customers make trip requests
        self._request_trips(period)
        # If there are drivers free, assign one to each request
        self._assign_drivers()
        # Some requests get abandoned if they have been open too long
        self._abandon_requests()
        # Update stats for everything that has happened in this period
        self._update_history_arrays(period)
        self._update_plot_stats(period)
        # Some arrays hold information for each trip:
        # compress these as needed to avoid a growing set
        # of completed or abandoned (dead) trips
        self._collect_garbage(period)
        self.period_index += 1

    def _request_trips(self, period):
        """
        Periodically initiate a request from an inactive rider
        For requests not assigned a driver, repeat the request.

        """
        # TODO This is the only place a History stat is updated outside
        # _update_period_stats. It would be good to fix this somehow.
        self.stats[History.CUMULATIVE_REQUESTS][period] += self.request_rate
        # Given a request rate r, compute the number of requests this
        # period.
        if period < FIRST_REQUEST_OFFSET:
            logging.info(f"period {period} < {FIRST_REQUEST_OFFSET}")
            return
        trips_this_period = (
            int(self.stats[History.CUMULATIVE_REQUESTS][period]) -
            int(self.stats[History.CUMULATIVE_REQUESTS][period - 1]))
        for trip in range(trips_this_period):
            trip = Trip(len(self.trips),
                        self.city,
                        min_trip_distance=self.config.min_trip_distance)
            self.trips.append(trip)
            logger.debug(
                (f"Request: trip {trip.origin} -> {trip.destination}"))
            # the trip has a random origin and destination
            # and is ready to make a request.
            # This sets the trip to TripPhase.UNASSIGNED
            # as no driver is assigned here
            trip.phase_change(TripPhase.UNASSIGNED)
        if trips_this_period > 0:
            logger.debug((f"Period {period}: "
                          f"rate {self.request_rate:.02f}: "
                          f"{trips_this_period} trip request(s)."))

    def _assign_drivers(self):
        """
        All trips without an assigned driver make a request
        Randomize the order just in case there is some problem
        """
        unassigned_trips = [
            trip for trip in self.trips if trip.phase == TripPhase.UNASSIGNED
        ]
        if unassigned_trips:
            random.shuffle(unassigned_trips)
            logger.debug(f"There are {len(unassigned_trips)} unassigned trips")
            available_drivers = [
                driver for driver in self.drivers
                if driver.phase == DriverPhase.AVAILABLE
            ]
            # randomize the driver list to prevent early drivers
            # having an advantage in the case of equality
            random.shuffle(available_drivers)
            for trip in unassigned_trips:
                # Try to assign a driver to this trop
                assigned_driver = self._assign_driver(trip, available_drivers)
                # If a driver is assigned (not None), update the trip phase
                if assigned_driver:
                    available_drivers.remove(assigned_driver)
                    assigned_driver.phase_change(trip=trip)

                    trip.phase_change(to_phase=TripPhase.WAITING)
                    if assigned_driver.location == trip.origin:
                        # Do the pick up now
                        assigned_driver.phase_change(trip=trip)
                        trip.phase_change(to_phase=TripPhase.RIDING)
                else:
                    logger.debug(f"No driver assigned for trip {trip.index}")

    def _assign_driver(self, trip, available_drivers):
        """
        Find the nearest driver to a ridehail call at x, y
        Set that driver's phase to PICKING_UP
        Returns an assigned driver or None
        """
        logger.debug("Assigning a driver to a request...")
        min_distance = self.city.city_size * 100  # Very big
        assigned_driver = None
        if available_drivers:
            for driver in available_drivers:
                travel_distance = self.city.travel_distance(
                    driver.location, driver.direction, trip.origin,
                    min_distance)
                if travel_distance < min_distance:
                    min_distance = travel_distance
                    assigned_driver = driver
                    logger.debug((f"Driver at {assigned_driver.location} "
                                  f"travelling {driver.direction.name} "
                                  f"assigned to pickup at {trip.origin}. "
                                  f"Travel distance {travel_distance}."))
                if travel_distance <= 1:
                    break
        return assigned_driver

    def _abandon_requests(self):
        """
        If a request has been waiting too long, abandon it.

        For now "too long" = city length
        """
        unassigned_trips = [
            trip for trip in self.trips if trip.phase == TripPhase.UNASSIGNED
        ]
        for trip in unassigned_trips:
            if trip.phase_time[TripPhase.UNASSIGNED] > self.city.city_size:
                trip.phase_change(to_phase=TripPhase.ABANDONED)
                logger.info(
                    (f"Trip {trip.index} abandoned after "
                     f"{trip.phase_time[TripPhase.UNASSIGNED]} periods."))

    def _init_period(self, period):
        """
        Add an item to the end of each stats list
        to hold this period's statistics.
        The value is carried over from the previous period,
        which works for Sum totals and is overwritten
        for others.
        """

        self.city.city_size = self.state["city_size"]
        self.interpolation_points = self.state["interpolation_points"]
        self.request_rate = self.state["request_rate"]
        self.city.trip_distribution = self.state["trip_distribution"]
        old_driver_count = len(self.drivers)
        driver_diff = self.state["driver_count"] - old_driver_count
        if driver_diff > 0:
            for d in range(driver_diff):
                self.drivers.append(
                    Driver(old_driver_count + d, self.city,
                           self.available_drivers_moving))
        elif driver_diff < 0:
            for d in range(-driver_diff):
                self.drivers.pop()
        for array_name, array in self.stats.items():
            # create a place to hold stats from this period
            if period > 1:
                # Copy the previous value into it as the default action
                array[period] = array[period - 1]
            else:
                array[period] = 0

    def _update_history_arrays(self, period):
        """
        Called after each period to update history statistics
        """
        # Update base stats
        # driver count and request rate are filled in anew each period
        self.stats[History.DRIVER_COUNT][period] = len(self.drivers)
        self.stats[History.REQUEST_RATE][period] = self.request_rate
        # other stats are cumulative, so that differences can be taken
        if self.drivers:
            for driver in self.drivers:
                self.stats[History.CUMULATIVE_DRIVER_TIME][period] += 1
                if driver.phase == DriverPhase.AVAILABLE:
                    self.stats[History.CUMULATIVE_DRIVER_P1_TIME][period] += 1
                elif driver.phase == DriverPhase.PICKING_UP:
                    self.stats[History.CUMULATIVE_DRIVER_P2_TIME][period] += 1
                elif driver.phase == DriverPhase.WITH_RIDER:
                    self.stats[History.CUMULATIVE_DRIVER_P3_TIME][period] += 1
        if self.trips:
            for trip in self.trips:
                phase = trip.phase
                trip.phase_time[phase] += 1
                if phase == TripPhase.UNASSIGNED:
                    self.stats[
                        History.CUMULATIVE_TRIP_UNASSIGNED_TIME][period] += 1
                    # Bad name: CUMULATIVE_WAIT_TIME = WAITING + UNASSIGNED
                    self.stats[History.CUMULATIVE_WAIT_TIME][period] += 1
                elif phase == TripPhase.WAITING:
                    self.stats[
                        History.CUMULATIVE_TRIP_AWAITING_TIME][period] += 1
                    # Bad name: CUMULATIVE_WAIT_TIME = WAITING + UNASSIGNED
                    self.stats[History.CUMULATIVE_WAIT_TIME][period] += 1
                elif phase == TripPhase.RIDING:
                    self.stats[
                        History.CUMULATIVE_TRIP_RIDING_TIME][period] += 1
                    self.stats[History.CUMULATIVE_TRIP_DISTANCE][period] += 1
                elif phase == TripPhase.FINISHED:
                    self.stats[History.CUMULATIVE_TRIP_COUNT][period] += 1
                    trip.phase = TripPhase.INACTIVE
                elif phase == TripPhase.ABANDONED:
                    # nothing yet, but will do something here
                    trip.phase = TripPhase.INACTIVE
                elif phase == TripPhase.INACTIVE:
                    # nothing done with INACTIVE trips
                    pass

    def _update_plot_stats(self, period):
        """
        Plot statistics are values computed from the History arrays
        but smoothed over self.rolling_window.
        """
        # the lower bound of which cannot be less than zero
        lower_bound = max((period - self.rolling_window), 0)
        window_driver_time = (
            self.stats[History.CUMULATIVE_DRIVER_TIME][period] -
            self.stats[History.CUMULATIVE_DRIVER_TIME][lower_bound])
        # driver stats
        if window_driver_time == 0:
            # Initialize the driver arrays
            self.stats[PlotStat.DRIVER_AVAILABLE_FRACTION][period] = 0
            self.stats[PlotStat.DRIVER_PICKUP_FRACTION][period] = 0
            self.stats[PlotStat.DRIVER_PAID_FRACTION][period] = 0
            self.stats[PlotStat.DRIVER_MEAN_COUNT][period] = len(self.drivers)
            self.stats[PlotStat.DRIVER_UTILITY][period] = 0
            if self.equilibrate != Equilibration.NONE:
                self.stats[PlotStat.DRIVER_COUNT_SCALED][period] = 0
                self.stats[PlotStat.REQUEST_RATE_SCALED][period] = 0
        else:
            self.stats[PlotStat.DRIVER_AVAILABLE_FRACTION][period] = (
                (self.stats[History.CUMULATIVE_DRIVER_P1_TIME][period] -
                 self.stats[History.CUMULATIVE_DRIVER_P1_TIME][lower_bound]) /
                window_driver_time)
            self.stats[PlotStat.DRIVER_PICKUP_FRACTION][period] = (
                (self.stats[History.CUMULATIVE_DRIVER_P2_TIME][period] -
                 self.stats[History.CUMULATIVE_DRIVER_P2_TIME][lower_bound]) /
                window_driver_time)
            self.stats[PlotStat.DRIVER_PAID_FRACTION][period] = (
                (self.stats[History.CUMULATIVE_DRIVER_P3_TIME][period] -
                 self.stats[History.CUMULATIVE_DRIVER_P3_TIME][lower_bound]) /
                window_driver_time)
            self.stats[PlotStat.DRIVER_MEAN_COUNT][period] = (
                sum(self.stats[History.DRIVER_COUNT][lower_bound:period]) /
                (len(self.stats[History.DRIVER_COUNT]) - lower_bound))
            if self.equilibrate != Equilibration.NONE:
                # take average of average utility. Not sure this is the best
                # way, but it may do for now
                utility_list = [
                    self._driver_utility(
                        self.stats[PlotStat.DRIVER_PAID_FRACTION][x])
                    for x in range(lower_bound, period + 1)
                ]
                self.stats[PlotStat.DRIVER_UTILITY][period] = (
                    sum(utility_list) / len(utility_list))
                self.stats[PlotStat.DRIVER_COUNT_SCALED][period] = (
                    len(self.drivers) / (5 * self.city.city_size))

        # trip stats
        window_trip_count = (
            (self.stats[History.CUMULATIVE_TRIP_COUNT][period] -
             self.stats[History.CUMULATIVE_TRIP_COUNT][lower_bound]))
        if window_trip_count == 0:
            self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][period] = 0
            self.stats[PlotStat.TRIP_MEAN_LENGTH][period] = 0
            self.stats[PlotStat.TRIP_LENGTH_FRACTION][period] = 0
            if self.equilibrate != Equilibration.NONE:
                self.stats[PlotStat.TRIP_UTILITY][period] = 0
                self.stats[PlotStat.REQUEST_RATE_SCALED][period] = 0
        else:
            self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][period] = (
                (self.stats[History.CUMULATIVE_WAIT_TIME][period] -
                 self.stats[History.CUMULATIVE_WAIT_TIME][lower_bound]) /
                window_trip_count)
            self.stats[PlotStat.TRIP_MEAN_LENGTH][period] = (
                (self.stats[History.CUMULATIVE_TRIP_DISTANCE][period] -
                 self.stats[History.CUMULATIVE_TRIP_DISTANCE][lower_bound]) /
                window_trip_count)
            self.stats[PlotStat.TRIP_LENGTH_FRACTION][period] = (
                self.stats[PlotStat.TRIP_MEAN_LENGTH][period] /
                self.city.city_size)
            # logging.info(
            # (f"period={period}"
            # f", TLF={self.stats[PlotStat.TRIP_LENGTH_FRACTION][period]}"
            # f", TML={self.stats[PlotStat.TRIP_MEAN_LENGTH][period]}"))
            self.stats[PlotStat.TRIP_WAIT_FRACTION][period] = (
                self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][period] /
                (self.stats[PlotStat.TRIP_MEAN_LENGTH][period] +
                 self.stats[PlotStat.TRIP_MEAN_WAIT_TIME][period]))
            self.stats[PlotStat.TRIP_COUNT][period] = (
                (self.stats[History.CUMULATIVE_TRIP_COUNT][period] -
                 self.stats[History.CUMULATIVE_TRIP_COUNT][lower_bound]) /
                (len(self.stats[History.CUMULATIVE_TRIP_COUNT]) - lower_bound))
            if self.equilibrate != Equilibration.NONE:
                utility_list = [
                    self._trip_utility(
                        self.stats[PlotStat.TRIP_WAIT_FRACTION][x])
                    for x in range(lower_bound, period + 1)
                ]
                self.stats[PlotStat.TRIP_UTILITY][period] = (
                    sum(utility_list) / len(utility_list))
                self.stats[PlotStat.REQUEST_RATE_SCALED][period] = (
                    self.request_rate)

    def _collect_garbage(self, period):
        """
        Garbage collect the list of trips to get rid of the finished ones
        Requires that driver trip_index values be re-assigned
        """
        if period % GARBAGE_COLLECTION_INTERVAL == 0:
            self.trips = [
                trip for trip in self.trips
                if trip.phase not in [TripPhase.FINISHED, TripPhase.ABANDONED]
            ]
            for i, trip in enumerate(self.trips):
                for driver in self.drivers:
                    driver.trip_index = (i if driver.trip_index == trip.index
                                         else driver.trip_index)
                trip.index = i

    def _animate(self):
        """
        Do the simulation but with displays
        """
        plot_size = 8
        if self.draw in (Draw.DRIVER, Draw.STATS, Draw.TRIP, Draw.MAP):
            ncols = 1
        elif self.draw in (Draw.ALL, ):
            ncols = 2
        elif self.draw in (Draw.EQUILIBRATION, ):
            ncols = 3
        fig, axes = plt.subplots(ncols=ncols,
                                 figsize=(ncols * plot_size, plot_size))
        fig.canvas.mpl_connect('button_press_event', self.on_click)
        fig.canvas.mpl_connect('key_press_event', self.on_key_press)
        if self.draw == Draw.EQUILIBRATION:
            suptitle = (f"U_S = {self.driver_price_factor:.02f}.B.p"
                        f" - {self.driver_cost:.02f}; "
                        f"U_D = {self.ride_utility:.02f} - p"
                        f" - {self.wait_cost:.02f} * W; "
                        f"p = {self.price}")
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

        self.animation = FuncAnimation(
            fig,
            self._next_frame,
            frames=(FRAME_COUNT_UPPER_LIMIT),
            # frames=(self.frame_count),
            fargs=[axes],
            interval=FRAME_INTERVAL,
            repeat=False,
            repeat_delay=3000)
        Plot().output(self.animation, plt, self.__class__.__name__,
                      self.output)
        fig.savefig(f"./img/{self.config_file_root}"
                    f"-{datetime.now().strftime('%Y-%m-%d-%H-%M')}.png")

    def _equilibrate_supply(self, period):
        """
        Change the driver count and request rate to move the system
        towards equilibrium.
        """
        if ((period % self.equilibration_interval == 0)
                and period >= self.rolling_window):
            # only update at certain time_periods
            # compute equilibrium condition D_0(L/S_0(W_0 + L) - B
            driver_increment = 0
            p3_fraction = self.stats[PlotStat.DRIVER_PAID_FRACTION][period]
            driver_utility = self._driver_utility(p3_fraction)
            damping_factor = 0.2
            driver_increment = round(driver_utility /
                                     (self.driver_cost * damping_factor))
            old_driver_count = len(self.drivers)
            if driver_increment > 0:
                self.drivers += [
                    Driver(i, self.city, self.available_drivers_moving)
                    for i in range(old_driver_count, old_driver_count +
                                   driver_increment)
                ]
            elif driver_increment < 0:
                drivers_removed = 0
                for i, driver in enumerate(self.drivers):
                    if driver.phase == DriverPhase.AVAILABLE:
                        del self.drivers[i]
                        drivers_removed += 1
                        if drivers_removed == -driver_increment:
                            break
                if drivers_removed == 0:
                    logger.info("No drivers without ride assignments. "
                                "Cannot remove any drivers")
            logger.info((f"{{'period': {period}, "
                         f"'driver_utility': {driver_utility:.02f}, "
                         f"'busy': {p3_fraction:.02f}, "
                         f"'increment': {driver_increment}, "
                         f"'old driver count': {old_driver_count}, "
                         f"'new driver count': {len(self.drivers)}}}"))

    def _equilibrate_demand(self, period):
        """
        At a fixed price, adjust the request rate
        """
        if ((period % self.equilibration_interval == 0)
                and period >= self.rolling_window):
            # only update at certain time_periods
            # compute equilibrium condition D_0(L/S_0(W_0 + L) - B
            wait_fraction = self.stats[PlotStat.TRIP_WAIT_FRACTION][period]
            trip_utility = self._trip_utility(wait_fraction)
            damping_factor = 20
            old_request_rate = self.request_rate
            increment = 1.0 / damping_factor
            if trip_utility > EQUILIBRIUM_BLUR:
                # Still some slack in the system: add requests
                self.request_rate = self.request_rate + increment
            elif trip_utility < -EQUILIBRIUM_BLUR:
                # Too many rides: cut some out
                self.request_rate = max(self.request_rate - increment, 0.1)
            logger.info((f"{{'period': {period}, "
                         f"'trip_utility': {trip_utility:.02f}, "
                         f"'wait_fraction': {wait_fraction:.02f}, "
                         f"'increment': {increment:.02f}, "
                         f"'old request rate': {old_request_rate:.02f}, "
                         f"'new request rate: {self.request_rate:.02f}}}"))

    def _driver_utility(self, busy_fraction):
        """
        Driver utility per unit time:
            driver_utility = p3 * p * f - Cost
        """
        driver_utility = (
            self.price * self.driver_price_factor * busy_fraction -
            self.driver_cost)
        return driver_utility

    def _trip_utility(self, wait_fraction, simple=True):
        """
        Trip utility per unit time:
        If simple:
            trip_utility = a - b * p - w * .W
        Else:
            trip_utility = a - b * p * (1 - W) - w * .W
        where W is the fraction of the trip spent waiting
        """
        trip_utility = (self.ride_utility - self.wait_cost * wait_fraction)
        if simple:
            trip_utility -= self.demand_slope * self.price
        else:
            trip_utility -= self.demand_slope * self.price * (1.0 -
                                                              wait_fraction)
        return trip_utility

    def _next_frame(self, ii, axes):
        """
        Function called from animator to generate frame ii of the animation.

        Ignore ii and handle the frame counter myself through self.frame_index
        to handle pauses. Not helping much yet though
        """
        i = self.frame_index
        if not self.pause_plot:
            self.frame_index += 1
        if self.period_index >= self.time_periods:
            logger.info(f"Period {self.period_index}: animation finished")
            self.animation.event_source.stop()
        plotstat_list = []
        if self._interpolation(i) == 0:
            # A "real" time point. Update the system
            # If the plotting is paused, don't compute the next period,
            # just redisplay what we have.
            if not self.pause_plot:
                self._next_period()
        axis_index = 0
        if self.draw in (Draw.ALL, Draw.MAP):
            self._draw_map(i, axes[axis_index])
            axis_index += 1
        if self.period_index % self.draw_update_period != 0:
            return
        if self.draw in (Draw.ALL, Draw.STATS, Draw.DRIVER, Draw.TRIP):
            if self.draw in (Draw.ALL, Draw.STATS, Draw.DRIVER):
                plotstat_list.append(PlotStat.DRIVER_AVAILABLE_FRACTION)
                plotstat_list.append(PlotStat.DRIVER_PICKUP_FRACTION)
                plotstat_list.append(PlotStat.DRIVER_PAID_FRACTION)
            if self.draw in (Draw.ALL, Draw.STATS, Draw.TRIP):
                plotstat_list.append(PlotStat.TRIP_WAIT_FRACTION)
                plotstat_list.append(PlotStat.TRIP_LENGTH_FRACTION)
            if self.equilibrate != Equilibration.NONE:
                plotstat_list = []
                plotstat_list.append(PlotStat.DRIVER_PAID_FRACTION)
                plotstat_list.append(PlotStat.TRIP_WAIT_FRACTION)
            if self.equilibrate in (Equilibration.FULL, Equilibration.SUPPLY):
                plotstat_list.append(PlotStat.DRIVER_COUNT_SCALED)
                plotstat_list.append(PlotStat.DRIVER_UTILITY)
            if self.equilibrate in (Equilibration.FULL, Equilibration.DEMAND):
                plotstat_list.append(PlotStat.REQUEST_RATE_SCALED)
                plotstat_list.append(PlotStat.TRIP_UTILITY)

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
                                          PlotStat.DRIVER_PAID_FRACTION,
                                          PlotStat.TRIP_WAIT_FRACTION,
                                          xlim=[0, 0.6],
                                          ylim=[0, 0.6])
            axis_index += 1
            self._draw_equilibration_plot(i,
                                          axes[axis_index],
                                          PlotStat.DRIVER_UTILITY,
                                          PlotStat.TRIP_UTILITY,
                                          xlim=[-0.6, 0.6],
                                          ylim=[-0.6, 0.6])
            axis_index += 1
        # TODO: set an axis that holds the actual button. THis makes all
        # axes[0] into a big button
        # button_plus = Button(axes[0], '+')
        # button_plus.on_clicked(self.on_click)

    def _draw_map(self, i, ax):
        """
        Draw the map, with drivers and trips
        """
        ax.clear()
        ax.set_title(
            (f"City size: {self.city.city_size}, "
             f"{len(self.drivers)} drivers, "
             f"{self.request_rate:.02f} requests / period, "
             f"{self.city.trip_distribution.name.lower()} trip distribution"))
        # Get the interpolation point
        distance_increment = (self._interpolation(i) /
                              self.interpolation_points)
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
                   color=self.color_palette[3],
                   alpha=0.7,
                   label="Ride request")
        ax.scatter(x_destination,
                   y_destination,
                   s=120,
                   marker='*',
                   color=self.color_palette[4],
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
        if self._interpolation(i) == 0:
            ax.clear()
            period = self.period_index
            lower_bound = max((period - CHART_X_RANGE), 0)
            x_range = list(range(lower_bound, period))
            title = ((
                f"City size: {self.city.city_size}, "
                f"{len(self.drivers)} drivers, "
                f"{self.request_rate:.02f} requests / period, "
                f"{self.city.trip_distribution.name.lower()} trip distribution"
                f"rolling {self.rolling_window}-period average."))
            if self.equilibrate != Equilibration.NONE:
                title += f" Equilibrating {self.equilibrate.value.lower()}, "
            if self.equilibrate in (Equilibration.SUPPLY, Equilibration.FULL):
                title += f" {len(self.drivers)} drivers"
            if self.equilibrate in (Equilibration.DEMAND, Equilibration.FULL):
                title += f" {self.request_rate:.02f} req/period"
            ax.set_title(title)
            if draw_line_chart:
                for index, fractional_property in enumerate(plotstat_list):
                    ax.plot(
                        x_range,
                        self.stats[fractional_property][lower_bound:period],
                        color=self.color_palette[index],
                        label=fractional_property.value,
                        lw=3,
                        alpha=0.7)
                if self.equilibrate == Equilibration.NONE:
                    ax.set_ylim(bottom=0, top=1)
                else:
                    ax.set_ylim(bottom=-1, top=1)
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
                    height.append(self.stats[fractional_property][i])
                    labels.append(fractional_property.value)
                    colors.append(
                        self.color_palette[fractional_property.value])
                caption = "\n".join(
                    (f"This simulation has {len(self.drivers)} drivers",
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
        if self._interpolation(i) == 0:
            x = self.stats[plotstat_x]
            y = self.stats[plotstat_y]
            period = int(i / self.interpolation_points)
            most_recent_equilibration = max(
                1,
                self.equilibration_interval *
                int(period / self.equilibration_interval))
            ax.clear()
            ax.set_title(f"Period {period}: {len(self.drivers)} drivers, "
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
            ax.plot(x[period],
                    y[period],
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

    def _interpolation(self, frame_index):
        """
        For plotting, we use interpolation points to give smoother
        motion in the map. With key events we can change the
        number of interpolation points in the middle of a simulation.
        This function tells us if the frame represents a new period
        or is an interpolation point.
        """
        interpolation_point = (frame_index - self.last_period_frame_index)
        if interpolation_point == self.interpolation_points:
            interpolation_point = 0
            self.last_period_frame_index = frame_index
        return interpolation_point


class RideHailSimulationResults():
    """
    Hold the results of a RideHailSimulation.
    Usually it just writes it out, but now we can do things like
    plot sequences of simulations
    """
    def __init__(self, simulation):
        self.sim = simulation
        self.results = {}
        self.config = {}
        self.config["city_size"] = self.sim.city.city_size
        self.config["driver_count"] = self.sim.config.driver_count
        self.config["trip_distribution"] = self.sim.city.trip_distribution.name
        self.config["min_trip_distance"] = self.sim.config.min_trip_distance
        self.config["time_periods"] = self.sim.config.time_periods
        self.config["request_rate"] = self.sim.config.request_rate
        self.config["equilibrate"] = self.sim.config.equilibrate
        self.config["rolling_window"] = self.sim.config.rolling_window
        self.config["results_window"] = self.sim.config.results_window
        self.config["available_drivers_moving"] = (
            self.sim.available_drivers_moving)
        self.results["config"] = self.config
        if self.sim.equilibrate and self.sim.equilibrate != Equilibration.NONE:
            self.equilibrate = {}
            self.equilibrate["price"] = self.sim.price
            self.equilibrate["equilibration_interval"] = (
                self.sim.equilibration_interval)
            if self.sim.equilibrate in (Equilibration.FULL,
                                        Equilibration.DEMAND):
                self.equilibrate["ride_utility"] = self.sim.ride_utility
                self.equilibrate["wait_cost"] = self.sim.wait_cost
            if self.sim.equilibrate in (Equilibration.FULL,
                                        Equilibration.SUPPLY):
                self.equilibrate["driver_cost"] = self.sim.driver_cost
            self.results["equilibrate"] = self.equilibrate
        # ----------------------------------------------------------------------
        # Collect final state, averaged over the final
        # sim.config.results_window periods of the simulation
        lower_bound = max(
            (self.sim.time_periods - self.sim.config.results_window), 0)
        result_periods = (len(self.sim.stats[History.REQUEST_RATE]) -
                          lower_bound)
        # N and R
        self.output = {}
        self.output["mean_driver_count"] = (
            sum(self.sim.stats[History.DRIVER_COUNT][lower_bound:]) /
            result_periods)
        self.output["mean_request_rate"] = (
            sum(self.sim.stats[History.REQUEST_RATE][lower_bound:]) /
            result_periods)
        # driver stats
        self.output["total_driver_time"] = (
            self.sim.stats[History.CUMULATIVE_DRIVER_TIME][-1] -
            self.sim.stats[History.CUMULATIVE_DRIVER_TIME][lower_bound])
        self.output["total_trip_count"] = (
            (self.sim.stats[History.CUMULATIVE_TRIP_COUNT][-1] -
             self.sim.stats[History.CUMULATIVE_TRIP_COUNT][lower_bound]))
        self.output["driver_fraction_available"] = (
            (self.sim.stats[History.CUMULATIVE_DRIVER_P1_TIME][-1] -
             self.sim.stats[History.CUMULATIVE_DRIVER_P1_TIME][lower_bound]) /
            self.output["total_driver_time"])
        self.output["driver_fraction_picking_up"] = (
            (self.sim.stats[History.CUMULATIVE_DRIVER_P2_TIME][-1] -
             self.sim.stats[History.CUMULATIVE_DRIVER_P2_TIME][lower_bound]) /
            self.output["total_driver_time"])
        self.output["driver_fraction_with_rider"] = (
            (self.sim.stats[History.CUMULATIVE_DRIVER_P3_TIME][-1] -
             self.sim.stats[History.CUMULATIVE_DRIVER_P3_TIME][lower_bound]) /
            self.output["total_driver_time"])
        # trip stats
        self.output["mean_trip_wait_time"] = (
            (self.sim.stats[History.CUMULATIVE_WAIT_TIME][-1] -
             self.sim.stats[History.CUMULATIVE_WAIT_TIME][lower_bound]) /
            self.output["total_trip_count"])
        self.output["mean_trip_distance"] = (
            (self.sim.stats[History.CUMULATIVE_TRIP_DISTANCE][-1] -
             self.sim.stats[History.CUMULATIVE_TRIP_DISTANCE][lower_bound]) /
            self.output["total_trip_count"])
        # TODO: this is probably incorrect
        self.output["trip_fraction_wait_time"] = (
            self.output["mean_trip_wait_time"] /
            (self.output["mean_trip_wait_time"] +
             self.output["mean_trip_distance"]))
        self.results["output"] = self.output
        # rl_over_nb = (
        # self.results["mean_trip_distance"] * self.request_rate /
        # (self.sim.driver_count * driver_fraction_with_rider))

    def write_json(self, jsonl_filename):
        """
        Write the results of the simulation as JSON lines
        """
        with open(f"{jsonl_filename}", 'a+') as f:
            f.write(json.dumps(self.results))
            f.write("\n")
