import logging
import enum
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
import json
import os
import sys
import time
from matplotlib import offsetbox
from datetime import datetime
from matplotlib import ticker
from matplotlib import animation  # , rc
from pandas.plotting import register_matplotlib_converters

# Console output
from rich.console import Console
from rich.layout import Layout, Panel
from rich.live import Live
from rich.progress import Progress, BarColumn, MofNCompleteColumn, TextColumn
from rich.table import Table
from rich import box

from ridehail.simulation import RideHailSimulationResults
from ridehail.atom import (
    Animation,
    CityScaleUnit,
    Direction,
    Equilibration,
    History,
    Measure,
    TripPhase,
    VehiclePhase,
)
from ridehail.config import WritableConfig

register_matplotlib_converters()

# PLOTTING_OFFSET = 128
# Placeholder frame count for animation.
mpl.rcParams["figure.dpi"] = 100
mpl.rcParams["savefig.dpi"] = 100
# mpl.rcParams['text.usetex'] = True
sns.set()
sns.set_style("darkgrid")
sns.set_palette("muted")
sns.set_context("talk")
# sns.set_context("notebook", font_scale=0.8)


class HistogramArray(enum.Enum):
    HIST_TRIP_WAIT_TIME = "Wait time"
    HIST_TRIP_DISTANCE = "Trip distance"


class RideHailAnimation:
    """
    Base class for plotting
    """

    __all__ = ["RideHailAnimation"]
    _ROADWIDTH_BASE = 60.0
    _FRAME_INTERVAL = 50
    _FRAME_COUNT_UPPER_LIMIT = 99999
    _DISPLAY_FRINGE = 0.25

    def __init__(self, sim):
        self.sim = sim
        self.title = sim.config.title.value
        # TODO: this is complex.
        self.animation_style = sim.config.animation_style.value
        self.animate_update_period = sim.config.animate_update_period.value
        self.interpolation_points = sim.config.interpolate.value
        self.annotation = sim.config.annotation.value
        self.smoothing_window = sim.config.smoothing_window.value
        self.animation_output_file = sim.config.animation_output_file.value
        self.time_blocks = sim.config.time_blocks.value
        self.frame_index = 0
        self.display_fringe = self._DISPLAY_FRINGE
        self.color_palette = sns.color_palette()
        # Only reset the interpoation points at an intersection.
        # Need a separate variable to hold it here
        self.current_interpolation_points = self.interpolation_points
        self.pause_plot = False  # toggle for pausing
        self.axes = []
        self.in_jupyter = False
        self.plot_arrays = {}
        for plot_array in list(Measure):
            self.plot_arrays[plot_array] = np.zeros(sim.time_blocks + 1)
        self.histograms = {}
        for histogram in list(HistogramArray):
            self.histograms[histogram] = np.zeros(sim.city.city_size + 1)
        self.plotstat_list = []
        self.changed_plotstat_flag = False
        self.state_dict = {}

    def _on_key_press(self, event):
        """
        Respond to shortcut keys
        """
        logging.info(f"key pressed: {event.key}")
        sys.stdout.flush()
        if event.key == "N":
            self.sim.target_state["vehicle_count"] += 1
        elif event.key == "n":
            self.sim.target_state["vehicle_count"] = max(
                (self.sim.target_state["vehicle_count"] - 1), 0
            )
        if event.key == "ctrl+N":
            self.sim.target_state["vehicle_count"] += 10
        elif event.key == "ctrl+n":
            self.sim.target_state["vehicle_count"] = max(
                (self.sim.target_state["vehicle_count"] - 10), 0
            )
        elif event.key == "K":
            self.sim.target_state["base_demand"] = (
                self.sim.target_state["base_demand"] + 0.1
            )
        elif event.key == "k":
            self.sim.target_state["base_demand"] = max(
                (self.sim.target_state["base_demand"] - 0.1), 0
            )
        elif event.key == "ctrl+K":
            self.sim.target_state["base_demand"] = (
                self.sim.target_state["base_demand"] + 1.0
            )
        elif event.key == "ctrl+k":
            self.sim.target_state["base_demand"] = max(
                (self.sim.target_state["base_demand"] - 1.0), 0
            )
        elif event.key == "L":
            self.sim.target_state["max_trip_distance"] = min(
                (self.sim.target_state["max_trip_distance"] + 1),
                self.sim.target_state["city_size"],
            )
        elif event.key == "l":
            self.sim.target_state["max_trip_distance"] = max(
                (self.sim.target_state["max_trip_distance"] - 1), 1
            )
        elif event.key == ("M"):
            self.sim.target_state["platform_commission"] = (
                self.sim.target_state["platform_commission"] + 0.01
            )
        elif event.key == ("m"):
            self.sim.target_state["platform_commission"] = (
                self.sim.target_state["platform_commission"] - 0.01
            )
        elif event.key == ("ctrl+M"):
            self.sim.target_state["platform_commission"] = (
                self.sim.target_state["platform_commission"] + 0.1
            )
        elif event.key == ("ctrl+m"):
            self.sim.target_state["platform_commission"] = (
                self.sim.target_state["platform_commission"] - 0.1
            )
        elif event.key == "P":
            self.sim.target_state["price"] = self.sim.target_state["price"] + 0.1
        elif event.key == "p":
            self.sim.target_state["price"] = max(
                self.sim.target_state["price"] - 0.1, 0.1
            )
        # elif event.key in ("m", "M"):
        # self.fig_manager.full_screen_toggle()
        # elif event.key in ("q", "Q"):
        # try:
        # self._animation.event_source.stop()
        # except AttributeError:
        # print("  User pressed 'q': quitting")
        # return
        # elif event.key == "r":
        # self.sim.target_state["demand_elasticity"] = max(
        # self.sim.target_state["demand_elasticity"] - 0.1, 0.0)
        # elif event.key == "R":
        # self.sim.target_state["demand_elasticity"] = min(
        # self.sim.target_state["demand_elasticity"] + 0.1, 1.0)
        elif event.key == "U":
            self.sim.target_state["reservation_wage"] = min(
                self.sim.target_state["reservation_wage"] + 0.01, 1.0
            )
        elif event.key == "u":
            self.sim.target_state["reservation_wage"] = max(
                self.sim.target_state["reservation_wage"] - 0.01, 0.1
            )
        elif event.key == "ctrl+u":
            self.sim.target_state["reservation_wage"] = max(
                self.sim.target_state["reservation_wage"] - 0.1, 0.1
            )
        elif event.key == "ctrl+U":
            self.sim.target_state["reservation_wage"] = min(
                self.sim.target_state["reservation_wage"] + 0.1, 1.0
            )
        elif event.key == "v":
            # Only apply if the map is being displayed
            if self.animation_style in (Animation.ALL, Animation.MAP):
                self.interpolation_points = max(
                    self.current_interpolation_points + 1, 0
                )
        elif event.key == "V":
            if self.animation_style in (Animation.ALL, Animation.MAP):
                self.interpolation_points = max(
                    self.current_interpolation_points - 1, 0
                )
        elif event.key == "c":
            self.sim.target_state["city_size"] = max(
                self.sim.target_state["city_size"] - 1, 2
            )
        elif event.key == "C":
            self.sim.target_state["city_size"] = max(
                self.sim.target_state["city_size"] + 1, 2
            )
        elif event.key == "i":
            self.sim.target_state["inhomogeneity"] -= min(
                self.sim.target_state["inhomogeneity"], 0.1
            )
            self.sim.target_state["inhomogeneity"] = round(
                self.sim.target_state["inhomogeneity"], 2
            )
        elif event.key == "I":
            self.sim.target_state["inhomogeneity"] += min(
                1.0 - self.sim.target_state["inhomogeneity"], 0.1
            )
            self.sim.target_state["inhomogeneity"] = round(
                self.sim.target_state["inhomogeneity"], 2
            )
        elif event.key in ("ctrl+E", "ctrl+e"):
            self.sim.target_state["equilibrate"] = not self.sim.target_state[
                "equilibrate"
            ]
            # if self.sim.target_state[
            # "equilibration"] == Equilibration.NONE:
            # self.sim.target_state[
            # "equilibration"] = Equilibration.PRICE
            # elif (self.sim.target_state["equilibration"] ==
            # Equilibration.PRICE):
            # self.sim.target_state[
            # "equilibration"] = Equilibration.NONE
            self.changed_plotstat_flag = True
        elif event.key == "ctrl+a":
            if self.animation_style == Animation.MAP:
                self.animation_style = Animation.STATS
            elif self.animation_style == Animation.ALL:
                self.animation_style = Animation.STATS
            elif self.animation_style == Animation.STATS:
                self.animation_style = Animation.BAR
            elif self.animation_style == Animation.BAR:
                self.animation_style = Animation.STATS
            else:
                logging.info(f"Animation unchanged at {self.animation_style}")
        elif event.key in ("escape", " "):
            self.pause_plot ^= True

    def _on_click(self, event):
        self.pause_plot ^= True


