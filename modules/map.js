const citySize = 4;
const canvas = document.getElementById('chartcanvas');
const ctx = canvas.getContext('2d');
const startTime = Date.now();

export function initMapChart() { 
  const mapOptions = {
    scales: {
      xAxis: {
        min: -0.5,
        max: citySize - 0.5,
        grid: {
          borderWidth: 1,
          linewidth: 20,
        },
        type: 'linear',
        ticks: {
          display: true,
        },
      },
      yAxis: {
        min: -0.5,
        max: citySize - 0.5,
        grid: {
          borderWidth: 1,
          linewidth: 1,
        },
        type: 'linear',
        ticks: {
          display: true,
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
        radius: 10
      }
    },
    transitions: {
      duration: 800,
      easing: 'linear',
      delay: 0,
      loop: false
    },
    animation: {
      duration: 800,
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

// const lineChart = new Chart(ctx, lineConfig);
  if (window.chart instanceof Chart) {
      window.chart.destroy();
  };
  window.chart = new Chart(ctx, mapConfig);
};

// Handle map messages
export function plotMap(eventData){
  if (eventData != null){
    if (eventData.length < 2){
      console.log("m: error? ", eventData)
    }
    let colors = eventData[1];
    let locations = eventData[2];
    let time = Math.round((Date.now() - startTime)/100) * 100;
    // console.log("m (", time, "): Regular-updated chart: locations[0] = ", locations[0]);
    // chart.data.datasets[0].pointBackgroundColor = colors;
    chart.data.datasets[0].pointBackgroundColor = 'rgba(255, 0, 0, 0.8)';;
    chart.data.datasets[0].data = locations;
    chart.options.animation.duration = 800;
    chart.update();
    let needsRefresh = false;
    let updatedLocations = [];
    locations.forEach((vehicle, index) => {
      let newX = vehicle.x;
      let newY = vehicle.y;
      if(vehicle.x > (citySize - 0.6)){
        // going off the right side
        newX = -0.5;
        needsRefresh = true;
      };
      if(vehicle.x < -0.1){
        // going off the left side
        newX = citySize - 0.5;
        needsRefresh = true;
      };
      if(vehicle.y > (citySize - 0.9)){
        // going off the top
        newY = -0.5;
        needsRefresh = true;
      };
      if(vehicle.y < -0.1){
        // going off the bottom
        newY = citySize - 0.5;
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
      chart.options.animation.duration = 50;
      chart.update();
    }
  };
};
