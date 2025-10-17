/* global  Chart ChartDataLabels */
import { colors } from "../js/constants.js";
import { appState } from "../js/app-state.js";
import { WEB_TO_DESKTOP_MAPPING } from "../js/config-mapping.js";

Chart.register(ChartDataLabels);

function clone(o) {
  return JSON.parse(JSON.stringify(o));
}

const baseConfig = {
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

const baseOptions = {
  responsive: true,
  maintainAspectRatio: true,
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

export function initWhatIfPhasesChart(uiSettings) {
  let config = clone(baseConfig);
  config.options = clone(baseOptions);
  config.data.labels = ["Vehicle phases"];
  config.options.scales.y.title.text = "Time %";
  config.options.scales.y.max = 100;
  config.data.datasets = [
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
  config.options.plugins.datalabels = {
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
  window.whatIfPhasesChart = new Chart(uiSettings.ctxWhatIfPhases, config);
}

export function initWhatIfIncomeChart(uiSettings) {
  let config = clone(baseConfig);
  config.options = clone(baseOptions);
  config.options.scales.y.suggestedMax = 30;
  config.data.labels = ["Driver income"];
  config.data.datasets = [
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
  config.options.scales.y.title.text = "$/hour";
  config.options.plugins.datalabels = {
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
  window.whatIfIncomeChart = new Chart(uiSettings.ctxWhatIfIncome, config);
}

export function initWhatIfWaitChart(uiSettings) {
  let waitConfig = clone(baseConfig);
  waitConfig.options = clone(baseOptions);
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
}

export function initWhatIfNChart(uiSettings) {
  let config = clone(baseConfig);
  config.options = clone(baseOptions);
  config.options.scales.y.suggestedMax = 240;
  config.data.labels = ["Vehicles"];
  config.data.datasets = [
    {
      label: "Vehicles",
      data: null,
      backgroundColor: colors.get("DISPATCHED"),
      stack: "Stack 0",
      datalabels: { align: "bottom", anchor: "end" },
    },
    {
      label: "Vehicles",
      data: null,
      backgroundColor: colors.get("DISPATCHED"),
      stack: "Stack 1",
      datalabels: { align: "bottom", anchor: "end" },
    },
  ];
  config.options.scales.y.title.text = "Number";
  config.options.plugins.datalabels = {
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
  window.whatIfNChart = new Chart(uiSettings.ctxWhatIfN, config);
}

export function initWhatIfDemandChart(uiSettings) {
  let config = clone(baseConfig);
  config.options = clone(baseOptions);
  config.options.scales.y.suggestedMax = 10;
  config.data.labels = ["Demand"];
  config.data.datasets = [
    {
      label: "Requests",
      data: null,
      backgroundColor: colors.get("WAITING"),
      stack: "Stack 0",
      datalabels: { align: "bottom", anchor: "end" },
    },
    {
      label: "Requests",
      data: null,
      backgroundColor: colors.get("WAITING"),
      stack: "Stack 1",
      datalabels: { align: "bottom", anchor: "end" },
    },
  ];
  config.options.scales.y.title.text = "Requests/hour";
  config.options.plugins.datalabels = {
    align: "start",
    anchor: "start",
    color: "#666",
    display: true,
    font: { weight: "bold" },
    formatter: function (value) {
      return Math.round(value * 600) / 10;
    },
  };
  if (window.whatIfDemandChart instanceof Chart) {
    window.whatIfDemandChart.destroy();
  }
  window.whatIfDemandChart = new Chart(uiSettings.ctxWhatIfDemand, config);
}

export function initWhatIfPlatformChart(uiSettings) {
  let platformConfig = clone(baseConfig);
  platformConfig.options = clone(baseOptions);
  platformConfig.options.scales.y.suggestedMax = 30;
  platformConfig.data.labels = ["Platform income"];
  platformConfig.data.datasets = [
    {
      label: "Income",
      data: null,
      backgroundColor: colors.get("IDLE"),
      stack: "Stack 0",
      datalabels: { align: "bottom", anchor: "end" },
    },
    {
      label: "Income",
      data: null,
      backgroundColor: colors.get("IDLE"),
      stack: "Stack 1",
      datalabels: { align: "bottom", anchor: "end" },
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
    platformConfig,
  );
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
  let useCostsAndIncomes = eventData.get("use_city_scale");
  let eventGross = eventData.get("VEHICLE_GROSS_INCOME");
  let eventExpenses =
    eventData.get("mean_vehicle_speed") * eventData.get("per_km_ops_cost");
  let eventP3 = eventData.get("VEHICLE_FRACTION_P3");
  let eventOnTheClock = eventGross / eventP3;
  if (!useCostsAndIncomes) {
    eventGross = 60 * eventGross;
    eventOnTheClock = eventGross / eventP3;
  }
  if (!baselineData) {
    stackData[0] = [
      eventGross - eventExpenses,
      eventExpenses,
      eventOnTheClock - eventGross,
    ];
    stackData[1] = [0, 0, 0];
    display[1] = false;
  } else {
    let baselineGross = baselineData.get("VEHICLE_GROSS_INCOME");
    let baselineExpenses =
      baselineData.get("mean_vehicle_speed") *
      baselineData.get("per_km_ops_cost");
    let baselineP3 = baselineData.get("VEHICLE_FRACTION_P3");
    let baselineOnTheClock = baselineGross / baselineP3;
    if (!useCostsAndIncomes) {
      baselineGross = 60 * baselineGross;
      baselineOnTheClock = baselineGross / baselineP3;
    }
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

export function plotWhatIfDemandChart(baselineData, eventData) {
  let stackData = [];
  let display = [true, true];
  if (!baselineData) {
    stackData[0] = [eventData.get("TRIP_MEAN_REQUEST_RATE")];
    stackData[1] = [0];
    display[1] = false;
  } else {
    stackData[0] = [baselineData.get("TRIP_MEAN_REQUEST_RATE")];
    stackData[1] = [eventData.get("TRIP_MEAN_REQUEST_RATE")];
  }
  window.whatIfDemandChart.data.datasets[0].data = [stackData[0][0]];
  window.whatIfDemandChart.data.datasets[1].data = [stackData[1][0]];
  window.whatIfDemandChart.data.datasets[0].datalabels.display = display[0];
  window.whatIfDemandChart.data.datasets[1].datalabels.display = display[1];
  window.whatIfDemandChart.update();
}

export function plotWhatIfPlatformChart(baselineData, eventData) {
  let stackData = [];
  let display = [true, true];
  let useCostsAndIncomes = eventData.get("use_city_scale");
  let eventPlatformIncome = eventData.get("PLATFORM_MEAN_INCOME");
  if (!useCostsAndIncomes) {
    eventPlatformIncome = 60.0 * eventPlatformIncome;
  }
  if (!baselineData) {
    // this is the baseline run. eventData represents the baseline [0].
    stackData[0] = [eventPlatformIncome];
    stackData[1] = [0];
    display[1] = false;
  } else {
    let baselinePlatformIncome = baselineData.get("PLATFORM_MEAN_INCOME");
    if (!useCostsAndIncomes) {
      baselinePlatformIncome = 60.0 * baselinePlatformIncome;
    }
    stackData[0] = [baselinePlatformIncome];
    stackData[1] = [eventPlatformIncome];
  }
  window.whatIfPlatformChart.data.datasets[0].data = [stackData[0][0]];
  window.whatIfPlatformChart.data.datasets[1].data = [stackData[1][0]];
  window.whatIfPlatformChart.data.datasets[0].datalabels.display = display[0];
  window.whatIfPlatformChart.data.datasets[1].datalabels.display = display[1];
  window.whatIfPlatformChart.update();
}

export function initWhatIfTables() {
  document.getElementById("what-if-table-settings-body").replaceChildren();
  document.getElementById("what-if-table-measures-body").replaceChildren();
}

export function fillWhatIfSettingsTable(
  baselineSimSettings,
  comparisonSimSettings,
) {
  let tableBody = document.getElementById("what-if-table-settings-body");
  let rows = [];
  const excludeList = [
    "name",
    "frameIndex",
    "blockIndex",
    "action",
    "chartType",
    "scale",
  ];
  Object.entries(baselineSimSettings).forEach(([key, value]) => {
    if (!excludeList.includes(key)) {
      let row = document.createElement("tr");
      let keyTag = document.createElement("td");
      keyTag.setAttribute("class", "mdl-data-table__cell--non-numeric");
      keyTag.innerHTML = WEB_TO_DESKTOP_MAPPING[key].key;
      let baselineValueTag = document.createElement("td");
      let comparisonValueTag = document.createElement("td");
      baselineValueTag.innerHTML = value;
      if (comparisonSimSettings) {
        comparisonValueTag.innerHTML = comparisonSimSettings[key];
        if (value != comparisonSimSettings[key]) {
          let backgroundColor = colors.get("WAITING");
          row.style.backgroundColor = backgroundColor;
          row.style.fontWeight = "bold";
        }
      }
      row.appendChild(keyTag);
      row.appendChild(baselineValueTag);
      row.appendChild(comparisonValueTag);
      rows.push(row);
    }
  });
  tableBody.replaceChildren(...rows);
}

export function fillWhatIfMeasuresTable(baselineData, eventData) {
  let tableBody = document.getElementById("what-if-table-measures-body");
  let rows = [];
  let baselineMeasures = null;
  let comparisonMeasures = null;
  // eventData is a map. Trick to filter it from
  // https://stackoverflow.com/questions/48707227/how-to-filter-a-javascript-map
  if (!baselineData) {
    baselineMeasures = eventData;
    comparisonMeasures = null;
  } else {
    baselineMeasures = baselineData;
    comparisonMeasures = eventData;
  }
  // settingsArray = settingsArray.filter((key) => key.toLowerCase() === key);
  baselineMeasures.forEach(function (value, key) {
    if (
      key.toUpperCase() === key &&
      ![
        "VEHICLE_SUM_TIME",
        "TRIP_SUM_COUNT",
        "TRIP_COMPLETED_FRACTION",
      ].includes(key)
    ) {
      // lower case means it's a setting, not a measure
      let row = document.createElement("tr");
      let keyTag = document.createElement("td");
      keyTag.setAttribute("class", "mdl-data-table__cell--non-numeric");
      keyTag.innerHTML = key;
      let baselineValueTag = document.createElement("td");
      if (typeof value == "number") {
        baselineValueTag.innerHTML = Math.round(100 * value) / 100.0;
      } else {
        baselineValueTag.innerHTML = value;
      }
      let comparisonValueTag = document.createElement("td");
      if (comparisonMeasures) {
        const comparisonValue = comparisonMeasures.get(key);
        if (typeof comparisonValue == "number") {
          comparisonValueTag.innerHTML =
            Math.round(100 * comparisonMeasures.get(key)) / 100.0;
        } else {
          comparisonValueTag.innerHTML = comparisonValue;
        }
      }
      row.appendChild(keyTag);
      row.appendChild(baselineValueTag);
      row.appendChild(comparisonValueTag);
      rows.push(row);
    }
  });
  tableBody.replaceChildren(...rows);
}
