#!/usr/bin/python3
"""
A simulation
"""
import logging
import random
import json
from datetime import datetime
import numpy as np
from ridehail import atom

logger = logging.getLogger(__name__)

FIRST_REQUEST_OFFSET = 0
EQUILIBRIUM_BLUR = 0.02
GARBAGE_COLLECTION_INTERVAL = 200
# Log the block every PRINT_INTERVAL blocks
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
        self.city = atom.City(config.city_size,
                              trip_distribution=config.trip_distribution)
        self.available_drivers_moving = config.available_drivers_moving
        self.drivers = [
            atom.Driver(i, self.city, self.available_drivers_moving)
            for i in range(config.driver_count)
        ]
        self.base_demand = config.base_demand
        self.equilibrate = config.equilibrate
        if self.equilibrate != atom.Equilibration.NONE:
            self.price = config.price
            self.reserved_wage = config.reserved_wage
            self.driver_price_factor = config.driver_price_factor
            self.demand_elasticity = config.demand_elasticity
            self.equilibration_interval = config.equilibration_interval
        self.request_rate = self._demand()
        self.time_blocks = config.time_blocks[0]
        self.block_index = 0
        self.trailing_window = config.trailing_window
        self.output = config.output
        self.trips = []
        self.stats = {}
        for history_item in list(atom.History):
            self.stats[history_item] = np.zeros(self.time_blocks + 1)
        # If we change a simulation parameter interactively, the new value
        # is stored in self.target_state, and the new values of the
        # actual parameters are updated at the beginning of the next block.
        # This set is expanding as the program gets more complex.
        self.target_state = {}
        self.target_state["city_size"] = self.city.city_size
        self.target_state["driver_count"] = len(self.drivers)
        self.target_state["base_demand"] = self.base_demand
        self.target_state["trip_distribution"] = self.city.trip_distribution
        if self.equilibrate and self.equilibrate != atom.Equilibration.NONE:
            self.target_state["reserved_wage"] = self.reserved_wage
            self.target_state["price"] = self.price

    # (todays_date-datetime.timedelta(10), time_blocks=10, freq='D')

    def simulate(self):
        """
        Plot the trend of cumulative cases, observed at
        earlier days, evolving over time.
        """
        for block in range(self.time_blocks):
            self.next_block()
        results = RideHailSimulationResults(self)
        return results

    def next_block(self):
        """
        Call all those functions needed to simulate the next block
        """
        block = self.block_index
        if block % PRINT_INTERVAL == 0:
            logger.debug(
                f"-------"
                f"Block {block} at"
                f" {datetime.now().strftime('%Y-%m-%d-%H:%M:%S.%f')[:-4]}"
                f"-----------")
        self._init_block(block)
        for driver in self.drivers:
            # Move drivers
            driver.update_location()
            driver.update_direction()
            if driver.trip_index is not None:
                # If the driver arrives at a pickup or dropoff location,
                # handle the phase changes
                trip = self.trips[driver.trip_index]
                if (driver.phase == atom.DriverPhase.PICKING_UP
                        and driver.location == driver.pickup):
                    # the driver has arrived at the pickup spot and picks up
                    # the rider
                    driver.phase_change()
                    trip.phase_change(to_phase=atom.TripPhase.RIDING)
                elif (driver.phase == atom.DriverPhase.WITH_RIDER
                      and driver.location == driver.dropoff):
                    # The driver has arrived at the dropoff and the trip ends.
                    # Update driver and trip to reflect the completion
                    driver.phase_change()
                    trip.phase_change(to_phase=atom.TripPhase.COMPLETED)
        # Using the stats from the previous block,
        # equilibrate the supply and/or demand of rides
        if self.equilibrate is not None:
            if (self.equilibrate in (atom.Equilibration.SUPPLY,
                                     atom.Equilibration.PRICE)):
                self._equilibrate_supply(block)
        # Customers make trip requests
        self._request_trips(block)
        # If there are drivers free, assign one to each request
        self._assign_drivers()
        # Some requests get cancelled if they have been open too long
        self._cancel_requests()
        # Update stats for everything that has happened in this block
        self._update_history_arrays(block)
        # Some arrays hold information for each trip:
        # compress these as needed to avoid a growing set
        # of completed or cancelled (dead) trips
        self._collect_garbage(block)
        self.block_index += 1
        return self.block_index

    def _request_trips(self, block):
        """
        Periodically initiate a request from an inactive rider
        For requests not assigned a driver, repeat the request.

        """
        # TODO This is the only place a atom.History stat is updated outside
        # _update_history_arrays. It would be good to fix this somehow.
        self.stats[
            atom.History.CUMULATIVE_REQUESTS][block] += self.request_rate
        # Given a request rate r, compute the number of requests this
        # block.
        if block < FIRST_REQUEST_OFFSET:
            logging.info(f"block {block} < {FIRST_REQUEST_OFFSET}")
            return
        requests_this_block = (
            int(self.stats[atom.History.CUMULATIVE_REQUESTS][block]) -
            int(self.stats[atom.History.CUMULATIVE_REQUESTS][block - 1]))
        for trip in range(requests_this_block):
            trip = atom.Trip(len(self.trips),
                             self.city,
                             min_trip_distance=self.config.min_trip_distance)
            self.trips.append(trip)
            logger.debug(
                (f"Request: trip {trip.origin} -> {trip.destination}"))
            # the trip has a random origin and destination
            # and is ready to make a request.
            # This sets the trip to atom.TripPhase.UNASSIGNED
            # as no driver is assigned here
            trip.phase_change(atom.TripPhase.UNASSIGNED)
        if requests_this_block > 0:
            logger.debug((f"Block {block}: "
                          f"rate {self.request_rate:.02f}: "
                          f"{requests_this_block} request(s)."))

    def _assign_drivers(self):
        """
        All trips without an assigned driver make a request
        Randomize the order just in case there is some problem
        """
        unassigned_trips = [
            trip for trip in self.trips
            if trip.phase == atom.TripPhase.UNASSIGNED
        ]
        if unassigned_trips:
            random.shuffle(unassigned_trips)
            logger.debug(f"There are {len(unassigned_trips)} unassigned trips")
            available_drivers = [
                driver for driver in self.drivers
                if driver.phase == atom.DriverPhase.AVAILABLE
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

                    trip.phase_change(to_phase=atom.TripPhase.WAITING)
                    if assigned_driver.location == trip.origin:
                        # Do the pick up now
                        assigned_driver.phase_change(trip=trip)
                        trip.phase_change(to_phase=atom.TripPhase.RIDING)
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

    def _cancel_requests(self):
        """
        If a request has been waiting too long, cancel it.

        For now "too long" = city length
        """
        unassigned_trips = [
            trip for trip in self.trips
            if trip.phase == atom.TripPhase.UNASSIGNED
        ]
        for trip in unassigned_trips:
            if trip.phase_time[
                    atom.TripPhase.UNASSIGNED] >= self.city.city_size:
                trip.phase_change(to_phase=atom.TripPhase.CANCELLED)
                logger.debug(
                    (f"Trip {trip.index} cancelled after "
                     f"{trip.phase_time[atom.TripPhase.UNASSIGNED]} blocks."))

    def _init_block(self, block):
        """
        - If needed, update simulations settings from user input
          (self.target_state values).
        - Initialize values for the "block" item of each array.
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
        # Update the trip distribution
        self.city.trip_distribution = self.target_state["trip_distribution"]
        # Update the base demand
        self.base_demand = self.target_state["base_demand"]
        if self.equilibrate == atom.Equilibration.PRICE:
            # Update the price
            self.price = self.target_state["price"]
            # Update the request rate to reflect the price
            self.request_rate = self._demand()
        # add or remove drivers for manual changes only
        if self.equilibrate == atom.Equilibration.NONE:
            old_driver_count = len(self.drivers)
            driver_diff = self.target_state["driver_count"] - old_driver_count
            if driver_diff > 0:
                for d in range(driver_diff):
                    self.drivers.append(
                        atom.Driver(old_driver_count + d, self.city,
                                    self.available_drivers_moving))
            elif driver_diff < 0:
                removed_drivers = self._remove_drivers(-driver_diff)
                logger.info(
                    f"Period start: removed {removed_drivers} drivers.")
        else:
            if self.reserved_wage != self.target_state["reserved_wage"]:
                self.reserved_wage = self.target_state["reserved_wage"]
                logger.info(f"New reserved_wage = {self.reserved_wage:.02f}")
        for array_name, array in self.stats.items():
            if 1 <= block < self.time_blocks:
                # Copy the previous value into the current value
                # as the default action
                array[block] = array[block - 1]

    def _update_history_arrays(self, block):
        """
        Called after each block to update history statistics
        """
        # Update base stats
        # driver count and request rate are filled in anew each block
        self.stats[atom.History.DRIVER_COUNT][block] = len(self.drivers)
        self.stats[atom.History.REQUEST_RATE][block] = self.request_rate
        # other stats are cumulative, so that differences can be taken
        if len(self.drivers) > 0:
            for driver in self.drivers:
                self.stats[atom.History.CUMULATIVE_DRIVER_TIME][block] += 1
                if driver.phase == atom.DriverPhase.AVAILABLE:
                    self.stats[
                        atom.History.CUMULATIVE_DRIVER_P1_TIME][block] += 1
                elif driver.phase == atom.DriverPhase.PICKING_UP:
                    self.stats[
                        atom.History.CUMULATIVE_DRIVER_P2_TIME][block] += 1
                elif driver.phase == atom.DriverPhase.WITH_RIDER:
                    self.stats[
                        atom.History.CUMULATIVE_DRIVER_P3_TIME][block] += 1
        if self.trips:
            for trip in self.trips:
                phase = trip.phase
                trip.phase_time[phase] += 1
                if phase == atom.TripPhase.UNASSIGNED:
                    self.stats[atom.History.
                               CUMULATIVE_TRIP_UNASSIGNED_TIME][block] += 1
                    # Bad name: CUMULATIVE_WAIT_TIME = WAITING + UNASSIGNED
                    self.stats[atom.History.CUMULATIVE_WAIT_TIME][block] += 1
                elif phase == atom.TripPhase.WAITING:
                    self.stats[
                        atom.History.CUMULATIVE_TRIP_AWAITING_TIME][block] += 1
                    # Bad name: CUMULATIVE_WAIT_TIME = WAITING + UNASSIGNED
                    self.stats[atom.History.CUMULATIVE_WAIT_TIME][block] += 1
                elif phase == atom.TripPhase.RIDING:
                    self.stats[
                        atom.History.CUMULATIVE_TRIP_RIDING_TIME][block] += 1
                    self.stats[
                        atom.History.CUMULATIVE_TRIP_DISTANCE][block] += 1
                elif phase == atom.TripPhase.COMPLETED:
                    self.stats[atom.History.CUMULATIVE_TRIP_COUNT][block] += 1
                    self.stats[
                        atom.History.CUMULATIVE_COMPLETED_TRIPS][block] += 1
                    trip.phase = atom.TripPhase.INACTIVE
                elif phase == atom.TripPhase.CANCELLED:
                    # Cancelled trips are still counted as trips
                    self.stats[atom.History.CUMULATIVE_TRIP_COUNT][block] += 1
                    trip.phase = atom.TripPhase.INACTIVE
                elif phase == atom.TripPhase.INACTIVE:
                    # nothing done with INACTIVE trips
                    pass
        json_string = (("{" f'"block": {block}'))
        for array_name, array in self.stats.items():
            json_string += (f', "{array_name}":' f' {array[block]}')
        json_string += ("}")
        logger.debug(f"Simulation: {json_string}")

    def _collect_garbage(self, block):
        """
        Garbage collect the list of trips to get rid of the completed and
        cancelled ones.

        For each trip, find the driver with that trip_index
        and reset the driver.trip_index and trip.index to
        "i".
        """
        if block % GARBAGE_COLLECTION_INTERVAL == 0:
            self.trips = [
                trip for trip in self.trips if trip.phase not in
                [atom.TripPhase.COMPLETED, atom.TripPhase.CANCELLED]
            ]
            for i, trip in enumerate(self.trips):
                trip_index = trip.index
                for driver in self.drivers:
                    if driver.trip_index == trip_index:
                        # Found the driver that matches this trip
                        driver.trip_index = i
                        break
                trip.index = i

    def _remove_drivers(self, number_to_remove):
        """
        Remove 'number_to_remove' drivers from self.drivers.
        Returns the number of drivers removed
        """
        drivers_removed = 0
        for i, driver in enumerate(self.drivers):
            if driver.phase == atom.DriverPhase.AVAILABLE:
                del self.drivers[i]
                drivers_removed += 1
                if drivers_removed == number_to_remove:
                    break
        return drivers_removed

    def _equilibrate_supply(self, block):
        """
        Change the driver count and request rate to move the system
        towards equilibrium.
        """
        if ((block % self.equilibration_interval == 0)
                and block >= self.equilibration_interval):
            # only equilibrate at certain times
            lower_bound = max((block - self.equilibration_interval), 0)
            # equilibration_blocks = (blocks - lower_bound)
            total_driver_time = (
                self.stats[atom.History.CUMULATIVE_DRIVER_TIME][block] -
                self.stats[atom.History.CUMULATIVE_DRIVER_TIME][lower_bound])
            p3_fraction = ((
                self.stats[atom.History.CUMULATIVE_DRIVER_P3_TIME][block] -
                self.stats[atom.History.CUMULATIVE_DRIVER_P3_TIME][lower_bound]
            ) / total_driver_time)
            driver_utility = self.driver_utility(p3_fraction)
            # logger.info((f"p3={p3_fraction}", f", U={driver_utility}"))
            old_driver_count = len(self.drivers)
            damping_factor = 0.4
            driver_increment = int(damping_factor * old_driver_count *
                                   driver_utility)
            if driver_increment > 0:
                driver_increment = min(driver_increment,
                                       int(0.1 * len(self.drivers)))
                self.drivers += [
                    atom.Driver(i, self.city, self.available_drivers_moving)
                    for i in range(old_driver_count, old_driver_count +
                                   driver_increment)
                ]
            elif driver_increment < 0:
                driver_increment = max(driver_increment,
                                       -0.1 * len(self.drivers))
                self._remove_drivers(-driver_increment)
            logger.debug((f"{{'block': {block}, "
                          f"'driver_utility': {driver_utility:.02f}, "
                          f"'busy': {p3_fraction:.02f}, "
                          f"'increment': {driver_increment}, "
                          f"'old driver count': {old_driver_count}, "
                          f"'new driver count': {len(self.drivers)}}}"))

    def driver_utility(self, busy_fraction):
        """
        Driver utility per unit time:
            driver_utility = p3 * p * f - reserved wage
        """
        return (self.price * self.driver_price_factor * busy_fraction -
                self.reserved_wage)

    def _demand(self):
        """
        Return demand (request_rate):
           request_rate = base_demand * price ^ (-elasticity)
        """
        if self.equilibrate == atom.Equilibration.NONE:
            demand = self.base_demand
        else:
            demand = (self.base_demand * self.price**(-self.demand_elasticity))
        return demand


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
        self.config["driver_count"] = len(self.sim.drivers)
        self.config["trip_distribution"] = self.sim.city.trip_distribution.name
        self.config["min_trip_distance"] = self.sim.config.min_trip_distance
        self.config["time_blocks"] = self.sim.time_blocks
        self.config["request_rate"] = self.sim.request_rate
        self.config["equilibrate"] = self.sim.config.equilibrate
        self.config["trailing_window"] = self.sim.config.trailing_window
        self.config["results_window"] = self.sim.config.results_window
        self.config["available_drivers_moving"] = (
            self.sim.available_drivers_moving)
        self.results["config"] = self.config
        if (self.sim.equilibrate
                and self.sim.equilibrate != atom.Equilibration.NONE):
            self.equilibrate = {}
            self.equilibrate["price"] = self.sim.price
            self.equilibrate["equilibration_interval"] = (
                self.sim.equilibration_interval)
            if self.sim.equilibrate == atom.Equilibration.PRICE:
                self.equilibrate["base_demand"] = self.base_demand
            if self.sim.equilibrate in (atom.Equilibration.PRICE,
                                        atom.Equilibration.SUPPLY):
                self.equilibrate["reserved_wage"] = self.sim.reserved_wage
            self.results["equilibrate"] = self.equilibrate
        # ----------------------------------------------------------------------
        # Collect final state, averaged over the final
        # sim.config.results_window blocks of the simulation
        blocks = self.sim.time_blocks - 1
        lower_bound = max(
            (self.sim.time_blocks - self.sim.config.results_window), 0)
        result_blocks = (blocks - lower_bound)
        # N and R
        self.output = {}
        self.output["mean_driver_count"] = (sum(
            self.sim.stats[atom.History.DRIVER_COUNT][lower_bound:blocks]) /
                                            result_blocks)
        self.output["mean_request_rate"] = (sum(
            self.sim.stats[atom.History.REQUEST_RATE][lower_bound:blocks]) /
                                            result_blocks)
        # driver stats
        self.output["total_driver_time"] = (
            self.sim.stats[atom.History.CUMULATIVE_DRIVER_TIME][blocks] -
            self.sim.stats[atom.History.CUMULATIVE_DRIVER_TIME][lower_bound])
        self.output["total_trip_count"] = (
            (self.sim.stats[atom.History.CUMULATIVE_TRIP_COUNT][blocks] -
             self.sim.stats[atom.History.CUMULATIVE_TRIP_COUNT][lower_bound]))
        self.output["driver_fraction_available"] = ((
            self.sim.stats[atom.History.CUMULATIVE_DRIVER_P1_TIME][blocks] -
            self.sim.stats[atom.History.CUMULATIVE_DRIVER_P1_TIME][lower_bound]
        ) / self.output["total_driver_time"])
        self.output["driver_fraction_picking_up"] = ((
            self.sim.stats[atom.History.CUMULATIVE_DRIVER_P2_TIME][blocks] -
            self.sim.stats[atom.History.CUMULATIVE_DRIVER_P2_TIME][lower_bound]
        ) / self.output["total_driver_time"])
        self.output["driver_fraction_with_rider"] = ((
            self.sim.stats[atom.History.CUMULATIVE_DRIVER_P3_TIME][blocks] -
            self.sim.stats[atom.History.CUMULATIVE_DRIVER_P3_TIME][lower_bound]
        ) / self.output["total_driver_time"])
        # trip stats
        self.output["mean_trip_wait_time"] = (
            (self.sim.stats[atom.History.CUMULATIVE_WAIT_TIME][blocks] -
             self.sim.stats[atom.History.CUMULATIVE_WAIT_TIME][lower_bound]) /
            self.output["total_trip_count"])
        self.output["mean_trip_distance"] = ((
            self.sim.stats[atom.History.CUMULATIVE_TRIP_DISTANCE][blocks] -
            self.sim.stats[atom.History.CUMULATIVE_TRIP_DISTANCE][lower_bound])
                                             / self.output["total_trip_count"])
        # TODO: this is probably incorrect
        self.output["trip_fraction_wait_time"] = (
            self.output["mean_trip_wait_time"] /
            (self.output["mean_trip_wait_time"] +
             self.output["mean_trip_distance"]))
        self.results["output"] = self.output
        # rl_over_nb = (
        # self.results["mean_trip_distance"] * self.request_rate /

    def write_json(self, jsonl_filename):
        """
        Write the results of the simulation as JSON lines
        """
        with open(f"{jsonl_filename}", 'a+') as f:
            f.write(json.dumps(self.results))
            f.write("\n")
