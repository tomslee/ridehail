"""
A simulation
"""

import logging
import random
import json
from os import path, makedirs
import sys
import select
import socket
from datetime import datetime
import subprocess

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
from ridehail.keyboard_mappings import (
    get_mapping_for_key,
    generate_help_text,
)
from ridehail.convergence import ConvergenceTracker, DEFAULT_CONVERGENCE_METRICS


GARBAGE_COLLECTION_INTERVAL = 50  # Reduced from 200 for better performance
# Log the block every LOG_INTERVAL blocks
LOG_INTERVAL = 10
EQUILIBRATION_DAMPING_FACTOR_PRICE = 0.2
EQUILIBRATION_DAMPING_FACTOR_WAIT = 0.2


class KeyboardHandler:
    """
    Centralized keyboard handler for simulation controls.
    Works in both text mode (non-blocking) and UI mode (event-based).
    """

    def __init__(self, simulation):
        self.sim = simulation
        self.is_paused = False
        self.should_quit = False
        self.should_step = False  # Flag for single-step execution
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
                # Use cbreak mode instead of raw mode to preserve output processing
                # This allows normal print() newlines while still getting non-blocking input
                tty.setcbreak(sys.stdin.fileno())
        except (OSError, Exception):
            # Environment where termios is not functional
            self.original_terminal_settings = None

    def restore_terminal(self):
        """Restore original terminal settings"""
        if self.original_terminal_settings and TERMIOS_AVAILABLE:
            try:
                termios.tcsetattr(
                    sys.stdin, termios.TCSADRAIN, self.original_terminal_settings
                )
            except Exception:
                pass

    def check_keyboard_input(self, timeout=0.0):
        """
        Check for keyboard input without blocking.
        Returns True if input was processed, False otherwise.
        """
        if (
            not TERMIOS_AVAILABLE
            or not sys.stdin.isatty()
            or self.original_terminal_settings is None
        ):
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
        # Handle Ctrl+C separately
        if key == "\x03":
            self.should_quit = True
            return True

        # Look up key mapping
        mapping = get_mapping_for_key(key, platform="terminal")
        if not mapping:
            return False

        # Execute action based on mapping
        action = mapping.action

        if action == "quit":
            self.should_quit = True
            return True

        elif action == "pause":
            self.is_paused = not self.is_paused
            return True

        elif action == "decrease_vehicles":
            if "vehicle_count" not in self.sim.target_state:
                self.sim.target_state["vehicle_count"] = self.sim.vehicle_count
            self.sim.target_state["vehicle_count"] = max(
                self.sim.target_state["vehicle_count"] - mapping.value, 0
            )
            return True

        elif action == "increase_vehicles":
            if "vehicle_count" not in self.sim.target_state:
                self.sim.target_state["vehicle_count"] = self.sim.vehicle_count
            self.sim.target_state["vehicle_count"] += mapping.value
            return True

        elif action == "decrease_demand":
            if "base_demand" not in self.sim.target_state:
                self.sim.target_state["base_demand"] = self.sim.base_demand
            self.sim.target_state["base_demand"] = max(
                self.sim.target_state["base_demand"] - mapping.value, 0
            )
            return True

        elif action == "increase_demand":
            if "base_demand" not in self.sim.target_state:
                self.sim.target_state["base_demand"] = self.sim.base_demand
            self.sim.target_state["base_demand"] += mapping.value
            return True

        elif action == "decrease_animation_delay":
            if "animation_delay" not in self.sim.target_state:
                self.sim.target_state["animation_delay"] = self.sim.animation_delay
            current_delay = self.sim.animation_delay
            new_delay = max(current_delay - mapping.value, 0.0)
            self.sim.target_state["animation_delay"] = new_delay
            self.sim.animation_delay = new_delay
            return True

        elif action == "increase_animation_delay":
            if "animation_delay" not in self.sim.target_state:
                self.sim.target_state["animation_delay"] = self.sim.animation_delay
            current_delay = self.sim.animation_delay
            new_delay = current_delay + mapping.value
            self.sim.target_state["animation_delay"] = new_delay
            self.sim.animation_delay = new_delay
            return True

        elif action == "help":
            self._print_help()
            return True

        elif action == "step":
            # Single step forward (only when paused)
            if self.is_paused:
                self.should_step = True
            return True

        elif action == "restart":
            self.sim._restart_simulation()
            return True

        return False

    def _print_help(self):
        """Print keyboard controls help"""
        # Save current pause state and pause while showing help
        help_previous_pause_state = self.is_paused
        if not self.is_paused:
            self.is_paused = True

        # Display help text
        help_text = generate_help_text(platform="terminal")
        print(f"\n{help_text}")
        print("\nPress any key to continue...")

        # Wait for keypress before continuing
        if TERMIOS_AVAILABLE and sys.stdin.isatty():
            try:
                sys.stdin.read(1)
            except Exception:
                pass

        # Restore previous pause state
        self.is_paused = help_previous_pause_state

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
            self.sim.target_state["vehicle_count"] += value or 1
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
            self.sim.target_state["base_demand"] += value or 0.1
            return self.sim.target_state["base_demand"]

        elif action == "decrease_animation_delay":
            if "animation_delay" not in self.sim.target_state:
                self.sim.target_state["animation_delay"] = self.sim.animation_delay
            current_delay = self.sim.animation_delay
            new_delay = max(current_delay - (value or 0.05), 0.0)
            self.sim.target_state["animation_delay"] = new_delay
            self.sim.animation_delay = new_delay
            return new_delay

        elif action == "increase_animation_delay":
            if "animation_delay" not in self.sim.target_state:
                self.sim.target_state["animation_delay"] = self.sim.animation_delay
            current_delay = self.sim.animation_delay
            new_delay = current_delay + (value or 0.05)
            self.sim.target_state["animation_delay"] = new_delay
            self.sim.animation_delay = new_delay
            return new_delay

        elif action == "step":
            # Single step forward (only when paused)
            if self.is_paused:
                self.should_step = True
            return True

        elif action == "restart":
            self.sim._restart_simulation()
            return True

        return None


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

        self.city = City(
            self.city_size,
            inhomogeneity=self.inhomogeneity,
            inhomogeneous_destinations=self.inhomogeneous_destinations,
        )
        self._set_output_files()
        self._validate_options()
        self.target_state = {}
        for attr in dir(self):
            option = getattr(self, attr)
            if callable(option) or attr.startswith("__"):
                continue
            if attr not in ("target_state",):
                self.target_state[attr] = option
        # Following items not set in config
        if config.random_number_seed.value:
            random.seed(config.random_number_seed.value)
        self.block_index = 0
        self.request_rate = self._demand()
        self.trips = {}
        self.next_trip_id = 0
        self.vehicles = [
            Vehicle(i, self.city, self.idle_vehicles_moving)
            for i in range(self.vehicle_count)
        ]
        self.changed_plotstat_flag = False
        self._request_capital = 0.0
        self._dispatcher = Dispatch(self.dispatch_method, self.forward_dispatch_bias)
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

        if self.animation not in (
            Animation.MAP,
            Animation.ALL,
            Animation.TERMINAL_MAP,
        ):
            # Interpolation is relevant only if the map is displayed
            self.interpolate = 0
        if (
            self.animation
            in (Animation.MAP, Animation.STATS, Animation.BAR, Animation.ALL)
            and self.animation_output_file
        ):
            if self.animation_output_file.endswith(
                "mp4"
            ) or self.animation_output_file.endswith(".gif"):
                # turn off actual animation during the simulation
                self.animation = Animation.NONE
            else:
                self.animation_output_file = None

        if self.inhomogeneity:
            # Default 0, must be between 0 and 1
            if self.inhomogeneity < 0.0 or self.inhomogeneity > 1.0:
                self.inhomogeneity = max(min(self.inhomogeneity, 1.0), 0.0)
        # inhomogeneous destinations overrides max_trip_distance
        if self.inhomogeneous_destinations and self.max_trip_distance < self.city_size:
            self.max_trip_distance = None
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

    def _create_metadata_record(self):
        """
        Create metadata record with provenance information.
        """
        metadata = {
            "type": "metadata",
            "version": self.version,
            "timestamp": datetime.now().isoformat(),
            "python_version": sys.version.split()[0],  # Just version number
        }

        # Add git commit if available
        try:
            git_commit = subprocess.check_output(
                ["git", "rev-parse", "--short", "HEAD"],
                stderr=subprocess.DEVNULL,
                cwd=path.dirname(__file__),
                text=True,
            ).strip()
            metadata["git_commit"] = git_commit
        except (subprocess.CalledProcessError, FileNotFoundError):
            # Git not available or not a git repo
            pass

        # Add hostname
        try:
            metadata["hostname"] = socket.gethostname()
        except Exception:
            pass

        # Add command line
        metadata["command_line"] = " ".join(sys.argv)

        # Add random seed if set
        if self.config.random_number_seed.value:
            metadata["random_seed_used"] = self.config.random_number_seed.value

        return metadata

    def _restart_simulation(self):
        """
        Restart the simulation from the beginning, reinitializing all state.
        """
        # Reset block index
        self.block_index = 0

        # Reinitialize vehicles
        self.vehicles = [
            Vehicle(i, self.city, self.idle_vehicles_moving)
            for i in range(self.vehicle_count)
        ]

        # Clear trips
        self.trips = {}
        self.next_trip_id = 0
        self._request_capital = 0.0

        # Reset request rate
        self.request_rate = self._demand()

        # Clear all history buffers
        for stat in list(History):
            self.history_buffer[stat] = CircularBuffer(self.smoothing_window)
            self.history_results[stat] = CircularBuffer(self.results_window)
            self.history_equilibration[stat] = CircularBuffer(
                self.equilibration_interval
            )

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
        Call all those functions needed to simulate the next block
        - block should be supplied if the simulation is run externally,
          rather than from the simulate() method (e.g. when
          running in a browser).
        - jsonl_file_handle should be None if running in a browser.
        """
        if block is None:
            block = self.block_index
        if block % LOG_INTERVAL == 0:
            pass
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
            self._dispatcher.dispatch_vehicles(
                unassigned_trips, self.city, self.vehicles
            )
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
                    [
                        vehicle.phase.name,
                        vehicle.location,
                        vehicle.direction.name,
                        vehicle.pickup_countdown,
                    ]
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

    def _flatten_end_state(self, end_state):
        """
        Flatten hierarchical end_state structure for CSV compatibility.
        Phase 1 enhancement helper method.
        """
        flat = {}
        if isinstance(end_state, dict):
            for section, values in end_state.items():
                if isinstance(values, dict):
                    for key, value in values.items():
                        # Create flat key like "vehicles_mean_count"
                        flat_key = f"{section}_{key}"
                        flat[flat_key] = value
                else:
                    flat[section] = values
        return flat

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
        if self.title is not None:
            state_dict["title"] = self.title
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
        return state_dict

    def _update_measures(self, block):
        """
        The measures are numeric values, built from history_buffer rolling
        averages. Some involve converting to fractions and others are just
        counts.  Treat each one individually here.

        The keys are the names of the Measure enum, rather than the enum items
        themselves, because these are exported to other domains that may not
        have access to the enum itself (e.g. JavaScript)

        There are a couple of measures (keys in the Measure enum) that are not
        updated here, but are computed only over history windows as part of the
        simulation results. For example, SIM_CHECK_P1_P2_P3. Not updating them
        here causes no problems as they are not included in the History buffers.
        """
        window = self.smoothing_window
        measures = {}
        for item in list(Measure):
            measures[item.name] = 0

        measures[Measure.TRIP_SUM_COUNT.name] = float(
            self.history_buffer[History.TRIP_COUNT].sum
        )
        measures[Measure.VEHICLE_MEAN_COUNT.name] = (
            float(self.history_buffer[History.VEHICLE_COUNT].sum) / window
        )
        measures[Measure.TRIP_MEAN_REQUEST_RATE.name] = (
            float(self.history_buffer[History.TRIP_REQUEST_RATE].sum) / window
        )
        measures[Measure.TRIP_MEAN_PRICE.name] = (
            float(self.history_buffer[History.TRIP_PRICE].sum) / window
        )
        measures[Measure.VEHICLE_SUM_TIME.name] = float(
            self.history_buffer[History.VEHICLE_TIME].sum
        )
        if measures[Measure.VEHICLE_SUM_TIME.name] > 0:
            measures[Measure.VEHICLE_FRACTION_P1.name] = (
                float(self.history_buffer[History.VEHICLE_TIME_P1].sum)
                / measures[Measure.VEHICLE_SUM_TIME.name]
            )
            measures[Measure.VEHICLE_FRACTION_P2.name] = (
                float(self.history_buffer[History.VEHICLE_TIME_P2].sum)
                / measures[Measure.VEHICLE_SUM_TIME.name]
            )
            measures[Measure.VEHICLE_FRACTION_P3.name] = (
                float(self.history_buffer[History.VEHICLE_TIME_P3].sum)
                / measures[Measure.VEHICLE_SUM_TIME.name]
            )
            measures[Measure.VEHICLE_GROSS_INCOME.name] = (
                self.price
                * (1.0 - self.platform_commission)
                * measures[Measure.VEHICLE_FRACTION_P3.name]
            )
            # if use_city_scale is false, net income is same as gross
            measures[Measure.VEHICLE_NET_INCOME.name] = (
                self.price
                * (1.0 - self.platform_commission)
                * measures[Measure.VEHICLE_FRACTION_P3.name]
            )
            measures[Measure.VEHICLE_MEAN_SURPLUS.name] = self.vehicle_utility(
                measures[Measure.VEHICLE_FRACTION_P3.name]
            )
        if measures[Measure.TRIP_SUM_COUNT.name] > 0:
            measures[Measure.TRIP_MEAN_WAIT_TIME.name] = (
                float(self.history_buffer[History.TRIP_WAIT_TIME].sum)
                / measures[Measure.TRIP_SUM_COUNT.name]
            )
            measures[Measure.TRIP_MEAN_RIDE_TIME.name] = (
                # float(self.history_buffer[History.TRIP_RIDING_TIME].sum) /
                float(self.history_buffer[History.TRIP_DISTANCE].sum)
                / measures[Measure.TRIP_SUM_COUNT.name]
            )
            measures[Measure.TRIP_MEAN_WAIT_FRACTION.name] = (
                measures[Measure.TRIP_MEAN_WAIT_TIME.name]
                / measures[Measure.TRIP_MEAN_RIDE_TIME.name]
            )
            measures[Measure.TRIP_MEAN_WAIT_FRACTION_TOTAL.name] = measures[
                Measure.TRIP_MEAN_WAIT_TIME.name
            ] / (
                measures[Measure.TRIP_MEAN_RIDE_TIME.name]
                + measures[Measure.TRIP_MEAN_WAIT_TIME.name]
            )
            measures[Measure.TRIP_DISTANCE_FRACTION.name] = measures[
                Measure.TRIP_MEAN_RIDE_TIME.name
            ] / float(self.city_size)
            measures[Measure.PLATFORM_MEAN_INCOME.name] = (
                self.price
                * self.platform_commission
                * measures[Measure.TRIP_SUM_COUNT.name]
                * measures[Measure.TRIP_MEAN_RIDE_TIME.name]
                / window
            )
            if self.dispatch_method == DispatchMethod.FORWARD_DISPATCH:
                measures[Measure.TRIP_FORWARD_DISPATCH_FRACTION.name] = (
                    float(self.history_buffer[History.TRIP_FORWARD_DISPATCH_COUNT].sum)
                    / measures[Measure.TRIP_SUM_COUNT.name]
                )
        if self.use_city_scale:
            measures[Measure.TRIP_MEAN_PRICE.name] = self.convert_units(
                measures[Measure.TRIP_MEAN_PRICE.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_MINUTE,
            )
            measures[Measure.TRIP_MEAN_WAIT_TIME.name] = self.convert_units(
                measures[Measure.TRIP_MEAN_WAIT_TIME.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_MINUTE,
            )
            measures[Measure.TRIP_MEAN_RIDE_TIME.name] = self.convert_units(
                measures[Measure.TRIP_MEAN_RIDE_TIME.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_MINUTE,
            )
            measures[Measure.VEHICLE_GROSS_INCOME.name] = self.convert_units(
                measures[Measure.VEHICLE_GROSS_INCOME.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_HOUR,
            )
            measures[Measure.VEHICLE_NET_INCOME.name] = measures[
                Measure.VEHICLE_GROSS_INCOME.name
            ] - self.convert_units(
                self.per_km_ops_cost, CityScaleUnit.PER_KM, CityScaleUnit.PER_HOUR
            )
            measures[Measure.PLATFORM_MEAN_INCOME.name] = self.convert_units(
                measures[Measure.PLATFORM_MEAN_INCOME.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_HOUR,
            )
            measures[Measure.VEHICLE_MEAN_SURPLUS.name] = self.convert_units(
                measures[Measure.VEHICLE_MEAN_SURPLUS.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_HOUR,
            )
            measures[Measure.TRIP_MEAN_PRICE.name] = self.convert_units(
                measures[Measure.TRIP_MEAN_PRICE.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_MINUTE,
            )

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
        requests_this_block = int(self._request_capital)
        for trip in range(requests_this_block):
            trip = Trip(
                self.next_trip_id,
                self.city,
                min_trip_distance=self.min_trip_distance,
                max_trip_distance=self.max_trip_distance,
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
                if attr == "equilibration":
                    self.changed_plotstat_flag = True

        # Additional actions to accommodate new values
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
                    self.vehicles.append(
                        Vehicle(
                            old_vehicle_count + d, self.city, self.idle_vehicles_moving
                        )
                    )
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
                    if self.dispatch_method == DispatchMethod.FORWARD_DISPATCH:
                        if trip.forward_dispatch:
                            this_block_value[History.TRIP_FORWARD_DISPATCH_COUNT] += 1
                elif phase == TripPhase.CANCELLED:
                    # Cancelled trips are still counted as trips,
                    # just not as completed trips
                    this_block_value[History.TRIP_COUNT] += 1
                # Note: INACTIVE trips are skipped at loop start (line 1223)
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

    def _remove_vehicles(self, number_to_remove):
        """
        Remove 'number_to_remove' vehicles from self.vehicles.
        Only removes P1 (idle) vehicles.
        Returns the number of vehicles actually removed.
        """
        p1_vehicles = [v for v in self.vehicles if v.phase == VehiclePhase.P1]
        non_p1_vehicles = [v for v in self.vehicles if v.phase != VehiclePhase.P1]

        # Determine how many P1 vehicles we can actually remove
        vehicles_to_remove = int(min(number_to_remove, len(p1_vehicles)))

        # Keep all non-P1 vehicles and only the P1 vehicles we're not removing
        self.vehicles = non_p1_vehicles + p1_vehicles[vehicles_to_remove:]

        return vehicles_to_remove

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
                    EQUILIBRATION_DAMPING_FACTOR_PRICE
                    * old_vehicle_count
                    * vehicle_utility
                )
            elif self.equilibration == Equilibration.WAIT_FRACTION:
                if self.history_buffer[History.TRIP_DISTANCE].sum > 0.0:
                    current_wait_fraction = float(
                        self.history_buffer[History.TRIP_WAIT_TIME].sum
                    ) / float(self.history_buffer[History.TRIP_DISTANCE].sum)
                    target_wait_fraction = self.wait_fraction
                    # If the current_wait_fraction is larger than the target_wait_fraction,
                    # then we need more cars on the road to lower the wait times. And vice versa.
                    # Sharing the damping factor with price equilibration led to be oscillations
                    # Use round() instead of int() to properly handle fractional increments
                    vehicle_increment = round(
                        EQUILIBRATION_DAMPING_FACTOR_WAIT
                        * old_vehicle_count
                        * (current_wait_fraction - target_wait_fraction)
                    )
            # whichever equilibration is chosen, we now have a vehicle increment
            # so add or remove vehicles as needed
            if vehicle_increment > 0:
                # Cap at 10% of vehicle count, but allow at least 1 vehicle change
                max_increment = max(1, round(0.1 * old_vehicle_count))
                vehicle_increment = min(vehicle_increment, max_increment)
                self.vehicles += [
                    Vehicle(i, self.city, self.idle_vehicles_moving)
                    for i in range(
                        old_vehicle_count, old_vehicle_count + vehicle_increment
                    )
                ]
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

    def get_keyboard_handler(self):
        """
        Get or create a keyboard handler for this simulation.
        Used by animations to access centralized keyboard controls.
        """
        if not hasattr(self, "_keyboard_handler"):
            self._keyboard_handler = KeyboardHandler(self)
        return self._keyboard_handler