class ConsoleAnimation(RideHailAnimation):
    def __init__(self, sim):
        super().__init__(sim)

    def animate(self):
        # self._setup_keyboard_shortcuts()
        console = Console()
        config_table = Table(border_style="steel_blue", box=box.SIMPLE)
        # config_table = Table()
        config_table.add_column("Setting", style="grey62", no_wrap=True)
        config_table.add_column("Value", style="grey70")
        for attr in dir(self.sim):
            option = getattr(self.sim, attr)
            attr_name = attr.__str__()
            if callable(option) or attr.startswith("__"):
                continue
            if attr_name.startswith("history_"):
                continue
            if attr_name in (
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
            ):
                continue
            config_table.add_row(f"{attr_name}", f"{option}")

        progress_bar = Progress(
            "{task.description}",
            BarColumn(bar_width=None, complete_style="dark_sea_green"),
            MofNCompleteColumn(),
            expand=False,
        )
        progress_tasks = []
        progress_tasks.append(progress_bar.add_task("[dark_sea_green]Block", total=1.0))
        vehicle_bar = Progress(
            "{task.description}",
            BarColumn(bar_width=None),
            TextColumn("[progress.percentage]{task.percentage:>02.0f}%",),
        )
        vehicle_tasks = []
        vehicle_tasks.append(
            vehicle_bar.add_task(
                f"[steel_blue]{Measure.VEHICLE_FRACTION_P1.value}", total=1.0
            )
        )
        vehicle_tasks.append(
            vehicle_bar.add_task(
                f"[orange3]{Measure.VEHICLE_FRACTION_P2.value}", total=1.0
            )
        )
        vehicle_tasks.append(
            vehicle_bar.add_task(
                f"[dark_sea_green]{Measure.VEHICLE_FRACTION_P3.value}", total=1.0
            )
        )
        totals_bar = Progress(
            "{task.description}",
            BarColumn(bar_width=None, complete_style="orange3"),
            TextColumn("[progress.completed]{task.completed:>5.1f}",),
        )
        totals_tasks = []
        totals_tasks.append(
            totals_bar.add_task("[orange3]Vehicles", total=self.sim.vehicle_count * 2)
        )
        if self.sim.use_city_scale:
            trip_bar = Progress(
                "{task.description}",
                BarColumn(bar_width=None,),
                TextColumn("[progress.completed]{task.completed:>03.1f} mins"),
            )
        else:
            trip_bar = Progress(
                "{task.description}",
                BarColumn(bar_width=None),
                TextColumn("[progress.completed]{task.completed:>03.1f} blocks"),
            )
        trip_tasks = []
        trip_tasks.append(
            trip_bar.add_task(
                f"[orange3]{Measure.TRIP_MEAN_WAIT_TIME.value}",
                total=self.sim.city.city_size,
            )
        )
        trip_tasks.append(
            trip_bar.add_task(
                f"[dark_sea_green]{Measure.TRIP_MEAN_RIDE_TIME.value}",
                total=self.sim.city.city_size,
            )
        )
        eq_tasks = []
        if self.sim.use_city_scale:
            eq_bar = Progress(
                "{task.description}",
                BarColumn(bar_width=None),
                TextColumn("[progress.completed]${task.completed:>5.2f}/hr"),
            )
            eq_tasks.append(
                eq_bar.add_task(
                    f"[magenta]{Measure.VEHICLE_GROSS_INCOME.value}",
                    total=self.sim.convert_units(
                        self.sim.price, CityScaleUnit.PER_BLOCK, CityScaleUnit.PER_HOUR
                    ),
                )
            )
            eq_tasks.append(
                eq_bar.add_task(
                    f"[orange3]{Measure.VEHICLE_NET_INCOME.value}",
                    total=self.sim.convert_units(
                        self.sim.price, CityScaleUnit.PER_BLOCK, CityScaleUnit.PER_HOUR
                    ),
                )
            )
            eq_tasks.append(
                eq_bar.add_task(
                    f"[dark_sea_green]{Measure.VEHICLE_MEAN_SURPLUS.value}",
                    total=self.sim.convert_units(
                        self.sim.price, CityScaleUnit.PER_BLOCK, CityScaleUnit.PER_HOUR
                    ),
                )
            )
        else:
            eq_bar = Progress(
                "{task.description}",
                BarColumn(bar_width=None),
                TextColumn("[progress.completed]{task.completed:>5.2f}"),
            )
            eq_tasks.append(
                eq_bar.add_task(
                    f"[magenta]{Measure.VEHICLE_GROSS_INCOME.value}",
                    total=self.sim.price,
                )
            )
            eq_tasks.append(
                eq_bar.add_task(
                    f"[dark_sea_green]{Measure.VEHICLE_MEAN_SURPLUS.value}",
                    total=self.sim.price,
                )
            )
        statistics_table = Table.grid(expand=True)
        statistics_table.add_row(
            Panel(progress_bar, title="[b]Progress", border_style="steel_blue",)
        )
        statistics_table.add_row(
            Panel(
                vehicle_bar,
                title="[b]Vehicle statistics",
                border_style="steel_blue",
                padding=(1, 1),
            )
        )
        statistics_table.add_row(
            Panel(
                trip_bar,
                title="[b]Trip statistics",
                border_style="steel_blue",
                padding=(1, 1),
                style="magenta",
            )
        )
        statistics_table.add_row(
            Panel(
                totals_bar,
                title="[b]Totals",
                border_style="steel_blue",
                padding=(1, 1),
                style="orange3",
            )
        )
        statistics_table.add_row(
            Panel(
                eq_bar,
                title="[b]Driver income",
                border_style="steel_blue",
                padding=(1, 1),
                style="dark_sea_green",
            )
        )
        self.layout = Layout()
        config_panel = Panel(
            config_table, title="Configuration", border_style="steel_blue"
        )
        self.layout.split_row(
            Layout(config_panel, name="config"), Layout(name="state"),
        )
        self.layout["state"].split_column(
            Layout(statistics_table, name="stats"),
            Layout(self._console_log_table(), name="log", size=10),
        )
        console.print(self.layout)
        with Live(self.layout, screen=True):
            if self.time_blocks > 0:
                for frame in range(self.time_blocks + 1):
                    self._next_frame(
                        progress_bar,
                        progress_tasks,
                        vehicle_bar,
                        vehicle_tasks,
                        totals_bar,
                        totals_tasks,
                        trip_bar,
                        trip_tasks,
                        eq_bar,
                        eq_tasks,
                    )
            else:
                frame = 0
                while True:
                    self._next_frame(
                        progress_bar,
                        progress_tasks,
                        vehicle_bar,
                        vehicle_tasks,
                        totals_bar,
                        totals_tasks,
                        trip_bar,
                        trip_tasks,
                        eq_bar,
                        eq_tasks,
                    )
                frame += 1

                # live.update(self._console_log_table(results))
            # For console animation, leave the final frame visible
            while True:
                time.sleep(1)

    # def _setup_keyboard_shortcuts(self):
    # listener = keyboard.Listener(on_press=self._on_key_press)
    # listener.start()

    def _console_log_table(self, results=None) -> Table:
        log_table = Table.grid(expand=True,)
        log_table.add_column("Counter", style="steel_blue", no_wrap=True)
        log_table.add_column("Value", style="dark_sea_green")
        if results:
            log_table.add_row("blocks", f"{results['block']}")
        return log_table

    def _next_frame(
        self,
        progress_bar,
        progress_tasks,
        vehicle_bar,
        vehicle_tasks,
        totals_bar,
        totals_tasks,
        trip_bar,
        trip_tasks,
        eq_bar,
        eq_tasks,
    ):
        return_values = "stats"
        results = self.sim.next_block(
            jsonl_file_handle=None, csv_file_handle=None, return_values=return_values
        )
        # self.layout.update(f"P1={results[Measure.VEHICLE_FRACTION_P1.name]}")
        if self.sim.time_blocks > 0:
            progress_bar.update(
                progress_tasks[0],
                completed=results["block"],
                total=self.sim.time_blocks,
            )
        else:
            progress_bar.update(
                progress_tasks[0],
                completed=(100 * int(results["block"] / 100) + results["block"] % 100),
                total=100 * (1 + int(results["block"] / 100)),
            )

        vehicle_bar.update(
            vehicle_tasks[0], completed=results[Measure.VEHICLE_FRACTION_P1.name]
        )
        vehicle_bar.update(
            vehicle_tasks[1], completed=results[Measure.VEHICLE_FRACTION_P2.name]
        )
        vehicle_bar.update(
            vehicle_tasks[2], completed=results[Measure.VEHICLE_FRACTION_P3.name]
        )
        trip_bar.update(
            trip_tasks[0], completed=results[Measure.TRIP_MEAN_WAIT_TIME.name]
        )
        trip_bar.update(
            trip_tasks[1], completed=results[Measure.TRIP_MEAN_RIDE_TIME.name]
        )
        totals_bar.update(
            totals_tasks[0],
            completed=results[Measure.VEHICLE_MEAN_COUNT.name],
            total=(
                int(results[Measure.VEHICLE_MEAN_COUNT.name] / self.sim.vehicle_count)
                + 1
            )
            * self.sim.vehicle_count,
        )
        eq_bar.update(eq_tasks[0], completed=results[Measure.VEHICLE_GROSS_INCOME.name])
        if self.sim.use_city_scale:
            eq_bar.update(
                eq_tasks[1], completed=results[Measure.VEHICLE_NET_INCOME.name]
            )
            eq_bar.update(
                eq_tasks[2], completed=results[Measure.VEHICLE_MEAN_SURPLUS.name]
            )
        else:
            eq_bar.update(
                eq_tasks[1], completed=results[Measure.VEHICLE_MEAN_SURPLUS.name]
            )
        # self._console_log_table(results)
        return results


