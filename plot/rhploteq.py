#!/usr/bin/python3

import os
import sys
import json
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns

mpl.rcParams["figure.dpi"] = 90
mpl.rcParams["savefig.dpi"] = 100
sns.set()
sns.set_palette("muted")


def fit_function(x, a, b, c):
    return a + b / (x + c)


def main():
    try:
        if os.path.isfile(sys.argv[1]):
            input_file = sys.argv[1]
            filename_root = os.path.splitext(os.path.basename(input_file))[0]
    except:
        print(
            "Usage:\n\tpython rhploteq.py <log_file>"
            "\n\n\twhere <log_file> is the output from a run of ridehail.py"
            "\n\twith run_sequence=False and -l <log_file>"
        )
        exit(-1)
    with open(input_file) as f:
        lines = f.readlines()

    periods = []
    for line in lines:
        try:
            periods.append(json.loads(line))
        except json.decoder.JSONDecodeError:
            pass

    x = [period["block"] for period in periods if "block" in period]
    supply = [period["Vehicle count"] for period in periods if "block" in period]
    demand = [period["Request rate"] for period in periods if "block" in period]
    p3_fraction = [period["Vehicle P3 time"] for period in periods if "block" in period]
    wait_fraction = [
        period["Trip wait fraction"] for period in periods if "block" in period
    ]

    fig = plt.figure(figsize=(16, 12))
    gridspec = fig.add_gridspec(3, 1)
    ax1 = fig.add_subplot(gridspec[0, 0])
    palette = sns.color_palette()
    palette_index = 0
    ax1.plot(
        x,
        supply,
        color=palette[palette_index],
        alpha=0.6,
        lw=3,
        ls="dashed",
        label="Supply",
    )
    palette_index += 1
    ax1.plot(
        x,
        wait_fraction,
        color=palette[palette_index],
        alpha=0.6,
        lw=3,
        label="Wait fraction",
    )
    palette_index += 1
    ax1.plot(
        x,
        p3_fraction,
        color=palette[palette_index],
        alpha=0.6,
        lw=3,
        label="P3 fraction",
    )
    palette_index += 1
    ax1.plot(
        x,
        demand,
        color=palette[palette_index],
        alpha=0.6,
        lw=3,
        ls="dashed",
        label="Demand",
    )
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Supply or Demand")
    ax1.set_title("Equilibration")
    ax1.legend()
    ax2 = fig.add_subplot(gridspec[1, 0])
    palette_index += 1
    ax2.plot(
        x,
        supply,
        color=palette[palette_index],
        alpha=0.6,
        lw=3,
        # marker="o",
        label="Vehicles",
    )
    ax2.set_xlabel("Time")
    ax2.set_ylabel("Vehicles")
    ax2.legend()
    ax3 = fig.add_subplot(gridspec[2, 0])
    palette_index += 1
    ax3.plot(
        x,
        demand,
        color=palette[palette_index],
        alpha=0.6,
        lw=3,
        # marker="o",
        label="Request Rate",
    )
    ax3.set_xlabel("Time")
    ax3.set_ylabel("Request rate")
    ax3.legend()
    filename = f"img/{filename_root}_eq.png"
    print(f"Writing file {filename}")
    plt.savefig(filename)


if __name__ == "__main__":
    main()
