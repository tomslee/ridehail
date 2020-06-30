#!/usr/bin/python3
"""
A simulation
"""
import logging
import os
import matplotlib.pyplot as plt
import random
from enum import Enum
from matplotlib.ticker import MultipleLocator
from matplotlib.animation import FuncAnimation
# from matplotlib.widgets import Slider
import seaborn as sns
from atoms import City, Driver, Trip, DriverPhase, TripPhase, Direction
from plot import Plot, PlotStat, Draw

logger = logging.getLogger(__name__)

FRAME_INTERVAL = 50
FIRST_REQUEST_OFFSET = 0
EQUILIBRIUM_BLUR = 0.01
DEFAULT_RESULT_WINDOW = 100
CHART_X_RANGE = 200


class History(Enum):
    CUMULATIVE_DRIVER_TIME = "Cumulative driver time"
    CUMULATIVE_WAIT_TIME = "Cumulative wait time"
    CUMULATIVE_TRIP_COUNT = "Cumulative completed trips"
    CUMULATIVE_TRIP_DISTANCE = "Cumulative distance"
    CUMULATIVE_REQUESTS = "Cumulative requests"
    DRIVER_COUNT = "Driver count"
    REQUEST_RATE = "Request rate"


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
        if self.equilibrate:
            self.driver_cost = config.driver_cost
            self.wait_cost = config.wait_cost
            self.ride_utility = config.ride_utility
            self.price = config.price
            self.equilibration_interval = config.equilibration_interval
        self.request_rate = config.request_rate
        self.city = City(config.city_size)
        self.time_periods = config.time_periods
        self.draw_update_period = config.draw_update_period
        self.interpolation_points = config.interpolate
        self.frame_count = config.time_periods * self.interpolation_points
        self.rolling_window = config.rolling_window
        self.output = config.output
        self.draw = config.draw
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
            if driver.trip_index is not None:
                # If the driver arrives at a pickup or dropoff location,
                # handle the phase changes
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
        # If there are drivers free, assign one to each request
        self._assign_drivers()
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
            logger.debug(
                (f"Request: trip {trip.origin} -> {trip.destination}"))
            # the trip has a random origin and destination
            # and is ready to make a request.
            # This sets the trip to TripPhase.UNNASSIGNED
            # as no driver is assigned here
            trip.phase_change()
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
            for trip in unassigned_trips:
                # Try to assign a driver to this trop
                assigned_driver = self._assign_driver(trip)
                # If a driver is assigned (not None), update the trip phase
                if assigned_driver:
                    assigned_driver.phase_change(trip=trip)
                    trip.phase_change()
                    if assigned_driver.location == trip.origin:
                        # Do the pick up now
                        assigned_driver.phase_change(trip=trip)
                        trip.phase_change()
                else:
                    logger.debug(f"No driver assigned for trip {trip.index}")

    def _assign_driver(self, trip):
        """
        Find the nearest driver to a ridehail call at x, y
        Set that driver's phase to PICKING_UP
        Returns an assigned driver or None
        """
        logger.debug("Assigning a driver to a request...")
        min_distance = self.city.city_size * 100  # Very big
        assigned_driver = None
        available_drivers = [
            driver for driver in self.drivers
            if driver.phase == DriverPhase.AVAILABLE
        ]
        if available_drivers:
            # randomize the driver list to prevent early drivers
            # having an advantage in the case of equality
            random.shuffle(available_drivers)
            for driver in available_drivers:
                distance = abs(driver.location[0] -
                               trip.origin[0]) + abs(driver.location[1] -
                                                     trip.origin[1])
                if distance < min_distance:
                    min_distance = distance
                    assigned_driver = driver
                    logger.debug((f"Driver at {assigned_driver.location} "
                                  f"assigned to pickup at {trip.origin}"))
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
            if self.equilibrate:
                self.stats[PlotStat.DRIVER_UTILITY][-1] = (
                    self._utility_supply(
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
            if self.equilibrate:
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
            damping_factor = 0.3
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
                    logger.debug("No drivers without ride assignments. "
                                 "Cannot remove any drivers")
            self.driver_count = len(self.drivers)
            logger.debug((f"Supply - period: {period}, "
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
            logger.debug((f"Demand - period: {period}, "
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
        logger.debug((f"End: {{'drivers': {self.sim.driver_count:02}, "
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


class Equilibration(Enum):
    SUPPLY = 0
    DEMAND = 1
    FULL = 2
    NONE = 3
