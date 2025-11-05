"""
SimulationRunner - Centralized simulation execution logic.

Extracts common simulation loop patterns from RideHailSimulation.simulate(),
TextAnimation.animate(), and other animation modules to reduce duplication
and provide consistent behavior across all animation types.
"""

import json
import logging
import time
from datetime import datetime
from os import path
from typing import Optional, Callable

from ridehail.config import WritableConfig
from ridehail.simulation_results import RideHailSimulationResults


def write_results_to_config(
    sim, simulation_results: RideHailSimulationResults, duration_seconds: float
):
    """
    Write simulation results to config file [RESULTS] section.

    Standalone function that can be used by any animation type without requiring
    a full SimulationRunner instance.

    Args:
        sim: RideHailSimulation instance
        simulation_results: RideHailSimulationResults instance
        duration_seconds: Total simulation duration

    Returns:
        bool: True if results were written successfully, False otherwise
    """
    # Only write if config file exists and simulation is not part of a sequence
    if not sim.config_file:
        logging.debug("Not writing results: No config file specified")
        return False
    if sim.run_sequence:
        logging.debug("Not writing results: Running as part of a sequence")
        return False

    # Get standardized results with timestamp and duration
    result_measures = simulation_results.get_result_measures(
        timestamp=datetime.now().isoformat(),
        duration_seconds=duration_seconds,
    )

    # Write to config file
    success = sim.config.write_results_section(sim.config_file, result_measures)
    # Note: write_results_section logs specific failure reasons, so no additional logging needed here
    return success


