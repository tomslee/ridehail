#!/usr/bin/python3
"""
Control a sequence of simulations
"""
import logging
import copy
import os
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import seaborn as sns
from scipy.optimize import curve_fit
from ridehail.plot import Plot, PlotStat, Draw
from ridehail.simulation import RideHailSimulation, Equilibration
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
        self.request_rates = [
            x / precision
            for x in range(int(self.config.request_rate * precision),
                           int(self.config.request_rate_max * precision) + 1,
                           int(self.config.request_rate_increment * precision))
        ]
        logger.info(self.request_rates)
        if len(self.request_rates) == 0:
            self.request_rates = [self.config.request_rate]
        self.trip_wait_fraction = []
        self.driver_paid_fraction = []
        self.driver_unpaid_fraction = []
        self.driver_available_fraction = []
        self.driver_pickup_fraction = []
        self.frame_count = (len(self.driver_counts) * len(self.request_rates) *
                            self.config.request_rate_repeat)
        self.plot_count = len(set(self.request_rates))
        self.color_palette = sns.color_palette()

    def run_sequence(self):
        """
        Do the run
        """
        if self.config.draw == Draw.NONE:
            # if os.path.exists(self.config["config_file"]):
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
            animation = FuncAnimation(fig,
                                      self._next_frame,
                                      frames=self.frame_count,
                                      fargs=[axes],
                                      repeat=False,
                                      repeat_delay=3000)
            Plot().output(animation, plt, self.__class__.__name__,
                          self.config.output)
            fig.savefig(
                f"ridehail-{datetime.now().strftime('%Y-%m-%d-%H-%M')}.png")
        logger.info("Sequence completed")

    def _collect_sim_results(self, driver_cost, wait_cost, request_rate,
                             driver_count, results):
        """
        After a simulation, collect the results for plotting etc
        """
        self.driver_available_fraction.append(
            results.sim.stats[PlotStat.DRIVER_AVAILABLE_FRACTION][-1])
        self.driver_pickup_fraction.append(
            results.sim.stats[PlotStat.DRIVER_PICKUP_FRACTION][-1])
        self.driver_unpaid_fraction.append(
            (results.sim.stats[PlotStat.DRIVER_AVAILABLE_FRACTION][-1] +
             results.sim.stats[PlotStat.DRIVER_PICKUP_FRACTION][-1]))
        self.driver_paid_fraction.append(
            results.sim.stats[PlotStat.DRIVER_PAID_FRACTION][-1])
        self.trip_wait_fraction.append(
            results.sim.stats[PlotStat.TRIP_WAIT_FRACTION][-1])
        logger.info(("Simulation completed"
                     f", request_rate={request_rate}"
                     f", driver_count={driver_count}"
                     f", p3 fraction={self.driver_available_fraction[-1]:.02f}"
                     f", p2 fraction={self.driver_pickup_fraction[-1]:.02f}"
                     f", p1 fraction={self.driver_paid_fraction[-1]:.02f}"))

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
        self._collect_sim_results(driver_cost, wait_cost, request_rate,
                                  driver_count, results)

    def _plot_with_fit(self, ax, i, palette_index, x, y, x_fit, y_fit, x_plot,
                       label):
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
                popt, _ = curve_fit(self._fit,
                                    x_fit,
                                    y_fit,
                                    p0=p0,
                                    maxfev=2000)
                y_plot = [self._fit(xval, *popt) for xval in x_plot]
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
        x = self.driver_counts[:j]
        z = zip(self.driver_counts[:j], self.driver_available_fraction[:j],
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
                            label=PlotStat.DRIVER_AVAILABLE_FRACTION.value)
        palette_index += 1
        self._plot_with_fit(ax,
                            i,
                            palette_index=palette_index,
                            x=x,
                            y=self.driver_pickup_fraction,
                            x_fit=x_fit,
                            y_fit=pickup_fit,
                            x_plot=x_plot,
                            label=PlotStat.DRIVER_PICKUP_FRACTION.value)
        palette_index += 1
        self._plot_with_fit(ax,
                            i,
                            palette_index=palette_index,
                            x=x,
                            y=self.driver_paid_fraction,
                            x_fit=x_fit,
                            y_fit=paid_fit,
                            x_plot=x_plot,
                            label=PlotStat.DRIVER_PAID_FRACTION.value)
        palette_index += 1
        self._plot_with_fit(ax,
                            i,
                            palette_index=palette_index,
                            x=x,
                            y=self.trip_wait_fraction,
                            x_fit=x_fit,
                            y_fit=wait_fit,
                            x_plot=x_plot,
                            label=PlotStat.TRIP_WAIT_FRACTION.value)
        palette_index += 1
        self._plot_with_fit(ax,
                            i,
                            palette_index=palette_index,
                            x=x,
                            y=self.driver_unpaid_fraction,
                            x_fit=x_fit,
                            y_fit=unpaid_fit,
                            x_plot=x_plot,
                            label="Unpaid fraction")
        ax.set_xlim(left=min(self.driver_counts),
                    right=max(self.driver_counts))
        ax.set_ylim(bottom=0, top=1)
        ax.set_xlabel("Drivers")
        ax.set_ylabel("Fractional values")
        caption = (
            f"City size={self.config.city_size} blocks\n"
            f"Demand={self.request_rates[0]} requests per period\n"
            f"Trip distribution={self.config.trip_distribution.name.lower()}\n"
            f"Minimum trip length={self.config.min_trip_distance} blocks\n"
            f"Idle drivers moving={self.config.available_drivers_moving}\n"
            f"Simulations of {self.config.time_periods} periods.")
        ax.text(.05,
                .05,
                caption,
                bbox={
                    'facecolor': 'whitesmoke',
                    'edgecolor': 'grey',
                    'pad': 10,
                },
                verticalalignment="bottom",
                transform=ax.transAxes,
                fontsize=11,
                alpha=0.8)
        ax.set_title(f"Ridehail simulation sequence, "
                     f"{datetime.now().strftime('%Y-%m-%d')}")
        ax.legend()

    def _fit(self, x, a, b, c):
        return (a + b / (x + c))
