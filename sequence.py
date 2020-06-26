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
        """
        self.config = config
        self.driver_count = []
        self.request_rate = []
        self.trip_wait_fraction = []
        self.driver_paid_fraction = []
        self.driver_unpaid_fraction = []
        self.frame_count = (len(self.config.request_rate) *
                            len(self.config.driver_count))
        self.plot_count = len(set(self.config.request_rate))
        self.color_palette = sns.color_palette()

    def run_sequence(self):
        """
        Do the run
        """
        plot_size = 6
        fig, axes = plt.subplots(ncols=self.plot_count,
                                 figsize=(self.plot_count * plot_size,
                                          plot_size))
        plt.suptitle(f"Request rate={self.config.request_rate[0]}, "
                     f"city size={self.config.city_size}")
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
        runconfig = copy.deepcopy(self.config)
        request_rate_index = int(index / len(self.config.driver_count))
        driver_count_index = index % len(self.config.driver_count)
        request_rate = self.config.request_rate[request_rate_index]
        driver_count = self.config.driver_count[driver_count_index]
        runconfig.request_rate = request_rate
        runconfig.driver_count = driver_count
        simulation = RideHailSimulation(runconfig)
        results = simulation.simulate()
        self.driver_count.append(results.sim.driver_count)
        self.request_rate.append(results.sim.request_rate)
        self.driver_unpaid_fraction.append(
            (results.sim.stats[PlotStat.DRIVER_AVAILABLE_FRACTION][-1] +
             results.sim.stats[PlotStat.DRIVER_PICKUP_FRACTION][-1]))
        self.driver_paid_fraction.append(
            results.sim.stats[PlotStat.DRIVER_PAID_FRACTION][-1])
        self.trip_wait_fraction.append(
            results.sim.stats[PlotStat.TRIP_WAIT_FRACTION][-1])

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
        x = self.driver_count
        driver_count_points = len(self.config.driver_count)
        z = zip(self.driver_count, self.request_rate, self.trip_wait_fraction,
                self.driver_unpaid_fraction, self.driver_paid_fraction)
        z_fit = [
            zval for zval in z if zval[0] > (self.config.city_size * zval[1])
        ]
        if len(z_fit) > 0:
            x_fit, request_rate, wait_fit, unpaid_fit, paid_fit = zip(*z_fit)
            x_plot = [
                x_val for x_val in x[:driver_count_points] if x_val in x_fit
            ]
        else:
            x_fit = None
            wait_fit = None
            unpaid_fit = None
            paid_fit = None
        ax.plot(x,
                self.trip_wait_fraction,
                lw=0,
                marker="o",
                markersize=6,
                color=self.color_palette[0],
                alpha=0.6,
                label=PlotStat.TRIP_WAIT_FRACTION.value)
        try:
            if x_fit and wait_fit:
                popt, _ = curve_fit(self._fit, x_fit, wait_fit)
                y_plot = [self._fit(xval, *popt) for xval in x_plot]
                ax.plot(x_plot,
                        y_plot,
                        lw=2,
                        alpha=0.8,
                        color=self.color_palette[0])
        except (RuntimeError, TypeError) as e:
            logger.error(e)
        ax.plot(x,
                self.driver_unpaid_fraction,
                lw=0,
                marker="o",
                markersize=6,
                color=self.color_palette[1],
                alpha=0.6,
                label="Unpaid fraction")
        try:
            if x_fit and unpaid_fit:
                popt1, _ = curve_fit(self._fit, x_fit, unpaid_fit)
                y_plot = [self._fit(xval, *popt1) for xval in x_plot]
                ax.plot(x_plot,
                        y_plot,
                        lw=2,
                        alpha=0.8,
                        color=self.color_palette[1])
        except (RuntimeError, TypeError) as e:
            logger.error(e)
        ax.plot(x,
                self.driver_paid_fraction,
                lw=0,
                marker="o",
                markersize=6,
                color=self.color_palette[2],
                alpha=0.6,
                label=PlotStat.DRIVER_PAID_FRACTION.value)
        try:
            if x_fit and paid_fit:
                popt2, _ = curve_fit(self._fit, x_fit, paid_fit)
                y_plot = [self._fit(xval, *popt2) for xval in x_plot]
                ax.plot(x_plot,
                        y_plot,
                        lw=2,
                        alpha=0.8,
                        color=self.color_palette[2])
        except (RuntimeError, TypeError) as e:
            logger.error(e)
        ax.set_xlim(left=0, right=max(self.config.driver_count))
        ax.set_ylim(bottom=0, top=1)
        ax.set_xlabel("Drivers")
        ax.legend()

    def _fit(self, x, a, b):
        return (a + b / x)
