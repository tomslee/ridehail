#!/usr/bin/python3
import logging
import enum
import numpy as np
import matplotlib as mpl
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from matplotlib import ticker
from matplotlib import animation  # , rc
from pandas.plotting import register_matplotlib_converters
from IPython.display import HTML
from ridehail import atom, simulation
register_matplotlib_converters()

PLOTTING_OFFSET = 128
FRAME_INTERVAL = 50
# Placeholder frame count for animation.
FRAME_COUNT_UPPER_LIMIT = 10000000
CHART_X_RANGE = 245
# TODO: IMAGEMAGICK_EXE is hardcoded here. Put it in a config file.
# It is in a config file but I don't think I do anything with it yet.
IMAGEMAGICK_DIR = "/Program Files/ImageMagick-7.0.9-Q16"
# IMAGEMAGICK_DIR = "/Program Files/ImageMagick-7.0.10-Q16"
# For ImageMagick configuration, see
# https://stackoverflow.com/questions/23417487/saving-a-matplotlib-animation-with-imagemagick-and-without-ffmpeg-or-mencoder/42565258#42565258
# -------------------------------------------------------------------------------
# Set up graphicself.color_palette['figure.figsize'] = [7.0, 4.0]

mpl.rcParams['figure.dpi'] = 90
mpl.rcParams['savefig.dpi'] = 100
mpl.rcParams['animation.convert_path'] = IMAGEMAGICK_DIR + "/magick.exe"
mpl.rcParams['animation.ffmpeg_path'] = IMAGEMAGICK_DIR + "/ffmpeg.exe"
mpl.rcParams['animation.embed_limit'] = 2**128
# mpl.rcParams['font.size'] = 12
# mpl.rcParams['legend.fontsize'] = 'large'
# mpl.rcParams['figure.titlesize'] = 'medium'
sns.set()
sns.set_style("darkgrid")
sns.set_palette("muted")
# sns.set_context("talk")

DISPLAY_FRINGE = 0.25


