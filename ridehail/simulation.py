#!/usr/bin/python3
"""
A simulation
"""
import logging
import random
import json
import numpy as np
from datetime import datetime
from ridehail import atom

GARBAGE_COLLECTION_INTERVAL = 200
# Log the block every LOG_INTERVAL blocks
LOG_INTERVAL = 10


class RideHailSimulation():
    """
    Simulate a ride-hail environment, with vehicles and trips
    """
    def __init__(self, config):
        """
        Initialize the class variables and call what needs to be called.
        The dataframe "data" has a row for each case.
        It must have the following columns:
        - "date_report": the date a case is reported
        """
        self.target_state = {}
        self.config = config
        self.city = atom.City(config.city_size,
                              trip_distribution=config.trip_distribution)
        self.target_state["city_size"] = self.city.city_size
        self.target_state["trip_distribution"] = self.city.trip_distribution
        self.idle_vehicles_moving = config.idle_vehicles_moving
        self.vehicles = [
            atom.Vehicle(i, self.city, self.idle_vehicles_moving)
            for i in range(config.vehicle_count)
        ]
        self.target_state["vehicle_count"] = len(self.vehicles)
        self.base_demand = config.base_demand
        self.target_state["base_demand"] = self.base_demand
        self.equilibrate = config.equilibrate
        self.target_state["equilibrate"] = self.equilibrate
        # if self.equilibrate != atom.Equilibration.NONE:
        if hasattr(config, "price"):
            self.price = config.price
            self.target_state["price"] = self.price
        if hasattr(config, "platform_commission"):
            self.platform_commission = config.platform_commission
            self.target_state["platform_commission"] = self.platform_commission
        if hasattr(config, "reserved_wage"):
            self.reserved_wage = config.reserved_wage
            self.target_state["reserved_wage"] = self.reserved_wage
        if hasattr(config, "demand_elasticity"):
            self.demand_elasticity = config.demand_elasticity
        if hasattr(config, "equilibration_interval"):
            self.equilibration_interval = config.equilibration_interval
        if hasattr(config, "impulse_list"):
            self.impulse_list = config.impulse_list
        self.request_rate = self._demand()
        self.time_blocks = config.time_blocks
        self.block_index = 0
        self.trips = []
        self.stats = {}
        for history_item in list(atom.History):
            self.stats[history_item] = np.zeros(self.time_blocks + 2)
        # If we change a simulation parameter interactively, the new value
        # is stored in self.target_state, and the new values of the
        # actual parameters are updated at the beginning of the next block.
        # This set is expanding as the program gets more complex.

    # (todays_date-datetime.timedelta(10), time_blocks=10, freq='D')

    def simulate(self):
        """
        Plot the trend of cumulative cases, observed at
        earlier days, evolving over time.
        """
        # open a results file
        self.results = RideHailSimulationResults(self)
        self.results.write_config()
        for block in range(self.time_blocks):
            self.next_block()
        self.results.write_end_state()
        return self.results

    def next_block(self):
        """
        Call all those functions needed to simulate the next block
        """
        block = self.block_index
        if block % LOG_INTERVAL == 0:
            logging.debug(
                f"-------"
                f" Block {block} at"
                f" {datetime.now().strftime('%Y-%m-%d-%H:%M:%S.%f')[:-4]}"
                f" -------")
        self._init_block(block)
        for vehicle in self.vehicles:
            # Move vehicles
            vehicle.update_location()
        for vehicle in self.vehicles:
            # Change direction
            vehicle.update_direction()
        for vehicle in self.vehicles:
            # Handle phase changes
            if vehicle.trip_index is not None:
                # If the vehicle arrives at a pickup or dropoff location,
                # handle the phase changes
                trip = self.trips[vehicle.trip_index]
                if (vehicle.phase == atom.VehiclePhase.DISPATCHED
                        and vehicle.location == vehicle.pickup):
                    # the vehicle has arrived at the pickup spot and picks up
                    # the rider
                    vehicle.phase_change(to_phase=atom.VehiclePhase.WITH_RIDER)
                    trip.phase_change(to_phase=atom.TripPhase.RIDING)
                elif (vehicle.phase == atom.VehiclePhase.WITH_RIDER
                      and vehicle.location == vehicle.dropoff):
                    # The vehicle has arrived at the dropoff and the trip ends.
                    # Update vehicle and trip to reflect the completion
                    vehicle.phase_change()
                    trip.phase_change(to_phase=atom.TripPhase.COMPLETED)
        # Using the stats from the previous block,
        # equilibrate the supply and/or demand of rides
        if self.equilibrate is not None:
            if (self.equilibrate
                    in (atom.Equilibration.SUPPLY, atom.Equilibration.PRICE)):
                self._equilibrate_supply(block)
        # Customers make trip requests
        self._request_trips(block)
        # If there are vehicles free, assign one to each request
        self._assign_vehicles()
        # Some requests get cancelled if they have been open too long
        self._cancel_requests(max_wait_time=None)
        # Update stats for everything that has happened in this block
        self._update_history_arrays(block)
        # Some arrays hold information for each trip:
        # compress these as needed to avoid a growing set
        # of completed or cancelled (dead) trips
        self._collect_garbage(block)
        self.results.write_state(block)
        self.block_index += 1
        return self.block_index

    def _request_trips(self, block):
        """
        Periodically initiate a request from an inactive rider
        For requests not assigned a vehicle, repeat the request.

        """
        requests_this_block = int(
            self.stats[atom.History.REQUEST_CAPITAL][block - 1])
        for trip in range(requests_this_block):
            trip = atom.Trip(len(self.trips),
                             self.city,
                             min_trip_distance=self.config.min_trip_distance,
                             max_trip_distance=self.config.max_trip_distance)
            self.trips.append(trip)
            logging.debug(
                (f"Request: trip {trip.origin} -> {trip.destination}"))
            # the trip has a random origin and destination
            # and is ready to make a request.
            # This sets the trip to atom.TripPhase.UNASSIGNED
            # as no vehicle is assigned here
            trip.phase_change(atom.TripPhase.UNASSIGNED)
        if requests_this_block > 0:
            logging.debug((f"Block {block}: "
                           f"rate {self.request_rate:.02f}: "
                           f"{requests_this_block} request(s)."))

    def _assign_vehicles(self):
        """
        All trips without an assigned vehicle make a request
        Randomize the order just in case there is some problem
        """
        unassigned_trips = [
            trip for trip in self.trips
            if trip.phase == atom.TripPhase.UNASSIGNED
        ]
        if unassigned_trips:
            random.shuffle(unassigned_trips)
            logging.debug(
                f"There are {len(unassigned_trips)} unassigned trips")
            idle_vehicles = [
                vehicle for vehicle in self.vehicles
                if vehicle.phase == atom.VehiclePhase.IDLE
            ]
            # randomize the vehicle list to prevent early vehicles
            # having an advantage in the case of equality
            random.shuffle(idle_vehicles)
            for trip in unassigned_trips:
                # Try to assign a vehicle to this trop
                assigned_vehicle = self._assign_vehicle(trip, idle_vehicles)
                # If a vehicle is assigned (not None), update the trip phase
                if assigned_vehicle:
                    idle_vehicles.remove(assigned_vehicle)
                    assigned_vehicle.phase_change(trip=trip)

                    trip.phase_change(to_phase=atom.TripPhase.WAITING)
                    if assigned_vehicle.location == trip.origin:
                        # Do the pick up now
                        assigned_vehicle.phase_change(trip=trip)
                        trip.phase_change(to_phase=atom.TripPhase.RIDING)
                else:
                    logging.debug(f"No vehicle assigned for trip {trip.index}")

    def _assign_vehicle(self, trip, idle_vehicles, random_choice=False):
        """
        Find the nearest vehicle to a ridehail call at x, y
        Set that vehicle's phase to DISPATCHED
        Returns an assigned vehicle or None
        """
        logging.debug("Assigning a vehicle to a request...")
        current_minimum = self.city.city_size * 100  # Very big
        assigned_vehicle = None
        if idle_vehicles:
            if random_choice:
                assigned_vehicle = random.choice(idle_vehicles)
            else:
                for vehicle in idle_vehicles:
                    travel_distance = self.city.travel_distance(
                        vehicle.location, vehicle.direction, trip.origin,
                        current_minimum)
                    if travel_distance < current_minimum:
                        current_minimum = travel_distance
                        assigned_vehicle = vehicle
                        logging.debug(
                            (f"Vehicle at {assigned_vehicle.location} "
                             f"travelling {vehicle.direction.name} "
                             f"assigned to pickup at {trip.origin}. "
                             f"Travel distance {travel_distance}."))
                        if travel_distance == 0:
                            break
        return assigned_vehicle

    def _cancel_requests(self, max_wait_time=None):
        """
        If a request has been waiting too long, cancel it.
        """
        if max_wait_time:
            unassigned_trips = [
                trip for trip in self.trips
                if trip.phase == atom.TripPhase.UNASSIGNED
            ]
            for trip in unassigned_trips:
                if trip.phase_time[atom.TripPhase.UNASSIGNED] >= max_wait_time:
                    trip.phase_change(to_phase=atom.TripPhase.CANCELLED)
                    logging.debug((
                        f"Trip {trip.index} cancelled after "
                        f"{trip.phase_time[atom.TripPhase.UNASSIGNED]} blocks."
                    ))

    def _init_block(self, block):
        """
        - If needed, update simulations settings from user input
          (self.target_state values).
        - Initialize values for the "block" item of each array.
        """
        # Apply any impulses in self.impulse_list settings
        if hasattr(self, "impulse_list") and self.impulse_list is not None:
            for impulse in self.impulse_list:
                if "block" in impulse:
                    if block == impulse["block"] and "base_demand" in impulse:
                        self.target_state["base_demand"] = impulse[
                            "base_demand"]
                    if (block == impulse["block"]
                            and "vehicle_count" in impulse):
                        self.target_state["vehicle_count"] = impulse[
                            "vehicle_count"]
        # resize the city
        if self.city.city_size != self.target_state["city_size"]:
            self.city.city_size = self.target_state["city_size"]
            # Reposition the vehicles within the city boundaries
            for vehicle in self.vehicles:
                for i in [0, 1]:
                    vehicle.location[
                        i] = vehicle.location[i] % self.city.city_size
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
        if self.equilibrate in (atom.Equilibration.PRICE,
                                atom.Equilibration.SUPPLY):
            # Update the price
            self.price = self.target_state["price"]
            # Update the request rate to reflect the price
            self.request_rate = self._demand()
            if self.reserved_wage != self.target_state["reserved_wage"]:
                self.reserved_wage = self.target_state["reserved_wage"]
                logging.info(f"New reserved_wage = {self.reserved_wage:.02f}")
            if (self.platform_commission !=
                    self.target_state["platform_commission"]):
                self.platform_commission = self.target_state[
                    "platform_commission"]
                logging.info(f"New platform commission = "
                             f"{self.platform_commission:.02f}")
        # add or remove vehicles for manual changes only
        elif self.equilibrate == atom.Equilibration.NONE:
            # Update the request rate to reflect the base demand
            self.request_rate = self._demand()
            old_vehicle_count = len(self.vehicles)
            vehicle_diff = self.target_state[
                "vehicle_count"] - old_vehicle_count
            if vehicle_diff > 0:
                for d in range(vehicle_diff):
                    self.vehicles.append(
                        atom.Vehicle(old_vehicle_count + d, self.city,
                                     self.idle_vehicles_moving))
            elif vehicle_diff < 0:
                removed_vehicles = self._remove_vehicles(-vehicle_diff)
                logging.info(
                    f"Period start: removed {removed_vehicles} vehicles.")
        self.equilibrate = self.target_state["equilibrate"]

        # Set trips that were completed last move to be 'inactive' for
        # the beginning of this one
        for trip in self.trips:
            if trip.phase in (atom.TripPhase.COMPLETED,
                              atom.TripPhase.CANCELLED):
                trip.phase = atom.TripPhase.INACTIVE

    def _update_history_arrays(self, block):
        """
        Called after each block to update history statistics
        """
        # Update base stats
        # vehicle count and request rate are filled in anew each block
        self.stats[atom.History.VEHICLE_COUNT][block] = len(self.vehicles)
        self.stats[atom.History.REQUEST_RATE][block] = self.request_rate
        self.stats[atom.History.REQUEST_CAPITAL][block] = (
            (self.stats[atom.History.REQUEST_CAPITAL][block - 1] % 1) +
            self.request_rate)
        if len(self.vehicles) > 0:
            for vehicle in self.vehicles:
                self.stats[atom.History.VEHICLE_TIME][block] += 1
                if vehicle.phase == atom.VehiclePhase.IDLE:
                    self.stats[atom.History.VEHICLE_P1_TIME][block] += 1
                elif vehicle.phase == atom.VehiclePhase.DISPATCHED:
                    self.stats[atom.History.VEHICLE_P2_TIME][block] += 1
                elif vehicle.phase == atom.VehiclePhase.WITH_RIDER:
                    self.stats[atom.History.VEHICLE_P3_TIME][block] += 1
        if self.trips:
            for trip in self.trips:
                phase = trip.phase
                trip.phase_time[phase] += 1
                if phase == atom.TripPhase.UNASSIGNED:
                    pass
                elif phase == atom.TripPhase.WAITING:
                    pass
                elif phase == atom.TripPhase.RIDING:
                    self.stats[atom.History.TRIP_RIDING_TIME][block] += 1
                elif phase == atom.TripPhase.COMPLETED:
                    self.stats[atom.History.TRIP_COUNT][block] += 1
                    self.stats[atom.History.COMPLETED_TRIPS][block] += 1
                    self.stats[atom.History.TRIP_DISTANCE][block] += (
                        trip.distance)
                    self.stats[atom.History.TRIP_AWAITING_TIME][block] += (
                        trip.phase_time[atom.TripPhase.WAITING])
                    self.stats[atom.History.TRIP_UNASSIGNED_TIME][block] += (
                        trip.phase_time[atom.TripPhase.UNASSIGNED])
                    # Bad name: WAIT_TIME = WAITING + UNASSIGNED
                    self.stats[atom.History.WAIT_TIME][block] += (
                        trip.phase_time[atom.TripPhase.UNASSIGNED] +
                        trip.phase_time[atom.TripPhase.WAITING])
                elif phase == atom.TripPhase.CANCELLED:
                    # Cancelled trips are still counted as trips,
                    # just not as completed trips
                    self.stats[atom.History.TRIP_COUNT][block] += 1
                elif phase == atom.TripPhase.INACTIVE:
                    # do nothing with INACTIVE trips
                    pass
        json_string = (("{" f'"block": {block}'))
        for array_name, array in self.stats.items():
            json_string += (f', "{array_name}":' f' {array[block]}')
        json_string += ("}")
        logging.debug(f"Simulation: {json_string}")

    def _collect_garbage(self, block):
        """
        Garbage collect the list of trips to get rid of the completed and
        cancelled ones.

        For each trip, find the vehicle with that trip_index
        and reset the vehicle.trip_index and trip.index to
        "i".
        """
        if block % GARBAGE_COLLECTION_INTERVAL == 0:
            self.trips = [
                trip for trip in self.trips if trip.phase not in
                [atom.TripPhase.COMPLETED, atom.TripPhase.CANCELLED]
            ]
            for i, trip in enumerate(self.trips):
                trip_index = trip.index
                for vehicle in self.vehicles:
                    if vehicle.trip_index == trip_index:
                        # Found the vehicle that matches this trip
                        vehicle.trip_index = i
                        break
                trip.index = i

    def _remove_vehicles(self, number_to_remove):
        """
        Remove 'number_to_remove' vehicles from self.vehicles.
        Returns the number of vehicles removed
        """
        vehicles_removed = 0
        for i, vehicle in enumerate(self.vehicles):
            if vehicle.phase == atom.VehiclePhase.IDLE:
                del self.vehicles[i]
                vehicles_removed += 1
                if vehicles_removed == number_to_remove:
                    break
        return vehicles_removed

    def _equilibrate_supply(self, block):
        """
        Change the vehicle count and request rate to move the system
        towards equilibrium.
        """
        if ((block % self.equilibration_interval == 0)
                and block >= self.equilibration_interval):
            # only equilibrate at certain times
            lower_bound = max((block - self.equilibration_interval), 0)
            # equilibration_blocks = (blocks - lower_bound)
            total_vehicle_time = (
                self.stats[atom.History.VEHICLE_TIME][block] -
                self.stats[atom.History.VEHICLE_TIME][lower_bound])
            p3_fraction = (
                (self.stats[atom.History.VEHICLE_P3_TIME][block] -
                 self.stats[atom.History.VEHICLE_P3_TIME][lower_bound]) /
                total_vehicle_time)
            vehicle_utility = self.vehicle_utility(p3_fraction)
            # logging.info((f"p3={p3_fraction}", f", U={vehicle_utility}"))
            old_vehicle_count = len(self.vehicles)
            damping_factor = 0.4
            vehicle_increment = int(damping_factor * old_vehicle_count *
                                    vehicle_utility)
            if vehicle_increment > 0:
                vehicle_increment = min(vehicle_increment,
                                        int(0.1 * len(self.vehicles)))
                self.vehicles += [
                    atom.Vehicle(i, self.city, self.idle_vehicles_moving)
                    for i in range(old_vehicle_count, old_vehicle_count +
                                   vehicle_increment)
                ]
            elif vehicle_increment < 0:
                vehicle_increment = max(vehicle_increment,
                                        -0.1 * len(self.vehicles))
                self._remove_vehicles(-vehicle_increment)
            logging.debug((f"{{'block': {block}, "
                           f"'vehicle_utility': {vehicle_utility:.02f}, "
                           f"'busy': {p3_fraction:.02f}, "
                           f"'increment': {vehicle_increment}, "
                           f"'old vehicle count': {old_vehicle_count}, "
                           f"'new vehicle count': {len(self.vehicles)}}}"))

    def vehicle_utility(self, busy_fraction):
        """
        Vehicle utility per unit time:
            vehicle_utility = p3 * p * (1 - f) - reserved wage
        """
        return (self.price * (1.0 - self.platform_commission) * busy_fraction -
                self.reserved_wage)

    def _demand(self):
        """
        Return demand (request_rate):
           request_rate = base_demand * price ^ (-elasticity)
        """
        demand = self.base_demand
        if self.equilibrate == atom.Equilibration.PRICE:
            demand *= self.price**(-self.demand_elasticity)
        return demand


