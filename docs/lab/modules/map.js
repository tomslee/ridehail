/* global Chart */
import { colors } from "../main.js";
// const startTime = Date.now();

var citySize = 0;

export function initMap(uiSettings, simSettings) {
  // data sets:
  // [0] - vehicles
  // [1] - trips
  citySize = simSettings.citySize;
  const mapOptions = {
    responsive: true,
    aspectRatio: 1,
    layout: {
      padding: 0,
    },
    scales: {
      xAxis: {
        min: -0.5,
        max: simSettings.citySize - 0.5,
        grid: {
          drawBorder: false,
          borderWidth: 1,
          borderColor: "grey",
          lineWidth: uiSettings.roadWidth,
          color: colors.get("ROAD"),
          drawTicks: false,
        },
        type: "linear",
        ticks: {
          display: false,
          // beginAtZero: true,
          includeBounds: false,
          maxTicksLimits: citySize,
          drawOnChartArea: true,
          drawTicks: false,
          stepSize: 0.5,
          callback: function (tick, index) {
            return index % 2 != 0 ? "" : null;
          },
        },
        // position: {yAxis: 0.0},
      },
      yAxis: {
        min: -0.5,
        max: citySize - 0.5,
        grid: {
          drawBorder: false,
          borderWidth: 1,
          borderColor: "grey",
          lineWidth: uiSettings.roadWidth,
          color: colors.get("ROAD"),
          drawTicks: false,
        },
        type: "linear",
        ticks: {
          display: false,
          // beginAtZero: true,
          includeBounds: false,
          maxTicksLimits: citySize,
          drawOnChartArea: true,
          drawTicks: false,
          stepSize: 0.5,
          callback: function (tick, index) {
            return index % 2 != 0 ? "" : null;
          },
        },
        // position: {xAxis: 0.0},
      },
    },
    elements: {
      line: {
        borderWidth: 0,
        tension: 0.4,
      },
    },
    transitions: {
      duration: 0,
      easing: "linear",
      delay: 0,
      loop: false,
    },
    animation: {
      duration: 0,
      easing: "linear",
      delay: 0,
      loop: false,
      // onComplete: function(animation){
      // animation.chart.data.datasets[0].pointBackgroundColor = 'rgba(0, 255, 0, 0.8)';
      // }
    },
    animations: {
      properties: ["x", "y"],
    },
    plugins: {
      legend: {
        display: false,
      },
    },
  };

  const mapConfig = {
    type: "scatter",
    data: {
      datasets: [
        {
          // vehicles
          data: null,
          pointStyle: "triangle",
          pointRadius: uiSettings.vehicleRadius,
          borderColor: "grey",
          borderWidth: 1,
          hoverRadius: 16,
        },
        {
          // trips
          data: null,
          pointStyle: "circle",
          pointRadius: uiSettings.vehicleRadius,
          borderColor: "grey",
          borderWidth: 1,
        },
      ],
    },
    options: mapOptions,
  };
  //options: {}

  if (window.chart instanceof Chart) {
    window.chart.destroy();
  }
  if (window.statsChart instanceof Chart) {
    window.statsChart.destroy();
  }
  window.chart = new Chart(uiSettings.ctx, mapConfig);
}

// Handle map simSettings
export function plotMap(eventData) {
  if (eventData != null) {
    if (eventData.size < 2) {
      console.log("m: error? ", eventData);
    }
    // "block": integer,
    let frameIndex = eventData.get("block");
    //  "vehicles": [[phase.name, location, direction],...],
    let vehicles = eventData.get("vehicles");
    let frameTimeout = eventData.get("frameTimeout");
    let vehicleLocations = [];
    let vehicleColors = [];
    let vehicleRotations = [];
    vehicles.forEach((vehicle) => {
      vehicleColors.push(colors.get(vehicle[0]));
      vehicleLocations.push({ x: vehicle[1][0], y: vehicle[1][1] });
      let rot = 0;
      if (vehicle[2] == "NORTH") {
        rot = 0;
      } else if (vehicle[2] == "EAST") {
        rot = 90;
      } else if (vehicle[2] == "SOUTH") {
        rot = 180;
      } else if (vehicle[2] == "WEST") {
        rot = 270;
      }
      vehicleRotations.push(rot);
    });
    // "trips": [[phase.name, origin, destination, distance],...],
    let trips = eventData.get("trips");
    let tripLocations = [];
    let tripColors = [];
    let tripStyles = [];
    trips.forEach((trip) => {
      /* Trip phases: INACTIVE = 0, UNASSIGNED = 1, WAITING = 2
                      RIDING = 3, COMPLETED = 4, CANCELLED = 5
    */
      if (trip[0] == "UNASSIGNED" || trip[0] == "WAITING") {
        tripLocations.push({ x: trip[1][0], y: trip[1][1] });
        tripColors.push(colors.get(trip[0]));
        tripStyles.push("rectRot");
      } else if (trip[0] == "RIDING") {
        tripLocations.push({ x: trip[2][0], y: trip[2][1] });
        tripColors.push(colors.get(trip[0]));
        tripStyles.push("circle");
      }
    });
    // let time = Math.round((Date.now() - startTime) / 100) * 100;
    // console.log("m (", time, "): Regular-updated chart: locations[0] = ", locations[0]);
    if (frameIndex % 2 != 0) {
      // interpolation point: change directions and trip marker location
      window.chart.data.datasets[1].pointBackgroundColor = tripColors;
      window.chart.data.datasets[1].pointStyle = tripStyles;
      window.chart.data.datasets[1].animationDuration = 0;
      window.chart.data.datasets[1].data = tripLocations;
      window.chart.data.datasets[0].rotation = vehicleRotations;
    }
    window.chart.options.animation.duration = 0;
    window.chart.update("none");
    window.chart.data.datasets[0].data = vehicleLocations;
    if (frameIndex == 0) {
      window.chart.options.animation.duration = 0;
    } else {
      window.chart.options.animation.duration = frameTimeout;
    }
    window.chart.data.datasets[0].pointBackgroundColor = vehicleColors;
    window.chart.update();
    let needsRefresh = false;
    let updatedLocations = [];
    vehicleLocations.forEach((vehicle) => {
      let newX = vehicle.x;
      let newY = vehicle.y;
      if (vehicle.x > citySize - 0.6) {
        // going off the right side
        newX = -0.5;
        needsRefresh = true;
      }
      if (vehicle.x < -0.1) {
        // going off the left side
        newX = citySize - 0.5;
        needsRefresh = true;
      }
      if (vehicle.y > citySize - 0.9) {
        // going off the top
        newY = -0.5;
        needsRefresh = true;
      }
      if (vehicle.y < -0.1) {
        // going off the bottom
        newY = citySize - 0.5;
        needsRefresh = true;
      }
      updatedLocations.push({ x: newX, y: newY });
    });
    // if (x > 1.9){
    if (needsRefresh == true) {
      // Reappear on the opposite  side of the chart
      // time = Math.round((Date.now() - startTime) / 100) * 100;
      // console.log("m (", time, "): Edge-updated chart: locations[0] = ", updatedLocations[0]);
      window.chart.data.datasets[0].pointBackgroundColor = vehicleColors;
      window.chart.data.datasets[0].rotation = vehicleRotations;
      window.chart.update("none");
      window.chart.data.datasets[0].data = updatedLocations;
      window.chart.data.datasets[0].pointBackgroundColor = vehicleColors;
      window.chart.update("none");
    }
  }
}
