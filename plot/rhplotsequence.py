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

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(message)s')
mpl.rcParams['figure.dpi'] = 90
mpl.rcParams['savefig.dpi'] = 100
sns.set()
sns.set_palette("muted")
# sns.set_palette("deep")


def fit_function(x, a, b, c):
    return (a + b / (x + c))


def fit_function_wait(x, a, b, c):
    """ I think this goes as the square root.
    Not in use at the moment as it fails to converge."""
    return (a + b / (math.sqrt(x) + c))


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
    with open(input_file) as f:
        lines = f.readlines()

    sequence = []
    for line in lines:
        sequence.append(json.loads(line))

    request_rates = list(
        set([
            sim["config"]["base_demand"] for sim in sequence if "config" in sim
        ]))
    fig, ax = plt.subplots(ncols=1, figsize=(14, 8))
    palette = sns.color_palette()
    for rate in request_rates:
        city_size = [sim["config"]["city_size"] for sim in sequence][0]
        request_rate = [sim["config"]["base_demand"] for sim in sequence][0]
        time_blocks = [sim["config"]["time_blocks"] for sim in sequence][0]
        trip_inhomogeneity = [
            sim["config"]["trip_inhomogeneity"] for sim in sequence
        ][0]
        min_trip_distance = [
            sim["config"]["min_trip_distance"] for sim in sequence
        ][0]
        max_trip_distance = [
            sim["config"]["max_trip_distance"] for sim in sequence
        ][0]
        idle_vehicles_moving = [
            sim["config"]["idle_vehicles_moving"] for sim in sequence
        ][0]
        results_window = [sim["config"]["results_window"]
                          for sim in sequence][0]
        x = [
            sim["config"]["vehicle_count"] for sim in sequence
            if sim["config"]["base_demand"] == rate and "config" in sim
        ]
        print(f"x={x}")
        y1 = [
            sim["results"]["vehicle_fraction_idle"] for sim in sequence
            if sim["config"]["base_demand"] == rate
        ]
        print(f"y1={y1}")
        y2 = [
            sim["results"]["vehicle_fraction_picking_up"] for sim in sequence
            if sim["config"]["base_demand"] == rate
        ]
        y3 = [
            sim["results"]["vehicle_fraction_with_rider"] for sim in sequence
            if sim["config"]["base_demand"] == rate
        ]
        y4 = [
            sim["results"]["mean_trip_wait_time"] /
            (sim["results"]["mean_trip_wait_time"] +
             sim["results"]["mean_trip_distance"]) for sim in sequence
            if sim["config"]["base_demand"] == rate
        ]
        y5 = [(sim["results"]["mean_trip_distance"] / city_size)
              for sim in sequence if sim["config"]["base_demand"] == rate]
        z = zip(x, y1, y2, y3, y4, y5)
        # Only fit for steady state solutions, where p1 > 0
        z_fit = [zval for zval in z if zval[1] > 0.05]
        if len(z_fit) > 0:
            (x_fit, y1_fit, y2_fit, y3_fit, y4_fit, y5_fit) = zip(*z_fit)
        p0_a = y1_fit[-1]
        p0_b = y1_fit[0] * x_fit[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        try:
            popt, _ = curve_fit(fit_function,
                                x_fit,
                                y1_fit,
                                p0=p0,
                                maxfev=2000)
            y1_plot = [fit_function(xval, *popt) for xval in x_fit]
        except Exception:
            logging.warning("Curve fit failed for y1")
            y1_plot = []
        p0_a = y2_fit[-1]
        p0_b = y2_fit[0] * x_fit[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        try:
            popt, _ = curve_fit(fit_function,
                                x_fit,
                                y2_fit,
                                p0=p0,
                                maxfev=2000)
            y2_plot = [fit_function(xval, *popt) for xval in x_fit]
        except Exception:
            y2_plot = []
            logging.warning("Curve fit failed for y2")
        p0_a = y3_fit[-1]
        p0_b = y3_fit[0] * x[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        try:
            popt, _ = curve_fit(fit_function,
                                x_fit,
                                y3_fit,
                                p0=p0,
                                maxfev=2000)
            y3_plot = [fit_function(xval, *popt) for xval in x_fit]
        except Exception:
            y3_plot = []
            logging.warning("Curve fit failed for y3")
        p0_a = y4_fit[-1]
        p0_b = y4_fit[0] * x_fit[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        try:
            popt, _ = curve_fit(fit_function,
                                x_fit,
                                y4_fit,
                                p0=p0,
                                maxfev=2000)
            y4_plot = [fit_function(xval, *popt) for xval in x_fit]
        except Exception:
            y4_plot = []
            logging.warning("Curve fit failed for y4")
        line_style = "solid"
        palette_index = 0
        # line, = ax.plot(x_fit,
        # y1_plot,
        # color=palette[palette_index],
        # alpha=0.8,
        # lw=2,
        # ls=line_style)
        line, = ax.plot(
            x,
            y1,
            color=palette[palette_index],
            alpha=0.8,
            marker="o",
            markersize=8,
            lw=0,
        )
        if len(x_fit) == len(y1_plot):
            line, = ax.plot(
                x_fit,
                y1_plot,
                color=palette[palette_index],
                alpha=0.8,
                lw=2,
                ls=line_style,
            )
        if rate <= min(request_rates):
            line.set_label("Vehicle idle (p1)")
        palette_index += 1
        line, = ax.plot(
            x,
            y2,
            color=palette[palette_index],
            alpha=0.8,
            lw=0,
            marker="o",
            markersize=8,
        )
        if len(x_fit) == len(y2_plot):
            line, = ax.plot(x_fit,
                            y2_plot,
                            color=palette[palette_index],
                            alpha=0.8,
                            lw=2,
                            ls=line_style)
        if rate <= min(request_rates):
            line.set_label("Vehicle dispatch (p2)")
        palette_index += 1
        line, = ax.plot(
            x,
            y3,
            color=palette[palette_index],
            alpha=0.8,
            lw=0,
            marker="o",
            markersize=8,
        )
        if len(x_fit) == len(y3_plot):
            line, = ax.plot(
                x_fit,
                y3_plot,
                color=palette[palette_index],
                alpha=0.8,
                lw=2,
                ls=line_style,
            )
        if rate <= min(request_rates):
            line.set_label("Vehicle with rider (p3)")
        palette_index += 1
        line, = ax.plot(
            x,
            y4,
            color=palette[palette_index],
            alpha=0.8,
            lw=0,
            marker="o",
            markersize=8,
        )
        if len(x_fit) == len(y4_plot):
            line, = ax.plot(
                x_fit,
                y4_plot,
                color=palette[palette_index],
                alpha=0.8,
                lw=2,
                ls="dashed",
            )
        if rate <= min(request_rates):
            line.set_label("Trip wait time (fraction)")
        palette_index += 1
        line, = ax.plot(
            x,
            y5,
            color=palette[palette_index],
            alpha=0.8,
            lw=1,
            ls="dotted",
            marker="x",
            markersize=4,
        )
        if rate <= min(request_rates):
            line.set_label("Mean trip length (fraction)")
    caption = (f"City size: {city_size}\n"
               f"Request rate: {request_rate} per block\n"
               f"Trip length: [{min_trip_distance}, {max_trip_distance}]\n"
               f"Trip inhomogeneity: {trip_inhomogeneity}\n"
               f"Idle vehicles moving: {idle_vehicles_moving}\n"
               f"Simulation time: {time_blocks} blocks\n"
               f"Results window: {results_window} blocks\n"
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
    if "title" in sequence[0]["config"]:
        title = [sim["config"]["title"] for sim in sequence][0]
    else:
        title = ("Ridehail simulation sequence: "
                 f"city size = {city_size}, "
                 f"request rate = {request_rate}, ")
    ax.set_title(title)
    ax.legend()
    plt.tight_layout()
    plt.savefig(f"img/{filename_root}.png")
    print(f"Chart saved as img/{filename_root}.png")


if __name__ == '__main__':
    main()
