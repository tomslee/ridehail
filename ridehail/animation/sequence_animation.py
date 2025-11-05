"""
Matplotlib-based sequence animation for ridehail simulations.

This module provides visualization for parameter sweep sequences,
showing how metrics change as vehicle counts, request rates,
inhomogeneities, or commissions are varied across simulations.
"""

import logging
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime
from matplotlib import animation
from matplotlib import offsetbox
from matplotlib.ticker import AutoMinorLocator
from scipy.optimize import curve_fit

from ridehail.animation.base import RideHailAnimation
from ridehail.atom import Measure, DispatchMethod, Equilibration


class SequenceAnimation(RideHailAnimation):
    """
    Matplotlib-based animation for sequence visualization.

    Displays line charts with curve fitting showing how simulation
    metrics evolve across parameter sweeps.
    """

    def __init__(self, sim, sequence_runner):
        """
        Initialize sequence animation.

        Args:
            sim: RideHailSimulation instance
            sequence_runner: RideHailSimulationSequence instance
        """
        super().__init__(sim)
        self.sequence_runner = sequence_runner
        self.plot_count = 1
        self.color_palette = sns.color_palette()

    def animate(self):
        """Start the matplotlib-based sequence animation"""
        plot_size_x = 12
        plot_size_y = 8
        ncols = self.plot_count
        fig, self.axes = plt.subplots(
            ncols=ncols, figsize=(ncols * plot_size_x, plot_size_y)
        )
        fig.canvas.mpl_connect("button_press_event", self._on_click)
        fig.canvas.mpl_connect("key_press_event", self._on_key_press)
        self.axes = [self.axes] if self.plot_count == 1 else self.axes

        # Position the display window on the screen
        self.fig_manager = plt.get_current_fig_manager()
        if hasattr(self.fig_manager, "window"):
            if hasattr(self.fig_manager.window, "wm_geometry"):
                # Set window title using matplotlib's method
                self.fig_manager.set_window_title(
                    f"Ridehail Animation Sequence - {self.sim.config_file_root}"
                )
                # Optionally set window position
                # self.fig_manager.window.wm_geometry("+10+10")
                anim = animation.FuncAnimation(
                    fig,
                    self._next_frame,
                    frames=self.sequence_runner.frame_count,
                    init_func=self._init_animation,
                    fargs=[self.sim.config],
                    repeat=False,
                    repeat_delay=3000,
                )
                self._output_animation(anim, plt, self.animation_output_file)
            else:
                logging.error(
                    ("Missing attribute on fig_manager: window or window.wm_geometry")
                )

    def _init_animation(self):
        """Initialize animation frame"""
        return None

    def _on_click(self, event):
        """Handle mouse click events"""
        # TEMP - could implement click-to-pause functionality
        pass

    def _on_key_press(self, event):
        """Handle keyboard events"""
        if event.key in ("escape", " "):
            self.pause_plot ^= True

    def _plot_with_fit(
        self, ax, i, palette_index, x, y, x_fit, y_fit, x_plot, label, fit_function
    ):
        """
        Plot a scatter plot for a given variable y,
        then a best fit line using fit method y_fit.
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
            logging.error(e)

    def _next_frame(self, i, *fargs):
        """
        Function called from sequence animator to generate frame i
        of the animation.
        """
        config = fargs[0]
        results = self.sequence_runner._next_sim(i, config=config)
        ax = self.axes[0]
        ax.clear()
        if self.pause_plot:
            return
        j = i + 1

        # Determine which parameter is being varied and get appropriate data
        if len(self.sequence_runner.vehicle_counts) > 1:
            x = self.sequence_runner.vehicle_counts[:j]
            fit_function = self._fit_vehicle_count
        elif len(self.sequence_runner.request_rates) > 1:
            x = self.sequence_runner.request_rates[:j]
            fit_function = self._fit_request_rate
        elif len(self.sequence_runner.inhomogeneities) > 1:
            x = self.sequence_runner.inhomogeneities[:j]
            fit_function = self._fit_inhomogeneity
        elif len(self.sequence_runner.commissions) > 1:
            x = self.sequence_runner.commissions[:j]
            fit_function = self._fit_commission

        # Prepare data for plotting based on varying parameter
        if len(self.sequence_runner.vehicle_counts) > 1:
            if (
                self.sequence_runner.dispatch_method
                == DispatchMethod.FORWARD_DISPATCH.value
            ):
                z = zip(
                    x,
                    self.sequence_runner.vehicle_p1_fraction[:j],
                    self.sequence_runner.vehicle_p2_fraction[:j],
                    self.sequence_runner.vehicle_p3_fraction[:j],
                    self.sequence_runner.trip_wait_fraction[:j],
                    self.sequence_runner.forward_dispatch_fraction[:j],
                )
            else:
                z = zip(
                    x,
                    self.sequence_runner.vehicle_p1_fraction[:j],
                    self.sequence_runner.vehicle_p2_fraction[:j],
                    self.sequence_runner.vehicle_p3_fraction[:j],
                    self.sequence_runner.trip_wait_fraction[:j],
                )
        elif len(self.sequence_runner.request_rates) > 1:
            z = zip(
                x,
                self.sequence_runner.vehicle_p1_fraction[:j],
                self.sequence_runner.vehicle_p2_fraction[:j],
                self.sequence_runner.vehicle_p3_fraction[:j],
                self.sequence_runner.trip_wait_fraction[:j],
                self.sequence_runner.mean_vehicle_count[:j],
            )
        elif len(self.sequence_runner.inhomogeneities) > 1:
            z = zip(
                x,
                self.sequence_runner.vehicle_p1_fraction[:j],
                self.sequence_runner.vehicle_p2_fraction[:j],
                self.sequence_runner.vehicle_p3_fraction[:j],
                self.sequence_runner.trip_wait_fraction[:j],
            )
        elif len(self.sequence_runner.commissions) > 1:
            z = zip(
                x,
                self.sequence_runner.vehicle_p1_fraction[:j],
                self.sequence_runner.vehicle_p2_fraction[:j],
                self.sequence_runner.vehicle_p3_fraction[:j],
                self.sequence_runner.trip_wait_fraction[:j],
                self.sequence_runner.mean_vehicle_count[:j],
            )

        # Only fit for states where vehicles have some idle time
        z_fit = [zval for zval in z if zval[1] > 0.05]
        if len(z_fit) > 0:
            if len(self.sequence_runner.vehicle_counts) > 1:
                if (
                    self.sequence_runner.dispatch_method
                    == DispatchMethod.FORWARD_DISPATCH.value
                ):
                    (
                        x_fit,
                        idle_fit,
                        pickup_fit,
                        paid_fit,
                        wait_fit,
                        forward_dispatch_fit,
                    ) = zip(*z_fit)
                else:
                    (
                        x_fit,
                        idle_fit,
                        pickup_fit,
                        paid_fit,
                        wait_fit,
                    ) = zip(*z_fit)
            elif len(self.sequence_runner.request_rates) > 1:
                (x_fit, idle_fit, pickup_fit, paid_fit, wait_fit, vehicle_count) = zip(
                    *z_fit
                )
            elif len(self.sequence_runner.commissions) > 1:
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
            forward_dispatch_fit = None
            x_plot = None

        # Plot each metric with curve fitting
        palette_index = 0
        self._plot_with_fit(
            ax,
            i,
            palette_index=palette_index,
            x=x,
            y=self.sequence_runner.vehicle_p1_fraction,
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
            y=self.sequence_runner.vehicle_p2_fraction,
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
            y=self.sequence_runner.vehicle_p3_fraction,
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
            y=self.sequence_runner.trip_wait_fraction,
            x_fit=x_fit,
            y_fit=wait_fit,
            x_plot=x_plot,
            label=Measure.TRIP_MEAN_WAIT_FRACTION.value,
            fit_function=fit_function,
        )
        if (
            self.sequence_runner.dispatch_method
            == DispatchMethod.FORWARD_DISPATCH.value
        ):
            palette_index += 1
            self._plot_with_fit(
                ax,
                i,
                palette_index=palette_index,
                x=x,
                y=self.sequence_runner.forward_dispatch_fraction,
                x_fit=x_fit,
                y_fit=forward_dispatch_fit,
                x_plot=x_plot,
                label=Measure.TRIP_FORWARD_DISPATCH_FRACTION.value,
                fit_function=fit_function,
            )

        # Configure plot appearance
        ax.set_ylim(bottom=0, top=1)
        if len(self.sequence_runner.vehicle_counts) > 1:
            ax.set_xlabel("Vehicles")
            ax.set_xlim(
                left=min(self.sequence_runner.vehicle_counts),
                right=max(self.sequence_runner.vehicle_counts),
            )
            # show the x axis to zero, unless it's way off from other points
            if (
                min(self.sequence_runner.vehicle_counts)
                / max(self.sequence_runner.vehicle_counts)
                < 0.2
            ):
                ax.set_xlim(left=0, right=max(self.sequence_runner.vehicle_counts))
            caption_location = "upper center"
        elif len(self.sequence_runner.request_rates) > 1:
            ax.set_xlabel("Request rates")
            ax.set_xlim(
                left=min(self.sequence_runner.request_rates),
                right=max(self.sequence_runner.request_rates),
            )
            caption_location = "upper left"
        elif len(self.sequence_runner.commissions) > 1:
            ax.set_xlabel("Commissions")
            ax.set_xlim(
                left=min(self.sequence_runner.commissions),
                right=max(self.sequence_runner.commissions),
            )
            caption_location = "upper center"

        ax.set_ylabel("Fractional values")
        ax.grid(
            visible=True,
            which="major",
            axis="both",
            linewidth="2",
        )
        ax.grid(
            which="minor",
            axis="both",
            linewidth="1",
        )

        # Configure ticks and gridlines
        ax.tick_params(which="minor", bottom=False, left=False)
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(4))
        ax.minorticks_on()

        # Add title and caption based on varying parameter
        anchor_props = {
            "bbox": {"facecolor": "#EAEAF2", "edgecolor": "silver", "pad": 5},
            "fontsize": 10,
            "linespacing": 2.0,
        }

        if len(self.sequence_runner.vehicle_counts) > 1:
            ax.set_title(
                f"Ridehail simulation sequence: city size = {config.city_size.value}"
            )
            caption = self._create_vehicle_count_caption(config)
        elif len(self.sequence_runner.request_rates) > 1:
            ax.set_title(
                (
                    f"Ridehail simulation sequence: "
                    f"city size = {config.city_size.value}, "
                    f"reservation_wage = {config.reservation_wage.value}"
                )
            )
            caption = self._create_request_rate_caption(config)
        elif len(self.sequence_runner.commissions) > 1:
            ax.set_title(
                (
                    f"Ridehail simulation sequence: "
                    f"city size = {config.city_size.value}, "
                    f"demand = {config.base_demand.value}"
                )
            )
            caption = self._create_commission_caption(config)
        else:
            ax.set_title(
                f"Ridehail simulation sequence: "
                f"city size = {config.city_size.value}, "
                f"request rate = {config.base_demand.value}, "
            )
            caption = self._create_default_caption(config)

        if config.title.value:
            ax.set_title(config.title.value)

        anchored_text = offsetbox.AnchoredText(
            caption, loc=caption_location, frameon=False, prop=anchor_props
        )
        ax.add_artist(anchored_text)
        ax.legend()
        return results

    def _create_vehicle_count_caption(self, config):
        """Create caption for vehicle count sequence"""
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
        if (
            self.sequence_runner.dispatch_method
            == DispatchMethod.FORWARD_DISPATCH.value
        ):
            caption += f"\nDispatch method={self.sequence_runner.dispatch_method}"
            caption += (
                f"\nwith forward dispatch bias={config.forward_dispatch_bias.value}"
            )
        return caption

    def _create_request_rate_caption(self, config):
        """Create caption for request rate sequence"""
        if config.equilibration.value == Equilibration.PRICE:
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
        elif config.equilibration.value == Equilibration.WAIT_FRACTION:
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
        return caption

    def _create_commission_caption(self, config):
        """Create caption for commission sequence"""
        if config.equilibration.value == Equilibration.PRICE:
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
        elif config.equilibration.value == Equilibration.WAIT_FRACTION:
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
        return caption

    def _create_default_caption(self, config):
        """Create default caption"""
        return (
            f"Trip length in [{config.min_trip_distance.value}, "
            f"{config.max_trip_distance.value}] blocks\n"
            f"Inhomogeneity={config.inhomogeneity.value}\n"
            f"Idle vehicles moving="
            f"{config.idle_vehicles_moving.value}\n"
            f"Simulation length={config.time_blocks.value} blocks\n"
            f"Results window={config.results_window.value} blocks\n"
            f"Generated on {datetime.now().strftime('%Y-%m-%d')}"
        )

    def _fit_vehicle_count(self, x, a, b, c):
        """Fit function for vehicle count sequences"""
        return a + b / (x + c)

    def _fit_price(self, x, a, b, c):
        """Fit function for price sequences"""
        return a + b * x + c * x * x

    def _fit_request_rate(self, x, a, b, c):
        """Fit function for request rate sequences"""
        return a + b * x + c * x * x

    def _fit_inhomogeneity(self, x, a, b, c):
        """Fit function for inhomogeneity sequences"""
        return a + b * x

    def _fit_commission(self, x, a, b, c):
        """Fit function for commission sequences"""
        return a + b * x + c * x * x

    def _output_animation(self, anim, plt, animation_output_file):
        """
        Generic output functions for animation
        """
        if animation_output_file:
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
