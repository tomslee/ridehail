/* global  Chart */
import { colors } from "../main.js";

export function initWhatIfChart(uiSettings, simSettings) {
  let suggestedIncomeMax =
    (simSettings.per_km_price * simSettings.mean_vehicle_speed +
      simSettings.per_minute_price * 60) *
    (1.0 - simSettings.platform_commission);

  const whatIfChartOptions = {
    responsive: true,
    aspectRatio: 2,
    layout: {
      padding: 0,
    },
    // indexAxis: "y",
    scales: {
      yFraction: {
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
      yIncome: {
        stacked: false,
        min: 0,
        suggestedMax: suggestedIncomeMax,
        position: "right",
        grid: {
          drawOnChartArea: false, // only want the grid lines for one axis to show up
        },
        title: {
          display: true,
          text: "Income ($/hour)",
        },
      },
    },
    plugins: {
      legend: {
        display: false,
      },
    },
  };

  let labels = ["P3", "Net Income"];
  let backgroundColor = [colors.get("WITH_RIDER")];

  const whatIfChartConfig = {
    type: "bar",
    data: {
      labels: labels,
      datasets: [
        {
          yAxisID: "yFraction",
          backgroundColor: backgroundColor,
          data: null,
        },
        {
          yAxisID: "yIncome",
          backgroundColor: colors.get("DISPATCHED"),
          data: null,
        },
      ],
    },
    options: whatIfChartOptions,
  };
  if (window.whatIfChart instanceof Chart) {
    window.whatIfChart.destroy();
  }
  window.whatIfChart = new Chart(uiSettings.ctx, whatIfChartConfig);
}

export function plotWhatIfChart(eventData) {
  if (eventData != null) {
    //let time = Math.round((Date.now() - startTime) / 100) * 100;
    // let platformCommission = eventData.get("platform_commission");
    // let price = eventData.get("TRIP_MEAN_PRICE");
    window.whatIfChart.options.plugins.title.text = "Driver income";
    window.whatIfChart.data.datasets[0].data = [
      eventData.get("VEHICLE_FRACTION_P3"),
      0,
    ];
    window.whatIfChart.data.datasets[1].data = [
      0,
      eventData.get("VEHICLE_NET_INCOME"),
    ];
    window.whatIfChart.update();
  }
}
