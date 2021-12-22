#!/usr/bin/python3

import sys
import os
import json
import matplotlib.pyplot as plt
import matplotlib as mpl
from matplotlib import offsetbox
from matplotlib.ticker import AutoMinorLocator
import seaborn as sns
from datetime import datetime
from scipy.optimize import curve_fit

mpl.rcParams['figure.dpi'] = 90
mpl.rcParams['savefig.dpi'] = 100
sns.set()
sns.set_palette("muted")


def fit_function(x, a, b, c):
    return (a + b / (x + c))


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
        set([sim["config"]["base_demand"] for sim in sequence if "config" in
             sim]))
    fig, ax = plt.subplots(ncols=1, figsize=(12, 8))
    palette = sns.color_palette()
    for rate in request_rates:
        x = [
            sim["config"]["vehicle_count"] for sim in sequence
            if sim["config"]["base_demand"] == rate
            and "config" in sim
        ]
        y1 = [
            sim["results"]["vehicle_fraction_idle"] for sim in sequence
            if sim["config"]["base_demand"] == rate
        ]
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
        z = zip(x, y1, y2, y3, y4)
        # Only fit for steady state solutions, where A > 0
        z_fit = [zval for zval in z if zval[1] > 0.1]
        if len(z_fit) > 0:
            (x, y1, y2, y3, y4) = zip(*z_fit)
        p0_a = y1[-1]
        p0_b = y1[0] * x[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        try:
            popt, _ = curve_fit(fit_function, x, y1, p0=p0, maxfev=2000)
            y1 = [fit_function(xval, *popt) for xval in x]
        except Exception:
            pass
        p0_a = y2[-1]
        p0_b = y2[0] * x[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        try:
            popt, _ = curve_fit(fit_function, x, y2, p0=p0, maxfev=2000)
            y2 = [fit_function(xval, *popt) for xval in x]
        except Exception:
            pass
        p0_a = y3[-1]
        p0_b = y3[0] * x[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        try:
            popt, _ = curve_fit(fit_function, x, y3, p0=p0, maxfev=2000)
            y3 = [fit_function(xval, *popt) for xval in x]
        except Exception:
            pass
        p0_a = y4[-1]
        p0_b = y4[0] * x[0]
        p0_c = 0
        p0 = (p0_a, p0_b, p0_c)
        try:
            popt, _ = curve_fit(fit_function, x, y4, p0=p0, maxfev=2000)
            y4 = [fit_function(xval, *popt) for xval in x]
        except Exception:
            pass
        line_style = "solid"
        palette_index = 0
        line, = ax.plot(x,
                        y1,
                        color=palette[palette_index],
                        alpha=0.8,
                        lw=2,
                        marker="o",
                        markersize=6,
                        ls=line_style)
        if rate <= min(request_rates):
            line.set_label("Vehicle idle (p1)")
        palette_index += 1
        line, = ax.plot(x,
                        y2,
                        color=palette[palette_index],
                        alpha=0.8,
                        lw=2,
                        marker="o",
                        markersize=6,
                        ls=line_style)
        if rate <= min(request_rates):
            line.set_label("Vehicle dispatch (p2)")
        palette_index += 1
        line, = ax.plot(x,
                        y3,
                        color=palette[palette_index],
                        alpha=0.8,
                        lw=2,
                        marker="o",
                        markersize=6,
                        ls=line_style)
        if rate <= min(request_rates):
            line.set_label("Vehicle with rider (p3)")
        palette_index += 1
        line, = ax.plot(x,
                        y4,
                        color=palette[palette_index],
                        alpha=0.8,
                        lw=2,
                        marker="o",
                        markersize=6,
                        ls="dashed")
        if rate <= min(request_rates):
            line.set_label("Trip wait time (fraction)")
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
    results_window = [
        sim["config"]["results_window"] for sim in sequence
    ][0]
    caption = (
        f"Trip length: [{min_trip_distance}, {max_trip_distance}]\n"
        f"Trip inhomogeneity: {trip_inhomogeneity}\n"
        f"Idle vehicles moving: {idle_vehicles_moving}\n"
        f"Simulation length: {time_blocks} blocks\n"
        f"Results window: {results_window} blocks\n"
        f"Generated on {datetime.now().strftime('%Y-%m-%d')}"
    )
    anchor_props =  {
        'bbox': {
                'facecolor': 'ghostwhite',
                'edgecolor': 'silver',
                'pad': 5,
            },
        'fontsize': 10,
        'linespacing': 2.0
    }
    caption_location = "right"
    anchored_text = offsetbox.AnchoredText(
            caption,
            loc=caption_location,
            frameon=False,
            prop=anchor_props
            )
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
    plt.savefig(f"img/{filename_root}.png")
    print (f"Chart saved as img/{filename_root}.png")


if __name__ == '__main__':
    main()
