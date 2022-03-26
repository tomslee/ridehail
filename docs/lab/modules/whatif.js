/* global  Chart */
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
};

const options = {
  responsive: true,
  aspectRatio: 0.5,
  layout: {
    padding: 0,
  },
  scales: {
    y: {
      stacked: false,
      min: 0.0,
      suggestedMax: 1.0,
      grid: {
        linewidth: 1,
        borderWidth: 1,
        drawOnChartArea: true, // only want the grid lines for one axis to show up
      },
      title: {
        display: true,
        text: null,
      },
      type: "linear",
    },
  },
  plugins: {
    legend: {
      display: false,
    },
  },
};

export function initWhatIfIncomeChart(uiSettings) {
  let incomeConfig = clone(config);
  incomeConfig.options = clone(options);
  incomeConfig.data.labels = ["Net income"];
  incomeConfig.data.datasets[0].backgroundColor = colors.get("PURPLE");
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
  waitConfig.data.labels = ["Wait time"];
  waitConfig.data.datasets[0].backgroundColor = colors.get("IDLE");
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

export function initWhatIfP3Chart(uiSettings) {
  const whatIfP3ChartOptions = {
    responsive: true,
    aspectRatio: 0.5,
    layout: {
      padding: 0,
    },
    scales: {
      y: {
        stacked: false,
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
          text: "Fraction",
        },
      },
    },
    plugins: {
      legend: {
        display: false,
      },
      title: {
        text: "P3 time",
      },
    },
  };

  let labels = ["Idle time"];
  let backgroundColor = [colors.get("WITH_RIDER")];

  const whatIfP3ChartConfig = {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          yAxisID: "y",
          backgroundColor: backgroundColor,
          data: null,
        },
      ],
    },
    options: whatIfP3ChartOptions,
  };

  if (window.whatIfP3Chart instanceof Chart) {
    window.whatIfP3Chart.destroy();
  }
  window.whatIfP3Chart = new Chart(uiSettings.ctxWhatIfP3, whatIfP3ChartConfig);
}

export function plotWhatIfP3Chart(eventData) {
  window.whatIfP3Chart.data.datasets[0].data = [
    eventData.get("VEHICLE_FRACTION_P1"),
  ];
  window.whatIfP3Chart.update();
}

export function plotWhatIfIncomeChart(eventData) {
  window.whatIfIncomeChart.data.datasets[0].data = [
    eventData.get("VEHICLE_NET_INCOME"),
  ];
  window.whatIfIncomeChart.update();
}

export function plotWhatIfWaitChart(eventData) {
  window.whatIfWaitChart.data.datasets[0].data = [
    eventData.get("TRIP_MEAN_WAIT_TIME"),
  ];
  window.whatIfWaitChart.update();
}

export function plotWhatIfNChart(eventData) {
  window.whatIfNChart.data.datasets[0].data = [
    eventData.get("VEHICLE_MEAN_COUNT"),
  ];
  window.whatIfNChart.update();
}
