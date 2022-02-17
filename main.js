var citySize = 4;
const canvas = document.getElementById('chartcanvas');
const ctx = canvas.getContext('2d');
const maxVehicleCount = 30;
const maxFrames = 20;
var labels = [];
const offset = 0.0;

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
    duration: 500
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
    duration: 100,
    easing: 'linear',
    delay: 0,
    loop: false
  },
  animation: {
    duration: 500,
    easing: 'linear',
    delay: 0,
    loop: false
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
    let colors = event.data[1];
    let locations = event.data[2];
    mapChart.data.datasets[0].pointBackgroundColor = colors;
    mapChart.data.datasets[0].data = locations;
    mapChart.options.animation.duration = 500;
    console.log("updating chart: locations[0] = ", locations[0]);
    mapChart.update();
    let updatedLocations = [];
    let needsRefresh = false;
    locations.forEach((vehicle, index) => {
      let newX = vehicle.x;
      let newY = vehicle.y;
      if(vehicle.x > (citySize - 0.9)){
        // going off the right side
        newX = -0.5;
        needsRefresh = true;
      };
      if(vehicle.x < -0.1){
        // going off the right side
        newX = citySize - 0.5;
        needsRefresh = true;
      };
      if(vehicle.y > (citySize - 0.9)){
        // going off the right side
        newY = -0.5;
        needsRefresh = true;
      };
      if(vehicle.y < -0.1){
        // going off the right side
        newY = citySize - 0.5;
        needsRefresh = true;
      };
      updatedLocations.push({x: newX, y: newY})
    });
    if(needsRefresh){
      console.log("Edge-updating chart: locations[0] = ", updatedLocations[0]);
      // mapChart.options.animation.duration = 0;
      // mapChart.options.animations.duration = 0;
      // mapChart.options.elements.point.display = false;
      mapChart.data.datasets[0].data = updatedLocations;
      mapChart.data.datasets[0].pointBackgroundColor = 'rgba(255, 255, 255, 0.0)';
      mapChart.update('none');
      console.log("Edge-updated chart: locations[0] = ", updatedLocations[0]);
    };
  };
  // if (event.data[0] >= maxFrames){
    // console.log("Terminating worker thread...");
    // w.terminate();
  // };
};
