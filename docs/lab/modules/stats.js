/* global  Chart */
import { colors } from "../main.js";
// const startTime = Date.now();

var useCityScale = false;

export function initDriverChart(uiSettings, simSettings) {
  let yAxisTitle = "Income";
  let suggestedMax = simSettings.price;
  useCityScale = simSettings.useCityScale;
  if (simSettings.useCityScale) {
    yAxisTitle = "Income ($/hour)";
    suggestedMax =
      (simSettings.per_km_price * simSettings.mean_vehicle_speed +
        simSettings.per_minute_price * 60) *
      (1.0 - simSettings.platform_commission);
  }
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
        suggestedMin: -0.2,
        suggestedMax: suggestedMax,
        grid: {
          linewidth: 1,
          borderWidth: 1,
          drawOnChartArea: true, // only want the grid lines for one axis to show up
        },
        type: "linear",
        title: {
          display: true,
          text: yAxisTitle,
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
          text: "Number",
        },
      },
    },
    plugins: {
      legend: {
        display: false,
      },
    },
  };

  let labels = ["On-the-clock", "Gross", "Net", "Surplus", "Vehicles"];
  let backgroundColor = [
    colors.get("RIDING"),
    colors.get("WITH_RIDER"),
    colors.get("PURPLE"),
    colors.get("IDLE"),
    colors.get("DISPATCHED"),
  ];
  if (!simSettings.useCityScale) {
    labels = ["Gross", "Surplus", "Vehicles"];
    backgroundColor = [
      colors.get("WITH_RIDER"),
      colors.get("IDLE"),
      colors.get("DISPATCHED"),
    ];
  }

  const driverChartConfig = {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          yAxisID: "y",
          backgroundColor: backgroundColor,
          data: null,
        },
        {
          yAxisID: "yVehicleCount",
          backgroundColor: colors.get("DISPATCHED"),
          data: null,
        },
      ],
    },
    options: driverChartOptions,
  };
  if (window.driverChart instanceof Chart) {
    window.driverChart.destroy();
  }
  window.driverChart = new Chart(uiSettings.ctxDriver, driverChartConfig);
}

export function initStatsChart(uiSettings, simSettings, style = "bar") {
  let yWaitAxisTitle = "Time";
  if (simSettings.useCityScale) {
    yWaitAxisTitle = "Time (mins)";
  }
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
        max: parseInt(simSettings.citySize * 0.7),
        type: "linear",
        // grace: "10%",
        position: "right",
        // grid line settings
        grid: {
          drawOnChartArea: false, // only want the grid lines for one axis to show up
        },
        title: {
          display: true,
          text: yWaitAxisTitle,
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
      labels: [
        "P1 (Idle)",
        "P2 (Dispatch)",
        "P3 (Busy)",
        "<Wait time>",
        "<Ride time>",
      ],
      datasets: [
        {
          data: null,
          yAxisID: "y",
          backgroundColor: [
            colors.get("IDLE"),
            colors.get("DISPATCHED"),
            colors.get("WITH_RIDER"),
          ],
          borderColor: [
            colors.get("IDLE"),
            colors.get("DISPATCHED"),
            colors.get("WITH_RIDER"),
          ],
          borderWidth: 3,
        },
        {
          data: null,
          yAxisID: "ywait",
          backgroundColor: [
            "black",
            "black",
            "black",
            colors.get("WAITING"),
            colors.get("PURPLE"),
          ],
          borderColor: [
            "black",
            "black",
            "black",
            colors.get("WAITING"),
            colors.get("PURPLE"),
          ],
          borderWidth: 3,
        },
      ],
    },
  };

  // line chart not in use. Just keeping this "in case"
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
    window.chart = new Chart(uiSettings.ctx, statsLineConfig);
  } else {
    window.chart = new Chart(uiSettings.ctx, statsBarConfig);
  }
}

export function plotDriverStats(eventData) {
  if (eventData != null) {
    //let time = Math.round((Date.now() - startTime) / 100) * 100;
    // let platformCommission = eventData.get("platform_commission");
    // let price = eventData.get("TRIP_MEAN_PRICE");
    let vehicleCount = eventData.get("VEHICLE_MEAN_COUNT");
    // let grossOnTheClockIncome = price * (1.0 - platformCommission);
    let grossHourlyIncome = eventData.get("VEHICLE_GROSS_INCOME");
    let grossOnTheClockIncome = grossHourlyIncome;
    if (eventData.get("VEHICLE_FRACTION_P3") > 0) {
      grossOnTheClockIncome =
        grossOnTheClockIncome / eventData.get("VEHICLE_FRACTION_P3");
    }
    let netIncome = eventData.get("VEHICLE_NET_INCOME");
    let surplusIncome = eventData.get("VEHICLE_MEAN_SURPLUS");
    window.driverChart.options.plugins.title.text = "Driver income";
    if (useCityScale) {
      window.driverChart.data.datasets[0].data = [
        grossOnTheClockIncome,
        grossHourlyIncome,
        netIncome,
        surplusIncome,
      ];
      window.driverChart.data.datasets[1].data = [0, 0, 0, 0, vehicleCount];
    } else {
      window.driverChart.data.datasets[0].data = [
        grossHourlyIncome,
        surplusIncome,
      ];
      window.driverChart.data.datasets[1].data = [0, 0, vehicleCount];
    }
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
      window.chart.data.datasets[0].data = [
        eventData.get("VEHICLE_FRACTION_P1"),
        eventData.get("VEHICLE_FRACTION_P2"),
        eventData.get("VEHICLE_FRACTION_P3"),
      ];
      window.chart.data.datasets[1].data = [
        0,
        0,
        0,
        eventData.get("TRIP_MEAN_WAIT_TIME"),
        eventData.get("TRIP_MEAN_RIDE_TIME"),
      ];
      window.chart.update();
    }
  }
}
