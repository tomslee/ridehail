const canvas = document.getElementById('chartcanvas');
const ctx = canvas.getContext('2d');
const maxVehicleCount = 30;
const maxFrames = 100;
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
    duration: 0
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
      max: 7.5,
      grid: {
        borderWidth: 1,
        linewidth: 20,
      },
      type: 'linear',
      ticks: {
      display: false,
      },
    },
    yAxis: {
      min: 0,
      max: 8,
      grid: {
        borderWidth: 1,
        linewidth: 1,
      },
      type: 'linear',
      ticks: {
      display: false,
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
    duration: 500,
    easing: 'linear',
  },
  animation: {
    duration: 500,
    easing: 'linear',
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

w.postMessage("Start!");

// Listen to the web worker
w.onmessage = function(event){
  // console.log("In main.js, event.data=" + event.data)
  // lineChart.data.datasets[0].data.push({x: event.data[0], y: event.data[1].get("vehicle_fraction_idle")});
  // data comes in from a self.postMessage([blockIndex, vehiclePhases, vehicleLocations]);
  if (event.data != null){
    mapChart.data.datasets[0].pointBackgroundColor = event.data[1];
    mapChart.data.datasets[0].data = event.data[2];
    console.log("in main.js, vehicleLocations = ", mapChart.data.datasets[0].data)
    console.log("in main.js, colors = ", mapChart.data.datasets[0].pointBackgroundColor)
    mapChart.update('linear');
  };
  if (event.data[0] >= maxFrames){
    console.log("Terminating worker thread...");
    w.terminate();
  };
};
