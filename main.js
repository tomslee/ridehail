var citySize = 4;
const canvas = document.getElementById('chartcanvas');
const ctx = canvas.getContext('2d');
const maxVehicleCount = 30;
const maxFrames = 20;
var labels = [];
const offset = 0.0;
const startTime = Date.now();
var locations;

function setData(offset, x, y){
  let data = [];
  for (var i = 0; i < x.length; i++) {
    data.push({x: x[i], y: y[i]});
  };
  return data;
}

const lineOptions = {
  scales: {
    xAxis: {
      min: 0,
      max: maxFrames,
      grid: {
        linewidth: 10,
        borderWidth: 10,
      },
      type: 'linear',
      title: {
        text: "Vehicle count",
        display: true,
        font: {
          weight: 'bold'
        },
      },
    },
    yAxis: {
      min: 0.0,
      max: 10.0,
      grid: {
        linewidth: 10,
        borderWidth: 10,
      },
      type: 'linear',
      title: {
        text: 'P3 fraction (idle time)',
        display: true,
        font: {
          weight: 'bold'
        },
      },
    }
  },
  elements: {
    line: {
      backgroundColor: 'rgba(255, 99, 132, 0.8)',
      borderWidth: 5,
      tension: 0.4,
    },
    point: {
      radius: 0
    }
  },
  animation: {
    duration: 800
  },
  plugins: {
    legend: {
      display: false
    }
  }
};

const lineConfig = {
  type: 'line',
  data: { 
    datasets: [{
      label: 'sin(x)',
      data: null,
      borderColor: 'rgba(255, 99, 132, 0.8)',
      backgroundColor: 'rgba(255, 99, 132, 0.8)',
    }]
  },
  options: lineOptions
};
  //options: {}

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
    onComplete: function(chart){
      //chart.data.datasets[0].pointBackgroundColor = 'rgba(0, 255, 0, 0.8)';
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
const mapChart = new Chart(ctx, mapConfig);
const div = document.getElementById('div1');

if (typeof(w) == "undefined") {
  var w = new Worker("webworker.js");
}

window.startAnimation=()=>{
  w.postMessage("Start!");
};

// Listen to the web worker
w.onmessage = function(event){
  // console.log("In main.js, event.data=" + event.data);
  // lineChart.data.datasets[0].data.push({x: event.data[0], y: event.data[1].get("vehicle_fraction_idle")});
  // data comes in from a self.postMessage([blockIndex, vehicleColors, vehicleLocations]);
  if (event.data != null){
    if (event.data.length < 2){
      console.log("m: error? ", event.data)
    }
    let colors = event.data[1];
    locations = event.data[2];
    let time = Math.round((Date.now() - startTime)/100) * 100;
    console.log("m (", time, "): Regular-updated chart: locations[0] = ", locations[0]);
    // mapChart.data.datasets[0].pointBackgroundColor = colors;
    mapChart.data.datasets[0].pointBackgroundColor = 'rgba(255, 0, 0, 0.8)';;
    mapChart.data.datasets[0].data = locations;
    mapChart.options.animation.duration = 800;
    mapChart.update();
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
      console.log("m (", time, "): Edge-updated chart: locations[0] = ", updatedLocations[0]);
      mapChart.data.datasets[0].data = updatedLocations;
      mapChart.data.datasets[0].pointBackgroundColor = 'rgba(0, 0, 255, 0.8)';
      mapChart.options.animation.duration = 50;
      mapChart.update();
    }
  };
};
