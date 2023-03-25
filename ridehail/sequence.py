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
from matplotlib.ticker import AutoMinorLocator
from scipy.optimize import curve_fit
from ridehail.simulation import RideHailSimulation
from ridehail.animation import Measure
from ridehail.atom import Animation, Equilibration


class RideHailSimulationSequence:
    """
    A sequence of simulations
    """

    def __init__(self, config):
        """
        Initialize sequence properties
        """
        self.vehicle_counts = [config.vehicle_count.value]
        self.request_rates = [config.base_demand.value]
        self.inhomogeneities = [config.inhomogeneity.value]
        self.reservation_wage = [config.reservation_wage.value]
        self.prices = [config.price.value]
        if config.vehicle_count_increment.value and config.vehicle_count_max.value:
            self.vehicle_counts = [
                x
                for x in range(
                    config.vehicle_count.value,
                    config.vehicle_count_max.value + 1,
                    config.vehicle_count_increment.value,
                )
            ]
        if config.request_rate_increment.value and config.request_rate_max.value:
            # request rates managed to two decimal places
            self.request_rates = [
                x * 0.01
                for x in range(
                    int(100 * config.base_demand.value),
                    int(100 * (config.request_rate_max.value + 1)),
                    int(100 * config.request_rate_increment.value),
                )
            ]
        if config.inhomogeneity_increment.value and config.inhomogeneity_max.value:
            # inhomogeneities managed to two decimal places
            self.inhomogeneities = [
                x * 0.01
                for x in range(
                    int(100 * config.inhomogeneity.value),
                    int(100 * (config.inhomogeneity_max.value) + 1),
                    int(100 * config.inhomogeneity_increment.value),
                )
            ]
        # Check if this is a valid sequence
        # Horribly inelegant at the moment
        # test_sequence = (
        # len(self.request_rates),
        # len(self.vehicle_counts),
        # len(self.inhomogeneities),
        # )
        # Create lists to hold the sequence plot data
        self.trip_wait_fraction = []
        self.vehicle_idle_fraction = []
        self.vehicle_pickup_fraction = []
        self.vehicle_paid_fraction = []
        self.mean_vehicle_count = []
        self.frame_count = len(self.vehicle_counts) * len(self.request_rates)
        self.plot_count = 1
        self.pause_plot = False  # toggle for pausing
        self.color_palette = sns.color_palette()

    def run_sequence(self, config):
        """
        Loop through the sequence of simulations.
        """
        # output_file_handle = open(f"{config.jsonl_file}", 'a')
        # output_file_handle.write(
        # json.dumps(rh_config.WritableConfig(config).__dict__) + "\n")
        # output_file_handle.close()
        if config.animation_style.value == Animation.NONE:
            # Iterate over models
            for request_rate in self.request_rates:
                for vehicle_count in self.vehicle_counts:
                    for inhomogeneity in self.inhomogeneities:
                        results = self._next_sim(
                            request_rate=request_rate,
                            vehicle_count=vehicle_count,
                            inhomogeneity=inhomogeneity,
                            config=config,
                        )
        elif config.animation_style.value == Animation.SEQUENCE:
            plot_size_x = 12
            plot_size_y = 8
            ncols = self.plot_count
            fig, self.axes = plt.subplots(
                ncols=ncols, figsize=(ncols * plot_size_x, plot_size_y)
            )
            fig.canvas.mpl_connect("button_press_event", self.on_click)
            fig.canvas.mpl_connect("key_press_event", self.on_key_press)
            self.axes = [self.axes] if self.plot_count == 1 else self.axes
            # Position the display window on the screen
            self.fig_manager = plt.get_current_fig_manager()
            if hasattr(self.fig_manager, "window"):
                if hasattr(self.fig_manager.window, "wm_geometry"):
                    self.fig_manager.window.wm_geometry("+10+10").set_window_title(
                        f"Ridehail Animation Sequence - " f"{config.config_file_root}"
                    )
                anim = animation.FuncAnimation(
                    fig,
                    self._next_frame,
                    frames=self.frame_count,
                    init_func=self.init_animation,
                    fargs=[config],
                    repeat=False,
                    repeat_delay=3000,
                )
            self.output_animation(anim, plt, config.animation_output_file.value)
            fig.savefig(f"./img/{config.config_file_root}" f"-{config.start_time}.png")
        else:
            logging.error(
                f"\n\tThe 'animation_style' configuration parameter "
                f"in the [ANIMATION] section of"
                f"\n\tthe configuration file is set to "
                f"'{config.animation_style.value}'."
                f"\n\n\tTo run a sequence, set this to either "
                f"'{Animation.SEQUENCE.value}'"
                f"or '{Animation.NONE.value}'."
                f"\n\t(A setting of "
                f"'{Animation.STATS.value}' may be the "
                "result of a typo)."
            )

    def init_animation(self):
        return None

    def on_click(self, event):
        # TEMP
        # self.pause_plot ^= True
        pass

    def on_key_press(self, event):
        """
        Respond to a key press
        """
        if event.key in ("escape", " "):
            self.pause_plot ^= True

    def _collect_sim_results(self, results):
        """
        After a simulation, collect the results for plotting etc
        """
        self.vehicle_idle_fraction.append(results.end_state["vehicle_fraction_p1"])
        self.vehicle_pickup_fraction.append(results.end_state["vehicle_fraction_p2"])
        self.vehicle_paid_fraction.append(results.end_state["vehicle_fraction_p3"])
        self.trip_wait_fraction.append(results.end_state["mean_trip_wait_fraction"])
        self.mean_vehicle_count.append(results.end_state["mean_vehicle_count"])

    def _next_sim(
        self,
        index=None,
        request_rate=None,
        vehicle_count=None,
        inhomogeneity=None,
        config=None,
    ):
        """
        Run a single simulation
        """
        # If called from animation, we are looping over a single variable.
        # Compute the value of that variable from the index.
        if request_rate is None:
            request_rate_index = index % len(self.request_rates)
            request_rate = self.request_rates[request_rate_index]
        if vehicle_count is None:
            vehicle_count_index = index % len(self.vehicle_counts)
            vehicle_count = self.vehicle_counts[vehicle_count_index]
        if inhomogeneity is None:
            inhomogeneity_index = index % len(self.inhomogeneities)
            inhomogeneity = self.inhomogeneities[inhomogeneity_index]
        # Set configuration parameters
        # For now, say we can't draw simulation-level plots
        # if we are running a sequence
        runconfig = copy.deepcopy(config)
        runconfig.animation_style.value = Animation.NONE
        runconfig.base_demand.value = request_rate
        runconfig.vehicle_count.value = vehicle_count
        runconfig.inhomogeneity.value = inhomogeneity
        sim = RideHailSimulation(runconfig)
        results = sim.simulate()
        self._collect_sim_results(results)
        logging.info(
            (
                "Simulation completed"
                f": Nv={vehicle_count:d}"
                f", R={request_rate:.02f}"
                f", I={inhomogeneity:.02f}"
                f", p1={self.vehicle_idle_fraction[-1]:.02f}"
                f", p2={self.vehicle_pickup_fraction[-1]:.02f}"
                f", p3={self.vehicle_paid_fraction[-1]:.02f}"
                f", mvc={self.mean_vehicle_count[-1]:.02f}"
                f", w={self.trip_wait_fraction[-1]:.02f}"
            )
        )
        return results

    def _plot_with_fit(
        self, ax, i, palette_index, x, y, x_fit, y_fit, x_plot, label, fit_function
    ):
        """
        plot a scatter plot, then a best fit line
        """
        if len(x) > 0:
            ax.plot(
                x[: i + 1],
                y[: i + 1],
                lw=0,
                marker="o",
                markersize=6,
                color=self.color_palette[palette_index],
                alpha=0.8,
                label=label,
            )
        try:
            if x_fit and y_fit:
                # a + b / (x+c)
                p0_a = y_fit[-1]
                p0_b = y_fit[0] * x_fit[0]
                p0_c = 0
                p0 = (p0_a, p0_b, p0_c)
                popt, _ = curve_fit(fit_function, x_fit, y_fit, p0=p0, maxfev=2000)
                y_plot = [fit_function(xval, *popt) for xval in x_plot]
                if label.lower().startswith("vehicle"):
                    linestyle = "solid"
                else:
                    linestyle = "dashed"
                ax.plot(
                    x_plot,
                    y_plot,
                    lw=2,
                    ls=linestyle,
                    alpha=0.8,
                    color=self.color_palette[palette_index],
                )
        except (RuntimeError, TypeError) as e:
            logging.info(e)

    def _next_frame(self, i, *fargs):
        """
        Function called from sequence animator to generate frame i
        of the animation.
        self.vehicle_count and other sequence variables
        hold a value for each simulation
        """
        config = fargs[0]
        results = self._next_sim(i, config=config)
        ax = self.axes[0]
        ax.clear()
        if self.pause_plot:
            return
        j = i + 1
        if len(self.vehicle_counts) > 1:
            x = self.vehicle_counts[:j]
            fit_function = self._fit_vehicle_count
        elif len(self.request_rates) > 1:
            x = self.request_rates[:j]
            fit_function = self._fit_request_rate
        elif len(self.inhomogeneities) > 1:
            x = self.inhomogeneities[:j]
            fit_function = self._fit_inhomogeneity
        if len(self.vehicle_counts) > 1:
            z = zip(
                x,
                self.vehicle_idle_fraction[:j],
                self.vehicle_pickup_fraction[:j],
                self.vehicle_paid_fraction[:j],
                self.trip_wait_fraction[:j],
            )
        elif len(self.request_rates) > 1:
            z = zip(
                x,
                self.vehicle_idle_fraction[:j],
                self.vehicle_pickup_fraction[:j],
                self.vehicle_paid_fraction[:j],
                self.trip_wait_fraction[:j],
                self.mean_vehicle_count[:j],
            )
        elif len(self.inhomogeneities) > 1:
            z = zip(
                x,
                self.vehicle_idle_fraction[:j],
                self.vehicle_pickup_fraction[:j],
                self.vehicle_paid_fraction[:j],
                self.trip_wait_fraction[:j],
            )
        # Only fit for states where vehicles have some idle time
        z_fit = [zval for zval in z if zval[1] > 0.05]
        if len(z_fit) > 0:
            if len(self.vehicle_counts) > 1:
                (x_fit, idle_fit, pickup_fit, paid_fit, wait_fit) = zip(*z_fit)
            elif len(self.request_rates) > 1:
                (x_fit, idle_fit, pickup_fit, paid_fit, wait_fit, vehicle_count) = zip(
                    *z_fit
                )
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
            label=Measure.VEHICLE_FRACTION_P1.value,
            fit_function=fit_function,
        )
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
            label=Measure.VEHICLE_FRACTION_P2.value,
            fit_function=fit_function,
        )
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
            label=Measure.VEHICLE_FRACTION_P3.value,
            fit_function=fit_function,
        )
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
            label=Measure.TRIP_MEAN_WAIT_FRACTION.value,
            fit_function=fit_function,
        )
        # palette_index += 1
        # self._plot_with_fit(ax,
        # i,
        # palette_index=palette_index,
        # x=x,
        # x_fit=x_fit,
        # x_plot=x_plot,
        # label="Unpaid fraction",
        # fit_function=fit_function)
        ax.set_ylim(bottom=0, top=1)
        if len(self.vehicle_counts) > 1:
            ax.set_xlabel("Vehicles")
            ax.set_xlim(left=min(self.vehicle_counts), right=max(self.vehicle_counts))
            # show the x axis to zero, unless it's way off from other points
            if min(self.vehicle_counts) / max(self.vehicle_counts) < 0.2:
                ax.set_xlim(left=0, right=max(self.vehicle_counts))
            # caption_supply_or_demand = (
            #   f"Fixed demand={config.base_demand} requests per block\n")
            # caption_x_location = 0.05
            # caption_y_location = 0.05
            caption_location = "upper center"
        elif len(self.request_rates) > 1:
            ax.set_xlabel("Request rates")
            ax.set_xlim(left=min(self.request_rates), right=max(self.request_rates))
            # caption_supply_or_demand = (
            #     f"Fixed supply={self.vehicle_counts[0]} vehicles\n")
            # caption_x_location = 0.05
            # caption_y_location = 0.4
            caption_location = "upper left"
        ax.set_ylabel("Fractional values")
        ax.grid(
            visible=True,
            which="major",
            axis="both",
            # color="black",
            linewidth="2",
        )
        ax.grid(
            # visible=True,
            which="minor",
            axis="both",
            # color="white",
            linewidth="1",
        )
        # Minor ticks
        # Show gridlines for:
        # which - both minor and major ticks
        # axis - both x and y
        #
        # ax.yaxis.set_minor_locator(MultipleLocator(4))
        # Now hide the minor ticks (but leave the gridlines).
        ax.tick_params(which="minor", bottom=False, left=False)
        # Only show minor gridlines once in between major gridlines.
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(4))
        ax.minorticks_on()
        anchor_props = {
            # 'backgroundcolor': 'lavender',
            "bbox": {"facecolor": "#EAEAF2", "edgecolor": "silver", "pad": 5},
            "fontsize": 10,
            "linespacing": 2.0,
        }
        if len(self.vehicle_counts) > 1:
            ax.set_title(
                f"Ridehail simulation sequence: "
                f"city size = {config.city_size.value}"
            )
            caption = (
                f"Request rate = {config.base_demand.value}/block\n"
                f"Trip length in [{config.min_trip_distance.value}, "
                f"{config.max_trip_distance.value}] blocks\n"
                f"Inhomogeneity={config.inhomogeneity.value}\n"
                f"Idle vehicles moving={config.idle_vehicles_moving.value}\n"
                f"Simulation length={config.time_blocks.value} blocks\n"
                f"Results window={config.results_window.value} blocks\n"
                f"Generated on {datetime.now().strftime('%Y-%m-%d')}"
            )
        elif len(self.request_rates) > 1:
            ax.set_title(
                (
                    f"Ridehail simulation sequence: "
                    f"city size = {config.city_size.value}, "
                    f"reservation_wage = {config.reservation_wage.value}"
                )
            )
            if config.equilibrate and config.equilibration.value == Equilibration.PRICE:
                caption = (
                    f"Reservation wage = {config.reservation_wage.value}\n"
                    f"Trip length in [{config.min_trip_distance.value}, "
                    f"{config.max_trip_distance.value}] blocks\n"
                    f"Inhomogeneity={config.inhomogeneity.value}\n"
                    f"Idle vehicles moving="
                    f"{config.idle_vehicles_moving.value}\n"
                    f"Simulation length={config.time_blocks.value} blocks\n"
                    f"Results window={config.results_window.value} blocks\n"
                    f"Generated on {datetime.now().strftime('%Y-%m-%d')}"
                )
            elif (
                config.equilibrate
                and config.equilibration.value == Equilibration.WAIT_FRACTION
            ):
                caption = (
                    f"Target wait fraction = {config.wait_fraction.value}\n"
                    f"Trip length in [{config.min_trip_distance.value}, "
                    f"{config.max_trip_distance.value}] blocks\n"
                    f"Inhomogeneity={config.inhomogeneity.value}\n"
                    f"Idle vehicles moving="
                    f"{config.idle_vehicles_moving.value}\n"
                    f"Simulation length={config.time_blocks.value} blocks\n"
                    f"Results window={config.results_window.value} blocks\n"
                    f"Generated on {datetime.now().strftime('%Y-%m-%d')}"
                )
            else:
                caption = (
                    f"{config.vehicle_count} vehicles\n"
                    f"Trip length in [{config.min_trip_distance.value}, "
                    f"{config.max_trip_distance.value}] blocks\n"
                    f"Inhomogeneity={config.inhomogeneity.value}\n"
                    f"Idle vehicles moving="
                    f"{config.idle_vehicles_moving.value}\n"
                    f"Simulation length={config.time_blocks.value} blocks\n"
                    f"Results window={config.results_window.value} blocks\n"
                    f"Generated on {datetime.now().strftime('%Y-%m-%d')}"
                )
        else:
            ax.set_title(
                f"Ridehail simulation sequence: "
                f"city size = {config.city_size.value}, "
                f"request rate = {config.base_demand.value}, "
            )
        if config.title.value:
            ax.set_title(config.title.value)
        anchored_text = offsetbox.AnchoredText(
            caption, loc=caption_location, frameon=False, prop=anchor_props
        )
        ax.add_artist(anchored_text)
        ax.legend()
        return results

    def _fit_vehicle_count(self, x, a, b, c):
        return a + b / (x + c)

    def _fit_price(self, x, a, b, c):
        return a + b * x + c * x * x

    def _fit_request_rate(self, x, a, b, c):
        return a + b * x + c * x * x

    def _fit_inhomogeneity(self, x, a, b, c):
        return a + b * x

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
