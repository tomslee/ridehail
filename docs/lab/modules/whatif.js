/* global  Chart ChartDataLabels */
import { colors } from "../main.js";

Chart.register(ChartDataLabels);

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
  options: { color: "white" },
};

const options = {
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
  let useCityScale = eventData.get("use_city_scale");
  let eventGross = eventData.get("VEHICLE_GROSS_INCOME");
  let eventExpenses =
    eventData.get("mean_vehicle_speed") * eventData.get("per_km_ops_cost");
  let eventP3 = eventData.get("VEHICLE_FRACTION_P3");
  let eventOnTheClock = eventGross / eventP3;
  if (!useCityScale) {
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
    if (!useCityScale) {
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

export function plotWhatIfPlatformChart(baselineData, eventData) {
  let stackData = [];
  let display = [true, true];
  let useCityScale = eventData.get("use_city_scale");
  let eventPlatformIncome = eventData.get("PLATFORM_MEAN_INCOME");
  if (!useCityScale) {
    eventPlatformIncome = 60.0 * eventPlatformIncome;
  }
  if (!baselineData) {
    // this is the baseline run. eventData represents the baseline [0].
    stackData[0] = [eventPlatformIncome];
    stackData[1] = [0];
    display[1] = false;
  } else {
    let baselinePlatformIncome = baselineData.get("PLATFORM_MEAN_INCOME");
    if (!useCityScale) {
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

export function fillWhatIfSettingsTable(baselineData, eventData) {
  let tableBody = document.getElementById("what-if-table-settings-body");
  let rows = [];
  let baselineSettings = null;
  let comparisonSettings = null;
  if (!baselineData) {
    baselineSettings = eventData;
    comparisonSettings = null;
  } else {
    baselineSettings = baselineData;
    comparisonSettings = eventData;
  }
  baselineSettings.forEach(function (value, key) {
    if (
      key.toLowerCase() === key &&
      !["block", "time_blocks", "name"].includes(key) &&
      (baselineSettings.get("use_city_scale") ||
        (!baselineSettings.get("use_city_scale") &&
          ![
            "per_km_price",
            "per_minute_price",
            "per_hour_opportunity_cost",
            "per_km_ops_cost",
            "mean_vehicle_speed",
            "minutes_per_block",
          ].includes(key)))
    ) {
      // 1. lower case means it's a setting, not a measure
      // 2. block is shown as "Frame" separately and
      //    name is purely internal
      // 3. if you are not using City Scale, don't list the settings
      //    that are ignored
      // 4. if you are using City Scale, we may need to recompute price and
      //    reservation wage from price components and costs
      let row = document.createElement("tr");
      let keyTag = document.createElement("td");
      keyTag.setAttribute("class", "mdl-data-table__cell--non-numeric");
      keyTag.innerHTML = key;
      let baselineValueTag = document.createElement("td");
      baselineValueTag.setAttribute("class", "mdl-data-table__cell");
      baselineValueTag.innerHTML = value;
      let comparisonValueTag = document.createElement("td");
      comparisonValueTag.setAttribute("class", "mdl-data-table__cell");
      if (comparisonSettings) {
        comparisonValueTag.innerHTML = comparisonSettings.get(key);
        if (value != comparisonSettings.get(key)) {
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
  let baselineSettings = null;
  let comparisonSettings = null;
  // eventData is a map. Trick to filter it from
  // https://stackoverflow.com/questions/48707227/how-to-filter-a-javascript-map
  if (!baselineData) {
    baselineSettings = eventData;
    comparisonSettings = null;
  } else {
    baselineSettings = baselineData;
    comparisonSettings = eventData;
  }
  // settingsArray = settingsArray.filter((key) => key.toLowerCase() === key);
  baselineSettings.forEach(function (value, key) {
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
      baselineValueTag.setAttribute("class", "mdl-data-table__cell");
      baselineValueTag.innerHTML = Math.round(100 * value) / 100.0;
      let comparisonValueTag = document.createElement("td");
      comparisonValueTag.setAttribute("class", "mdl-data-table__cell");
      if (comparisonSettings) {
        comparisonValueTag.innerHTML =
          Math.round(100 * comparisonSettings.get(key)) / 100.0;
      }
      row.appendChild(keyTag);
      row.appendChild(baselineValueTag);
      row.appendChild(comparisonValueTag);
      rows.push(row);
    }
  });
  tableBody.replaceChildren(...rows);
}
