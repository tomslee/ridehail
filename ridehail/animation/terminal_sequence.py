"""
Textual-based sequence animation for ridehail simulation using plotext.
Provides real-time scatter plot visualization of parameter sweep results.
"""

import logging
import copy
from typing import Dict

from textual.app import ComposeResult
from textual.containers import Container, Vertical
from textual.widgets import Header, Footer
from textual_plotext import PlotextPlot


from ridehail.simulation import RideHailSimulation
from ridehail.atom import DispatchMethod
from .terminal_base import TextualBasedAnimation, RidehailTextualApp

CHART_MARKER_CHARACTER = "\u25cf"  # Solid circle
DATA_THRESHOLD_MIN = 0.0001  # Minimum value threshold for plotting data
DATA_THRESHOLD_MAX = 1.0  # Maximum value threshold for plotting data


class SequenceChartWidget(Container):
    """Container for the plotext-based sequence chart"""

    def __init__(self, sim, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim
        self.config = sim.config

        # Initialize sequence parameters (ported from RideHailSimulationSequence)
        self._initialize_sequence_parameters()

        # Create lists to hold the sequence plot data
        self.vehicle_p1_fraction = []
        self.vehicle_p2_fraction = []
        self.vehicle_p3_fraction = []
        self.mean_vehicle_count = []
        self.trip_wait_fraction = []
        self.mean_ride_time = []
        self.forward_dispatch_fraction = []

        self.current_simulation_index = 0
        self.dispatch_method = self.config.dispatch_method.value.value

    def _initialize_sequence_parameters(self):
        """Initialize sequence parameter ranges based on config (ported from RideHailSimulationSequence.__init__)"""
        config = self.config

        # Initialize with base values
        self.vehicle_counts = [config.vehicle_count.value]
        self.request_rates = [config.base_demand.value]
        self.inhomogeneities = [config.inhomogeneity.value]
        self.commissions = [config.platform_commission.value]

        # Expand ranges if increments and max values are specified
        if config.vehicle_count_increment.value and config.vehicle_count_max.value:
            self.vehicle_counts = [
                x
                for x in range(
                    config.vehicle_count.value,
                    config.vehicle_count_max.value + 1,
                    config.vehicle_count_increment.value,
                )
            ]

        if config.request_rate_increment.value and config.request_rate_max.value:
            # Request rates managed to two decimal places
            self.request_rates = [
                x * 0.01
                for x in range(
                    int(100 * config.base_demand.value),
                    int(100 * (config.request_rate_max.value + 1)),
                    int(100 * config.request_rate_increment.value),
                )
            ]

        if config.inhomogeneity_increment.value and config.inhomogeneity_max.value:
            # Inhomogeneities managed to two decimal places
            self.inhomogeneities = [
                x * 0.01
                for x in range(
                    int(100 * config.inhomogeneity.value),
                    int(100 * (config.inhomogeneity_max.value) + 1),
                    int(100 * config.inhomogeneity_increment.value),
                )
            ]

        if config.commission_increment.value and config.commission_max.value:
            # Commissions managed to two decimal places
            self.commissions = [
                x * 0.01
                for x in range(
                    int(100 * config.platform_commission.value),
                    int(100 * (config.commission_max.value + 0.01)),
                    int(100 * config.commission_increment.value),
                )
            ]

        # Calculate total frame count
        self.frame_count = (
            len(self.vehicle_counts)
            * len(self.request_rates)
            * len(self.inhomogeneities)
            * len(self.commissions)
        )

    def compose(self) -> ComposeResult:
        yield PlotextPlot(id="sequence_plot")

    def update_chart(self, simulation_results=None):
        """Update the chart with new simulation results"""
        chart_widget = self.query_one("#sequence_plot", PlotextPlot)

        if simulation_results:
            self._collect_sim_results(simulation_results)

        # Configure chart
        self._configure_chart(chart_widget)

        # Plot current data
        self._plot_metrics(chart_widget)

        chart_widget.refresh()

    def _collect_sim_results(self, results):
        end_state = results.get_end_state()
        """Collect results from completed simulation (ported from sequence.py)"""
        self.vehicle_p1_fraction.append(end_state["vehicles"]["fraction_p1"])
        self.vehicle_p2_fraction.append(end_state["vehicles"]["fraction_p2"])
        self.vehicle_p3_fraction.append(end_state["vehicles"]["fraction_p3"])
        self.trip_wait_fraction.append(end_state["trips"]["mean_wait_fraction_total"])
        self.mean_ride_time.append(
            end_state["trips"]["mean_ride_time"] / self.sim.city_size
        )
        self.mean_vehicle_count.append(end_state["vehicles"]["mean_count"])

        if self.dispatch_method == DispatchMethod.FORWARD_DISPATCH.value:
            self.forward_dispatch_fraction.append(
                end_state["trips"]["forward_dispatch_fraction"]
            )

    def _configure_chart(self, chart_widget):
        """Configure chart axes and appearance"""
        plt = chart_widget.plt
        plt.clear_data()
        plt.clear_figure()

        # Determine x-axis based on which parameter is varying
        # Use full parameter range for limits, sliced range for plotting
        if len(self.vehicle_counts) > 1:
            x_data_full = self.vehicle_counts
            x_data = self.vehicle_counts[: len(self.vehicle_p1_fraction)]
            x_label = "Vehicle Count"
        elif len(self.request_rates) > 1:
            x_data_full = self.request_rates
            x_data = self.request_rates[: len(self.vehicle_p1_fraction)]
            x_label = "Request Rate"
        elif len(self.inhomogeneities) > 1:
            x_data_full = self.inhomogeneities
            x_data = self.inhomogeneities[: len(self.vehicle_p1_fraction)]
            x_label = "Inhomogeneity"
        elif len(self.commissions) > 1:
            x_data_full = self.commissions
            x_data = self.commissions[: len(self.vehicle_p1_fraction)]
            x_label = "Commission"
        else:
            x_data_full = list(range(self.frame_count))
            x_data = list(range(len(self.vehicle_p1_fraction)))
            x_label = "Simulation Index"

        self.x_data = x_data

        # Configure plot
        plt.xlabel(x_label)
        plt.ylabel("Fractional Values")

        # Use config title with progress indicator
        plt.title(
            f"{self.config.title.value} - {len(self.vehicle_p1_fraction)} of {self.frame_count} simulations"
        )

        # Set x-axis limits to full range (known from start)
        if len(x_data_full) > 0:
            plt.xlim(
                min(x_data_full),
                max(x_data_full) if len(x_data_full) > 1 else max(x_data_full) + 1,
            )
        plt.ylim(0, 1.1)

    def _plot_metrics(self, chart_widget):
        """Plot the sequence metrics as scatter plots"""
        plt = chart_widget.plt

        data_length = len(self.vehicle_p1_fraction)
        if data_length == 0:
            return

        # Ensure x_data exists and has correct length
        if not hasattr(self, "x_data") or len(self.x_data) == 0:
            return

        x_data = self.x_data[:data_length]

        # Additional safety check: ensure x_data and y_data have same length
        if len(x_data) != data_length:
            logging.warning(
                f"x_data length ({len(x_data)}) doesn't match data_length ({data_length})"
            )
            return

        # Only show labels (legend) once we have at least 2 data points
        # This works around a plotext bug with legend rendering on first data point
        show_labels = data_length >= 2

        # Plot P1 (blue) - only if we have data
        if len(self.vehicle_p1_fraction) > 0 and len(x_data) > 0:
            y_data = self.vehicle_p1_fraction
            if any(y > DATA_THRESHOLD_MIN for y in y_data) and any(
                y < DATA_THRESHOLD_MAX for y in y_data
            ):
                plt.scatter(
                    x_data,
                    y_data,
                    marker=CHART_MARKER_CHARACTER,
                    color="blue",
                    label="P1 (available)" if show_labels else None,
                )

        # Plot P2 (orange) - only if we have data
        if len(self.vehicle_p2_fraction) > 0 and len(x_data) > 0:
            y_data = self.vehicle_p2_fraction
            if any(y > DATA_THRESHOLD_MIN for y in y_data) and any(
                y < DATA_THRESHOLD_MAX for y in y_data
            ):
                plt.scatter(
                    x_data,
                    y_data,
                    marker=CHART_MARKER_CHARACTER,
                    color="orange",
                    label="P2 (en route)" if show_labels else None,
                )

        # Plot P3 (green) - only if we have data
        if len(self.vehicle_p3_fraction) > 0 and len(x_data) > 0:
            y_data = self.vehicle_p3_fraction
            if any(y > DATA_THRESHOLD_MIN for y in y_data) and any(
                y < DATA_THRESHOLD_MAX for y in y_data
            ):
                plt.scatter(
                    x_data,
                    y_data,
                    marker=CHART_MARKER_CHARACTER,
                    color="green",
                    label="P3 (busy)" if show_labels else None,
                )

        # Plot wait fraction - only if we have data
        if len(self.trip_wait_fraction) > 0 and len(x_data) > 0:
            y_data = self.trip_wait_fraction
            if any(y > DATA_THRESHOLD_MIN for y in y_data) and any(
                y < DATA_THRESHOLD_MAX for y in y_data
            ):
                plt.scatter(
                    x_data,
                    y_data,
                    marker=CHART_MARKER_CHARACTER,
                    color="red",
                    label="Wait fraction of total" if show_labels else None,
                )

        # Plot trip lentgh - only if we have data
        if len(self.mean_ride_time) > 0 and len(x_data) > 0:
            y_data = self.mean_ride_time
            if any(y > DATA_THRESHOLD_MIN for y in y_data) and any(
                y < DATA_THRESHOLD_MAX for y in y_data
            ):
                plt.scatter(
                    x_data,
                    y_data,
                    marker=CHART_MARKER_CHARACTER,
                    color="gray",
                    label="Trip distance / C" if show_labels else None,
                )

        # Plot forward dispatch if available - only if we have data
        if (
            self.dispatch_method == DispatchMethod.FORWARD_DISPATCH.value
            and len(self.forward_dispatch_fraction) > 0
            and len(x_data) > 0
        ):
            y_data = self.forward_disatch_fraction
            if any(y > DATA_THRESHOLD_MIN for y in y_data) and any(
                y < DATA_THRESHOLD_MAX for y in y_data
            ):
                plt.scatter(
                    x_data,
                    y_data,
                    marker="o",
                    color="purple",
                    label="Forward dispatch" if show_labels else None,
                )


class TextualSequenceAnimation(TextualBasedAnimation):
    """
    Textual-based sequence animation using plotext for terminal visualization.
    Runs parameter sweeps and displays results as real-time scatter plots.
    """

    def __init__(self, sim):
        super().__init__(sim)
        self.sequence_widget = None
        self.sequence_iterator = None
        self.app = None  # Will be set when app is created

    def create_app(self):
        """Create the Textual application for sequence animation"""
        app = RidehailSequenceTextualApp(self)
        self.app = app
        return app

    def compose(self) -> ComposeResult:
        """Create the layout for the sequence animation app"""
        from textual.containers import Horizontal
        from .terminal_base import ConfigPanel

        with Vertical():
            # Use base class header creation for consistency
            yield self.app.create_header()

            # Check if terminal is wide enough for config panel
            terminal_width = (
                self.app.console.size.width if hasattr(self.app.console, "size") else 80
            )

            if terminal_width >= 100:
                # Two-column layout with config panel
                with Horizontal(id="layout_container"):
                    yield self._create_sequence_widget()
                    yield ConfigPanel(self.sim, id="config_panel")
            else:
                # Single-column layout (current behavior)
                yield self._create_sequence_widget()

            yield Footer()

    def _create_sequence_widget(self) -> SequenceChartWidget:
        """Create and configure the sequence chart widget"""
        self.sequence_widget = SequenceChartWidget(self.sim, classes="chart-container")
        return self.sequence_widget

    def on_ready(self) -> None:
        """Initialize the sequence when the app is ready"""
        self._start_sequence()

    def _start_sequence(self):
        """Start the sequence of simulations"""
        if not self.sequence_widget:
            logging.error("Sequence widget not initialized")
            return

        # Initialize sequence iterator
        self.sequence_iterator = self._sequence_generator()

        # Start first simulation
        self._run_next_simulation()

    def _sequence_generator(self):
        """Generator that yields parameter combinations for sequence"""
        widget = self.sequence_widget

        for request_rate in widget.request_rates:
            for vehicle_count in widget.vehicle_counts:
                for inhomogeneity in widget.inhomogeneities:
                    for commission in widget.commissions:
                        yield {
                            "request_rate": request_rate,
                            "vehicle_count": vehicle_count,
                            "inhomogeneity": inhomogeneity,
                            "commission": commission,
                        }

    def _run_next_simulation(self):
        """Run the next simulation in the sequence"""
        # Check if sequence is paused
        if self.app.sequence_paused:
            # Wait a bit and check again
            self.app.set_timer(0.5, self._run_next_simulation)
            return

        try:
            params = next(self.sequence_iterator)
            sim_index = self.sequence_widget.current_simulation_index + 1
            total_sims = self.sequence_widget.frame_count

            # Create and run simulation with current parameters
            sim_config = self._create_simulation_config(params)
            simulation = RideHailSimulation(sim_config)
            results = simulation.simulate()

            # Update chart with results (chart_widget.refresh() is called internally)
            self.sequence_widget.update_chart(results)
            self.sequence_widget.current_simulation_index += 1

            # Schedule next simulation using the app's call_later
            if (
                self.sequence_widget.current_simulation_index
                < self.sequence_widget.frame_count
            ):
                # Add delay to allow UI refresh between simulations
                self.app.set_timer(0.1, self._run_next_simulation)

        except StopIteration:
            pass  # Sequence complete

    def _resume_sequence(self):
        """Resume sequence execution after pause"""
        # Trigger the next simulation immediately
        self.app.set_timer(0.1, self._run_next_simulation)

    def _create_simulation_config(self, params: Dict[str, float]):
        """Create a simulation config with the specified parameters"""
        from ridehail.atom import Animation

        # Create a copy of the current config
        sim_config = copy.deepcopy(self.sim.config)

        # Update parameters
        sim_config.base_demand.value = params["request_rate"]
        sim_config.vehicle_count.value = int(params["vehicle_count"])
        sim_config.inhomogeneity.value = params["inhomogeneity"]
        sim_config.platform_commission.value = params["commission"]

        # CRITICAL: Set animation style to NONE to run simulation completely without animation
        # This matches the behavior in sequence.py line 226
        sim_config.animation.value = Animation.NONE

        return sim_config


class RidehailSequenceTextualApp(RidehailTextualApp, inherit_bindings=False):
    """Textual app specifically for sequence animation"""

    # Override base class BINDINGS with sequence-appropriate controls
    # Setting inherit_bindings=False prevents parent bindings from being merged
    BINDINGS = [
        ("q", "quit", "Quit"),
        ("space", "pause_sequence", "Pause Sequence"),
        ("r", "restart_sequence", "Restart"),
        ("question_mark", "show_help", "Help"),
        ("h", "show_help", "Help"),
        ("z", "toggle_config_panel", "Toggle Config Panel"),
    ]

    def __init__(self, animation_instance: TextualSequenceAnimation):
        super().__init__(animation_instance.sim, animation=animation_instance)
        self.sequence_paused = False

    def start_simulation(self) -> None:
        """Override to prevent base class timer - sequence manages its own execution.

        The sequence animation uses set_timer() calls in _run_next_simulation()
        to control execution flow, rather than the base class's interval timer.
        This prevents the repeated simulation_step() calls after sequence completion.
        """
        # Don't call super() - no interval timer needed for sequence animation
        pass

    CSS = (
        RidehailTextualApp.CSS
        + """
        /* Sequence-specific styling */

        .chart-container {
            width: 1fr;
            height: 1fr;
            border: solid $primary;
            background: $panel;
        }

        .chart-title {
            height: 1;
            content-align: center middle;
            background: $primary;
            color: $text;
        }
        """
    )

    def on_mount(self) -> None:
        """Called when app starts"""
        # Set consistent header title (matches other animations)
        version = self.animation.sim.config.version.value
        self.title = f"Ridehail Simulation - version {version}"
        # Don't call super().on_mount() to avoid starting base class simulation timer

    def on_ready(self) -> None:
        """Initialize when the app is ready"""
        # Delegate to the animation's on_ready method
        self.animation.on_ready()

    def compose(self) -> ComposeResult:
        """Use the animation's compose method for layout"""
        yield from self.animation.compose()

    def action_pause_sequence(self) -> None:
        """Toggle pause/resume for sequence progression"""
        self.sequence_paused = not self.sequence_paused
        if not self.sequence_paused:
            # Resume sequence if it was waiting
            if hasattr(self.animation, "_resume_sequence"):
                self.animation._resume_sequence()

    def action_restart_sequence(self) -> None:
        """Restart the sequence from the beginning"""
        # Reset sequence state
        self.animation.sequence_widget.current_simulation_index = 0
        self.animation.sequence_widget.vehicle_p1_fraction.clear()
        self.animation.sequence_widget.vehicle_p2_fraction.clear()
        self.animation.sequence_widget.vehicle_p3_fraction.clear()
        self.animation.sequence_widget.trip_wait_fraction.clear()
        self.animation.sequence_widget.mean_ride_time.clear()
        self.animation.sequence_widget.mean_vehicle_count.clear()
        self.animation.sequence_widget.forward_dispatch_fraction.clear()

        # Clear chart
        self.animation.sequence_widget.update_chart()

        # Restart sequence
        self.sequence_paused = False
        self.animation._start_sequence()
