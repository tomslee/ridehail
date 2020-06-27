#!/usr/bin/python3
"""
Control a sequence of simulations
"""
import logging
import copy
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import seaborn as sns
from scipy.optimize import curve_fit
from plot import Plot, PlotStat
from simulation import RideHailSimulation

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
        self.driver_counts = [
            x for x in
            range(self.config.driver_count, self.config.driver_count_max,
                  self.config.driver_count_increment)
        ]
        # TODO: can only handle one request rate for now
        # self.request_rates = [
        # x * 0.1
        # for x in range(int(self.config.request_rate *
        # 10), int(self.config.request_rate_max * 10),
        # int(self.config.request_rate_increment * 10))
        # ]
        # if len(self.request_rates) == 0:
        self.request_rates = [self.config.request_rate]
        logger.info(self.driver_counts)
        logger.info(self.request_rates)
        self.trip_wait_fraction = []
        self.driver_paid_fraction = []
        self.driver_unpaid_fraction = []
        self.frame_count = (len(self.driver_counts) * len(self.request_rates) *
                            self.config.request_rate_repeat)
        self.plot_count = len(set(self.request_rates))
        self.color_palette = sns.color_palette()

    def run_sequence(self):
        """
        Do the run
        """
        plot_size = 6
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
        logger.info("Sequence completed")

    def _next_sim(self, index):
        """
        Run a single simulation
        """
        # request_rate_index should always be zero now
        request_rate_index = int(index / len(self.driver_counts))
        driver_count_index = index % len(self.driver_counts)
        runconfig = copy.deepcopy(self.config)
        request_rate = self.request_rates[request_rate_index]
        driver_count = self.driver_counts[driver_count_index]
        runconfig.request_rate = request_rate
        runconfig.driver_count = driver_count
        simulation = RideHailSimulation(runconfig)
        results = simulation.simulate()
        self.driver_unpaid_fraction.append(
            (results.sim.stats[PlotStat.DRIVER_AVAILABLE_FRACTION][-1] +
             results.sim.stats[PlotStat.DRIVER_PICKUP_FRACTION][-1]))
        self.driver_paid_fraction.append(
            results.sim.stats[PlotStat.DRIVER_PAID_FRACTION][-1])
        self.trip_wait_fraction.append(
            results.sim.stats[PlotStat.TRIP_WAIT_FRACTION][-1])

    def _plot_with_fit(self, ax, i, palette_index, x, y, x_fit, y_fit, x_plot,
                       label):
        """
        plot a scatter plot, then a best fit line
        """
        if len(x) > 0:
            ax.plot(x[:i],
                    y[:i],
                    lw=0,
                    marker="o",
                    markersize=6,
                    color=self.color_palette[palette_index],
                    alpha=0.6,
                    label=label)
        try:
            if x_fit and y_fit:
                popt, _ = curve_fit(self._fit, x_fit, y_fit)
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
        # TODO: Use zip to prepare a data set for fitting
        self._next_sim(i)
        ax = axes[0]
        ax.clear()
        x = self.driver_counts[:i]
        z = zip(self.driver_counts[:i], self.trip_wait_fraction[:i],
                self.driver_unpaid_fraction[:i], self.driver_paid_fraction[:i])
        z_fit = [
            zval for zval in z
            if zval[0] > (self.config.city_size * self.request_rates[0])
        ]
        if len(z_fit) > 0:
            x_fit, wait_fit, unpaid_fit, paid_fit = zip(*z_fit)
            x_plot = [x_val for x_val in x if x_val in x_fit]
        else:
            x_fit = None
            wait_fit = None
            unpaid_fit = None
            paid_fit = None
        if x_fit:
            self._plot_with_fit(ax,
                                i,
                                palette_index=0,
                                x=x,
                                y=self.trip_wait_fraction,
                                x_fit=x_fit,
                                y_fit=wait_fit,
                                x_plot=x_plot,
                                label=PlotStat.TRIP_WAIT_FRACTION.value)
            self._plot_with_fit(ax,
                                i,
                                palette_index=1,
                                x=x,
                                y=self.driver_unpaid_fraction,
                                x_fit=x_fit,
                                y_fit=unpaid_fit,
                                x_plot=x_plot,
                                label="Unpaid fraction")
            self._plot_with_fit(ax,
                                i,
                                palette_index=2,
                                x=x,
                                y=self.driver_paid_fraction,
                                x_fit=x_fit,
                                y_fit=paid_fit,
                                x_plot=x_plot,
                                label=PlotStat.DRIVER_PAID_FRACTION.value)
        ax.set_xlim(left=0, right=max(self.driver_counts))
        ax.set_ylim(bottom=0, top=1)
        ax.set_xlabel("Drivers")
        ax.set_title(f"Request rate={self.request_rates[0]}, "
                     f"city size={self.config.city_size}")
        ax.legend()

    def _fit(self, x, a, b):
        return (a + b / x)
