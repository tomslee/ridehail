"""
Controls for a running simulation: pause, step, quit, restart, and live
changes to the fleet, demand and animation delay.

SimulationControls applies the actions. KeyboardHandler adds non-blocking
terminal input (Unix/Linux/macOS), for the text animation and the
SimulationRunner loop. Live changes go through sim.target_state, and the
simulation applies them at the start of its next block.
"""

import select
import sys

from ridehail.keyboard_mappings import generate_help_text, get_mapping_for_key

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


class SimulationControls:
    """
    The actions a user can take on a running simulation, shared by the text
    animation, the Textual animations and the matplotlib animations. It does
    not touch the terminal.
    """

    def __init__(self, simulation):
        self.sim = simulation
        self.is_paused = False
        self.should_quit = False
        self.should_step = False  # Flag for single-step execution

    def handle_ui_action(self, action, value=None):
        """
        Apply an action. value is the step for the increase/decrease actions
        (defaults: 1 vehicle, 0.1 demand, 0.05 s delay). Returns the action's
        result (the new pause state or target value, or True), or None for an
        action this class doesn't handle.
        """
        if action == "pause":
            self.is_paused = not self.is_paused
            return self.is_paused

        elif action == "quit":
            self.should_quit = True
            return True

        elif action == "decrease_vehicles":
            return self._adjust_vehicles(-(value or 1))

        elif action == "increase_vehicles":
            return self._adjust_vehicles(value or 1)

        elif action == "decrease_demand":
            return self._adjust_demand(-(value or 0.1))

        elif action == "increase_demand":
            return self._adjust_demand(value or 0.1)

        elif action == "decrease_animation_delay":
            return self._adjust_animation_delay(-(value or 0.05))

        elif action == "increase_animation_delay":
            return self._adjust_animation_delay(value or 0.05)

        elif action == "step":
            # Single step forward (only when paused)
            if self.is_paused:
                self.should_step = True
            return True

        elif action == "restart":
            self.sim._restart_simulation()
            return True

        return None

    def _adjust_vehicles(self, delta):
        """Change the target vehicle count by delta. Returns the new target."""
        current = self.sim.target_state.get("vehicle_count", self.sim.vehicle_count)
        self.sim.target_state["vehicle_count"] = max(current + delta, 0)
        return self.sim.target_state["vehicle_count"]

    def _adjust_demand(self, delta):
        """
        Change the target base_demand by delta in user-facing units (trips/min
        when use_city_scale, trips/block otherwise). Returns the new target,
        in internal units.
        """
        current = self.sim.target_state.get("base_demand", self.sim.base_demand)
        new = max(self.sim.demand_to_display(current) + delta, 0)
        self.sim.target_state["base_demand"] = self.sim.demand_from_display(new)
        return self.sim.target_state["base_demand"]

    def _adjust_animation_delay(self, delta):
        """
        Change the animation delay by delta seconds, at once: it paces the
        display, not the simulation. Returns the new delay.
        """
        self.sim.animation_delay = max(self.sim.animation_delay + delta, 0.0)
        return self.sim.animation_delay

    def adjust_city_size(self, delta):
        """
        Change the target city size by delta, keeping it even and at least 2.
        Returns the new target.
        """
        current = self.sim.target_state.get("city_size", self.sim.city_size)
        self.sim.target_state["city_size"] = max(2 * round((current + delta) / 2), 2)
        return self.sim.target_state["city_size"]


class KeyboardHandler(SimulationControls):
    """
    SimulationControls driven by non-blocking terminal input. Puts the
    terminal in cbreak mode; call restore_terminal() when done.
    """

    def __init__(self, simulation):
        super().__init__(simulation)
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
        Handle a key press. Returns True if the key was processed, False
        otherwise.
        """
        # Handle Ctrl+C separately
        if key == "\x03":
            self.should_quit = True
            return True

        mapping = get_mapping_for_key(key, platform="terminal")
        if not mapping:
            return False
        if mapping.action == "show_help":
            self._print_help()
            return True
        return self.handle_ui_action(mapping.action, mapping.value) is not None

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
