"""
A simulation
"""

import logging
import random
import json
import numpy as np
from os import path, makedirs
import sys
import select
from datetime import datetime

# Conditional imports for terminal functionality (not available in all environments)
try:
    import termios
    import tty
    TERMIOS_AVAILABLE = True
except ImportError:
    # Pyodide/browser environment or Windows - termios not available
    termios = None
    tty = None
    TERMIOS_AVAILABLE = False
from ridehail.dispatch import Dispatch
from ridehail.atom import (
    Animation,
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
from ridehail.config import WritableConfig


GARBAGE_COLLECTION_INTERVAL = 200
# Log the block every LOG_INTERVAL blocks
LOG_INTERVAL = 10


class KeyboardHandler:
    """
    Centralized keyboard handler for simulation controls.
    Works in both text mode (non-blocking) and UI mode (event-based).
    """

    def __init__(self, simulation):
        self.sim = simulation
        self.is_paused = False
        self.should_quit = False
        self.original_terminal_settings = None
        self._setup_terminal()

    def _setup_terminal(self):
        """Setup terminal for non-blocking keyboard input (Unix/Linux/macOS only)"""
        if not TERMIOS_AVAILABLE:
            self.original_terminal_settings = None
            return

        try:
            if sys.stdin.isatty():
                self.original_terminal_settings = termios.tcgetattr(sys.stdin)
                tty.setraw(sys.stdin.fileno())
        except (OSError, Exception):
            # Environment where termios is not functional
            self.original_terminal_settings = None

    def restore_terminal(self):
        """Restore original terminal settings"""
        if self.original_terminal_settings and TERMIOS_AVAILABLE:
            try:
                termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.original_terminal_settings)
            except Exception:
                pass

    def check_keyboard_input(self, timeout=0.0):
        """
        Check for keyboard input without blocking.
        Returns True if input was processed, False otherwise.
        """
        if not TERMIOS_AVAILABLE or not sys.stdin.isatty() or self.original_terminal_settings is None:
            return False

        try:
            # Use select to check if input is available
            ready, _, _ = select.select([sys.stdin], [], [], timeout)
            if ready:
                char = sys.stdin.read(1)
                return self._handle_key(char)
        except (OSError, ValueError, KeyboardInterrupt):
            # Handle various errors or Ctrl+C
            self.should_quit = True
            return True

        return False

    def _handle_key(self, key):
        """
        Handle keyboard input with centralized simulation controls.
        Returns True if key was processed, False otherwise.
        """
        if key == 'q' or key == '\x03':  # 'q' or Ctrl+C
            self.should_quit = True
            print("\nQuitting simulation...")
            return True

        elif key == ' ':  # Space - pause/resume
            self.is_paused = not self.is_paused
            status = "PAUSED" if self.is_paused else "RESUMED"
            print(f"\nSimulation {status}")
            return True

        elif key == 'n':  # Decrease vehicles by 1
            if "vehicle_count" not in self.sim.target_state:
                self.sim.target_state["vehicle_count"] = self.sim.vehicle_count
            self.sim.target_state["vehicle_count"] = max(
                self.sim.target_state["vehicle_count"] - 1, 0
            )
            print(f"\nVehicles: {self.sim.target_state['vehicle_count']}")
            return True

        elif key == 'N':  # Increase vehicles by 1
            if "vehicle_count" not in self.sim.target_state:
                self.sim.target_state["vehicle_count"] = self.sim.vehicle_count
            self.sim.target_state["vehicle_count"] += 1
            print(f"\nVehicles: {self.sim.target_state['vehicle_count']}")
            return True

        elif key == 'k':  # Decrease demand by 0.1
            if "base_demand" not in self.sim.target_state:
                self.sim.target_state["base_demand"] = self.sim.base_demand
            self.sim.target_state["base_demand"] = max(
                self.sim.target_state["base_demand"] - 0.1, 0
            )
            print(f"\nBase demand: {self.sim.target_state['base_demand']:.1f}")
            return True

        elif key == 'K':  # Increase demand by 0.1
            if "base_demand" not in self.sim.target_state:
                self.sim.target_state["base_demand"] = self.sim.base_demand
            self.sim.target_state["base_demand"] += 0.1
            print(f"\nBase demand: {self.sim.target_state['base_demand']:.1f}")
            return True

        elif key == 'd':  # Decrease animation delay by 0.05s
            current_delay = self.sim.config.animation_delay.value
            if current_delay is None:
                current_delay = self.sim.config.animation_delay.default
            new_delay = max(current_delay - 0.05, 0.0)
            self.sim.config.animation_delay.value = new_delay
            print(f"\nAnimation delay: {new_delay:.2f}s")
            return True

        elif key == 'D':  # Increase animation delay by 0.05s
            current_delay = self.sim.config.animation_delay.value
            if current_delay is None:
                current_delay = self.sim.config.animation_delay.default
            new_delay = current_delay + 0.05
            self.sim.config.animation_delay.value = new_delay
            print(f"\nAnimation delay: {new_delay:.2f}s")
            return True

        elif key == 'h' or key == '?':  # Help
            self._print_help()
            return True

        return False

    def _print_help(self):
        """Print keyboard controls help"""
        print("\n" + "="*50)
        print("KEYBOARD CONTROLS:")
        print("  q       - Quit simulation")
        print("  space   - Pause/Resume simulation")
        print("  n/N     - Decrease/Increase vehicles by 1")
        print("  k/K     - Decrease/Increase demand by 0.1")
        print("  d/D     - Decrease/Increase animation delay by 0.05s")
        print("  h/?     - Show this help")
        print("="*50)

    def handle_ui_action(self, action, value=None):
        """
        Handle UI actions from animation modules.
        This allows animations to use the same centralized control logic.
        """
        if action == "pause":
            self.is_paused = not self.is_paused
            return self.is_paused

        elif action == "quit":
            self.should_quit = True
            return True

        elif action == "decrease_vehicles":
            if "vehicle_count" not in self.sim.target_state:
                self.sim.target_state["vehicle_count"] = self.sim.vehicle_count
            self.sim.target_state["vehicle_count"] = max(
                self.sim.target_state["vehicle_count"] - (value or 1), 0
            )
            return self.sim.target_state["vehicle_count"]

        elif action == "increase_vehicles":
            if "vehicle_count" not in self.sim.target_state:
                self.sim.target_state["vehicle_count"] = self.sim.vehicle_count
            self.sim.target_state["vehicle_count"] += (value or 1)
            return self.sim.target_state["vehicle_count"]

        elif action == "decrease_demand":
            if "base_demand" not in self.sim.target_state:
                self.sim.target_state["base_demand"] = self.sim.base_demand
            self.sim.target_state["base_demand"] = max(
                self.sim.target_state["base_demand"] - (value or 0.1), 0
            )
            return self.sim.target_state["base_demand"]

        elif action == "increase_demand":
            if "base_demand" not in self.sim.target_state:
                self.sim.target_state["base_demand"] = self.sim.base_demand
            self.sim.target_state["base_demand"] += (value or 0.1)
            return self.sim.target_state["base_demand"]

        elif action == "decrease_animation_delay":
            current_delay = self.sim.config.animation_delay.value
            if current_delay is None:
                current_delay = self.sim.config.animation_delay.default
            new_delay = max(current_delay - (value or 0.05), 0.0)
            self.sim.config.animation_delay.value = new_delay
            return new_delay

        elif action == "increase_animation_delay":
            current_delay = self.sim.config.animation_delay.value
            if current_delay is None:
                current_delay = self.sim.config.animation_delay.default
            new_delay = current_delay + (value or 0.05)
            self.sim.config.animation_delay.value = new_delay
            return new_delay

        return None


