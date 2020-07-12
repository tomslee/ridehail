#!/usr/bin/python3

import json
import matplotlib.pyplot as plt
import matplotlib as mpl
import seaborn as sns

mpl.rcParams['figure.dpi'] = 90
mpl.rcParams['savefig.dpi'] = 100
sns.set()
sns.set_palette("muted")


def fit_function(x, a, b, c):
    return (a + b / (x + c))


def main():
    with open("2020-07-10-1.log") as f:
        lines = f.readlines()

    periods = []
    for line in lines:
        try:
            periods.append(json.loads(line))
        except json.decoder.JSONDecodeError as e:
            pass

    x = [period["period"] for period in periods]
    supply = [period["supply"] for period in periods]
    demand = [period["demand"] for period in periods]
    drivers = [period["new driver count"] for period in periods]
    request_rate = [period["new request rate"] for period in periods]
    p3_fraction = [period["busy"] for period in periods]
    wait_fraction = [period["wait_fraction"] for period in periods]

    fig = plt.figure(figsize=(16, 12))
    gridspec = fig.add_gridspec(3, 1)
    ax1 = fig.add_subplot(gridspec[0, 0])
    palette = sns.color_palette()
    palette_index = 0
    ax1.plot(x,
             supply,
             color=palette[palette_index],
             alpha=0.6,
             lw=3,
             ls="dashed",
             label="Supply")
    palette_index += 1
    ax1.plot(x,
             wait_fraction,
             color=palette[palette_index],
             alpha=0.6,
             lw=3,
             label="Wait fraction")
    palette_index += 1
    ax1.plot(x,
             p3_fraction,
             color=palette[palette_index],
             alpha=0.6,
             lw=3,
             label="P3 fraction")
    palette_index += 1
    ax1.plot(x,
             demand,
             color=palette[palette_index],
             alpha=0.6,
             lw=3,
             ls="dashed",
             label="Demand")
    ax1.set_xlabel("Time")
    ax1.set_ylabel("Supply or Demand")
    ax1.set_title("Equilibration")
    ax1.legend()
    ax2 = fig.add_subplot(gridspec[1, 0])
    palette_index += 1
    ax2.plot(x,
             drivers,
             color=palette[palette_index],
             alpha=0.6,
             lw=3,
             marker="o",
             label="Drivers")
    ax2.set_xlabel("Time")
    ax2.set_ylabel("Drivers")
    ax2.legend()
    ax3 = fig.add_subplot(gridspec[2, 0])
    palette_index += 1
    ax3.plot(x,
             request_rate,
             color=palette[palette_index],
             alpha=0.6,
             lw=3,
             marker="o",
             label="Request Rate")
    ax3.set_xlabel("Time")
    ax3.set_ylabel("Request rate")
    ax3.legend()
    filename = "img/reploteq.png"
    print(f"Writing file {filename}")
    plt.savefig(filename)


if __name__ == '__main__':
    main()