class PlotArray(enum.Enum):
    VEHICLE_IDLE_FRACTION = "Vehicle idle (p1)"
    VEHICLE_PICKUP_FRACTION = "Vehicle dispatch (p2)"
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
    def __init__(self, sim):
        self.sim = sim
        self._animate = sim.config.animate
        self.smoothing_window = sim.config.smoothing_window
        self.output_file = sim.config.animation_output
        self.frame_index = 0
        self.last_block_frame_index = 0
        self.display_fringe = DISPLAY_FRINGE
        self.color_palette = sns.color_palette()
        self.interpolation_points = sim.config.interpolate
        self.animate_update_period = sim.config.animate_update_period
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

    def animate(self):
        """
        Do the simulation but with displays
        """
        self.sim.results = simulation.RideHailSimulationResults(self.sim)
        self.sim.results.write_config()
        plot_size = 8
        ncols = 1
        if self._animate in (Animation.ALL, ):
            ncols += 1
        fig, self.axes = plt.subplots(ncols=ncols,
                                      figsize=(ncols * plot_size, plot_size))
        fig.canvas.mpl_connect('button_press_event', self.on_click)
        fig.canvas.mpl_connect('key_press_event', self.on_key_press)
        self.axes = [self.axes] if ncols == 1 else self.axes
        # Position the display window on the screen
        self.fig_manager = plt.get_current_fig_manager()
        if hasattr(self.fig_manager, "window"):
            self.fig_manager.window.wm_geometry("+10+10")
            self.fig_manager.set_window_title(
                f"Ridehail Animation - "
                f"{self.sim.config.config_file_root}")
            self.fig_manager.full_screen_toggle()
        self._animation = animation.FuncAnimation(
            fig,
            self._next_frame,
            frames=(FRAME_COUNT_UPPER_LIMIT),
            # fargs=[axes],
            interval=FRAME_INTERVAL,
            repeat=False,
            repeat_delay=3000)
        self.write_animation(self._animation, plt, self.output_file)
        if hasattr(self.sim.config, "config_file_root"):
            fig.savefig(f"./img/{self.sim.config.config_file_root}"
                        f"-{self.sim.config.start_time}.png")
        # self.sim.results.write_results()

    def on_click(self, event):
        self.pause_plot ^= True

    def on_key_press(self, event):
        """
        Respond to shortcut keys
        """
        if event.key == "N":
            self.sim.target_state["vehicle_count"] = max(
                int(self.sim.target_state["vehicle_count"] * 1.1),
                self.sim.target_state["vehicle_count"] + 1)
        elif event.key == "n":
            self.sim.target_state["vehicle_count"] = min(
                int(self.sim.target_state["vehicle_count"] * 0.9),
                (self.sim.target_state["vehicle_count"] - 1))
        if event.key == "ctrl+K":
            self.sim.target_state["base_demand"] = (
                self.sim.target_state["base_demand"] + 1)
        elif event.key == "ctrl+k":
            self.sim.target_state["base_demand"] = max(
                (self.sim.target_state["base_demand"] - 1), 0)
        if event.key == "K":
            self.sim.target_state["base_demand"] = (
                self.sim.target_state["base_demand"] + 0.1)
        elif event.key == "k":
            self.sim.target_state["base_demand"] = max(
                (self.sim.target_state["base_demand"] - 0.1), 0)
        elif event.key in ("f", "h"):
            self.sim.target_state["platform_commission"] = (
                self.sim.target_state["platform_commission"] - 0.02)
        elif event.key in ("F", "H"):
            self.sim.target_state["platform_commission"] = (
                self.sim.target_state["platform_commission"] + 0.02)
        elif event.key == "p":
            self.sim.target_state["price"] = max(
                self.sim.target_state["price"] - 0.1, 0.1)
        elif event.key == "P":
            self.sim.target_state[
                "price"] = self.sim.target_state["price"] + 0.1
        elif event.key in ("m", "M"):
            self.fig_manager.full_screen_toggle()
        elif event.key == "q":
            try:
                self._animation.event_source.stop()
            except AttributeError:
                print("  User pressed 'q': quitting")
                return
        elif event.key == "u":
            self.sim.target_state["reserved_wage"] = max(
                self.sim.target_state["reserved_wage"] - 0.01, 0.1)
        elif event.key == "U":
            self.sim.target_state["reserved_wage"] = min(
                self.sim.target_state["reserved_wage"] + 0.01, 1.0)
        elif event.key == "v":
            # Only apply if the map is being displayed
            if self._animate in (Animation.ALL, Animation.MAP):
                self.interpolation_points = max(self.interpolation_points + 1,
                                                1)
        elif event.key == "V":
            if self._animate in (Animation.ALL, Animation.MAP):
                self.interpolation_points = max(self.interpolation_points - 1,
                                                1)
        elif event.key == "c":
            self.sim.target_state["city_size"] = max(
                self.sim.target_state["city_size"] - 1, 2)
        elif event.key == "C":
            self.sim.target_state["city_size"] = max(
                self.sim.target_state["city_size"] + 1, 2)
        elif event.key == "ctrl+t":
            if self.sim.target_state[
                    "trip_distribution"] == atom.TripDistribution.UNIFORM:
                self.sim.target_state[
                    "trip_distribution"] = atom.TripDistribution.BETA_SHORT
            elif self.sim.target_state[
                    "trip_distribution"] == atom.TripDistribution.BETA_SHORT:
                self.sim.target_state[
                    "trip_distribution"] = atom.TripDistribution.BETA_LONG
            elif self.sim.target_state[
                    "trip_distribution"] == atom.TripDistribution.BETA_LONG:
                self.sim.target_state[
                    "trip_distribution"] = atom.TripDistribution.UNIFORM
        elif event.key == "ctrl+e":
            # TODO: not working well
            if self.sim.target_state["equilibrate"] == atom.Equilibration.NONE:
                self.sim.target_state["equilibrate"] = atom.Equilibration.PRICE
            elif (self.sim.target_state["equilibrate"] ==
                  atom.Equilibration.PRICE):
                self.sim.target_state["equilibrate"] = atom.Equilibration.NONE
            self.changed_plotstat_flag = True
        elif event.key in ("escape", " "):
            self.pause_plot ^= True
        # else:
        # print(f"event.key='{event.key}'")

    def _set_plotstat_list(self):
        """
        Set the list of lines to plot
        """
        self.plotstat_list = []
        if self._animate in (Animation.ALL, Animation.STATS):
            if self.sim.equilibrate == atom.Equilibration.NONE:
                if self._animate in (Animation.ALL, Animation.STATS):
                    self.plotstat_list.append(PlotArray.VEHICLE_IDLE_FRACTION)
                    self.plotstat_list.append(
                        PlotArray.VEHICLE_PICKUP_FRACTION)
                    self.plotstat_list.append(PlotArray.VEHICLE_PAID_FRACTION)
                if self._animate in (Animation.ALL, Animation.STATS):
                    self.plotstat_list.append(PlotArray.TRIP_WAIT_FRACTION)
                    self.plotstat_list.append(PlotArray.TRIP_DISTANCE_FRACTION)
                    # self.plotstat_list.append(
                    # PlotArray.TRIP_COMPLETED_FRACTION)
            else:
                self.plotstat_list.append(PlotArray.VEHICLE_IDLE_FRACTION)
                self.plotstat_list.append(PlotArray.VEHICLE_PICKUP_FRACTION)
                self.plotstat_list.append(PlotArray.VEHICLE_PAID_FRACTION)
                if self.sim.equilibrate in (atom.Equilibration.PRICE,
                                            atom.Equilibration.SUPPLY):
                    self.plotstat_list.append(PlotArray.VEHICLE_COUNT)
                    self.plotstat_list.append(PlotArray.VEHICLE_UTILITY)
                self.plotstat_list.append(PlotArray.TRIP_WAIT_FRACTION)
                self.plotstat_list.append(PlotArray.TRIP_COMPLETED_FRACTION)
                # self.plotstat_list.append(PlotArray.TRIP_DISTANCE_FRACTION)
                if self.sim.equilibrate == atom.Equilibration.PRICE:
                    self.plotstat_list.append(PlotArray.PLATFORM_INCOME)
                    self.plotstat_list.append(PlotArray.TRIP_REQUEST_RATE)

    def _next_frame(self, ii):
        """
        Function called from animator to generate frame ii of the animation.

        Ignore ii and handle the frame counter myself through self.frame_index
        to handle pauses.
        """
        # Set local variables for frame index and block values
        i = self.frame_index
        block = self.sim.block_index
        if block >= self.sim.time_blocks:
            # Quit: simulation is done
            logging.info(f"Period {self.sim.block_index}: animation completed")
            self._animation.event_source.stop()
            return
        if not self.pause_plot:
            # OK, we are plotting. Increment
            self.frame_index += 1
        if (self._interpolation(i) == 0 and not self.pause_plot):
            # A "real" time point. Carry out a step of simulation
            # If the plotting is paused, don't compute the next block,
            # just redisplay what we have.
            # next_block updates the block_index
            self.sim.next_block()
            if self.changed_plotstat_flag:
                self._set_plotstat_list()
                self.changed_plotstat_flag = False
        # Now call the plotting functions
        if (self._animate == Animation.BAR
                and self.frame_index < self.sim.city.city_size):
            logging.info(f"Warming up: block {self.frame_index} "
                         f"of {self.sim.city.city_size}")
            return
        axis_index = 0
        if self._animate in (Animation.ALL, Animation.MAP):
            self._plot_map(i, self.axes[axis_index])
            axis_index += 1
        if self._animate in (Animation.ALL, Animation.STATS):
            if block % self.animate_update_period == 0:
                self._update_plot_arrays(block)
                self._plot_stats(i,
                                 self.axes[axis_index],
                                 self.plotstat_list,
                                 fractional=True)
            axis_index += 1
        if self._animate in [Animation.BAR]:
            histogram_list = [
                HistogramArray.HIST_TRIP_WAIT_TIME,
                HistogramArray.HIST_TRIP_DISTANCE
            ]
            self._update_histogram_arrays(block, histogram_list)
            self._plot_histograms(block, histogram_list, self.axes[axis_index])
            axis_index += 1

    def _update_histogram_arrays(self, block, histogram_list):
        """
        On each move, fill in the histograms
        """
        for trip in self.sim.trips:
            if trip.phase == atom.TripPhase.COMPLETED:
                for histogram in histogram_list:
                    if histogram == HistogramArray.HIST_TRIP_WAIT_TIME:
                        self.histograms[histogram][trip.phase_time[
                            atom.TripPhase.WAITING]] += 1
                    elif histogram == HistogramArray.HIST_TRIP_DISTANCE:
                        self.histograms[histogram][trip.distance] += 1

    def _update_plot_arrays(self, block):
        """
        Animate statistics are values computed from the History arrays
        but smoothed over self.smoothing_window.
        """
        logging.info("in _update_plot_arrays")
        lower_bound = max((block - self.smoothing_window), 0)
        window_vehicle_time = (sum(
            self.sim.stats[atom.History.VEHICLE_TIME][lower_bound:block]))
        # vehicle stats
        if window_vehicle_time > 0:
            self.stats[PlotArray.VEHICLE_IDLE_FRACTION][block] = (
                sum(self.sim.stats[atom.History.VEHICLE_P1_TIME]
                    [lower_bound:block]) / window_vehicle_time)
            self.stats[PlotArray.VEHICLE_PICKUP_FRACTION][block] = (
                sum(self.sim.stats[atom.History.VEHICLE_P2_TIME]
                    [lower_bound:block]) / window_vehicle_time)
            self.stats[PlotArray.VEHICLE_PAID_FRACTION][block] = (
                sum(self.sim.stats[atom.History.VEHICLE_P3_TIME]
                    [lower_bound:block]) / window_vehicle_time)
            # Additional items when equilibrating
            if self.sim.equilibrate != atom.Equilibration.NONE:
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
        logging.info(
            (f"animation: window_req_c={window_request_count}"
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
        ax.set_title((
            f"{self.sim.city.city_size} blocks, "
            f"{len(self.sim.vehicles)} vehicles, "
            f"{self.sim.request_rate:.02f} requests/block, "
            f"{self.sim.city.trip_distribution.name.lower()} trip distribution"
        ))
        # Get the animation interpolation point
        distance_increment = (self._interpolation(i) /
                              self.interpolation_points)
        roadwidth = 60.0 / self.sim.city.city_size
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
        Plot histograms
        """
        ax.clear()
        width = 0.8 / len(histogram_list)
        offset = 0
        ind = np.arange(self.sim.city.city_size + 1)
        ymax = 0
        for histogram in histogram_list:
            y = np.true_divide(self.histograms[histogram],
                               sum(self.histograms[histogram]))
            ymax = max([max(y), ymax])
            if np.isnan(ymax):
                ymax = 1.0
            ax.bar(x=ind + offset,
                   height=y,
                   width=width,
                   bottom=0,
                   label=histogram.value)
            offset += width
        ax.set_title(f"City size {self.sim.city.city_size}"
                     f", N_v={len(self.sim.vehicles)}"
                     f", R={self.sim.request_rate:.01f}"
                     f", block {block}")
        ax.set_xticks(ind + width / 2)
        ax.set_xticklabels(ind)
        ax.set_xlabel("Time or Distance")
        ax.set_ylabel("Fraction")
        ytop = int(ymax * 5 + 1) / 5.0
        ax.set_ylim(bottom=0.0, top=ytop)
        # logging.info(f"Block {block}: ymax = {ymax}, ytop = {ytop}")
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
            lower_bound = max((block - CHART_X_RANGE), 0)
            x_range = list(range(lower_bound, block))
            title = ((
                f"Simulation {self.sim.config.config_file_root}.config on "
                f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"))
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
                if this_property in (PlotArray.TRIP_REQUEST_RATE,
                                     PlotArray.VEHICLE_COUNT,
                                     PlotArray.PLATFORM_INCOME):
                    ymax = np.max(self.stats[this_property][lower_bound:block])
                    y_array = (np.true_divide(
                        self.stats[this_property][lower_bound:block], ymax))
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
                ax.text(
                    x=max(x_range),
                    y=y_text,
                    s=f"{current_value:.02f}",
                    fontsize=12,
                    color=self.color_palette[index],
                    horizontalalignment='left',
                    verticalalignment='center',
                )
            if self.sim.equilibrate == atom.Equilibration.NONE and fractional:
                ymin = 0
                ymax = 1
                caption = (f"{self.sim.city.city_size} block city\n"
                           f"{len(self.sim.vehicles)} vehicles\n"
                           f"{self.sim.request_rate:.02f} requests / block\n"
                           f"{self.sim.city.trip_distribution.name.lower()} "
                           "trip distribution\n"
                           f"{self.sim.time_blocks}-block simulation")
            elif (self.sim.equilibrate == atom.Equilibration.SUPPLY
                  and fractional):
                ymin = -0.25
                ymax = 1.1
                caption = (
                    f"A {self.sim.city.city_size}-block city "
                    f"with {self.sim.request_rate:.01f} requests/block"
                    f", {len(self.sim.vehicles)} vehicles\n"
                    f"{self.sim.equilibrate.value.capitalize()} equilibration"
                    f" with p={self.sim.price:.02f}"
                    f", f={self.sim.platform_commission:.02f}"
                    f", c={self.sim.reserved_wage:.02f}.\n"
                    f"-> I ="
                    f" {self.stats[PlotArray.PLATFORM_INCOME][block - 1]:.02f}"
                    f".\n{self.sim.city.trip_distribution.name.capitalize()} "
                    "trip distribution\n"
                    f"{self.sim.time_blocks}-block simulation")
            elif (self.sim.equilibrate == atom.Equilibration.PRICE
                  and fractional):
                ymin = -0.25
                ymax = 1.1
                caption = (
                    f"{self.sim.city.city_size}-block city"
                    f", p={self.sim.price:.01f}"
                    f", f={self.sim.platform_commission:.02f}"
                    f", c={self.sim.reserved_wage:.02f}"
                    f", k={self.sim.base_demand:.01f}"
                    f", r={self.sim.demand_elasticity:.01f}.\n"
                    f"{self.sim.request_rate:.01f} requests/block, "
                    f"{len(self.sim.vehicles)} vehicles, "
                    f"{self.sim.city.trip_distribution.name.lower()} "
                    "trip distribution\n"
                    f"{self.sim.equilibrate.value.capitalize()}"
                    " equilibration -> I = "
                    f"{self.stats[PlotArray.PLATFORM_INCOME][block - 1]:.02f}."
                    f"\n{self.sim.time_blocks}-block simulation")
            if fractional:
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
        number of interpolation points in the middle of a simulation.
        This function tells us if the frame represents a new block
        or is an interpolation point.
        """
        interpolation_point = (frame_index - self.last_block_frame_index)
        # Inequality in case self.interpolation_points has changed
        # during the block
        if interpolation_point >= self.interpolation_points:
            interpolation_point = 0
            self.last_block_frame_index = frame_index
        return interpolation_point

    def write_animation(self, anim, plt, output_file):
        """
        Generic output functions
        """
        if output_file is not None:
            logging.info(f"Writing output to {output_file}...")
        if output_file.endswith("mp4"):
            writer = animation.FFMpegFileWriter(fps=10, bitrate=1800)
            anim.save(output_file, writer=writer)
            del anim
        elif output_file.endswith("gif"):
            writer = animation.ImageMagickFileWriter()
            anim.save(output_file, writer=writer)
            del anim
        else:
            if self.in_jupyter:
                print("In write_animation: in_jupyter = True")
                # rc('anim', html='jshtml')
                HTML(anim.to_jshtml())
            plt.show()
            del anim
            plt.close()
