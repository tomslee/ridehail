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
  options: { color: "white" },
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
    legend: false,
  },
};

export function initWhatIfPhasesChart(baselineData, uiSettings) {
  let phasesConfig = clone(config);
  phasesConfig.options = clone(options);
  phasesConfig.data.labels = ["Vehicle phases"];
  phasesConfig.options.scales.y.title.text = "Percentage";
  phasesConfig.options.scales.y.max = 100;
  phasesConfig.data.datasets = [
    {
      label: "P3",
      data: null,
      backgroundColor: colors.get("WITH_RIDER"),
      stack: "Stack 0",
    },
    {
      label: "P2",
      data: null,
      backgroundColor: colors.get("DISPATCHED"),
      stack: "Stack 0",
    },
    {
      label: "P1",
      data: null,
      backgroundColor: colors.get("IDLE"),
      stack: "Stack 0",
    },
    {
      label: "P3",
      data: null,
      backgroundColor: colors.get("WITH_RIDER"),
      stack: "Stack 1",
    },
    {
      label: "P2",
      data: null,
      backgroundColor: colors.get("DISPATCHED"),
      stack: "Stack 1",
    },
    {
      label: "P1",
      data: null,
      backgroundColor: colors.get("IDLE"),
      stack: "Stack 1",
    },
  ];
  phasesConfig.options.plugins.datalabels = {
    align: "center",
    anchor: "center",
    color: "blue",
    display: true,
    font: { weight: "bold" },
    formatter: Math.round,
  };
  if (window.whatIfPhasesChart instanceof Chart) {
    window.whatIfPhasesChart.destroy();
  }
  window.whatIfPhasesChart = new Chart(
    uiSettings.ctxWhatIfPhases,
    phasesConfig
  );
  window.whatIfPhasesChart.canvas.parentNode.style.height = "128px";
}

