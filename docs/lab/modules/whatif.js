/* global  Chart ChartDataLabels */
import { colors } from "../main.js";

function clone(o) {
  return JSON.parse(JSON.stringify(o));
}

const config = {
  type: "bar",
  data: {
    labels: null,
    datasets: [
      {
        backgroundColor: "blue",
        data: null,
      },
    ],
  },
  plugins: [ChartDataLabels],
};

const options = {
  responsive: true,
  aspectRatio: 0.5,
  layout: {
    padding: 0,
  },
  scales: {
    x: {
      stacked: true,
    },
    y: {
      stacked: true,
      min: 0.0,
      suggestedMax: 1.0,
      grid: {
        linewidth: 1,
        borderWidth: 1,
        drawOnChartArea: true, // only want the grid lines for one axis to show up
      },
      type: "linear",
      title: {
        display: true,
        text: null,
      },
    },
  },
  plugins: {
    legend: {
      display: false,
    },
    datalabels: {},
  },
};

export function initWhatIfPhasesChart(uiSettings) {
  let phasesConfig = clone(config);
  phasesConfig.options = clone(options);
  phasesConfig.data.labels = ["Vehicle phases"];
  phasesConfig.options.scales.y.title.text = "Percentage";
  phasesConfig.options.scales.y.max = 100;
  phasesConfig.data.datasets = [
    { label: "P3", data: null, backgroundColor: colors.get("WITH_RIDER") },
    { label: "P2", data: null, backgroundColor: colors.get("DISPATCHED") },
    { label: "P1", data: null, backgroundColor: colors.get("IDLE") },
  ];
  phasesConfig.options.plugins.datalabels = {
    align: "end",
    anchor: "end",
    color: "blue",
    formatter: function (value) {
      return value;
    },
  };
  if (window.whatIfPhasesChart instanceof Chart) {
    window.whatIfPhasesChart.destroy();
  }
  window.whatIfPhasesChart = new Chart(
    uiSettings.ctxWhatIfPhases,
    phasesConfig
  );
}

export function initWhatIfIncomeChart(uiSettings) {
  let incomeConfig = clone(config);
  incomeConfig.options = clone(options);
  incomeConfig.data.labels = ["Driver income"];
  incomeConfig.data.datasets = [
    {
      label: "Net",
      data: null,
      backgroundColor: colors.get("WITH_RIDER"),
    },
    {
      label: "Expenses",
      data: null,
      backgroundColor: colors.get("DISPATCHED"),
    },
  ];
  incomeConfig.options.scales.y.title.text = "$/hour";
  if (window.whatIfIncomeChart instanceof Chart) {
    window.whatIfIncomeChart.destroy();
  }
  window.whatIfIncomeChart = new Chart(
    uiSettings.ctxWhatIfIncome,
    incomeConfig
  );
}

export function initWhatIfWaitChart(uiSettings) {
  let waitConfig = clone(config);
  waitConfig.options = clone(options);
  waitConfig.data.labels = ["Passenger time"];
  waitConfig.data.datasets = [
    {
      label: "Waiting",
      data: null,
      backgroundColor: colors.get("WAITING"),
    },
    {
      label: "Riding",
      data: null,
      backgroundColor: colors.get("RIDING"),
    },
  ];
  waitConfig.options.scales.y.title.text = "Minutes";
  if (window.whatIfWaitChart instanceof Chart) {
    window.whatIfWaitChart.destroy();
  }
  window.whatIfWaitChart = new Chart(uiSettings.ctxWhatIfWait, waitConfig);
}

export function initWhatIfNChart(uiSettings) {
  let nConfig = clone(config);
  nConfig.options = clone(options);
  nConfig.data.labels = ["Vehicles"];
  nConfig.data.datasets[0].backgroundColor = colors.get("DISPATCHED");
  nConfig.options.scales.y.title.text = "Number";
  if (window.whatIfNChart instanceof Chart) {
    window.whatIfNChart.destroy();
  }
  window.whatIfNChart = new Chart(uiSettings.ctxWhatIfN, nConfig);
}

export function plotWhatIfPhasesChart(eventData) {
  window.whatIfPhasesChart.data.datasets[0].data = [
    100.0 * eventData.get("VEHICLE_FRACTION_P1"),
  ];
  window.whatIfPhasesChart.data.datasets[1].data = [
    100.0 * eventData.get("VEHICLE_FRACTION_P2"),
  ];
  window.whatIfPhasesChart.data.datasets[2].data = [
    100.0 * eventData.get("VEHICLE_FRACTION_P3"),
  ];
  window.whatIfPhasesChart.update();
}

export function plotWhatIfIncomeChart(eventData) {
  window.whatIfIncomeChart.data.datasets[0].data = [
    eventData.get("VEHICLE_NET_INCOME"),
  ];
  window.whatIfIncomeChart.data.datasets[1].data = [
    eventData.get("VEHICLE_GROSS_INCOME") - eventData.get("VEHICLE_NET_INCOME"),
  ];
  window.whatIfIncomeChart.update();
}

export function plotWhatIfWaitChart(eventData) {
  window.whatIfWaitChart.data.datasets[0].data = [
    eventData.get("TRIP_MEAN_WAIT_TIME"),
  ];
  window.whatIfWaitChart.data.datasets[1].data = [
    eventData.get("TRIP_MEAN_RIDE_TIME"),
  ];
  window.whatIfWaitChart.update();
}

export function plotWhatIfNChart(eventData) {
  window.whatIfNChart.data.datasets[0].data = [
    eventData.get("VEHICLE_MEAN_COUNT"),
  ];
  window.whatIfNChart.update();
}
