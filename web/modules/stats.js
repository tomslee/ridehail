/* global  Chart */
import { message, colors } from "../main.js";
// const startTime = Date.now();

export function initStatsChart(ctx, style = "bar") {
  const statsBarOptions = {
    responsive: true,
    aspectRatio: 1,
    layout: {
      padding: 0,
    },
    scales: {
      y: {
        min: 0.0,
        max: 1.0,
      },
    },
    plugins: {
      legend: {
        display: false,
      },
      title: {
        display: true,
        text: "Ridehail statistics",
      },
    },
  };

  const statsLineOptions = {
    responsive: true,
    aspectRatio: 1.2,
    layout: {
      padding: 0,
    },
    scales: {
      xAxis: {
        min: 0,
        max: message.timeBlocks,
        grid: {
          linewidth: 1,
          borderWidth: 1,
        },
        type: "linear",
        title: {
          text: "Time (blocks)",
          display: true,
          font: {
            weight: "normal",
          },
        },
      },
      yAxis: {
        min: 0.0,
        max: 1.0,
        grid: {
          linewidth: 1,
          borderWidth: 1,
        },
        type: "linear",
        title: {
          text: "Fraction",
          display: true,
          font: {
            weight: "normal",
          },
        },
      },
    },
    elements: {
      line: {
        borderWidth: 5,
        tension: 0.3,
      },
      point: {
        radius: 0,
      },
    },
    animation: {
      duration: 0,
    },
    plugins: {
      legend: {
        display: true,
      },
      title: {
        display: true,
        text: "Ridehail statistics",
      },
    },
  };

  const statsBarConfig = {
    type: "bar",
    options: statsBarOptions,
    data: {
      labels: ["P1", "P2", "P3", "Waiting"],
      datasets: [
        {
          data: null,
          backgroundColor: [
            colors.get("IDLE"),
            colors.get("DISPATCHED"),
            colors.get("WITH_RIDER"),
            colors.get("WAITING"),
          ],
          borderColor: [
            colors.get("IDLE"),
            colors.get("DISPATCHED"),
            colors.get("WITH_RIDER"),
            colors.get("WAITING"),
          ],
          borderWidth: 3,
        },
      ],
    },
  };

  const statsLineConfig = {
    type: "line",
    data: {
      datasets: [
        {
          label: "P1 (idle)",
          data: null,
          backgroundColor: colors.get("IDLE"),
          borderColor: colors.get("IDLE"),
          borderWidth: 3,
        },
        {
          label: "P2 (dispatched)",
          data: null,
          backgroundColor: colors.get("DISPATCHED"),
          borderColor: colors.get("DISPATCHED"),
          borderWidth: 3,
        },
        {
          label: "P3 (busy)",
          data: null,
          backgroundColor: colors.get("WITH_RIDER"),
          borderColor: colors.get("WITH_RIDER"),
          borderWidth: 3,
        },
        {
          label: "Wait time / In-vehicle time",
          data: null,
          backgroundColor: colors.get("WAITING"),
          borderColor: colors.get("WAITING"),
          borderWidth: 1,
          borderDash: [10, 10],
        },
      ],
    },
    options: statsLineOptions,
  };

  //options: {}
  if (style == "line") {
    window.chart = new Chart(ctx, statsLineConfig);
  } else {
    window.chart = new Chart(ctx, statsBarConfig);
  }
}

// Handle stats messages
export function plotStats(eventData, style = "bar") {
  if (eventData != null) {
    //let time = Math.round((Date.now() - startTime) / 100) * 100;
    window.chart.options.plugins.title.text = `City size ${
      message.citySize
    } blocks, ${message.vehicleCount} vehicles, ${
      message.requestRate
    } requests, Time ${eventData.get("block")}`;
    if (style == "line") {
      window.chart.data.datasets.forEach((dataset, index) => {
        dataset.data.push({
          x: eventData.get("block"),
          y: eventData.get("values")[index],
        });
      });
      window.chart.options.scales.xAxis.max = eventData.get("block");
      window.chart.update();
    } else {
      // bar chart. Only one data set
      window.chart.data.datasets[0].data = eventData.get("values");
      window.chart.update();
    }
  }
}