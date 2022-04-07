/* global  Chart ChartDataLabels */
import { colors } from "../main.js";

Chart.register(ChartDataLabels);

function clone(o) {
  return JSON.parse(JSON.stringify(o));
}

var settingsTable;
// var measuresTable

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
  phasesConfig.options.scales.y.title.text = "Time %";
  phasesConfig.options.scales.y.max = 100;
  phasesConfig.data.datasets = [
    {
      label: "P3",
      data: null,
      backgroundColor: colors.get("WITH_RIDER"),
      stack: "Stack 0",
      datalabels: { align: "top", anchor: "start" },
    },
    {
      label: "P2",
      data: null,
      backgroundColor: colors.get("DISPATCHED"),
      stack: "Stack 0",
      datalabels: { align: "center", anchor: "center" },
    },
    {
      label: "P1",
      data: null,
      backgroundColor: colors.get("IDLE"),
      stack: "Stack 0",
      datalabels: { align: "bottom", anchor: "end" },
    },
    {
      label: "P3",
      data: null,
      backgroundColor: colors.get("WITH_RIDER"),
      stack: "Stack 1",
      datalabels: { align: "top", anchor: "start" },
    },
    {
      label: "P2",
      data: null,
      backgroundColor: colors.get("DISPATCHED"),
      stack: "Stack 1",
      datalabels: { align: "center", anchor: "center" },
    },
    {
      label: "P1",
      data: null,
      backgroundColor: colors.get("IDLE"),
      stack: "Stack 1",
      datalabels: { align: "bottom", anchor: "end" },
    },
  ];
  phasesConfig.options.plugins.datalabels = {
    color: "#666",
    display: true,
    font: { weight: "bold" },
    formatter: function (value) {
      return Math.round(value) + "%";
    },
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
      label: "Unpaid time",
      data: null,
      backgroundColor: colors.get("IDLE"),
      stack: "Stack 0",
      datalabels: { align: "bottom", anchor: "end" },
    },
    {
      label: "Net",
      data: null,
      backgroundColor: colors.get("WITH_RIDER"),
      stack: "Stack 1",
      datalabels: { align: "top", anchor: "start" },
    },
    {
      label: "Expenses",
      data: null,
      backgroundColor: colors.get("DISPATCHED"),
      stack: "Stack 1",
      datalabels: { align: "center", anchor: "center" },
    },
    {
      label: "Unpaid time",
      data: null,
      backgroundColor: colors.get("IDLE"),
      stack: "Stack 1",
      datalabels: { align: "bottom", anchor: "end" },
    },
  ];
  incomeConfig.options.scales.y.title.text = "$/hour";
  incomeConfig.options.plugins.datalabels = {
    color: "#666",
    display: true,
    font: { weight: "bold" },
    formatter: function (value) {
      return Math.round(value * 10) / 10;
    },
  };
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
      datalabels: { align: "top", anchor: "start" },
    },
    {
      label: "Riding",
      data: null,
      backgroundColor: colors.get("RIDING"),
      stack: "Stack 0",
      datalabels: { align: "bottom", anchor: "end" },
    },
    {
      label: "Waiting",
      data: null,
      backgroundColor: colors.get("WAITING"),
      stack: "Stack 1",
      datalabels: { align: "top", anchor: "start" },
    },
    {
      label: "Riding",
      data: null,
      backgroundColor: colors.get("RIDING"),
      stack: "Stack 1",
      datalabels: { align: "bottom", anchor: "end" },
    },
  ];
  waitConfig.options.scales.y.title.text = "Minutes";
  waitConfig.options.plugins.datalabels = {
    align: "center",
    anchor: "center",
    color: "#666",
    display: true,
    font: { weight: "bold" },
    formatter: function (value) {
      return Math.round(value * 10) / 10;
    },
  };
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
      datalabels: { align: "center", anchor: "center" },
    },
    {
      label: "Vehicles",
      data: null,
      backgroundColor: colors.get("DISPATCHED"),
      stack: "Stack 1",
      datalabels: { align: "center", anchor: "center" },
    },
  ];
  nConfig.options.scales.y.title.text = "Number";
  nConfig.options.plugins.datalabels = {
    align: "start",
    anchor: "start",
    color: "#666",
    display: true,
    font: { weight: "bold" },
    formatter: Math.round,
  };
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
  platformConfig.options.plugins.datalabels = {
    align: "center",
    anchor: "center",
    color: "#666",
    display: true,
    font: { weight: "bold" },
    formatter: Math.round,
  };
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
  let display = [true, true];
  if (!baselineData) {
    stackData[0] = [
      100.0 * eventData.get("VEHICLE_FRACTION_P3"),
      100.0 * eventData.get("VEHICLE_FRACTION_P2"),
      100.0 * eventData.get("VEHICLE_FRACTION_P1"),
    ];
    stackData[1] = [0.0, 0.0, 0.0];
    display[1] = false;
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
  window.whatIfPhasesChart.data.datasets[0].datalabels.display = display[0];
  window.whatIfPhasesChart.data.datasets[1].datalabels.display = display[0];
  window.whatIfPhasesChart.data.datasets[2].datalabels.display = display[0];
  window.whatIfPhasesChart.data.datasets[3].datalabels.display = display[1];
  window.whatIfPhasesChart.data.datasets[4].datalabels.display = display[1];
  window.whatIfPhasesChart.data.datasets[5].datalabels.display = display[1];
  window.whatIfPhasesChart.update();
}