export function initWhatIfIncomeChart(baselineData, uiSettings) {
  let incomeConfig = clone(config);
  incomeConfig.options = clone(options);
  incomeConfig.options.scales.y.suggestedMax = 30;
  incomeConfig.data.labels = ["Driver income"];
  incomeConfig.data.datasets = [
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
    {
      label: "Net",
      data: null,
      backgroundColor: colors.get("WITH_RIDER"),
      stack: "Stack 1",
      datalabels: { align: "center", anchor: "center" },
    },
    {
      label: "Expenses",
      data: null,
      backgroundColor: colors.get("DISPATCHED"),
      stack: "Stack 1",
    },
    {
      label: "Unpaid time",
      data: null,
      backgroundColor: colors.get("IDLE"),
      stack: "Stack 1",
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
  window.whatIfIncomeChart.canvas.parentNode.style.height = "128px";
}

export function initWhatIfWaitChart(baselineData, uiSettings) {
  let waitConfig = clone(config);
  waitConfig.options = clone(options);
  waitConfig.options.scales.y.suggestedMax = 24;
  waitConfig.data.labels = ["Passenger time"];
  waitConfig.data.datasets = [
    {
      label: "Waiting",
      data: null,
      backgroundColor: colors.get("WAITING"),
      stack: "Stack 0",
    },
    {
      label: "Riding",
      data: null,
      backgroundColor: colors.get("RIDING"),
      stack: "Stack 0",
    },
    {
      label: "Waiting",
      data: null,
      backgroundColor: colors.get("WAITING"),
      stack: "Stack 1",
    },
    {
      label: "Riding",
      data: null,
      backgroundColor: colors.get("RIDING"),
      stack: "Stack 1",
    },
  ];
  waitConfig.options.scales.y.title.text = "Minutes";
  if (window.whatIfWaitChart instanceof Chart) {
    window.whatIfWaitChart.destroy();
  }
  window.whatIfWaitChart = new Chart(uiSettings.ctxWhatIfWait, waitConfig);
  window.whatIfWaitChart.canvas.parentNode.style.height = "128px";
}

export function initWhatIfNChart(baselineData, uiSettings) {
  let nConfig = clone(config);
  nConfig.options = clone(options);
  nConfig.options.scales.y.suggestedMax = 240;
  nConfig.data.labels = ["Vehicles"];
  nConfig.data.datasets = [
    {
      label: "Vehicles",
      data: null,
      backgroundColor: colors.get("DISPATCHED"),
      stack: "Stack 0",
    },
    {
      label: "Vehicles",
      data: null,
      backgroundColor: colors.get("DISPATCHED"),
      stack: "Stack 1",
    },
  ];
  nConfig.options.scales.y.title.text = "Number";
  if (window.whatIfNChart instanceof Chart) {
    window.whatIfNChart.destroy();
  }
  window.whatIfNChart = new Chart(uiSettings.ctxWhatIfN, nConfig);
  window.whatIfNChart.canvas.parentNode.style.height = "128px";
}

export function initWhatIfPlatformChart(baselineData, uiSettings) {
  let platformConfig = clone(config);
  platformConfig.options = clone(options);
  platformConfig.options.scales.y.suggestedMax = 30;
  platformConfig.data.labels = ["Platform income"];
  platformConfig.data.datasets = [
    {
      label: "Income",
      data: null,
      backgroundColor: colors.get("IDLE"),
      stack: "Stack 0",
      datalabels: { align: "center", anchor: "center" },
    },
    {
      label: "Income",
      data: null,
      backgroundColor: colors.get("IDLE"),
      stack: "Stack 1",
      datalabels: { align: "center", anchor: "center" },
    },
  ];
  platformConfig.options.scales.y.title.text = "$/hour";
  if (window.whatIfPlatformChart instanceof Chart) {
    window.whatIfPlatformChart.destroy();
  }
  window.whatIfPlatformChart = new Chart(
    uiSettings.ctxWhatIfPlatform,
    platformConfig
  );
  window.whatIfPlatformChart.canvas.parentNode.style.height = "128px";
}

export function plotWhatIfPhasesChart(baselineData, eventData) {
  let stackData = [];
  if (!baselineData) {
    stackData[0] = [
      100.0 * eventData.get("VEHICLE_FRACTION_P3"),
      100.0 * eventData.get("VEHICLE_FRACTION_P2"),
      100.0 * eventData.get("VEHICLE_FRACTION_P1"),
    ];
    stackData[1] = [0.0, 0.0, 0.0];
  } else {
    stackData[0] = [
      100.0 * baselineData.get("VEHICLE_FRACTION_P3"),
      100.0 * baselineData.get("VEHICLE_FRACTION_P2"),
      100.0 * baselineData.get("VEHICLE_FRACTION_P1"),
    ];
    stackData[1] = [
      100.0 * eventData.get("VEHICLE_FRACTION_P3"),
      100.0 * eventData.get("VEHICLE_FRACTION_P2"),
      100.0 * eventData.get("VEHICLE_FRACTION_P1"),
    ];
  }
  window.whatIfPhasesChart.data.datasets[0].data = [stackData[0][0]];
  window.whatIfPhasesChart.data.datasets[1].data = [stackData[0][1]];
  window.whatIfPhasesChart.data.datasets[2].data = [stackData[0][2]];
  window.whatIfPhasesChart.data.datasets[3].data = [stackData[1][0]];
  window.whatIfPhasesChart.data.datasets[4].data = [stackData[1][1]];
  window.whatIfPhasesChart.data.datasets[5].data = [stackData[1][2]];
  window.whatIfPhasesChart.update();
}

export function plotWhatIfIncomeChart(baselineData, eventData) {
  let stackData = [];
  let eventGross = 60 * eventData.get("VEHICLE_GROSS_INCOME");
  let eventExpenses = 30 * eventData.get("per_km_ops_cost");
  let eventOnTheClock = eventGross / eventData.get("VEHICLE_FRACTION_P3");
  if (!baselineData) {
    stackData[0] = [
      eventGross - eventExpenses,
      eventExpenses,
      eventOnTheClock - eventGross,
    ];
    stackData[1] = [0, 0, 0];
  } else {
    let baselineGross = 60 * baselineData.get("VEHICLE_GROSS_INCOME");
    let baselineExpenses = 30 * baselineData.get("per_km_ops_cost");
    let baselineOnTheClock =
      baselineGross / baselineData.get("VEHICLE_FRACTION_P3");
    stackData[0] = [
      baselineGross - baselineExpenses,
      baselineExpenses,
      baselineOnTheClock - baselineGross,
    ];
    stackData[1] = [
      eventGross - eventExpenses,
      eventExpenses,
      eventOnTheClock - eventGross,
    ];
  }
  window.whatIfIncomeChart.data.datasets[0].data = [stackData[0][0]];
  window.whatIfIncomeChart.data.datasets[1].data = [stackData[0][1]];
  window.whatIfIncomeChart.data.datasets[2].data = [stackData[0][2]];
  window.whatIfIncomeChart.data.datasets[3].data = [stackData[1][0]];
  window.whatIfIncomeChart.data.datasets[4].data = [stackData[1][1]];
  window.whatIfIncomeChart.data.datasets[5].data = [stackData[1][2]];
  window.whatIfIncomeChart.update();
}

export function plotWhatIfWaitChart(baselineData, eventData) {
  let stackData = [];
  if (!baselineData) {
    stackData[0] = [
      eventData.get("TRIP_MEAN_WAIT_TIME"),
      eventData.get("TRIP_MEAN_RIDE_TIME"),
    ];
    stackData[1] = [0, 0];
  } else {
    stackData[0] = [
      baselineData.get("TRIP_MEAN_WAIT_TIME"),
      baselineData.get("TRIP_MEAN_RIDE_TIME"),
    ];
    stackData[1] = [
      eventData.get("TRIP_MEAN_WAIT_TIME"),
      eventData.get("TRIP_MEAN_RIDE_TIME"),
    ];
  }
  window.whatIfWaitChart.data.datasets[0].data = [stackData[0][0]];
  window.whatIfWaitChart.data.datasets[1].data = [stackData[0][1]];
  window.whatIfWaitChart.data.datasets[2].data = [stackData[1][0]];
  window.whatIfWaitChart.data.datasets[3].data = [stackData[1][1]];
  window.whatIfWaitChart.update();
}

export function plotWhatIfNChart(baselineData, eventData) {
  let stackData = [];
  if (!baselineData) {
    stackData[0] = [eventData.get("VEHICLE_MEAN_COUNT")];
    stackData[1] = [0];
  } else {
    stackData[0] = [baselineData.get("VEHICLE_MEAN_COUNT")];
    stackData[1] = [eventData.get("VEHICLE_MEAN_COUNT")];
  }
  window.whatIfNChart.data.datasets[0].data = [stackData[0][0]];
  window.whatIfNChart.data.datasets[1].data = [stackData[1][0]];
  window.whatIfNChart.update();
}

export function plotWhatIfPlatformChart(baselineData, eventData) {
  let stackData = [];
  // TODO: Hack to add $2.50 per trip
  if (!baselineData) {
    stackData[0] = [
      60.0 * eventData.get("PLATFORM_MEAN_INCOME") +
        2.5 * 60.0 * eventData.get("TRIP_MEAN_REQUEST_RATE"),
    ];
    stackData[1] = [0];
  } else {
    stackData[0] = [
      60.0 * baselineData.get("PLATFORM_MEAN_INCOME") +
        2.5 * 60.0 * baselineData.get("TRIP_MEAN_REQUEST_RATE"),
    ];
    stackData[1] = [
      60.0 * eventData.get("PLATFORM_MEAN_INCOME") +
        2.5 * 60.0 * eventData.get("TRIP_MEAN_REQUEST_RATE"),
    ];
  }
  window.whatIfPlatformChart.data.datasets[0].data = [stackData[0][0]];
  window.whatIfPlatformChart.data.datasets[1].data = [stackData[1][0]];
  window.whatIfPlatformChart.update();
}
