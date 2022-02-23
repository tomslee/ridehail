import {message, ctx} from "../main.js";
const colors = new Map();
colors.set("WITH_RIDER", "rgba(60, 179, 113, 0.4)");
colors.set("DISPATCHED", "rgba(255, 165, 0, 0.4)");
colors.set("IDLE", "rgba(0, 0, 255, 0.4)");
const startTime = Date.now();

export function initMapChart() { 
  const mapOptions = {
    scales: {
      xAxis: {
        min: -0.5,
        max: message.citySize - 0.5,
        grid: {
          borderWidth: 1,
          linewidth: 20,
        },
        type: 'linear',
        ticks: {
          display: true,
          includeBounds: false,
          maxTicksLimits: message.citySize,
        },
      },
      yAxis: {
        min: -0.5,
        max: message.citySize - 0.5,
        grid: {
          borderWidth: 1,
          linewidth: 1,
        },
        type: 'linear',
        ticks: {
          display: true,
          includeBounds: false,
          maxTicksLimits: message.citySize,
        },
      }
    },
    elements: {
      line: {
        borderWidth: 0,
        tension: 0.4,
      },
      point: {
        backgroundColor: 'rgba(255, 99, 132, 0.8)',
        borderWidth: 0,
        // radius: 1,
      }
    },
    transitions: {
      duration: message.frameTimeout,
      easing: 'linear',
      delay: 0,
      loop: false
    },
    animation: {
      duration: message.frameTimeout,
      easing: 'linear',
      delay: 0,
      loop: false,
      onComplete: function(animation){
        animation.chart.data.datasets[0].pointBackgroundColor = 'rgba(0, 255, 0, 0.8)';
      }
    },
    plugins: {
      legend: {
        display: false
      }
    }
  };

  const mapConfig = {
    type: 'scatter',
    data: { 
      datasets: [{
        data: null,
        borderColor: 'rgba(255, 99, 132, 0.8)',
        backgroundColor: 'rgba(255, 99, 132, 0.8)',
      }]
    },
    options: mapOptions
  };
  //options: {}

  window.chart = new Chart(ctx, mapConfig);
};

// Handle map messages
export function plotMap(eventData){
  if (eventData != null){
    if (eventData.size < 2){
      console.log("m: error? ", eventData)
    }
    let frameIndex = eventData.get("block");
    let vehicles = eventData.get("vehicles");
    let vehicleLocations = [];
    let vehicleColors = [];
    vehicles.forEach((vehicle, index) => {
      vehicleColors.push(colors.get(vehicle[0]));
      vehicleLocations.push({x: vehicle[1][0], y: vehicle[1][1]});
    });
    let time = Math.round((Date.now() - startTime)/100) * 100;
    // console.log("m (", time, "): Regular-updated chart: locations[0] = ", locations[0]);
    // chart.data.datasets[0].pointBackgroundColor = colors;
    chart.data.datasets[0].pointBackgroundColor = 'rgba(255, 0, 0, 0.8)';;
    chart.data.datasets[0].data = vehicleLocations;
    chart.options.animation.duration = message.frameTimeout;
    chart.update();
    let needsRefresh = false;
    let updatedLocations = [];
    vehicleLocations.forEach((vehicle, index) => {
      let newX = vehicle.x;
      let newY = vehicle.y;
      if(vehicle.x > (message.citySize - 0.6)){
        // going off the right side
        newX = -0.5;
        needsRefresh = true;
      };
      if(vehicle.x < -0.1){
        // going off the left side
        newX = message.citySize - 0.5;
        needsRefresh = true;
      };
      if(vehicle.y > (message.citySize - 0.9)){
        // going off the top
        newY = -0.5;
        needsRefresh = true;
      };
      if(vehicle.y < -0.1){
        // going off the bottom
        newY = message.citySize - 0.5;
        needsRefresh = true;
      };
      updatedLocations.push({x: newX, y: newY})
    });
    // if (x > 1.9){
    if (needsRefresh == true){
      // Reappear on the opposite  side of the chart
      time = Math.round((Date.now() - startTime)/100) * 100;
      // console.log("m (", time, "): Edge-updated chart: locations[0] = ", updatedLocations[0]);
      chart.data.datasets[0].data = updatedLocations;
      chart.data.datasets[0].pointBackgroundColor = 'rgba(0, 0, 255, 0.8)';
      chart.options.animation.duration = message.frameTimeout;
      chart.update();
    }
  };
};
