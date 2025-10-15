/* global  Chart ChartDataLabels */
import { colors } from "../js/constants.js";
// const startTime = Date.now();
// Register the data labels plugin
Chart.register(ChartDataLabels);

export function initCityChart(uiSettings) {
  const cityBarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    layout: {
      padding: 0,
    },
    scales: {
      y: {
        stacked: false,
        min: 0.0,
        suggestedMax: 10.0,
        title: {
          display: false,
          text: "Number",
        },
        ticks: {
          display: false,
        },
      },
      yreq: {
        stacked: false,
        min: 0.0,
        suggestedMax: 10.0,
        position: "right",
        title: {
          display: false,
          text: "Request Rate",
        },
        ticks: {
          display: false,
        },
        grid: {
          drawOnChartArea: false,
        },
      },
    },
    plugins: {
      legend: {
        legend: { position: "top" },
      },
      title: {
        display: false,
      },
    },
  };

  const cityBarConfig = {
    type: "bar",
    options: cityBarOptions,
    data: {
      labels: ["Counts"],
      datasets: [
        {
          label: "Vehicles",
          data: null,
          backgroundColor: colors.get("WITH_RIDER"),
          yAxisID: "y",
          stack: "Stack 0",
          datalabels: { align: "bottom", anchor: "end" },
        },
        {
          label: "Requests",
          data: null,
          backgroundColor: colors.get("WAITING"),
          yAxisID: "yreq",
          stack: "Stack 1",
          datalabels: { align: "bottom", anchor: "end" },
        },
      ],
    },
  };
  cityBarConfig.options.plugins.datalabels = {
    color: "#666",
    display: true,
    font: { weight: "bold" },
    formatter: Math.round,
  };
  if (window.cityChart instanceof Chart) {
    window.cityChart.destroy();
  }
  window.cityChart = new Chart(uiSettings.ctxCity, cityBarConfig);
}

export function initPhasesChart(uiSettings) {
  const phasesBarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    layout: {
      padding: 0,
    },
    scales: {
      y: {
        stacked: true,
        min: 0.0,
        max: 100.0,
        title: {
          display: false,
          text: "Time (%)",
        },
      },
    },
    plugins: {
      legend: {
        display: false,
        legend: { position: "top", labels: { boxWidth: 20 } },
      },
      title: {
        display: false,
      },
    },
  };

  const phasesBarConfig = {
    type: "bar",
    options: phasesBarOptions,
    data: {
      labels: ["Vehicle phases"],
      datasets: [
        {
          label: "P3",
          data: null,
          backgroundColor: colors.get("WITH_RIDER"),
          yAxisID: "y",
          stack: "Stack 0",
          datalabels: { align: "top", anchor: "start" },
        },
        {
          label: "P2",
          data: null,
          backgroundColor: colors.get("DISPATCHED"),
          yAxisID: "y",
          stack: "Stack 0",
          datalabels: { align: "center", anchor: "center" },
        },
        {
          label: "P1",
          data: null,
          backgroundColor: colors.get("IDLE"),
          yAxisID: "y",
          stack: "Stack 0",
          datalabels: { align: "bottom", anchor: "end" },
        },
      ],
    },
  };
  phasesBarConfig.options.plugins.datalabels = {
    color: "#666",
    display: true,
    font: { weight: "bold" },
    formatter: function (value, context) {
      return context.dataset.label + ": " + Math.round(value) + "%";
    },
  };
  if (window.phasesChart instanceof Chart) {
    window.phasesChart.destroy();
  }
  window.phasesChart = new Chart(uiSettings.ctxPhases, phasesBarConfig);
}

