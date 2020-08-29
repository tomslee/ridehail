#!/usr/bin/python3
"""
A simulation
"""
import logging
import os
import random
import json
from datetime import datetime
import numpy as np
from ridehail.atom import (City, Driver, Trip, DriverPhase, TripPhase,
                           Equilibration, History)
from ridehail.animation import PlotStat

logger = logging.getLogger(__name__)

FIRST_REQUEST_OFFSET = 0
EQUILIBRIUM_BLUR = 0.02
GARBAGE_COLLECTION_INTERVAL = 10
# Log the period every PRINT_INTERVAL periods
PRINT_INTERVAL = 10


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
        self.period_index = 0
        self.rolling_window = config.rolling_window
        self.output = config.output
        self.trips = []
        self.stats = {}
        for total in list(History):
            self.stats[total] = np.empty(self.time_periods)
        for stat in list(PlotStat):
            self.stats[stat] = np.empty(self.time_periods)
        # If we change a simulation parameter interactively, the new value
        # is stored in self.target_state, and the new values of the
        # actual parameters are updated at the beginning of the next period.
        # This set is expanding as the program gets more complex.
        self.target_state = {}
        self.target_state["city_size"] = self.city.city_size
        self.target_state["driver_count"] = len(self.drivers)
        self.target_state["request_rate"] = self.request_rate
        self.target_state["trip_distribution"] = self.city.trip_distribution

    # (todays_date-datetime.timedelta(10), time_periods=10, freq='D')

    def simulate(self):
        """
        Plot the trend of cumulative cases, observed at
        earlier days, evolving over time.
        """
        for period in range(self.time_periods):
            self.next_period()
        results = RideHailSimulationResults(self)
        return results

    def next_period(self):
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
        # resize the city
        if self.city.city_size != self.target_state["city_size"]:
            self.city.city_size = self.target_state["city_size"]
            # Reposition the drivers within the city boundaries
            for driver in self.drivers:
                for i in [0, 1]:
                    driver.location[
                        i] = driver.location[i] % self.city.city_size
            # Likewise for trips: reposition origins and destinations
            # within the city boundaries
            for trip in self.trips:
                for i in [0, 1]:
                    trip.origin[i] = trip.origin[i] % self.city.city_size
                    trip.destination[
                        i] = trip.destination[i] % self.city.city_size
        self.city.trip_distribution = self.target_state["trip_distribution"]
        self.request_rate = self.target_state["request_rate"]
        # add or remove drivers
        old_driver_count = len(self.drivers)
        driver_diff = self.target_state["driver_count"] - old_driver_count
        if driver_diff > 0:
            for d in range(driver_diff):
                self.drivers.append(
                    Driver(old_driver_count + d, self.city,
                           self.available_drivers_moving))
        elif driver_diff < 0:
            removed_drivers = self._remove_drivers(-driver_diff)
            logger.info(f"Removed {removed_drivers} drivers.")
        for array_name, array in self.stats.items():
            # create a place to hold stats from this period
            if period >= 1:
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

    def _remove_drivers(self, number_to_remove):
        """
        Remove 'number_to_remove' drivers from self.drivers.
        Returns the number of drivers removed
        """
        drivers_removed = 0
        for i, driver in enumerate(self.drivers):
            if driver.phase == DriverPhase.AVAILABLE:
                del self.drivers[i]
                drivers_removed += 1
                if drivers_removed == number_to_remove:
                    break
        return drivers_removed

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
                drivers_removed = self._remove_drivers(-driver_increment)
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
