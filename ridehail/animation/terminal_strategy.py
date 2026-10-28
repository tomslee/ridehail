"""
Textual-based display of the individual strategy (use_strategy): how the
seated car is doing against the fleet, and the offers it sees
(claude/terminal-strategy-spec.md).

Three parts, top to bottom: a relative-performance panel (text), the car's
and the fleet's cumulative net income over the shift (plotext line chart),
and the offers the car has seen, binned by rate and split into accepted and
declined (plotext bar chart), with a rate:N threshold marked. The data comes
from the simulation's StrategyController; the text, points and bins from
ridehail/strategy_display.py, which has no Textual dependency.
"""

import logging
from typing import Any

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Container, Horizontal, Vertical
from textual.widgets import Footer, Header, Static
from textual_plotext import PlotextPlot

from ridehail.strategy_display import (
    PANEL_LINES,
    count_ticks,
    offer_histogram,
    performance_lines,
    rate_threshold,
    series_points,
)

from .palette import P1_RGB, P3_RGB, WAITING_RIDER_RGB
from .terminal_base import ConfigPanel, RidehailTextualApp, TextualBasedAnimation

# The fleet's line: the colour of the net income sparkline in the console
# display ($warning in the textual-dark theme, #ffa62b), so net income reads
# the same in both; the car's line is its with-rider green (P3)
FLEET_RGB = (255, 166, 43)
CHART_MARKER_CHARACTER = "●"  # Solid circle
BAR_WIDTH = 0.6
MAX_BINS = 12
# The cumulative chart keeps at most this many points
MAX_CHART_POINTS = 400
# Width (columns) from which the configuration panel is shown
CONFIG_PANEL_MIN_WIDTH = 100
# The shortest time between blocks (seconds), even with animation_delay 0.
# A block and its drawing take 15 ms or more here; the base app's 1 ms
# timer for a zero delay left too little time to draw the screen and read
# the keyboard, and the display froze (2026-10-15).
MIN_FRAME_INTERVAL = 0.02


def _plot_size(widget, min_width=40, min_height=8):
    try:
        size = widget.size
        return max(min_width, size.width), max(min_height, size.height)
    except Exception:
        return 80, 15


class PerformancePanel(Static):
    """The car against the fleet, over the same blocks (performance_lines)."""

    def update_panel(self, controller) -> None:
        text = Text()
        for i, (line, style) in enumerate(performance_lines(controller)):
            if i:
                text.append("\n")
            if style == "lead":
                text.append(line, style="bold green")
            elif style == "lag":
                text.append(line, style="bold red")
            else:
                text.append(line)
        # A fixed height (PANEL_LINES lines): updating needs no layout pass,
        # which would redraw both charts every block
        self.update(text, layout=False)


class NetIncomeChart(Container):
    """Cumulative net income of the car and of the fleet over the shift."""

    def compose(self) -> ComposeResult:
        yield PlotextPlot(id="net_plot")

    def update_chart(self, controller) -> None:
        plot = self.query_one("#net_plot", PlotextPlot)
        plt: Any = plot.plt
        plt.clear_data()
        plt.clear_figure()
        plt.plotsize(*_plot_size(plot))
        unit = "hour" if controller.per_hour else "block"
        for key, label, color in (
            ("fleet", "fleet", FLEET_RGB),
            ("car", "car", P3_RGB),
        ):
            xs, ys = series_points(
                controller.net_series[key].points(), MAX_CHART_POINTS
            )
            if xs:
                plt.plot(
                    xs, ys, color=color, label=label, marker=CHART_MARKER_CHARACTER
                )
        plt.title(f"Net income per {unit} over the shift so far")
        plt.xlabel("Block of the shift")
        plot.refresh()


