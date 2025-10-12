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
from ridehail.dispatch import Dispatch
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
            dispatch = Dispatch(self.sim.dispatch_method, self.sim.forward_dispatch_bias)
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

            # Get animation delay from config for consistent timing
            animation_delay = self.sim.config.animation_delay.value
            if animation_delay is None:
                animation_delay = self.sim.config.animation_delay.default

            # -----------------------------------------------------------
            # Here is the simulation loop
            if self.sim.time_blocks > 0:
                # time_blocks is the number of time periods to simulate.
                for block in range(self.sim.time_blocks):
                    # Check for quit request
                    if keyboard_handler.should_quit:
                        break

                    # Execute simulation step if not paused, or if single-stepping
                    if not keyboard_handler.is_paused or keyboard_handler.should_step:
                        state_dict = self.sim.next_block(
                            jsonl_file_handle=jsonl_file_handle,
                            csv_file_handle=csv_file_handle,
                            block=block,
                            dispatch=dispatch,
                        )
                        # Print current state
                        self._print_state(state_dict, block)

                        # Reset step flag after executing single step
                        if keyboard_handler.should_step:
                            keyboard_handler.should_step = False

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
                            ):
                                keyboard_handler.check_keyboard_input(0.1)
            else:
                # time_blocks = 0: continue indefinitely.
                block = 0
                while not keyboard_handler.should_quit:
                    # Execute simulation step if not paused, or if single-stepping
                    if not keyboard_handler.is_paused or keyboard_handler.should_step:
                        state_dict = self.sim.next_block(
                            jsonl_file_handle=jsonl_file_handle,
                            csv_file_handle=csv_file_handle,
                            block=block,
                            dispatch=dispatch,
                        )
                        # Print current state
                        self._print_state(state_dict, block)

                        block += 1
                        # Reset step flag after executing single step
                        if keyboard_handler.should_step:
                            keyboard_handler.should_step = False

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
                            ):
                                keyboard_handler.check_keyboard_input(0.1)
        finally:
            # Always restore terminal settings
            keyboard_handler.restore_terminal()

        # -----------------------------------------------------------
        # write out the final results
        results.compute_end_state()
        output_dict["end_state"] = results.end_state
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

        # Print end state
        print("\nEnd state:")
        print(json.dumps(output_dict, indent=2, sort_keys=True))

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
            f"W={state_dict[Measure.TRIP_MEAN_WAIT_TIME.name]:.2f} min"
        )
        print(f"\r{s}", end="", flush=True)
