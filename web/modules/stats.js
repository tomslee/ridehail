/* global  Chart */
import { message, colors } from "../main.js";
// const startTime = Date.now();

export function initStatsChart(ctx) {
  const statsOptions = {
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
          text: "Wait fraction",
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

  const statsConfig = {
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
          borderWidth: 3,
          borderDash: [10, 10],
        },
      ],
    },
    options: statsOptions,
  };
  //options: {}
  window.chart = new Chart(ctx, statsConfig);
}

// Handle stats messages
export function plotStats(eventData) {
  if (eventData != null) {
    //let time = Math.round((Date.now() - startTime) / 100) * 100;
    window.chart.data.datasets.forEach((dataset, index) => {
      dataset.data.push({
        x: eventData.get("block"),
        y: eventData.get("values")[index],
      });
    });
    window.chart.options.scales.xAxis.max = eventData.get("block");
    window.chart.options.plugins.title.text = `City size ${message.citySize} blocks, ${message.vehicleCount} vehicles, Time block ${eventData[0]}`;
    window.chart.update("none");
  }
}
