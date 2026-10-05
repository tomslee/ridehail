"""
SimulationRunner - Centralized simulation execution logic.

Extracts common simulation loop patterns from RideHailSimulation.simulate(),
TextAnimation.animate(), and other animation modules to reduce duplication
and provide consistent behavior across all animation types.
"""

import json
import logging
import socket
import subprocess
import sys
import time
from datetime import datetime
from os import path
from typing import Optional, Callable

from ridehail.config import WritableConfig
from ridehail.results import RideHailSimulationResults


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


def create_metadata_record(sim):
    """
    Create metadata record with provenance information.
    """
    metadata = {
        "type": "metadata",
        "version": sim.version,
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
    if sim.config.random_number_seed.value:
        metadata["random_seed_used"] = sim.config.random_number_seed.value

    return metadata


def flatten_end_state(end_state):
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


class SimulationOutput:
    """
    The JSONL and CSV output files of one run. A simulation has them only
    with write_output_files (-o) and a config file (sim.jsonl_file and
    sim.csv_file are None otherwise); then every animation that steps the
    simulation passes these handles to next_block():

        output = SimulationOutput(sim)
        sim.next_block(jsonl_file_handle=output.jsonl, csv_file_handle=output.csv)
        ...
        output.close(simulation_results, duration_seconds)

    The JSONL file gets a metadata record and a config record now, a block
    record per block (written by next_block), and an end_state record at
    close(). In a sequence, the CSV file gets one row of end-state measures
    per simulation.
    """

    def __init__(self, sim):
        self.sim = sim
        self.jsonl = open(sim.jsonl_file, "a") if sim.jsonl_file else None
        # A sequence appends one row per simulation: write the header only
        # into a new file
        self.csv_exists = bool(sim.csv_file) and path.exists(sim.csv_file)
        self.csv = open(sim.csv_file, "a") if sim.csv_file else None
        if self.jsonl:
            self.jsonl.write(json.dumps(create_metadata_record(sim)) + "\n")
            config_record = {"type": "config"}
            config_record.update(WritableConfig(sim.config).__dict__)
            self.jsonl.write(json.dumps(config_record) + "\n")

    def close(self, simulation_results, duration_seconds):
        """Write the end state, and close the files."""
        end_state = simulation_results.get_end_state()
        if self.jsonl:
            end_state_record = {
                "type": "end_state",
                "duration_seconds": round(duration_seconds, 2),
            }
            end_state_record.update(end_state)
            self.jsonl.write(json.dumps(end_state_record) + "\n")
            self.jsonl.close()
            self.jsonl = None
        if self.csv:
            # CSV output for sequences (flat structure for backward compatibility)
            if self.sim.run_sequence:
                flat_end_state = flatten_end_state(end_state)
                if not self.csv_exists:
                    for key in flat_end_state:
                        self.csv.write(f'"{key}", ')
                    self.csv.write("\n")
                for key in flat_end_state:
                    self.csv.write(str(flat_end_state[key]) + ", ")
                self.csv.write("\n")
            self.csv.close()
            self.csv = None


class SimulationRunner:
    """
    Run a simulation in a loop, for the no-animation and text modes (and the
    simulations of a sequence), with a pluggable display callback.

    Handles:
    - Keyboard input polling
    - Pause/step/quit control
    - Animation delay with responsive keyboard checking
    - File I/O (JSONL/CSV), via SimulationOutput
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

    def run(
        self,
        display_callback: Optional[Callable[[dict, int], None]] = None,
        should_stop_callback: Optional[Callable[[], bool]] = None,
    ) -> RideHailSimulationResults:
        """
        Run the simulation until time_blocks blocks have been simulated (or
        until quit, if time_blocks is 0).

        Args:
            display_callback: Optional function(state_dict, block) called after
                each block for custom display/animation updates. After a
                restart it is called once with (None, -1).
            should_stop_callback: Optional function() -> bool to check for
                external stop conditions (e.g., matplotlib window closed)

        Returns:
            RideHailSimulationResults with end state
        """
        start_time = time.time()

        simulation_results = RideHailSimulationResults(self.sim)
        output = SimulationOutput(self.sim)
        # Set up the keyboard handler last: it puts the terminal in cbreak
        # mode, which the finally clause below restores
        from ridehail.keyboard import KeyboardHandler

        self.keyboard_handler = KeyboardHandler(self.sim)
        time_blocks = self.sim.time_blocks
        last_block = -1
        try:
            while not self.keyboard_handler.should_quit:
                block = self.sim.block_index
                if 0 < time_blocks <= block:
                    break
                # Check for external stop condition
                if should_stop_callback and should_stop_callback():
                    break
                # A restart (from the keyboard) sets block_index back to 0
                if block < last_block and display_callback:
                    display_callback(None, -1)
                last_block = block

                # Execute simulation step if not paused, or if single-stepping
                if (
                    not self.keyboard_handler.is_paused
                    or self.keyboard_handler.should_step
                ):
                    state_dict = self.sim.next_block(
                        jsonl_file_handle=output.jsonl,
                        csv_file_handle=output.csv,
                    )
                    if display_callback:
                        display_callback(state_dict, block)
                    # Reset step flag after executing single step
                    if self.keyboard_handler.should_step:
                        self.keyboard_handler.should_step = False

                # Apply animation delay with keyboard input checking
                self._sleep_with_keyboard_check()

        finally:
            # Always restore terminal settings
            self.keyboard_handler.restore_terminal()

        # Write final results
        duration_seconds = time.time() - start_time
        output.close(simulation_results, duration_seconds)
        # Write results to config file [RESULTS] section using shared helper
        write_results_to_config(self.sim, simulation_results, duration_seconds)
        return simulation_results

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
