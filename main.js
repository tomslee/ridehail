const canvas = document.getElementById('chartcanvas');
const ctx = canvas.getContext('2d');
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
      max: 7.0,
      grid: {
        linewidth: 10,
      },
      type: 'linear'
    },
    yAxis: {
      min: -1.0,
      max: +1.0,
      grid: {
        linewidth: 10,
      },
      type: 'linear'
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
  console.log("In main.js, received " + event.data[0] + ", " + event.data[1] + ", " + event.data[2]) 
  //myChart.data.datasets[0].data = setData(event.data[2]);
  // myChart.data.datasets[0].data = setData(event.data[0], event.data[1], event.data[2]);
  myChart.data.datasets[0].data.push({x: event.data[0], y: event.data[1]});
  myChart.update('none');
  if (event.data[0] > 2 * Math.PI){
    console.log("Terminating worker thread...");
    w.terminate();
  };
};