class CircularBuffer:
    """
    Class to hold arrays to do smoothing averages
    From
    https://stackoverflow.com/questions/42771110/fastest-way-to-left-cycle-a-numpy-array-like-pop-push-for-a-queue

    Oddly enough, this class pushes new values on to the tail, and drops them
    from the head. Think of it like appending to the tail of a file.
    """

    def __init__(self, maxlen: int):
        # allocate the memory we need ahead of time
        self._max_length: int = maxlen
        self._queue_tail: int = maxlen - 1
        self._rec_queue = np.zeros(maxlen)
        self.sum = np.sum(self._rec_queue)

    def _enqueue(self, new_data: np.array) -> None:
        # move tail pointer forward then insert at the tail of the queue
        # to enforce max length of recording
        self._queue_tail = (self._queue_tail + 1) % self._max_length
        self._rec_queue[self._queue_tail] = new_data

    def _get_head(self) -> int:
        queue_head = (self._queue_tail + 1) % self._max_length
        return self._rec_queue[queue_head]

    def _get_tail(self) -> int:
        return self._rec_queue[self._queue_tail]

    def push(self, new_data: np.array) -> float:
        """
        Add an item to the buffer, and update the sum
        """
        head = self._get_head()
        self._enqueue(new_data)
        tail = self._get_tail()
        self.sum += tail - head

    def __repr__(self):
        return "tail: " + str(self._queue_tail) + "\narray: " + str(self._rec_queue)

    def __str__(self):
        return "tail: " + str(self._queue_tail) + "\narray: " + str(self._rec_queue)
        # return str(self.to_array())


