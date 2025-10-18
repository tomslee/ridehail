"""
Text-based animation for ridehail simulation.

Provides simple text output to stdout, showing:
- Current simulation state on each block (single line, updated in place)
- Final results as JSON at completion
"""

import json
import time
from ridehail.animation.base import RideHailAnimation
from ridehail.simulation import KeyboardHandler, RideHailSimulationResults
from ridehail.config import WritableConfig
from ridehail.atom import Measure
from os import path


class TextAnimation(RideHailAnimation):
    """
    Simple text-based animation that prints simulation state to stdout.

    Displays a single line showing current block and key metrics, updated in place.
    At completion, prints the full end state as formatted JSON.
    """

    def __init__(self, sim):
        super().__init__(sim)
        # Track previous state for detecting keyboard action effects
        self._prev_vehicle_count = None
        self._prev_base_demand = None
        self._prev_animation_delay = None

    def animate(self):
        """
        Run the simulation with text output.

        Prints:
        - Keyboard controls help at start
        - Current state on each block (updated in place)
        - Final results as JSON at completion
        """
        # Setup keyboard handler for interactive controls
        keyboard_handler = KeyboardHandler(self.sim)

        try:
            results = RideHailSimulationResults(self.sim)

            # write out the config information, if appropriate
            if self.sim.jsonl_file or self.sim.csv_file:
                jsonl_file_handle = (
                    open(f"{self.sim.jsonl_file}", "a") if self.sim.jsonl_file else None
                )
                csv_exists = False
                if self.sim.csv_file and path.exists(self.sim.csv_file):
                    csv_exists = True
                csv_file_handle = (
                    open(f"{self.sim.csv_file}", "a") if self.sim.csv_file else None
                )
            else:
                csv_file_handle = None
                jsonl_file_handle = None

            output_dict = {}
            output_dict["config"] = WritableConfig(self.sim.config).__dict__
            if self.sim.jsonl_file and jsonl_file_handle and not self.sim.run_sequence:
                jsonl_file_handle.write(json.dumps(output_dict) + "\n")
                # The configuration information does not get written to the csv file

            # -----------------------------------------------------------
            # Here is the simulation loop
            if self.sim.time_blocks > 0:
                # time_blocks is the number of time periods to simulate.
                # Use while loop instead of for loop to support restart
                block = 0
                while block < self.sim.time_blocks and not keyboard_handler.should_quit:
                    # Check for restart request (block_index was reset to 0)
                    if self.sim.block_index == 0 and block > 0:
                        # Restart detected - reset block counter
                        block = 0
                        print("\r[Restarted simulation]", end="", flush=True)
                        # Reset tracked state for clean feedback after restart
                        self._prev_vehicle_count = None
                        self._prev_base_demand = None
                        self._prev_animation_delay = None

                    # Check for keyboard action effects and print feedback
                    self._check_and_print_keyboard_actions(keyboard_handler)

                    # Execute simulation step if not paused, or if single-stepping
                    if not keyboard_handler.is_paused or keyboard_handler.should_step:
                        state_dict = self.sim.next_block(
                            jsonl_file_handle=jsonl_file_handle,
                            csv_file_handle=csv_file_handle,
                            block=block,
                        )
                        # Print current state
                        self._print_state(state_dict, block)

                        # Increment block counter after successful step
                        block += 1

                        # Reset step flag after executing single step
                        if keyboard_handler.should_step:
                            keyboard_handler.should_step = False

                    # Get current animation delay (may have been changed by keyboard)
                    animation_delay = self.sim.config.animation_delay.value
                    if animation_delay is None:
                        animation_delay = self.sim.config.animation_delay.default

                    # Apply animation delay with keyboard input checking
                    if animation_delay > 0:
                        # Check for keyboard input during sleep intervals
                        sleep_chunks = max(
                            1, int(animation_delay / 0.1)
                        )  # 100ms chunks
                        chunk_duration = animation_delay / sleep_chunks

                        for _ in range(sleep_chunks):
                            if keyboard_handler.should_quit:
                                break
                            if not keyboard_handler.is_paused:
                                time.sleep(chunk_duration)
                            keyboard_handler.check_keyboard_input(0.0)

                            # If paused, keep checking for input without advancing simulation
                            while (
                                keyboard_handler.is_paused
                                and not keyboard_handler.should_quit
                                and not keyboard_handler.should_step
                            ):
                                keyboard_handler.check_keyboard_input(0.1)
                            # Break out of sleep loop if step was requested
                            if keyboard_handler.should_step:
                                break
            else:
                # time_blocks = 0: continue indefinitely.
                block = 0
                while not keyboard_handler.should_quit:
                    # Check for keyboard action effects and print feedback
                    self._check_and_print_keyboard_actions(keyboard_handler)

                    # Execute simulation step if not paused, or if single-stepping
                    if not keyboard_handler.is_paused or keyboard_handler.should_step:
                        state_dict = self.sim.next_block(
                            jsonl_file_handle=jsonl_file_handle,
                            csv_file_handle=csv_file_handle,
                            block=block,
                        )
                        # Print current state
                        self._print_state(state_dict, block)

                        block += 1
                        # Reset step flag after executing single step
                        if keyboard_handler.should_step:
                            keyboard_handler.should_step = False

                    # Get current animation delay (may have been changed by keyboard)
                    animation_delay = self.sim.config.animation_delay.value
                    if animation_delay is None:
                        animation_delay = self.sim.config.animation_delay.default

                    # Apply animation delay with keyboard input checking
                    if animation_delay > 0:
                        # Check for keyboard input during sleep intervals
                        sleep_chunks = max(
                            1, int(animation_delay / 0.1)
                        )  # 100ms chunks
                        chunk_duration = animation_delay / sleep_chunks

                        for _ in range(sleep_chunks):
                            if keyboard_handler.should_quit:
                                break
                            if not keyboard_handler.is_paused:
                                time.sleep(chunk_duration)
                            keyboard_handler.check_keyboard_input(0.0)

                            # If paused, keep checking for input without advancing simulation
                            while (
                                keyboard_handler.is_paused
                                and not keyboard_handler.should_quit
                                and not keyboard_handler.should_step
                            ):
                                keyboard_handler.check_keyboard_input(0.1)
                            # Break out of sleep loop if step was requested
                            if keyboard_handler.should_step:
                                break
        finally:
            # Always restore terminal settings
            keyboard_handler.restore_terminal()

        # -----------------------------------------------------------
        # write out the final results
        output_dict["end_state"] = results.get_end_state()
        if self.sim.jsonl_file:
            jsonl_file_handle.write(json.dumps(output_dict) + "\n")
            jsonl_file_handle.close()
        if self.sim.csv_file and self.sim.run_sequence:
            if not csv_exists:
                for key in output_dict["end_state"]:
                    csv_file_handle.write(f'"{key}", ')
                csv_file_handle.write("\n")
            for key in output_dict["end_state"]:
                csv_file_handle.write(str(output_dict["end_state"][key]) + ", ")
            csv_file_handle.write("\n")
        if self.sim.csv_file:
            csv_file_handle.close()

        # Write results to config file [RESULTS] section
        # Only write if config file exists and simulation is not part of a sequence
        if self.sim.config_file and not self.sim.run_sequence:
            import logging
            from datetime import datetime

            # Get standardized results with timestamp
            standardized_results = results.get_standardized_results(
                timestamp=datetime.now().isoformat(),
                duration_seconds=None,  # TextAnimation doesn't track duration
            )
            # Write to config file
            success = self.sim.config.write_results_section(
                self.sim.config_file, standardized_results
            )
            if not success:
                logging.warning(
                    f"Failed to write [RESULTS] section to {self.sim.config_file}"
                )

        # Print end state
        print("\n\n Category     | Measure                        |     Value")
        print(" ----------------------------------------------------------")
        for type in output_dict["end_state"]:
            # goes over vehicles etc
            for key, value in output_dict["end_state"][type].items():
                print(f" {type:<12} | {key:<30} | {value:>10}")
        print(" ----------------------------------------------------------")

        # print(json.dumps(output_dict, indent=2, sort_keys=True))
        return results

    def _print_state(self, state_dict, block):
        """
        Print current simulation state in a compact format.

        Args:
            state_dict: Dictionary containing current state measures
            block: Current block number
        """
        s = (
            f"block {block:5d}: cs={self.sim.city_size:3d}, "
            f"N={state_dict[Measure.VEHICLE_MEAN_COUNT.name]:.2f}, "
            f"R={state_dict[Measure.TRIP_MEAN_REQUEST_RATE.name]:.2f}, "
            f"P1={state_dict[Measure.VEHICLE_FRACTION_P1.name]:.2f}, "
            f"P2={state_dict[Measure.VEHICLE_FRACTION_P2.name]:.2f}, "
            f"P3={state_dict[Measure.VEHICLE_FRACTION_P3.name]:.2f}, "
            f"W={state_dict[Measure.TRIP_MEAN_WAIT_FRACTION.name]:.2f}, "
            f"rmsr={state_dict[Measure.SIM_CONVERGENCE_MAX_RMS_RESIDUAL.name]:.2f}"
        )
        print(f"\r{s}", end="", flush=True)

    def _check_and_print_keyboard_actions(self, keyboard_handler):
        """
        Check for keyboard action effects and print feedback.

        Uses newlines to print feedback messages, then the status line
        will continue to update normally with \r.

        Note: Restart detection is handled in the main loop, not here.
        """
        # Check for vehicle count changes
        current_vehicle_count = self.sim.target_state.get(
            "vehicle_count", len(self.sim.vehicles)
        )
        if (
            self._prev_vehicle_count is not None
            and current_vehicle_count != self._prev_vehicle_count
        ):
            diff = current_vehicle_count - self._prev_vehicle_count
            action = "increased" if diff > 0 else "decreased"
            print(
                f"\r[Vehicles {action} to {current_vehicle_count}]", end="", flush=True
            )
        self._prev_vehicle_count = current_vehicle_count

        # Check for demand changes
        current_base_demand = self.sim.target_state.get(
            "base_demand", self.sim.base_demand
        )
        if (
            self._prev_base_demand is not None
            and abs(current_base_demand - self._prev_base_demand) > 0.001
        ):
            print(f"\r[Demand set to {current_base_demand:.2f}]", end="", flush=True)
        self._prev_base_demand = current_base_demand

        # Check for animation delay changes
        current_animation_delay = self.sim.config.animation_delay.value
        if current_animation_delay is None:
            current_animation_delay = self.sim.config.animation_delay.default
        if (
            self._prev_animation_delay is not None
            and abs(current_animation_delay - self._prev_animation_delay) > 0.001
        ):
            print(
                f"\r[Animation delay set to {current_animation_delay:.2f}s]",
                end="",
                flush=True,
            )
        self._prev_animation_delay = current_animation_delay

        # Check for pause state changes
        if keyboard_handler.is_paused:
            # Only print pause message once when transitioning to paused
            if not hasattr(self, "_was_paused") or not self._was_paused:
                print(
                    "\r[Paused - press space/p to resume, s to step, r to restart]",
                    end="",
                    flush=True,
                )
        self._was_paused = keyboard_handler.is_paused
