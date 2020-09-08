#!/usr/bin/python3
import logging
from enum import Enum
from datetime import datetime
import matplotlib as mpl
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from matplotlib.animation import FuncAnimation
from matplotlib.animation import ImageMagickFileWriter, FFMpegFileWriter
import seaborn as sns
from ridehail.atom import (Equilibration, TripDistribution, History, Direction,
                           DriverPhase, TripPhase)

logger = logging.getLogger(__name__)

FRAME_INTERVAL = 50
# Placeholder frame count for animation.
FRAME_COUNT_UPPER_LIMIT = 10000000
CHART_X_RANGE = 200
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
# mpl.rcParams['font.size'] = 12
# mpl.rcParams['legend.fontsize'] = 'large'
# mpl.rcParams['figure.titlesize'] = 'medium'
sns.set()
sns.set_style("darkgrid")
sns.set_palette("muted")
# sns.set_context("talk")

DISPLAY_FRINGE = 0.25


class TrailingStat(Enum):
    DRIVER_AVAILABLE_FRACTION = "Available fraction"
    DRIVER_PICKUP_FRACTION = "Picking up fraction"
    DRIVER_PAID_FRACTION = "Paid fraction"
    DRIVER_MEAN_COUNT = "Mean driver count"
    DRIVER_UTILITY = "Driver utility"
    TRIP_MEAN_WAIT_TIME = "Mean wait time"
    TRIP_MEAN_LENGTH = "Mean trip distance"
    TRIP_WAIT_FRACTION = "Wait fraction"
    TRIP_LENGTH_FRACTION = "Trip length fraction"
    TRIP_COUNT = "Trips completed"
    TRIP_COMPLETED_FRACTION = "Trip completed fraction"


