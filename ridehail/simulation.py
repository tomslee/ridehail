"""
A simulation
"""
import logging
import random
import json
import numpy as np
from datetime import datetime
from ridehail.atom import (City, Equilibration, History, Trip, TripPhase,
                           Vehicle, VehiclePhase)
from ridehail import config as rh_config

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
        if config.random_number_seed.value:
            random.seed(config.random_number_seed.value)
        self.target_state = {}
        self.config = config
        self.city_size = config.city_size.value
        self.trip_inhomogeneity = config.trip_inhomogeneity.value
        self.trip_inhomogeneous_destinations = (
            config.trip_inhomogeneous_destinations.value)
        self.city = City(self.city_size,
                         trip_inhomogeneity=self.trip_inhomogeneity,
                         trip_inhomogeneous_destinations=self.
                         trip_inhomogeneous_destinations)
        self.base_demand = config.base_demand.value
        self.vehicle_count = config.vehicle_count.value
        self.min_trip_distance = config.min_trip_distance.value
        self.max_trip_distance = config.max_trip_distance.value
        self.idle_vehicles_moving = config.idle_vehicles_moving.value
        self.time_blocks = config.time_blocks.value
        self.results_window = config.results_window.value
        self.animate = config.animate.value
        self.interpolate = config.interpolate.value
        self.annotation = config.annotation.value
        self.equilibrate = config.equilibrate.value
        self.run_sequence = config.run_sequence.value
        self.equilibration = config.equilibration.value
        self.price = config.price.value
        self.platform_commission = config.platform_commission.value
        self.reserved_wage = config.reserved_wage.value
        self.demand_elasticity = config.demand_elasticity.value
        self.equilibration_interval = config.equilibration_interval.value
        self.impulse_list = config.impulse_list.value
        for attr in dir(self):
            option = getattr(self, attr)
            if (callable(option) or attr.startswith("__")):
                continue
            if attr not in ("target_state", ):
                self.target_state[attr] = option
        # Following items not set in config
        self.block_index = 0
        self.request_rate = self._demand()
        self.trips = []
        self.history = {}
        self.vehicles = [
            Vehicle(i, self.city, self.idle_vehicles_moving)
            for i in range(self.vehicle_count)
        ]
        for history_item in list(History):
            self.history[history_item] = np.zeros(self.time_blocks + 2)
        self.changed_plotstat_flag = False
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
        if hasattr(self.config, "jsonl_file"):
            output_file_handle = open(f"{self.config.jsonl_file}", 'a')
        else:
            output_file_handle = None
        output_dict = {}
        output_dict["config"] = rh_config.WritableConfig(self.config).__dict__
        if (hasattr(self.config, "jsonl_file")
                and not self.config.run_sequence.value):
            output_file_handle.write(json.dumps(output_dict) + "\n")
        results = RideHailSimulationResults(self)
        for block in range(self.time_blocks):
            self.next_block(output_file_handle, block)
        results.end_state = results.compute_end_state()
        output_dict["results"] = results.end_state
        if hasattr(self.config, "jsonl_file"):
            output_file_handle.write(json.dumps(output_dict) + "\n")
            output_file_handle.close()
        return results

    def next_block(self,
                   output_file_handle=None,
                   block=None,
                   return_values=None):
        """
        Call all those functions needed to simulate the next block
        - block should be supplied if the simulation is run externally,
          rather than from the simulate() method.
        - output_file_handle should be None if running in a browser.
        """
        if block is None:
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
                if (vehicle.phase == VehiclePhase.DISPATCHED
                        and vehicle.location == vehicle.pickup):
                    # the vehicle has arrived at the pickup spot and picks up
                    # the rider
                    vehicle.phase_change(to_phase=VehiclePhase.WITH_RIDER)
                    trip.phase_change(to_phase=TripPhase.RIDING)
                elif (vehicle.phase == VehiclePhase.WITH_RIDER
                      and vehicle.location == vehicle.dropoff):
                    # The vehicle has arrived at the dropoff and the trip ends.
                    # Update vehicle and trip to reflect the completion
                    vehicle.phase_change()
                    trip.phase_change(to_phase=TripPhase.COMPLETED)
        # Using the history from the previous block,
        # equilibrate the supply and/or demand of rides
        if (self.equilibrate and self.equilibration
                in (Equilibration.SUPPLY, Equilibration.PRICE)):
            self._equilibrate_supply(block)
        # Customers make trip requests
        self._request_trips(block)
        # If there are vehicles free, assign one to each request
        self._assign_vehicles()
        # Some requests get cancelled if they have been open too long
        self._cancel_requests(max_wait_time=None)
        # Update history for everything that has happened in this block
        self._update_history_arrays(block)
        # Some arrays hold information for each trip:
        # compress these as needed to avoid a growing set
        # of completed or cancelled (dead) trips
        self._collect_garbage(block)
        if self.config.run_sequence.value:
            state_dict = None
        else:
            state_dict = self.write_state(
                block, output_file_handle=output_file_handle)
            logging.info(f"Block {block} completed")
        self.block_index += 1
        # return self.block_index
        if return_values == "stats":
            return state_dict
        elif return_values == "map":
            vehicles = [[
                vehicle.phase.name, vehicle.location, vehicle.direction
            ] for vehicle in self.vehicles]
            return [self.block_index, vehicles]

    def vehicle_utility(self, busy_fraction):
        """
        Vehicle utility per unit time:
            vehicle_utility = (p3 * p * (1 - f) - reserved wage)
        """
        return (self.price * (1.0 - self.platform_commission) * busy_fraction -
                self.reserved_wage)

    def write_state(self, block, output_file_handle=None):
        """
        Write a json object with the current state to the output file
        """
        state_dict = {}
        state_dict["block"] = block
        for history_item in list(History):
            state_dict[history_item.value] = self.history[history_item][block]
        if output_file_handle:
            json_string = json.dumps(state_dict) + "\n"
            output_file_handle.write(json_string)
        return state_dict

    def _request_trips(self, block):
        """
        Periodically initiate a request from an inactive rider
        For requests not assigned a vehicle, repeat the request.

        """
        requests_this_block = int(self.history[History.REQUEST_CAPITAL][block -
                                                                        1])
        for trip in range(requests_this_block):
            trip = Trip(len(self.trips),
                        self.city,
                        min_trip_distance=self.min_trip_distance,
                        max_trip_distance=self.max_trip_distance)
            self.trips.append(trip)
            logging.debug(
                (f"Request: trip {trip.origin} -> {trip.destination}"))
            # the trip has a random origin and destination
            # and is ready to make a request.
            # This sets the trip to TripPhase.UNASSIGNED
            # as no vehicle is assigned here
            trip.phase_change(TripPhase.UNASSIGNED)
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
            trip for trip in self.trips if trip.phase == TripPhase.UNASSIGNED
        ]
        if unassigned_trips:
            random.shuffle(unassigned_trips)
            logging.debug(
                f"There are {len(unassigned_trips)} unassigned trips")
            idle_vehicles = [
                vehicle for vehicle in self.vehicles
                if vehicle.phase == VehiclePhase.IDLE
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

                    trip.phase_change(to_phase=TripPhase.WAITING)
                    if assigned_vehicle.location == trip.origin:
                        # Do the pick up now
                        assigned_vehicle.phase_change(trip=trip)
                        trip.phase_change(to_phase=TripPhase.RIDING)
                else:
                    logging.debug(f"No vehicle assigned for trip {trip.index}")

    def _assign_vehicle(self, trip, idle_vehicles, random_choice=False):
        """
        Find the nearest vehicle to a ridehail call at x, y
        Set that vehicle's phase to DISPATCHED
        Returns an assigned vehicle or None.

        The minimum distance is 1, not zero, because it takes
        a period to do the assignment. Also, this makes scaling
        more realistic as small city sizes are equivalent to "batching"
        requests across a longer time interval (see notebook, 2021-12-06).
        """
        logging.debug("Assigning a vehicle to a request...")
        current_minimum = self.city_size * 100  # Very big
        assigned_vehicle = None
        if idle_vehicles:
            if random_choice:
                assigned_vehicle = random.choice(idle_vehicles)
            else:
                for vehicle in idle_vehicles:
                    travel_distance = self.city.travel_distance(
                        vehicle.location, vehicle.direction, trip.origin,
                        current_minimum)
                    if 0 < travel_distance < current_minimum:
                        current_minimum = travel_distance
                        assigned_vehicle = vehicle
                        logging.debug(
                            (f"Vehicle at {assigned_vehicle.location} "
                             f"travelling {vehicle.direction.name} "
                             f"assigned to pickup at {trip.origin}. "
                             f"Travel distance {travel_distance}."))
                        if travel_distance == 1:
                            break
        return assigned_vehicle

    def _cancel_requests(self, max_wait_time=None):
        """
        If a request has been waiting too long, cancel it.
        """
        if max_wait_time:
            unassigned_trips = [
                trip for trip in self.trips
                if trip.phase == TripPhase.UNASSIGNED
            ]
            for trip in unassigned_trips:
                if trip.phase_time[TripPhase.UNASSIGNED] >= max_wait_time:
                    trip.phase_change(to_phase=TripPhase.CANCELLED)
                    logging.debug(
                        (f"Trip {trip.index} cancelled after "
                         f"{trip.phase_time[TripPhase.UNASSIGNED]} blocks."))

    def _init_block(self, block):
        """
        - If needed, update simulations settings from user input
          (self.target_state values).
        - Initialize values for the "block" item of each array.
        """
        # Target state changes come from key events or from config.impulse_list
        # Apply any impulses in self.impulse_list settings
        self.changed_plotstat_flag = False
        if self.impulse_list:
            for impulse_dict in self.impulse_list:
                if "block" in impulse_dict and block == impulse_dict["block"]:
                    for key, val in impulse_dict.items():
                        self.target_state[key] = val
        # Apply the target_state values
        for attr in dir(self):
            val = getattr(self, attr)
            if (callable(attr) or attr.startswith("__")
                    or attr not in self.target_state.keys()):
                continue
            if val != self.target_state[attr]:
                setattr(self, attr, self.target_state[attr])
                if attr == "equilibrate":
                    self.changed_plotstat_flag = True
        # Additional actions to accommidatenew values
        self.city.city_size = self.city_size
        self.city.trip_inhomogeneity = self.trip_inhomogeneity
        self.request_rate = self._demand()
        # Reposition the vehicles within the city boundaries
        for vehicle in self.vehicles:
            for i in [0, 1]:
                vehicle.location[i] = vehicle.location[i] % self.city_size
        # Likewise for trips: reposition origins and destinations
        # within the city boundaries
        for trip in self.trips:
            for i in [0, 1]:
                trip.origin[i] = trip.origin[i] % self.city_size
                trip.destination[i] = trip.destination[i] % self.city_size
        # Add or remove vehicles and requests
        # for non-equilibrating simulations only
        if (not self.equilibrate or self.equilibration == Equilibration.NONE):
            # Update the request rate to reflect the base demand
            old_vehicle_count = len(self.vehicles)
            vehicle_diff = self.vehicle_count - old_vehicle_count
            if vehicle_diff > 0:
                for d in range(vehicle_diff):
                    self.vehicles.append(
                        Vehicle(old_vehicle_count + d, self.city,
                                self.idle_vehicles_moving))
            elif vehicle_diff < 0:
                removed_vehicles = self._remove_vehicles(-vehicle_diff)
                logging.debug(
                    f"Period start: removed {removed_vehicles} vehicles.")
        # Set trips that were completed last move to be 'inactive' for
        # the beginning of this one
        for trip in self.trips:
            if trip.phase in (TripPhase.COMPLETED, TripPhase.CANCELLED):
                trip.phase = TripPhase.INACTIVE

    def _update_history_arrays(self, block):
        """
        Called after each block to update history statistics.

        The history statistics represent two kinds of things:
        - some (eg VEHICLE_COUNT, REQUEST_RATE) track the current state of
          a variable throughout a simulation
        - others (eg VEHICLE_P1_TIME, TRIP_DISTANCE) are cumulative values
          incremented over the entire run
        - TRIP_WAIT_FRACTION is an average and probably should not be trusted.
          Fortunately, animation does not use it - I think it is just written
          out in end_state.

        All averaging and smoothing is done in the animation function
        Animation._update_plot_arrays, which uses History functions over
        the smoothing_window (sometimes differences, sometimes sums).
        """
        # Update base history
        # vehicle count and request rate are filled in anew each block
        self.history[History.VEHICLE_COUNT][block] = len(self.vehicles)
        self.history[History.REQUEST_RATE][block] = self.request_rate
        self.history[History.REQUEST_CAPITAL][block] = (
            (self.history[History.REQUEST_CAPITAL][block - 1] % 1) +
            self.request_rate)
        if len(self.vehicles) > 0:
            for vehicle in self.vehicles:
                self.history[History.VEHICLE_TIME][block] += 1
                if vehicle.phase == VehiclePhase.IDLE:
                    self.history[History.VEHICLE_P1_TIME][block] += 1
                elif vehicle.phase == VehiclePhase.DISPATCHED:
                    self.history[History.VEHICLE_P2_TIME][block] += 1
                elif vehicle.phase == VehiclePhase.WITH_RIDER:
                    self.history[History.VEHICLE_P3_TIME][block] += 1
        if self.trips:
            for trip in self.trips:
                phase = trip.phase
                trip.phase_time[phase] += 1
                if phase == TripPhase.UNASSIGNED:
                    pass
                elif phase == TripPhase.WAITING:
                    pass
                elif phase == TripPhase.RIDING:
                    self.history[History.TRIP_RIDING_TIME][block] += 1
                elif phase == TripPhase.COMPLETED:
                    self.history[History.TRIP_COUNT][block] += 1
                    self.history[History.COMPLETED_TRIPS][block] += 1
                    self.history[History.TRIP_DISTANCE][block] += (
                        trip.distance)
                    self.history[History.TRIP_AWAITING_TIME][block] += (
                        trip.phase_time[TripPhase.WAITING])
                    self.history[History.TRIP_UNASSIGNED_TIME][block] += (
                        trip.phase_time[TripPhase.UNASSIGNED])
                    # Bad name: WAIT_TIME = WAITING + UNASSIGNED
                    trip_wait_time = (trip.phase_time[TripPhase.UNASSIGNED] +
                                      trip.phase_time[TripPhase.WAITING])
                    self.history[History.WAIT_TIME][block] += trip_wait_time
                    self.history[History.TRIP_WAIT_FRACTION][block] += (
                        trip_wait_time / (trip_wait_time + trip.distance))
                elif phase == TripPhase.CANCELLED:
                    # Cancelled trips are still counted as trips,
                    # just not as completed trips
                    self.history[History.TRIP_COUNT][block] += 1
                elif phase == TripPhase.INACTIVE:
                    # do nothing with INACTIVE trips
                    pass
        json_string = (("{" f'"block": {block}'))
        for array_name, array in self.history.items():
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
                [TripPhase.COMPLETED, TripPhase.CANCELLED]
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
            if vehicle.phase == VehiclePhase.IDLE:
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
                and block >= max(self.city_size, self.equilibration_interval)):
            # only equilibrate at certain times
            lower_bound = max((block - self.equilibration_interval), 0)
            # equilibration_blocks = (blocks - lower_bound)
            total_vehicle_time = (
                self.history[History.VEHICLE_TIME][block] -
                self.history[History.VEHICLE_TIME][lower_bound])
            p3_fraction = (
                (self.history[History.VEHICLE_P3_TIME][block] -
                 self.history[History.VEHICLE_P3_TIME][lower_bound]) /
                total_vehicle_time)
            vehicle_utility = self.vehicle_utility(p3_fraction)
            old_vehicle_count = len(self.vehicles)
            damping_factor = 0.8
            vehicle_increment = int(damping_factor * old_vehicle_count *
                                    vehicle_utility)
            if vehicle_increment > 0:
                vehicle_increment = min(vehicle_increment,
                                        int(0.1 * old_vehicle_count))
                self.vehicles += [
                    Vehicle(i, self.city, self.idle_vehicles_moving)
                    for i in range(old_vehicle_count, old_vehicle_count +
                                   vehicle_increment)
                ]
            elif vehicle_increment < 0:
                vehicle_increment = max(vehicle_increment,
                                        -0.1 * old_vehicle_count)
                self._remove_vehicles(-vehicle_increment)
            logging.debug((f"Equilibrating: {{'block': {block}, "
                           f"'P3': {p3_fraction:.02f}, "
                           f"'vehicle_utility': {vehicle_utility:.02f}, "
                           f"'increment': {vehicle_increment}, "
                           f"'old count': {old_vehicle_count}, "
                           f"'new count': {len(self.vehicles)}}}"))

    def _demand(self):
        """
        Return demand (request_rate):
           request_rate = base_demand * price ^ (-elasticity)
        """
        demand = self.base_demand
        if self.equilibration == Equilibration.PRICE:
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
        config["city_size"] = self.sim.city_size
        config["vehicle_count"] = len(self.sim.vehicles)
        config["trip_inhomogeneity"] = self.sim.city.trip_inhomogeneity
        config["min_trip_distance"] = self.sim.min_trip_distance
        config["max_trip_distance"] = self.sim.max_trip_distance
        config["time_blocks"] = self.sim.time_blocks
        config["request_rate"] = self.sim.request_rate
        config["results_window"] = self.sim.results_window
        config["idle_vehicles_moving"] = (self.sim.idle_vehicles_moving)
        config["animate"] = self.sim.animate
        config["equilibrate"] = self.sim.equilibrate
        config["run_sequence"] = self.sim.run_sequence
        self.results["config"] = config
        if (self.sim.equilibrate
                and self.sim.equilibration != Equilibration.NONE):
            equilibrate = {}
            equilibrate["equilibration"] = self.sim.equilibration.name
            equilibrate["price"] = self.sim.price
            equilibrate["platform_commission"] = (self.sim.platform_commission)
            equilibrate["equilibration_interval"] = (
                self.sim.equilibration_interval)
            if self.sim.equilibrate == Equilibration.PRICE:
                equilibrate["base_demand"] = self.sim.base_demand
                equilibrate["demand_elasticity"] = self.sim.demand_elasticity
            if self.sim.equilibrate in (Equilibration.PRICE,
                                        Equilibration.SUPPLY):
                equilibrate["reserved_wage"] = self.sim.reserved_wage
            self.results["equilibrate"] = equilibrate

    def compute_end_state(self):
        """
        Collect final state, averaged over the final
        sim.results_window blocks of the simulation
        """
        block = self.sim.time_blocks - 1
        block_lower_bound = max(
            (self.sim.time_blocks - self.sim.results_window), 0)
        result_blocks = (block - block_lower_bound)
        # N and R
        end_state = {}
        end_state["mean_vehicle_count"] = round((sum(
            self.sim.history[History.VEHICLE_COUNT][block_lower_bound:block]) /
                                                 result_blocks), 3)
        end_state["mean_request_rate"] = round((sum(
            self.sim.history[History.REQUEST_RATE][block_lower_bound:block]) /
                                                result_blocks), 3)
        # vehicle history
        end_state["total_vehicle_time"] = round((sum(
            self.sim.history[History.VEHICLE_TIME][block_lower_bound:block])),
                                                3)
        end_state["total_trip_count"] = round((sum(
            self.sim.history[History.TRIP_COUNT][block_lower_bound:block])), 3)
        end_state["vehicle_fraction_idle"] = round(
            (sum(self.sim.history[History.VEHICLE_P1_TIME]
                 [block_lower_bound:block]) / end_state["total_vehicle_time"]),
            3)
        end_state["vehicle_fraction_picking_up"] = round(
            (sum(self.sim.history[History.VEHICLE_P2_TIME]
                 [block_lower_bound:block]) / end_state["total_vehicle_time"]),
            3)
        end_state["vehicle_fraction_with_rider"] = round(
            (sum(self.sim.history[History.VEHICLE_P3_TIME]
                 [block_lower_bound:block]) / end_state["total_vehicle_time"]),
            3)
        # trip history
        if end_state["total_trip_count"] > 0:
            end_state["mean_trip_wait_time"] = round(
                (sum(self.sim.history[History.WAIT_TIME]
                     [block_lower_bound:block]) /
                 end_state["total_trip_count"]), 3)
            end_state["mean_trip_distance"] = round(
                (sum(self.sim.history[History.TRIP_DISTANCE]
                     [block_lower_bound:block]) /
                 end_state["total_trip_count"]), 3)
            # TODO: this is probably incorrect: dividing means doesn't give a
            # mean
            end_state["mean_trip_wait_fraction"] = round(
                (sum(self.sim.history[History.TRIP_WAIT_FRACTION]
                     [block_lower_bound:block]) /
                 end_state["total_trip_count"]), 3)
        return end_state
