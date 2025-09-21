"""
Textual-based console animation for ridehail simulation.
"""

from typing import Dict, Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical, Container
from textual.widgets import (
    TabbedContent,
    TabPane,
    Static,
    ProgressBar,
    Label,
    Button,
    DataTable,
    Header,
    Footer,
)
from textual.reactive import reactive

from ridehail.atom import Measure, CityScaleUnit, DispatchMethod, Equilibration
from ridehail.dispatch import Dispatch
from .textual_base import TextualBasedAnimation, RidehailTextualApp


class EnhancedProgressPanel(Container):
    """Enhanced progress display panel with all console animation metrics"""

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

        # Dispatch metrics (conditional)
        if self.sim.dispatch_method in (
            DispatchMethod.FORWARD_DISPATCH,
            DispatchMethod.DEFAULT,
        ):
            yield Static("Dispatch Metrics", classes="subsection-title")
            yield Label("Forward Dispatch Fraction")
            yield ProgressBar(total=1.0, show_percentage=True, id="dispatch_fraction")

        # Total vehicles
        yield Static("Vehicle Totals", classes="subsection-title")
        yield Label("Mean Vehicle Count")
        yield ProgressBar(
            total=self.sim.vehicle_count * 2, show_percentage=False, id="vehicle_total"
        )

        # Income/Equilibrium metrics
        yield Static("Driver Economics", classes="subsection-title")
        if self.sim.use_city_scale:
            yield Label("Gross Income ($/hr)")
            yield ProgressBar(total=100.0, show_percentage=False, id="gross_income")
            yield Label("Net Income ($/hr)")
            yield ProgressBar(total=100.0, show_percentage=False, id="net_income")
            if self.sim.equilibrate and self.sim.equilibration == Equilibration.PRICE:
                yield Label("Mean Surplus ($/hr)")
                yield ProgressBar(total=100.0, show_percentage=False, id="mean_surplus")
        else:
            yield Label("Gross Income")
            yield ProgressBar(
                total=self.sim.price, show_percentage=False, id="gross_income"
            )
            yield Label("Mean Surplus")
            yield ProgressBar(
                total=self.sim.price, show_percentage=False, id="mean_surplus"
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

        # Dispatch metrics (if available)
        if self.sim.dispatch_method in (
            DispatchMethod.FORWARD_DISPATCH,
            DispatchMethod.DEFAULT,
        ):
            dispatch_bar = self.query_one("#dispatch_fraction", expect_type=ProgressBar)
            if dispatch_bar:
                dispatch_bar.update(
                    progress=results[Measure.TRIP_FORWARD_DISPATCH_FRACTION.name]
                )

        # Vehicle totals
        vehicle_total_bar = self.query_one("#vehicle_total", expect_type=ProgressBar)
        if vehicle_total_bar:
            mean_count = results[Measure.VEHICLE_MEAN_COUNT.name]
            total = (
                int(mean_count / self.sim.vehicle_count) + 1
            ) * self.sim.vehicle_count
            vehicle_total_bar.update(progress=mean_count, total=total)

        # Income metrics
        gross_income_bar = self.query_one("#gross_income", expect_type=ProgressBar)
        if gross_income_bar:
            gross_income_bar.update(progress=results[Measure.VEHICLE_GROSS_INCOME.name])

        if self.sim.use_city_scale:
            net_income_bar = self.query_one("#net_income", expect_type=ProgressBar)
            if net_income_bar:
                net_income_bar.update(progress=results[Measure.VEHICLE_NET_INCOME.name])

            if self.sim.equilibrate and self.sim.equilibration == Equilibration.PRICE:
                surplus_bar = self.query_one("#mean_surplus", expect_type=ProgressBar)
                if surplus_bar:
                    surplus_bar.update(
                        progress=results[Measure.VEHICLE_MEAN_SURPLUS.name]
                    )
        else:
            surplus_bar = self.query_one("#mean_surplus", expect_type=ProgressBar)
            if surplus_bar:
                surplus_bar.update(progress=results[Measure.VEHICLE_MEAN_SURPLUS.name])


class InteractiveControlPanel(Container):
    """Enhanced control panel with real-time parameter adjustment"""

    def __init__(self, sim, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim
        self.is_paused = False

    def compose(self) -> ComposeResult:
        yield Static("Simulation Controls", classes="panel-title")

        # Playback controls
        with Horizontal(classes="control-buttons"):
            yield Button("⏸️ Pause", id="pause_btn", variant="primary")
            yield Button("⏹️ Stop", id="stop_btn", variant="error")
            yield Button("📊 Stats", id="stats_btn")

        # Vehicle count controls
        yield Static("Vehicle Count", classes="control-section-title")
        with Horizontal(classes="control-row"):
            yield Button("-10", id="vehicles_minus_10", classes="small-btn")
            yield Button("-1", id="vehicles_minus_1", classes="small-btn")
            yield Label(
                str(self.sim.vehicle_count),
                id="vehicle_count_display",
                classes="value-display",
            )
            yield Button("+1", id="vehicles_plus_1", classes="small-btn")
            yield Button("+10", id="vehicles_plus_10", classes="small-btn")

        # Demand controls
        yield Static("Base Demand", classes="control-section-title")
        with Horizontal(classes="control-row"):
            yield Button("-0.5", id="demand_minus_half", classes="small-btn")
            yield Button("-0.1", id="demand_minus", classes="small-btn")
            yield Label(
                f"{self.sim.base_demand:.1f}",
                id="demand_display",
                classes="value-display",
            )
            yield Button("+0.1", id="demand_plus", classes="small-btn")
            yield Button("+0.5", id="demand_plus_half", classes="small-btn")

        # City size controls
        yield Static("City Size", classes="control-section-title")
        with Horizontal(classes="control-row"):
            yield Button("-5", id="city_minus_5", classes="small-btn")
            yield Button("-1", id="city_minus_1", classes="small-btn")
            yield Label(
                str(self.sim.city.city_size),
                id="city_size_display",
                classes="value-display",
            )
            yield Button("+1", id="city_plus_1", classes="small-btn")
            yield Button("+5", id="city_plus_5", classes="small-btn")

        # Keyboard shortcuts info
        yield Static("Keyboard Shortcuts", classes="control-section-title")
        shortcuts_table = DataTable(
            show_header=False, zebra_stripes=True, classes="shortcuts-table"
        )
        shortcuts_table.add_column("Key", width=8)
        shortcuts_table.add_column("Action", width=20)
        shortcuts_table.add_rows(
            [
                ("Space", "Pause/Resume"),
                ("Q", "Quit"),
                ("N/n", "Vehicle +/-"),
                ("K/k", "Demand +/-"),
                ("C/c", "City +/-"),
            ]
        )
        yield shortcuts_table

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses for simulation control"""
        button_id = event.button.id

        if button_id == "pause_btn":
            self.is_paused = not self.is_paused
            event.button.label = "▶️ Resume" if self.is_paused else "⏸️ Pause"
            self.post_message(self.SimulationPaused(self.is_paused))

        elif button_id == "stop_btn":
            self.post_message(self.SimulationStopped())

        elif button_id == "vehicles_minus_10":
            self._adjust_vehicles(-10)
        elif button_id == "vehicles_minus_1":
            self._adjust_vehicles(-1)
        elif button_id == "vehicles_plus_1":
            self._adjust_vehicles(1)
        elif button_id == "vehicles_plus_10":
            self._adjust_vehicles(10)

        elif button_id == "demand_minus_half":
            self._adjust_demand(-0.5)
        elif button_id == "demand_minus":
            self._adjust_demand(-0.1)
        elif button_id == "demand_plus":
            self._adjust_demand(0.1)
        elif button_id == "demand_plus_half":
            self._adjust_demand(0.5)

        elif button_id == "city_minus_5":
            self._adjust_city_size(-5)
        elif button_id == "city_minus_1":
            self._adjust_city_size(-1)
        elif button_id == "city_plus_1":
            self._adjust_city_size(1)
        elif button_id == "city_plus_5":
            self._adjust_city_size(5)

    def _adjust_vehicles(self, change: int):
        """Adjust vehicle count"""
        self.sim.target_state["vehicle_count"] = max(
            self.sim.target_state["vehicle_count"] + change, 0
        )
        self.query_one("#vehicle_count_display").update(
            str(self.sim.target_state["vehicle_count"])
        )

    def _adjust_demand(self, change: float):
        """Adjust base demand"""
        self.sim.target_state["base_demand"] = max(
            self.sim.target_state["base_demand"] + change, 0
        )
        self.query_one("#demand_display").update(
            f"{self.sim.target_state['base_demand']:.1f}"
        )

    def _adjust_city_size(self, change: int):
        """Adjust city size"""
        new_size = max(
            self.sim.target_state.get("city_size", self.sim.city.city_size) + change, 2
        )
        self.sim.target_state["city_size"] = new_size
        self.query_one("#city_size_display").update(str(new_size))

    class SimulationPaused:
        def __init__(self, is_paused: bool):
            self.is_paused = is_paused

    class SimulationStopped:
        pass


class TextualConsoleApp(RidehailTextualApp):
    """Enhanced Textual app for console animation with full feature parity"""

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
        color: $accent;
    }

    .control-section-title {
        text-style: bold;
        margin: 1 0 0 0;
        color: $secondary;
    }

    .control-buttons {
        height: 3;
        margin: 1 0;
    }

    .control-row {
        height: 3;
        margin: 0 0 1 0;
    }

    .small-btn {
        width: 8;
        margin: 0 1;
    }

    .value-display {
        width: 10;
        text-align: center;
        background: $surface;
        border: solid $primary;
        margin: 0 1;
        padding: 0 1;
    }

    .shortcuts-table {
        height: 8;
        margin: 1 0;
    }

    .left-panel {
        width: 1fr;
    }

    .right-panel {
        width: 1fr;
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
        ("ctrl+n", "decrease_vehicles_10", "Vehicles -10"),
        ("ctrl+N", "increase_vehicles_10", "Vehicles +10"),
        ("k", "decrease_demand", "Demand -0.1"),
        ("K", "increase_demand", "Demand +0.1"),
        ("c", "decrease_city", "City -1"),
        ("C", "increase_city", "City +1"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the enhanced console app"""
        yield Header()

        with TabbedContent(initial="main"):
            with TabPane("Console Dashboard", id="main"):
                with Horizontal():
                    with Vertical(classes="left-panel"):
                        yield EnhancedProgressPanel(self.sim, id="progress_panel")
                    with Vertical(classes="right-panel"):
                        yield InteractiveControlPanel(self.sim, id="control_panel")
                        yield self.create_config_panel()

        yield Footer()

    def create_progress_panel(self):
        """Override to use enhanced progress panel"""
        return EnhancedProgressPanel(self.sim, id="progress_panel")

    def create_control_panel(self):
        """Override to use interactive control panel"""
        return InteractiveControlPanel(self.sim, id="control_panel")

    def simulation_step(self) -> None:
        """Enhanced simulation step with better progress tracking"""
        if self.is_paused:
            return

        try:
            print(f"console simulation step {self.sim.block_index}", flush=True)
            print(f"sim.dispatch={self.animation.dispatch}", flush=True)
            results = self.sim.next_block(
                jsonl_file_handle=None,
                csv_file_handle=None,
                return_values="stats",
                dispatch=self.animation.dispatch,
            )

            # Update title to show progress
            self.title = (
                "Ridehail Console - "
                f"Block {self.sim.block_index}/{self.sim.time_blocks}"
            )

            # Update enhanced progress panel
            print("update progress panel...", flush=True)
            progress_panel = self.query_one("#progress_panel")
            progress_panel.update_progress(results)

            # Check if simulation is complete
            if (
                self.sim.time_blocks > 0
                and self.sim.block_index >= self.sim.time_blocks
            ):
                print("stopping simulation", flush=True)
                self.stop_simulation()

        except Exception as e:
            print(f"exception: {e}")
            self.stop_simulation()

    # Enhanced keyboard actions
    def action_decrease_vehicles_10(self) -> None:
        """Decrease vehicle count by 10"""
        control_panel = self.query_one("#control_panel")
        control_panel._adjust_vehicles(-10)

    def action_increase_vehicles_10(self) -> None:
        """Increase vehicle count by 10"""
        control_panel = self.query_one("#control_panel")
        control_panel._adjust_vehicles(10)

    def action_decrease_city(self) -> None:
        """Decrease city size by 1"""
        control_panel = self.query_one("#control_panel")
        control_panel._adjust_city_size(-1)

    def action_increase_city(self) -> None:
        """Increase city size by 1"""
        control_panel = self.query_one("#control_panel")
        control_panel._adjust_city_size(1)


class TextualConsoleAnimation(TextualBasedAnimation):
    """Enhanced Textual-based console animation with full Rich feature parity"""

    def create_app(self) -> TextualConsoleApp:
        """Create the enhanced Textual console app instance"""
        return TextualConsoleApp(self.sim, animation=self)
