#!/usr/bin/python3
"""
Control a sequence of simulations
"""
import logging
import copy
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from matplotlib import animation
from matplotlib import offsetbox
from scipy.optimize import curve_fit
from ridehail import atom
from ridehail import simulation
from ridehail import animation as rh_animation

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
        if self.config.equilibrate != atom.Equilibration.NONE:
            if self.config.reserved_wage_increment is None:
                self.reserved_wages = [self.config.reserved_wage]
            else:
                self.reserved_wages = [
                    x / precision for x in range(
                        int(self.config.reserved_wage * precision),
                        int(self.config.reserved_wage_max * precision + 1),
                        int(self.config.reserved_wage_increment * precision))
                ]
            if self.config.wait_cost_increment is None:
                self.wait_costs = [self.config.wait_cost]
            else:
                self.wait_costs = [
                    int(self.config.wait_cost_max * precision + 1),
                    int(self.config.wait_cost_increment * precision)
                ]
        else:
            self.reserved_wages = [0]
            self.wait_costs = [0]
        self.driver_counts = [
            x for x in
            range(self.config.driver_count, self.config.driver_count_max +
                  1, self.config.driver_count_increment)
        ]
        logger.info(f"Driver counts: {self.driver_counts}")
        if len(self.driver_counts) == 0:
            self.driver_counts = [self.config.driver_count]
        self.prices = [
            x / precision
            for x in range(int(self.config.price * precision),
                           int(self.config.price_max * precision) +
                           1, int(self.config.price_increment * precision))
        ]
        logger.info(f"Prices: {self.prices}")
        if len(self.prices) == 0:
            self.prices = [self.config.price]
        if len(self.prices) > 1 and len(self.driver_counts) > 1:
            logger.error("Limitation: cannot run a sequence incrementing "
                         "both driver counts and prices.\n"
                         "Please set either price_max or driver_count_max "
                         "to less than or equal to price or driver_count.")
            exit(-1)
        self.trip_wait_fraction = []
        self.driver_paid_fraction = []
        self.driver_unpaid_fraction = []
        self.driver_available_fraction = []
        self.driver_pickup_fraction = []
        self.frame_count = (len(self.driver_counts) * len(self.prices) *
                            self.config.price_repeat)
        # self.plot_count = len(set(self.prices))
        self.plot_count = 1
        self.color_palette = sns.color_palette()

    def run_sequence(self):
        """
        Do the run
        """
        if self.config.draw == rh_animation.Animation.NONE:
            # if os.path.exists(self.config["config_file"]):
            # Iterate over equilibration models for driver counts
            for reserved_wage in self.reserved_wages:
                for wait_cost in self.wait_costs:
                    for price in self.prices:
                        for driver_count in self.driver_counts:
                            self._next_sim(reserved_wage=reserved_wage,
                                           wait_cost=wait_cost,
                                           price=price,
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
            anim = animation.FuncAnimation(fig,
                                           self._next_frame,
                                           frames=self.frame_count,
                                           fargs=[axes],
                                           repeat=False,
                                           repeat_delay=3000)
            self.output_animation(anim, plt, self.config.output)
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
            results.output["trip_fraction_wait_time"])

    def _next_sim(self,
                  index=None,
                  reserved_wage=None,
                  wait_cost=None,
                  price=None,
                  driver_count=None):
        """
        Run a single simulation
        """
        if price is None:
            price_index = int(index / len(self.driver_counts))
            price = self.prices[price_index]
        if driver_count is None:
            driver_count_index = index % len(self.driver_counts)
            driver_count = self.driver_counts[driver_count_index]
        if reserved_wage is None:
            reserved_wage_index = index % len(self.reserved_wages)
            reserved_wage = self.reserved_wages[reserved_wage_index]
        if wait_cost is None:
            wait_cost_index = index % len(self.wait_costs)
            wait_cost = self.wait_costs[wait_cost_index]
        # Set configuration parameters
        # For now, say we can't draw simulation-level plots
        # if we are running a sequence
        runconfig = copy.deepcopy(self.config)
        runconfig.draw = rh_animation.Animation.NONE
        runconfig.reserved_wage = reserved_wage
        runconfig.wait_cost = wait_cost
        runconfig.price = price
        runconfig.driver_count = driver_count
        sim = simulation.RideHailSimulation(runconfig)
        results = sim.simulate()
        results.write_json(self.config.jsonl)
        self._collect_sim_results(results)
        logger.info(("Simulation completed"
                     f", price={price}"
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
        elif len(self.prices) > 1:
            x = self.prices[:j]
            fit_function = self._fit_price
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

        self._plot_with_fit(
            ax,
            i,
            palette_index=palette_index,
            x=x,
            y=self.driver_available_fraction,
            x_fit=x_fit,
            y_fit=available_fit,
            x_plot=x_plot,
            label=rh_animation.PlotArray.DRIVER_AVAILABLE_FRACTION.value,
            fit_function=fit_function)
        palette_index += 1
        self._plot_with_fit(
            ax,
            i,
            palette_index=palette_index,
            x=x,
            y=self.driver_pickup_fraction,
            x_fit=x_fit,
            y_fit=pickup_fit,
            x_plot=x_plot,
            label=rh_animation.PlotArray.DRIVER_PICKUP_FRACTION.value,
            fit_function=fit_function)
        palette_index += 1
        self._plot_with_fit(
            ax,
            i,
            palette_index=palette_index,
            x=x,
            y=self.driver_paid_fraction,
            x_fit=x_fit,
            y_fit=paid_fit,
            x_plot=x_plot,
            label=rh_animation.PlotArray.DRIVER_PAID_FRACTION.value,
            fit_function=fit_function)
        palette_index += 1
        self._plot_with_fit(
            ax,
            i,
            palette_index=palette_index,
            x=x,
            y=self.trip_wait_fraction,
            x_fit=x_fit,
            y_fit=wait_fit,
            x_plot=x_plot,
            label=rh_animation.PlotArray.TRIP_WAIT_FRACTION.value,
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
        if len(self.prices) == 1:
            ax.set_xlabel("Drivers")
            ax.set_xlim(left=min(self.driver_counts),
                        right=max(self.driver_counts))
            caption_supply_or_demand = (
                f"Fixed demand={self.prices[0]} requests per block\n")
            # caption_x_location = 0.05
            # caption_y_location = 0.05
            caption_location = "upper right"
        elif len(self.driver_counts) == 1:
            ax.set_xlabel("Request rates")
            ax.set_xlim(left=min(self.prices), right=max(self.prices))
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
        anchored_text = offsetbox.AnchoredText(caption,
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
        ax.legend(loc="lower left")

    def _fit_driver_count(self, x, a, b, c):
        return (a + b / (x + c))

    def _fit_price(self, x, a, b, c):
        return (a + b * x + c * x * x)

    def output_animation(self, anim, plt, output):
        """
        Generic output functions
        """
        if output is not None:
            logger.debug(f"Writing output to {output}...")
        if output.endswith("mp4"):
            writer = animation.FFMpegFileWriter(fps=10, bitrate=1800)
            anim.save(output, writer=writer)
            del anim
        elif output.endswith("gif"):
            writer = animation.ImageMagickFileWriter()
            anim.save(output, writer=writer)
            del anim
        else:
            plt.show()
            del anim
            plt.close()