class MPLAnimation(RideHailAnimation):
    """
    The plotting parts for MatPlotLib output.
    """

    def __init__(self, sim):
        super().__init__(sim)
        self._set_plotstat_list()
        # TODO: IMAGEMAGICK_EXE is hardcoded here. Put it in a config file.
        # It is in a config file but I don't think I do anything with it yet.
        # IMAGEMAGICK_DIR = "/Program Files/ImageMagick-7.0.9-Q16"
        # IMAGEMAGICK_DIR = "/Program Files/ImageMagick-7.0.10-Q16-HDRI"
        # For ImageMagick configuration, see
        # https://stackoverflow.com/questions/23417487/saving-a-matplotlib-animation-with-imagemagick-and-without-ffmpeg-or-mencoder/42565258#42565258
        # -------------------------------------------------------------------------------
        # Set up graphicself.color_palette['figure.figsize'] = [7.0, 4.0]
        if self.sim.config.imagemagick_dir.value:
            mpl.rcParams["animation.convert_path"] = (
                self.sim.config.imagemagick_dir.value + "/magick"
            )
            mpl.rcParams["animation.ffmpeg_path"] = (
                self.sim.config.imagemagick_dir.value + "/ffmpeg"
            )
        else:
            mpl.rcParams["animation.convert_path"] = "magick"
            mpl.rcParams["animation.ffmpeg_path"] = "ffmpeg"
        mpl.rcParams["animation.embed_limit"] = 2 ** 128
        # mpl.rcParams['font.size'] = 12
        # mpl.rcParams['legend.fontsize'] = 'large'
        # mpl.rcParams['figure.titlesize'] = 'medium'

    def animate(self):
        """
        Do the simulation but with displays
        """
        self.sim.results = RideHailSimulationResults(self.sim)
        jsonl_file_handle = open(f"{self.sim.jsonl_file}", "a")
        csv_file_handle = open(f"{self.sim.csv_file}", "a")
        # output_dict copied from RideHailSimulation.simulate(). Not good
        # practice
        output_dict = {}
        output_dict["config"] = WritableConfig(self.sim.config).__dict__
        jsonl_file_handle.write(json.dumps(output_dict) + "\n")
        # No csv output here
        # self.sim.write_config(jsonl_file_handle)
        ncols = 1
        plot_size_x = 8
        plot_size_y = 8
        if self.animation_style in (Animation.MAP,) and self.annotation:
            # Allow space for annotation at right
            plot_size_x += 4
            plot_size_y = 8
        if self.animation_style in (Animation.ALL,):
            ncols += 1
        if self.animation_style in (Animation.BAR, Animation.STATS, Animation.SEQUENCE):
            plot_size_x = 16
            plot_size_y = 8
        fig, self.axes = plt.subplots(
            ncols=ncols, figsize=(ncols * plot_size_x, plot_size_y)
        )
        # plt.tight_layout(rect=[0, 0, 0.75, 1])
        plt.subplots_adjust(right=0.8)
        fig.canvas.mpl_connect("button_press_event", self._on_click)
        fig.canvas.mpl_connect("key_press_event", self._on_key_press)
        # print keys
        if not self.animation_output_file:
            self._print_keyboard_controls()
        self.axes = [self.axes] if ncols == 1 else self.axes
        # Position the display window on the screen
        self.fig_manager = plt.get_current_fig_manager()
        if hasattr(self.fig_manager, "window"):
            if hasattr(self.fig_manager.window, "wm_geometry"):
                # self.fig_manager.window.wm_geometry("+10+10").set_window_title(
                self.fig_manager.window.wm_geometry("").set_window_title(
                    f"Ridehail Animation - " f"{self.sim.config.config_file_root}"
                )
                # self.fig_manager.full_screen_toggle()
                self._animation = animation.FuncAnimation(
                    fig,
                    self._next_frame,
                    frames=(self._FRAME_COUNT_UPPER_LIMIT),
                    fargs=[jsonl_file_handle, csv_file_handle],
                    interval=self._FRAME_INTERVAL,
                    repeat=False,
                    repeat_delay=3000,
                )
            else:
                if self.animation_style in (Animation.ALL, Animation.MAP):
                    frame_count = (self.sim.time_blocks + 1) * (
                        self.interpolation_points + 1
                    )
                else:
                    if self.sim.time_blocks > 0:
                        frame_count = self.sim.time_blocks + 1
                    else:
                        frame_count = None
                self._animation = animation.FuncAnimation(
                    fig,
                    self._next_frame,
                    frames=frame_count,
                    fargs=[jsonl_file_handle, csv_file_handle],
                    interval=self._FRAME_INTERVAL,
                    repeat=False,
                    repeat_delay=3000,
                )
        self._run_animation(self._animation, plt)
        if hasattr(self.sim.config, "config_file_root"):
            if not os.path.exists("./img"):
                os.makedirs("./img")
            fig.savefig(
                f"./img/{self.sim.config.config_file_root}"
                f"-{self.sim.config.start_time}.png"
            )
        self.sim.results.compute_end_state()
        output_dict["end_state"] = self.sim.results.end_state
        jsonl_file_handle.write(json.dumps(output_dict) + "\n")
        jsonl_file_handle.close()
        # No csv writing here: it's all in sim.next_block or sim.simulate

    def _print_keyboard_controls(self):
        """
        For user convenience, print the keyboard controls
        """
        s = (
            "\n"
            "Animation keyboard controls:\n"
            "\tN|n: increase/decrease vehicle count by 1\n"
            "\tCtrl+N|Ctrl+n: increase/decrease vehicle count by 10\n"
            "\tK|k: increase/decrease base demand by 0.1\n"
            "\tCtrl+K|Ctrl+k: increase/decrease base demand by 1.0\n"
            "\tC|c: increase/decrease city size by one block\n"
            "\tI|i: increase/decrease inhomogeneity by 0.1\n"
            "\tL|i: increase/decrease max trip distance by 1\n"
            "\tV|v: increase/decrease apparent speed (map only)\n"
            "\t  f: toggle full screen\n"
            "\n"
            "\tCtrl+e: toggle equilibration\n"
            "\tP|p: if equilibrating, increase/decrease price by 0.1\n"
            "\tM|m: if equilibrating, increase/decrease\n"
            "platform commission by 0.01\n"
            "\tCtrl+M|Ctrl+m: if equilibrating, increase/decrease\n"
            "platform commission by 0.1\n"
            "\tU|u: if equilibrating, increase/decrease\n"
            "reservation wage by 0.01\n"
            "\tCtrl+U|Ctrl+u: if equilibrating, increase/decrease\n"
            "reservation wage by 0.1\n"
            "\n"
            "\tSpace: toggle simulation (pause / run)\n"
            "\t    q: quit\n"
        )
        print(s)

    def _set_plotstat_list(self):
        """
        Set the list of lines to plot
        """
        self.plotstat_list = []
        if self.animation_style in (Animation.ALL, Animation.STATS):
            self.plotstat_list.append(Measure.VEHICLE_FRACTION_P1)
            self.plotstat_list.append(Measure.VEHICLE_FRACTION_P2)
            self.plotstat_list.append(Measure.VEHICLE_FRACTION_P3)
            self.plotstat_list.append(Measure.TRIP_MEAN_WAIT_FRACTION)
            self.plotstat_list.append(Measure.TRIP_DISTANCE_FRACTION)
            if self.sim.equilibrate and self.sim.equilibration != Equilibration.NONE:
                # self.plotstat_list.append(Measure.VEHICLE_MEAN_COUNT)
                self.plotstat_list.append(Measure.VEHICLE_MEAN_SURPLUS)
                # self.plotstat_list.append(Measure.PLATFORM_INCOME)

    def _next_frame(self, ii, *fargs):
        """
        Function called from animator to generate frame ii of the animation.

        Ignore ii and handle the frame counter myself through self.frame_index
        to handle pauses.
        """
        # Set local variables for frame index and block values
        jsonl_file_handle = fargs[0]
        csv_file_handle = fargs[1]
        i = self.frame_index
        block = self.sim.block_index
        if block > self.sim.time_blocks > 0:
            # The simulation is complete
            logging.info(f"Period {self.sim.block_index}: animation completed")
            # TODO This does not quit the simulation
            self.frame_index = self._FRAME_COUNT_UPPER_LIMIT + 1
            if hasattr(self._animation.event_source, "stop"):
                self._animation.event_source.stop()
                logging.info("animation.event_source stop")
            else:
                plt.close()
            return
        if not self.pause_plot:
            # OK, we are plotting. Increment
            self.frame_index += 1
        if self._interpolation(i) == 0 and not self.pause_plot:
            # A "real" time point. Carry out a step of simulation
            # If the plotting is paused, don't compute the next block,
            # just redisplay what we have.
            # next_block updates the block_index
            # Only change the current interpolation points by at most one
            self.state_dict = self.sim.next_block(jsonl_file_handle, csv_file_handle)
            if self.changed_plotstat_flag or self.sim.changed_plotstat_flag:
                self._set_plotstat_list()
                self.changed_plotstat_flag = False
            logging.debug(f"Animation in progress: frame {i}")
            self.current_interpolation_points = self.interpolation_points
        # Now call the plotting functions
        if (
            self.animation_style == Animation.BAR
            and self.frame_index < self.sim.city.city_size
        ):
            return
        axis_index = 0
        if self.animation_style in (Animation.ALL, Animation.MAP):
            self._plot_map(i, self.axes[axis_index])
            axis_index += 1
        if self.animation_style == Animation.ALL:
            if block % self.animate_update_period == 0:
                self._plot_stats(i, self.axes[axis_index], fractional=True)
            axis_index += 1
        elif self.animation_style == Animation.STATS:
            if block % self.animate_update_period == 0 and self._interpolation(i) == 0:
                self._plot_stats(i, self.axes[axis_index], fractional=True)
            axis_index += 1
        if self.animation_style in [Animation.BAR]:
            histogram_list = [
                HistogramArray.HIST_TRIP_DISTANCE,
                HistogramArray.HIST_TRIP_WAIT_TIME,
            ]
            self._update_plot_arrays(block)
            self._update_histogram_arrays(block, histogram_list)
            self._plot_histograms(block, histogram_list, self.axes[axis_index])
            axis_index += 1

    def _update_histogram_arrays(self, block, histogram_list):
        """
        On each move, fill in the histograms with data from
        the completed trips.
        """
        for trip in self.sim.trips:
            if trip.phase == TripPhase.COMPLETED:
                for histogram in histogram_list:
                    try:
                        if histogram == HistogramArray.HIST_TRIP_WAIT_TIME:
                            if (
                                trip.phase_time[TripPhase.WAITING]
                                < self.sim.city.city_size
                            ):
                                # The arrays don't hold very long wait times,
                                # which may happen when there are few vehicles
                                self.histograms[histogram][
                                    trip.phase_time[TripPhase.WAITING]
                                ] += 1
                        elif histogram == HistogramArray.HIST_TRIP_DISTANCE:
                            self.histograms[histogram][trip.distance] += 1
                    except IndexError as e:
                        logging.error(
                            f"{e}\n"
                            f"histogram={histogram}\n"
                            f"histogram_list={histogram_list}\n"
                            f"trip.phase_time={trip.phase_time}\n"
                            f"trip.distance={trip.distance}\n"
                        )

    def _update_plot_arrays(self, block):
        """
        OBSOLETE: Kept for reference
        Measure arrays are values computed from the History arrays
        but smoothed over self.smoothing_window.

        The list of Measure members to be calculated is set, depending
        on chart type and options, in self._set_plotstat_list and is held
        in self.plotstat_list.

        The arrays themselves are all numpy arrays, one in each
        of self.plot_arrays. self.sim.history holds the simulation
        History lists.
        """
        lower_bound = max((block - self.smoothing_window), 0)
        window_block_count = block - lower_bound
        window_vehicle_time = sum(
            self.sim.history[History.VEHICLE_TIME][lower_bound:block]
        )
        # vehicle stats
        if window_vehicle_time > 0:
            self.plot_arrays[Measure.VEHICLE_FRACTION_P1][block] = (
                sum(self.sim.history[History.VEHICLE_TIME_P1][lower_bound:block])
                / window_vehicle_time
            )
            self.plot_arrays[Measure.VEHICLE_FRACTION_P2][block] = (
                sum(self.sim.history[History.VEHICLE_TIME_P2][lower_bound:block])
                / window_vehicle_time
            )
            self.plot_arrays[Measure.VEHICLE_FRACTION_P3][block] = (
                sum(self.sim.history[History.VEHICLE_TIME_P3][lower_bound:block])
                / window_vehicle_time
            )
            # Additional items when equilibrating
            if self.sim.equilibration != Equilibration.NONE:
                self.plot_arrays[Measure.VEHICLE_MEAN_COUNT][block] = (
                    sum(self.sim.history[History.VEHICLE_MEAN_COUNT][lower_bound:block])
                    / window_block_count
                )
                self.plot_arrays[Measure.TRIP_MEAN_REQUEST_RATE][block] = (
                    sum(
                        self.sim.history[History.TRIP_MEAN_REQUEST_RATE][
                            lower_bound:block
                        ]
                    )
                    / window_block_count
                )
                self.plot_arrays[Measure.PLATFORM_MEAN_INCOME][block] = (
                    self.sim.price
                    * self.sim.platform_commission
                    * sum(
                        self.sim.history[History.TRIP_COMPLETED_COUNT][
                            lower_bound:block
                        ]
                    )
                    / window_block_count
                )
                # take average of average utility. Not sure this is the best
                # way, but it may do for now
                utility_list = [
                    self.sim.vehicle_utility(
                        self.plot_arrays[Measure.VEHICLE_FRACTION_P3][x]
                    )
                    for x in range(lower_bound, block + 1)
                ]
                self.plot_arrays[Measure.VEHICLE_MEAN_SURPLUS][block] = sum(
                    utility_list
                ) / len(utility_list)

        # trip stats
        window_request_count = sum(
            self.sim.history[History.TRIP_COUNT][lower_bound:block]
        )
        window_completed_trip_count = sum(
            self.sim.history[History.TRIP_COMPLETED_COUNT][lower_bound:block]
        )
        window_riding_time = sum(
            self.sim.history[History.TRIP_RIDING_TIME][lower_bound:block]
        )
        if window_request_count > 0 and window_completed_trip_count > 0:
            self.plot_arrays[Measure.TRIP_MEAN_WAIT_TIME][block] = (
                sum(self.sim.history[History.WAIT_TIME][lower_bound:block])
                / window_completed_trip_count
            )
            self.plot_arrays[Measure.TRIP_MEAN_RIDE_TIME][block] = (
                sum(self.sim.history[History.TRIP_DISTANCE][lower_bound:block])
                / window_completed_trip_count
            )
            self.plot_arrays[Measure.TRIP_DISTANCE_FRACTION][block] = (
                self.plot_arrays[Measure.TRIP_DISTANCE][block] / self.sim.city.city_size
            )
            self.plot_arrays[Measure.TRIP_MEAN_WAIT_FRACTION][block] = (
                sum(self.sim.history[History.WAIT_TIME][lower_bound:block])
                / window_riding_time
            )
            self.plot_arrays[Measure.TRIP_SUM_COUNT][block] = (
                window_request_count / window_block_count
            )
            self.plot_arrays[Measure.TRIP_COMPLETED_FRACTION][block] = (
                window_completed_trip_count / window_request_count
            )
        logging.debug(
            (
                f"block={block}"
                f", animation: window_req_c={window_request_count}"
                f", w_completed_trips={window_completed_trip_count}"
                f", trip_distance="
                f"{self.plot_arrays[Measure.TRIP_MEAN_RIDE_TIME][block]:.02f}"
                f", trip_distance_fraction="
                f"{self.plot_arrays[Measure.TRIP_DISTANCE_FRACTION][block]:.02f}"
                f", wait_time="
                f"{self.plot_arrays[Measure.TRIP_MEAN_WAIT_TIME][block]:.02f}"
                f", wait_fraction="
                f"{self.plot_arrays[Measure.TRIP_MEAN_WAIT_FRACTION][block]:.02f}"
            )
        )

    def _plot_map(self, i, ax):
        """
        Draw the map, with vehicles and trips
        """
        ax.clear()
        if self.title:
            ax.set_title(self.title)
        else:
            ax.set_title(
                (
                    f"{self.sim.city.city_size} blocks, "
                    f"{len(self.sim.vehicles)} vehicles, "
                    f"{self.sim.request_rate:.02f} requests/block"
                )
            )
        # Get the animation interpolation point: the distance added to the
        # previous actual block intersection
        distance_increment = self._interpolation(i) / (
            self.current_interpolation_points + 1
        )
        roadwidth = self._ROADWIDTH_BASE / self.sim.city.city_size
        # Animate the vehicles: one set of arrays for each direction
        # as each direction has a common marker
        x_dict = {}
        y_dict = {}
        color = {}
        size = {}
        markers = ("^", ">", "v", "<")
        # vehicles markers:
        sizes = (20 * roadwidth, 30 * roadwidth, 30 * roadwidth)
        for direction in list(Direction):
            x_dict[direction.name] = []
            y_dict[direction.name] = []
            color[direction.name] = []
            size[direction.name] = []
        locations = [x_dict, y_dict]

        for vehicle in self.sim.vehicles:
            for i in [0, 1]:
                # Position, including edge correction
                x = vehicle.location[i]
                if vehicle.phase != VehiclePhase.P1 or self.sim.idle_vehicles_moving:
                    x += distance_increment * vehicle.direction.value[i]
                x = (
                    x + self.display_fringe
                ) % self.sim.city.city_size - self.display_fringe
                # Make the displayed-position fit on the map, with
                # fringe display_fringe around the edges
                locations[i][vehicle.direction.name].append(x)
            size[vehicle.direction.name].append(sizes[vehicle.phase.value])
            color[vehicle.direction.name].append(
                self.color_palette[vehicle.phase.value]
            )
        for i, direction in enumerate(list(Direction)):
            ax.scatter(
                locations[0][direction.name],
                locations[1][direction.name],
                s=size[direction.name],
                marker=markers[i],
                color=color[direction.name],
                alpha=0.8,
            )

        x_origin = []
        y_origin = []
        x_destination = []
        y_destination = []
        for trip in self.sim.trips:
            logging.debug(f"In map drawing: loop over {len(self.sim.trips)} trips")
            if trip.phase in (TripPhase.UNASSIGNED, TripPhase.WAITING):
                x_origin.append(trip.origin[0])
                y_origin.append(trip.origin[1])
            if trip.phase == TripPhase.RIDING:
                x_destination.append(trip.destination[0])
                y_destination.append(trip.destination[1])
        ax.scatter(
            x_origin,
            y_origin,
            s=30 * roadwidth,
            marker="o",
            color=self.color_palette[3],
            alpha=0.8,
            label="Ride request",
        )
        ax.scatter(
            x_destination,
            y_destination,
            s=40 * roadwidth,
            marker="*",
            color=self.color_palette[4],
            label="Ride destination",
        )

        # Draw the map: the second term is a bit of wrapping
        # so that the outside road is shown properly
        ax.set_xlim(-self.display_fringe, self.sim.city.city_size - self.display_fringe)
        ax.set_ylim(-self.display_fringe, self.sim.city.city_size - self.display_fringe)
        ax.xaxis.set_major_locator(ticker.MultipleLocator(1))
        ax.yaxis.set_major_locator(ticker.MultipleLocator(1))
        ax.grid(True, which="major", axis="both", lw=roadwidth)
        ax.set_xticklabels([])
        ax.set_yticklabels([])

    def _plot_histograms(self, block, histogram_list, ax):
        """
        Plot histograms of WAIT_TIME and TRIP_DISTANCE
        """
        ax.clear()
        width = 0.9 / len(histogram_list)
        offset = 0
        index = np.arange(self.sim.city.city_size + 1)
        ymax = [0, 0]
        for key, histogram in enumerate(histogram_list):
            y = np.true_divide(
                self.histograms[histogram], sum(self.histograms[histogram])
            )
            ymax[key] = max([max(y), ymax[key]])
            if np.isnan(ymax[key]):
                logging.warning("ymax[key] is NaN")
                ymax[key] = 1.0
            ax.bar(
                x=index + offset,
                height=y,
                width=width,
                color=self.color_palette[key + 2],
                bottom=0,
                alpha=0.8,
                label=histogram.value,
            )
            offset += width
        ytop = int(max(ymax) * 1.2 * 5.0 + 1.0) / 5.0
        # TODO Caption code is copied and pasted from plot_stats. Don't!
        caption = (
            f"{self.sim.city.city_size} blocks\n"
            f"{len(self.sim.vehicles)} vehicles\n"
            f"{self.sim.request_rate:.02f} requests/block\n"
            f"Trip length in "
            f"[{self.sim.min_trip_distance}, "
            f"{self.sim.max_trip_distance}]\n"
            f"Inhomogeneity: {self.sim.city.inhomogeneity}\n"
            f"Inhomogeneous destinations "
            f"{self.sim.city.inhomogeneous_destinations}\n"
            f"{self.sim.time_blocks}-block simulation\n"
            f"Generated on {datetime.now().strftime('%Y-%m-%d')}"
        )
        caption_location = "upper left"
        caption_props = {"fontsize": 10, "family": ["sans-serif"], "linespacing": 2.0}
        anchored_text = offsetbox.AnchoredText(
            caption,
            loc=caption_location,
            bbox_to_anchor=(1.0, 1.0),
            bbox_transform=ax.transAxes,
            frameon=False,
            prop=caption_props,
        )
        ax.add_artist(anchored_text)
        annotation_props = {
            # 'backgroundcolor': '#FAFAF2',
            "fontsize": 10,
            "color": "darkslategrey",
            "alpha": 0.9,
            "family": ["sans-serif"],
            "linespacing": 2.0,
        }
        anchored_annotation = offsetbox.AnchoredText(
            self.sim.annotation,
            loc=caption_location,
            bbox_to_anchor=(1.0, 0.0, 0.4, 0.5),
            bbox_transform=ax.transAxes,
            height=5.5,
            frameon=False,
            prop=annotation_props,
        )
        ax.add_artist(anchored_annotation)
        ax.axvline(
            self.plot_arrays[Measure.TRIP_MEAN_DISTANCE][block - 1],
            ymin=0,
            ymax=ymax[0] * 1.2 / ytop,
            # alpha=0.8,
            color=self.color_palette[2],
            linestyle="dashed",
            linewidth=1,
        )
        ax.axvline(
            self.plot_arrays[Measure.TRIP_MEAN_WAIT_TIME][block - 1],
            ymin=0,
            ymax=ymax[1] * 1.2 / ytop,
            # alpha=0.8,
            color=self.color_palette[3],
            linestyle="dashed",
            linewidth=1,
        )
        if self.title:
            ax.set_title(self.title)
        else:
            ax.set_title(
                f"City size {self.sim.city.city_size}"
                f", N_v={len(self.sim.vehicles)}"
                f", R={self.sim.request_rate:.01f}"
                f", block {block}"
            )
        # ax.set_xticks(index + width / 2)
        # ax.set_xticklabels(index)
        ax.set_xlabel("Time or Distance")
        ax.set_ylabel("Fraction")
        ax.set_ylim(bottom=0.0, top=ytop)
        x_tick_count = 8
        x_tick_interval = int(self.sim.city.city_size / x_tick_count)
        xlocs = [x for x in range(0, self.sim.city.city_size + 1, x_tick_interval)]
        # xlabels = [
        # f"{x / 60.0:.01f}" for x in range(self.sim.city.city_size)
        # if x % 30 == 0
        # ]
        xlabels = [f"{x}" for x in xlocs]
        ax.set_xticks(xlocs)
        ax.set_xticklabels(xlabels)
        ax.legend()

    def _plot_stats(self, i, ax, fractional=True):
        """
        For a list of Measure arrays that describe fractional properties,
        draw them on a plot with vertical axis [0,1]
        """
        if self._interpolation(i) == 0:
            # only plot at actual time increments, not interpolated frames
            ax.clear()
            if self.title:
                title = self.title
            else:
                rr = self.state_dict[Measure.TRIP_MEAN_REQUEST_RATE.name]
                title = (
                    f"{self.state_dict['city_size']} blocks, "
                    f"{self.state_dict[Measure.VEHICLE_MEAN_COUNT.name]} "
                    f"vehicles, {rr:.02f} requests/block"
                )
            ax.set_title(title)
            x_range = range(len(self.plotstat_list))
            label = []
            tick_label = []
            color = []
            y_array = []
            for key, this_property in enumerate(self.plotstat_list):
                current_value = self.state_dict[this_property.name]
                color.append(self.color_palette[key])
                label.append(this_property.value)
                y_array.append(current_value)
            ymin = 0
            ymax = 1.1
            caption = (
                "Input:\n"
                f"{self.sim.city.city_size} blocks\n"
                f"{len(self.sim.vehicles)} vehicles\n"
                f"{self.sim.request_rate:.02f} requests/block\n"
                f"Trip length in "
                f"[{self.sim.min_trip_distance}, "
                f"{self.sim.max_trip_distance}]\n"
                f"Inhomogeneity: {self.sim.city.inhomogeneity}\n"
                f"Inhomogeneous destinations "
                f"{self.sim.city.inhomogeneous_destinations}\n"
                f"Time block: {i}\n"
                f"Generated on {datetime.now().strftime('%Y-%m-%d')}"
            )
            if self.sim.equilibrate and self.sim.equilibration == Equilibration.PRICE:
                ymin = -0.25
                ymax = 1.1
                utility = self.state_dict[Measure.VEHICLE_MEAN_SURPLUS.name]
                caption_eq = (
                    f"Equilibration:\n"
                    f"  utility $= p_3p(1-f)-c$\n"
                    f"  $= (p_3)({self.sim.price:.02f})"
                    f"(1-{self.sim.platform_commission:.02f})"
                    f"-{self.sim.reservation_wage:.02f}$\n"
                    f"  $= "
                    f"{utility:.02f}$"
                )
                if self.sim.price != 1.0 and self.sim.demand_elasticity != 0.0:
                    caption_eq += (
                        "\n  demand = $kp^{-e}"
                        f" = ({self.sim.base_demand:.01f})"
                        f"({self.sim.price:.01f}"
                        f"^{{{self.sim.demand_elasticity:.01f}}})$\n"
                        f"  $= {self.sim.request_rate:.02f}$ "
                        "requests/block\n"
                    )
            else:
                caption_eq = None
            if fractional:
                caption_location = "upper left"
                # caption_width = 0.3
                caption_linespacing = 1.5
                caption_props = {
                    "fontsize": 9,
                    "family": ["sans-serif"],
                    "color": "darkslategrey",
                    "linespacing": caption_linespacing,
                }
                anchored_text = offsetbox.AnchoredText(
                    caption,
                    loc=caption_location,
                    bbox_to_anchor=(1.0, 1.0),
                    bbox_transform=ax.transAxes,
                    frameon=False,
                    prop=caption_props,
                )
                ax.add_artist(anchored_text)
                if caption_eq:
                    caption_eq_props = {
                        "fontsize": 9,
                        "family": ["sans-serif"],
                        "color": "darkslategrey",
                        "linespacing": caption_linespacing,
                    }
                    anchored_text_eq = offsetbox.AnchoredText(
                        caption_eq,
                        loc=caption_location,
                        bbox_to_anchor=(1.0, 0.6),
                        bbox_transform=ax.transAxes,
                        frameon=False,
                        prop=caption_eq_props,
                    )
                    ax.add_artist(anchored_text_eq)
                annotation_props = {
                    # 'backgroundcolor': '#FAFAF2',
                    "fontsize": 9,
                    "color": "darkslategrey",
                    "alpha": 0.9,
                    "family": ["sans-serif"],
                    "linespacing": caption_linespacing,
                }
                anchored_annotation = offsetbox.AnchoredText(
                    self.sim.annotation,
                    loc=caption_location,
                    bbox_to_anchor=(1.0, 0.3),
                    bbox_transform=ax.transAxes,
                    frameon=False,
                    prop=annotation_props,
                )
                ax.add_artist(anchored_annotation)
                if self.pause_plot:
                    watermark_props = {
                        "fontsize": 36,
                        "color": "darkslategrey",
                        "alpha": 0.2,
                        "family": ["sans-serif"],
                    }
                    watermark = offsetbox.AnchoredText(
                        "PAUSED",
                        loc="center",
                        bbox_to_anchor=(0.5, 0.5),
                        bbox_transform=ax.transAxes,
                        frameon=False,
                        prop=watermark_props,
                    )
                    ax.add_artist(watermark)

                ax.set_ylabel("Fractional values")
            tick_label.append("P1")
            tick_label.append("P2")
            tick_label.append("P3")
            tick_label.append("Wait (W/L)")
            tick_label.append("Distance (L/C)")
            if self.sim.equilibrate and self.sim.equilibration != "none":
                tick_label.append("Utility")
            ax.bar(
                x_range,
                height=y_array,
                width=0.7,
                color=color,
                tick_label=tick_label,
                bottom=0,
                alpha=0.6,
            )
            ax.set_ylim(bottom=ymin, top=ymax)
            ylocs = [y / 10 for y in range(int(ymin * 10), int(ymax * 10))]
            ax.set_yticks(ylocs)
            # Draw the x axis as a thicker line
            # ax.axhline(y=0, linewidth=3, color="white", zorder=-1)
            # for _, s in ax.spines.items():
            # s.set_linewidth = 5
            # ax.legend(label, loc='upper left')

    def _interpolation(self, frame_index):
        """
        For plotting, we use interpolation points to give smoother
        motion in the map. With key events we can change the
        points in the middle of a simulation.
        This function tells us if the frame represents a new block
        or is an interpolation point.
        """
        return frame_index % (self.current_interpolation_points + 1)

    def _run_animation(self, anim, plt):
        """
        Generic output functions
        """
        if self.animation_output_file:
            if self.animation_output_file.endswith("mp4"):
                writer = animation.FFMpegFileWriter(fps=10, bitrate=1800)
                print(f"Saving animation to {self.animation_output_file}...")
                anim.save(self.animation_output_file, writer=writer)
                del anim
            elif self.animation_output_file.endswith("gif"):
                writer = animation.ImageMagickFileWriter()
                print(f"Saving animation to {self.animation_output_file}...")
                anim.save(self.animation_output_file, writer=writer)
                del anim
        else:
            if self.in_jupyter:
                print("In _run_animation: in_jupyter = True")
                # rc('anim', html='jshtml')
                # Disabled for now (2021-07-09)
                # HTML(anim.to_jshtml())
            plt.show()
            del anim
            plt.close()
