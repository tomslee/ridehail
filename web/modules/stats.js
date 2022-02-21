import {ctx} from "../main.js";
const maxFrames = 10;
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
        tension: 0.3,
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
        display: true
      },
      colorschemes: {
        scheme: 'brewer.Paired12',
      },
      title: {
        display: true,
        text: 'Ridehail statistics',
      },
    }
  };

  const statsConfig = {
    type: 'line',
    data: { 
      datasets: [{
        label: 'P1',
        data: null,
        backgroundColor: 'rgba(232, 32, 32, 0.8)',
        borderColor: 'rgba(232, 32, 32, 0.8)',
        borderWidth: 3,
      },
        {label: 'P2',
        data: null,
        backgroundColor: 'rgba(32, 32, 232, 0.8)',
        borderColor: 'rgba(32, 32, 232, 0.8)',
        borderWidth: 3,
      },
        {label: 'P3',
        data: null,
        backgroundColor: 'rgba(32, 232, 32, 0.8)',
        borderColor: 'rgba(32, 232, 32, 0.8)',
        borderWidth: 3,
      },
        {label: 'Wait fraction',
        data: null,
        backgroundColor: 'rgba(232, 132, 132, 0.8)',
        borderColor: 'rgba(232, 132, 132, 0.8)',
        borderWidth: 3,
        borderDash: [10, 10],
      },
      ]
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
    console.log("stats: eventData=", eventData);
    let time = Math.round((Date.now() - startTime)/100) * 100;
    // mapChart.data.datasets[0].pointBackgroundColor = colors;
    chart.data.datasets.forEach((dataset, index) => {
      dataset.data.push({x: eventData[0], y: eventData[1][index]});
    })
    chart.options.scales.xAxis.max = eventData[0];
    chart.options.plugins.title.text = `Ridehail statistics: Frame ${eventData[0]}`;
    chart.update('none');
  };
};