class RideHailSimulationResults():
    """
    Hold the results of a RideHailSimulation.
    Usually it just writes it out, but now we can do things like
    plot sequences of simulations
    """
    def __init__(self, sim):
        self.sim = sim
        self.results = {}
        config = {}
        config["city_size"] = self.sim.city.city_size
        config["vehicle_count"] = len(self.sim.vehicles)
        config["trip_distribution"] = self.sim.city.trip_distribution.name
        config["min_trip_distance"] = self.sim.config.min_trip_distance
        config["time_blocks"] = self.sim.time_blocks
        config["request_rate"] = self.sim.request_rate
        config["results_window"] = self.sim.config.results_window
        config["idle_vehicles_moving"] = (self.sim.idle_vehicles_moving)
        config["animation"] = self.sim.config.equilibration
        config["equilibration"] = self.sim.config.equilibration
        config["sequence"] = self.sim.config.sequence
        self.results["config"] = config
        if (self.sim.config.equilibration
                and self.sim.equilibrate != atom.Equilibration.NONE):
            equilibrate = {}
            equilibrate["equilibrate"] = self.sim.equilibrate.name
            equilibrate["price"] = self.sim.price
            equilibrate["platform_commission"] = (self.sim.platform_commission)
            equilibrate["equilibration_interval"] = (
                self.sim.equilibration_interval)
            if self.sim.equilibrate == atom.Equilibration.PRICE:
                equilibrate["base_demand"] = self.sim.base_demand
            if self.sim.equilibrate in (atom.Equilibration.PRICE,
                                        atom.Equilibration.SUPPLY):
                equilibrate["reserved_wage"] = self.sim.reserved_wage
            self.results["equilibrate"] = equilibrate
        self.results_file_handle = open(f"{self.sim.config.jsonl_file}", 'w')

    def write_config(self):
        self.results_file_handle.write(json.dumps(self.results))
        self.results_file_handle.write("\n")

    def write_state(self, block):
        """
        Write a json object with the current state to the output file
        """
        state_dict = {}
        state_dict["block"] = block
        for history_item in list(atom.History):
            state_dict[
                history_item.value] = self.sim.stats[history_item][block]
        self.results_file_handle.write(json.dumps(state_dict) + "\n")

    def write_end_state(self):
        """
        Collect final state, averaged over the final
        sim.config.results_window blocks of the simulation
        """
        block = self.sim.time_blocks - 1
        lower_bound = max(
            (self.sim.time_blocks - self.sim.config.results_window), 0)
        result_blocks = (block - lower_bound)
        # N and R
        end_state = {}
        end_state["mean_vehicle_count"] = (sum(
            self.sim.stats[atom.History.VEHICLE_COUNT][lower_bound:block]) /
                                           result_blocks)
        end_state["mean_request_rate"] = (
            sum(self.sim.stats[atom.History.REQUEST_RATE][lower_bound:block]) /
            result_blocks)
        # vehicle stats
        end_state["total_vehicle_time"] = (sum(
            self.sim.stats[atom.History.VEHICLE_TIME][lower_bound:block]))
        end_state["total_trip_count"] = (sum(
            self.sim.stats[atom.History.TRIP_COUNT][lower_bound:block]))
        end_state["vehicle_fraction_idle"] = (sum(
            self.sim.stats[atom.History.VEHICLE_P1_TIME][lower_bound:block]) /
                                              end_state["total_vehicle_time"])
        end_state["vehicle_fraction_picking_up"] = (
            sum(self.sim.stats[atom.History.VEHICLE_P2_TIME]
                [lower_bound:block]) / end_state["total_vehicle_time"])
        end_state["vehicle_fraction_with_rider"] = (
            sum(self.sim.stats[atom.History.VEHICLE_P3_TIME]
                [lower_bound:block]) / end_state["total_vehicle_time"])
        # trip stats
        if end_state["total_trip_count"] > 0:
            end_state["mean_trip_wait_time"] = (sum(
                self.sim.stats[atom.History.WAIT_TIME][lower_bound:block]) /
                                                end_state["total_trip_count"])
            end_state["mean_trip_distance"] = (sum(
                self.sim.stats[atom.History.TRIP_DISTANCE][lower_bound:block])
                                               / end_state["total_trip_count"])
            # TODO: this is probably incorrect
            end_state["trip_fraction_wait_time"] = (
                end_state["mean_trip_wait_time"] /
                (end_state["mean_trip_wait_time"] +
                 end_state["mean_trip_distance"]))
        self.results["end_state"] = end_state
        self.results_file_handle.write(json.dumps(self.results) + "\n")
        self.results_file_handle.close()
