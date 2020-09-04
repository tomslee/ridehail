#!/usr/bin/python3
"""
Control a sequence of simulations
"""
import logging
import copy
import os
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
from matplotlib.offsetbox import AnchoredText
import seaborn as sns
from scipy.optimize import curve_fit
from ridehail.atom import Equilibration
from ridehail.simulation import RideHailSimulation
from ridehail.animation import PlotStat, Draw
from datetime import datetime

logger = logging.getLogger(__name__)


class RideHailSimulationSequence():
    """
    A sequence of simulations
    """
    def __init__(self, config):
        """
        Initialize sequence properties
        """
        self.config = config
        precision = 10
        if self.config.equilibrate != Equilibration.NONE:
            if self.config.driver_cost_increment is None:
                self.driver_costs = [self.config.driver_cost]
            else:
                self.driver_costs = [
                    x / precision for x in range(
                        int(self.config.driver_cost * precision),
                        int(self.config.driver_cost_max * precision + 1),
                        int(self.config.driver_cost_increment * precision))
                ]
            if self.config.wait_cost_increment is None:
                self.wait_costs = [self.config.wait_cost]
            else:
                self.wait_costs = [
                    int(self.config.wait_cost_max * precision + 1),
                    int(self.config.wait_cost_increment * precision)
                ]
        else:
            self.driver_costs = [0]
            self.wait_costs = [0]
        self.driver_counts = [
            x for x in
            range(self.config.driver_count, self.config.driver_count_max +
                  1, self.config.driver_count_increment)
        ]
        logger.info(f"Driver counts: {self.driver_counts}")
        if len(self.driver_counts) == 0:
            self.driver_counts = [self.config.driver_count]
        self.request_rates = [
            x / precision
            for x in range(int(self.config.request_rate * precision),
                           int(self.config.request_rate_max * precision) + 1,
                           int(self.config.request_rate_increment * precision))
        ]
        logger.info(f"Request rates: {self.request_rates}")
        if len(self.request_rates) == 0:
            self.request_rates = [self.config.request_rate]
        if len(self.request_rates) > 1 and len(self.driver_counts) > 1:
            logger.error(
                "Limitation: cannot run a sequence incrementing "
                "both driver counts and request rates.\n"
                "Please set either request_rate_max or driver_count_max "
                "to less than or equal to request_rate or driver_count.")
            exit(-1)
        self.trip_wait_fraction = []
        self.driver_paid_fraction = []
        self.driver_unpaid_fraction = []
        self.driver_available_fraction = []
        self.driver_pickup_fraction = []
        self.frame_count = (len(self.driver_counts) * len(self.request_rates) *
                            self.config.request_rate_repeat)
        # self.plot_count = len(set(self.request_rates))
        self.plot_count = 1
        self.color_palette = sns.color_palette()

    def run_sequence(self):
        """
        Do the run
        """
        if self.config.draw == Draw.NONE:
            # if os.path.exists(self.config["config_file"]):
            # Iterate over equilibration models for driver counts
            for driver_cost in self.driver_costs:
                for wait_cost in self.wait_costs:
                    for request_rate in self.request_rates:
                        for driver_count in self.driver_counts:
                            self._next_sim(driver_cost=driver_cost,
                                           wait_cost=wait_cost,
                                           request_rate=request_rate,
                                           driver_count=driver_count)
        else:
            plot_size = 10
            fig, axes = plt.subplots(ncols=self.plot_count,
                                     figsize=(self.plot_count * plot_size,
                                              plot_size))
            axes = [axes] if self.plot_count == 1 else axes
            # Position the display window on the screen
            thismanager = plt.get_current_fig_manager()
            thismanager.window.wm_geometry("+10+10")
            # animation = FuncAnimation(fig,
            animation = FuncAnimation(fig,
                                      self._next_frame,
                                      frames=self.frame_count,
                                      fargs=[axes],
                                      repeat=False,
                                      repeat_delay=3000)
            self.output_animation(animation, plt, self.config.output)
            fig.savefig(
                f"ridehail-{datetime.now().strftime('%Y-%m-%d-%H-%M')}.png")
        logger.info("Sequence completed")

    def _collect_sim_results(self, results):
        """
        After a simulation, collect the results for plotting etc
        """
        self.driver_available_fraction.append(
            results.output["driver_fraction_available"])
        self.driver_pickup_fraction.append(
            results.output["driver_fraction_picking_up"])
        self.driver_unpaid_fraction.append(
            results.output["driver_fraction_available"] +
            results.output["driver_fraction_picking_up"])
        self.driver_paid_fraction.append(
            results.output["driver_fraction_with_rider"])
        self.trip_wait_fraction.append(
            results.sim.stats[PlotStat.TRIP_WAIT_FRACTION][-1])

    def _next_sim(self,
                  index=None,
                  driver_cost=None,
                  wait_cost=None,
                  request_rate=None,
                  driver_count=None):
        """
        Run a single simulation
        """
        if request_rate is None:
            request_rate_index = int(index / len(self.driver_counts))
            request_rate = self.request_rates[request_rate_index]
        if driver_count is None:
            driver_count_index = index % len(self.driver_counts)
            driver_count = self.driver_counts[driver_count_index]
        if driver_cost is None:
            driver_cost_index = index % len(self.driver_costs)
            driver_cost = self.driver_costs[driver_cost_index]
        if wait_cost is None:
            wait_cost_index = index % len(self.wait_costs)
            wait_cost = self.wait_costs[wait_cost_index]
        # Set configuration parameters
        # For now, say we can't draw simulation-level plots
        # if we are running a sequence
        runconfig = copy.deepcopy(self.config)
        runconfig.draw = Draw.NONE
        runconfig.driver_cost = driver_cost
        runconfig.wait_cost = wait_cost
        runconfig.request_rate = request_rate
        runconfig.driver_count = driver_count
        simulation = RideHailSimulation(runconfig)
        results = simulation.simulate()
        results.write_json(self.config.jsonl)
        self._collect_sim_results(results)
        logger.info(("Simulation completed"
                     f", request_rate={request_rate}"
                     f", driver_count={driver_count}"
                     f", p1 fraction={self.driver_available_fraction[-1]:.02f}"
                     f", p2 fraction={self.driver_pickup_fraction[-1]:.02f}"
                     f", p3 fraction={self.driver_paid_fraction[-1]:.02f}"))

    def _plot_with_fit(self, ax, i, palette_index, x, y, x_fit, y_fit, x_plot,
                       label, fit_function):
        """
        plot a scatter plot, then a best fit line
        """
        if len(x) > 0:
            ax.plot(x[:i + 1],
                    y[:i + 1],
                    lw=0,
                    marker="o",
                    markersize=6,
                    color=self.color_palette[palette_index],
                    alpha=0.6,
                    label=label)
        try:
            if x_fit and y_fit:
                # a + b / (x+c)
                p0_a = y_fit[-1]
                p0_b = y_fit[0] * x_fit[0]
                p0_c = 0
                p0 = (p0_a, p0_b, p0_c)
                popt, _ = curve_fit(fit_function,
                                    x_fit,
                                    y_fit,
                                    p0=p0,
                                    maxfev=2000)
                y_plot = [fit_function(xval, *popt) for xval in x_plot]
                ax.plot(x_plot,
                        y_plot,
                        lw=2,
                        alpha=0.8,
                        color=self.color_palette[palette_index])
        except (RuntimeError, TypeError) as e:
            logger.error(e)

    def _next_frame(self, i, axes):
        """
        Function called from sequence animator to generate frame i
        of the animation.
        self.driver_count and other sequence variables
        hold a value for each simulation
        """
        self._next_sim(i)
        ax = axes[0]
        ax.clear()
        j = i + 1
        if len(self.driver_counts) > 1:
            x = self.driver_counts[:j]
            fit_function = self._fit_driver_count
        elif len(self.request_rates) > 1:
            x = self.request_rates[:j]
            fit_function = self._fit_request_rate
        z = zip(x, self.driver_available_fraction[:j],
                self.driver_pickup_fraction[:j], self.driver_paid_fraction[:j],
                self.trip_wait_fraction[:j], self.driver_unpaid_fraction[:j])
        # Only fit for states where drivers have some available time
        z_fit = [zval for zval in z if zval[1] > 0.05]
        if len(z_fit) > 0:
            (x_fit, available_fit, pickup_fit, paid_fit, wait_fit,
             unpaid_fit) = zip(*z_fit)
            x_plot = [x_val for x_val in x if x_val in x_fit]
        else:
            x_fit = None
            available_fit = None
            pickup_fit = None
            paid_fit = None
            wait_fit = None
            unpaid_fit = None
            x_plot = None
        palette_index = 0

        self._plot_with_fit(ax,
                            i,
                            palette_index=palette_index,
                            x=x,
                            y=self.driver_available_fraction,
                            x_fit=x_fit,
                            y_fit=available_fit,
                            x_plot=x_plot,
                            label=PlotStat.DRIVER_AVAILABLE_FRACTION.value,
                            fit_function=fit_function)
        palette_index += 1
        self._plot_with_fit(ax,
                            i,
                            palette_index=palette_index,
                            x=x,
                            y=self.driver_pickup_fraction,
                            x_fit=x_fit,
                            y_fit=pickup_fit,
                            x_plot=x_plot,
                            label=PlotStat.DRIVER_PICKUP_FRACTION.value,
                            fit_function=fit_function)
        palette_index += 1
        self._plot_with_fit(ax,
                            i,
                            palette_index=palette_index,
                            x=x,
                            y=self.driver_paid_fraction,
                            x_fit=x_fit,
                            y_fit=paid_fit,
                            x_plot=x_plot,
                            label=PlotStat.DRIVER_PAID_FRACTION.value,
                            fit_function=fit_function)
        palette_index += 1
        self._plot_with_fit(ax,
                            i,
                            palette_index=palette_index,
                            x=x,
                            y=self.trip_wait_fraction,
                            x_fit=x_fit,
                            y_fit=wait_fit,
                            x_plot=x_plot,
                            label=PlotStat.TRIP_WAIT_FRACTION.value,
                            fit_function=fit_function)
        palette_index += 1
        self._plot_with_fit(ax,
                            i,
                            palette_index=palette_index,
                            x=x,
                            y=self.driver_unpaid_fraction,
                            x_fit=x_fit,
                            y_fit=unpaid_fit,
                            x_plot=x_plot,
                            label="Unpaid fraction",
                            fit_function=fit_function)
        ax.set_ylim(bottom=0, top=1)
        if len(self.request_rates) == 1:
            ax.set_xlabel("Drivers")
            ax.set_xlim(left=min(self.driver_counts),
                        right=max(self.driver_counts))
            caption_supply_or_demand = (
                f"Fixed demand={self.request_rates[0]} requests per block\n")
            # caption_x_location = 0.05
            # caption_y_location = 0.05
            caption_location = "upper right"
        elif len(self.driver_counts) == 1:
            ax.set_xlabel("Request rates")
            ax.set_xlim(left=min(self.request_rates),
                        right=max(self.request_rates))
            caption_supply_or_demand = (
                f"Fixed supply={self.driver_counts[0]} drivers\n")
            # caption_x_location = 0.05
            # caption_y_location = 0.4
            caption_location = "lower right"
        ax.set_ylabel("Fractional values")
        caption = (
            f"City size={self.config.city_size} blocks\n"
            f"{caption_supply_or_demand}"
            f"Trip distribution={self.config.trip_distribution.name.lower()}\n"
            f"Minimum trip length={self.config.min_trip_distance} blocks\n"
            f"Idle drivers moving={self.config.available_drivers_moving}\n"
            f"Simulations of {self.config.time_blocks} blocks.")
        anchor_props = {
            'backgroundcolor': 'whitesmoke',
        }
        anchored_text = AnchoredText(caption,
                                     loc=caption_location,
                                     frameon=False,
                                     prop=anchor_props)
        ax.add_artist(anchored_text)
        # ax.text(caption_x_location,
        # caption_y_location,
        # caption,
        # bbox={
        # 'facecolor': 'whitesmoke',
        # 'edgecolor': 'grey',
        # 'pad': 10,
        # },
        # verticalalignment="bottom",
        # transform=ax.transAxes,
        # fontsize=11,
        # alpha=0.8)
        ax.set_title(f"Ridehail simulation sequence, "
                     f"{datetime.now().strftime('%Y-%m-%d')}")
        ax.legend(loc="center right")

    def _fit_driver_count(self, x, a, b, c):
        return (a + b / (x + c))

    def _fit_request_rate(self, x, a, b, c):
        return (a + b * x + c * x * x)

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
