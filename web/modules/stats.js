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
        title: {
          display: true,
          text: "Driver phases - fraction of time",
        },
      },
      ywait: {
        min: 0.0,
        suggestedMax: 5.0,
        position: "right",
        // grid line settings
        grid: {
          drawOnChartArea: false, // only want the grid lines for one axis to show up
        },
        title: {
          display: true,
          text: "Wait time (minutes)",
        },
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
          text: "Time (minutes)",
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
      labels: ["P1 (Idle)", "P2 (Dispatch)", "P3 (Busy)", "Wait time"],
      datasets: [
        {
          data: null,
          yAxisID: "y",
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
        {
          data: null,
          yAxisID: "ywait",
          backgroundColor: colors.get("WAITING"),
          borderColor: colors.get("WAITING"),
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
          label: "Wait time",
          data: null,
          backgroundColor: colors.get("WAITING"),
          borderColor: colors.get("WAITING"),
          borderWidth: 1,
          borderDash: [10, 10],
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

export function plotStats(eventData, style = "bar") {
  if (eventData != null) {
    //let time = Math.round((Date.now() - startTime) / 100) * 100;
    window.chart.options.plugins.title.text = `Community size ${eventData.get(
      "city_size"
    )} minutes, ${eventData.get("vehicle_count")} vehicles, ${eventData.get(
      "base_demand"
    )} requests/min, Time ${eventData.get("block")} mins`;
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
      console.log("ww: values=", eventData.get("values"));
      console.log("ww: values[3]=", eventData.get("values")[3]);
      // bar chart. Only one data set
      window.chart.data.datasets[0].data = eventData.get("values").slice(0, 3);
      window.chart.data.datasets[1].data = [
        0,
        0,
        0,
        eventData.get("values")[3],
      ];
      window.chart.update();
    }
  }
}
