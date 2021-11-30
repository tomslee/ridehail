#!/usr/bin/python3

import sys
import os
import json
import matplotlib.pyplot as plt
import matplotlib as mpl
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
        set([sim["config"]["request_rate"] for sim in sequence]))
    fig, ax = plt.subplots(ncols=1, figsize=(8, 8))
    palette = sns.color_palette()
    for rate in request_rates:
        x = [
            sim["config"]["driver_count"] for sim in sequence
            if sim["config"]["request_rate"] == rate
        ]
        y1 = [
            sim["output"]["driver_fraction_available"] for sim in sequence
            if sim["config"]["request_rate"] == rate
        ]
        y2 = [
            sim["output"]["driver_fraction_picking_up"] for sim in sequence
            if sim["config"]["request_rate"] == rate
        ]
        y3 = [
            sim["output"]["driver_fraction_with_rider"] for sim in sequence
            if sim["config"]["request_rate"] == rate
        ]
        y4 = [
            sim["output"]["mean_trip_wait_time"] /
            (sim["output"]["mean_trip_wait_time"] +
             sim["output"]["mean_trip_distance"]) for sim in sequence
            if sim["config"]["request_rate"] == rate
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
                        alpha=0.6,
                        lw=2,
                        ls=line_style)
        if rate <= min(request_rates):
            line.set_label("Available")
        palette_index += 1
        line, = ax.plot(x,
                        y2,
                        color=palette[palette_index],
                        alpha=0.6,
                        lw=2,
                        ls=line_style)
        if rate <= min(request_rates):
            line.set_label("Picking up")
        palette_index += 1
        line, = ax.plot(x,
                        y3,
                        color=palette[palette_index],
                        alpha=0.6,
                        lw=2,
                        ls=line_style)
        if rate <= min(request_rates):
            line.set_label("With rider")
        palette_index += 1
        line, = ax.plot(x,
                        y4,
                        color=palette[palette_index],
                        alpha=0.6,
                        lw=2,
                        ls=line_style)
        if rate <= min(request_rates):
            line.set_label("Waiting")
    city_size = [sim["config"]["city_size"] for sim in sequence][0]
    request_rate = [sim["config"]["request_rate"] for sim in sequence][0]
    time_periods = [sim["config"]["time_periods"] for sim in sequence][0]
    trip_distribution = [
        sim["config"]["trip_distribution"].lower() for sim in sequence
    ][0]
    min_trip_distance = [
        sim["config"]["min_trip_distance"] for sim in sequence
    ][0]
    available_drivers_moving = [
        sim["config"]["available_drivers_moving"] for sim in sequence
    ][0]
    caption = (f"City size={city_size} blocks\n"
               f"Demand={request_rate} requests per period\n"
               f"Trip distribution={trip_distribution}\n"
               f"Minimum trip length={min_trip_distance} blocks\n"
               f"Idle drivers moving={available_drivers_moving}\n"
               f"Simulation length={time_periods} periods.")
    ax.text(.95,
            .75,
            caption,
            bbox={
                'facecolor': 'whitesmoke',
                'edgecolor': 'grey',
                'pad': 10,
            },
            verticalalignment="top",
            horizontalalignment="right",
            transform=ax.transAxes,
            fontsize=11,
            alpha=0.8)
    ax.set_xlabel("Drivers")
    ax.set_ylabel("Fraction")
    ax.legend()
    ax.set_title((f"Ride-hail simulation results, "
                  f"plotted on {datetime.now().strftime('%Y-%m-%d')}"))
    plt.savefig(f"img/{filename_root}.png")


if __name__ == '__main__':
    main()
