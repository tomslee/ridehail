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

FRAME_INTERVAL = 50
# Placeholder frame count for animation.
FRAME_COUNT_UPPER_LIMIT = 10000000
CHART_X_RANGE = 1441
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
    DRIVER_AVAILABLE_FRACTION = "Driver available (p1)"
    DRIVER_PICKUP_FRACTION = "Driver dispatch (p2)"
    DRIVER_PAID_FRACTION = "Driver paid (p3)"
    DRIVER_COUNT_SCALED = "Driver count (relative)"
    DRIVER_UTILITY = "Driver utility"
    TRIP_MEAN_WAIT_TIME = "Trip wait time"
    TRIP_MEAN_DISTANCE = "Trip distance"
    TRIP_WAIT_FRACTION = "Trip wait time (fraction)"
    TRIP_DISTANCE_FRACTION = "Trip distance / city size"
    TRIP_COUNT = "Trips completed"
    TRIP_COMPLETED_FRACTION = "Trips completed (fraction)"
    TRIP_REQUEST_RATE = "Request rate (relative)"


class Animation(enum.Enum):
    NONE = "none"
    MAP = "map"
    STATS = "stats"
    ALL = "all"
    DRIVER = "driver"
    TRIP = "trip"
    SUMMARY = "summary"
    EQUILIBRATION = "equilibration"
    WAIT = "wait"


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
        self.stats = {}
        self.in_jupyter = False
        for stat in list(PlotArray):
            self.stats[stat] = np.zeros(sim.time_blocks + 1)
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
        elif self._animate in (Animation.EQUILIBRATION, ):
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
                        f"-{datetime.now().strftime('%Y-%m-%d-%H-%M')}.png")
        self.sim.results.write_results()

    def on_click(self, event):
        self.pause_plot ^= True

    def on_key_press(self, event):
        """
        Respond to shortcut keys
        """
        if event.key == "+":
            self.sim.target_state["driver_count"] = max(
                int(self.sim.target_state["driver_count"] * 1.1),
                self.sim.target_state["driver_count"] + 1)
        elif event.key == "-":
            self.sim.target_state["driver_count"] = min(
                int(self.sim.target_state["driver_count"] * 0.9),
                (self.sim.target_state["driver_count"] - 1))
        if event.key == "ctrl++":
            self.sim.target_state["base_demand"] = max(
                int(self.sim.target_state["base_demand"] * 1.1),
                self.sim.target_state["base_demand"] + 0.1)
        elif event.key == "ctrl+-":
            self.sim.target_state["base_demand"] = max(
                min((self.sim.target_state["base_demand"] * 0.9),
                    (self.sim.target_state["base_demand"] - 0.1)), 0)
        elif event.key == "f":
            self.sim.target_state["platform_commission"] = (
                self.sim.target_state["platform_commission"] - 0.1)
        elif event.key == "F":
            self.sim.target_state["platform_commission"] = (
                self.sim.target_state["platform_commission"] + 0.1)
        elif event.key == "p":
            self.sim.target_state["price"] = max(
                self.sim.target_state["price"] * 0.9, 0.1)
        elif event.key == "P":
            self.sim.target_state[
                "price"] = self.sim.target_state["price"] * 1.1
        elif event.key in ("m", "M"):
            self.fig_manager.full_screen_toggle()
        elif event.key == "q":
            try:
                self._animation.event_source.stop()
            except AttributeError:
                logging.info("User pressed 'q': quitting")
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
        if self._animate in (Animation.ALL, Animation.STATS, Animation.DRIVER,
                             Animation.TRIP, Animation.EQUILIBRATION):
            if self.sim.equilibrate == atom.Equilibration.NONE:
                if self._animate in (Animation.ALL, Animation.STATS,
                                     Animation.DRIVER):
                    self.plotstat_list.append(
                        PlotArray.DRIVER_AVAILABLE_FRACTION)
                    self.plotstat_list.append(PlotArray.DRIVER_PICKUP_FRACTION)
                    self.plotstat_list.append(PlotArray.DRIVER_PAID_FRACTION)
                if self._animate in (Animation.ALL, Animation.STATS,
                                     Animation.TRIP):
                    self.plotstat_list.append(PlotArray.TRIP_WAIT_FRACTION)
                    # self.plotstat_list.append(PlotArray.TRIP_DISTANCE_FRACTION)
                    # self.plotstat_list.append(
                    # PlotArray.TRIP_COMPLETED_FRACTION)
            else:
                self.plotstat_list.append(PlotArray.DRIVER_AVAILABLE_FRACTION)
                self.plotstat_list.append(PlotArray.DRIVER_PICKUP_FRACTION)
                self.plotstat_list.append(PlotArray.DRIVER_PAID_FRACTION)
                if self.sim.equilibrate in (atom.Equilibration.PRICE,
                                            atom.Equilibration.SUPPLY):
                    self.plotstat_list.append(PlotArray.DRIVER_COUNT_SCALED)
                    self.plotstat_list.append(PlotArray.DRIVER_UTILITY)
                self.plotstat_list.append(PlotArray.TRIP_WAIT_FRACTION)
                self.plotstat_list.append(PlotArray.TRIP_COMPLETED_FRACTION)
                # self.plotstat_list.append(PlotArray.TRIP_DISTANCE_FRACTION)
                if self.sim.equilibrate == atom.Equilibration.PRICE:
                    self.plotstat_list.append(PlotArray.TRIP_REQUEST_RATE)

    def _next_frame(self, ii):
        """
        Function called from animator to generate frame ii of the animation.

        Ignore ii and handle the frame counter myself through self.frame_index
        to handle pauses. Not helping much yet though
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
        for array_name, array in self.stats.items():
            # Initialize arrays
            # create a place to hold stats from this block
            if 1 <= block < self.sim.time_blocks:
                # Copy the previous value into it as the default action
                array[block] = array[block - 1]
        if (self._interpolation(i) == 0 and not self.pause_plot):
            # A "real" time point. Carry out a step of simulation
            # If the plotting is paused, don't compute the next block,
            # just redisplay what we have.
            # next_block updates the block_index
            self.sim.next_block()
            if self.changed_plotstat_flag:
                self._set_plotstat_list()
                self.changed_plotstat_flag = False
            self._update_plot_arrays(block)
        # Now call the plotting functions
        axis_index = 0
        if self._animate in (Animation.ALL, Animation.MAP):
            self._plot_map(i, self.axes[axis_index])
            axis_index += 1
        if self._animate in (Animation.ALL, Animation.STATS):
            # TODO: use the incremented functions or not?
            if block % self.animate_update_period == 0:
                self._plot_stats(i,
                                 self.axes[axis_index],
                                 self.plotstat_list,
                                 fractional=True)
            axis_index += 1
        elif self._animate in (Animation.EQUILIBRATION, ):
            plotstat_list = []
            plotstat_list.append(PlotArray.DRIVER_COUNT_SCALED)
            plotstat_list.append(PlotArray.TRIP_REQUEST_RATE)
            self._plot_stats(i,
                             self.axes[axis_index],
                             plotstat_list,
                             fractional=False)
        # TODO: set an axis that holds the actual button. THis makes all
        # axes[0] into a big button
        # button_plus = Button(axes[0], '+')
        # button_plus.on_clicked(self.on_click)

    def _update_plot_arrays(self, block):
        """
        Animate statistics are values computed from the History arrays
        but smoothed over self.smoothing_window.
        """
        # the lower bound of which cannot be less than zero
        lower_bound = max((block - self.smoothing_window), 0)
        window_driver_time = (
            self.sim.stats[atom.History.CUMULATIVE_DRIVER_TIME][block] -
            self.sim.stats[atom.History.CUMULATIVE_DRIVER_TIME][lower_bound])
        # driver stats
        if window_driver_time > 0:
            self.stats[PlotArray.DRIVER_AVAILABLE_FRACTION][block] = (
                (self.sim.stats[atom.History.CUMULATIVE_DRIVER_P1_TIME][block]
                 - self.sim.stats[atom.History.CUMULATIVE_DRIVER_P1_TIME]
                 [lower_bound]) / window_driver_time)
            self.stats[PlotArray.DRIVER_PICKUP_FRACTION][block] = (
                (self.sim.stats[atom.History.CUMULATIVE_DRIVER_P2_TIME][block]
                 - self.sim.stats[atom.History.CUMULATIVE_DRIVER_P2_TIME]
                 [lower_bound]) / window_driver_time)
            self.stats[PlotArray.DRIVER_PAID_FRACTION][block] = (
                (self.sim.stats[atom.History.CUMULATIVE_DRIVER_P3_TIME][block]
                 - self.sim.stats[atom.History.CUMULATIVE_DRIVER_P3_TIME]
                 [lower_bound]) / window_driver_time)
            # Additional items when equilibrating
            if self.sim.equilibrate != atom.Equilibration.NONE:
                self.stats[PlotArray.DRIVER_COUNT_SCALED][block] = (
                    sum(self.sim.stats[atom.History.DRIVER_COUNT]
                        [lower_bound:block]) /
                    (self.sim.city.city_size * self.sim.city.city_size *
                     (block - lower_bound)))
                self.stats[PlotArray.TRIP_REQUEST_RATE][block] = (
                    sum(self.sim.stats[atom.History.REQUEST_RATE]
                        [lower_bound:block]) / (self.sim.city.city_size *
                                                (block - lower_bound)))
                # take average of average utility. Not sure this is the best
                # way, but it may do for now
                utility_list = [
                    self.sim.driver_utility(
                        self.stats[PlotArray.DRIVER_PAID_FRACTION][x])
                    for x in range(lower_bound, block + 1)
                ]
                self.stats[PlotArray.DRIVER_UTILITY][block] = (
                    sum(utility_list) / len(utility_list))

        # trip stats
        window_request_count = (
            (self.sim.stats[atom.History.CUMULATIVE_TRIP_COUNT][block] -
             self.sim.stats[atom.History.CUMULATIVE_TRIP_COUNT][lower_bound]))
        window_completed_trip_count = (
            self.sim.stats[atom.History.CUMULATIVE_COMPLETED_TRIPS][block] -
            self.sim.stats[
                atom.History.CUMULATIVE_COMPLETED_TRIPS][lower_bound])
        window_total_trip_time = (
            self.sim.stats[atom.History.CUMULATIVE_TRIP_UNASSIGNED_TIME][block]
            - self.sim.stats[
                atom.History.CUMULATIVE_TRIP_UNASSIGNED_TIME][lower_bound] +
            self.sim.stats[atom.History.CUMULATIVE_TRIP_AWAITING_TIME][block] -
            self.sim.stats[
                atom.History.CUMULATIVE_TRIP_AWAITING_TIME][lower_bound] +
            self.sim.stats[atom.History.CUMULATIVE_TRIP_RIDING_TIME][block] -
            self.sim.stats[
                atom.History.CUMULATIVE_TRIP_RIDING_TIME][lower_bound])
        if window_request_count > 0 and window_completed_trip_count > 0:
            self.stats[PlotArray.TRIP_MEAN_WAIT_TIME][block] = (
                (self.sim.stats[atom.History.CUMULATIVE_WAIT_TIME][block] -
                 self.sim.stats[atom.History.CUMULATIVE_WAIT_TIME][lower_bound]
                 ) / window_completed_trip_count)
            self.stats[PlotArray.TRIP_MEAN_DISTANCE][block] = (
                (self.sim.stats[atom.History.CUMULATIVE_TRIP_DISTANCE][block] -
                 self.sim.stats[atom.History.CUMULATIVE_TRIP_DISTANCE]
                 [lower_bound]) / window_completed_trip_count)
            self.stats[PlotArray.TRIP_DISTANCE_FRACTION][block] = (
                self.stats[PlotArray.TRIP_MEAN_DISTANCE][block] /
                self.sim.city.city_size)
            self.stats[PlotArray.TRIP_WAIT_FRACTION][block] = (
                (self.sim.stats[
                    atom.History.CUMULATIVE_TRIP_UNASSIGNED_TIME][block] -
                 self.sim.stats[atom.History.CUMULATIVE_TRIP_UNASSIGNED_TIME]
                 [lower_bound] + self.sim.stats[
                     atom.History.CUMULATIVE_TRIP_AWAITING_TIME][block] -
                 self.sim.stats[atom.History.CUMULATIVE_TRIP_AWAITING_TIME]
                 [lower_bound]) / window_total_trip_time)
            self.stats[PlotArray.TRIP_COUNT][block] = (window_request_count /
                                                       (block - lower_bound))
            self.stats[PlotArray.TRIP_COMPLETED_FRACTION][block] = (
                window_completed_trip_count / window_request_count)
        logging.debug(
            (f"animation: window_req_c={window_request_count}"
             f", w_completed_trips={window_completed_trip_count}"
             f", trip_length="
             f"{self.stats[PlotArray.TRIP_MEAN_DISTANCE][block]:.02f}"
             f", wait_time="
             f"{self.stats[PlotArray.TRIP_MEAN_WAIT_TIME][block]:.02f}"
             f", wait_fraction="
             f"{self.stats[PlotArray.TRIP_WAIT_FRACTION][block]:.02f}"))

    def _plot_map(self, i, ax):
        """
        Draw the map, with drivers and trips
        """
        ax.clear()
        ax.set_title((
            f"{self.sim.city.city_size} blocks, "
            f"{len(self.sim.drivers)} drivers, "
            f"{self.sim.request_rate:.02f} requests/block, "
            f"{self.sim.city.trip_distribution.name.lower()} trip distribution"
        ))
        # Get the animation interpolation point
        distance_increment = (self._interpolation(i) /
                              self.interpolation_points)
        roadwidth = 60.0 / self.sim.city.city_size
        # Animate the drivers: one set of arrays for each direction
        # as each direction has a common marker
        x_dict = {}
        y_dict = {}
        color = {}
        size = {}
        markers = ('^', '>', 'v', '<')
        # driver markers:
        sizes = (20 * roadwidth, 30 * roadwidth, 30 * roadwidth)
        for direction in list(atom.Direction):
            x_dict[direction.name] = []
            y_dict[direction.name] = []
            color[direction.name] = []
            size[direction.name] = []
        locations = [x_dict, y_dict]

        for driver in self.sim.drivers:
            for i in [0, 1]:
                # Position, including edge correction
                x = driver.location[i]
                if (driver.phase != atom.DriverPhase.AVAILABLE
                        or self.sim.available_drivers_moving):
                    x += distance_increment * driver.direction.value[i]
                x = ((x + self.display_fringe) % self.sim.city.city_size -
                     self.display_fringe)
                # Make the displayed-position fit on the map, with
                # fringe display_fringe around the edges
                locations[i][driver.direction.name].append(x)
            size[driver.direction.name].append(sizes[driver.phase.value])
            color[driver.direction.name].append(
                self.color_palette[driver.phase.value])
        for i, direction in enumerate(list(atom.Direction)):
            ax.scatter(locations[0][direction.name],
                       locations[1][direction.name],
                       s=size[direction.name],
                       marker=markers[i],
                       color=color[direction.name],
                       alpha=0.7)

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
                   alpha=0.7,
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
                if this_property.name.startswith("DRIVER"):
                    linestyle = "solid"
                    if this_property == PlotArray.DRIVER_UTILITY:
                        linewidth = 1
                    else:
                        linewidth = 2
                elif this_property.name.startswith("TRIP"):
                    linestyle = "dashed"
                    linewidth = 2
                if this_property in (PlotArray.TRIP_REQUEST_RATE,
                                     PlotArray.DRIVER_COUNT_SCALED):
                    ymax = np.max(self.stats[this_property][lower_bound:block])
                    y_array = (np.true_divide(
                        self.stats[this_property][lower_bound:block], ymax))
                    linestyle = "dotted"
                    linewidth = 3
                    ax.plot(x_range,
                            y_array,
                            color=self.color_palette[index],
                            label=this_property.value,
                            lw=linewidth,
                            ls=linestyle,
                            alpha=0.7)
                else:
                    ax.plot(x_range,
                            self.stats[this_property][lower_bound:block],
                            color=self.color_palette[index],
                            label=this_property.value,
                            lw=linewidth,
                            ls=linestyle,
                            alpha=0.7)
            if self.sim.equilibrate == atom.Equilibration.NONE and fractional:
                ymin = 0
                ymax = 1
                caption = (f"{self.sim.city.city_size} block city\n"
                           f"{len(self.sim.drivers)} drivers\n"
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
                    f"with {self.sim.request_rate:.01f} requests/block.\n"
                    f"{len(self.sim.drivers)} drivers\n"
                    f"{self.sim.equilibrate.value.capitalize()} equilibration "
                    f"with reserved wage={self.sim.reserved_wage:.02f}.\n"
                    f"{self.sim.city.trip_distribution.name.capitalize()} "
                    "trip distribution\n"
                    f"{self.sim.time_blocks}-block simulation")
            elif (self.sim.equilibrate == atom.Equilibration.PRICE
                  and fractional):
                ymin = -0.25
                ymax = 1.1
                caption = (f"{self.sim.city.city_size}-block city, "
                           f"price={self.sim.price:.01f}, "
                           f"commission={self.sim.platform_commission:.01f}, "
                           f"{self.sim.request_rate:.01f} requests/block, "
                           f"{len(self.sim.drivers)} drivers, "
                           f"{self.sim.city.trip_distribution.name.lower()} "
                           "trip distribution\n"
                           f"{self.sim.equilibrate.value.capitalize()}"
                           " equilibration, "
                           f"base demand={self.sim.base_demand:.01f}, "
                           f"reserved wage={self.sim.reserved_wage:.02f}.\n"
                           f"{self.sim.time_blocks}-block simulation")
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
            ax.set_xlabel("Time / 'hours'")
            xlocs = [x for x in x_range if x % 30 == 0]
            xlabels = [f"{x / 60.0:.01f}" for x in x_range if x % 30 == 0]
            ax.set_xticks(xlocs)
            ax.set_xticklabels(xlabels)
            ax.set_ylim(bottom=ymin, top=ymax)
            ylocs = [y / 10 for y in range(int(ymin * 10), int(ymax * 10))]
            ax.set_yticks(ylocs)
            # Draw the x axis as a thicker line
            ax.axhline(y=0, linewidth=3, color="white", zorder=-1)
            # for _, s in ax.spines.items():
            # s.set_linewidth = 5
            ax.legend()

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
            logging.debug(f"Writing output to {output_file}...")
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
