"""
Console-based animation for ridehail simulation using Rich library.
"""
import logging
import time
import signal

from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.live import Live
from rich.progress import Progress, BarColumn, MofNCompleteColumn, TextColumn
from rich.table import Table
from rich import box

from ridehail.atom import (
    CityScaleUnit,
    DispatchMethod,
    Equilibration,
    Measure,
)
from .base import RideHailAnimation


class ConsoleAnimation(RideHailAnimation):

    # Configuration attributes to exclude from display
    CONFIG_EXCLUDE_ATTRS = {
        "city", "config", "target_state", "jsonl_file", "csv_file",
        "trips", "vehicles", "interpolate", "changed_plot_flag",
        "block_index", "animate", "animation_style", "annotation",
        "request_capital", "changed_plotstat_flag"
    }

    # Sleep interval for final display
    FINAL_DISPLAY_SLEEP = 0.1

    def __init__(self, sim):
        super().__init__(sim)
        self.quit_requested = False
        # Progress bars stored as instance variables
        self.progress_bars = {}
        self.progress_tasks = {}
        # Terminal compatibility
        self.terminal_compatible = self._check_terminal_compatibility()

    def _check_terminal_compatibility(self):
        """Check if terminal supports Rich features"""
        try:
            from rich.console import Console
            console = Console()
            # Basic checks for terminal capabilities
            if not console.is_terminal:
                logging.warning("Not running in a terminal - Rich features may not work properly")
                return False
            if console.size.width < 80 or console.size.height < 24:
                logging.warning(f"Terminal size ({console.size.width}x{console.size.height}) may be too small for optimal display")
            return True
        except Exception as e:
            logging.error(f"Terminal compatibility check failed: {e}")
            return False

    def _setup_signal_handler(self):
        """Setup signal handler for Ctrl+C"""
        def signal_handler(sig, frame):
            self.quit_requested = True
        signal.signal(signal.SIGINT, signal_handler)

    def _setup_config_table(self):
        """Create and populate the configuration table"""
        config_table = Table(border_style="steel_blue", box=box.SIMPLE)
        config_table.add_column("Setting", style="grey62", no_wrap=True)
        config_table.add_column("Value", style="grey70")

        for attr in dir(self.sim):
            option = getattr(self.sim, attr)
            attr_name = attr.__str__()

            # Skip callables, private attributes, and excluded attributes
            if (callable(option) or
                attr.startswith("__") or
                attr_name.startswith("history_") or
                attr_name in self.CONFIG_EXCLUDE_ATTRS):
                continue

            config_table.add_row(f"{attr_name}", f"{option}")

        return config_table

    def _setup_progress_bars(self):
        """Setup all progress bars and store them in instance variables"""
        # Main progress bar
        self.progress_bars['progress'] = Progress(
            "{task.description}",
            BarColumn(bar_width=None, complete_style="dark_sea_green"),
            MofNCompleteColumn(),
            expand=False,
        )
        self.progress_tasks['progress'] = [
            self.progress_bars['progress'].add_task("[dark_sea_green]Block", total=1.0)
        ]

        # Vehicle progress bar
        self.progress_bars['vehicle'] = Progress(
            "{task.description}",
            BarColumn(bar_width=None, complete_style="dark_cyan"),
            TextColumn("[progress.percentage]{task.percentage:>02.0f}%"),
        )
        self.progress_tasks['vehicle'] = [
            self.progress_bars['vehicle'].add_task(f"[steel_blue]{Measure.VEHICLE_FRACTION_P1.value}", total=1.0),
            self.progress_bars['vehicle'].add_task(f"[orange3]{Measure.VEHICLE_FRACTION_P2.value}", total=1.0),
            self.progress_bars['vehicle'].add_task(f"[dark_sea_green]{Measure.VEHICLE_FRACTION_P3.value}", total=1.0)
        ]

        # Totals bar
        self.progress_bars['totals'] = Progress(
            "{task.description}",
            BarColumn(bar_width=None, complete_style="orange3"),
            TextColumn("[progress.completed]{task.completed:>5.1f}"),
        )
        self.progress_tasks['totals'] = [
            self.progress_bars['totals'].add_task("[orange3]Vehicles", total=self.sim.vehicle_count * 2)
        ]

        # Trip bar (conditional formatting based on city scale)
        if self.sim.use_city_scale:
            self.progress_bars['trip'] = Progress(
                "{task.description}",
                BarColumn(bar_width=None),
                TextColumn("[progress.completed]{task.completed:>03.1f} mins"),
            )
        else:
            self.progress_bars['trip'] = Progress(
                "{task.description}",
                BarColumn(bar_width=None),
                TextColumn("[progress.completed]{task.completed:>03.1f} blocks"),
            )
        self.progress_tasks['trip'] = [
            self.progress_bars['trip'].add_task(f"[orange3]{Measure.TRIP_MEAN_WAIT_TIME.value}", total=self.sim.city.city_size),
            self.progress_bars['trip'].add_task(f"[dark_sea_green]{Measure.TRIP_MEAN_RIDE_TIME.value}", total=self.sim.city.city_size)
        ]

        # Dispatch bar (conditional)
        self.progress_tasks['dispatch'] = []
        if self.sim.dispatch_method in (DispatchMethod.FORWARD_DISPATCH, DispatchMethod.DEFAULT):
            self.progress_bars['dispatch'] = Progress(
                "{task.description}",
                BarColumn(bar_width=None, complete_style="light_coral"),
                TextColumn("[progress.percentage]{task.percentage:>02.0f}%"),
            )
            self.progress_tasks['dispatch'].append(
                self.progress_bars['dispatch'].add_task(
                    f"[light_coral]{Measure.TRIP_FORWARD_DISPATCH_FRACTION.value}",
                    total=1.0
                )
            )

        # Equilibrium bar (conditional formatting)
        self.progress_tasks['eq'] = []
        if self.sim.use_city_scale:
            self.progress_bars['eq'] = Progress(
                "{task.description}",
                BarColumn(bar_width=None),
                TextColumn("[progress.completed]${task.completed:>5.2f}/hr"),
            )
            price_per_hour = self.sim.convert_units(self.sim.price, CityScaleUnit.PER_BLOCK, CityScaleUnit.PER_HOUR)
            self.progress_tasks['eq'].extend([
                self.progress_bars['eq'].add_task(f"[magenta]{Measure.VEHICLE_GROSS_INCOME.value}", total=price_per_hour),
                self.progress_bars['eq'].add_task(f"[orange3]{Measure.VEHICLE_NET_INCOME.value}", total=price_per_hour)
            ])
            if self.sim.equilibrate and self.sim.equilibration == Equilibration.PRICE:
                self.progress_tasks['eq'].append(
                    self.progress_bars['eq'].add_task(
                        f"[dark_sea_green]{Measure.VEHICLE_MEAN_SURPLUS.value}",
                        total=self.sim.convert_units(self.sim.price, CityScaleUnit.PER_BLOCK, CityScaleUnit.PER_HOUR)
                    )
                )
        else:
            self.progress_bars['eq'] = Progress(
                "{task.description}",
                BarColumn(bar_width=None),
                TextColumn("[progress.completed]{task.completed:>5.2f}"),
            )
            self.progress_tasks['eq'].extend([
                self.progress_bars['eq'].add_task(f"[magenta]{Measure.VEHICLE_GROSS_INCOME.value}", total=self.sim.price),
                self.progress_bars['eq'].add_task(f"[dark_sea_green]{Measure.VEHICLE_MEAN_SURPLUS.value}", total=self.sim.price)
            ])

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

    def _fallback_animation(self):
        """Simple fallback animation for terminals that don't support Rich features"""
        print("Running ridehail simulation (text-only mode)...")
        print("Terminal does not support rich features - using simple text output")

        if self.time_blocks > 0:
            for frame in range(self.time_blocks + 1):
                if self.quit_requested:
                    break
                results = self.sim.next_block(
                    jsonl_file_handle=None,
                    csv_file_handle=None,
                    return_values="stats",
                    dispatch=self.dispatch,
                )
                # Simple text progress
                if frame % 10 == 0:  # Print every 10 blocks
                    print(f"Block {results['block']}: {len(self.sim.vehicles)} vehicles, "
                          f"{len([v for v in self.sim.vehicles if v.phase.name == 'P3'])} occupied")
        else:
            frame = 0
            while not self.quit_requested and frame < 1000:  # Safety limit
                results = self.sim.next_block(
                    jsonl_file_handle=None,
                    csv_file_handle=None,
                    return_values="stats",
                    dispatch=self.dispatch,
                )
                if frame % 10 == 0:
                    print(f"Block {results['block']}: {len(self.sim.vehicles)} vehicles, "
                          f"{len([v for v in self.sim.vehicles if v.phase.name == 'P3'])} occupied")
                frame += 1

    def animate(self):
        # Check terminal compatibility first
        if not self.terminal_compatible:
            print("Warning: Terminal may not support rich animations. Using fallback mode.")
            self._fallback_animation()
            return

        try:
            console = Console()
            self._setup_signal_handler()
            config_table = self._setup_config_table()
            self._setup_progress_bars()
            self._setup_layout(config_table)
            console.print(self.layout)

            with Live(self.layout, screen=True):
                if self.time_blocks > 0:
                    for frame in range(self.time_blocks + 1):
                        if self.quit_requested:
                            break
                        self._next_frame()
                else:
                    frame = 0
                    while not self.quit_requested:
                        self._next_frame()
                        frame += 1

                # For console animation, leave the final frame visible unless quit was requested
                if not self.quit_requested:
                    while not self.quit_requested:
                        time.sleep(self.FINAL_DISPLAY_SLEEP)

        except KeyboardInterrupt:
            self.quit_requested = True
        except Exception as e:
            logging.error(f"Rich animation failed: {e}")
            print(f"Animation error: {e}")
            print("Falling back to simple text mode...")
            self._fallback_animation()

    def _next_frame(self):
        """Execute one frame of the animation and update all progress bars"""
        return_values = "stats"
        results = self.sim.next_block(
            jsonl_file_handle=None,
            csv_file_handle=None,
            return_values=return_values,
            dispatch=self.dispatch,
        )

        # Update progress bar
        if self.sim.time_blocks > 0:
            self.progress_bars['progress'].update(
                self.progress_tasks['progress'][0],
                completed=results["block"],
                total=self.sim.time_blocks,
            )
        else:
            self.progress_bars['progress'].update(
                self.progress_tasks['progress'][0],
                completed=(100 * int(results["block"] / 100) + results["block"] % 100),
                total=100 * (1 + int(results["block"] / 100)),
            )

        # Update vehicle progress bars
        self.progress_bars['vehicle'].update(
            self.progress_tasks['vehicle'][0], completed=results[Measure.VEHICLE_FRACTION_P1.name]
        )
        self.progress_bars['vehicle'].update(
            self.progress_tasks['vehicle'][1], completed=results[Measure.VEHICLE_FRACTION_P2.name]
        )
        self.progress_bars['vehicle'].update(
            self.progress_tasks['vehicle'][2], completed=results[Measure.VEHICLE_FRACTION_P3.name]
        )

        # Update trip progress bars
        self.progress_bars['trip'].update(
            self.progress_tasks['trip'][0], completed=results[Measure.TRIP_MEAN_WAIT_TIME.name]
        )
        self.progress_bars['trip'].update(
            self.progress_tasks['trip'][1], completed=results[Measure.TRIP_MEAN_RIDE_TIME.name]
        )

        # Update dispatch progress bar (if applicable)
        if self.sim.dispatch_method == DispatchMethod.FORWARD_DISPATCH and self.progress_tasks['dispatch']:
            self.progress_bars['dispatch'].update(
                self.progress_tasks['dispatch'][0],
                completed=results[Measure.TRIP_FORWARD_DISPATCH_FRACTION.name],
            )

        # Update totals progress bar
        self.progress_bars['totals'].update(
            self.progress_tasks['totals'][0],
            completed=results[Measure.VEHICLE_MEAN_COUNT.name],
            total=(
                int(results[Measure.VEHICLE_MEAN_COUNT.name] / self.sim.vehicle_count)
                + 1
            )
            * self.sim.vehicle_count,
        )

        # Update equilibrium progress bars
        self.progress_bars['eq'].update(
            self.progress_tasks['eq'][0], completed=results[Measure.VEHICLE_GROSS_INCOME.name]
        )
        if self.sim.use_city_scale:
            self.progress_bars['eq'].update(
                self.progress_tasks['eq'][1], completed=results[Measure.VEHICLE_NET_INCOME.name]
            )
            if self.sim.equilibration == Equilibration.PRICE and len(self.progress_tasks['eq']) > 2:
                self.progress_bars['eq'].update(
                    self.progress_tasks['eq'][2], completed=results[Measure.VEHICLE_MEAN_SURPLUS.name]
                )
        else:
            if self.sim.equilibration == Equilibration.PRICE and len(self.progress_tasks['eq']) > 1:
                self.progress_bars['eq'].update(
                    self.progress_tasks['eq'][1], completed=results[Measure.VEHICLE_MEAN_SURPLUS.name]
                )

        return results