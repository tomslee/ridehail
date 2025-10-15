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
        self.max_history_length = sim.results_window

    def compose(self) -> ComposeResult:
        yield Static("Simulation Statistics", classes="panel-title")

        # Main progress bar
        yield Static("Simulation Metrics", classes="subsection-title")
        with Horizontal(classes="progress-row"):
            yield Label(
                "Simulation Progress",
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
                "Simulation Convergence",
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
                classes="progress-sparkline",
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
                classes="progress-sparkline",
                id="vehicle_count_sparkline",
            )
            yield Label("0", classes="sparkline-value", id="vehicle_count_value")

        # Trip metrics
        yield Static("Trip Metrics", classes="subsection-title")
        with Horizontal(classes="progress-row"):
            yield Label(
                "Mean Wait Time", classes="progress-label", id="wait_time_label"
            )
            yield ProgressBar(
                total=self.sim.city.city_size,
                show_percentage=True,
                show_eta=False,
                classes="progress-bar",
                id="wait_time",
            )
        with Horizontal(classes="progress-row"):
            yield Label(
                "Mean Ride Time", classes="progress-label", id="ride_time_label"
            )
            yield ProgressBar(
                total=self.sim.city.city_size,
                show_percentage=True,
                show_eta=False,
                classes="progress-bar",
                id="ride_time",
            )

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
        if self.sim.use_city_scale:
            with Horizontal(classes="progress-row"):
                yield Label("Gross Income ($/hr)", classes="progress-label")
                yield ProgressBar(
                    total=100.0,
                    show_percentage=False,
                    classes="progress-bar",
                    id="gross_income",
                )
            with Horizontal(classes="progress-row"):
                yield Label("Net Income ($/hr)", classes="progress-label")
                yield ProgressBar(
                    total=100.0,
                    show_percentage=False,
                    classes="progress-bar",
                    id="net_income",
                )
            if self.sim.equilibrate and self.sim.equilibration == Equilibration.PRICE:
                with Horizontal(classes="progress-row"):
                    yield Label("Mean Surplus ($/hr)", classes="progress-label")
                    yield ProgressBar(
                        total=100.0,
                        show_percentage=False,
                        classes="progress-bar",
                        id="mean_surplus",
                    )
        else:
            with Horizontal(classes="progress-row"):
                yield Label("Gross Income", classes="progress-label")
                yield ProgressBar(
                    total=self.sim.price,
                    show_percentage=False,
                    classes="progress-bar",
                    id="gross_income",
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
        # Main progress
        if self.sim.time_blocks > 0:
            progress = results["block"] / self.sim.time_blocks
            self.query_one("#main_progress").update(progress=progress)
        # Convergence
        # self.query_one("#convergence_progress").update(
        # progress=results[Measure.CONVERGENCE_MAX_RMS_RESIDUAL.name]
        # )
        # Update sparkline
        convergence_value = results[Measure.CONVERGENCE_MAX_RMS_RESIDUAL.name]
        self.convergence_history.append(convergence_value)
        if len(self.convergence_history) > self.max_history_length:
            self.convergence_history.pop(0)
        sparkline = self.query_one("#convergence_sparkline", expect_type=Sparkline)
        if len(self.convergence_history) >= 1:
            sparkline.data = self.convergence_history.copy()
        # Update current value display
        convergence_value_label = self.query_one(
            "#convergence_value", expect_type=Label
        )
        convergence_value_label.update(f"{convergence_value:.3f}")

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
        if (
            self.sim.dispatch_method != DispatchMethod.DEFAULT
            and self.sim.use_advanced_dispatch
        ):
            dispatch_bar = self.query_one("#dispatch_fraction", expect_type=ProgressBar)
            if dispatch_bar:
                dispatch_bar.update(
                    progress=results[Measure.TRIP_FORWARD_DISPATCH_FRACTION.name]
                )

        # Vehicle totals
        vehicle_mean_count = results[Measure.VEHICLE_MEAN_COUNT.name]

        # Update vehicle count history
        self.vehicle_count_history.append(vehicle_mean_count)
        if len(self.vehicle_count_history) > self.max_history_length:
            self.vehicle_count_history.pop(0)

        # Update sparkline
        sparkline = self.query_one("#vehicle_count_sparkline", expect_type=Sparkline)
        if len(self.vehicle_count_history) >= 1:
            sparkline.data = self.vehicle_count_history.copy()
        # Update current value display
        vehicle_value_label = self.query_one("#vehicle_count_value", expect_type=Label)
        vehicle_value_label.update(f"{vehicle_mean_count:.0f}")

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

    .progress-sparkline {
        width: 1fr;
        max-width: 40;
    }

    #convergence_sparkline {
        min-width: 10;
        max-width: 29;
        width: 1fr;
    }

    #convergence_sparkline > .sparkline--min-color {
        color: goldenrod;
    }

    #convergence_sparkline > .sparkline--max-color {
        color: goldenrod;
    }

    #convergence_value {
        width: 8;
        text-align: right;
        color: goldenrod;
        padding: 0 0 0 3;
    }


    #vehicle_count_sparkline {
        min-width: 10;
        max-width: 30;
        width: 1fr;
    }

    #vehicle_count_sparkline > .sparkline--min-color {
        color: salmon;
    }

    #vehicle_count_sparkline > .sparkline--max-color {
        color: salmon;
    }

    #vehicle_count_value {
        width: 7;
        text-align: right;
        color: salmon;
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

    /* progress bar colors */

    #main_progress > #bar > .bar--bar {
        color: deepskyblue;
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

    #wait_time > #bar > .bar--complete {
        color: goldenrod;
    }

    #wait_time > #bar > .bar--bar {
        color: goldenrod;
    }

    #ride_time > #bar > .bar--bar {
        color: limegreen;
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

    #wait_time_label {
        color: goldenrod;
    }

    #ride_time_label {
        color: limegreen;
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

    #wait_time > #percentage {
        color: salmon;
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
