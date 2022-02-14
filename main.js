const canvas = document.getElementById('chartcanvas');
const ctx = canvas.getContext('2d');
const maxVehicleCount = 50;
var labels = [];
const offset = 0.0;

function setData(offset, x, y){
  let data = [];
  for (var i = 0; i < x.length; i++) {
    data.push({x: x[i], y: y[i]});
  };
  return data;
}

const options = {
  scales: {
    xAxis: {
      min: 0,
      max: maxVehicleCount,
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
      max: 1.0,
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
      // backgroundColor: 'rgba(255, 99, 132, 0.8)',
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

const config = {
  type: 'line',
  data: { 
    datasets: [{
      label: 'sin(x)',
      data: null,
      borderColor: 'rgba(255, 99, 132, 0.8)',
      backgroundColor: 'rgba(255, 99, 132, 0.8)',
    }]
  },
  options: options
};
  //options: {}

const myChart = new Chart(ctx, config);
const div = document.getElementById('div1');

if (typeof(w) == "undefined") {
  var w = new Worker("webworker.js");
}

w.postMessage("Start!");

// Listen to the web worker
w.onmessage = function(event){
  console.log("In main.js, received " + event.data)
  myChart.data.datasets[0].data.push({x: event.data[0],
    y: event.data[1].get("vehicle_fraction_idle")});
  myChart.update('none');
  if (event.data[0] > maxVehicleCount){
    console.log("Terminating worker thread...");
    w.terminate();
  };
};
