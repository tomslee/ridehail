"""
Textual-based animation base class for ridehail simulation.
"""

import logging
import asyncio
from typing import Optional, Dict, Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import (
    Header,
    Footer,
    Static,
    ProgressBar,
    Label,
    Button,
    DataTable,
    TabbedContent,
    TabPane,
)
from textual.message import Message
from textual.timer import Timer

from ridehail.atom import Measure
from .base import RideHailAnimation


class SimulationControlPanel(Container):
    """Control panel for simulation playback and parameters"""

    def __init__(self, sim, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim
        self.is_paused = False

    def compose(self) -> ComposeResult:
        yield Static("Simulation Controls", classes="panel-title")
        with Horizontal(classes="control-buttons"):
            yield Button("⏸️ Pause", id="pause_btn", variant="primary")
            yield Button("⏹️ Stop", id="stop_btn", variant="error")
            yield Button("⚙️ Settings", id="settings_btn")

        yield Static("Vehicle Count: ", classes="control-label")
        with Horizontal(classes="control-row"):
            yield Button("-10", id="vehicles_minus_10", classes="small-btn")
            yield Button("-1", id="vehicles_minus_1", classes="small-btn")
            yield Label(str(self.sim.vehicle_count), id="vehicle_count_display")
            yield Button("+1", id="vehicles_plus_1", classes="small-btn")
            yield Button("+10", id="vehicles_plus_10", classes="small-btn")

        yield Static("Base Demand: ", classes="control-label")
        with Horizontal(classes="control-row"):
            yield Button("-0.1", id="demand_minus", classes="small-btn")
            yield Label(f"{self.sim.base_demand:.1f}", id="demand_display")
            yield Button("+0.1", id="demand_plus", classes="small-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses for simulation control"""
        button_id = event.button.id

        if button_id == "pause_btn":
            self.is_paused = not self.is_paused
            event.button.label = "▶️ Resume" if self.is_paused else "⏸️ Pause"
            self.post_message(SimulationPaused(self.is_paused))

        elif button_id == "stop_btn":
            self.post_message(SimulationStopped())

        elif button_id == "vehicles_minus_10":
            self.sim.target_state["vehicle_count"] = max(
                self.sim.target_state["vehicle_count"] - 10, 0
            )
            self.query_one("#vehicle_count_display").update(
                str(self.sim.target_state["vehicle_count"])
            )

        elif button_id == "vehicles_minus_1":
            self.sim.target_state["vehicle_count"] = max(
                self.sim.target_state["vehicle_count"] - 1, 0
            )
            self.query_one("#vehicle_count_display").update(
                str(self.sim.target_state["vehicle_count"])
            )

        elif button_id == "vehicles_plus_1":
            self.sim.target_state["vehicle_count"] += 1
            self.query_one("#vehicle_count_display").update(
                str(self.sim.target_state["vehicle_count"])
            )

        elif button_id == "vehicles_plus_10":
            self.sim.target_state["vehicle_count"] += 10
            self.query_one("#vehicle_count_display").update(
                str(self.sim.target_state["vehicle_count"])
            )

        elif button_id == "demand_minus":
            self.sim.target_state["base_demand"] = max(
                self.sim.target_state["base_demand"] - 0.1, 0
            )
            self.query_one("#demand_display").update(
                f"{self.sim.target_state['base_demand']:.1f}"
            )

        elif button_id == "demand_plus":
            self.sim.target_state["base_demand"] += 0.1
            self.query_one("#demand_display").update(
                f"{self.sim.target_state['base_demand']:.1f}"
            )


class ProgressPanel(Container):
    """Progress display panel with multiple metrics"""

    def __init__(self, sim, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim

    def compose(self) -> ComposeResult:
        yield Static("Simulation Progress", classes="panel-title")

        # Main progress bar
        yield Label("Block Progress")
        yield ProgressBar(total=1.0, show_eta=False, id="main_progress")

        # Vehicle status bars
        yield Static("Vehicle Status", classes="subsection-title")
        yield Label("P1 (Idle)")
        yield ProgressBar(total=1.0, show_percentage=True, id="vehicle_p1")
        yield Label("P2 (Dispatched)")
        yield ProgressBar(total=1.0, show_percentage=True, id="vehicle_p2")
        yield Label("P3 (Occupied)")
        yield ProgressBar(total=1.0, show_percentage=True, id="vehicle_p3")

        # Trip metrics
        yield Static("Trip Metrics", classes="subsection-title")
        yield Label("Mean Wait Time")
        yield ProgressBar(
            total=self.sim.city.city_size, show_percentage=False, id="wait_time"
        )
        yield Label("Mean Ride Time")
        yield ProgressBar(
            total=self.sim.city.city_size, show_percentage=False, id="ride_time"
        )

    def update_progress(self, results: Dict[str, Any]) -> None:
        """Update all progress bars with simulation results"""
        # Main progress
        if self.sim.time_blocks > 0:
            progress = results["block"] / self.sim.time_blocks
            self.query_one("#main_progress").update(progress=progress)

        # Vehicle status
        self.query_one("#vehicle_p1").update(
            progress=results[Measure.VEHICLE_FRACTION_P1.name]
        )
        self.query_one("#vehicle_p2").update(
            progress=results[Measure.VEHICLE_FRACTION_P2.name]
        )
        self.query_one("#vehicle_p3").update(
            progress=results[Measure.VEHICLE_FRACTION_P3.name]
        )

        # Trip metrics
        self.query_one("#wait_time").update(
            progress=results[Measure.TRIP_MEAN_WAIT_TIME.name]
        )
        self.query_one("#ride_time").update(
            progress=results[Measure.TRIP_MEAN_RIDE_TIME.name]
        )


class ConfigPanel(Container):
    """Configuration display panel"""

    def __init__(self, sim, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim

    def compose(self) -> ComposeResult:
        yield Static("Configuration", classes="panel-title")

        table = DataTable(show_header=False, zebra_stripes=True)
        table.add_column("Setting", width=20)
        table.add_column("Value", width=20)

        # Add configuration rows (excluding complex objects)
        exclude_attrs = {
            "city",
            "config",
            "target_state",
            "jsonl_file",
            "csv_file",
            "trips",
            "vehicles",
            "interpolate",
            "changed_plot_flag",
            "block_index",
            "animate",
            "animation_style",
            "annotation",
            "request_capital",
            "changed_plotstat_flag",
            "plotstat_list",
            "state_dict",
            "dispatch",
        }

        for attr in dir(self.sim):
            if (
                not attr.startswith("_")
                and not callable(getattr(self.sim, attr))
                and attr not in exclude_attrs
            ):
                value = getattr(self.sim, attr)
                table.add_row(attr, str(value))

        yield table


class SimulationPaused(Message):
    """Message sent when simulation is paused/resumed"""

    def __init__(self, is_paused: bool):
        self.is_paused = is_paused
        super().__init__()


class SimulationStopped(Message):
    """Message sent when simulation is stopped"""

    pass


class RidehailTextualApp(App):
    """Main Textual application for ridehail animations"""

    CSS = """
    .panel-title {
        text-style: bold;
        background: $primary;
        color: $text;
        padding: 1;
        margin: 1 0;
    }

    .subsection-title {
        text-style: bold;
        margin: 1 0 0 0;
    }

    .control-buttons {
        height: 3;
        margin: 1 0;
    }

    .control-row {
        height: 3;
        margin: 0 0 1 0;
    }

    .control-label {
        margin: 1 0 0 0;
    }

    .small-btn {
        width: 6;
        margin: 0 1;
    }

    Container {
        border: solid $primary;
        margin: 1;
        padding: 1;
    }

    ProgressBar {
        margin: 0 0 1 0;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("space", "pause", "Pause/Resume"),
        ("n", "decrease_vehicles", "Vehicles -1"),
        ("N", "increase_vehicles", "Vehicles +1"),
        ("k", "decrease_demand", "Demand -0.1"),
        ("K", "increase_demand", "Demand +0.1"),
    ]

    def __init__(self, sim, animation=None, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim
        self.animation = animation
        self.is_paused = False
        self.simulation_timer: Optional[Timer] = None

    def compose(self) -> ComposeResult:
        """Create child widgets for the app"""
        yield self.create_header()

        with TabbedContent(initial="main"):
            with TabPane("Main", id="main"):
                with Horizontal():
                    with Vertical(classes="left-panel"):
                        yield self.create_progress_panel()
                        yield self.create_control_panel()
                    with Vertical(classes="right-panel"):
                        yield self.create_config_panel()

        yield self.create_footer()

    def create_header(self):
        """Create the header widget"""
        return Header()

    def create_footer(self):
        """Create the footer widget"""
        return Footer()

    def create_progress_panel(self):
        """Create the progress panel widget"""
        return ProgressPanel(self.sim, id="progress_panel")

    def create_control_panel(self):
        """Create the control panel widget"""
        return SimulationControlPanel(self.sim, id="control_panel")

    def create_config_panel(self):
        """Create the config panel widget"""
        return ConfigPanel(self.sim, id="config_panel")

    def on_mount(self) -> None:
        """Called when app starts"""
        self.title = f"Ridehail Simulation - {self.sim.config.title.value}"
        self.start_simulation()

    def start_simulation(self) -> None:
        """Start the simulation timer"""
        if not self.simulation_timer:
            try:
                # Use configurable frame_timeout from config for consistent timing across all animations
                frame_interval = self.sim.config.frame_timeout.value
                if frame_interval is None:
                    frame_interval = self.sim.config.frame_timeout.default

                self.simulation_timer = self.set_interval(
                    interval=frame_interval, callback=self.simulation_step, repeat=0
                )
            except Exception as e:
                logging.error(f"Simulation step failed: {e}")
                self.stop_simulation()
        else:
            with open("/tmp/textual_debug.log", "a") as f:
                f.write("simulation_timer already exists, not starting again\n")
                f.flush()

    def simulation_step(self) -> None:
        """Execute one simulation step"""
        # Increment step counter for debugging
        self._step_count = getattr(self, "_step_count", 0) + 1

        if self.is_paused:
            return

        try:
            print(f"base simulation step at index {self.sim.block_index}...")
            results = self.sim.next_block(
                jsonl_file_handle=None,
                csv_file_handle=None,
                return_values="stats",
                dispatch=self.animation.dispatch,
            )

            # Update title to show current progress
            self.title = f"Ridehail Simulation - Block {self.sim.block_index}/{self.sim.time_blocks}"

            # Update progress panel
            progress_panel = self.query_one("#progress_panel")
            progress_panel.update_progress(results)

            # Check if simulation is complete
            if (
                self.sim.time_blocks > 0
                and self.sim.block_index >= self.sim.time_blocks
            ):
                self.stop_simulation()

        except Exception as e:
            logging.error(f"Simulation step failed: {e}")
            self.stop_simulation()

    def stop_simulation(self) -> None:
        """Stop the simulation timer"""
        if self.simulation_timer:
            self.simulation_timer.stop()
            self.simulation_timer = None

    def on_simulation_paused(self, event: SimulationPaused) -> None:
        """Handle simulation pause/resume"""
        self.is_paused = event.is_paused

    def on_simulation_stopped(self, event: SimulationStopped) -> None:
        """Handle simulation stop"""
        self.stop_simulation()
        self.exit()

    def action_quit(self) -> None:
        """Quit the application"""
        self.stop_simulation()
        self.exit()

    def action_pause(self) -> None:
        """Toggle pause/resume"""
        self.is_paused = not self.is_paused

    def action_decrease_vehicles(self) -> None:
        """Decrease vehicle count by 1"""
        self.sim.target_state["vehicle_count"] = max(
            self.sim.target_state["vehicle_count"] - 1, 0
        )

    def action_increase_vehicles(self) -> None:
        """Increase vehicle count by 1"""
        self.sim.target_state["vehicle_count"] += 1

    def action_decrease_demand(self) -> None:
        """Decrease base demand by 0.1"""
        self.sim.target_state["base_demand"] = max(
            self.sim.target_state["base_demand"] - 0.1, 0
        )

    def action_increase_demand(self) -> None:
        """Increase base demand by 0.1"""
        self.sim.target_state["base_demand"] += 0.1


class TextualBasedAnimation(RideHailAnimation):
    """
    Base class for Textual-based terminal animations.
    Provides common functionality for TextualConsoleAnimation and TextualMapAnimation.
    """

    def __init__(self, sim):
        super().__init__(sim)
        self.app: Optional[RidehailTextualApp] = None
        self.textual_compatible = self._check_textual_compatibility()

    def _check_textual_compatibility(self) -> bool:
        """Check if terminal supports Textual features"""
        try:
            # Basic import test
            from textual.app import App

            return True
        except ImportError as e:
            logging.error(f"Textual not available: {e}")
            return False
        except Exception as e:
            logging.error(f"Textual compatibility check failed: {e}")
            return False

    def _fallback_animation(self):
        """Fallback to Rich-based animation for terminals that don't support Textual"""
        print("Warning: Terminal does not support Textual features.")
        print("Falling back to Rich-based animation...")

        # Import here to avoid circular imports
        from .console import ConsoleAnimation

        fallback = ConsoleAnimation(self.sim)
        fallback.animate()

    def create_app(self) -> RidehailTextualApp:
        """Create the Textual app instance (to be overridden by subclasses)"""
        return RidehailTextualApp(self.sim, animation=self)

    def animate(self):
        """Main animation loop using Textual app"""
        if not self.textual_compatible:
            self._fallback_animation()
            return

        try:
            self.app = self.create_app()
            self.app.run()
        except KeyboardInterrupt:
            logging.info("Animation interrupted by user")
        except Exception as e:
            logging.error(f"Textual animation failed: {e}")
            print(f"Textual animation error: {e}")
            print("Falling back to Rich-based animation...")
            self._fallback_animation()
        finally:
            if self.app:
                self.app.exit()
