"""
A simulation
"""

import json
import logging
import random
from collections import deque
from os import makedirs, path

from ridehail.dispatch import Dispatch
from ridehail.measures import compute_measures
from ridehail.atom import (
    CircularBuffer,
    City,
    CityScaleUnit,
    DispatchMethod,
    Equilibration,
    History,
    Measure,
    Trip,
    TripPhase,
    Vehicle,
    VehiclePhase,
)
from ridehail.convergence import ConvergenceTracker, DEFAULT_CONVERGENCE_METRICS


GARBAGE_COLLECTION_INTERVAL = 50  # Reduced from 200 for better performance


class RideHailSimulation:
    """
    Simulate a ridehail environment, with vehicles and trips
    """

    def __init__(self, config):
        """
        Set up a simulation from a RideHailConfig: copy the config values
        to attributes, validate them, and create the city and the vehicles.
        """
        self.config = config
        # Automatically copy all config items to the simulation object
        # Some of these may be changed dynamically during the course of a
        # simulation, so making a copy makes sense rather than referencing
        # the self.config.attr_name throughout. The two things are logically
        # distinct.
        # self.attr_name = config.attr_name.value for each item in the config
        for attr_name in dir(config):
            attr = getattr(config, attr_name)
            if hasattr(attr, "value") and not attr_name.startswith("_"):
                setattr(self, attr_name, attr.value)
        # special cases
        self.config_file = config.config_file.value or None
        self.start_time = config.start_time
        # dispatch_method applies only with use_advanced_dispatch, whether it
        # came from the config file, the command line, or code
        if not self.use_advanced_dispatch:
            self.dispatch_method = DispatchMethod.DEFAULT

        self.city = City(
            self.city_size,
            inhomogeneity=self.inhomogeneity,
            inhomogeneous_destinations=self.inhomogeneous_destinations,
            idle_vehicles_returning=self.idle_vehicles_returning,
        )
        self._set_output_files()
        self._validate_options()
        # When use_city_scale=True, base_demand is in trips/minute (real time).
        # Convert to trips/block so the rest of the simulation uses the correct
        # internal unit. minutes_per_block is the congestion lever: higher
        # values raise per-block demand, holding trips/minute constant.
        if self.use_city_scale:
            self.base_demand = self.convert_units(
                self.base_demand, CityScaleUnit.PER_MINUTE, CityScaleUnit.PER_BLOCK
            )
        self._update_city_scale_prices()
        # Live changes to settings, {attribute: new value}: set by keyboard
        # controls, the web lab's live controls and impulse_list, applied at
        # the start of the next block (_init_block) and then cleared. Code that
        # changes an attribute directly needs no entry here.
        self.target_state = {}
        # Following items not set in config
        if config.random_number_seed.value:
            random.seed(config.random_number_seed.value)
        self.block_index = 0
        self.request_rate = self._demand()
        self.trips = {}
        self.next_trip_id = 0
        # (block, wait_time, distance) tuples for recently completed trips,
        # pruned to the last `results_window` blocks. Used by the
        # terminal_wait animation's histogram, and to compute median trip
        # wait-time statistics (a true per-trip median isn't recoverable
        # from the block-summed History buffers).
        self.trip_completion_history = deque()
        # Each vehicle gets a new index (see _new_vehicle), so an index
        # identifies one vehicle for the whole run, even as the fleet grows and
        # shrinks. It is not the vehicle's position in self.vehicles.
        self._next_vehicle_index = 0
        self.vehicles = [self._new_vehicle() for _ in range(self.vehicle_count)]
        self.changed_plotstat_flag = False
        self._request_capital = 0.0
        self.dispatcher = Dispatch(self.dispatch_method, self.forward_dispatch_bias)
        # history_buffer is used for smoothing plots, and getting average
        # or total quantities over a window of size smoothing_window
        self.history_buffer = {}
        for stat in list(History):
            self.history_buffer[stat] = CircularBuffer(self.smoothing_window)
        self.history_results = {}
        # history_results stores the final end state of the simulation,
        # averaged or summed over a window of size results_window
        for stat in list(History):
            self.history_results[stat] = CircularBuffer(self.results_window)
        # Adaptive equilibration parameters (Phase 1: oscillation detection + adaptive damping)
        # Only used when equilibration_interval == 0 (automatic mode)
        # Initialize BEFORE history_equilibration buffers so we can use it for buffer size
        self.damping_factor = 0.5
        self.adaptive_equilibration_interval = 5  # Dynamic update frequency
        self.previous_vehicle_increment = (
            0  # Track previous increment for oscillation detection
        )
        self.previous_vehicle_increment_sign = 0  # Sign of previous increment
        self.oscillation_count = 0  # Count consecutive oscillations
        self.consecutive_improvements = 0  # Count improvements for damping reduction
        self.previous_convergence_residual = float("inf")  # Track convergence progress

        # history_equilibration is used to provide values to drive equilibration,
        # averaged or summed over a window of size equilibration_interval
        # When equilibration_interval == 0 (adaptive mode), use max interval (20)
        # to accommodate dynamic interval changes during simulation
        equilibration_buffer_size = (
            20  # Maximum adaptive interval
            if self.equilibration_interval == 0
            else self.equilibration_interval
        )
        self.history_equilibration = {}
        for stat in list(History):
            self.history_equilibration[stat] = CircularBuffer(equilibration_buffer_size)
        # Convergence tracker for monitoring approach to steady state
        self.convergence_metrics = DEFAULT_CONVERGENCE_METRICS
        self.convergence_tracker = ConvergenceTracker(
            metrics_to_track=self.convergence_metrics,
            chain_length=self.smoothing_window,
            convergence_windows=int(self.results_window / self.smoothing_window) + 1,
        )

    def convert_units(
        self, in_value: float, from_unit: CityScaleUnit, to_unit: CityScaleUnit
    ):
        """
        Returns None on error
        """
        hours_per_minute = 1.0 / 60.0
        blocks = None
        per_block = None
        out_value = None
        if from_unit == CityScaleUnit.MINUTE:
            blocks = in_value / self.minutes_per_block
        elif from_unit == CityScaleUnit.HOUR:
            blocks = in_value / (self.minutes_per_block * hours_per_minute)
        elif from_unit == CityScaleUnit.KM:
            blocks = in_value / (
                self.minutes_per_block * hours_per_minute * self.mean_vehicle_speed
            )
        elif from_unit == CityScaleUnit.BLOCK:
            blocks = in_value
        # Convert from blocks to out_value
        if blocks is not None and to_unit == CityScaleUnit.MINUTE:
            out_value = blocks * self.minutes_per_block
        elif blocks is not None and to_unit == CityScaleUnit.HOUR:
            out_value = blocks * self.minutes_per_block * hours_per_minute
        elif blocks is not None and to_unit == CityScaleUnit.KM:
            out_value = (
                blocks
                * self.minutes_per_block
                * hours_per_minute
                * self.mean_vehicle_speed
            )
        elif blocks is not None and to_unit == CityScaleUnit.BLOCK:
            out_value = blocks

        # convert rates to per_block
        if from_unit == CityScaleUnit.PER_BLOCK:
            per_block = in_value
        elif from_unit == CityScaleUnit.PER_MINUTE:
            per_block = in_value * self.minutes_per_block
        elif from_unit == CityScaleUnit.PER_HOUR:
            per_block = in_value * (self.minutes_per_block * hours_per_minute)
        elif from_unit == CityScaleUnit.PER_KM:
            per_block = in_value * (
                self.mean_vehicle_speed * hours_per_minute * self.minutes_per_block
            )
        # Convert from per_block to out_value
        if per_block is not None and to_unit == CityScaleUnit.PER_BLOCK:
            out_value = per_block
        elif per_block is not None and to_unit == CityScaleUnit.PER_MINUTE:
            out_value = per_block / self.minutes_per_block
        elif per_block is not None and to_unit == CityScaleUnit.PER_HOUR:
            out_value = per_block / (self.minutes_per_block * hours_per_minute)
        elif per_block is not None and to_unit == CityScaleUnit.PER_KM:
            out_value = per_block / (
                self.minutes_per_block * hours_per_minute * self.mean_vehicle_speed
            )
        return out_value

    def _update_city_scale_prices(self):
        """
        With use_city_scale, set the per-block price and reservation wage from
        the per-km, per-minute and per-hour inputs. Called when the simulation
        is created and at the start of every block, so live changes to those
        inputs take effect.
        """
        if not self.use_city_scale:
            return
        self.reservation_wage = round(
            self.convert_units(
                self.per_hour_opportunity_cost,
                CityScaleUnit.PER_HOUR,
                CityScaleUnit.PER_BLOCK,
            )
            + self.convert_units(
                self.per_km_ops_cost, CityScaleUnit.PER_KM, CityScaleUnit.PER_BLOCK
            ),
            2,
        )
        self.price = round(
            self.convert_units(
                self.per_minute_price, CityScaleUnit.PER_MINUTE, CityScaleUnit.PER_BLOCK
            )
            + self.convert_units(
                self.per_km_price, CityScaleUnit.PER_KM, CityScaleUnit.PER_BLOCK
            )
            # A base fare is collected once per trip. A busy (P3) vehicle
            # completes 1/mean_trip_distance trips per block, so the base fare
            # adds base_fare / mean_trip_distance to the per-block price.
            # Folding it in here keeps the equilibration utility and every
            # income measure (which all use self.price) correct.
            + (
                self.base_fare / self.mean_trip_distance
                if self.mean_trip_distance
                else 0.0
            ),
            2,
        )

    def _restart_simulation(self):
        """
        Restart the simulation from the beginning, reinitializing all state.
        """
        # Reset block index
        self.block_index = 0

        # Reinitialize vehicles
        self._next_vehicle_index = 0
        self.vehicles = [self._new_vehicle() for _ in range(self.vehicle_count)]

        # Clear trips
        self.trips = {}
        self.next_trip_id = 0
        self.trip_completion_history.clear()
        self._request_capital = 0.0

        # Reset request rate
        self.request_rate = self._demand()

        # Reset adaptive equilibration parameters
        self.damping_factor = 0.5
        self.adaptive_equilibration_interval = 5
        self.previous_vehicle_increment = 0
        self.previous_vehicle_increment_sign = 0
        self.oscillation_count = 0
        self.consecutive_improvements = 0
        self.previous_convergence_residual = float("inf")

        # Clear all history buffers
        # When equilibration_interval == 0 (adaptive mode), use max interval (20)
        # to accommodate dynamic interval changes during simulation
        equilibration_buffer_size = (
            20  # Maximum adaptive interval
            if self.equilibration_interval == 0
            else self.equilibration_interval
        )
        for stat in list(History):
            self.history_buffer[stat] = CircularBuffer(self.smoothing_window)
            self.history_results[stat] = CircularBuffer(self.results_window)
            self.history_equilibration[stat] = CircularBuffer(equilibration_buffer_size)

        # Reset convergence tracker
        self.convergence_tracker = ConvergenceTracker(
            metrics_to_track=self.convergence_metrics,
            chain_length=self.smoothing_window,
            convergence_windows=int(self.results_window / self.smoothing_window) + 1,
        )

    def simulate(self):
        """
        Simulation runner, called from sequence.py and where animation is disabled.
        Uses SimulationRunner for centralized execution logic.
        """
        from ridehail.simulation_runner import SimulationRunner

        runner = SimulationRunner(self)
        return runner.run()

    def next_block(
        self,
        jsonl_file_handle=None,
        csv_file_handle=None,
        block=None,
        return_values=None,
    ):
        """
        Simulate the next block (block number self.block_index), and return
        its state dict (None when run_sequence is set).
        - block: kept for compatibility; leave it out. If given, it must
          equal self.block_index.
        - jsonl_file_handle, csv_file_handle: open output files to write a
          record to (see simulation_runner.SimulationOutput), or None.
        - return_values: "map" adds the vehicles and trips to the state dict.
        """
        if block is None:
            block = self.block_index
        self._init_block(block)
        for vehicle in self.vehicles:
            # Move vehicles
            vehicle.update_location()
        for vehicle in self.vehicles:
            # Update vehicle and trip phases, as needed
            if vehicle.trip_index is not None:
                # If the vehicle arrives at a pickup or dropoff location,
                # update the vehicle and trip phases
                trip = self.trips[vehicle.trip_index]
                if (
                    vehicle.phase == VehiclePhase.P2
                    and vehicle.location == vehicle.pickup_location
                ):
                    # the vehicle has arrived at the pickup spot
                    if vehicle.pickup_countdown is None:
                        # First arrival at pickup location
                        if self.pickup_time > 0:
                            vehicle.pickup_countdown = self.pickup_time
                        else:
                            # Instant pickup (backward compatibility)
                            vehicle.update_phase(to_phase=VehiclePhase.P3)
                            trip.update_phase(to_phase=TripPhase.RIDING)
                    elif vehicle.pickup_countdown > 0:
                        # Decrement countdown each block
                        vehicle.pickup_countdown -= 1
                        if vehicle.pickup_countdown == 0:
                            # Pickup complete, transition phases
                            vehicle.update_phase(to_phase=VehiclePhase.P3)
                            trip.update_phase(to_phase=TripPhase.RIDING)
                            vehicle.pickup_countdown = None
                elif (
                    vehicle.phase == VehiclePhase.P3
                    and vehicle.location == vehicle.dropoff_location
                ):
                    # The vehicle has arrived at the dropoff and the trip ends.
                    # Update vehicle and trip phase to reflect the completion
                    vehicle.update_phase(to_phase=VehiclePhase.P1)
                    trip.update_phase(to_phase=TripPhase.COMPLETED)
        # Using the history from the previous block,
        # equilibrate the supply and/or demand of rides
        if self.equilibration in (
            Equilibration.SUPPLY,
            Equilibration.PRICE,
            Equilibration.WAIT_FRACTION,
        ):
            self._equilibrate_supply(block)
        # Customers make trip requests
        self._request_trips(block)
        # If there are vehicles free, dispatch one to each request
        unassigned_trips = [
            trip for trip in self.trips.values() if trip.phase == TripPhase.UNASSIGNED
        ]
        if len(unassigned_trips) != 0:
            random.shuffle(unassigned_trips)
            self.dispatcher.dispatch_vehicles(
                unassigned_trips, self.city, self.vehicles
            )
        # Cancel any requests that have been open too long
        self._cancel_requests(max_wait_time=self.max_wait_time)
        # Update history for everything that has happened in this block
        for vehicle in self.vehicles:
            # Change direction: this is the direction that will be used in the
            # NEXT block's call to update_location, and so should reflect the
            # phase that the vehicle is now in, and the assignments made in
            # this block.
            # Note: you might think the direction could better be set at the
            # beginning of the next block, but it must be set *before* the next
            # block, so that the interpolated steps in map animations go along
            # the right path.
            vehicle.update_direction()
        self._update_history(block)
        # Some arrays hold information for each trip:
        # compress these as needed to avoid a growing set
        # of completed or cancelled (dead) trips
        self._collect_garbage(block)
        # return values and/or write them out
        if self.run_sequence:
            state_dict = None
        else:
            # create a state_dict with the configuration information and
            # scalar measures such as TRIP_MEAN_PRICE
            state_dict = self._update_state(block)
            if return_values == "map":
                state_dict["vehicles"] = [
                    [
                        vehicle.phase.name,
                        vehicle.location,
                        vehicle.direction.name,
                        vehicle.pickup_countdown,
                    ]
                    for vehicle in self.vehicles
                ]
                # Only UNASSIGNED/WAITING/RIDING trips are ever drawn on the map
                # (see map.js); COMPLETED/CANCELLED/INACTIVE trips linger in
                # self.trips for up to GARBAGE_COLLECTION_INTERVAL blocks, so
                # without this filter the array sent to the browser every frame
                # balloons with entries the frontend immediately discards.
                state_dict["trips"] = [
                    [
                        trip.phase.name,
                        trip.origin,
                        trip.destination,
                        trip.distance,
                    ]
                    for trip in self.trips.values()
                    if trip.phase
                    in (TripPhase.UNASSIGNED, TripPhase.WAITING, TripPhase.RIDING)
                ]
        # Write block record with restructured format
        if self.jsonl_file and jsonl_file_handle and not self.run_sequence:
            # Separate measures from config parameters (only UPPER_CASE keys are measures)
            measures = {k: v for k, v in state_dict.items() if k.isupper()}
            block_record = {
                "type": "block",
                "block": state_dict["block"],
                "measures": measures,
            }
            jsonl_file_handle.write(json.dumps(block_record, default=str) + "\n")

        # CSV output maintains flat structure for backward compatibility
        if self.csv_file and csv_file_handle and not self.run_sequence:
            if block == 0:
                for key in state_dict:
                    csv_file_handle.write(f'"{key}", ')
                csv_file_handle.write("\n")
            for key in state_dict:
                csv_file_handle.write(str(state_dict[key]) + ", ")
            csv_file_handle.write("\n")
        self.block_index += 1
        # return self.block_index
        return state_dict

    def vehicle_utility(self, busy_fraction):
        """
        Vehicle utility per block
            vehicle_utility = (p * (1 - f) * p3 - reservation wage)
        """
        return (
            self.price * (1.0 - self.platform_commission) * busy_fraction
            - self.reservation_wage
        )

    def _set_output_files(self):
        # Always initialize these attributes to avoid AttributeError
        self.jsonl_file = None
        self.csv_file = None

        if self.config_file and self.write_output_files:
            # Only create output files if write_output_files is True
            self.config_file_dir = path.dirname(self.config_file)
            self.config_file_root = path.splitext(path.split(self.config_file)[1])[0]
            if not path.exists("./out"):
                makedirs("./out")
            self.jsonl_file = f"./out/{self.config_file_root}-{self.start_time}.jsonl"
            self.csv_file = f"./out/{self.config_file_root}-{self.start_time}.csv"

    def _validate_options(self):
        """
        For options that have validation constraints, impose them.
        For options that may be overwritten by other options, such
        as when equilibrate=True or use_city_scale=True, overwrite them.
        """
        # city_size must be an even integer. It is normally already even (the
        # city_size ConfigItem has must_be_even=True), but enforce it here too
        # in case the value reached the simulation through another path.
        specified_city_size = self.city_size
        city_size = 2 * int(specified_city_size / 2)
        if city_size != specified_city_size:
            self.city_size = city_size
            # Keep the config in sync so dependent validators (below) see the
            # corrected value.
            self.config.city_size.value = city_size
        # Re-apply the authoritative mean_trip_distance constraint rather than
        # duplicating a clamp here. The single source of truth is
        # config.py::_validate_mean_trip_distance, which caps a value in the
        # band (city_size // 2, city_size] at city_size // 2 and rejects
        # anything above city_size. This also picks up any city_size correction
        # made above.
        is_valid, validated_value, _ = self.config.mean_trip_distance.validate_value(
            self.mean_trip_distance, self.config
        )
        if is_valid:
            if validated_value is not None:
                self.mean_trip_distance = validated_value
        elif self.mean_trip_distance is not None:
            # Value exceeds city_size (would fail config-time validation). Fall
            # back to the maximum sensible value instead of leaving it out of
            # range. Reaching here means the value was set through a path that
            # bypassed config validation. Derive the cap from the same relation
            # the validator uses so the rule lives in exactly one place.
            relation = self.config.mean_trip_distance.max_relation
            base_value = getattr(self, relation["param"])
            self.mean_trip_distance = int(base_value * relation["fraction"])

    def _update_state(self, block):
        """
        Write a json object with the current state to the output file
        """
        state_dict = {}
        if self.title is not None:
            state_dict["title"] = self.title
        state_dict["city_size"] = self.city_size
        state_dict["base_demand"] = self.display_base_demand
        # TODO: vehicle_count should be reset?
        # state_dict["vehicle_count"] = self.vehicle_count
        state_dict["vehicle_count"] = len(self.vehicles)
        state_dict["inhomogeneity"] = self.inhomogeneity
        state_dict["min_trip_distance"] = self.min_trip_distance
        state_dict["mean_trip_distance"] = self.mean_trip_distance
        state_dict["idle_vehicles_moving"] = self.idle_vehicles_moving
        state_dict["idle_vehicles_returning"] = self.idle_vehicles_returning
        state_dict["max_wait_time"] = self.max_wait_time
        state_dict["time_blocks"] = self.time_blocks
        state_dict["price"] = self.price
        state_dict["platform_commission"] = self.platform_commission
        state_dict["reservation_wage"] = self.reservation_wage
        state_dict["demand_elasticity"] = self.demand_elasticity
        state_dict["use_city_scale"] = self.use_city_scale
        state_dict["mean_vehicle_speed"] = self.mean_vehicle_speed
        state_dict["minutes_per_block"] = self.minutes_per_block
        state_dict["per_hour_opportunity_cost"] = self.per_hour_opportunity_cost
        state_dict["per_km_ops_cost"] = self.per_km_ops_cost
        state_dict["per_km_price"] = self.per_km_price
        state_dict["per_minute_price"] = self.per_minute_price
        state_dict["block"] = block
        # The measures are averages over the history buffers, and are exported
        # to any animation or recording output
        # Add to state_dict a set of measures (e.g. TRIP_COMPLETED_FRACTION)
        measures = self._update_measures(block)

        return state_dict | measures

    def _update_measures(self, block):
        """
        The measures are numeric values, built from history_buffer rolling
        averages. Some involve converting to fractions and others are just
        counts. The shared computation (identical for live and end-of-run
        measures, aside from which History buffer/window is used) lives in
        ridehail.measures.compute_measures().

        The keys are the names of the Measure enum, rather than the enum items
        themselves, because these are exported to other domains that may not
        have access to the enum itself (e.g. JavaScript)

        There are a couple of measures (keys in the Measure enum) that are not
        updated here, but are computed only over history windows as part of the
        simulation results. For example, SIM_CHECK_P1_P2_P3. Not updating them
        here causes no problems as they are not included in the History buffers.
        """
        measures = compute_measures(self, self.history_buffer, self.smoothing_window)

        self.convergence_tracker.push_measures(measures)
        # Compute convergence metrics if we have sufficient history
        # Check convergence every smoothing_windoe blocks after minimum warmup
        if block >= self.convergence_tracker.chain_length:
            (max_rms_residual, metric, is_converged) = (
                self.convergence_tracker.max_rms_residual(block)
            )
            # Add convergence metrics using Measure enum for consistency
            measures[Measure.SIM_CONVERGENCE_MAX_RMS_RESIDUAL.name] = max_rms_residual
            measures[Measure.SIM_CONVERGENCE_METRIC.name] = metric.name
            measures[Measure.SIM_IS_CONVERGED.name] = is_converged
            measures[Measure.SIM_BLOCKS_SIMULATED.name] = self.block_index
        return measures

    def _request_trips(self, block):
        """
        Periodically initiate a request from an inactive rider
        For requests not assigned a vehicle, repeat the request.
        """
        requests_this_block = int(self._request_capital)
        for trip in range(requests_this_block):
            trip = Trip(
                self.next_trip_id,
                self.city,
                min_trip_distance=self.min_trip_distance,
                mean_trip_distance=self.mean_trip_distance,
                trip_distance_distribution=self.trip_distance_distribution,
            )
            self.trips[self.next_trip_id] = trip
            self.next_trip_id += 1
            # the trip has a random origin and destination
            # and is ready to make a request.
            # This sets the trip to TripPhase.UNASSIGNED
            # as no vehicle is assigned here
            trip.update_phase(TripPhase.UNASSIGNED)

    def _cancel_requests(self, max_wait_time=None):
        """
        If a request has been waiting too long, cancel it.
        """
        if max_wait_time:
            unassigned_trips = [
                trip
                for trip in self.trips.values()
                if trip.phase == TripPhase.UNASSIGNED
            ]
            for trip in unassigned_trips:
                if trip.phase_time[TripPhase.UNASSIGNED] >= max_wait_time:
                    trip.update_phase(to_phase=TripPhase.CANCELLED)

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
        # Apply the pending live changes, then clear them. Keys that are not
        # simulation attributes (e.g. the "block" key carried in impulse_list
        # entries) are ignored.
        pending, self.target_state = self.target_state, {}
        for key, target_value in pending.items():
            if not hasattr(self, key):
                continue
            if getattr(self, key) != target_value:
                setattr(self, key, target_value)
                if key == "equilibration":
                    self.changed_plotstat_flag = True
                if key == "idle_vehicles_moving":
                    for vehicle in self.vehicles:
                        vehicle.idle_vehicles_moving = target_value
                if key in ("dispatch_method", "forward_dispatch_bias"):
                    # Keep any offer_filter / offline set by the caller
                    self.dispatcher.dispatch_method = self.dispatch_method
                    self.dispatcher.forward_dispatch_bias = self.forward_dispatch_bias

        # Additional actions to accommodate new values
        self.city.city_size = self.city_size
        self.city.inhomogeneity = self.inhomogeneity
        self.city.idle_vehicles_returning = self.idle_vehicles_returning
        self._update_city_scale_prices()
        self.request_rate = self._demand()
        # Reposition the vehicles within the city boundaries
        for vehicle in self.vehicles:
            for i in [0, 1]:
                vehicle.location[i] = vehicle.location[i] % self.city_size
        # Likewise for trips: reposition origins and destinations
        # within the city boundaries
        # PERFORMANCE: Only process active trips (skip COMPLETED/CANCELLED/INACTIVE)
        for trip in self.trips.values():
            if trip.phase in (
                TripPhase.COMPLETED,
                TripPhase.CANCELLED,
                TripPhase.INACTIVE,
            ):
                continue
            for i in [0, 1]:
                trip.origin[i] = trip.origin[i] % self.city_size
                trip.destination[i] = trip.destination[i] % self.city_size
        # Add or remove vehicles and requests
        # for non-equilibrating simulations only
        if self.equilibration == Equilibration.NONE:
            # Update the request rate to reflect the base demand
            old_vehicle_count = len(self.vehicles)
            vehicle_diff = self.vehicle_count - old_vehicle_count
            if vehicle_diff > 0:
                for d in range(vehicle_diff):
                    self.vehicles.append(self._new_vehicle())
            elif vehicle_diff < 0:
                self._remove_vehicles(-vehicle_diff)
        # Set trips that were completed last move to be 'inactive' for
        # the beginning of this one
        for trip in self.trips.values():
            if trip.phase in (TripPhase.COMPLETED, TripPhase.CANCELLED):
                trip.phase = TripPhase.INACTIVE

    def _update_history(self, block):
        """
        Called after each block to update history statistics.

        The history statistics represent two kinds of things:
        - some (eg VEHICLE_COUNT, TRIP_REQUEST_RATE) track the current state of
          a variable throughout a simulation
        - others (eg VEHICLE_TIME_P1, TRIP_DISTANCE) are cumulative values
          incremented over the entire run
        - TRIP_WAIT_FRACTION is an average and probably should not be trusted.
          Fortunately, animation does not use it - I think it is just written
          out in end_state.

        All averaging and smoothing is done in the animation function
        Animation._update_plot_arrays, which uses History functions over
        the smoothing_window (sometimes differences, sometimes sums).
        """
        # vehicle count and request rate are filled in anew each block
        this_block_value = {}
        for history_item in list(History):
            this_block_value[history_item] = 0.0
        this_block_value[History.SIM_CONVERGENCE_MAX_RMS_RESIDUAL] = (
            self.convergence_tracker.max_rms_residual(block)[0]
        )
        this_block_value[History.VEHICLE_COUNT] = len(self.vehicles)
        this_block_value[History.TRIP_REQUEST_RATE] = self.request_rate
        this_block_value[History.TRIP_PRICE] = self.price
        self._request_capital = self._request_capital % 1 + self.request_rate
        # history[History.REQUEST_CAPITAL] = (
        # (history[History.REQUEST_CAPITAL][block - 1] % 1) +
        # self.request_rate)
        if len(self.vehicles) > 0:
            for vehicle in self.vehicles:
                this_block_value[History.VEHICLE_TIME] += 1
                if vehicle.phase == VehiclePhase.P1:
                    this_block_value[History.VEHICLE_TIME_P1] += 1
                elif vehicle.phase == VehiclePhase.P2:
                    this_block_value[History.VEHICLE_TIME_P2] += 1
                elif vehicle.phase == VehiclePhase.P3:
                    this_block_value[History.VEHICLE_TIME_P3] += 1
                else:
                    logging.error(
                        f"Invalid phase {vehicle.phase}: All vehicles must "
                        "be in phase P1, P2, or P3"
                    )
        if self.trips:
            # PERFORMANCE: Only process active trips (skip INACTIVE
            #  to avoid iterating over dead trips)
            for trip in self.trips.values():
                phase = trip.phase
                if phase == TripPhase.INACTIVE:
                    continue
                trip.phase_time[phase] += 1
                if phase == TripPhase.UNASSIGNED:
                    pass
                elif phase == TripPhase.WAITING:
                    pass
                elif phase == TripPhase.RIDING:
                    this_block_value[History.TRIP_RIDING_TIME] += 1
                elif phase == TripPhase.COMPLETED:
                    # Many trip statistics are evaluated at completion.
                    # As the trip is deleted following the block in which
                    # it is completed, each trip should be in the phase
                    # TripPhase.COMPLETED for only one block
                    this_block_value[History.TRIP_COUNT] += 1
                    this_block_value[History.TRIP_COMPLETED_COUNT] += 1
                    this_block_value[History.TRIP_DISTANCE] += trip.distance
                    this_block_value[History.TRIP_AWAITING_TIME] += trip.phase_time[
                        TripPhase.WAITING
                    ]
                    this_block_value[History.TRIP_UNASSIGNED_TIME] += trip.phase_time[
                        TripPhase.UNASSIGNED
                    ]
                    # Bad name: WAIT_TIME = WAITING + UNASSIGNED
                    trip_wait_time = (
                        trip.phase_time[TripPhase.UNASSIGNED]
                        + trip.phase_time[TripPhase.WAITING]
                    )
                    this_block_value[History.TRIP_WAIT_TIME] += trip_wait_time
                    self.trip_completion_history.append(
                        (block, trip_wait_time, trip.distance)
                    )
                    if self.dispatch_method == DispatchMethod.FORWARD_DISPATCH:
                        if trip.forward_dispatch:
                            this_block_value[History.TRIP_FORWARD_DISPATCH_COUNT] += 1
                elif phase == TripPhase.CANCELLED:
                    # Cancelled trips are still counted as trips,
                    # just not as completed trips
                    this_block_value[History.TRIP_COUNT] += 1
                # Note: INACTIVE trips are skipped at loop start (line 1223)
        # Evict trip_completion_history entries older than results_window
        # blocks, even on blocks where no trip completed.
        while (
            self.trip_completion_history
            and block - self.trip_completion_history[0][0] > self.results_window
        ):
            self.trip_completion_history.popleft()
        # Update the rolling averages as well
        for stat in list(History):
            self.history_buffer[stat].push(this_block_value[stat])
        for stat in list(History):
            self.history_results[stat].push(this_block_value[stat])
        for stat in list(History):
            self.history_equilibration[stat].push(this_block_value[stat])

    def _collect_garbage(self, block):
        """
        Garbage collect the dictionary of trips to get rid of the completed,
        cancelled, and inactive ones.

        With dictionary-based storage, trip IDs are permanent so no need to
        update vehicle.trip_index or trip.index references.
        """
        if block % GARBAGE_COLLECTION_INTERVAL == 0:
            self.trips = {
                trip_id: trip
                for trip_id, trip in self.trips.items()
                if trip.phase
                not in [TripPhase.COMPLETED, TripPhase.CANCELLED, TripPhase.INACTIVE]
            }

    def _new_vehicle(self):
        """A new vehicle, with the next unused index."""
        vehicle = Vehicle(
            self._next_vehicle_index, self.city, self.idle_vehicles_moving
        )
        self._next_vehicle_index += 1
        return vehicle

    def _remove_vehicles(self, number_to_remove):
        """
        Remove 'number_to_remove' vehicles from self.vehicles.
        Only removes P1 (idle) vehicles: the first ones in the list.
        The vehicles that remain keep their order, so frame-to-frame displays
        that match vehicles by position move as few of them as possible.
        Returns the number of vehicles actually removed.
        """
        p1_vehicles = [v for v in self.vehicles if v.phase == VehiclePhase.P1]
        # Determine how many P1 vehicles we can actually remove
        vehicles_to_remove = int(min(number_to_remove, len(p1_vehicles)))
        removed = set(p1_vehicles[:vehicles_to_remove])
        self.vehicles = [v for v in self.vehicles if v not in removed]
        return vehicles_to_remove

    def _equilibrate_supply(self, block):
        """
        Change the vehicle count and request rate to move the system
        towards equilibrium.

        When equilibration_interval == 0, uses adaptive convergence management:
        - Dynamically adjusts update interval based on convergence state
        - Adaptively adjusts damping factor to prevent oscillations
        - Detects and responds to oscillatory behavior
        - Uses gain scheduling for state-dependent control (Phase 2)
        """
        # Determine effective equilibration interval
        # equilibration_interval == 0 enables adaptive mode
        if self.equilibration_interval == 0:
            # Adaptive mode: adjust interval based on convergence state
            (max_rms_residual, metric, is_converged) = (
                self.convergence_tracker.max_rms_residual(block)
            )

            # Adaptive interval: shorter when far from equilibrium, longer when converged
            if is_converged:
                self.adaptive_equilibration_interval = 20  # Infrequent when stable
            elif max_rms_residual > 0.1:
                self.adaptive_equilibration_interval = (
                    3  # Frequent when far from target
                )
            else:
                self.adaptive_equilibration_interval = 7  # Moderate during transition

            effective_interval = self.adaptive_equilibration_interval

            # Phase 2: Gain Scheduling - adjust damping based on convergence state
            # Different control strategies for different operating regimes
            if is_converged:
                # Very small adjustments when at equilibrium to prevent over-correction
                effective_damping = self.damping_factor * 0.2
                gain_schedule = "converged (0.2x)"
            elif max_rms_residual > 0.15:
                # Aggressive adjustments when far from equilibrium for faster convergence
                effective_damping = self.damping_factor * 1.5
                gain_schedule = "far (1.5x)"
            else:
                # Normal adjustments during transition region
                effective_damping = self.damping_factor
                gain_schedule = "transition (1.0x)"

            # Log gain scheduling decisions at DEBUG level
            logging.debug(
                f"Block {block}: Gain schedule={gain_schedule}, "
                f"base_damping={self.damping_factor:.3f}, "
                f"effective_damping={effective_damping:.3f}, "
                f"residual={max_rms_residual:.4f}"
            )
        else:
            # Traditional fixed mode
            effective_interval = self.equilibration_interval
            effective_damping = self.damping_factor

        # Check if it's time to equilibrate
        if (block % effective_interval == 0) and block >= max(
            self.city_size, effective_interval
        ):
            old_vehicle_count = len(self.vehicles)
            vehicle_increment = 0
            if self.equilibration == Equilibration.PRICE:
                total_vehicle_time = self.history_equilibration[
                    History.VEHICLE_TIME
                ].sum
                p3_fraction = (
                    self.history_equilibration[History.VEHICLE_TIME_P3].sum
                    / total_vehicle_time
                )
                vehicle_utility = self.vehicle_utility(p3_fraction)
                # Use round() instead of int() to properly handle fractional increments
                # This fixes equilibration for small vehicle counts where int() truncates to 0
                vehicle_increment = round(
                    effective_damping * old_vehicle_count * vehicle_utility
                )
            elif self.equilibration == Equilibration.WAIT_FRACTION:
                if self.history_buffer[History.TRIP_DISTANCE].sum > 0.0:
                    current_wait_fraction = float(
                        self.history_buffer[History.TRIP_WAIT_TIME].sum
                    ) / float(
                        self.history_buffer[History.TRIP_DISTANCE].sum
                        + self.history_buffer[History.TRIP_WAIT_TIME].sum
                    )
                    target_wait_fraction = self.wait_fraction
                    # If the current_wait_fraction is larger than the target_wait_fraction,
                    # then we need more cars on the road to lower wait times, and vice versa.
                    # Use round() instead of int() to properly handle fractional increments
                    vehicle_increment = round(
                        effective_damping
                        * old_vehicle_count
                        * (current_wait_fraction - target_wait_fraction)
                    )

            # Adaptive mode: oscillation detection and damping adjustment
            if self.equilibration_interval == 0 and vehicle_increment != 0:
                # Get current convergence residual for improvement tracking
                current_residual = self.convergence_tracker.max_rms_residual(block)[0]

                # Detect oscillations by tracking sign changes
                current_sign = 1 if vehicle_increment > 0 else -1
                if (
                    self.previous_vehicle_increment_sign != 0
                    and current_sign != self.previous_vehicle_increment_sign
                ):
                    # Sign changed - potential oscillation
                    self.oscillation_count += 1

                    if self.oscillation_count >= 3:
                        # Sustained oscillation detected - increase damping
                        self.damping_factor = min(2.0, self.damping_factor * 1.5)
                        self.oscillation_count = 0  # Reset counter
                        logging.info(
                            f"Block {block}: Oscillation detected, "
                            f"increased damping to {self.damping_factor:.3f}"
                        )
                else:
                    # No sign change - reset oscillation counter
                    self.oscillation_count = 0

                # Track convergence improvement for damping reduction
                if current_residual < self.previous_convergence_residual * 0.95:
                    # Significant improvement - count it
                    self.consecutive_improvements += 1

                    if self.consecutive_improvements >= 2:
                        # Multiple improvements - can decrease damping for faster convergence
                        self.damping_factor = max(0.05, self.damping_factor * 0.7)
                        self.consecutive_improvements = 0
                        logging.info(
                            f"Block {block}: Convergence improving, "
                            f"decreased damping to {self.damping_factor:.3f}"
                        )
                else:
                    # No improvement - reset counter
                    self.consecutive_improvements = 0

                # Update tracking variables
                self.previous_vehicle_increment = vehicle_increment
                self.previous_vehicle_increment_sign = current_sign
                self.previous_convergence_residual = current_residual

            # whichever equilibration is chosen, we now have a vehicle increment
            # so add or remove vehicles as needed
            if vehicle_increment > 0:
                # Cap at 10% of vehicle count, but allow at least 1 vehicle change
                max_increment = max(1, round(0.1 * old_vehicle_count))
                vehicle_increment = min(vehicle_increment, max_increment)
                self.vehicles += [self._new_vehicle() for _ in range(vehicle_increment)]
            elif vehicle_increment < 0:
                # Cap at -10% of vehicle count, but allow at least -1 vehicle change
                min_increment = min(-1, -round(0.1 * old_vehicle_count))
                vehicle_increment = max(vehicle_increment, min_increment)
                self._remove_vehicles(-vehicle_increment)

    def _demand(self):
        """
        Return demand (request_rate):
           request_rate = base_demand * price ^ (-elasticity)
        """
        demand = self.base_demand
        if self.equilibration != Equilibration.NONE or self.use_city_scale:
            demand *= self.price ** (-self.demand_elasticity)
        return demand

    @property
    def display_base_demand(self):
        """base_demand in user-facing units: trips/min when use_city_scale, trips/block otherwise."""
        return self.demand_to_display(self.base_demand)

    def demand_to_display(self, demand):
        """A demand in internal units (trips/block) in user-facing units."""
        if self.use_city_scale:
            return self.convert_units(
                demand, CityScaleUnit.PER_BLOCK, CityScaleUnit.PER_MINUTE
            )
        return demand

    def demand_from_display(self, demand):
        """
        A demand in user-facing units (trips/min when use_city_scale,
        trips/block otherwise) in internal units, e.g. for a live update:
        sim.target_state["base_demand"] = sim.demand_from_display(value).
        """
        if self.use_city_scale:
            return self.convert_units(
                demand, CityScaleUnit.PER_MINUTE, CityScaleUnit.PER_BLOCK
            )
        return demand