export function initTripChart(uiSettings, simSettings) {
  let yAxisTitle = "Time (blocks)";
  let units = "";
  if (simSettings.useCostsAndIncomes) {
    yAxisTitle = "Time (minutes)";
    units = "mins";
  }
  const tripBarOptions = {
    responsive: true,
    maintainAspectRatio: false,
    layout: {
      padding: 0,
    },
    scales: {
      y: {
        stacked: true,
        min: 0.0,
        max: 1.2 * parseInt(simSettings.citySize),
        type: "linear",
        grid: {
          linewidth: 1,
          borderWidth: 1,
          drawOnChartArea: true,
        },
        title: {
          display: false,
          text: yAxisTitle,
        },
      },
    },
    plugins: {
      legend: {
        display: false,
        legend: { position: "top", labels: { boxWidth: 20 } },
      },
      title: {
        display: false,
      },
    },
  };

  const tripBarConfig = {
    type: "bar",
    options: tripBarOptions,
    data: {
      labels: ["Passenger time"],
      datasets: [
        {
          label: "Wait",
          data: null,
          backgroundColor: colors.get("WAITING"),
          stack: "Stack 1",
          datalabels: { align: "top", anchor: "start" },
        },
        {
          label: "Ride",
          data: null,
          backgroundColor: colors.get("RIDING"),
          stack: "Stack 1",
          datalabels: { align: "bottom", anchor: "end" },
        },
      ],
    },
  };

  //options: {}
  tripBarConfig.options.plugins.datalabels = {
    color: "#666",
    display: true,
    font: { weight: "bold" },
    textAlign: "center",
    formatter: function (value, context) {
      return (
        context.dataset.label + "\n" + Math.round(value * 10) / 10 + " " + units
      );
    },
  };
  if (window.tripChart instanceof Chart) {
    window.tripChart.destroy();
  }
  window.tripChart = new Chart(uiSettings.ctxTrip, tripBarConfig);
}

export function initIncomeChart(uiSettings, simSettings) {
  let suggestedMax = simSettings.price;
  let currency = "";
  let period = "";
  if (simSettings.useCostsAndIncomes) {
    suggestedMax =
      simSettings.perMinutePrice * 60 +
      simSettings.perKmPrice * simSettings.meanVehicleSpeed;
    currency = "$";
    period = "/hr";
  }
  const incomeChartOptions = {
    responsive: true,
    maintainAspectRatio: false,
    layout: {
      padding: 0,
    },
    scales: {
      y: {
        stacked: true,
        min: 0,
        max: suggestedMax,
        grid: {
          linewidth: 1,
          borderWidth: 1,
          drawOnChartArea: true,
        },
        type: "linear",
        title: {
          display: false,
        },
      },
    },
    plugins: {
      legend: {
        display: false,
        legend: { position: "top", labels: { boxWidth: 20 } },
      },
      title: {
        display: false,
      },
    },
  };

  const incomeChartConfig = {
    type: "bar",
    data: {
      labels: ["Driver income"],
    },
    options: incomeChartOptions,
  };
  if (simSettings.useCostsAndIncomes) {
    incomeChartConfig.data.datasets = [
      {
        label: "Net",
        data: null,
        backgroundColor: colors.get("WITH_RIDER"),
        stack: "Stack 0",
        datalabels: { align: "top", anchor: "start" },
      },
      {
        label: "Expenses",
        data: null,
        backgroundColor: colors.get("DISPATCHED"),
        stack: "Stack 0",
        datalabels: { align: "center", anchor: "center" },
      },
      {
        label: "Unpaid",
        data: null,
        backgroundColor: colors.get("IDLE"),
        stack: "Stack 0",
        datalabels: { align: "bottom", anchor: "end" },
      },
    ];
  } else {
    // simple model: no expenses
    incomeChartConfig.data.datasets = [
      {
        label: "Paid",
        data: null,
        backgroundColor: colors.get("WITH_RIDER"),
        stack: "Stack 0",
        datalabels: { align: "top", anchor: "start" },
      },
      {
        label: "Unpaid",
        data: null,
        backgroundColor: colors.get("IDLE"),
        stack: "Stack 0",
        datalabels: { align: "bottom", anchor: "end" },
      },
    ];
  }

  incomeChartConfig.options.plugins.datalabels = {
    color: "#666",
    display: true,
    font: { weight: "bold" },
    textAlign: "center",
    formatter: function (value, context) {
      return (
        context.dataset.label +
        "\n" +
        currency +
        Math.round(value * 10) / 10 +
        period
      );
    },
  };
  if (window.incomeChart instanceof Chart) {
    window.incomeChart.destroy();
  }
  window.incomeChart = new Chart(uiSettings.ctxIncome, incomeChartConfig);
}