class OffersChart(Container):
    """The offers the car has seen, by rate: accepted and declined."""

    def compose(self) -> ComposeResult:
        yield PlotextPlot(id="offers_plot")

    def update_chart(self, controller) -> None:
        plot = self.query_one("#offers_plot", PlotextPlot)
        plt: Any = plot.plt
        plt.clear_data()
        plt.clear_figure()
        plt.plotsize(*_plot_size(plot))
        threshold = rate_threshold(controller)
        histogram = offer_histogram(controller.offer_log, threshold, MAX_BINS)
        unit = "$/hr" if controller.per_hour else "per block"
        edges = histogram["edges"]
        if edges:
            self._draw_bars(plt, histogram)
            if threshold is not None:
                # Bars sit at x = 1, 2, ...; the threshold is a bin edge, so
                # it falls half way between two bars
                for k, edge in enumerate(edges):
                    if abs(edge - threshold) < 1e-9:
                        plt.vline(k + 0.5, color=WAITING_RIDER_RGB)
                        break
        offers = controller.offers
        shown = len(controller.offer_log)
        # An open-ended run's log keeps only the latest offers
        latest = f" (the latest {shown})" if shown < offers else ""
        plt.title(
            f"Offers the car has seen: {offers}{latest}, "
            f"by rate ({unit}, pickup included)"
        )
        plt.xlabel(f"Offered rate ({unit})")
        plot.refresh()

    @staticmethod
    def _draw_bars(plt, histogram) -> None:
        """
        Accepted offers at the bottom of each bin's bar, declined above, at x
        = 1, 2, ... and labelled with the bins' lower edges. Each bar is drawn
        on its own, and only if it has height: plotext draws a zero-height
        bar with blank characters along the axis, which would rub out the
        bottom row of the other series' bar in the same bin (as stacked_bar
        does when a bin is all accepted or all declined).
        """
        accepted, declined = histogram["accepted"], histogram["declined"]
        bins = len(accepted)
        labelled = set()
        for k in range(bins):
            x = k + 1
            total = accepted[k] + declined[k]
            # The whole bar in the declined colour, then the accepted part
            # over its lower end
            for height, color, label in (
                (total if declined[k] else 0, P1_RGB, "declined"),
                (accepted[k], P3_RGB, "accepted"),
            ):
                if height:
                    plt.bar(
                        [x],
                        [height],
                        color=color,
                        width=BAR_WIDTH,
                        label=None if label in labelled else label,
                        reset_ticks=False,
                    )
                    labelled.add(label)
        plt.xticks(
            list(range(1, bins + 1)), [f"{edge:g}" for edge in histogram["edges"][:-1]]
        )
        plt.xlim(0.5, bins + 0.5)
        # The bars are counts: whole-number ticks only
        y_ticks, y_labels = count_ticks(max(a + d for a, d in zip(accepted, declined)))
        plt.yticks(y_ticks, y_labels)
        plt.ylim(0, y_ticks[-1])


class TextualStrategyAnimation(TextualBasedAnimation):
    """
    Textual-based display of the seated car's relative performance and the
    offers it sees (use_strategy).
    """

    def __init__(self, sim):
        super().__init__(sim)

    def create_app(self) -> RidehailTextualApp:
        class StrategyApp(RidehailTextualApp):
            CSS = (
                RidehailTextualApp.CSS
                + """
            #strategy_column {
                width: 1fr;
                height: 1fr;
            }

            #performance_panel {
                height: RH_PANEL_HEIGHT;
                border: solid $primary;
                padding: 0 1;
            }

            #net_chart, #offers_chart {
                width: 1fr;
                height: 1fr;
            }

            #net_plot, #offers_plot {
                width: 1fr;
                height: 1fr;
                border: solid $primary;
            }
            """
            ).replace("RH_PANEL_HEIGHT", str(PANEL_LINES + 2))  # + the border

            def __init__(self, sim, animation=None):
                super().__init__(sim, animation=animation)
                self.animation = animation
                self._offers_drawn = None

            def compose(self) -> ComposeResult:
                yield Header(show_clock=True)
                terminal_width = (
                    self.console.size.width if hasattr(self.console, "size") else 80
                )
                with Horizontal(id="layout_container"):
                    with Vertical(id="strategy_column"):
                        yield PerformancePanel(id="performance_panel")
                        yield NetIncomeChart(id="net_chart")
                        yield OffersChart(id="offers_chart")
                    if terminal_width >= CONFIG_PANEL_MIN_WIDTH:
                        yield ConfigPanel(self.sim, id="config_panel")
                yield Footer()

            def start_simulation(self) -> None:
                """
                As the base app's, but never faster than MIN_FRAME_INTERVAL
                between blocks, so the screen is drawn and keys are read.
                """
                if not self.simulation_timer:
                    interval = max(self.sim.animation_delay, MIN_FRAME_INTERVAL)
                    self.simulation_timer = self.set_interval(
                        interval=interval, callback=self.simulation_step, repeat=0
                    )

            def on_mount(self) -> None:
                super().on_mount()
                self._update_displays()

            def _update_displays(self) -> None:
                # The controller is replaced when the simulation restarts
                controller = self.sim.strategy_controller
                if controller is None:
                    return
                try:
                    self.query_one("#performance_panel", PerformancePanel).update_panel(
                        controller
                    )
                    self.query_one("#net_chart", NetIncomeChart).update_chart(
                        controller
                    )
                    # The histogram changes only with a new offer (or a restart)
                    drawn = (id(controller), controller.offers)
                    if drawn != self._offers_drawn:
                        self.query_one("#offers_chart", OffersChart).update_chart(
                            controller
                        )
                        self._offers_drawn = drawn
                except Exception as e:
                    logging.error(f"Strategy display update failed: {e}")
                    logging.exception("Strategy display update failed:")

            def _execute_simulation_step(self) -> None:
                """One block, then the displays (the Template Method hook)."""
                try:
                    self._next_block(return_values="stats")
                    self._update_displays()
                    if (
                        self.sim.time_blocks > 0
                        and self.sim.block_index >= self.sim.time_blocks
                    ):
                        self.stop_simulation()
                except Exception as e:
                    logging.error(f"Simulation step failed: {e}")
                    self.stop_simulation()

            def action_restart(self) -> None:
                """Restart: the car is seated again and the shift cleared."""
                super().action_restart()
                self._offers_drawn = None
                self._update_displays()

        return StrategyApp(self.sim, animation=self)
