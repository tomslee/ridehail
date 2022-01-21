import logging
import enum
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
import json
import sys
from matplotlib import offsetbox
from datetime import datetime
from matplotlib import ticker
from matplotlib import animation  # , rc
from pandas.plotting import register_matplotlib_converters
# from IPython.display import HTML
from ridehail import atom, simulation
from ridehail import config as rh_config

register_matplotlib_converters()

PLOTTING_OFFSET = 128
FRAME_INTERVAL = 50
# Placeholder frame count for animation.
FRAME_COUNT_UPPER_LIMIT = 10000000
CHART_X_RANGE = 245
mpl.rcParams['figure.dpi'] = 100
mpl.rcParams['savefig.dpi'] = 100
sns.set()
sns.set_style("darkgrid")
sns.set_palette("muted")
# sns.set_context("talk")

DISPLAY_FRINGE = 0.25


class PlotArray(enum.Enum):
    VEHICLE_IDLE_FRACTION = "Vehicle idle (p1)"
    VEHICLE_DISPATCH_FRACTION = "Vehicle dispatch (p2)"
    VEHICLE_PAID_FRACTION = "Vehicle paid (p3)"
    VEHICLE_COUNT = "Vehicle count"
    VEHICLE_UTILITY = "Vehicle utility"
    TRIP_MEAN_WAIT_TIME = "Trip wait time"
    TRIP_MEAN_DISTANCE = "Trip distance"
    TRIP_WAIT_FRACTION = "Trip wait time (fraction)"
    TRIP_DISTANCE_FRACTION = "Trip distance / city size"
    TRIP_COUNT = "Trips completed"
    TRIP_COMPLETED_FRACTION = "Trips completed (fraction)"
    TRIP_REQUEST_RATE = "Request rate (relative)"
    PLATFORM_INCOME = "Platform income"


class HistogramArray(enum.Enum):
    HIST_TRIP_WAIT_TIME = "Wait time"
    HIST_TRIP_DISTANCE = "Trip distance"


class Animation(enum.Enum):
    NONE = "none"
    MAP = "map"
    STATS = "stats"
    ALL = "all"
    BAR = "bar"  # plot histograms of phase distributions
    SEQUENCE = "sequence"


