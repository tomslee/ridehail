"""
Text-based animation for ridehail simulation.

Provides simple text output to stdout, showing:
- Current simulation state on each block (single line, updated in place)
- Final results as JSON at completion
"""

from ridehail.animation.base import RideHailAnimation
from ridehail.atom import Measure
from rich import print


def format_simulation_state(state_dict, block, city_size):
    """
    Format simulation state as a compact string.

    Args:
        state_dict: Dictionary containing current state measures
        block: Current block number
        city_size: Size of the city grid

    Returns:
        Formatted string showing simulation state
    """
    return (
        f"block={block:5d}, "
        f"cs={city_size:3d}, "
        f"N={state_dict[Measure.VEHICLE_MEAN_COUNT.name]:.2f}, "
        f"R={state_dict[Measure.TRIP_MEAN_REQUEST_RATE.name]:.2f}, "
        f"P1={state_dict[Measure.VEHICLE_FRACTION_P1.name]:.2f}, "
        f"P2={state_dict[Measure.VEHICLE_FRACTION_P2.name]:.2f}, "
        f"P3={state_dict[Measure.VEHICLE_FRACTION_P3.name]:.2f}, "
        f"W={state_dict[Measure.TRIP_MEAN_WAIT_FRACTION_TOTAL.name]:.2f}, "
        f"rmsr={state_dict[Measure.SIM_CONVERGENCE_MAX_RMS_RESIDUAL.name]:.3f}"
    )


class TextAnimation(RideHailAnimation):
    """
    Simple text-based animation that prints simulation state to stdout.

    Displays a single line showing current block and key metrics, updated in place.
    At completion, prints the full end state as a table.
    For sequences, no end-state table is printed.
    """

    def __init__(self, sim, print_results_table=True, enable_keyboard=True):
        super().__init__(sim)
        # Track previous state for detecting keyboard action effects
        self._prev_vehicle_count = None
        self._prev_base_demand = None
        self._prev_animation_delay = None
        # Control whether to print results table at end (disabled for sequences)
        self._print_results_table = print_results_table
        # Control whether to enable keyboard handling (disabled for sequences)
        self._enable_keyboard = enable_keyboard

    def animate(self):
        """
        Run the simulation with text output.

        Prints:
        - Keyboard controls help at start (if keyboard enabled)
        - Current state on each block (updated in place)
        - Final results as JSON at completion (if print_results_table enabled)
        """
        if self._enable_keyboard:
            # Run with keyboard handling for interactive use
            simulation_results = self._animate_with_keyboard()
        else:
            # Run simple loop without keyboard handling for sequences
            simulation_results = self._animate_simple()

        # Print end state (conditionally based on print_results_table setting)
        if self._print_results_table:
            end_state = simulation_results.get_end_state()
            print("\n\n Category         | Measure                        |     Value")
            print(" --------------------------------------------------------------")
            for type in end_state:
                # goes over vehicles etc
                for key, value in end_state[type].items():
                    print(f" {type:<16} | {key:<30} | {value:>10}")
            print(" --------------------------------------------------------------")
        else:
            # For sequences: just print newline to finalize the last block's state
            print()

        return simulation_results

    def _animate_with_keyboard(self):
        """
        Run simulation with keyboard handling enabled.

        Returns:
            RideHailSimulationResults: Results from the completed simulation
        """
        from ridehail.simulation_runner import SimulationRunner

        # Create a display callback that handles text output
        def display_callback(state_dict, block):
            # Handle restart signal
            if state_dict is None and block == -1:
                print("\r[Restarted simulation]", end="", flush=True)
                # Reset tracked state for clean feedback after restart
                self._prev_vehicle_count = None
                self._prev_base_demand = None
                self._prev_animation_delay = None
                return

            # Check for keyboard action effects and print feedback
            self._check_and_print_keyboard_actions(runner.keyboard_handler)

            # Print current state
            if state_dict:
                self._print_state(state_dict, block)

        # Run simulation with display callback
        runner = SimulationRunner(self.sim)
        return runner.run(display_callback=display_callback)

    def _animate_simple(self):
        """
        Run simulation without keyboard handling (for sequences).

        Returns:
            RideHailSimulationResults: Results from the completed simulation
        """
        from ridehail.results import RideHailSimulationResults

        # Run simulation blocks with text output
        for block in range(self.sim.time_blocks):
            state_dict = self.sim.next_block(block=block)
            self._print_state(state_dict, block)

        return RideHailSimulationResults(self.sim)

    def _print_state(self, state_dict, block):
        """
        Print current simulation state in a compact format.

        Args:
            state_dict: Dictionary containing current state measures
            block: Current block number
        """
        s = format_simulation_state(state_dict, block, self.sim.city_size)
        print(f"{s}", end="\r", flush=True)

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
            print(f"\n[R -> {current_base_demand:.2f}]", flush=True)
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