class RideHailSimulation:
    """
    Simulate a ridehail environment, with vehicles and trips
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
        if config.config_file.value:
            self.config_file = config.config_file.value
        else:
            self.config_file = None
        self.start_time = config.start_time
        self.city_size = config.city_size.value
        self.inhomogeneity = config.inhomogeneity.value
        self.inhomogeneous_destinations = config.inhomogeneous_destinations.value
        self.city = City(
            self.city_size,
            inhomogeneity=self.inhomogeneity,
            inhomogeneous_destinations=self.inhomogeneous_destinations,
        )
        self.base_demand = config.base_demand.value
        self.vehicle_count = config.vehicle_count.value
        self.min_trip_distance = config.min_trip_distance.value
        # self.max_trip_distance = config.max_trip_distance.value
        self.max_trip_distance = (
            config.city_size.value
            if config.max_trip_distance.value is None
            else config.max_trip_distance.value
        )
        self.idle_vehicles_moving = config.idle_vehicles_moving.value
        self.time_blocks = config.time_blocks.value
        self.results_window = config.results_window.value
        self.animate = config.animate.value
        self.animation_style = config.animation_style.value
        self.animation_output_file = config.animation_output_file.value
        self.interpolate = config.interpolate.value
        self.smoothing_window = config.smoothing_window.value
        self.annotation = config.annotation.value
        self.equilibrate = config.equilibrate.value
        self.run_sequence = config.run_sequence.value
        self.use_city_scale = config.use_city_scale.value
        self.equilibration = config.equilibration.value
        self.wait_fraction = config.wait_fraction.value
        self.price = config.price.value
        self.platform_commission = config.platform_commission.value
        self.reservation_wage = config.reservation_wage.value
        self.demand_elasticity = config.demand_elasticity.value
        self.equilibration_interval = config.equilibration_interval.value
        self.impulse_list = config.impulse_list.value
        self.mean_vehicle_speed = config.mean_vehicle_speed.value
        self.minutes_per_block = config.minutes_per_block.value
        self.per_hour_opportunity_cost = config.per_hour_opportunity_cost.value
        self.per_km_ops_cost = config.per_km_ops_cost.value
        self.per_km_price = config.per_km_price.value
        self.per_minute_price = config.per_minute_price.value
        self.use_advanced_dispatch = config.use_advanced_dispatch.value
        self.dispatch_method = config.dispatch_method.value
        self.forward_dispatch_bias = config.forward_dispatch_bias.value
        self._set_output_files()
        self._validate_options()
        for attr in dir(self):
            option = getattr(self, attr)
            if callable(option) or attr.startswith("__"):
                continue
            if attr not in ("target_state",):
                self.target_state[attr] = option
        # Following items not set in config
        self.block_index = 0
        self.request_rate = self._demand()
        self.trips = {}
        self.next_trip_id = 0
        self.vehicles = [
            Vehicle(i, self.city, self.idle_vehicles_moving)
            for i in range(self.vehicle_count)
        ]
        self.request_capital = 0.0
        self.changed_plotstat_flag = False
        # If we change a simulation parameter interactively, the new value
        # is stored in self.target_state, and the new values of the
        # actual parameters are updated at the beginning of the next block.
        # This set is expanding as the program gets more complex.
        # (todays_date-datetime.timedelta(10), time_blocks=10, freq='D')
        #
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
        # history_equilibration is used to provide values to drive equilibration,
        # averaged or summed over a window of size equilibration_interval
        self.history_equilibration = {}
        for stat in list(History):
            self.history_equilibration[stat] = CircularBuffer(
                self.equilibration_interval
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
        if blocks and to_unit == CityScaleUnit.MINUTE:
            out_value = blocks * self.minutes_per_block
        elif blocks and to_unit == CityScaleUnit.HOUR:
            out_value = blocks * self.minutes_per_block * hours_per_minute
        elif blocks and to_unit == CityScaleUnit.KM:
            out_value = (
                blocks
                * self.minutes_per_block
                * hours_per_minute
                * self.mean_vehicle_speed
            )
        elif blocks and to_unit == CityScaleUnit.BLOCK:
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

        if self.animation_style not in (
            Animation.MAP,
            Animation.ALL,
            Animation.TERMINAL_MAP,
        ):
            # Interpolation is relevant only if the map is displayed
            self.interpolate = 0
        if (
            self.animation_style
            in (Animation.MAP, Animation.STATS, Animation.BAR, Animation.ALL)
            and self.animation_output_file
        ):
            if self.animation_output_file.endswith(
                "mp4"
            ) or self.animation_output_file.endswith(".gif"):
                # turn off actual animation during the simulation
                self.animation_style = Animation.NONE
            else:
                self.animation_output_file = None

        if self.inhomogeneity:
            # Default 0, must be between 0 and 1
            if self.inhomogeneity < 0.0 or self.inhomogeneity > 1.0:
                self.inhomogeneity = max(min(self.inhomogeneity, 1.0), 0.0)
        # inhomogeneous destinations overrides max_trip_distance
        if self.inhomogeneous_destinations and self.max_trip_distance < self.city_size:
            self.max_trip_distance = None
            logging.info(
                "inhomogeneous_destinations overrides max_trip_distance\n"
                f"max_trip_distance reset to {self.max_trip_distance}"
            )

        # use_city_scale overwrites reservation_wage and price
        if self.use_city_scale:
            self.reservation_wage = round(
                (
                    self.convert_units(
                        self.per_hour_opportunity_cost,
                        CityScaleUnit.PER_HOUR,
                        CityScaleUnit.PER_BLOCK,
                    )
                    + self.convert_units(
                        self.per_km_ops_cost,
                        CityScaleUnit.PER_KM,
                        CityScaleUnit.PER_BLOCK,
                    )
                ),
                2,
            )
            self.price = round(
                (
                    self.convert_units(
                        self.per_minute_price,
                        CityScaleUnit.PER_MINUTE,
                        CityScaleUnit.PER_BLOCK,
                    )
                    + self.convert_units(
                        self.per_km_price, CityScaleUnit.PER_KM, CityScaleUnit.PER_BLOCK
                    )
                ),
                2,
            )

    def simulate(self):
        """
        Plot the trend of cumulative cases, observed at
        earlier days, evolving over time.
        """
        import time

        # Setup keyboard handler for interactive controls
        keyboard_handler = KeyboardHandler(self)

        try:
            dispatch = Dispatch(self.dispatch_method, self.forward_dispatch_bias)
            results = RideHailSimulationResults(self)
            # write out the config information, if appropriate
            if self.jsonl_file or self.csv_file:
                jsonl_file_handle = (
                    open(f"{self.jsonl_file}", "a") if self.jsonl_file else None
                )
                csv_exists = False
                if self.csv_file and path.exists(self.csv_file):
                    csv_exists = True
                csv_file_handle = open(f"{self.csv_file}", "a") if self.csv_file else None
            else:
                csv_file_handle = None
                jsonl_file_handle = None
            output_dict = {}
            output_dict["config"] = WritableConfig(self.config).__dict__
            if self.jsonl_file and jsonl_file_handle and not self.run_sequence:
                jsonl_file_handle.write(json.dumps(output_dict) + "\n")
                # The configuration information does not get written to the csv file

            # Get animation delay from config for consistent timing across all animation styles
            animation_delay = self.config.animation_delay.value
            if animation_delay is None:
                animation_delay = self.config.animation_delay.default

            # Print keyboard controls help for text-based simulations
            if self.animation_style in (Animation.TEXT, Animation.NONE, "text", "none"):
                print("Press 'h' for keyboard controls help")

            # -----------------------------------------------------------
            # Here is the simulation loop
            if self.time_blocks > 0:
                # time_blocks is the number of time periods to simulate."
                for block in range(self.time_blocks):
                    # Check for quit request
                    if keyboard_handler.should_quit:
                        break

                    # Skip simulation step if paused
                    if not keyboard_handler.is_paused:
                        self.next_block(
                            jsonl_file_handle=jsonl_file_handle,
                            csv_file_handle=csv_file_handle,
                            block=block,
                            dispatch=dispatch,
                        )

                    # Apply animation delay with keyboard input checking
                    if animation_delay > 0:
                        # Check for keyboard input during sleep intervals
                        sleep_chunks = max(1, int(animation_delay / 0.1))  # 100ms chunks
                        chunk_duration = animation_delay / sleep_chunks

                        for _ in range(sleep_chunks):
                            if keyboard_handler.should_quit:
                                break
                            if not keyboard_handler.is_paused:
                                time.sleep(chunk_duration)
                            keyboard_handler.check_keyboard_input(0.0)

                            # If paused, keep checking for input without advancing simulation
                            while keyboard_handler.is_paused and not keyboard_handler.should_quit:
                                keyboard_handler.check_keyboard_input(0.1)
            else:
                # time_blocks = 0: continue indefinitely.
                block = 0
                while not keyboard_handler.should_quit:
                    # Skip simulation step if paused
                    if not keyboard_handler.is_paused:
                        self.next_block(
                            jsonl_file_handle=jsonl_file_handle,
                            csv_file_handle=csv_file_handle,
                            block=block,
                            dispatch=dispatch,
                        )
                        block += 1

                    # Apply animation delay with keyboard input checking
                    if animation_delay > 0:
                        # Check for keyboard input during sleep intervals
                        sleep_chunks = max(1, int(animation_delay / 0.1))  # 100ms chunks
                        chunk_duration = animation_delay / sleep_chunks

                        for _ in range(sleep_chunks):
                            if keyboard_handler.should_quit:
                                break
                            if not keyboard_handler.is_paused:
                                time.sleep(chunk_duration)
                            keyboard_handler.check_keyboard_input(0.0)

                            # If paused, keep checking for input without advancing simulation
                            while keyboard_handler.is_paused and not keyboard_handler.should_quit:
                                keyboard_handler.check_keyboard_input(0.1)
        finally:
            # Always restore terminal settings
            keyboard_handler.restore_terminal()
        # -----------------------------------------------------------
        # write out the final results
        # results.end_state = results.compute_end_state()
        results.compute_end_state()
        output_dict["end_state"] = results.end_state
        if self.jsonl_file:
            jsonl_file_handle.write(json.dumps(output_dict) + "\n")
            jsonl_file_handle.close()
        if self.csv_file and self.run_sequence:
            if not csv_exists:
                for key in output_dict["end_state"]:
                    csv_file_handle.write(f'"{key}", ')
                csv_file_handle.write("\n")
            for key in output_dict["end_state"]:
                csv_file_handle.write(str(output_dict["end_state"][key]) + ", ")
            csv_file_handle.write("\n")
        if self.csv_file:
            csv_file_handle.close()
        if self.animate and self.animation_style == Animation.TEXT:
            print("End state:")
            print(json.dumps(output_dict, indent=2, sort_keys=True))
        return results

    def next_block(
        self,
        jsonl_file_handle=None,
        csv_file_handle=None,
        block=None,
        return_values=None,
        dispatch=Dispatch(),
    ):
        """
        Call all those functions needed to simulate the next block
        - block should be supplied if the simulation is run externally,
          rather than from the simulate() method (e.g. when
          running in a browser).
        - jsonl_file_handle should be None if running in a browser.
        """
        if block is None:
            block = self.block_index
        if block % LOG_INTERVAL == 0:
            logging.debug(
                f"-------"
                f" Block {block} at"
                f" {datetime.now().strftime('%Y-%m-%d-%H:%M:%S.%f')[:-4]}"
                f" -------"
            )
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
                    # the vehicle has arrived at the pickup spot and picks up
                    # the rider
                    vehicle.update_phase(to_phase=VehiclePhase.P3)
                    trip.update_phase(to_phase=TripPhase.RIDING)
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
        if self.equilibrate and self.equilibration in (
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
            dispatch.dispatch_vehicles(unassigned_trips, self.city, self.vehicles)
        # Cancel any requests that have been open too long
        self._cancel_requests(max_wait_time=None)
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
                    [vehicle.phase.name, vehicle.location, vehicle.direction.name]
                    for vehicle in self.vehicles
                ]
                state_dict["trips"] = []
                if len(self.trips) > 0:
                    state_dict["trips"] = [
                        [
                            trip.phase.name,
                            trip.origin,
                            trip.destination,
                            trip.distance,
                            # trip.phase_time
                        ]
                        for trip in self.trips.values()
                    ]
        #
        # Update vehicle utilization stats
        # self._update_vehicle_utilization_stats()
        #
        if self.jsonl_file and jsonl_file_handle and not self.run_sequence:
            jsonl_file_handle.write(json.dumps(state_dict) + "\n")
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

        if self.config_file:
            # Sometimes, eg in tests, you don't want to use a config_file
            # but you still want the jsonl_file and csv_file for output,
            # so supply the config_file argument even though use_config_file
            # might be false, so that you can create jsonl_file and csv_file
            # handles for output
            self.config_file_dir = path.dirname(self.config_file)
            self.config_file_root = path.splitext(path.split(self.config_file)[1])[0]
            if not path.exists("./output"):
                makedirs("./output")
            self.jsonl_file = (
                f"./output/{self.config_file_root}-{self.start_time}.jsonl"
            )
            self.csv_file = f"./output/{self.config_file_root}-{self.start_time}.csv"

    def _validate_options(self):
        """
        For options that have validation constraints, impose them.
        For options that may be overwritten by other options, such
        as when equilibrate=True or use_city_scale=True, overwrite them.
        """
        # city_size
        specified_city_size = self.city_size
        city_size = 2 * int(specified_city_size / 2)
        if city_size != specified_city_size:
            # City size must be an even integer: reset.
            self.city_size = city_size
            # max_trip_distance
            if self.max_trip_distance == specified_city_size:
                self.max_trip_distance = None

    def _update_state(self, block):
        """
        Write a json object with the current state to the output file
        """
        state_dict = {}
        state_dict["city_size"] = self.city_size
        state_dict["base_demand"] = self.base_demand
        # TODO: vehicle_count should be reset?
        # state_dict["vehicle_count"] = self.vehicle_count
        state_dict["vehicle_count"] = len(self.vehicles)
        state_dict["inhomogeneity"] = self.inhomogeneity
        state_dict["min_trip_distance"] = self.min_trip_distance
        state_dict["max_trip_distance"] = self.max_trip_distance
        state_dict["idle_vehicles_moving"] = self.idle_vehicles_moving
        state_dict["time_blocks"] = self.time_blocks
        state_dict["equilibrate"] = self.equilibrate
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
        # Combine state_dict and measures. This operator was introduced in
        # Python 3.9
        if sys.version_info >= (3, 9):
            state_dict = state_dict | measures  # NOTE: 3.9+ ONLY
        else:
            # Python 3.5 or later
            state_dict = {**state_dict, **measures}
        if self.animate and self.animation_style == Animation.TEXT:
            s = (
                f"block {block:5d}: cs={self.city_size:3d}, "
                f"N={measures[Measure.VEHICLE_MEAN_COUNT.name]:.2f}, "
                f"R={measures[Measure.TRIP_MEAN_REQUEST_RATE.name]:.2f}, "
                f"P1={measures[Measure.VEHICLE_FRACTION_P1.name]:.2f}, "
                f"P2={measures[Measure.VEHICLE_FRACTION_P2.name]:.2f}, "
                f"P3={measures[Measure.VEHICLE_FRACTION_P3.name]:.2f}, "
                f"W={measures[Measure.TRIP_MEAN_WAIT_TIME.name]:.2f} min"
            )
            print(f"\r{s}", end="", flush=True)
        return state_dict

    def _update_measures(self, block):
        """
        The measures are numeric values, built from history_buffer rolling
        averages. Some involve converting to fractions and others are just
        counts.  Treat each one individually here.

        The keys are the names of the Measure enum, rather than the enum items
        themselves, because these are exported to other domains that may not
        have access to the enum itself (e.g. JavaScript)
        """
        window = self.smoothing_window
        measure = {}
        for item in list(Measure):
            measure[item.name] = 0
        measure[Measure.TRIP_SUM_COUNT.name] = float(
            self.history_buffer[History.TRIP_COUNT].sum
        )
        measure[Measure.VEHICLE_MEAN_COUNT.name] = (
            float(self.history_buffer[History.VEHICLE_COUNT].sum) / window
        )
        measure[Measure.TRIP_MEAN_REQUEST_RATE.name] = (
            float(self.history_buffer[History.TRIP_REQUEST_RATE].sum) / window
        )
        measure[Measure.TRIP_MEAN_PRICE.name] = (
            float(self.history_buffer[History.TRIP_PRICE].sum) / window
        )
        measure[Measure.VEHICLE_SUM_TIME.name] = float(
            self.history_buffer[History.VEHICLE_TIME].sum
        )
        if measure[Measure.VEHICLE_SUM_TIME.name] > 0:
            measure[Measure.VEHICLE_FRACTION_P1.name] = (
                float(self.history_buffer[History.VEHICLE_TIME_P1].sum)
                / measure[Measure.VEHICLE_SUM_TIME.name]
            )
            measure[Measure.VEHICLE_FRACTION_P2.name] = (
                float(self.history_buffer[History.VEHICLE_TIME_P2].sum)
                / measure[Measure.VEHICLE_SUM_TIME.name]
            )
            measure[Measure.VEHICLE_FRACTION_P3.name] = (
                float(self.history_buffer[History.VEHICLE_TIME_P3].sum)
                / measure[Measure.VEHICLE_SUM_TIME.name]
            )
            measure[Measure.VEHICLE_GROSS_INCOME.name] = (
                self.price
                * (1.0 - self.platform_commission)
                * measure[Measure.VEHICLE_FRACTION_P3.name]
            )
            # if use_city_scale is false, net income is same as gross
            measure[Measure.VEHICLE_NET_INCOME.name] = (
                self.price
                * (1.0 - self.platform_commission)
                * measure[Measure.VEHICLE_FRACTION_P3.name]
            )
            measure[Measure.VEHICLE_MEAN_SURPLUS.name] = self.vehicle_utility(
                measure[Measure.VEHICLE_FRACTION_P3.name]
            )
        if measure[Measure.TRIP_SUM_COUNT.name] > 0:
            measure[Measure.TRIP_MEAN_WAIT_TIME.name] = (
                float(self.history_buffer[History.TRIP_WAIT_TIME].sum)
                / measure[Measure.TRIP_SUM_COUNT.name]
            )
            measure[Measure.TRIP_MEAN_RIDE_TIME.name] = (
                # float(self.history_buffer[History.TRIP_RIDING_TIME].sum) /
                float(self.history_buffer[History.TRIP_DISTANCE].sum)
                / measure[Measure.TRIP_SUM_COUNT.name]
            )
            measure[Measure.TRIP_MEAN_WAIT_FRACTION.name] = (
                measure[Measure.TRIP_MEAN_WAIT_TIME.name]
                / measure[Measure.TRIP_MEAN_RIDE_TIME.name]
            )
            measure[Measure.TRIP_MEAN_WAIT_FRACTION_TOTAL.name] = measure[
                Measure.TRIP_MEAN_WAIT_TIME.name
            ] / (
                measure[Measure.TRIP_MEAN_RIDE_TIME.name]
                + measure[Measure.TRIP_MEAN_WAIT_TIME.name]
            )
            measure[Measure.TRIP_DISTANCE_FRACTION.name] = measure[
                Measure.TRIP_MEAN_RIDE_TIME.name
            ] / float(self.city_size)
            measure[Measure.PLATFORM_MEAN_INCOME.name] = (
                self.price
                * self.platform_commission
                * measure[Measure.TRIP_SUM_COUNT.name]
                * measure[Measure.TRIP_MEAN_RIDE_TIME.name]
                / window
            )
            if self.dispatch_method == DispatchMethod.FORWARD_DISPATCH:
                measure[Measure.TRIP_FORWARD_DISPATCH_FRACTION.name] = (
                    float(self.history_buffer[History.TRIP_FORWARD_DISPATCH_COUNT].sum)
                    / measure[Measure.TRIP_SUM_COUNT.name]
                )
        # print(
        # f"block={block}: p1={measure[Measure.VEHICLE_FRACTION_P1.name]}, "
        # f"ucs={self.use_city_scale}")

        if self.use_city_scale:
            measure[Measure.TRIP_MEAN_PRICE.name] = self.convert_units(
                measure[Measure.TRIP_MEAN_PRICE.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_MINUTE,
            )
            measure[Measure.TRIP_MEAN_WAIT_TIME.name] = self.convert_units(
                measure[Measure.TRIP_MEAN_WAIT_TIME.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_MINUTE,
            )
            measure[Measure.TRIP_MEAN_RIDE_TIME.name] = self.convert_units(
                measure[Measure.TRIP_MEAN_RIDE_TIME.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_MINUTE,
            )
            measure[Measure.VEHICLE_GROSS_INCOME.name] = self.convert_units(
                measure[Measure.VEHICLE_GROSS_INCOME.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_HOUR,
            )
            measure[Measure.VEHICLE_NET_INCOME.name] = measure[
                Measure.VEHICLE_GROSS_INCOME.name
            ] - self.convert_units(
                self.per_km_ops_cost, CityScaleUnit.PER_KM, CityScaleUnit.PER_HOUR
            )
            measure[Measure.PLATFORM_MEAN_INCOME.name] = self.convert_units(
                measure[Measure.PLATFORM_MEAN_INCOME.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_HOUR,
            )
            measure[Measure.VEHICLE_MEAN_SURPLUS.name] = self.convert_units(
                measure[Measure.VEHICLE_MEAN_SURPLUS.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_HOUR,
            )
            measure[Measure.TRIP_MEAN_PRICE.name] = self.convert_units(
                measure[Measure.TRIP_MEAN_PRICE.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_MINUTE,
            )
        return measure

    def _update_vehicle_utilization_stats(self):
        # Currently experimental: for analysing distribution of utilization
        for v in self.vehicles:
            v.utilization[v.phase] += 1
            v.utilization["total"] += 1

    def _request_trips(self, block):
        """
        Periodically initiate a request from an inactive rider
        For requests not assigned a vehicle, repeat the request.
        """
        requests_this_block = int(self.request_capital)
        for trip in range(requests_this_block):
            trip = Trip(
                self.next_trip_id,
                self.city,
                min_trip_distance=self.min_trip_distance,
                max_trip_distance=self.max_trip_distance,
            )
            self.trips[self.next_trip_id] = trip
            self.next_trip_id += 1
            logging.debug((f"Request: trip {trip.origin} -> {trip.destination}"))
            # the trip has a random origin and destination
            # and is ready to make a request.
            # This sets the trip to TripPhase.UNASSIGNED
            # as no vehicle is assigned here
            trip.update_phase(TripPhase.UNASSIGNED)
        if requests_this_block > 0:
            logging.debug(
                (
                    f"Block {block}: "
                    f"rate {self.request_rate:.02f}: "
                    f"{requests_this_block} request(s) this block."
                )
            )

    def _cancel_requests(self, max_wait_time=None):
        """
        If a request has been waiting too long, cancel it.
        """
        if max_wait_time:
            unassigned_trips = [
                trip for trip in self.trips.values() if trip.phase == TripPhase.UNASSIGNED
            ]
            for trip in unassigned_trips:
                if trip.phase_time[TripPhase.UNASSIGNED] >= max_wait_time:
                    trip.update_phase(to_phase=TripPhase.CANCELLED)
                    logging.debug(
                        (
                            f"Trip {trip.index} cancelled after "
                            f"{trip.phase_time[TripPhase.UNASSIGNED]} blocks."
                        )
                    )

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
            if (
                callable(attr)
                or attr.startswith("__")
                or attr not in self.target_state.keys()
            ):
                continue
            if val != self.target_state[attr]:
                setattr(self, attr, self.target_state[attr])
                if attr == "equilibrate":
                    self.changed_plotstat_flag = True

        # Additional actions to accommidate new values
        self.city.city_size = self.city_size
        self.city.inhomogeneity = self.inhomogeneity
        if self.use_city_scale:
            # This code cot and pasted from validate_options
            # Recalculate the reservation wage and price
            self.reservation_wage = round(
                (
                    self.convert_units(
                        self.per_hour_opportunity_cost,
                        CityScaleUnit.PER_HOUR,
                        CityScaleUnit.PER_BLOCK,
                    )
                    + self.convert_units(
                        self.per_km_ops_cost,
                        CityScaleUnit.PER_KM,
                        CityScaleUnit.PER_BLOCK,
                    )
                ),
                2,
            )
            self.price = round(
                (
                    self.convert_units(
                        self.per_minute_price,
                        CityScaleUnit.PER_MINUTE,
                        CityScaleUnit.PER_BLOCK,
                    )
                    + self.convert_units(
                        self.per_km_price, CityScaleUnit.PER_KM, CityScaleUnit.PER_BLOCK
                    )
                ),
                2,
            )
        self.request_rate = self._demand()
        # Reposition the vehicles within the city boundaries
        for vehicle in self.vehicles:
            for i in [0, 1]:
                vehicle.location[i] = vehicle.location[i] % self.city_size
        # Likewise for trips: reposition origins and destinations
        # within the city boundaries
        for trip in self.trips.values():
            for i in [0, 1]:
                trip.origin[i] = trip.origin[i] % self.city_size
                trip.destination[i] = trip.destination[i] % self.city_size
        # Add or remove vehicles and requests
        # for non-equilibrating simulations only
        if not self.equilibrate or self.equilibration == Equilibration.NONE:
            # Update the request rate to reflect the base demand
            old_vehicle_count = len(self.vehicles)
            vehicle_diff = self.vehicle_count - old_vehicle_count
            if vehicle_diff > 0:
                for d in range(vehicle_diff):
                    self.vehicles.append(
                        Vehicle(
                            old_vehicle_count + d, self.city, self.idle_vehicles_moving
                        )
                    )
            elif vehicle_diff < 0:
                removed_vehicles = self._remove_vehicles(-vehicle_diff)
                logging.debug(f"Period start: removed {removed_vehicles} vehicles.")
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
        this_block_value[History.VEHICLE_COUNT] = len(self.vehicles)
        this_block_value[History.TRIP_REQUEST_RATE] = self.request_rate
        this_block_value[History.TRIP_PRICE] = self.price
        self.request_capital = self.request_capital % 1 + self.request_rate
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
        if self.trips:
            for trip in self.trips.values():
                phase = trip.phase
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
                    if self.dispatch_method == DispatchMethod.FORWARD_DISPATCH:
                        if trip.forward_dispatch:
                            this_block_value[History.TRIP_FORWARD_DISPATCH_COUNT] += 1
                elif phase == TripPhase.CANCELLED:
                    # Cancelled trips are still counted as trips,
                    # just not as completed trips
                    this_block_value[History.TRIP_COUNT] += 1
                elif phase == TripPhase.INACTIVE:
                    # do nothing with INACTIVE trips
                    pass
        # Update the rolling averages as well
        for stat in list(History):
            self.history_buffer[stat].push(this_block_value[stat])
        for stat in list(History):
            self.history_results[stat].push(this_block_value[stat])
        for stat in list(History):
            self.history_equilibration[stat].push(this_block_value[stat])
        json_string = f'{{"block": {block}'
        for array_name, array in self.history_buffer.items():
            json_string += f', "{array_name}": {array}'
        json_string += "}"
        logging.debug(f"Simulation History: {json_string}\n")

    def _collect_garbage(self, block):
        """
        Garbage collect the dictionary of trips to get rid of the completed and
        cancelled ones.

        With dictionary-based storage, trip IDs are permanent so no need to
        update vehicle.trip_index or trip.index references.
        """
        if block % GARBAGE_COLLECTION_INTERVAL == 0:
            self.trips = {
                trip_id: trip
                for trip_id, trip in self.trips.items()
                if trip.phase not in [TripPhase.COMPLETED, TripPhase.CANCELLED]
            }

    def _remove_vehicles(self, number_to_remove):
        """
        Remove 'number_to_remove' vehicles from self.vehicles.
        Returns the number of vehicles removed
        """
        vehicles_removed = 0
        for i, vehicle in enumerate(self.vehicles):
            if vehicle.phase == VehiclePhase.P1:
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
        if (block % self.equilibration_interval == 0) and block >= max(
            self.city_size, self.equilibration_interval
        ):
            # only equilibrate at certain times
            # lower_bound = max((block - self.equilibration_interval), 0)
            # equilibration_blocks = (blocks - lower_bound)
            old_vehicle_count = len(self.vehicles)
            vehicle_increment = 0
            if self.equilibration == Equilibration.PRICE:
                damping_factor = 0.8
                total_vehicle_time = self.history_equilibration[
                    History.VEHICLE_TIME
                ].sum
                p3_fraction = (
                    self.history_equilibration[History.VEHICLE_TIME_P3].sum
                    / total_vehicle_time
                )
                vehicle_utility = self.vehicle_utility(p3_fraction)
                vehicle_increment = int(
                    damping_factor * old_vehicle_count * vehicle_utility
                )
                logging.debug(
                    (
                        f"Equilibrating: {{'block': {block}, "
                        f"'P3': {p3_fraction:.02f}, "
                        f"'vehicle_utility': {vehicle_utility:.02f}, "
                        f"'increment': {vehicle_increment}, "
                        f"'old count': {old_vehicle_count}, "
                        f"'new count': {len(self.vehicles)}}}"
                    )
                )
            elif self.equilibration == Equilibration.WAIT_FRACTION:
                if self.history_buffer[History.TRIP_DISTANCE].sum > 0.0:
                    damping_factor = 0.2
                    current_wait_fraction = float(
                        self.history_buffer[History.TRIP_WAIT_TIME].sum
                    ) / float(self.history_buffer[History.TRIP_DISTANCE].sum)
                    target_wait_fraction = self.wait_fraction
                    # If the current_wait_fraction is larger than the target_wait_fraction,
                    # then we need more cars on the road to lower the wait times. And vice versa.
                    # Sharing the damping factor with price equilibration led to be oscillations
                    vehicle_increment = int(
                        damping_factor
                        * old_vehicle_count
                        * (current_wait_fraction - target_wait_fraction)
                    )
                    logging.debug(
                        (
                            f"Equilibrating: {{'block': {block}, "
                            f"'wait_fraction': {current_wait_fraction:.02f}, "
                            f"'target_wait_fraction': {target_wait_fraction:.02f}, "
                            f"'old count': {old_vehicle_count}}}"
                        )
                    )
            # whichever equilibration is chosen, we now have a vehicle increment
            # so add or remove vehicles as needed
            if vehicle_increment > 0:
                vehicle_increment = min(vehicle_increment, int(0.1 * old_vehicle_count))
                self.vehicles += [
                    Vehicle(i, self.city, self.idle_vehicles_moving)
                    for i in range(
                        old_vehicle_count, old_vehicle_count + vehicle_increment
                    )
                ]
            elif vehicle_increment < 0:
                vehicle_increment = max(vehicle_increment, -0.1 * old_vehicle_count)
                self._remove_vehicles(-vehicle_increment)

    def _demand(self):
        """
        Return demand (request_rate):
           request_rate = base_demand * price ^ (-elasticity)
        """
        demand = self.base_demand
        if self.equilibrate or self.use_city_scale:
            demand *= self.price ** (-self.demand_elasticity)
        return demand

    def get_keyboard_handler(self):
        """
        Get or create a keyboard handler for this simulation.
        Used by animations to access centralized keyboard controls.
        """
        if not hasattr(self, '_keyboard_handler'):
            self._keyboard_handler = KeyboardHandler(self)
        return self._keyboard_handler


class RideHailSimulationResults:
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
        config["inhomogeneity"] = self.sim.city.inhomogeneity
        config["min_trip_distance"] = self.sim.min_trip_distance
        config["max_trip_distance"] = self.sim.max_trip_distance
        config["time_blocks"] = self.sim.time_blocks
        config["request_rate"] = self.sim.request_rate
        config["results_window"] = self.sim.results_window
        config["idle_vehicles_moving"] = self.sim.idle_vehicles_moving
        config["animate"] = self.sim.animate
        config["equilibrate"] = self.sim.equilibrate
        config["run_sequence"] = self.sim.run_sequence
        config["dispatch_method"] = self.sim.dispatch_method
        self.results["config"] = config
        if self.sim.equilibrate and self.sim.equilibration != Equilibration.NONE:
            equilibrate = {}
            equilibrate["equilibration"] = self.sim.equilibration.name
            equilibrate["price"] = self.sim.price
            equilibrate["platform_commission"] = self.sim.platform_commission
            equilibrate["equilibration_interval"] = self.sim.equilibration_interval
            if self.sim.equilibrate == Equilibration.PRICE:
                equilibrate["base_demand"] = self.sim.base_demand
                equilibrate["demand_elasticity"] = self.sim.demand_elasticity
            if self.sim.equilibrate in (Equilibration.PRICE, Equilibration.SUPPLY):
                equilibrate["reservation_wage"] = self.sim.reservation_wage
            self.results["equilibrate"] = equilibrate
        self.end_state = {}

    def compute_end_state(self):
        """
        Collect final state, averaged over the final
        sim.results_window blocks of the simulation.

        Use strings for keys instead of enums as this needs to be callable from
        outside environments.
        """
        # check for case where results_window is bigger than time_blocks
        block = self.sim.time_blocks
        block_lower_bound = max((self.sim.time_blocks - self.sim.results_window), 0)
        result_blocks = block - block_lower_bound
        # N and R
        end_state = {}
        end_state["mean_vehicle_count"] = round(
            (self.sim.history_results[History.VEHICLE_COUNT].sum / result_blocks), 3
        )
        end_state["mean_request_rate"] = round(
            (self.sim.history_results[History.TRIP_REQUEST_RATE].sum / result_blocks), 3
        )
        # vehicle history
        total_vehicle_time = round(
            self.sim.history_results[History.VEHICLE_TIME].sum, 3
        )
        if total_vehicle_time > 0:
            end_state["vehicle_fraction_p1"] = round(
                (
                    self.sim.history_results[History.VEHICLE_TIME_P1].sum
                    / total_vehicle_time
                ),
                3,
            )
            end_state["vehicle_fraction_p2"] = round(
                (
                    self.sim.history_results[History.VEHICLE_TIME_P2].sum
                    / total_vehicle_time
                ),
                3,
            )
            end_state["vehicle_fraction_p3"] = round(
                (
                    self.sim.history_results[History.VEHICLE_TIME_P3].sum
                    / total_vehicle_time
                ),
                3,
            )
        # trip history
        total_trip_count = round(self.sim.history_results[History.TRIP_COUNT].sum, 3)
        if total_trip_count > 0:
            end_state["mean_trip_wait_time"] = round(
                (
                    self.sim.history_results[History.TRIP_WAIT_TIME].sum
                    / total_trip_count
                ),
                3,
            )
            end_state["mean_trip_distance"] = round(
                (
                    self.sim.history_results[History.TRIP_DISTANCE].sum
                    / total_trip_count
                ),
                3,
            )
            end_state["trip_distance"] = round(
                self.sim.history_results[History.TRIP_DISTANCE].sum, 3
            )
            end_state["mean_trip_wait_fraction"] = round(
                (end_state["mean_trip_wait_time"] / end_state["mean_trip_distance"]), 3
            )
            end_state["forward_dispatch_fraction"] = round(
                (
                    self.sim.history_results[History.TRIP_FORWARD_DISPATCH_COUNT].sum
                    / total_trip_count
                ),
                3,
            )
            # Checks of result consistency
            end_state["check_np3_over_rl"] = round(
                end_state["mean_vehicle_count"]
                * end_state["vehicle_fraction_p3"]
                / (end_state["mean_request_rate"] * end_state["mean_trip_distance"]),
                3,
            )
            end_state["check_np2_over_rw"] = round(
                end_state["mean_vehicle_count"]
                * end_state["vehicle_fraction_p2"]
                / (end_state["mean_request_rate"] * end_state["mean_trip_wait_time"]),
                3,
            )
        end_state["check_p1+p2+p3"] = round(
            end_state["vehicle_fraction_p1"]
            + end_state["vehicle_fraction_p2"]
            + end_state["vehicle_fraction_p3"],
            3,
        )
        self.end_state = end_state