class Draw(Enum):
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
    def __init__(self, simulation):
        self.sim = simulation
        self.draw = simulation.config.draw
        self.output = simulation.output
        self.frame_index = 0
        self.last_block_frame_index = 0
        self.display_fringe = DISPLAY_FRINGE
        self.color_palette = sns.color_palette()
        self.interpolation_points = self.sim.config.interpolate
        self.draw_update_period = self.sim.config.draw_update_period
        self.pause_plot = False  # toggle for pausing
        self.axes = []

    def animate(self):
        """
        Do the simulation but with displays
        """
        plot_size = 8
        if self.draw in (Draw.DRIVER, Draw.STATS, Draw.TRIP, Draw.MAP):
            ncols = 1
        elif self.draw in (Draw.ALL, ):
            ncols = 2
        elif self.draw in (Draw.EQUILIBRATION, ):
            ncols = 3
        fig, self.axes = plt.subplots(ncols=ncols,
                                      figsize=(ncols * plot_size, plot_size))
        fig.canvas.mpl_connect('button_press_event', self.on_click)
        fig.canvas.mpl_connect('key_press_event', self.on_key_press)
        if ncols == 1:
            self.axes = [self.axes]
        # Position the display window on the screen
        thismanager = plt.get_current_fig_manager()
        thismanager.window.wm_geometry("+10+10")
        self.animation = FuncAnimation(
            fig,
            self._next_frame,
            frames=(FRAME_COUNT_UPPER_LIMIT),
            # fargs=[axes],
            interval=FRAME_INTERVAL,
            repeat=False,
            repeat_delay=3000)
        self.output_animation(self.animation, plt, self.sim.config.output)
        fig.savefig(f"./img/{self.sim.config_file_root}"
                    f"-{datetime.now().strftime('%Y-%m-%d-%H-%M')}.png")

    def on_click(self, event):
        self.pause_plot ^= True

    def on_key_press(self, event):
        """
        Respond to a + or - key press
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
                min(int(self.sim.target_state["base_demand"] * 0.9),
                    (self.sim.target_state["base_demand"] - 0.1)), 0)
        elif event.key == "p":
            self.sim.target_state["price"] = max(
                self.sim.target_state["price"] * 0.9, 0.1)
        elif event.key == "P":
            self.sim.target_state[
                "price"] = self.sim.target_state["price"] * 1.1
        elif event.key == "u":
            self.sim.target_state["reserved_wage"] = max(
                self.sim.target_state["reserved_wage"] - 0.01, 0.1)
        elif event.key == "U":
            self.sim.target_state["reserved_wage"] = min(
                self.sim.target_state["reserved_wage"] + 0.01, 1.0)
        elif event.key == "v":
            self.interpolation_points = max(self.interpolation_points + 1, 1)
        elif event.key == "V":
            self.interpolation_points = max(self.interpolation_points - 1, 1)
        # elif event.key == "P":
        # if self.draw in (Draw.STATS, Draw.MAP):
        # self.draw = Draw.ALL
        # self.axes = self.axes[0]
        # elif event.key == "p":
        # if self.draw == Draw.ALL:
        # self.draw = Draw.STATS
        # self.axes = self.axes[1]
        # elif self.draw == Draw.STATS:
        # self.draw = Draw.MAP
        # self.axes = self.axes[0]
        elif event.key == "c":
            self.sim.target_state["city_size"] = max(
                self.sim.target_state["city_size"] - 1, 2)
        elif event.key == "C":
            self.sim.target_state["city_size"] = max(
                self.sim.target_state["city_size"] + 1, 2)
        elif event.key == "ctrl+t":
            if self.sim.target_state[
                    "trip_distribution"] == TripDistribution.UNIFORM:
                self.sim.target_state[
                    "trip_distribution"] = TripDistribution.BETA
            elif self.sim.target_state[
                    "trip_distribution"] == TripDistribution.BETA:
                self.sim.target_state[
                    "trip_distribution"] = TripDistribution.UNIFORM
        elif event.key in ("escape", " "):
            self.pause_plot ^= True
        # else:
        # print(f"event.key='{event.key}'")

    def _next_frame(self, ii):
        """
        Function called from animator to generate frame ii of the animation.

        Ignore ii and handle the frame counter myself through self.frame_index
        to handle pauses. Not helping much yet though
        """
        i = self.frame_index
        if not self.pause_plot:
            self.frame_index += 1
        if self.sim.block_index >= self.sim.time_blocks:
            logger.info(f"Period {self.sim.block_index}: animation completed")
            self.animation.event_source.stop()
        plotstat_list = []
        if self._interpolation(i) == 0:
            # A "real" time point. Update the system
            # If the plotting is paused, don't compute the next block,
            # just redisplay what we have.
            if not self.pause_plot:
                self.sim.next_block()
        axis_index = 0
        if self.draw in (Draw.ALL, Draw.MAP):
            self._plot_map(i, self.axes[axis_index])
            axis_index += 1
        if self.sim.block_index % self.draw_update_period != 0:
            return
        if self.draw in (Draw.ALL, Draw.STATS, Draw.DRIVER, Draw.TRIP):
            plotstat_list = []
            if self.sim.equilibrate == Equilibration.NONE:
                if self.draw in (Draw.ALL, Draw.STATS, Draw.DRIVER):
                    plotstat_list.append(
                        TrailingStat.DRIVER_AVAILABLE_FRACTION)
                    plotstat_list.append(TrailingStat.DRIVER_PICKUP_FRACTION)
                    plotstat_list.append(TrailingStat.DRIVER_PAID_FRACTION)
                if self.draw in (Draw.ALL, Draw.STATS, Draw.TRIP):
                    plotstat_list.append(TrailingStat.TRIP_WAIT_FRACTION)
                    plotstat_list.append(TrailingStat.TRIP_LENGTH_FRACTION)
                    plotstat_list.append(TrailingStat.TRIP_COMPLETED_FRACTION)
            else:
                plotstat_list.append(TrailingStat.DRIVER_AVAILABLE_FRACTION)
                plotstat_list.append(TrailingStat.TRIP_WAIT_FRACTION)
                plotstat_list.append(TrailingStat.DRIVER_PAID_FRACTION)
                plotstat_list.append(TrailingStat.TRIP_COMPLETED_FRACTION)
                plotstat_list.append(TrailingStat.TRIP_LENGTH_FRACTION)
                if self.sim.equilibrate in (Equilibration.PRICE,
                                            Equilibration.SUPPLY):
                    plotstat_list.append(TrailingStat.DRIVER_UTILITY)

            self._plot_fractional_stats(i, self.axes[axis_index],
                                        plotstat_list)
            axis_index += 1
        if self.draw in (Draw.EQUILIBRATION, ):
            # This plot type is probably obsolete, but I'm leaving it in for
            # now
            self._draw_equilibration_plot(i,
                                          self.axes[axis_index],
                                          History.DRIVER_COUNT,
                                          History.REQUEST_RATE,
                                          xlim=[0],
                                          ylim=[0])
        # TODO: set an axis that holds the actual button. THis makes all
        # axes[0] into a big button
        # button_plus = Button(axes[0], '+')
        # button_plus.on_clicked(self.on_click)

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
        # Plot the drivers: one set of arrays for each direction
        # as each direction has a common marker
        x_dict = {}
        y_dict = {}
        color = {}
        size = {}
        markers = ('^', '>', 'v', '<')
        # driver markers:
        sizes = (60, 100, 100)
        for direction in list(Direction):
            x_dict[direction.name] = []
            y_dict[direction.name] = []
            color[direction.name] = []
            size[direction.name] = []
        locations = [x_dict, y_dict]

        for driver in self.sim.drivers:
            for i in [0, 1]:
                # Position, including edge correction
                x = driver.location[i]
                if (driver.phase != DriverPhase.AVAILABLE
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
        for i, direction in enumerate(list(Direction)):
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
            if trip.phase in (TripPhase.UNASSIGNED, TripPhase.WAITING):
                x_origin.append(trip.origin[0])
                y_origin.append(trip.origin[1])
            if trip.phase == TripPhase.RIDING:
                x_destination.append(trip.destination[0])
                y_destination.append(trip.destination[1])
        ax.scatter(x_origin,
                   y_origin,
                   s=80,
                   marker='o',
                   color=self.color_palette[3],
                   alpha=0.7,
                   label="Ride request")
        ax.scatter(x_destination,
                   y_destination,
                   s=120,
                   marker='*',
                   color=self.color_palette[4],
                   label="Ride destination")

        # Draw the map: the second term is a bit of wrapping
        # so that the outside road is shown properly
        ax.set_xlim(-self.display_fringe,
                    self.sim.city.city_size - self.display_fringe)
        ax.set_ylim(-self.display_fringe,
                    self.sim.city.city_size - self.display_fringe)
        ax.xaxis.set_major_locator(MultipleLocator(1))
        ax.yaxis.set_major_locator(MultipleLocator(1))
        ax.grid(True, which="major", axis="both", lw=roadwidth)
        ax.set_xticklabels([])
        ax.set_yticklabels([])

    def _plot_fractional_stats(self,
                               i,
                               ax,
                               plotstat_list,
                               draw_line_chart=True):
        """
        For a list of TrailingStats arrays that describe fractional properties,
        draw them on a plot with vertical axis [0,1]
        """
        if self._interpolation(i) == 0:
            ax.clear()
            block = self.sim.block_index
            lower_bound = max((block - CHART_X_RANGE), 0)
            x_range = list(range(lower_bound, block))
            title = ((f"Simulation {self.sim.config_file_root}.config on "
                      f"{datetime.now().strftime('%Y-%m-%d %H:%M')}"))
            ax.set_title(title)
            for index, fractional_property in enumerate(plotstat_list):
                ax.plot(x_range,
                        self.sim.stats[fractional_property][lower_bound:block],
                        color=self.color_palette[index],
                        label=fractional_property.value,
                        lw=3,
                        alpha=0.7)
            if self.sim.equilibrate == Equilibration.NONE:
                ax.set_ylim(bottom=0, top=1)
                caption = (f"{self.sim.city.city_size} block city\n"
                           f"{len(self.sim.drivers)} drivers\n"
                           f"{self.sim.request_rate:.02f} requests / block\n"
                           f"{self.sim.city.trip_distribution.name.lower()} "
                           "trip distribution\n"
                           f"{self.sim.time_blocks}-block simulation")
            elif self.sim.equilibrate == Equilibration.SUPPLY:
                ax.set_ylim(bottom=-0.25, top=1)
                caption = (
                    f"A {self.sim.city.city_size}-block city "
                    f"with {self.sim.request_rate:.01f} requests/block.\n"
                    f"{len(self.sim.drivers)} drivers\n"
                    f"{self.sim.equilibrate.value.capitalize()} equilibration "
                    f"with reserved wage={self.sim.reserved_wage:.02f}.\n"
                    f"{self.sim.city.trip_distribution.name.capitalize()} "
                    "trip distribution\n"
                    f"{self.sim.time_blocks}-block simulation")
            elif self.sim.equilibrate == Equilibration.PRICE:
                ax.set_ylim(bottom=-0.25, top=1)
                caption = (f"{self.sim.city.city_size}-block city, "
                           f"price={self.sim.price:.01f}, "
                           f"{self.sim.request_rate:.01f} requests/block, "
                           f"{len(self.sim.drivers)} drivers, "
                           f"{self.sim.city.trip_distribution.name.lower()} "
                           "trip distribution\n"
                           f"{self.sim.equilibrate.value.capitalize()}"
                           " equilibration, "
                           f"base demand={self.sim.base_demand:.0f}, "
                           f"reserved wage={self.sim.reserved_wage:.02f}.\n"
                           f"{self.sim.time_blocks}-block simulation")
            ax.text(0.05,
                    0.05,
                    caption,
                    bbox={
                        'facecolor': 'lavender',
                        'edgecolor': 'silver',
                        'pad': 10,
                    },
                    verticalalignment="bottom",
                    horizontalalignment="left",
                    transform=ax.transAxes,
                    fontsize=10,
                    linespacing=2.0)
            ax.set_xlabel("Time (blocks)")
            ax.set_ylabel("Fractional property values")
            # Draw the x axis as a thicker line
            ax.axhline(y=0, linewidth=3, color="white", zorder=-1)
            # for _, s in ax.spines.items():
            # s.set_linewidth = 5
            ax.legend()

    def _draw_equilibration_plot(self,
                                 i,
                                 ax,
                                 plotstat_x,
                                 plotstat_y,
                                 xlim=None,
                                 ylim=None):
        """
        Plot wait time against busy fraction, to watch equilibration
        """
        if self._interpolation(i) == 0:
            x = self.stats[plotstat_x]
            y = self.stats[plotstat_y]
            # TODO: This is wrong when interpolation_points changes
            block = int(i / self.interpolation_points)
            most_recent_equilibration = max(
                1,
                self.equilibration_interval *
                int(block / self.equilibration_interval))
            ax.clear()
            ax.set_title(f"Block {block}: {len(self.sim.drivers)} drivers, "
                         f"{self.request_rate:.02f} requests per block")
            ax.plot(x[:most_recent_equilibration],
                    y[:most_recent_equilibration],
                    lw=3,
                    color=self.color_palette[1],
                    alpha=0.2)
            ax.plot(x[most_recent_equilibration - 1:],
                    y[most_recent_equilibration - 1:],
                    lw=3,
                    color=self.color_palette[1],
                    alpha=0.6)
            ax.plot(x[block],
                    y[block],
                    marker='o',
                    markersize=10,
                    color=self.color_palette[2],
                    alpha=0.9)
            if xlim:
                ax.set_xlim(left=min(xlim))
                if len(xlim) > 1:
                    ax.set_xlim(right=max(xlim))
            if ylim:
                ax.set_ylim(bottom=min(ylim))
                if len(ylim) > 1:
                    ax.set_ylim(top=max(ylim))
            ax.set_xlabel(f"{plotstat_x.value}")
            ax.set_ylabel(f"{plotstat_y.value}")

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

    def output_animation(self, anim, plt, output):
        """
        Generic output functions
        """
        if output is not None:
            logger.debug(f"Writing output to {output}...")
        if output.endswith("mp4"):
            writer = FFMpegFileWriter(fps=10, bitrate=1800)
            anim.save(output, writer=writer)
            del anim
        elif output.endswith("gif"):
            writer = ImageMagickFileWriter()
            anim.save(output, writer=writer)
            del anim
        else:
            plt.show()
            del anim
            plt.close()