class SimulationRunner:
    """
    Centralized simulation execution with pluggable display callbacks.

    Provides two execution modes:
    1. Loop-based: For text and matplotlib animations
    2. Timer-based: For Textual async animations (used via manual stepping)

    Handles:
    - Keyboard input polling
    - Pause/step/quit control
    - Animation delay with responsive keyboard checking
    - File I/O (JSONL/CSV)
    - Results collection and writing
    """

    def __init__(self, sim):
        """
        Initialize runner with a simulation instance.

        Args:
            sim: RideHailSimulation instance
        """
        self.sim = sim
        self.keyboard_handler = None
        self.jsonl_file_handle = None
        self.csv_file_handle = None
        self.csv_exists = False

    def run(
        self,
        display_callback: Optional[Callable[[dict, int], None]] = None,
        should_stop_callback: Optional[Callable[[], bool]] = None,
    ) -> RideHailSimulationResults:
        """
        Run simulation with loop-based execution.

        Args:
            display_callback: Optional function(state_dict, block) called after each block
                             for custom display/animation updates
            should_stop_callback: Optional function() -> bool to check for external stop conditions
                                 (e.g., matplotlib window closed)

        Returns:
            RideHailSimulationResults with end state
        """
        start_time = time.time()

        # Setup keyboard handler
        from ridehail.simulation import KeyboardHandler

        self.keyboard_handler = KeyboardHandler(self.sim)

        try:
            simulation_results = RideHailSimulationResults(self.sim)

            # Setup file handles
            self._setup_file_handles()

            # Write metadata and config records
            self._write_initial_records()

            # Main simulation loop
            if self.sim.time_blocks > 0:
                # Fixed number of blocks
                block = 0
                while (
                    block < self.sim.time_blocks
                    and not self.keyboard_handler.should_quit
                ):
                    # Check for external stop condition
                    if should_stop_callback and should_stop_callback():
                        break

                    # Check for restart (block_index was reset to 0)
                    if self.sim.block_index == 0 and block > 0:
                        block = 0
                        if display_callback:
                            # Let display know about restart
                            display_callback(None, -1)  # Special signal for restart

                    # Execute simulation step if not paused, or if single-stepping
                    if (
                        not self.keyboard_handler.is_paused
                        or self.keyboard_handler.should_step
                    ):
                        state_dict = self.sim.next_block(
                            jsonl_file_handle=self.jsonl_file_handle,
                            csv_file_handle=self.csv_file_handle,
                            block=block,
                        )

                        # Call display callback
                        if display_callback:
                            display_callback(state_dict, block)

                        block += 1

                        # Reset step flag after executing single step
                        if self.keyboard_handler.should_step:
                            self.keyboard_handler.should_step = False

                    # Apply animation delay with keyboard input checking
                    self._sleep_with_keyboard_check()

            else:
                # time_blocks = 0: continue indefinitely
                block = 0
                while not self.keyboard_handler.should_quit:
                    # Check for external stop condition
                    if should_stop_callback and should_stop_callback():
                        break

                    # Execute simulation step if not paused, or if single-stepping
                    if (
                        not self.keyboard_handler.is_paused
                        or self.keyboard_handler.should_step
                    ):
                        state_dict = self.sim.next_block(
                            jsonl_file_handle=self.jsonl_file_handle,
                            csv_file_handle=self.csv_file_handle,
                            block=block,
                        )

                        # Call display callback
                        if display_callback:
                            display_callback(state_dict, block)

                        block += 1

                        # Reset step flag after executing single step
                        if self.keyboard_handler.should_step:
                            self.keyboard_handler.should_step = False

                    # Apply animation delay with keyboard input checking
                    self._sleep_with_keyboard_check()

        finally:
            # Always restore terminal settings
            if self.keyboard_handler:
                self.keyboard_handler.restore_terminal()

        # Write final results
        duration_seconds = time.time() - start_time
        self._write_final_results(simulation_results, duration_seconds)

        return simulation_results

    def _setup_file_handles(self):
        """Setup JSONL and CSV file handles if needed"""
        if self.sim.jsonl_file or self.sim.csv_file:
            self.jsonl_file_handle = (
                open(f"{self.sim.jsonl_file}", "a") if self.sim.jsonl_file else None
            )

            self.csv_exists = False
            if self.sim.csv_file and path.exists(self.sim.csv_file):
                self.csv_exists = True
            self.csv_file_handle = (
                open(f"{self.sim.csv_file}", "a") if self.sim.csv_file else None
            )
        else:
            self.jsonl_file_handle = None
            self.csv_file_handle = None

    def _write_initial_records(self):
        """Write metadata and config records to output files"""
        # Write metadata record (if not in sequence mode)
        if self.jsonl_file_handle:
            metadata = self.sim._create_metadata_record()
            self.jsonl_file_handle.write(json.dumps(metadata) + "\n")

        # Write config record
        config_record = {"type": "config"}
        config_record.update(WritableConfig(self.sim.config).__dict__)
        if self.jsonl_file_handle:
            self.jsonl_file_handle.write(json.dumps(config_record) + "\n")

    def _sleep_with_keyboard_check(self):
        """
        Apply animation delay with responsive keyboard input checking.

        Breaks sleep into small chunks (100ms) to allow responsive keyboard
        input processing. Handles pause state by continuing to check keyboard
        without advancing simulation.
        """
        if self.sim.animation_delay > 0:
            # Check for keyboard input during sleep intervals
            sleep_chunks = max(1, int(self.sim.animation_delay / 0.1))  # 100ms chunks
            chunk_duration = self.sim.animation_delay / sleep_chunks

            for _ in range(sleep_chunks):
                if self.keyboard_handler.should_quit:
                    break
                if not self.keyboard_handler.is_paused:
                    time.sleep(chunk_duration)
                self.keyboard_handler.check_keyboard_input(0.0)

                # If paused, keep checking for input without advancing simulation
                while (
                    self.keyboard_handler.is_paused
                    and not self.keyboard_handler.should_quit
                    and not self.keyboard_handler.should_step
                ):
                    self.keyboard_handler.check_keyboard_input(0.1)

                # Break out of sleep loop if step was requested
                if self.keyboard_handler.should_step:
                    break

    def _write_final_results(
        self, simulation_results: RideHailSimulationResults, duration_seconds: float
    ):
        """
        Write final results to output files and config file.

        Args:
            simulation_results: RideHailSimulationResults instance
            duration_seconds: Total simulation duration
        """
        end_state = simulation_results.get_end_state()

        # Write end_state record to JSONL
        if self.jsonl_file_handle:
            end_state_record = {
                "type": "end_state",
                "duration_seconds": round(duration_seconds, 2),
            }
            end_state_record.update(end_state)
            self.jsonl_file_handle.write(json.dumps(end_state_record) + "\n")
            self.jsonl_file_handle.close()

        # CSV output for sequences (keep flat structure for backward compatibility)
        if self.csv_file_handle and self.sim.run_sequence:
            # Flatten hierarchical end_state for CSV
            flat_end_state = self.sim._flatten_end_state(end_state)
            if not self.csv_exists:
                for key in flat_end_state:
                    self.csv_file_handle.write(f'"{key}", ')
                self.csv_file_handle.write("\n")
            for key in flat_end_state:
                self.csv_file_handle.write(str(flat_end_state[key]) + ", ")
            self.csv_file_handle.write("\n")

        if self.csv_file_handle:
            self.csv_file_handle.close()

        # Write results to config file [RESULTS] section using shared helper
        write_results_to_config(self.sim, simulation_results, duration_seconds)
