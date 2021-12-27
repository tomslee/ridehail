#!/usr/bin/python3

import sys
import os
import json
import matplotlib.pyplot as plt
import matplotlib as mpl
import logging
import math
from matplotlib import offsetbox
from matplotlib.ticker import AutoMinorLocator
import seaborn as sns
from datetime import datetime
from scipy.optimize import curve_fit
import numpy as np

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
mpl.rcParams['figure.dpi'] = 90
mpl.rcParams['savefig.dpi'] = 100
sns.set()
sns.set_palette("muted")
# sns.set_palette("deep")


def fit_function(x, a, b, c):
    return (a + b / (x + c))


def fit_linear(x, a, b):
    return (a * x + b)


def residual_linear(p, x, y):
    return (y - fit_linear(x, *p))


def fit_function_wait(x, a, b, c):
    """ I think this goes as the square root.
    Not in use at the moment as it fails to converge."""
    return (a + b / (math.sqrt(x) + c))


class Plot():

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
        self.trip_inhomogeneity = []
        self.min_trip_distance = []
        self.max_trip_distance = []
        self.idle_vehicles_moving = []
        self.results_window = []
        self.reserved_wage = []
        self.vehicle_count = []
        self.p1 = []
        self.p2 = []
        self.p3 = []
        self.mean_vehicle_count = []
        self.wait = []
        self.trip_distance = []
        for sim in self.sequence:
            self.city_size.append(sim["config"]["city_size"])
            self.time_blocks.append(sim["config"]["time_blocks"])
            self.request_rate.append(sim["config"]["base_demand"])
            self.trip_inhomogeneity.append(sim["config"]["trip_inhomogeneity"])
            self.min_trip_distance.append(sim["config"]["min_trip_distance"])
            self.max_trip_distance.append(sim["config"]["max_trip_distance"])
            self.idle_vehicles_moving.append(
                sim["config"]["idle_vehicles_moving"])
            self.results_window.append(sim["config"]["results_window"])
            if "equilibration" in sim["config"]:
                self.reserved_wage.append(
                    sim["config"]["equilibration"]["reserved_wage"])
            self.vehicle_count.append(sim["config"]["vehicle_count"])
            self.p1.append(sim["results"]["vehicle_fraction_idle"])
            self.p2.append(sim["results"]["vehicle_fraction_picking_up"])
            self.p3.append(sim["results"]["vehicle_fraction_with_rider"])
            self.mean_vehicle_count.append(
                sim["results"]["mean_vehicle_count"])
            self.wait.append(sim["results"]["mean_trip_wait_time"] /
                             (sim["results"]["mean_trip_wait_time"] +
                              sim["results"]["mean_trip_distance"]))
            self.trip_distance.append(sim["results"]["mean_trip_distance"] /
                                      self.city_size[0])
        return ()

    def set_x_axis(self):
        """
        Identify the x axis.
        It is currently either vehicle counts, or request rates, depending
        on the simulation sequence run.
        """
        # set removes the duplicates from a list
        if len(set(self.vehicle_count)) > 1:
            self.x_axis = "vehicle_count"
            x = self.vehicle_count
            self.x_label = "Vehicles"
            self.caption = (
                f"City size: {self.city_size[0]}\n"
                f"Request rate: {self.request_rate[0]} per block\n"
                f"Trip length: "
                f"[{self.min_trip_distance[0]}, {self.max_trip_distance[0]}]\n"
                f"Trip inhomogeneity: {self.trip_inhomogeneity[0]}\n"
                f"Idle vehicles moving: {self.idle_vehicles_moving[0]}\n"
                f"Simulation time: {self.time_blocks[0]} blocks\n"
                f"Results window: {self.results_window[0]} blocks\n")
        if len(set(self.request_rate)) > 1:
            self.x_axis = "request_rate"
            x = self.request_rate
            self.x_label = "Requests per block"
            self.caption = (
                f"City size: {self.city_size[0]}\n"
                f"Reserved wage: {self.reserved_wage[0]} per block\n"
                f"Trip length: "
                f"[{self.min_trip_distance[0]}, {self.max_trip_distance[0]}]\n"
                f"Trip inhomogeneity: {self.trip_inhomogeneity[0]}\n"
                f"Idle vehicles moving: {self.idle_vehicles_moving[0]}\n"
                f"Simulation time: {self.time_blocks[0]} blocks\n"
                f"Results window: {self.results_window[0]} blocks\n"
                f"Simulation run on {datetime.now().strftime('%Y-%m-%d')}")
        return x

    def fit_line_series(self, x=[], y=[], fitter=None, p0=None):
        try:
            popt, _ = curve_fit(fitter, x, y, p0=p0, maxfev=2000)
            y_plot = [fitter(xval, *popt) for xval in x]
        except Exception:
            logging.warning("Curve fit failed")
            y_plot = []
        return y_plot

    def fit_range(self):
        """
        The plots include fitted lines over those simulations with a
        steady-state. That is, all those with some number of idle vehicles:
        self.p1[i] > 0. This function assumes it is a contiguous range.
        """
        steady_state_indexes = [
            index for index, p1 in enumerate(self.p1) if p1 > 0.05
        ]
        if len(steady_state_indexes) > 0:
            ix = [min(steady_state_indexes), max(steady_state_indexes)]
        else:
            ix = [None, None]
        return ix

    def fit_lines(self, x, ix_lower=None, ix_upper=None):
        """
        """
        p0_a = self.p1[ix_lower]
        p0_b = self.p1[ix_lower] * x[ix_lower]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        self.p1_plot = self.fit_line_series(x=x[ix_lower:ix_upper + 1],
                                            y=self.p1[ix_lower:ix_upper + 1],
                                            fitter=fit_function,
                                            p0=p0)
        p0_a = self.p2[ix_upper]
        p0_b = self.p2[ix_lower] * x[ix_lower]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        self.p2_plot = self.fit_line_series(x=x[ix_lower:ix_upper + 1],
                                            y=self.p2[ix_lower:ix_upper + 1],
                                            fitter=fit_function,
                                            p0=p0)
        p0_a = self.p3[ix_upper]
        p0_b = self.p3[ix_lower] * x[ix_lower]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        self.p3_plot = self.fit_line_series(x=x[ix_lower:ix_upper + 1],
                                            y=self.p3[ix_lower:ix_upper + 1],
                                            fitter=fit_function,
                                            p0=p0)
        p0_a = self.wait[ix_upper]
        p0_b = self.wait[ix_lower] * x[ix_lower]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        self.wait_plot = self.fit_line_series(x=x[ix_lower:ix_upper + 1],
                                              y=self.wait,
                                              fitter=fit_function,
                                              p0=p0)
        # trip distance
        p0_a = 1.
        p0_b = 1.
        p0 = (p0_a, p0_b)
        popt = np.polyfit(x[ix_lower:ix_upper + 1],
                          self.trip_distance[ix_lower:ix_upper + 1], 1)
        self.trip_distance_plot = np.polyval(popt, x[ix_lower:ix_upper + 1])
        # Vehicle count (for request_rate plot)
        if self.x_axis == "request_rate":
            p0_a = 1.
            p0_b = 1.
            p0 = (p0_a, p0_b)
            y = [
                0.9 * mvc / max(self.mean_vehicle_count)
                for mvc in self.mean_vehicle_count
            ]
            popt = np.polyfit(x[ix_lower:ix_upper + 1],
                              y[ix_lower:ix_upper + 1], 1)
            self.vehicle_count_plot = np.polyval(popt,
                                                 x[ix_lower:ix_upper + 1])

    def plot_points_series(self, ax, palette, x, y, index):
        line, = ax.plot(
            x,
            y,
            color=palette[index],
            alpha=0.8,
            marker="o",
            markersize=6,
            lw=0,
        )

    def plot_points(self, ax, x, palette):
        palette_index = 0
        self.plot_points_series(ax, palette, x, self.p1, palette_index)
        palette_index += 1
        self.plot_points_series(ax, palette, x, self.p2, palette_index)
        palette_index += 1
        self.plot_points_series(ax, palette, x, self.p3, palette_index)
        palette_index += 1
        self.plot_points_series(ax, palette, x, self.wait, palette_index)
        palette_index += 1
        self.plot_points_series(ax, palette, x, self.trip_distance,
                                palette_index)
        if self.x_axis == "request_rate":
            palette_index += 1
            y = [
                0.9 * mvc / max(self.mean_vehicle_count)
                for mvc in self.mean_vehicle_count
            ]
            self.plot_points_series(ax, palette, x, y, palette_index)
            ax.text(x[0] + (x[-1] - x[0]) / 50,
                    y[0],
                    int(self.mean_vehicle_count[0]),
                    ha="left",
                    va="center")
            ax.text(x[-1] - (x[-1] - x[0]) / 50,
                    y[-1],
                    int(self.mean_vehicle_count[-1]),
                    ha="right",
                    va="center")

    def plot_fit_line_series(self, ax, palette, x, y, palette_index, label):
        line_style = "dashed"
        line_width = 1
        if label.startswith("Vehicle"):
            line_style = "solid"
            line_width = 2
        if len(x) == len(y):
            line, = ax.plot(x,
                            y,
                            color=palette[palette_index],
                            alpha=0.8,
                            lw=line_width,
                            ls=line_style,
                            label=label)
        else:
            logging.warning("Incompatible coordinate arrays: "
                            f"lengths {len(x)} and {len(y)}")

    def plot_fit_lines(self, ax, x, palette):
        # PLOTTING
        palette_index = 0
        label = "Vehicle idle (p1)"
        self.plot_fit_line_series(ax, palette, x, self.p1_plot, palette_index,
                                  label)
        palette_index += 1
        label = "Vehicle dispatch (p2)"
        self.plot_fit_line_series(ax, palette, x, self.p2_plot, palette_index,
                                  label)
        palette_index += 1
        label = "Vehicle with rider (p3)"
        self.plot_fit_line_series(ax, palette, x, self.p3_plot, palette_index,
                                  label)
        palette_index += 1
        label = "Trip wait fraction"
        self.plot_fit_line_series(ax, palette, x, self.wait_plot,
                                  palette_index, label)
        palette_index += 1
        label = "Trip length fraction"
        self.plot_fit_line_series(ax, palette, x, self.trip_distance_plot,
                                  palette_index, label)
        if self.x_axis == "request_rate":
            palette_index += 1
            label = "Mean vehicle count"
            y = [
                0.9 * mvc / max(self.vehicle_count_plot)
                for mvc in self.vehicle_count_plot
            ]
            self.plot_fit_line_series(ax, palette, x, y, palette_index, label)

    def draw_plot(self, ax):
        caption_location = "upper center"
        caption_location = "upper left"
        anchor_props = {
            'fontsize': 11,
            'family': ['sans-serif'],
            'linespacing': 2.0
        }
        anchored_text = offsetbox.AnchoredText(self.caption,
                                               loc=caption_location,
                                               bbox_to_anchor=(1., 1.),
                                               bbox_transform=ax.transAxes,
                                               frameon=False,
                                               prop=anchor_props)
        ax.add_artist(anchored_text)
        ax.grid(
            visible=True,
            which="major",
            axis="both",
            # color="black",
            linewidth="2")
        ax.grid(
            visible=True,
            which="minor",
            axis="both",
            # color="white",
            linewidth="1")
        # Minor ticks
        ax.set_ylim(bottom=0, top=1)
        ax.tick_params(which='minor', bottom=False, left=False)
        ax.xaxis.set_minor_locator(AutoMinorLocator(2))
        ax.yaxis.set_minor_locator(AutoMinorLocator(4))
        ax.minorticks_on()
        ax.set_xlabel(self.x_label)
        ax.set_ylabel("Fraction")
        if "title" in self.sequence[0]["config"]:
            title = [sim["config"]["title"] for sim in self.sequence][0]
        else:
            title = ("Ridehail simulation sequence: "
                     f"city size = {self.city_size}, "
                     f"request rate = {self.request_rate}, ")
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
            "\n\twith run_sequence=True")
        exit(-1)
    plot = Plot(input_file)

    # Only fit for steady state solutions, where p1 > 0
    fig, ax = plt.subplots(ncols=1, figsize=(14, 8))
    palette = sns.color_palette()
    plot.construct_arrays()
    x = plot.set_x_axis()
    plot.plot_points(ax, x, palette)
    [ix_lower, ix_upper] = plot.fit_range()
    if ix_lower is not None:
        plot.fit_lines(x, ix_lower, ix_upper)
        plot.plot_fit_lines(ax, x[ix_lower:ix_upper + 1], palette)
    plot.draw_plot(ax)


if __name__ == '__main__':
    main()
