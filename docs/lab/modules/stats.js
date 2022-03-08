/* global  Chart */
const blocksToHours = 60;
// const blocksToKm = 2;
// const kmToHours = 30;
import { simSettings, colors } from "../main.js";
// const startTime = Date.now();

export function initDriverChart(ctxDriver) {
  const driverChartOptions = {
    responsive: true,
    aspectRatio: 2,
    layout: {
      padding: 0,
    },
    // indexAxis: "y",
    scales: {
      y: {
        stacked: false,
        min: 0.0,
        suggestedMax: 40.0,
        grid: {
          linewidth: 1,
          borderWidth: 1,
          drawOnChartArea: true, // only want the grid lines for one axis to show up
        },
        type: "linear",
        title: {
          display: true,
          text: "$ / hour",
        },
      },
      yVehicleCount: {
        stacked: false,
        min: 0,
        suggestedMax: simSettings.vehicleCount,
        position: "right",
        grid: {
          drawOnChartArea: false, // only want the grid lines for one axis to show up
        },
        title: {
          display: true,
          text: "Vehicles",
        },
      },
    },
    plugins: {
      legend: {
        display: false,
      },
    },
  };
  const driverChartConfig = {
    type: "bar",
    data: {
      labels: ["On-the-clock", "Gross", "Net", "Vehicles"],
      datasets: [
        {
          yAxisID: "y",
          backgroundColor: [
            colors.get("WAITING"),
            colors.get("DISPATCHED"),
            colors.get("WITH_RIDER"),
            colors.get("IDLE"),
          ],
          data: null,
        },
        {
          yAxisID: "yVehicleCount",
          backgroundColor: colors.get("IDLE"),
          data: null,
        },
      ],
    },
    options: driverChartOptions,
  };
  if (window.driverChart instanceof Chart) {
    window.driverChart.destroy();
  }
  window.driverChart = new Chart(ctxDriver, driverChartConfig);
}

export function initStatsChart(ctx, style = "bar") {
  const statsBarOptions = {
    responsive: true,
    aspectRatio: 2,
    // indexAxis: "y",
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
        max: simSettings.timeBlocks,
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
  if (window.chart instanceof Chart) {
    window.chart.destroy();
  }
  if (style == "line") {
    window.chart = new Chart(ctx, statsLineConfig);
  } else {
    window.chart = new Chart(ctx, statsBarConfig);
  }
}

export function plotDriverStats(eventData) {
  if (eventData != null) {
    //let time = Math.round((Date.now() - startTime) / 100) * 100;
    let platformCommission = eventData.get("platform_commission");
    let price = eventData.get("price");
    let p3 = eventData.get("values")[2];
    let speed = eventData.get("mean_vehicle_speed");
    // let waitTime = eventData.get("values")[3];
    // let reservedWage = eventData.get("reserved_wage");
    let vehicleCount = eventData.get("values")[5];
    let perKmOpsCost = eventData.get("per_km_ops_cost");
    let grossOnTheClockIncome =
      price * (1.0 - platformCommission) * blocksToHours;
    let grossHourlyIncome = grossOnTheClockIncome * p3;
    let netHourlyIncome = grossHourlyIncome - perKmOpsCost * speed;
    window.driverChart.options.plugins.title.text = "Driver income";
    window.driverChart.data.datasets[0].data = [
      grossOnTheClockIncome,
      grossHourlyIncome,
      netHourlyIncome,
    ];
    window.driverChart.data.datasets[1].data = [0, 0, 0, vehicleCount];
    window.driverChart.update();
  }
}

export function plotStats(eventData, style = "bar") {
  if (eventData != null) {
    //let time = Math.round((Date.now() - startTime) / 100) * 100;
    window.chart.options.plugins.title.text = `Community size ${eventData.get(
      "city_size"
    )} blocks, ${eventData.get("base_demand") * 60} requests/hour`;
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
      // bar chart. valus provide the P1, P2, P3 times and wait time
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
