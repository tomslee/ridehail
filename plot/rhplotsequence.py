#!/usr/bin/python3

import sys
import os
import json
import matplotlib.pyplot as plt
import matplotlib as mpl
import logging
import math
import enum
from matplotlib import offsetbox
from matplotlib.ticker import AutoMinorLocator
import seaborn as sns
from datetime import datetime
from scipy.optimize import curve_fit
import numpy as np

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
mpl.rcParams["figure.dpi"] = 90
mpl.rcParams["savefig.dpi"] = 100
sns.set()
sns.set_palette("muted")
# sns.set_palette("deep")


class PlotXAxis(enum.Enum):
    VEHICLE_COUNT = "vehicle count"
    REQUEST_RATE = "request rate"
    INHOMOGENEITY = "inhomogeneity"


def fit_degree_minus_one(x, a, b, c):
    return a + b / (x + c)


def fit_linear(x, a, b):
    return a * x + b


def fit_degree_two(x, a, b, c):
    return a * x * x + b * x + c


def residual_linear(p, x, y):
    return y - fit_linear(x, *p)


def fit_function_wait(x, a, b, c):
    """ I think this goes as the square root.
    Not in use at the moment as it fails to converge."""
    return a + b / (math.sqrt(x) + c)


class Plot:

    sequence = []

    def __init__(self, input_file):
        """
        Read the jsonl input file into a list of dictionaries.
        """
        self.input_file = input_file
        with open(input_file) as f:
            lines = f.readlines()
        for line in lines:
            self.sequence.append(json.loads(line))

    def construct_arrays(self):
        """
        Build arrays from the list of json documents (dictionaries) in the
        sequence output file (one for each simulation).
        Some of these are configuration options that are the same for each
        simulation, but this function builds arrays anyway and we'll deal
        with that later.
        """
        self.city_size = []
        self.time_blocks = []
        self.request_rate = []
        self.inhomogeneity = []
        self.min_trip_distance = []
        self.max_trip_distance = []
        self.idle_vehicles_moving = []
        self.results_window = []
        self.reservation_wage = []
        self.vehicle_count = []
        self.p1 = []
        self.p2 = []
        self.p3 = []
        self.mean_vehicle_count = []
        self.trip_wait_fraction = []
        self.trip_wait_time = []
        self.trip_distance = []
        self.equilibration = False
        if "equilibration" in self.sequence[0]["config"]:
            self.equilibration = True
        for sim in self.sequence:
            self.city_size.append(sim["config"]["city_size"])
            self.time_blocks.append(sim["config"]["time_blocks"])
            self.request_rate.append(sim["config"]["base_demand"])
            self.inhomogeneity.append(sim["config"]["inhomogeneity"])
            self.min_trip_distance.append(sim["config"]["min_trip_distance"])
            self.max_trip_distance.append(sim["config"]["max_trip_distance"])
            self.idle_vehicles_moving.append(sim["config"]["idle_vehicles_moving"])
            self.results_window.append(sim["config"]["results_window"])
            if self.equilibration:
                self.reservation_wage.append(
                    sim["config"]["equilibration"]["reservation_wage"]
                )
            self.vehicle_count.append(sim["config"]["vehicle_count"])
            self.p1.append(sim["end_state"]["vehicle_fraction_p1"])
            self.p2.append(sim["end_state"]["vehicle_fraction_p2"])
            self.p3.append(sim["end_state"]["vehicle_fraction_p3"])
            self.mean_vehicle_count.append(sim["end_state"]["mean_vehicle_count"])
            self.trip_wait_fraction.append(
                sim["end_state"]["mean_trip_wait_time"]
                / (
                    sim["end_state"]["mean_trip_wait_time"]
                    + sim["end_state"]["mean_trip_distance"]
                )
            )
            self.trip_wait_time.append(
                sim["end_state"]["mean_trip_wait_time"]
                / sim["end_state"]["mean_trip_distance"]
            )
            self.trip_distance.append(
                sim["end_state"]["mean_trip_distance"] / self.city_size[0]
            )
        return ()

    def set_x_axis(self):
        """
        Identify the x axis.
        It is currently either vehicle counts, or request rates, depending
        on the simulation sequence run.
        """
        # set removes the duplicates from a list
        if len(set(self.vehicle_count)) > 1:
            self.x_axis = PlotXAxis.VEHICLE_COUNT
            x = self.vehicle_count
            self.x_label = "Vehicles"
            self.caption = (
                f"City size: {self.city_size[0]}\n"
                f"Demand: {self.request_rate[0]} requests/block\n"
                f"Trip length: "
                f"[{self.min_trip_distance[0]}, {self.max_trip_distance[0]}]\n"
                f"Inhomogeneity: {self.inhomogeneity[0]}\n"
                f"Idle vehicles moving: {self.idle_vehicles_moving[0]}\n"
                f"Results window: {self.results_window[0]} blocks\n"
                f"Simulation time: {self.time_blocks[0]} blocks\n"
            )
        if len(set(self.inhomogeneity)) > 1:
            self.x_axis = PlotXAxis.INHOMOGENEITY
            x = self.inhomogeneity
            self.x_label = "Inhomogeneity"
            self.caption = (
                f"City size: {self.city_size[0]}\n"
                f"Vehicle count: {self.vehicle_count[0]}\n"
                f"Demand: {self.request_rate[0]} requests/block\n"
                f"Trip length: "
                f"[{self.min_trip_distance[0]}, {self.max_trip_distance[0]}]\n"
                f"Idle vehicles moving: {self.idle_vehicles_moving[0]}\n"
                f"Results window: {self.results_window[0]} blocks\n"
                f"Simulation time: {self.time_blocks[0]} blocks\n"
            )
        if len(set(self.request_rate)) > 1:
            self.x_axis = PlotXAxis.REQUEST_RATE
            x = self.request_rate
            self.x_label = "Requests per block"
            if self.equilibration:
                self.caption = (
                    f"City size: {self.city_size[0]}\n"
                    f"Reserved wage: {self.reservation_wage[0]:.2f}/block\n"
                    f"Trip length: "
                    f"[{self.min_trip_distance[0]}, "
                    f"{self.max_trip_distance[0]}]\n"
                    f"Inhomogeneity: {self.inhomogeneity[0]}\n"
                    f"Idle vehicles moving: {self.idle_vehicles_moving[0]}\n"
                    f"Results window: {self.results_window[0]} blocks\n"
                    f"Simulation time: {datetime.now().strftime('%Y-%m-%d')}"
                )
            else:
                self.caption = (
                    f"City size: {self.city_size[0]}\n"
                    f"Vehicle count: {self.vehicle_count[0]}\n"
                    f"Trip length: "
                    f"[{self.min_trip_distance[0]}, "
                    f"{self.max_trip_distance[0]}]\n"
                    f"Inhomogeneity: {self.inhomogeneity[0]}\n"
                    f"Idle vehicles moving: {self.idle_vehicles_moving[0]}\n"
                    f"Results window: {self.results_window[0]} blocks\n"
                    f"Simulation time: {datetime.now().strftime('%Y-%m-%d')}"
                )
        return x

    def fit_line_series(self, x=[], y=[], fitter=None, p0=None):
        try:
            popt, _ = curve_fit(fitter, x, y, p0=p0, maxfev=2000)
            y_best_fit_line = [fitter(xval, *popt) for xval in x]
        except Exception:
            logging.warning("Curve fit failed")
            y_best_fit_line = []
        return y_best_fit_line

    def fit_range(self):
        """
        The plots include fitted lines over those simulations with a
        steady-state. That is, all those with some number of idle vehicles:
        self.p1[i] > 0. This function assumes it is a contiguous range.
        """
        steady_state_indexes = [index for index, p1 in enumerate(self.p1) if p1 > 0.05]
        if len(steady_state_indexes) > 0:
            ix = [min(steady_state_indexes), max(steady_state_indexes)]
        else:
            ix = [None, None]
        return ix

    def fit_lines(
        self,
        x,
        ix_lower=None,
        ix_upper=None,
        plot_x_axis=None,
        arrays=None,
        labels=None,
    ):
        """
        """
        best_fit_lines = []
        for i, y in enumerate(arrays):
            if labels[i] == "Trip length fraction":
                # trip distance
                p0_a = 1.0
                p0_b = 1.0
                p0 = (p0_a, p0_b)
                popt = np.polyfit(
                    x[ix_lower : ix_upper + 1], y[ix_lower : ix_upper + 1], 1
                )
                best_fit_lines.append(np.polyval(popt, x[ix_lower : ix_upper + 1]))
            elif labels[i] == "Mean vehicle count":
                # Vehicle count (for request_rate plot)
                p0_a = 1.0
                p0_b = 1.0
                p0 = (p0_a, p0_b)
                y = [0.9 * mvc / max(y) for mvc in y]
                popt = np.polyfit(
                    x[ix_lower : ix_upper + 1], y[ix_lower : ix_upper + 1], 1
                )
                best_fit_lines.append(np.polyval(popt, x[ix_lower : ix_upper + 1]))
            elif self.x_axis == PlotXAxis.INHOMOGENEITY:
                # Vehicle count (for request_rate plot)
                p0_a = y[ix_lower]
                p0_b = y[ix_lower] * x[ix_lower]
                p0_c = 0
                p0 = (p0_a, p0_b, p0_c)
                best_fit_lines.append(
                    self.fit_line_series(
                        x=x[ix_lower : ix_upper + 1],
                        y=y[ix_lower : ix_upper + 1],
                        fitter=fit_degree_two,
                        p0=p0,
                    )
                )
            else:
                p0_a = y[ix_lower]
                p0_b = y[ix_lower] * x[ix_lower]
                p0_c = 0
                p0 = (p0_a, p0_b, p0_c)
                best_fit_lines.append(
                    self.fit_line_series(
                        x=x[ix_lower : ix_upper + 1],
                        y=y[ix_lower : ix_upper + 1],
                        fitter=fit_degree_minus_one,
                        p0=p0,
                    )
                )

        return best_fit_lines

    def plot_points_series(self, ax, palette, x, y, index, label):
        if label.startswith("Vehicle"):
            marker = "o"
            markersize = 8
            alpha = 0.8
            fillstyle = "full"
        else:
            marker = "o"
            markersize = 8
            alpha = 0.6
            fillstyle = "full"
        (line,) = ax.plot(
            x,
            y,
            color=palette[index],
            marker=marker,
            markersize=markersize,
            alpha=alpha,
            fillstyle=fillstyle,
            lw=0,
            label=label,
        )

    def plot_points(self, ax, x, palette, arrays, labels):
        # Plot text for at most five points to avoid clutter
        MAX_TEXT_POINTS = 5
        for i, y in enumerate(arrays):
            if labels[i] == "Mean vehicle count":
                y_mod = [0.9 * mvc / max(y) for mvc in y]
                self.plot_points_series(ax, palette, x, y_mod, i, labels[i])
                for i2, x_val in enumerate(x):
                    if i2 % int((len(x) + 1) / MAX_TEXT_POINTS) == 0:
                        ax.text(
                            x_val,
                            y_mod[i2] + 0.02,
                            int(self.mean_vehicle_count[i2]),
                            fontsize="x-small",
                            ha="center",
                            va="center",
                        )
            else:
                self.plot_points_series(ax, palette, x, y, i, labels[i])

    def plot_fit_line_series(self, ax, palette, x, y, palette_index, label):
        line_style = "dashed"
        line_width = 2
        if label.startswith("Vehicle"):
            line_style = "solid"
            line_width = 2
        if len(x) == len(y):
            (line,) = ax.plot(
                x,
                y,
                color=palette[palette_index],
                alpha=0.8,
                lw=line_width,
                ls=line_style,
            )
        else:
            logging.warning(
                "Incompatible coordinate arrays: " f"lengths {len(x)} and {len(y)}"
            )

    def plot_best_fit_lines(
        self, ax, x, best_fit_lines, labels, ix_lower, ix_upper, palette
    ):
        # PLOTTING
        for i, y in enumerate(best_fit_lines):
            if labels[i] == "Mean vehicle count":
                y_mod = [0.9 * mvc / max(y) for mvc in y]
                self.plot_fit_line_series(ax, palette, x, y_mod, i, labels[i])
            else:
                self.plot_fit_line_series(
                    ax, palette, x[ix_lower : ix_upper + 1], y, i, labels[i]
                )

    def draw_plot(self, ax):
        caption_location = "upper center"
        caption_location = "upper left"
        anchor_props = {"fontsize": 11, "family": ["sans-serif"], "linespacing": 2.0}
        anchored_text = offsetbox.AnchoredText(
            self.caption,
            loc=caption_location,
            bbox_to_anchor=(1.0, 1.0),
            bbox_transform=ax.transAxes,
            frameon=False,
            prop=anchor_props,
        )
        ax.add_artist(anchored_text)
        ax.grid(
            visible=True,
            which="major",
            axis="both",
            # color="black",
            linewidth="2",
        )
        ax.grid(
            visible=True,
            which="minor",
            axis="both",
            # color="white",
            linewidth="1",
        )
        # Minor ticks
        ax.set_ylim(bottom=0, top=1)
        ax.tick_params(which="minor", bottom=False, left=False)
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(4))
        ax.minorticks_on()
        ax.set_xlabel(self.x_label)
        ax.set_ylabel("Fraction")
        if "title" in self.sequence[0]["config"]:
            title = [sim["config"]["title"] for sim in self.sequence][0]
        else:
            title = (
                "Ridehail simulation sequence: "
                f"city size = {self.city_size}, "
                f"request rate = {self.request_rate}, "
            )
        ax.set_title(title)
        # TODO: labels are associated with fitted lines. The legend fails
        # if there is no line fit. Add labels to the points instead!
        ax.legend()
        plt.tight_layout()

        filename_root = os.path.splitext(os.path.basename(self.input_file))[0]
        file_path = f"img/{filename_root}.png"
        plt.savefig(file_path)
        print(f"Chart saved as {file_path}")