export function plotWhatIfIncomeChart(baselineData, eventData) {
  let stackData = [];
  let display = [true, true];
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
    display[1] = false;
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
  window.whatIfIncomeChart.data.datasets[0].datalabels.display = display[0];
  window.whatIfIncomeChart.data.datasets[1].datalabels.display = display[0];
  window.whatIfIncomeChart.data.datasets[2].datalabels.display = display[0];
  window.whatIfIncomeChart.data.datasets[3].datalabels.display = display[1];
  window.whatIfIncomeChart.data.datasets[4].datalabels.display = display[1];
  window.whatIfIncomeChart.data.datasets[5].datalabels.display = display[1];
  window.whatIfIncomeChart.update();
}

export function plotWhatIfWaitChart(baselineData, eventData) {
  let stackData = [];
  let display = [true, true];
  if (!baselineData) {
    stackData[0] = [
      eventData.get("TRIP_MEAN_WAIT_TIME"),
      eventData.get("TRIP_MEAN_RIDE_TIME"),
    ];
    stackData[1] = [0, 0];
    display[1] = false;
  } else {
    stackData[0] = [
      baselineData.get("TRIP_MEAN_WAIT_TIME"),
      baselineData.get("TRIP_MEAN_RIDE_TIME"),
    ];
    display[0] = true;
    stackData[1] = [
      eventData.get("TRIP_MEAN_WAIT_TIME"),
      eventData.get("TRIP_MEAN_RIDE_TIME"),
    ];
    display[0] = true;
  }
  window.whatIfWaitChart.data.datasets[0].data = [stackData[0][0]];
  window.whatIfWaitChart.data.datasets[1].data = [stackData[0][1]];
  window.whatIfWaitChart.data.datasets[2].data = [stackData[1][0]];
  window.whatIfWaitChart.data.datasets[3].data = [stackData[1][1]];
  window.whatIfWaitChart.data.datasets[0].datalabels.display = display[0];
  window.whatIfWaitChart.data.datasets[1].datalabels.display = display[0];
  window.whatIfWaitChart.data.datasets[2].datalabels.display = display[1];
  window.whatIfWaitChart.data.datasets[3].datalabels.display = display[1];
  window.whatIfWaitChart.update();
}

export function plotWhatIfNChart(baselineData, eventData) {
  let stackData = [];
  let display = [true, true];
  if (!baselineData) {
    stackData[0] = [eventData.get("VEHICLE_MEAN_COUNT")];
    stackData[1] = [0];
    display[1] = false;
  } else {
    stackData[0] = [baselineData.get("VEHICLE_MEAN_COUNT")];
    stackData[1] = [eventData.get("VEHICLE_MEAN_COUNT")];
  }
  window.whatIfNChart.data.datasets[0].data = [stackData[0][0]];
  window.whatIfNChart.data.datasets[1].data = [stackData[1][0]];
  window.whatIfNChart.data.datasets[0].datalabels.display = display[0];
  window.whatIfNChart.data.datasets[1].datalabels.display = display[1];
  window.whatIfNChart.update();
}

export function plotWhatIfPlatformChart(baselineData, eventData) {
  let stackData = [];
  let display = [true, true];
  // TODO: Hack to add $2.50 per trip
  if (!baselineData) {
    stackData[0] = [
      60.0 * eventData.get("PLATFORM_MEAN_INCOME") +
        2.5 * 60.0 * eventData.get("TRIP_MEAN_REQUEST_RATE"),
    ];
    stackData[1] = [0];
    display[1] = false;
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
  window.whatIfPlatformChart.data.datasets[0].datalabels.display = display[0];
  window.whatIfPlatformChart.data.datasets[1].datalabels.display = display[1];
  window.whatIfPlatformChart.update();
}

export function initWhatIfSettingsTable(baselineData, uiSettings) {
  settingsTable = uiSettings.settingsTable;
  let settings_list = [
    "what-if-settings-time-blocks-baseline",
    "what-if-settings-price-baseline",
    "what-if-settings-per-km-price-baseline",
    "what-if-settings-per-min-price-baseline",
  ];
  settings_list.forEach(function (id) {
    let cell = settingsTable.querySelector("#" + id);
    cell.innerHTML = Math.round(100 * Math.random());
  });
}

export function fillWhatIfSettingsTable(baselineData, eventData) {
  let settings = {
    "what-if-settings-time-blocks-baseline": "time_blocks",
    "what-if-settings-price-baseline": "price",
    "what-if-settings-per-km-price-baseline": "per_km_price",
    "what-if-settings-per-min-price-baseline": "per_minute_price",
  };
  for (const [key, value] of Object.entries(settings)) {
    let cell = settingsTable.querySelector("#" + key);
    cell.innerHTML = eventData.get(value);
  }
}
