const maxFrames = 10;
const citySize = 4;
const canvas = document.getElementById('chartcanvas');
const ctx = canvas.getContext('2d');
const startTime = Date.now();

export function initStatsChart(){
  const statsOptions = {
    scales: {
      xAxis: {
        min: 0,
        max: maxFrames,
        grid: {
          linewidth: 1,
          borderWidth: 1,
        },
        type: 'linear',
        title: {
          text: "Time (blocks)",
          display: true,
          font: {
            weight: 'normal'
          },
        },
      },
      yAxis: {
        min: 0.0,
        max: 1.0,
        grid: {
          linewidth: 1,
          borderWidth: 1,
        },
        type: 'linear',
        title: {
          text: 'Wait fraction',
          display: true,
          font: {
            weight: 'normal'
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

  const statsConfig = {
    type: 'line',
    data: { 
      datasets: [{
        label: 'wait fraction',
        data: null,
        borderColor: 'rgba(255, 99, 132, 0.8)',
        backgroundColor: 'rgba(255, 99, 132, 0.8)',
      }]
    },
    options: statsOptions
  };
  //options: {}

  if (window.chart instanceof Chart) {
      window.chart.destroy();
  };
  window.chart = new Chart(ctx, statsConfig);
};

// Handle stats messages
export function plotStats(eventData){
  if (eventData != null){
    let time = Math.round((Date.now() - startTime)/100) * 100;
    // mapChart.data.datasets[0].pointBackgroundColor = colors;
    chart.data.datasets.forEach((dataset) => {
      dataset.data.push({x: eventData[0], y: eventData[1][0]});
    })
    chart.options.scales.xAxis.max = eventData[0];
    chart.update();
  };
};