def main():
    try:
        if os.path.isfile(sys.argv[1]):
            input_file = sys.argv[1]
    except FileNotFoundError:
        print(
            "Usage:\n\tpython rhplotsequence.py <jsonl_file>"
            "\n\n\twhere <jsonl_file> is the output from a run of ridehail.py"
            "\n\twith run_sequence=True"
        )
        exit(-1)
    plot = Plot(input_file)

    # Only fit for steady state solutions, where p1 > 0
    fig, ax = plt.subplots(ncols=1, figsize=(16, 8))
    # fig, ax = plt.subplots(ncols=1, figsize=(14, 8), constrained_layout=True)
    palette = sns.color_palette()
    plot.construct_arrays()
    x = plot.set_x_axis()
    if plot.x_axis == PlotXAxis.VEHICLE_COUNT:
        arrays = [
            plot.p1,
            plot.p2,
            plot.p3,  # plot.trip_wait_fraction,
            plot.trip_wait_time,
            # plot.trip_distance
        ]
        labels = [
            "Vehicle idle (p1)",
            "Vehicle en route (p2)",
            "Vehicle with rider (p3)",  # "Trip wait fraction",
            "Trip wait time (fraction)",
            # "Trip length fraction"
        ]
    elif plot.x_axis == PlotXAxis.REQUEST_RATE:
        arrays = [
            plot.p1,
            plot.p2,
            plot.p3,  # plot.trip_wait_fraction,
            plot.trip_wait_time,
            # plot.trip_distance,
            plot.mean_vehicle_count,
        ]
        labels = [
            "Vehicle idle (p1)",
            "Vehicle en route (p2)",
            "Vehicle with rider (p3)",  # "Trip wait fraction",
            "Trip wait time (fraction)",
            "Mean vehicle count",
        ]
    elif plot.x_axis == PlotXAxis.INHOMOGENEITY:
        arrays = [
            plot.p1,
            plot.p2,
            plot.p3,  # plot.trip_wait_fraction,
            plot.trip_wait_time,
            # plot.trip_distance
        ]
        labels = [
            "Vehicle idle (p1)",
            "Vehicle en route (p2)",
            "Vehicle with rider (p3)",  # "Trip wait fraction",
            "Trip wait time (fraction)",
            # "Trip length fraction"
        ]
    plot.plot_points(ax, x, palette, arrays, labels)
    [ix_lower, ix_upper] = plot.fit_range()
    if ix_lower is not None:
        best_fit_lines = plot.fit_lines(
            x, ix_lower, ix_upper, arrays=arrays, labels=labels
        )
        plot.plot_best_fit_lines(
            ax, x, best_fit_lines, labels, ix_lower, ix_upper, palette
        )
    plot.draw_plot(ax)


if __name__ == "__main__":
    main()
