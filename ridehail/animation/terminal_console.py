"""
Textual-based console animation for ridehail simulation.
"""

from typing import Dict, Any

from textual.app import ComposeResult
from textual.containers import Horizontal, Container
from textual.widgets import (
    Static,
    ProgressBar,
    Label,
    Footer,
    Sparkline,
)

from ridehail.atom import Measure, DispatchMethod, Equilibration
from .terminal_base import TextualBasedAnimation, RidehailTextualApp


class EnhancedProgressPanel(Container):
    """Enhanced progress display panel with all console animation metrics"""

    def __init__(self, sim, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim
        self.vehicle_count_history = []
        self.convergence_history = []
        self.gross_income = []
        self.net_income = []
        self.max_history_length = sim.results_window

    def compose(self) -> ComposeResult:
        yield Static("Simulation Statistics", classes="panel-title")

        # Main progress bar
        yield Static("Simulation Metrics", classes="subsection-title")
        with Horizontal(classes="progress-row"):
            yield Label(
                "Progress",
                classes="progress-label",
                id="main_progress_label",
            )
            yield ProgressBar(
                total=1.0,
                show_percentage=True,
                show_eta=False,
                classes="progress-bar",
                id="main_progress",
            )

        # Convergence bar
        with Horizontal(classes="progress-row"):
            yield Label(
                "Convergence",
                classes="progress-label",
                id="convergence_label",
            )
            # yield ProgressBar(
            # total=1.0,
            # show_percentage=True,
            # show_eta=False,
            # classes="progress-bar",
            # id="convergence_progress",
            # )
            yield Sparkline(
                data=[0.0],
                summary_function=max,
                classes="sparkline",
                id="convergence_sparkline",
            )
            yield Label("0", classes="sparkline-value", id="convergence_value")

        # Vehicle status bars
        yield Static("Vehicle Metrics", classes="subsection-title")
        with Horizontal(classes="progress-row"):
            yield Label("P1 (Idle)", classes="progress-label", id="vehicle_p1_label")
            yield ProgressBar(
                total=1.0,
                show_percentage=True,
                show_eta=False,
                classes="progress-bar",
                id="vehicle_p1",
            )
        with Horizontal(classes="progress-row"):
            yield Label(
                "P2 (Dispatched)", classes="progress-label", id="vehicle_p2_label"
            )
            yield ProgressBar(
                total=1.0,
                show_percentage=True,
                show_eta=False,
                classes="progress-bar",
                id="vehicle_p2",
            )
        with Horizontal(classes="progress-row"):
            yield Label(
                "P3 (Occupied)", classes="progress-label", id="vehicle_p3_label"
            )
            yield ProgressBar(
                total=1.0,
                show_percentage=True,
                show_eta=False,
                classes="progress-bar",
                id="vehicle_p3",
            )
        # Total vehicles
        with Horizontal(classes="progress-row"):
            yield Label("Vehicles", classes="progress-label", id="vehicle_count_label")
            yield Sparkline(
                data=[0.0],
                summary_function=max,
                classes="sparkline",
                id="vehicle_count_sparkline",
            )
            yield Label("0", classes="sparkline-value", id="vehicle_count_value")
        # Trip metrics
        yield Static("Trip Metrics", classes="subsection-title")
        with Horizontal(classes="progress-row"):
            yield Label(
                "Wait (% of Total Trip)",
                classes="progress-label",
                id="wait_fraction_label",
            )
            yield ProgressBar(
                total=1,
                show_percentage=True,
                show_eta=False,
                classes="progress-bar",
                id="wait_fraction",
            )
        with Horizontal(classes="progress-row"):
            yield Label(
                "Mean Trip Distance", classes="progress-label", id="ride_time_label"
            )
            yield ProgressBar(
                total=self.sim.city.city_size,
                show_percentage=False,
                show_eta=False,
                classes="progress-bar-no-percentage",
                id="ride_time",
            )
            yield Label("0", classes="sparkline-value", id="ride_time_value")
        # Dispatch metrics (conditional)
        if (
            self.sim.dispatch_method != DispatchMethod.DEFAULT
            and self.sim.use_advanced_dispatch
        ):
            yield Static("Dispatch Metrics", classes="subsection-title")
            with Horizontal(classes="progress-row"):
                yield Label("Forward Dispatches", classes="progress-label")
                yield ProgressBar(
                    total=1.0,
                    show_percentage=True,
                    show_eta=False,
                    classes="progress-bar",
                    id="dispatch_fraction",
                )
        # Income/Equilibrium metrics
        yield Static("Driver Economics", classes="subsection-title")
        with Horizontal(classes="progress-row"):
            if self.sim.use_city_scale:
                gross_income_label_text = "Gross Incime ($/hr)"
            else:
                gross_income_label_text = "Gross Income"
            yield Label(
                gross_income_label_text,
                classes="progress-label",
                id="gross_income_label",
            )
            yield Sparkline(
                data=[0.0],
                summary_function=max,
                classes="sparkline",
                id="gross_income_sparkline",
            )
            yield Label("0", classes="sparkline-value", id="gross_income_value")
        with Horizontal(classes="progress-row"):
            yield Label(
                "Net Income ($/hr)", classes="progress-label", id="net_income_label"
            )
            yield Sparkline(
                data=[0.0],
                summary_function=max,
                classes="sparkline",
                id="net_income_sparkline",
            )
            yield Label("0", classes="sparkline-value", id="net_income_value")
        if self.sim.equilibrate and self.sim.equilibration == Equilibration.PRICE:
            with Horizontal(classes="progress-row"):
                yield Label("Mean Surplus ($/hr)", classes="progress-label")
                yield ProgressBar(
                    total=100.0,
                    show_percentage=False,
                    classes="progress-bar",
                    id="mean_surplus",
                )
        with Horizontal(classes="progress-row"):
            yield Label("Mean Surplus", classes="progress-label")
            yield ProgressBar(
                total=self.sim.price,
                show_percentage=False,
                classes="progress-bar",
                id="mean_surplus",
            )

    def update_progress(self, results: Dict[str, Any]) -> None:
        """Update all progress bars with simulation results"""
        # ------------------------------------------------------------------------
        # Main progress
        if self.sim.time_blocks > 0:
            progress = results["block"] / self.sim.time_blocks
            self.query_one("#main_progress").update(progress=progress)
        # Convergence
        # self.query_one("#convergence_progress").update(
        # progress=results[Measure.CONVERGENCE_MAX_RMS_RESIDUAL.name]
        # )

        # ------------------------------------------------------------------------
        # Convergence
        convergence_value = results[Measure.SIM_CONVERGENCE_MAX_RMS_RESIDUAL.name]
        self.convergence_history.append(convergence_value)
        if len(self.convergence_history) > self.max_history_length:
            self.convergence_history.pop(0)
        sparkline = self.query_one("#convergence_sparkline", expect_type=Sparkline)
        if len(self.convergence_history) >= 1:
            sparkline.data = self.convergence_history.copy()
        convergence_value_label = self.query_one(
            "#convergence_value", expect_type=Label
        )
        convergence_value_label.update(f"{convergence_value:.3f}")

        # ------------------------------------------------------------------------
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

        # ------------------------------------------------------------------------
        # Trip metrics
        self.query_one("#wait_fraction").update(
            progress=results[Measure.TRIP_MEAN_WAIT_FRACTION_TOTAL.name]
        )
        mean_ride_time = results[Measure.TRIP_MEAN_RIDE_TIME.name]
        self.query_one("#ride_time").update(
            progress=results[Measure.TRIP_MEAN_RIDE_TIME.name]
        )
        ride_time_value = self.query_one("#ride_time_value", expect_type=Label)
        ride_time_value.update(f"{mean_ride_time:.0f}")

        # ------------------------------------------------------------------------
        # Dispatch metrics (if available)
        if (
            self.sim.dispatch_method != DispatchMethod.DEFAULT
            and self.sim.use_advanced_dispatch
        ):
            dispatch_bar = self.query_one("#dispatch_fraction", expect_type=ProgressBar)
            if dispatch_bar:
                dispatch_bar.update(
                    progress=results[Measure.TRIP_FORWARD_DISPATCH_FRACTION.name]
                )

        # ------------------------------------------------------------------------
        # Vehicle totals
        vehicle_mean_count = results[Measure.VEHICLE_MEAN_COUNT.name]
        # Update vehicle count history
        self.vehicle_count_history.append(vehicle_mean_count)
        if len(self.vehicle_count_history) > self.max_history_length:
            self.vehicle_count_history.pop(0)
        # Update vehicle count sparkline
        vehicle_count_sparkline = self.query_one(
            "#vehicle_count_sparkline", expect_type=Sparkline
        )
        if len(self.vehicle_count_history) >= 1:
            vehicle_count_sparkline.data = self.vehicle_count_history.copy()
        # Update current value display
        vehicle_count_value = self.query_one("#vehicle_count_value", expect_type=Label)
        vehicle_count_value.update(f"{vehicle_mean_count:.0f}")

        # ------------------------------------------------------------------------
        # Gross income
        gross_income_value = results[Measure.VEHICLE_GROSS_INCOME.name]
        self.gross_income.append(gross_income_value)
        if len(self.gross_income) > self.max_history_length:
            self.gross_income.pop(0)
        gross_income_sparkline = self.query_one(
            "#gross_income_sparkline", expect_type=Sparkline
        )
        if len(self.gross_income) >= 1:
            gross_income_sparkline.data = self.gross_income.copy()
        gross_income_value_label = self.query_one(
            "#gross_income_value", expect_type=Label
        )
        gross_income_value_label.update(f"{gross_income_value:.3f}")

        # ------------------------------------------------------------------------
        # Nat income
        net_income_value = results[Measure.VEHICLE_NET_INCOME.name]
        self.net_income.append(net_income_value)
        if len(self.net_income) > self.max_history_length:
            self.net_income.pop(0)
        net_income_sparkline = self.query_one(
            "#net_income_sparkline", expect_type=Sparkline
        )
        if len(self.net_income) >= 1:
            net_income_sparkline.data = self.net_income.copy()
        net_income_value_label = self.query_one("#net_income_value", expect_type=Label)
        net_income_value_label.update(f"{net_income_value:.3f}")

        # ------------------------------------------------------------------------
        # Price
        if self.sim.use_city_scale:
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


class TextualConsoleApp(RidehailTextualApp):
    """Enhanced Textual app for console animation with full feature parity"""

    CSS = (
        RidehailTextualApp.CSS
        + """
    /* Console-specific overrides and additions */

    Header {
        background: $secondary;  /* Console uses secondary for header */
    }

    #progress_panel {
        width: 2fr;
        border: solid $primary;
        padding: 0 1;
        margin: 0;
    }

    #config_panel {
        width: 1fr;  /* Console uses different width ratio than other animations */
    }

    .subsection-title {
        border-top: solid grey;  /* Console adds border to subsections */
        margin: 0 0 1 0;
    }

    .progress-bar {
        width: 1fr;
        max-width: 50;
    }

    .progress-bar-no-percentage {
        width: 1fr;
        max-width: 30;
    }

    .sparkline {
        width: 1fr;
        min-width: 10;
        max-width: 29;
    }

    .sparkline-value {
        width: 7;
        text-align: right;
        padding: 0 0 0 3;
    }

    .progress-row {
        width: 1fr;
        height: 1;
        margin: 0 0 1 0;
        align: left middle;
    }

    .progress_bar {
        margin: 0;
        width: 3fr;
        min-width: 30;
    }

    .progress_bar > #bar {
        width: 1fr;
    }

    /* progress bar and sparkline colours */

    #main_progress > #bar > .bar--bar {
        color: deepskyblue;
    }

    #convergence_sparkline > .sparkline--min-color {
        color: goldenrod;
    }

    #convergence_sparkline > .sparkline--max-color {
        color: goldenrod;
    }

    #vehicle_p1 > #bar > .bar--complete {
        color: deepskyblue;
    }

    #vehicle_p1 > #bar > .bar--bar {
        color: deepskyblue;
    }

    #vehicle_p2 > #bar > .bar--bar {
        color: goldenrod;
    }

    #vehicle_p3 > #bar > .bar--bar {
        color: limegreen;
    }

    #wait_fraction > #bar > .bar--complete {
        color: red;
    }

    #vehicle_count_sparkline > .sparkline--min-color {
        color: salmon;
    }

    #vehicle_count_sparkline > .sparkline--max-color {
        color: salmon;
    }

    #wait_fraction > #bar > .bar--bar {
        color: red;
    }

    #ride_time > #bar > .bar--bar {
        color: limegreen;
    }

    #gross_income_sparkline > .sparkline--min-color {
        color: deepskyblue;
    }

    #gross_income_sparkline > .sparkline--max-color {
        color: deepskyblue;
    }

    #net_income_sparkline > .sparkline--min-color {
        color: goldenrod;
    }

    #net_income_sparkline > .sparkline--max-color {
        color: goldenrod;
    }

    #convergence_value {
        width: 8;
        color: goldenrod;
    }

    #vehicle_count_value {
        color: salmon;
    }

    #ride_time_value {
        color: limegreen;
    }

    #gross_income_value {
        color: deepskyblue;
    }

    #net_income_value {
        color: goldenrod;
    }

    /* Simulation statistics labels: all progress-label class and then
       colour by ID */

    .progress-label {
        width: 25;
        text-align: left;
        margin: 0 1 0 0;
        padding: 0;
        text-style: none;
    }

    #main_progress_label {
        color: deepskyblue;
    }

    #convergence_label {
        color: goldenrod;
    }

    #vehicle_p1_label {
        color: deepskyblue;
    }

    #vehicle_p2_label {
        color: goldenrod;
    }

    #vehicle_p3_label {
        color: limegreen;
    }

    #vehicle_count_label {
        color: salmon;
    }

    #wait_fraction_label {
        color: red;
    }

    #ride_time_label {
        color: limegreen;
    }

    #gross_income_label {
        color: deepskyblue;
    }

    #net_income_label {
        color: goldenrod;
    }

    /* Progress bar percentage text labels */

    #main_progress > #percentage {
        color: deepskyblue;
    }

    #vehicle_p1 > #percentage {
        color: deepskyblue;
    }

    #vehicle_p2 > #percentage {
        color: goldenrod;
    }

    #vehicle_p3 > #percentage {
        color: limegreen;
    }

    #wait_fraction > #percentage {
        color: red;
    }

    #ride_time > #percentage {
        color: limegreen;
    }

    """
    )

    # Inherits BINDINGS from RidehailTextualApp base class
    # This ensures consistency across all animation types (console, map, stats)

    def compose(self) -> ComposeResult:
        """Create child widgets for the enhanced console app"""
        yield self.create_header()
        with Horizontal():
            yield EnhancedProgressPanel(self.sim, id="progress_panel")
            # yield InteractiveControlPanel(self.sim, id="control_panel")
            yield self.create_config_panel()
        yield Footer()

    def simulation_step(self) -> None:
        """Enhanced simulation step with better progress tracking"""
        handler = self.sim.get_keyboard_handler()
        if self.is_paused and not handler.should_step:
            return
        if handler.should_step:
            handler.should_step = False

        try:
            results = self.sim.next_block(
                jsonl_file_handle=None, csv_file_handle=None, return_values="stats"
            )

            # self.title = "Ridehail Console"

            # Update enhanced progress panel
            progress_panel = self.query_one("#progress_panel")
            progress_panel.update_progress(results)

            # Check if simulation is complete
            if (
                self.sim.time_blocks > 0
                and self.sim.block_index >= self.sim.time_blocks
            ):
                self.stop_simulation()

        except Exception as e:
            print(f"exception: {e}")
            self.stop_simulation()


class TextualConsoleAnimation(TextualBasedAnimation):
    """Enhanced Textual-based console animation with full Rich feature parity"""

    def create_app(self) -> TextualConsoleApp:
        """Create the enhanced Textual console app instance"""
        return TextualConsoleApp(self.sim, animation=self)
