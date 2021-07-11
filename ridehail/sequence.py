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
        # construct a list of reserved_wages and costs
        if self.config.equilibrate == atom.Equilibration.NONE:
            self.reserved_wages = [0]
            self.wait_costs = [0]
        else:
            if self.config.reserved_wage_increment is None:
                self.reserved_wages = [self.config.reserved_wage]
            else:
                self.reserved_wages = [
                    x / precision for x in range(
                        int(config.reserved_wage * precision),
                        int(config.reserved_wage_max * precision +
                            1), int(config.reserved_wage_increment *
                                    precision))
                ]
            if self.config.wait_cost_increment is None:
                self.wait_costs = [config.wait_cost]
            else:
                self.wait_costs = [
                    int(config.wait_cost_max * precision + 1),
                    int(config.wait_cost_increment * precision)
                ]
        # Create the list of vehicle counts for the sequence
        self.vehicle_counts = [
            x for x in range(config.vehicle_count, config.vehicle_count_max +
                             1, config.vehicle_count_increment)
        ]
        if len(self.vehicle_counts) == 0:
            self.vehicle_counts = [config.vehicle_count]
        # logging.info(f"Vehicle counts for this sequence = {self.vehicle_counts}")
        # Create the list of prices for the sequence
        if hasattr(config, "price_max") and config.price_max is not None:
            logging.info(f"price_max = {config.price_max}")
            self.prices = [
                x / precision
                for x in range(int(config.price * precision),
                               int(config.price_max * precision) +
                               1, int(config.price_increment * precision))
            ]
        elif hasattr(config, "price"):
            self.prices = [config.price]
        else:
            self.prices = [1]
        logging.info(f"Prices for this sequence = {self.prices}")
        logging.info(f"Vehicle counts for this sequence = {self.vehicle_counts}")
        # Check if this is a valid sequence
        if len(self.prices) > 1 and len(self.vehicle_counts) > 1:
            logging.error("Limitation: cannot run a sequence incrementing "
                          "both vehicle counts and prices.\n"
                          "Please set either price_max or vehicle_count_max "
                          "to less than or equal to price or vehicle_count.")
            exit(-1)
        # Create lists to hold the sequence plot data
        self.trip_wait_fraction = []
        self.vehicle_paid_fraction = []
        self.vehicle_unpaid_fraction = []
        self.vehicle_idle_fraction = []
        self.vehicle_pickup_fraction = []
        self.frame_count = (len(self.vehicle_counts) * len(self.prices))
        # self.plot_count = len(set(self.prices))
        self.plot_count = 1
        self.pause_plot = False  # toggle for pausing
        self.color_palette = sns.color_palette()

    def run_sequence(self):
        """
        Loop through the sequence of simulations.
        """
        if self.config.animate == rh_animation.Animation.NONE:
            # Iterate over equilibration models for vehicle counts
            for reserved_wage in self.reserved_wages:
                for wait_cost in self.wait_costs:
                    for price in self.prices:
                        for vehicle_count in self.vehicle_counts:
                            self._next_sim(reserved_wage=reserved_wage,
                                           wait_cost=wait_cost,
                                           price=price,
                                           vehicle_count=vehicle_count)
        elif self.config.animate == rh_animation.Animation.SEQUENCE:
            logging.info(f"self.config.animate = {self.config.animate}")
            plot_size_x = 12
            plot_size_y = 8
            ncols = self.plot_count
            fig, self.axes = plt.subplots(ncols=ncols,
                                          figsize=(ncols * plot_size_x,
                                                   plot_size_y))
            fig.canvas.mpl_connect('button_press_event', self.on_click)
            fig.canvas.mpl_connect('key_press_event', self.on_key_press)
            self.axes = [self.axes] if self.plot_count == 1 else self.axes
            # Position the display window on the screen
            self.fig_manager = plt.get_current_fig_manager()
            logging.warning(f"self.fig_manager = {self.fig_manager}")
            if hasattr(self.fig_manager, "window"):
                #self.fig_manager.window.wm_geometry("+10+10").set_window_title(
                #f"Ridehail Animation Sequence - "
                #f"{self.config.config_file_root}")
                anim = animation.FuncAnimation(
                    fig,
                    self._next_frame,
                    frames=self.frame_count,
                    # fargs=[],
                    repeat=False,
                    repeat_delay=3000)
            # if hasattr(self.config, "output_animation_file"):
            self.output_animation(anim, plt, self.config.animation_output_file)
            fig.savefig(f"./img/{self.config.config_file_root}"
                        f"-{self.config.start_time}.png")
        else:
            logging.error(
                f"\n\tThe 'animate' configuration parameter in the [ANIMATION] section of"
            f"\n\tthe configuration file is set to '{self.config.animate.value}'." 
            f"\n\n\tTo run a sequence, set this to either '{rh_animation.Animation.SEQUENCE.value}'" 
            f"or '{rh_animation.Animation.NONE.value}'."
            f"\n\t(A setting of '{rh_animation.Animation.STATS.value}' may be the "
            "result of a typo).")
        logging.info("Sequence completed")

    def on_click(self, event):
        self.pause_plot ^= True

    def on_key_press(self, event):
        """
        Respond to a key press
        """
        if event.key == "q":
            try:
                self._animation.event_source.stop()
            except AttributeError:
                logging.info("User pressed 'q': quitting")
                return
        elif event.key in ("m", "M"):
            self.fig_manager.full_screen_toggle()
        elif event.key in ("escape", " "):
            self.pause_plot ^= True
        # else:

    def _collect_sim_results(self, results):
        """
        After a simulation, collect the results for plotting etc
        """
        self.vehicle_idle_fraction.append(
            results.results["end_state"]["vehicle_fraction_idle"])
        self.vehicle_pickup_fraction.append(
            results.results["end_state"]["vehicle_fraction_picking_up"])
        self.vehicle_unpaid_fraction.append(
            results.results["end_state"]["vehicle_fraction_idle"] +
            results.results["end_state"]["vehicle_fraction_picking_up"])
        self.vehicle_paid_fraction.append(
            results.results["end_state"]["vehicle_fraction_with_rider"])
        self.trip_wait_fraction.append(
            results.results["end_state"]["trip_fraction_wait_time"])

    def _next_sim(self,
                  index=None,
                  reserved_wage=None,
                  wait_cost=None,
                  price=None,
                  vehicle_count=None):
        """
        Run a single simulation
        """
        logging.info(f"index = {index}")
        if price is None:
            price_index = int(index / len(self.vehicle_counts))
            price = self.prices[price_index]
        if vehicle_count is None:
            vehicle_count_index = index % len(self.vehicle_counts)
            vehicle_count = self.vehicle_counts[vehicle_count_index]
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
        runconfig.vehicle_count = vehicle_count
        sim = simulation.RideHailSimulation(runconfig)
        results = sim.simulate()
        self._collect_sim_results(results)
        logging.info(("Simulation completed"
                      f", price={price}"
                      f", vehicle_count={vehicle_count}"
                      f", p1 fraction={self.vehicle_idle_fraction[-1]:.02f}"
                      f", p2 fraction={self.vehicle_pickup_fraction[-1]:.02f}"
                      f", p3 fraction={self.vehicle_paid_fraction[-1]:.02f}"))

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
                    alpha=0.8,
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
                if label.lower().startswith("vehicle"):
                    linestyle = "solid"
                else:
                    linestyle = "dashed"
                ax.plot(x_plot,
                        y_plot,
                        lw=2,
                        ls=linestyle,
                        alpha=0.8,
                        color=self.color_palette[palette_index])
        except (RuntimeError, TypeError) as e:
            logging.info(e)

    def _next_frame(self, i):
        """
        Function called from sequence animator to generate frame i
        of the animation.
        self.vehicle_count and other sequence variables
        hold a value for each simulation
        """
        self._next_sim(i)
        ax = self.axes[0]
        logging.info(f"ax = {ax}")
        ax.clear()
        if self.pause_plot:
            return
        j = i + 1
        if len(self.vehicle_counts) > 1:
            x = self.vehicle_counts[:j]
            fit_function = self._fit_vehicle_count
        elif len(self.prices) > 1:
            x = self.prices[:j]
            fit_function = self._fit_price
        z = zip(x, self.vehicle_idle_fraction[:j],
                self.vehicle_pickup_fraction[:j],
                self.vehicle_paid_fraction[:j], self.trip_wait_fraction[:j],
                self.vehicle_unpaid_fraction[:j])
        # Only fit for states where vehicles have some idle time
        z_fit = [zval for zval in z if zval[1] > 0.05]
        if len(z_fit) > 0:
            (x_fit, idle_fit, pickup_fit, paid_fit, wait_fit,
             unpaid_fit) = zip(*z_fit)
            x_plot = [x_val for x_val in x if x_val in x_fit]
        else:
            x_fit = None
            idle_fit = None
            pickup_fit = None
            paid_fit = None
            wait_fit = None
            x_plot = None
        palette_index = 0
        self._plot_with_fit(
            ax,
            i,
            palette_index=palette_index,
            x=x,
            y=self.vehicle_idle_fraction,
            x_fit=x_fit,
            y_fit=idle_fit,
            x_plot=x_plot,
            label=rh_animation.PlotArray.VEHICLE_IDLE_FRACTION.value,
            fit_function=fit_function)
        palette_index += 1
        self._plot_with_fit(
            ax,
            i,
            palette_index=palette_index,
            x=x,
            y=self.vehicle_pickup_fraction,
            x_fit=x_fit,
            y_fit=pickup_fit,
            x_plot=x_plot,
            label=rh_animation.PlotArray.VEHICLE_DISPATCH_FRACTION.value,
            fit_function=fit_function)
        palette_index += 1
        self._plot_with_fit(
            ax,
            i,
            palette_index=palette_index,
            x=x,
            y=self.vehicle_paid_fraction,
            x_fit=x_fit,
            y_fit=paid_fit,
            x_plot=x_plot,
            label=rh_animation.PlotArray.VEHICLE_PAID_FRACTION.value,
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
        # palette_index += 1
        # self._plot_with_fit(ax,
        # i,
        # palette_index=palette_index,
        # x=x,
        # y=self.vehicle_unpaid_fraction,
        # x_fit=x_fit,
        # y_fit=unpaid_fit,
        # x_plot=x_plot,
        # label="Unpaid fraction",
        # fit_function=fit_function)
        ax.set_ylim(bottom=0, top=1)
        if len(self.prices) == 1:
            ax.set_xlabel("Vehicles")
            ax.set_xlim(left=min(self.vehicle_counts),
                        right=max(self.vehicle_counts))
            caption_supply_or_demand = (
                f"Fixed demand={self.config.base_demand} requests per block\n")
            # caption_x_location = 0.05
            # caption_y_location = 0.05
            caption_location = "upper center"
        elif len(self.vehicle_counts) == 1:
            ax.set_xlabel("Request rates")
            ax.set_xlim(left=min(self.prices), right=max(self.prices))
            caption_supply_or_demand = (
                f"Fixed supply={self.vehicle_counts[0]} vehicles\n")
            # caption_x_location = 0.05
            # caption_y_location = 0.4
            caption_location = "lower right"
        ax.set_ylabel("Fractional values")
        caption = (
            f"City size={self.config.city_size} blocks\n"
            f"{caption_supply_or_demand}"
            f"Trip distribution={self.config.trip_distribution.name.lower()}\n"
            f"Minimum trip length={self.config.min_trip_distance} blocks\n"
            f"Maximum trip length={self.config.max_trip_distance} blocks\n"
            f"Idle vehicles moving={self.config.idle_vehicles_moving}\n"
            f"Simulations of {self.config.time_blocks} blocks.")
        anchor_props = {
            # 'backgroundcolor': 'lavender',
            'bbox': {
                'facecolor': 'lavender',
                'edgecolor': 'silver',
                'pad': 5,
            },
            'fontsize': 10,
            'linespacing': 2.0
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
        ax.legend()
        
    def _fit_vehicle_count(self, x, a, b, c):
        return (a + b / (x + c))

    def _fit_price(self, x, a, b, c):
        return (a + b * x + c * x * x)

    def output_animation(self, anim, plt, animation_output_file):
        """
        Generic output functions
        """
        if animation_output_file:
            logging.debug(f"Writing animation_output to {animation_output_file}...")
            if animation_output_file.endswith("mp4"):
                writer = animation.FFMpegFileWriter(fps=10, bitrate=1800)
                anim.save(animation_output_file, writer=writer)
                del anim
            elif animation_output_file.endswith("gif"):
                writer = animation.ImageMagickFileWriter()
                anim.save(animation_output_file, writer=writer)
                del anim
        else:
            plt.show()
            del anim
            plt.close()