export function plotCityChart(eventData) {
  if (eventData) {
    window.cityChart.data.datasets[0].data = [
      eventData.get("VEHICLE_MEAN_COUNT"),
    ];
    window.cityChart.data.datasets[1].data = [
      eventData.get("TRIP_MEAN_REQUEST_RATE"),
    ];
    window.cityChart.update();
  }
}

export function plotPhasesChart(eventData) {
  if (eventData) {
    //let time = Math.round((Date.now() - startTime) / 100) * 100;
    window.phasesChart.options.plugins.title.text = `${
      eventData.get("base_demand") * 60
    } requests/hour`;
    // bar chart. valus provide the P1, P2, P3 times and wait time
    window.phasesChart.data.datasets[0].data = [
      100.0 * eventData.get("VEHICLE_FRACTION_P3"),
    ];
    window.phasesChart.data.datasets[1].data = [
      100.0 * eventData.get("VEHICLE_FRACTION_P2"),
    ];
    window.phasesChart.data.datasets[2].data = [
      100.0 * eventData.get("VEHICLE_FRACTION_P1"),
    ];
    window.phasesChart.update();
  }
}

export function plotTripChart(eventData) {
  if (eventData != null) {
    //let time = Math.round((Date.now() - startTime) / 100) * 100;
    window.tripChart.options.plugins.title.text = `${
      eventData.get("base_demand") * 60
    } requests/hour`;
    // bar chart. valus provide the P1, P2, P3 times and wait time
    window.tripChart.data.datasets[0].data = [
      eventData.get("TRIP_MEAN_WAIT_TIME"),
    ];
    window.tripChart.data.datasets[1].data = [
      eventData.get("TRIP_MEAN_RIDE_TIME"),
    ];
    window.tripChart.update();
  }
}

export function plotIncomeChart(eventData) {
  if (eventData) {
    //let time = Math.round((Date.now() - startTime) / 100) * 100;
    // let platformCommission = eventData.get("platform_commission");
    // let price = eventData.get("TRIP_MEAN_PRICE");
    window.incomeChart.options.plugins.title.text = `${
      eventData.get("base_demand") * 60
    } requests/hour`;
    let grossIncome = eventData.get("VEHICLE_GROSS_INCOME");
    let netIncome = eventData.get("VEHICLE_NET_INCOME");
    // let surplusIncome = eventData.get("VEHICLE_MEAN_SURPLUS");
    // TODO: Get the conversion properly, in worker.py
    let expenses =
      eventData.get("mean_vehicle_speed") * eventData.get("per_km_ops_cost");
    let grossOnTheClockIncome = grossIncome;
    if (eventData.get("VEHICLE_FRACTION_P3") > 0) {
      grossOnTheClockIncome =
        grossIncome / eventData.get("VEHICLE_FRACTION_P3");
    }
    if (eventData.get("use_city_scale")) {
      window.incomeChart.data.datasets[0].data = [netIncome];
      window.incomeChart.data.datasets[1].data = [expenses];
      window.incomeChart.data.datasets[2].data = [
        grossOnTheClockIncome - grossIncome,
      ];
    } else {
      window.incomeChart.data.datasets[0].data = [netIncome];
      window.incomeChart.data.datasets[1].data = [
        grossOnTheClockIncome - grossIncome,
      ];
    }
    window.incomeChart.update();
  }
}
