"""
Console-based animation for ridehail simulation using Rich library.
"""

from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table

from ridehail.atom import (
    DispatchMethod,
)
from .rich_base import RichBasedAnimation


class ConsoleAnimation(RichBasedAnimation):

    def __init__(self, sim):
        super().__init__(sim)


    def _setup_progress_bars(self):
        """Setup all progress bars and store them in instance variables"""
        # Setup basic progress bars from parent class
        self._setup_basic_progress_bars()
        # Setup extended progress bars specific to ConsoleAnimation
        self._setup_extended_progress_bars()

    def _setup_layout(self, config_table):
        """Setup the Rich layout with config and statistics panels"""
        statistics_table = Table.grid(expand=True)

        # Add progress bar panels
        statistics_table.add_row(
            Panel(
                self.progress_bars['progress'],
                title="[b]Progress",
                border_style="steel_blue",
            )
        )
        statistics_table.add_row(
            Panel(
                self.progress_bars['vehicle'],
                title="[b]Vehicle statistics",
                border_style="steel_blue",
                padding=(1, 1),
            )
        )
        statistics_table.add_row(
            Panel(
                self.progress_bars['trip'],
                title="[b]Trip statistics",
                border_style="steel_blue",
                padding=(1, 1),
                style="magenta",
            )
        )

        # Conditional dispatch panel
        if self.sim.dispatch_method == DispatchMethod.FORWARD_DISPATCH:
            statistics_table.add_row(
                Panel(
                    self.progress_bars['dispatch'],
                    title="[b]Dispatch statistics",
                    border_style="steel_blue",
                    padding=(1, 1),
                    style="magenta",
                )
            )

        statistics_table.add_row(
            Panel(
                self.progress_bars['totals'],
                title="[b]Totals",
                border_style="steel_blue",
                padding=(1, 1),
                style="orange3",
            )
        )
        statistics_table.add_row(
            Panel(
                self.progress_bars['eq'],
                title="[b]Driver income",
                border_style="steel_blue",
                padding=(1, 1),
                style="dark_sea_green",
            )
        )

        # Create main layout
        self.layout = Layout()
        config_panel = Panel(
            config_table, title="Configuration", border_style="steel_blue"
        )
        self.layout.split_row(
            Layout(config_panel, name="config"),
            Layout(name="state"),
        )
        self.layout["state"].split_column(
            Layout(statistics_table, name="stats"),
            Layout(self._console_log_table(), name="log", size=10),
        )

    def _console_log_table(self, results=None) -> Table:
        log_table = Table.grid(expand=True)
        log_table.add_column("Counter", style="steel_blue", no_wrap=True)
        log_table.add_column("Value", style="dark_sea_green")
        if results:
            log_table.add_row("blocks", f"{results['block']}")
        return log_table


    def animate(self):
        def setup_func(config_table):
            self._setup_progress_bars()
            self._setup_layout(config_table)

        def update_func():
            self._next_frame()

        self._execute_animation_loop(setup_func, update_func)

    def _next_frame(self):
        """Execute one frame of the animation and update all progress bars"""
        return_values = "stats"
        results = self.sim.next_block(
            jsonl_file_handle=None,
            csv_file_handle=None,
            return_values=return_values,
            dispatch=self.dispatch,
        )

        # Update basic and extended progress bars
        self._update_basic_progress_bars(results)
        self._update_extended_progress_bars(results)

        return results