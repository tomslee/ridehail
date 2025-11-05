"""
Textual-based stats animation for ridehail simulation using plotext.
Provides real-time line chart visualization of vehicle phase metrics (P1, P2, P3).
"""

import logging
from typing import Dict, List, Any
from collections import defaultdict

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer
from textual_plotext import PlotextPlot

from ridehail.atom import Measure, DispatchMethod, Equilibration, History
from .terminal_base import TextualBasedAnimation, RidehailTextualApp


# Chart configuration constants
CHART_X_RANGE = 60  # Number of blocks to display in rolling window
DEFAULT_UPDATE_PERIOD = 1  # Update chart every N blocks
MAX_CHART_LINES = 7  # Maximum number of lines to display for readability
CHART_MARKER_CHARACTER = "\u25cf"  # Solid circle
DATA_THRESHOLD_MIN = 0.0001  # Minimum value threshold for plotting data
DATA_THRESHOLD_MAX = 1.0  # Maximum value threshold for plotting data
# CHART_MARKER_CHARACTER = "\u26ac"  # Slightly smaller open circle


class StatsChartWidget(Container):
    """Container for the plotext-based statistics chart"""

    def __init__(self, sim, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim
        self.plot_arrays = defaultdict(lambda: [0.0] * (sim.time_blocks + 1))
        self.smoothing_window = sim.results_window
        self.animate_update_period = DEFAULT_UPDATE_PERIOD

    def compose(self) -> ComposeResult:
        yield PlotextPlot(id="stats_plot")

    def _update_plot_arrays(self, block: int):
        """
        Update plot arrays with current simulation data.
        Ported from matplotlib animation implementation.
        """
        if block == 0:
            return

        # Calculate smoothing window bounds (matching matplotlib implementation)
        lower_bound = max((block - self.smoothing_window), 0)
        window_block_count = block - lower_bound
        window_vehicle_time = self.sim.history_buffer[History.VEHICLE_TIME].sum

        # Vehicle statistics - fractions based on time spent in each phase
        if window_vehicle_time > 0:
            try:
                p1_frac = (
                    self.sim.history_buffer[History.VEHICLE_TIME_P1].sum
                    / window_vehicle_time
                )
                p2_frac = (
                    self.sim.history_buffer[History.VEHICLE_TIME_P2].sum
                    / window_vehicle_time
                )
                p3_frac = (
                    self.sim.history_buffer[History.VEHICLE_TIME_P3].sum
                    / window_vehicle_time
                )

                self.plot_arrays[Measure.VEHICLE_FRACTION_P1][block] = p1_frac
                self.plot_arrays[Measure.VEHICLE_FRACTION_P2][block] = p2_frac
                self.plot_arrays[Measure.VEHICLE_FRACTION_P3][block] = p3_frac

                # Optional equilibration metrics
                if self.sim.equilibration != Equilibration.NONE:
                    self.plot_arrays[Measure.VEHICLE_MEAN_COUNT][block] = (
                        self.sim.history_buffer[History.VEHICLE_TIME].sum
                    ) / window_block_count
                    self.plot_arrays[Measure.TRIP_MEAN_REQUEST_RATE][block] = (
                        self.sim.history_buffer[History.TRIP_REQUEST_RATE].sum
                        / window_block_count
                    )

                    # Vehicle surplus calculation
                    utility_list = [
                        self.sim.vehicle_utility(
                            self.plot_arrays[Measure.VEHICLE_FRACTION_P3][x]
                        )
                        for x in range(lower_bound, block + 1)
                    ]
                    self.plot_arrays[Measure.VEHICLE_MEAN_SURPLUS][block] = sum(
                        utility_list
                    ) / len(utility_list)
            except Exception as e:
                logging.info(
                    f"window_vehicle_time={window_vehicle_time}, "
                    f"block={block}, len={len(self.plot_arrays[Measure.VEHICLE_FRACTION_P1])}, "
                    f"self.sim.history_buffer[History.VEHICLE_TIME].sum={self.sim.history_buffer[History.VEHICLE_TIME].sum}, "
                    f"{e}"
                )

        # Trip statistics
        window_request_count = self.sim.history_buffer[History.TRIP_COUNT].sum
        window_completed_trip_count = self.sim.history_buffer[
            History.TRIP_COMPLETED_COUNT
        ].sum
        window_riding_time = self.sim.history_buffer[History.TRIP_RIDING_TIME].sum

        if window_request_count > 0 and window_completed_trip_count > 0:
            try:
                # print(f"trip stats, block={block}")
                # Mean wait time
                self.plot_arrays[Measure.TRIP_MEAN_WAIT_TIME][block] = (
                    self.sim.history_buffer[History.TRIP_WAIT_TIME].sum
                    / window_completed_trip_count
                )
                # Mean ride time (distance)
                self.plot_arrays[Measure.TRIP_MEAN_RIDE_TIME][block] = (
                    self.sim.history_buffer[History.TRIP_DISTANCE].sum
                    / window_completed_trip_count
                )
                # Distance fraction
                self.plot_arrays[Measure.TRIP_DISTANCE_FRACTION][block] = (
                    self.plot_arrays[Measure.TRIP_MEAN_RIDE_TIME][block]
                    / self.sim.city.city_size
                )
                # Wait time fraction
                self.plot_arrays[Measure.TRIP_MEAN_WAIT_FRACTION][block] = (
                    self.sim.history_buffer[History.TRIP_WAIT_TIME].sum
                    / window_riding_time
                )
                self.plot_arrays[Measure.TRIP_MEAN_WAIT_FRACTION_TOTAL][block] = (
                    self.plot_arrays[Measure.TRIP_MEAN_WAIT_TIME][block]
                    / (
                        self.plot_arrays[Measure.TRIP_MEAN_RIDE_TIME][block]
                        + self.plot_arrays[Measure.TRIP_MEAN_WAIT_TIME][block]
                    )
                )
            except Exception as e:
                logging.info(
                    f"DEBUG: window_riding_time={window_riding_time}, "
                    f"block={block}, len={len(self.plot_arrays[Measure.TRIP_MEAN_WAIT_FRACTION])}, "
                    f"self.sim.history_buffer[History.TRIP_WAIT_TIME].sum={self.sim.history_buffer[History.TRIP_WAIT_TIME].sum}, "
                    f"{e}"
                )

        # Optional forward dispatch metrics
        if (
            self.sim.dispatch_method == DispatchMethod.FORWARD_DISPATCH
            and window_completed_trip_count > 0
        ):
            self.plot_arrays[Measure.TRIP_FORWARD_DISPATCH_FRACTION][block] = (
                self.sim.history_buffer[History.TRIP_FORWARD_DISPATCH_COUNT].sum
                / window_completed_trip_count
            )

    def _get_plotstat_list(self) -> List[Measure]:
        """
        Get list of measures to plot based on simulation configuration.
        Matches matplotlib implementation logic.
        """
        plotstat_list = [
            Measure.VEHICLE_FRACTION_P1,
            Measure.VEHICLE_FRACTION_P2,
            Measure.VEHICLE_FRACTION_P3,
            Measure.TRIP_MEAN_WAIT_FRACTION_TOTAL,
            Measure.TRIP_DISTANCE_FRACTION,
        ]

        # Add conditional metrics
        if self.sim.equilibration == Equilibration.PRICE:
            plotstat_list.append(Measure.VEHICLE_MEAN_SURPLUS)

        if self.sim.dispatch_method == DispatchMethod.FORWARD_DISPATCH:
            plotstat_list.append(Measure.TRIP_FORWARD_DISPATCH_FRACTION)

        return plotstat_list

    def _configure_chart(self, widget_plt: Any, block: int, lines_plotted: int) -> None:
        """
        Configure chart appearance, labels, and legend.

        Args:
            widget_plt: Plotext instance from the widget
            block: Current simulation block number
            lines_plotted: Number of lines that were plotted
        """
        # Configure chart appearance
        title = (
            f"{self.sim.title} - "
            f"{len(self.sim.vehicles)} vehicles, {self.sim.request_rate:.2f} requests/block "
            f"(block {block})"
        )
        widget_plt.title(title)
        widget_plt.xlabel("Block")
        widget_plt.ylabel("Fraction")
        widget_plt.ylim(0, DATA_THRESHOLD_MAX)

        # Show legend if we have plotted lines
        if lines_plotted > 0:
            try:
                widget_plt.legend()
            except AttributeError:
                # Fallback if legend method doesn't exist
                pass

    def _plot_metrics(
        self,
        widget_plt: Any,
        x_range: List[int],
        plotstat_list: List[Measure],
        color_map: Dict[Measure, str],
    ) -> int:
        """
        Plot metric lines and return number of lines plotted.

        Args:
            widget_plt: Plotext instance from the widget
            x_range: Range of x-values (block numbers) to plot
            plotstat_list: List of measures to plot
            color_map: Mapping of measures to colors

        Returns:
            Number of lines successfully plotted
        """
        lines_plotted = 0

        for measure in plotstat_list:
            if measure in color_map and lines_plotted < MAX_CHART_LINES:
                # Extract y_data for the rolling window
                y_data = []
                for x in x_range:
                    if x < len(self.plot_arrays[measure]):
                        y_data.append(self.plot_arrays[measure][x])
                    else:
                        y_data.append(0.0)

                if (
                    len(y_data) == len(x_range)
                    and any(y > DATA_THRESHOLD_MIN for y in y_data)
                    and any(y < DATA_THRESHOLD_MAX for y in y_data)
                ):
                    widget_plt.plot(
                        x_range,
                        y_data,
                        color=color_map[measure],
                        label=measure.value[:20],
                        marker=CHART_MARKER_CHARACTER,
                    )
                    lines_plotted += 1

        return lines_plotted

    def update_chart(self, block: int) -> None:
        """
        Update the chart with current simulation data.

        Args:
            block: Current simulation block number
        """
        try:
            # Update data arrays
            self._update_plot_arrays(block)

            # Only update chart display every update period
            if block % self.animate_update_period != 0:
                return

            # Get chart widget
            chart_widget = self.query_one("#stats_plot", PlotextPlot)

            # Calculate display range for rolling window
            lower_bound = max(block - CHART_X_RANGE, 1)
            if block <= lower_bound:
                return

            x_range = list(range(lower_bound, block))
            plotstat_list = self._get_plotstat_list()

            # Enhanced color scheme matching existing conventions
            color_map = {
                Measure.VEHICLE_FRACTION_P1: "cyan",  # P1 (idle) - cyan
                Measure.VEHICLE_FRACTION_P2: "orange",  # P2 (dispatched) - orange
                Measure.VEHICLE_FRACTION_P3: "green",  # P3 (occupied) - green
                Measure.TRIP_MEAN_WAIT_FRACTION_TOTAL: "red",  # Wait times - red
                Measure.TRIP_DISTANCE_FRACTION: "gray",  # Distance - purple
                Measure.VEHICLE_MEAN_SURPLUS: "blue",  # Surplus - blue
                Measure.TRIP_FORWARD_DISPATCH_FRACTION: "magenta",  # Forward dispatch - yellow
            }

            # Update the widget using the correct textual-plotext pattern
            try:
                # Use the widget's plt instance directly - textual-plotext should auto-refresh
                widget_plt = chart_widget.plt

                # Clear and configure plot
                widget_plt.clear_data()
                widget_plt.clear_figure()

                # Get widget size for responsive plotting
                try:
                    widget_size = chart_widget.size
                    plot_width = max(60, widget_size.width)
                    plot_height = max(15, widget_size.height)
                except Exception:
                    plot_width, plot_height = 80, 20

                widget_plt.plotsize(plot_width, plot_height)

                # Plot metrics and configure chart
                lines_plotted = self._plot_metrics(
                    widget_plt, x_range, plotstat_list, color_map
                )
                self._configure_chart(widget_plt, block, lines_plotted)

                # Trigger refresh to update display
                chart_widget.refresh()

            except Exception as e:
                logging.error(f"Chart rendering error: {e}")
                logging.exception("Chart rendering error:")

        except Exception as e:
            logging.error(f"Chart update error: {e}")
            logging.exception("Full traceback:")


class TextualStatsAnimation(TextualBasedAnimation):
    """
    Textual-based statistics animation showing real-time line charts
    of vehicle phase fractions (P1, P2, P3) and trip metrics.
    """

    def __init__(self, sim):
        super().__init__(sim)

    def create_app(self) -> RidehailTextualApp:
        """Create the Textual application for stats animation"""

        class StatsApp(RidehailTextualApp):
            CSS = (
                RidehailTextualApp.CSS
                + """
            /* Stats-specific styling */

            #chart_container {
                width: 1fr;
                height: 1fr;
            }

            #stats_plot {
                width: 1fr;
                height: 1fr;
                border: solid $primary;
                padding: 1;
            }
            """
            )

            def __init__(self, sim, animation=None):
                super().__init__(sim, animation=animation)
                self.animation = animation

            def compose(self) -> ComposeResult:
                from textual.containers import Horizontal
                from ridehail.animation.terminal_base import ConfigPanel

                yield Header(show_clock=True)

                # Check if terminal is wide enough for config panel
                terminal_width = (
                    self.console.size.width if hasattr(self.console, "size") else 80
                )

                if terminal_width >= 100:
                    # Two-column layout with config panel
                    with Horizontal(id="layout_container"):
                        yield StatsChartWidget(self.animation.sim, id="chart_container")
                        yield ConfigPanel(self.sim, id="config_panel")
                else:
                    # Single-column layout (current behavior)
                    yield StatsChartWidget(self.animation.sim, id="chart_container")

                yield Footer()

            def _execute_simulation_step(self) -> None:
                """Execute one simulation step and update chart (Template Method hook)"""
                # Increment step counter for debugging
                self._step_count = getattr(self, "_step_count", 0) + 1

                try:
                    self.sim.next_block(
                        jsonl_file_handle=None,
                        csv_file_handle=None,
                        return_values="stats",
                    )

                    # Update chart with current block data
                    try:
                        chart_container = self.query_one(
                            "#chart_container", StatsChartWidget
                        )
                        chart_container.update_chart(self.sim.block_index)
                    except Exception as e:
                        pass

                    # Check if simulation is complete
                    if (
                        self.sim.time_blocks > 0
                        and self.sim.block_index >= self.sim.time_blocks
                    ):
                        self.stop_simulation()

                except Exception as e:
                    logging.error(f"Simulation step failed: {e}")
                    self.stop_simulation()

            def key_q(self):
                """Quit the application"""
                self.exit()

            def key_space(self):
                """Toggle simulation pause"""
                self.is_paused = not self.is_paused

            def key_r(self):
                """Reset chart view"""
                chart_container = self.query_one("#chart_container", StatsChartWidget)
                chart_container.chart_data.clear()
                chart_container.update_chart(self.animation.sim.block_index)

        return StatsApp(self.sim, animation=self)
