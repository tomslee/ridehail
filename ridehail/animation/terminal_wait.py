"""
Textual-based wait-time distribution animation for ridehail simulation using
plotext. Displays a live histogram of wait times among recently completed
trips (the last `results_window` blocks), to show the shape of the
distribution rather than just its rolling mean (see terminal_stats.py).
"""

import logging
import math
import statistics
from typing import Any, List, Tuple

from textual.app import ComposeResult
from textual.containers import Container
from textual.widgets import Header, Footer
from textual_plotext import PlotextPlot

from .terminal_base import TextualBasedAnimation, RidehailTextualApp


MAX_BINS = 12  # Maximum number of histogram bins for readability
BAR_WIDTH = 0.5  # Relative bar width (0-1); leaves a gap so adjacent bars
# don't visually overlap
Y_AXIS_TICK_COUNT = 5  # Approximate number of y-axis ticks to show
Y_AXIS_LABEL_WIDTH = 6  # Fixed width (chars) for y-axis tick labels, so the
# axis column doesn't change width (and the plot area shift sideways) as
# trip counts grow or shrink between updates.


class WaitTimeChartWidget(Container):
    """Container for the plotext-based wait-time histogram"""

    def __init__(self, sim, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim

    def compose(self) -> ComposeResult:
        yield PlotextPlot(id="wait_plot")

    def _compute_histogram(self, data: List[int]) -> Tuple[List[str], List[int]]:
        """
        Compute adaptive-width histogram bins spanning the observed
        min/max wait time, up to MAX_BINS bins. Bin width is an integer
        number of blocks, since wait times are integer block counts.
        """
        lo, hi = min(data), max(data)
        data_range = hi - lo
        if data_range == 0:
            bin_width = 1
            bins = [lo]
        else:
            bin_width = max(1, -(-data_range // MAX_BINS))  # ceil division
            bins = list(range(lo, hi + 1, bin_width))

        counts = [0] * len(bins)
        for value in data:
            index = min((value - lo) // bin_width, len(bins) - 1)
            counts[index] += 1

        labels = [
            str(b) if bin_width == 1 else f"{b}-{min(b + bin_width - 1, hi)}"
            for b in bins
        ]
        return labels, counts

    def _nice_step(self, rough_step: float) -> int:
        """Round a rough tick step up to a 'nice' 1/2/5-times-a-power-of-10 step."""
        if rough_step <= 0:
            return 1
        magnitude = 10 ** math.floor(math.log10(rough_step))
        residual = rough_step / magnitude
        if residual <= 1:
            nice = 1
        elif residual <= 2:
            nice = 2
        elif residual <= 5:
            nice = 5
        else:
            nice = 10
        return max(1, int(nice * magnitude))

    def _format_y_ticks(self, max_count: int) -> Tuple[List[int], List[str]]:
        """
        Build y-axis ticks at 'nice' round numbers, with labels padded to a
        fixed width. A fixed label width keeps the axis column (and hence
        the plot area) from shifting sideways as trip counts vary between
        updates.
        """
        max_count = max(max_count, 1)
        step = self._nice_step(max_count / (Y_AXIS_TICK_COUNT - 1))
        top = step * ((max_count // step) + 1)
        ticks = list(range(0, top + 1, step))
        labels = [str(t).rjust(Y_AXIS_LABEL_WIDTH) for t in ticks]
        return ticks, labels

    def update_chart(self, block: int) -> None:
        """
        Update the histogram with the current wait-time distribution.

        Args:
            block: Current simulation block number
        """
        try:
            data = [
                wait_time for (_, wait_time) in self.sim.trip_wait_time_history
            ]
            if not data:
                return

            labels, counts = self._compute_histogram(data)

            chart_widget = self.query_one("#wait_plot", PlotextPlot)

            try:
                widget_plt: Any = chart_widget.plt

                widget_plt.clear_data()
                widget_plt.clear_figure()

                try:
                    widget_size = chart_widget.size
                    plot_width = max(60, widget_size.width)
                    plot_height = max(15, widget_size.height)
                except Exception:
                    plot_width, plot_height = 80, 20

                widget_plt.plotsize(plot_width, plot_height)

                widget_plt.bar(labels, counts, color="red", width=BAR_WIDTH)

                y_ticks, y_labels = self._format_y_ticks(max(counts))
                widget_plt.yticks(y_ticks, y_labels)

                median_wait = statistics.median(data)
                title = (
                    f"{self.sim.title} - wait time distribution, "
                    f"{len(data)} trips over last {self.sim.results_window} "
                    f"blocks, median {median_wait:.1f} (block {block})"
                )
                widget_plt.title(title)
                widget_plt.xlabel("Wait time (blocks)")
                widget_plt.ylabel("Trip count")

                chart_widget.refresh()

            except Exception as e:
                logging.error(f"Chart rendering error: {e}")
                logging.exception("Chart rendering error:")

        except Exception as e:
            logging.error(f"Chart update error: {e}")
            logging.exception("Full traceback:")


class TextualWaitAnimation(TextualBasedAnimation):
    """
    Textual-based animation showing a real-time histogram of the
    distribution of recent trip wait times.
    """

    def __init__(self, sim):
        super().__init__(sim)

    def create_app(self) -> RidehailTextualApp:
        """Create the Textual application for wait-time animation"""

        class WaitApp(RidehailTextualApp):
            CSS = (
                RidehailTextualApp.CSS
                + """
            /* Wait-time-specific styling */

            #chart_container {
                width: 1fr;
                height: 1fr;
            }

            #wait_plot {
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
                        yield WaitTimeChartWidget(
                            self.animation.sim, id="chart_container"
                        )
                        yield ConfigPanel(self.sim, id="config_panel")
                else:
                    # Single-column layout (current behavior)
                    yield WaitTimeChartWidget(
                        self.animation.sim, id="chart_container"
                    )

                yield Footer()

            def _execute_simulation_step(self) -> None:
                """Execute one simulation step and update chart (Template Method hook)"""
                try:
                    self.sim.next_block(
                        jsonl_file_handle=None,
                        csv_file_handle=None,
                        return_values="stats",
                    )

                    # Update chart with current block data
                    try:
                        chart_container = self.query_one(
                            "#chart_container", WaitTimeChartWidget
                        )
                        chart_container.update_chart(self.sim.block_index)
                    except Exception:
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

        return WaitApp(self.sim, animation=self)
