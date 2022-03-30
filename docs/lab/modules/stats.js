/* global  Chart */
import { colors } from "../main.js";
// const startTime = Date.now();

export function initIncomeChart(uiSettings, simSettings) {
  let suggestedMax = simSettings.price;
  if (simSettings.useCityScale) {
    suggestedMax = simSettings.price * 60;
  }
  const incomeChartOptions = {
    responsive: true,
    aspectRatio: 0.5,
    layout: {
      padding: 0,
    },
    scales: {
      y: {
        stacked: true,
        suggestedMin: 0,
        suggestedMax: suggestedMax,
        grid: {
          linewidth: 1,
          borderWidth: 1,
          drawOnChartArea: true,
        },
        type: "linear",
        title: {
          display: true,
          text: "Income",
        },
      },
    },
    plugins: {
      legend: {
        display: false,
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
      datasets: [
        {
          label: "Net",
          data: null,
          backgroundColor: colors.get("WITH_RIDER"),
          stack: "Stack 0",
          datalabels: { align: "center", anchor: "center" },
        },
        {
          label: "Expenses",
          data: null,
          backgroundColor: colors.get("DISPATCHED"),
          stack: "Stack 0",
        },
        {
          label: "Unpaid time",
          data: null,
          backgroundColor: colors.get("IDLE"),
          stack: "Stack 0",
        },
      ],
    },
    options: incomeChartOptions,
  };

  if (window.incomeChart instanceof Chart) {
    window.incomeChart.destroy();
  }
  window.incomeChart = new Chart(uiSettings.ctxIncome, incomeChartConfig);
}

export function initPhasesChart(uiSettings, simSettings) {
  const phasesBarOptions = {
    responsive: true,
    aspectRatio: 0.5,
    layout: {
      padding: 0,
    },
    scales: {
      y: {
        stacked: true,
        min: 0.0,
        max: 100.0,
        title: {
          display: true,
          text: "Percent of time",
        },
      },
    },
    plugins: {
      legend: {
        display: false,
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
        },
        {
          label: "P2",
          data: null,
          backgroundColor: colors.get("DISPATCHED"),
          yAxisID: "y",
          stack: "Stack 0",
        },
        {
          label: "P1",
          data: null,
          backgroundColor: colors.get("IDLE"),
          yAxisID: "y",
          stack: "Stack 0",
        },
      ],
    },
  };
  //options: {}
  if (window.phasesChart instanceof Chart) {
    window.phasesChart.destroy();
  }
  window.phasesChart = new Chart(uiSettings.ctxPhases, phasesBarConfig);
}

export function initTripChart(uiSettings, simSettings) {
  let yAxisTitle = "Time";
  if (simSettings.useCityScale) {
    yAxisTitle = "Time (mins)";
  }
  const tripBarOptions = {
    responsive: true,
    aspectRatio: 0.5,
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
          display: true,
          text: yAxisTitle,
        },
      },
    },
    plugins: {
      legend: {
        display: false,
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
          label: "Wait time",
          data: null,
          backgroundColor: colors.get("WAITING"),
          stack: "Stack 1",
        },
        {
          label: "Ride time",
          data: null,
          backgroundColor: colors.get("RIDING"),
          stack: "Stack 1",
        },
      ],
    },
  };

  //options: {}
  if (window.tripChart instanceof Chart) {
    window.tripChart.destroy();
  }
  window.tripChart = new Chart(uiSettings.ctxTrip, tripBarConfig);
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
    let surplusIncome = eventData.get("VEHICLE_MEAN_SURPLUS");
    let expenses = eventData.get("per_km_ops_cost");
    let grossOnTheClockIncome = grossIncome;
    if (eventData.get("VEHICLE_FRACTION_P3") > 0) {
      grossOnTheClockIncome =
        grossIncome / eventData.get("VEHICLE_FRACTION_P3");
    }
    window.incomeChart.data.datasets[0].data = [netIncome];
    window.incomeChart.data.datasets[1].data = [expenses];
    window.incomeChart.data.datasets[2].data = [
      grossOnTheClockIncome - grossIncome,
    ];
    window.incomeChart.update();
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
