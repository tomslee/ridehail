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
    request_rates = []
    p1_plot = []

    def __init__(self, input_file):
        self.input_file = input_file
        with open(input_file) as f:
            lines = f.readlines()
        for line in lines:
            self.sequence.append(json.loads(line))
        self.request_rates = list(set([
            sim["config"]["base_demand"] for sim in self.sequence if "config" in sim
        ]))

    def construct_arrays(self, rate):
        self.city_size = [sim["config"]["city_size"] for sim in self.sequence][0]
        self.request_rate = [sim["config"]["base_demand"] for sim in self.sequence][0]
        self.time_blocks = [sim["config"]["time_blocks"] for sim in self.sequence][0]
        self.trip_inhomogeneity = []
        self.min_trip_distance = []
        self.max_trip_distance = []
        self.idle_vehicles_moving = []
        self.results_window = []
        self.vehicle_count = []
        self.p1 = []
        self.p2 = []
        self.p3 = []
        self.wait = []
        self.trip_distance = []
        for sim in self.sequence:
            self.trip_inhomogeneity.append(sim["config"]["trip_inhomogeneity"])
            self.min_trip_distance.append(sim["config"]["min_trip_distance"])
            self.max_trip_distance.append(sim["config"]["max_trip_distance"])
            self.idle_vehicles_moving.append(sim["config"]["idle_vehicles_moving"])
            self.results_window.append(sim["config"]["results_window"])
            if sim["config"]["base_demand"] == rate:
                self.vehicle_count.append(sim["config"]["vehicle_count"])
                self.p1.append(sim["results"]["vehicle_fraction_idle"])
                self.p2.append(sim["results"]["vehicle_fraction_picking_up"])
                self.p3.append(sim["results"]["vehicle_fraction_with_rider"])
                self.wait.append(sim["results"]["mean_trip_wait_time"] /
                               (sim["results"]["mean_trip_wait_time"] +
                                sim["results"]["mean_trip_distance"]))
                self.trip_distance.append(sim["results"]["mean_trip_distance"] / self.city_size)
        return()

    def fit_line_series(self, x=[], y=[], fitter=None, p0=None):
        try:
            popt, _ = curve_fit(fitter,
                                x,
                                y,
                                p0=p0,
                                maxfev=2000)
            y_plot = [fitter(xval, *popt) for xval in x]
        except Exception:
            logging.warning("Curve fit failed")
            y_plot = []
        return y_plot

    def fit_lines(self):
        z = zip(self.vehicle_count, self.p1, self.p2, self.p3, self.wait,
                     self.trip_distance)
        z_fit = [zval for zval in z if zval[1] > 0.05]
        if len(z_fit) > 0:
            (x_fit, p1_fit, p2_fit, p3_fit, wait_fit,
             trip_distance_fit) = zip(*z_fit)
        else:
            pass
        p0_a = p1_fit[-1]
        p0_b = p1_fit[0] * self.vehicle_count[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        self.p1_plot = self.fit_line_series(x=x_fit,
                                            y=p1_fit,
                                            fitter=fit_function,
                                            p0=p0)
        p0_a = p2_fit[-1]
        p0_b = p2_fit[0] * self.vehicle_count[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        self.p2_plot = self.fit_line_series(x=x_fit,
                                            y=p2_fit,
                                            fitter=fit_function,
                                            p0=p0)
        p0_a = p3_fit[-1]
        p0_b = p3_fit[0] * self.vehicle_count[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        self.p3_plot = self.fit_line_series(x=x_fit,
                                            y=p3_fit,
                                            fitter=fit_function,
                                            p0=p0)
        p0_a = wait_fit[-1]
        p0_b = wait_fit[0] * x_fit[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        self.wait_plot = self.fit_line_series(x=x_fit,
                                            y=wait_fit,
                                            fitter=fit_function,
                                            p0=p0)
        p0_a = 1.
        p0_b = 1.
        p0 = (p0_a, p0_b)
        popt = np.polyfit(x_fit, trip_distance_fit, 1)
        self.trip_distance_plot = np.polyval(popt, x_fit)
        return x_fit

    def draw_plot_points_series(self, ax, palette, x, y, index):
        line, = ax.plot(
            x,
            y,
            color=palette[index],
            alpha=0.8,
            marker="o",
            markersize=8,
            lw=0,
        )

    def draw_plot_points(self, ax, x, palette):
        palette_index = 0
        self.draw_plot_points_series(ax, palette, x, self.p1,
                                     palette_index)
        palette_index += 1
        self.draw_plot_points_series(ax, palette, x, self.p2,
                                     palette_index)
        palette_index += 1
        self.draw_plot_points_series(ax, palette, x, self.p3,
                                     palette_index)
        palette_index += 1
        self.draw_plot_points_series(ax, palette, x, self.wait,
                                     palette_index)
        palette_index += 1
        self.draw_plot_points_series(ax, palette, x, self.trip_distance,
                                     palette_index)

    def draw_plot_fit_line_series(self, ax, palette, x, y, palette_index, label):
        line_style = "dashed"
        line_width = 2
        if label.startswith("Vehicle"):
            line_style = "solid"
        if label.startswith("Trip length"):
            line_width = 1
        if len(x) == len(y):
            line, = ax.plot(
                    x,
                    y,
                    color=palette[palette_index],
                    alpha=0.8,
                    lw=line_width,
                    ls=line_style,
                    label=label
                )
        else:
            logging.warning("Incompatible coordinate arrays: "
                            f"lengths {len(x)} and {len(y)}")

    def draw_plot_fit_lines(self, rate, ax, x, palette):
        # PLOTTING
        line_style="solid"
        palette_index = 0
        label="Vehicle idle (p1)"
        self.draw_plot_fit_line_series(ax, palette, x,
                                       self.p1_plot, palette_index, label)
        palette_index += 1
        label="Vehicle dispatch (p2)"
        self.draw_plot_fit_line_series(ax, palette, x,
                                       self.p2_plot, palette_index, label)
        palette_index += 1
        label="Vehicle with rider (p3)"
        self.draw_plot_fit_line_series(ax, palette, x,
                                       self.p3_plot, palette_index, label)
        palette_index += 1
        label="Trip wait fraction"
        self.draw_plot_fit_line_series(ax, palette, x,
                                       self.wait_plot, palette_index, label)
        palette_index += 1
        label="Trip length fraction"
        self.draw_plot_fit_line_series(ax, palette, x,
                                       self.trip_distance_plot, palette_index, label)
        caption = (f"City size: {self.city_size}\n"
                   f"Request rate: {self.request_rate} per block\n"
                   f"Trip length: [{self.min_trip_distance[0]}, {self.max_trip_distance[0]}]\n"
                   f"Trip inhomogeneity: {self.trip_inhomogeneity[0]}\n"
                   f"Idle vehicles moving: {self.idle_vehicles_moving[0]}\n"
                   f"Simulation time: {self.time_blocks} blocks\n"
                   f"Results window: {self.results_window[0]} blocks\n"
                   f"Simulation run on {datetime.now().strftime('%Y-%m-%d')}")
        anchor_props = {
            # 'bbox': {
            # 'facecolor': '#EAEAF2',
            # 'edgecolor': 'silver',
            # 'pad': 5,
            # },
            'fontsize': 11,
            'family': ['sans-serif'],
            # 'sans-serif': [
            # 'Arial', 'DejaVu Sans', 'Liberation Sans', 'Bitstream Vera Sans',
            # 'sans-serif'
            # ],
            'linespacing': 2.0
        }
        caption_location = "upper center"
        caption_location = "upper left"
        anchored_text = offsetbox.AnchoredText(caption,
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
        ax.set_xlabel("Vehicles")
        ax.set_ylabel("Fraction")
        if "title" in self.sequence[0]["config"]:
            title = [sim["config"]["title"] for sim in self.sequence][0]
        else:
            title = ("Ridehail simulation sequence: "
                     f"city size = {self.city_size}, "
                     f"request rate = {self.request_rate}, ")
        ax.set_title(title)
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
            filename_root = os.path.splitext(os.path.basename(input_file))[0]
    except FileNotFoundError:
        print(
            "Usage:\n\tpython rhplotsequence.py <jsonl_file>"
            "\n\n\twhere <jsonl_file> is the output from a run of ridehail.py"
            "\n\twith run_sequence=True")
        exit(-1)
    plot = Plot(input_file)



    # Only fit for steady state solutions, where p1 > 0
    for rate in plot.request_rates:
        plot.construct_arrays(rate)
        vehicle_count_fit = plot.fit_lines()
        fig, ax = plt.subplots(ncols=1, figsize=(14, 8))
        palette = sns.color_palette()
        plot.draw_plot_points(ax, plot.vehicle_count, palette)
        plot.draw_plot_fit_lines(rate, ax, vehicle_count_fit, palette)

if __name__ == '__main__':
    main()
