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
    logging.info(f"fit_linear: x={x}, a={a}, b={b}")
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
        self.y1 = []
        self.y2 = []
        self.y3 = []
        self.y4 = []
        self.y5 = []
        for sim in self.sequence:
            logging.info(f'sim={sim}')
            logging.info(f'sim["config"]={sim["config"]}')
            self.trip_inhomogeneity.append(sim["config"]["trip_inhomogeneity"])
            self.min_trip_distance.append(sim["config"]["min_trip_distance"])
            self.max_trip_distance.append(sim["config"]["max_trip_distance"])
            self.idle_vehicles_moving.append(sim["config"]["idle_vehicles_moving"])
            self.results_window.append(sim["config"]["results_window"])
            if sim["config"]["base_demand"] == rate:
                self.vehicle_count.append(sim["config"]["vehicle_count"])
                self.y1.append(sim["results"]["vehicle_fraction_idle"])
                self.y2.append(sim["results"]["vehicle_fraction_picking_up"])
                self.y3.append(sim["results"]["vehicle_fraction_with_rider"])
                self.y4.append(sim["results"]["mean_trip_wait_time"] /
                               (sim["results"]["mean_trip_wait_time"] +
                                sim["results"]["mean_trip_distance"]))
                self.y5.append(sim["results"]["mean_trip_distance"] / self.city_size)
        self.z = zip(self.vehicle_count, self.y1, self.y2, self.y3, self.y4, self.y5)
        return()

    def construct_plot_arrays(self, rate):
        z_fit = [zval for zval in self.z if zval[1] > 0.05]
        if len(z_fit) > 0:
            (self.vehicle_count_fit, y1_fit, y2_fit, y3_fit, y4_fit, y5_fit) = zip(*z_fit)
        p0_a = y1_fit[-1]
        p0_b = y1_fit[0] * self.vehicle_count_fit[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        try:
            popt, _ = curve_fit(fit_function,
                                self.vehicle_count_fit,
                                y1_fit,
                                p0=p0,
                                maxfev=2000)
            self.y1_plot = [fit_function(xval, *popt) for xval in
                            self.vehicle_count_fit]
        except Exception:
            logging.warning("Curve fit failed for y1")
            self.y1_plot = []
        p0_a = y2_fit[-1]
        p0_b = y2_fit[0] * self.vehicle_count_fit[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        try:
            popt, _ = curve_fit(fit_function,
                                self.vehicle_count_fit,
                                y2_fit,
                                p0=p0,
                                maxfev=2000)
            self.y2_plot = [fit_function(xval, *popt) for xval in
                            self.vehicle_count_fit]
        except Exception:
            self.y2_plot = []
            logging.warning("Curve fit failed for y2")
        p0_a = y3_fit[-1]
        p0_b = y3_fit[0] * self.vehicle_count[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        try:
            popt, _ = curve_fit(fit_function,
                                self.vehicle_count_fit,
                                y3_fit,
                                p0=p0,
                                maxfev=2000)
            self.y3_plot = [fit_function(xval, *popt) for xval in
                            self.vehicle_count_fit]
        except Exception:
            self.y3_plot = []
            logging.warning("Curve fit failed for y3")

        p0_a = y4_fit[-1]
        p0_b = y4_fit[0] * self.vehicle_count_fit[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        try:
            popt, _ = curve_fit(fit_function,
                                self.vehicle_count_fit,
                                y4_fit,
                                p0=p0,
                                maxfev=2000)
            self.y4_plot = [fit_function(xval, *popt) for xval in
                            self.vehicle_count_fit]
        except Exception:
            self.y4_plot = []
            logging.warning("Curve fit failed for y4")

        p0_a = 1.
        p0_b = 1.
        p0 = (p0_a, p0_b)
        logging.info(f"y5_fit={y5_fit}")
        popt = np.polyfit(self.vehicle_count_fit, y5_fit, 1)
        self.y5_plot = np.polyval(popt, self.vehicle_count)

    def draw_plot(self, rate):
        # PLOTTING
        fig, ax = plt.subplots(ncols=1, figsize=(14, 8))
        palette = sns.color_palette()
        line_style = "solid"
        palette_index = 0
        line, = ax.plot(
            self.vehicle_count,
            self.y1,
            color=palette[palette_index],
            alpha=0.8,
            marker="o",
            markersize=8,
            lw=0,
        )
        if len(self.vehicle_count_fit) == len(self.y1_plot):
            line, = ax.plot(
                self.vehicle_count_fit,
                self.y1_plot,
                color=palette[palette_index],
                alpha=0.8,
                lw=2,
                ls=line_style,
            )
        if rate <= min(self.request_rates):
            line.set_label("Vehicle idle (p1)")
        palette_index += 1
        line, = ax.plot(
            self.vehicle_count,
            self.y2,
            color=palette[palette_index],
            alpha=0.8,
            lw=0,
            marker="o",
            markersize=8,
        )
        if len(self.vehicle_count_fit) == len(self.y2_plot):
            line, = ax.plot(self.vehicle_count_fit,
                            self.y2_plot,
                            color=palette[palette_index],
                            alpha=0.8,
                            lw=2,
                            ls=line_style)
        if rate <= min(self.request_rates):
            line.set_label("Vehicle dispatch (p2)")
        palette_index += 1
        line, = ax.plot(
            self.vehicle_count,
            self.y3,
            color=palette[palette_index],
            alpha=0.8,
            lw=0,
            marker="o",
            markersize=8,
        )
        if len(self.vehicle_count_fit) == len(self.y3_plot):
            line, = ax.plot(
                self.vehicle_count_fit,
                self.y3_plot,
                color=palette[palette_index],
                alpha=0.8,
                lw=2,
                ls=line_style,
            )
        if rate <= min(self.request_rates):
            line.set_label("Vehicle with rider (p3)")
        palette_index += 1
        line, = ax.plot(
            self.vehicle_count,
            self.y4,
            color=palette[palette_index],
            alpha=0.8,
            lw=0,
            marker="o",
            markersize=8,
        )
        if len(self.vehicle_count_fit) == len(self.y4_plot):
            line, = ax.plot(
                self.vehicle_count_fit,
                self.y4_plot,
                color=palette[palette_index],
                alpha=0.8,
                lw=2,
                ls="dashed",
            )
        if rate <= min(self.request_rates):
            line.set_label("Trip wait time (fraction)")
        palette_index += 1
        line, = ax.plot(
            self.vehicle_count,
            self.y5,
            color=palette[palette_index],
            alpha=0.6,
            lw=0,
            # ls="dotted",
            marker="s",
            markersize=4,
        )
        if len(self.vehicle_count) == len(self.y5_plot):
            line, = ax.plot(
                self.vehicle_count,
                self.y5_plot,
                color=palette[palette_index],
                alpha=0.6,
                lw=1,
                ls="dashed",
            )
        if rate <= min(self.request_rates):
            line.set_label("Mean trip length (fraction)")
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
        plot.construct_plot_arrays(rate)
        plot.draw_plot(rate)

if __name__ == '__main__':
    main()