class RideHailAnimation():
    """
    The plotting parts.
    """
    __all__ = ['RideHailAnimation']
    ROADWIDTH_BASE = 60.0

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
        self.frame_index = 0
        self.display_fringe = DISPLAY_FRINGE
        self.color_palette = sns.color_palette()
        # Only reset the interpoation points at an intersection.
        # Need a separate variable to hold it here
        self.current_interpolation_points = self.interpolation_points
        self.pause_plot = False  # toggle for pausing
        self.axes = []
        self.in_jupyter = False
        self.stats = {}
        for stat in list(PlotArray):
            self.stats[stat] = np.zeros(sim.time_blocks + 1)
        self.histograms = {}
        for histogram in list(HistogramArray):
            self.histograms[histogram] = np.zeros(sim.city.city_size + 1)
        self.plotstat_list = []
        self.changed_plotstat_flag = False
        self._set_plotstat_list()
        # TODO: IMAGEMAGICK_EXE is hardcoded here. Put it in a config file.
        # It is in a config file but I don't think I do anything with it yet.
        # IMAGEMAGICK_DIR = "/Program Files/ImageMagick-7.0.9-Q16"
        # IMAGEMAGICK_DIR = "/Program Files/ImageMagick-7.0.10-Q16-HDRI"
        # For ImageMagick configuration, see
        # https://stackoverflow.com/questions/23417487/saving-a-matplotlib-animation-with-imagemagick-and-without-ffmpeg-or-mencoder/42565258#42565258
        # -------------------------------------------------------------------------------
        # Set up graphicself.color_palette['figure.figsize'] = [7.0, 4.0]

        mpl.rcParams['animation.convert_path'] = (
            self.sim.config.imagemagick_dir.value + "/magick.exe")
        mpl.rcParams['animation.ffmpeg_path'] = (
            self.sim.config.imagemagick_dir.value + "/ffmpeg.exe")
        mpl.rcParams['animation.embed_limit'] = 2**128
        # mpl.rcParams['font.size'] = 12
        # mpl.rcParams['legend.fontsize'] = 'large'
        # mpl.rcParams['figure.titlesize'] = 'medium'

    def animate(self):
        """
        Do the simulation but with displays
        """
        self.sim.results = simulation.RideHailSimulationResults(self.sim)
        output_file_handle = open(f"{self.sim.config.jsonl_file}", 'a')
        # output_dict copied from RideHailSimulation.simulate(). Not good
        # practice
        output_dict = {}
        output_dict["config"] = rh_config.WritableConfig(
            self.sim.config).__dict__
        output_file_handle.write(json.dumps(output_dict) + "\n")
        # self.sim.write_config(output_file_handle)
        ncols = 1
        plot_size_x = 8
        plot_size_y = 8
        if self.animation_style in (Animation.MAP, ) and self.annotation:
            # Allow space for annotation at right
            plot_size_x += 4
            plot_size_y = 8
        if self.animation_style in (Animation.ALL, ):
            ncols += 1
        if self.animation_style in (Animation.STATS, Animation.SEQUENCE):
            plot_size_x = 16
            plot_size_y = 8
        fig, self.axes = plt.subplots(ncols=ncols,
                                      figsize=(ncols * plot_size_x,
                                               plot_size_y))
        # plt.tight_layout(rect=[0, 0, 0.75, 1])
        plt.subplots_adjust(right=0.8)
        fig.canvas.mpl_connect('button_press_event', self.on_click)
        fig.canvas.mpl_connect('key_press_event', self.on_key_press)
        # print keys
        if not self.animation_output_file:
            self.print_keyboard_controls()
        self.axes = [self.axes] if ncols == 1 else self.axes
        # Position the display window on the screen
        self.fig_manager = plt.get_current_fig_manager()
        if hasattr(self.fig_manager, "window"):
            if hasattr(self.fig_manager.window, "wm_geometry"):
                # self.fig_manager.window.wm_geometry("+10+10").set_window_title(
                self.fig_manager.window.wm_geometry("").set_window_title(
                    f"Ridehail Animation - "
                    f"{self.sim.config.config_file_root}")
                # self.fig_manager.full_screen_toggle()
                self._animation = animation.FuncAnimation(
                    fig,
                    self._next_frame,
                    frames=(FRAME_COUNT_UPPER_LIMIT),
                    fargs=[output_file_handle],
                    interval=FRAME_INTERVAL,
                    repeat=False,
                    repeat_delay=3000)
            else:
                if self.animation_style in (Animation.ALL, Animation.MAP):
                    frame_count = self.sim.time_blocks * (
                        self.interpolation_points + 1)
                else:
                    frame_count = self.sim.time_blocks
                self._animation = animation.FuncAnimation(
                    fig,
                    self._next_frame,
                    frames=frame_count,
                    fargs=[output_file_handle],
                    interval=FRAME_INTERVAL,
                    repeat=False,
                    repeat_delay=3000)
        self.run_animation(self._animation, plt)
        if hasattr(self.sim.config, "config_file_root"):
            fig.savefig(f"./img/{self.sim.config.config_file_root}"
                        f"-{self.sim.config.start_time}.png")
        self.sim.results.end_state = self.sim.results.compute_end_state()
        output_dict["results"] = self.sim.results.end_state
        output_file_handle.write(json.dumps(output_dict) + "\n")
        output_file_handle.close()

    def on_click(self, event):
        self.pause_plot ^= True

    def print_keyboard_controls(self):
        """
        For user convenience, print the keyboard controls
        """
        print("")
        print("Animation keyboard controls:")
        print("\tN|n: increase/decrease vehicle count by 1")
        print("\tCtrl+N|Ctrl+n: increase/decrease vehicle count by 10")
        print("\tK|k: increase/decrease base demand by 0.1")
        print("\tCtrl+K|Ctrl+k: increase/decrease base demand by 1.0")
        print("\tF|f: increase/decrease platform commission by 0.05")
        print("\tI|i: increase/decrease trip inhomogeneity by 0.1")
        print("\tL|i: increase/decrease max trip distance by 1")
        print("\tP|p: increase/decrease price by 0.1")
        print("\tR|r: increase/decrease demand elasticity by 0.1")
        print("\tU|u: increase/decrease reserved wage by 0.01")
        print("\tV|v: increase/decrease apparent speed on map")
        print("\tC|c: increase/decrease city size by one block")
        print("\tCtrl+E: toggle equilibration")
        print("\tM|m: toggle full screen")
        print("\tCtrl+a: move to next animation type")
        print("\tEsc: toggle simulation (pause / run)")
        print("\tQ|q: quit")

    def on_key_press(self, event):
        """
        Respond to shortcut keys
        """
        # logging.debug(f"key pressed: {event.key}")
        sys.stdout.flush()
        if event.key == "N":
            self.sim.target_state["vehicle_count"] += 1
        elif event.key == "n":
            self.sim.target_state["vehicle_count"] = max(
                (self.sim.target_state["vehicle_count"] - 1), 0)
        if event.key == "ctrl+N":
            self.sim.target_state["vehicle_count"] += 10
        elif event.key == "ctrl+n":
            self.sim.target_state["vehicle_count"] = max(
                (self.sim.target_state["vehicle_count"] - 10), 0)
        elif event.key == "K":
            self.sim.target_state["base_demand"] = (
                self.sim.target_state["base_demand"] + 0.1)
        elif event.key == "k":
            self.sim.target_state["base_demand"] = max(
                (self.sim.target_state["base_demand"] - 0.1), 0)
        elif event.key == "ctrl+K":
            self.sim.target_state["base_demand"] = (
                self.sim.target_state["base_demand"] + 1.0)
        elif event.key == "ctrl+k":
            self.sim.target_state["base_demand"] = max(
                (self.sim.target_state["base_demand"] - 1.0), 0)
        elif event.key == "L":
            self.sim.target_state["max_trip_distance"] = min(
                (self.sim.target_state["max_trip_distance"] + 1),
                self.sim.target_state["city_size"])
        elif event.key == "l":
            self.sim.target_state["max_trip_distance"] = max(
                (self.sim.target_state["max_trip_distance"] - 1), 1)
        elif event.key == ("f"):
            self.sim.target_state["platform_commission"] = (
                self.sim.target_state["platform_commission"] - 0.05)
        elif event.key == ("F"):
            self.sim.target_state["platform_commission"] = (
                self.sim.target_state["platform_commission"] + 0.05)
        elif event.key == "p":
            self.sim.target_state["price"] = max(
                self.sim.target_state["price"] - 0.1, 0.1)
        elif event.key == "P":
            self.sim.target_state[
                "price"] = self.sim.target_state["price"] + 0.1
        elif event.key in ("m", "M"):
            self.fig_manager.full_screen_toggle()
        elif event.key in ("q", "Q"):
            try:
                self._animation.event_source.stop()
            except AttributeError:
                print("  User pressed 'q': quitting")
                return
        elif event.key == "r":
            self.sim.target_state["demand_elasticity"] = max(
                self.sim.target_state["demand_elasticity"] - 0.1, 0.0)
        elif event.key == "R":
            self.sim.target_state["demand_elasticity"] = min(
                self.sim.target_state["demand_elasticity"] + 0.1, 1.0)
        elif event.key == "u":
            self.sim.target_state["reserved_wage"] = max(
                self.sim.target_state["reserved_wage"] - 0.01, 0.1)
        elif event.key == "U":
            self.sim.target_state["reserved_wage"] = min(
                self.sim.target_state["reserved_wage"] + 0.01, 1.0)
        elif event.key == "v":
            # Only apply if the map is being displayed
            if self.animation_style in (Animation.ALL, Animation.MAP):
                self.interpolation_points = max(
                    self.current_interpolation_points + 1, 0)
        elif event.key == "V":
            if self.animation_style in (Animation.ALL, Animation.MAP):
                self.interpolation_points = max(
                    self.current_interpolation_points - 1, 0)
        elif event.key == "c":
            self.sim.target_state["city_size"] = max(
                self.sim.target_state["city_size"] - 1, 2)
        elif event.key == "C":
            self.sim.target_state["city_size"] = max(
                self.sim.target_state["city_size"] + 1, 2)
        elif event.key == "i":
            self.sim.target_state["trip_inhomogeneity"] -= min(
                self.sim.target_state["trip_inhomogeneity"], 0.1)
            self.sim.target_state["trip_inhomogeneity"] = round(
                self.sim.target_state["trip_inhomogeneity"], 2)
        elif event.key == "I":
            self.sim.target_state["trip_inhomogeneity"] += min(
                1.0 - self.sim.target_state["trip_inhomogeneity"], 0.1)
            self.sim.target_state["trip_inhomogeneity"] = round(
                self.sim.target_state["trip_inhomogeneity"], 2)
        elif event.key in ("ctrl+E", "ctrl+e"):
            self.sim.target_state[
                "equilibrate"] = not self.sim.target_state["equilibrate"]
            if self.sim.target_state[
                    "equilibration"] == atom.Equilibration.NONE:
                self.sim.target_state[
                    "equilibration"] = atom.Equilibration.PRICE
            elif (self.sim.target_state["equilibration"] ==
                  atom.Equilibration.PRICE):
                self.sim.target_state[
                    "equilibration"] = atom.Equilibration.NONE
            self.changed_plotstat_flag = True
        elif event.key == "ctrl+a":
            if self._animate == Animation.MAP:
                self._animate = Animation.ALL
            elif self._animate == Animation.ALL:
                self._animate = Animation.STATS
            elif self._animate == Animation.STATS:
                self._animate = Animation.MAP
            else:
                logging.info(f"Animation unchanged at {self._animate}")
        elif event.key in ("escape", " "):
            self.pause_plot ^= True

    def _set_plotstat_list(self):
        """
        Set the list of lines to plot
        """
        self.plotstat_list = []
        if self.animation_style in (Animation.ALL, Animation.STATS):
            if (not self.sim.equilibrate
                    or self.sim.equilibration == atom.Equilibration.NONE):
                if self.animation_style in (Animation.ALL, Animation.STATS):
                    self.plotstat_list.append(PlotArray.VEHICLE_IDLE_FRACTION)
                    self.plotstat_list.append(
                        PlotArray.VEHICLE_DISPATCH_FRACTION)
                    self.plotstat_list.append(PlotArray.VEHICLE_PAID_FRACTION)
                if self.animation_style in (Animation.ALL, Animation.STATS):
                    self.plotstat_list.append(PlotArray.TRIP_WAIT_FRACTION)
                    self.plotstat_list.append(PlotArray.TRIP_DISTANCE_FRACTION)
                    # self.plotstat_list.append(
                    # PlotArray.TRIP_COMPLETED_FRACTION)
            else:
                self.plotstat_list.append(PlotArray.VEHICLE_IDLE_FRACTION)
                self.plotstat_list.append(PlotArray.VEHICLE_DISPATCH_FRACTION)
                self.plotstat_list.append(PlotArray.VEHICLE_PAID_FRACTION)
                if self.sim.equilibration in (atom.Equilibration.PRICE,
                                              atom.Equilibration.SUPPLY):
                    self.plotstat_list.append(PlotArray.VEHICLE_COUNT)
                    self.plotstat_list.append(PlotArray.VEHICLE_UTILITY)
                self.plotstat_list.append(PlotArray.TRIP_WAIT_FRACTION)
                # Should plot this only if max_wait_time is not None
                # self.plotstat_list.append(PlotArray.TRIP_COMPLETED_FRACTION)
                # self.plotstat_list.append(PlotArray.TRIP_DISTANCE_FRACTION)
                if self.sim.equilibration == atom.Equilibration.PRICE:
                    # self.plotstat_list.append(PlotArray.PLATFORM_INCOME)
                    self.plotstat_list.append(PlotArray.TRIP_REQUEST_RATE)

    def _next_frame(self, ii, *fargs):
        """
        Function called from animator to generate frame ii of the animation.

        Ignore ii and handle the frame counter myself through self.frame_index
        to handle pauses.
        """
        # Set local variables for frame index and block values
        output_file_handle = fargs[0]
        i = self.frame_index
        block = self.sim.block_index
        if block >= self.sim.time_blocks:
            # The simulation is complete
            logging.info(f"Period {self.sim.block_index}: animation completed")
            # TODO This does not quit the simulation
            self.frame_index = FRAME_COUNT_UPPER_LIMIT + 1
            if hasattr(self._animation.event_source, "stop"):
                self._animation.event_source.stop()
                logging.info("animation.event_source stop")
            else:
                plt.close()
            return
        if not self.pause_plot:
            # OK, we are plotting. Increment
            self.frame_index += 1
        if (self._interpolation(i) == 0 and not self.pause_plot):
            # A "real" time point. Carry out a step of simulation
            # If the plotting is paused, don't compute the next block,
            # just redisplay what we have.
            # next_block updates the block_index
            # Only change the current interpolation points by at most one
            self.sim.next_block(output_file_handle)
            if (self.changed_plotstat_flag or self.sim.changed_plotstat_flag):
                self._set_plotstat_list()
                self.changed_plotstat_flag = False
            logging.debug(f"Animation in progress: frame {i}")
            self.current_interpolation_points = self.interpolation_points
        # Now call the plotting functions
        if (self.animation_style == Animation.BAR
                and self.frame_index < self.sim.city.city_size):
            return
        axis_index = 0
        if self.animation_style in (Animation.ALL, Animation.MAP):
            self._plot_map(i, self.axes[axis_index])
            axis_index += 1
        if self.animation_style in (Animation.ALL, Animation.STATS):
            if block % self.animate_update_period == 0:
                self._update_plot_arrays(block)
                self._plot_stats(i,
                                 self.axes[axis_index],
                                 self.plotstat_list,
                                 fractional=True)
            axis_index += 1
        if self.animation_style in [Animation.BAR]:
            histogram_list = [
                HistogramArray.HIST_TRIP_DISTANCE,
                HistogramArray.HIST_TRIP_WAIT_TIME
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
            if trip.phase == atom.TripPhase.COMPLETED:
                for histogram in histogram_list:
                    try:
                        if histogram == HistogramArray.HIST_TRIP_WAIT_TIME:
                            if (trip.phase_time[atom.TripPhase.WAITING] <
                                    self.sim.city.city_size):
                                # The arrays don't hold very long wait times,
                                # which may happen when there are few vehicles
                                self.histograms[histogram][trip.phase_time[
                                    atom.TripPhase.WAITING]] += 1
                        elif histogram == HistogramArray.HIST_TRIP_DISTANCE:
                            self.histograms[histogram][trip.distance] += 1
                    except IndexError as e:
                        logging.error(f"{e}\n"
                                      f"histogram={histogram}\n"
                                      f"histogram_list={histogram_list}\n"
                                      f"trip.phase_time={trip.phase_time}\n"
                                      f"trip.distance={trip.distance}\n")

    def _update_plot_arrays(self, block):
        """
        Animate statistics are values computed from the History arrays
        but smoothed over self.smoothing_window.
        """
        lower_bound = max((block - self.smoothing_window), 0)
        window_vehicle_time = (sum(
            self.sim.stats[atom.History.VEHICLE_TIME][lower_bound:block]))
        # vehicle stats
        if window_vehicle_time > 0:
            self.stats[PlotArray.VEHICLE_IDLE_FRACTION][block] = (
                sum(self.sim.stats[atom.History.VEHICLE_P1_TIME]
                    [lower_bound:block]) / window_vehicle_time)
            self.stats[PlotArray.VEHICLE_DISPATCH_FRACTION][block] = (
                sum(self.sim.stats[atom.History.VEHICLE_P2_TIME]
                    [lower_bound:block]) / window_vehicle_time)
            self.stats[PlotArray.VEHICLE_PAID_FRACTION][block] = (
                sum(self.sim.stats[atom.History.VEHICLE_P3_TIME]
                    [lower_bound:block]) / window_vehicle_time)
            # Additional items when equilibrating
            if self.sim.equilibration != atom.Equilibration.NONE:
                self.stats[PlotArray.VEHICLE_COUNT][block] = (
                    sum(self.sim.stats[atom.History.VEHICLE_COUNT]
                        [lower_bound:block]) / (block - lower_bound))
                self.stats[PlotArray.TRIP_REQUEST_RATE][block] = (
                    sum(self.sim.stats[atom.History.REQUEST_RATE]
                        [lower_bound:block]) / (block - lower_bound))
                self.stats[PlotArray.PLATFORM_INCOME][block] = (
                    self.sim.price * self.sim.platform_commission *
                    sum(self.sim.stats[atom.History.COMPLETED_TRIPS]
                        [lower_bound:block]) / (block - lower_bound))
                # take average of average utility. Not sure this is the best
                # way, but it may do for now
                utility_list = [
                    self.sim.vehicle_utility(
                        self.stats[PlotArray.VEHICLE_PAID_FRACTION][x])
                    for x in range(lower_bound, block + 1)
                ]
                self.stats[PlotArray.VEHICLE_UTILITY][block] = (
                    sum(utility_list) / len(utility_list))

        # trip stats
        window_request_count = (sum(
            self.sim.stats[atom.History.TRIP_COUNT][lower_bound:block]))
        window_completed_trip_count = (sum(
            self.sim.stats[atom.History.COMPLETED_TRIPS][lower_bound:block]))
        window_total_trip_time = (
            sum(self.sim.stats[atom.History.TRIP_UNASSIGNED_TIME]
                [lower_bound:block]) + sum(self.sim.stats[
                    atom.History.TRIP_AWAITING_TIME][lower_bound:block]) +
            sum(self.sim.stats[atom.History.TRIP_RIDING_TIME]
                [lower_bound:block]))
        if window_request_count > 0 and window_completed_trip_count > 0:
            self.stats[PlotArray.TRIP_MEAN_WAIT_TIME][block] = (
                sum(self.sim.stats[atom.History.WAIT_TIME][lower_bound:block])
                / window_completed_trip_count)
            self.stats[PlotArray.TRIP_MEAN_DISTANCE][block] = (
                sum(self.sim.stats[atom.History.TRIP_DISTANCE]
                    [lower_bound:block]) / window_completed_trip_count)
            self.stats[PlotArray.TRIP_DISTANCE_FRACTION][block] = (
                self.stats[PlotArray.TRIP_MEAN_DISTANCE][block] /
                self.sim.city.city_size)
            self.stats[PlotArray.TRIP_WAIT_FRACTION][block] = (
                sum(self.sim.stats[atom.History.WAIT_TIME][lower_bound:block])
                / window_total_trip_time)
            self.stats[PlotArray.TRIP_COUNT][block] = (window_request_count /
                                                       (block - lower_bound))
            self.stats[PlotArray.TRIP_COMPLETED_FRACTION][block] = (
                window_completed_trip_count / window_request_count)
        logging.debug(
            (f"block={block}"
             f", animation: window_req_c={window_request_count}"
             f", w_completed_trips={window_completed_trip_count}"
             f", trip_distance="
             f"{self.stats[PlotArray.TRIP_MEAN_DISTANCE][block]:.02f}"
             f", trip_distance_fraction="
             f"{self.stats[PlotArray.TRIP_DISTANCE_FRACTION][block]:.02f}"
             f", wait_time="
             f"{self.stats[PlotArray.TRIP_MEAN_WAIT_TIME][block]:.02f}"
             f", wait_fraction="
             f"{self.stats[PlotArray.TRIP_WAIT_FRACTION][block]:.02f}"))

    def _plot_map(self, i, ax):
        """
        Draw the map, with vehicles and trips
        """
        ax.clear()
        if self.title:
            ax.set_title(self.title)
        else:
            ax.set_title((f"{self.sim.city.city_size} blocks, "
                          f"{len(self.sim.vehicles)} vehicles, "
                          f"{self.sim.request_rate:.02f} requests/block"))
        # Get the animation interpolation point: the distance added to the
        # previous actual block intersection
        distance_increment = (self._interpolation(i) /
                              (self.current_interpolation_points + 1))
        roadwidth = self.ROADWIDTH_BASE / self.sim.city.city_size
        # Animate the vehicles: one set of arrays for each direction
        # as each direction has a common marker
        x_dict = {}
        y_dict = {}
        color = {}
        size = {}
        markers = ('^', '>', 'v', '<')
        # vehicles markers:
        sizes = (20 * roadwidth, 30 * roadwidth, 30 * roadwidth)
        for direction in list(atom.Direction):
            x_dict[direction.name] = []
            y_dict[direction.name] = []
            color[direction.name] = []
            size[direction.name] = []
        locations = [x_dict, y_dict]

        for vehicle in self.sim.vehicles:
            for i in [0, 1]:
                # Position, including edge correction
                x = vehicle.location[i]
                if (vehicle.phase != atom.VehiclePhase.IDLE
                        or self.sim.idle_vehicles_moving):
                    x += distance_increment * vehicle.direction.value[i]
                x = ((x + self.display_fringe) % self.sim.city.city_size -
                     self.display_fringe)
                # Make the displayed-position fit on the map, with
                # fringe display_fringe around the edges
                locations[i][vehicle.direction.name].append(x)
            size[vehicle.direction.name].append(sizes[vehicle.phase.value])
            color[vehicle.direction.name].append(
                self.color_palette[vehicle.phase.value])
        for i, direction in enumerate(list(atom.Direction)):
            ax.scatter(locations[0][direction.name],
                       locations[1][direction.name],
                       s=size[direction.name],
                       marker=markers[i],
                       color=color[direction.name],
                       alpha=0.8)

        x_origin = []
        y_origin = []
        x_destination = []
        y_destination = []
        for trip in self.sim.trips:
            logging.debug(
                f"In map drawing: loop over {len(self.sim.trips)} trips")
            if trip.phase in (atom.TripPhase.UNASSIGNED,
                              atom.TripPhase.WAITING):
                x_origin.append(trip.origin[0])
                y_origin.append(trip.origin[1])
            if trip.phase == atom.TripPhase.RIDING:
                x_destination.append(trip.destination[0])
                y_destination.append(trip.destination[1])
        ax.scatter(x_origin,
                   y_origin,
                   s=30 * roadwidth,
                   marker='o',
                   color=self.color_palette[3],
                   alpha=0.8,
                   label="Ride request")
        ax.scatter(x_destination,
                   y_destination,
                   s=40 * roadwidth,
                   marker='*',
                   color=self.color_palette[4],
                   label="Ride destination")

        # Draw the map: the second term is a bit of wrapping
        # so that the outside road is shown properly
        ax.set_xlim(-self.display_fringe,
                    self.sim.city.city_size - self.display_fringe)
        ax.set_ylim(-self.display_fringe,
                    self.sim.city.city_size - self.display_fringe)
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
            y = np.true_divide(self.histograms[histogram],
                               sum(self.histograms[histogram]))
            ymax[key] = max([max(y), ymax[key]])
            if np.isnan(ymax[key]):
                logging.warning("ymax[key] is NaN")
                ymax[key] = 1.0
            ax.bar(x=index + offset,
                   height=y,
                   width=width,
                   color=self.color_palette[key + 2],
                   bottom=0,
                   alpha=0.8,
                   label=histogram.value)
            offset += width
        ytop = int(max(ymax) * 1.2 * 5.0 + 1.0) / 5.0
        ax.axvline(
            self.stats[PlotArray.TRIP_MEAN_DISTANCE][block - 1],
            ymin=0,
            ymax=ymax[0] * 1.2 / ytop,
            # alpha=0.8,
            color=self.color_palette[2],
            linestyle='dashed',
            linewidth=1)
        ax.axvline(
            self.stats[PlotArray.TRIP_MEAN_WAIT_TIME][block - 1],
            ymin=0,
            ymax=ymax[1] * 1.2 / ytop,
            # alpha=0.8,
            color=self.color_palette[3],
            linestyle='dashed',
            linewidth=1)
        if self.title:
            ax.set_title(self.title)
        else:
            ax.set_title(f"City size {self.sim.city.city_size}"
                         f", N_v={len(self.sim.vehicles)}"
                         f", R={self.sim.request_rate:.01f}"
                         f", block {block}")
        ax.set_xticks(index + width / 2)
        ax.set_xticklabels(index)
        ax.set_xlabel("Time or Distance")
        ax.set_ylabel("Fraction")
        ax.set_ylim(bottom=0.0, top=ytop)
        ax.legend()

    def _plot_stats(self,
                    i,
                    ax,
                    plotstat_list,
                    draw_line_chart=True,
                    fractional=True):
        """
        For a list of PlotArray arrays that describe fractional properties,
        draw them on a plot with vertical axis [0,1]
        """
        if self._interpolation(i) == 0:
            ax.clear()
            block = self.sim.block_index
            lower_bound = max((block - CHART_X_RANGE), 1)
            if block <= lower_bound:
                return
            x_range = list(range(lower_bound, block))
            if self.title:
                title = self.title
            else:
                title = (f"{self.sim.city.city_size} blocks, "
                         f"{len(self.sim.vehicles)} vehicles, "
                         f"{self.sim.request_rate:.02f} requests/block")
            # title = ((
            #    f"Simulation {self.sim.config.config_file_root}.config on "
            #    f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"))
            ax.set_title(title)
            linewidth = 3
            for index, this_property in enumerate(plotstat_list):
                current_value = self.stats[this_property][block - 1]
                y_text = current_value
                if this_property.name.startswith("VEHICLE"):
                    linestyle = "solid"
                    if this_property == PlotArray.VEHICLE_UTILITY:
                        linewidth = 1
                    else:
                        linewidth = 2
                elif this_property.name.startswith("TRIP"):
                    linestyle = "dashed"
                    linewidth = 2
                if this_property == PlotArray.TRIP_DISTANCE_FRACTION:
                    linewidth = 1
                    linestyle = "dotted"
                # Scale the plot so that the y axis goes to the maximum value
                if this_property in (PlotArray.TRIP_REQUEST_RATE,
                                     PlotArray.VEHICLE_COUNT,
                                     PlotArray.PLATFORM_INCOME):
                    y_array = self.stats[this_property][lower_bound:block]
                    ymax = np.max(y_array)
                    if ymax > 0:
                        y_array = np.true_divide(y_array, ymax)
                    y_text = y_array[-1]
                    linestyle = "dotted"
                    linewidth = 3
                else:
                    y_array = self.stats[this_property][lower_bound:block]
                ax.plot(x_range,
                        y_array,
                        color=self.color_palette[index],
                        label=this_property.value,
                        lw=linewidth,
                        ls=linestyle,
                        alpha=0.8)
                if this_property == PlotArray.VEHICLE_COUNT:
                    valign = 'top'
                    value = f"{int(current_value):d}"
                else:
                    valign = 'center'
                    value = f"{current_value:.02f}"
                ax.text(
                    x=max(x_range),
                    y=y_text,
                    s=value,
                    fontsize=10,
                    color=self.color_palette[index],
                    horizontalalignment='left',
                    verticalalignment=valign,
                )
            if ((not self.sim.equilibrate
                 or self.sim.equilibration == atom.Equilibration.NONE)
                    and fractional):
                ymin = 0
                ymax = 1
                caption = (
                    f"{self.sim.city.city_size} block city\n"
                    f"{len(self.sim.vehicles)} vehicles\n"
                    f"{self.sim.request_rate:.02f} requests / block\n"
                    f"trip inhomogeneity: {self.sim.city.trip_inhomogeneity}\n"
                    f"{self.sim.time_blocks}-block simulation\n"
                    f"Generated on {datetime.now().strftime('%Y-%m-%d')}")
            elif (self.sim.equilibrate and self.sim.equilibration
                  in (atom.Equilibration.PRICE, atom.Equilibration.SUPPLY)
                  and fractional):
                ymin = -0.25
                ymax = 1.1
                caption = (
                    f"{self.sim.city.city_size}-block city\n"
                    f"{self.sim.request_rate:.01f} requests/block\n"
                    f"Vehicle count: {len(self.sim.vehicles)}\n"
                    f"Trip length in "
                    f"[{self.sim.min_trip_distance}, "
                    f"{self.sim.max_trip_distance}]\n"
                    f"Trip inhomogeneity={self.sim.city.trip_inhomogeneity}\n"
                    f"{self.sim.time_blocks}-block simulation\n"
                    f"Equlibration: \n"
                    f"    p={self.sim.price:.02f}, "
                    f"f={self.sim.platform_commission:.02f}\n"
                    f"    c={self.sim.reserved_wage:.02f}, "
                    f"k={self.sim.base_demand:.01f}, "
                    f"r={self.sim.demand_elasticity:.01f}.\n")
                # f"{self.sim.equilibration.value.capitalize()}"
                # " equilibration -> Platform income = "
                # f"{self.stats[PlotArray.PLATFORM_INCOME][block-1]:.02f}.\n"
            if fractional:
                caption_in_chart = False
                if caption_in_chart:
                    ax.text(0.05,
                            0.95,
                            caption,
                            bbox={
                                'facecolor': 'lavender',
                                'edgecolor': 'silver',
                                'pad': 10,
                            },
                            verticalalignment="top",
                            horizontalalignment="left",
                            transform=ax.transAxes,
                            fontsize=10,
                            linespacing=2.0)
                else:
                    caption_location = "upper left"
                    caption_props = {
                        'fontsize': 10,
                        'family': ['sans-serif'],
                        'linespacing': 2.0
                    }
                    anchored_text = offsetbox.AnchoredText(
                        caption,
                        loc=caption_location,
                        bbox_to_anchor=(1., 1.),
                        bbox_transform=ax.transAxes,
                        frameon=False,
                        prop=caption_props)
                    ax.add_artist(anchored_text)
                    annotation_props = {
                        # 'backgroundcolor': '#FAFAF2',
                        'fontsize': 11,
                        'color': 'midnightblue',
                        'alpha': 0.9,
                        'family': ['sans-serif'],
                        'linespacing': 2.0
                    }
                    anchored_annotation = offsetbox.AnchoredText(
                        self.sim.annotation,
                        loc=caption_location,
                        bbox_to_anchor=(1., 0.0, 0.4, 0.5),
                        bbox_transform=ax.transAxes,
                        height=5.5,
                        frameon=False,
                        prop=annotation_props)
                    ax.add_artist(anchored_annotation)
                    ax.set_ylabel("Fractional values")
            # ax.set_xlabel("Time / 'hours'")
            # xlocs = [x for x in x_range if x % 30 == 0]
            # xlabels = [f"{x / 60.0:.01f}" for x in x_range if x % 30 == 0]
            # ax.set_xticks(xlocs)
            # ax.set_xticklabels(xlabels)
            ax.set_ylim(bottom=ymin, top=ymax)
            ylocs = [y / 10 for y in range(int(ymin * 10), int(ymax * 10))]
            ax.set_yticks(ylocs)
            # Draw the x axis as a thicker line
            ax.axhline(y=0, linewidth=3, color="white", zorder=-1)
            # for _, s in ax.spines.items():
            # s.set_linewidth = 5
            ax.legend(loc='lower left')

    def _interpolation(self, frame_index):
        """
        For plotting, we use interpolation points to give smoother
        motion in the map. With key events we can change the
        points in the middle of a simulation.
        This function tells us if the frame represents a new block
        or is an interpolation point.
        """
        return frame_index % (self.current_interpolation_points + 1)

    def run_animation(self, anim, plt):
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
                print("In run_animation: in_jupyter = True")
                # rc('anim', html='jshtml')
                # Disabled for now (2021-07-09)
                # HTML(anim.to_jshtml())
            plt.show()
            del anim
            plt.close()
