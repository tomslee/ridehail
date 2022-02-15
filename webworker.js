// JavaScript webworker.js
// from https://pyodide.org/en/stable/usage/webworker.html

// Setup your project to serve `webworker.js`. You should also serve
// `pyodide.js`, and all its associated `.asm.js`, `.data`, `.json`,
// and `.wasm` files as well:
importScripts("./pyodide/pyodide.js");
var citySize = 4;
var vehicleCount = 1;
var blockIndex = 0;
const colors = new Map();
const timeOut = 1000;
var frameCount = 20;
colors.set("WITH_RIDER", "rgba(60, 179, 113, 0.4)");
colors.set("DISPATCHED", "rgba(255, 165, 0, 0.4)");
colors.set("IDLE", "rgba(0, 0, 255, 0.4)");

async function loadPyodideAndPackages() {
  self.pyodide = await loadPyodide({
    // indexURL: "https://cdn.jsdelivr.net/pyodide/v0.19.0/full/",
    indexURL: "./pyodide/",
  });
  await self.pyodide.loadPackage(["numpy", "micropip"]);
  await pyodide.runPythonAsync(`
      import micropip
      micropip.install('./dist/ridehail-0.0.1-py3-none-any.whl')
  `);
  await pyodide.runPythonAsync(`
      from pyodide.http import pyfetch
      response = await pyfetch("./worker.py")
      with open("worker.py", "wb") as f:
         f.write(await response.bytes())
   `);
  workerPackage = pyodide.pyimport("worker");
}
let pyodideReadyPromise = loadPyodideAndPackages();

function runSimulation() {
  try {
    vehicleCount = vehicleCount + 1;
    let results = workerPackage.simulate(vehicleCount).toJs();
    self.postMessage([vehicleCount, results]);
    setTimeout("runSimulation()", 100);
  } catch (error) {
    self.postMessage({ error: error.message });
  }
};


function runSimulationStep(previousLocations) {
  try {
    let blockResults = workerPackage.next_block(blockIndex).toJs();
    let vehicleLocations = [];
    if (previousLocations != null){
      blockResults.forEach((vehicle, index) => {
        let x = vehicle[1][0];
        let y = vehicle[1][1];
        let oldX = previousLocations[index]["x"];
        let oldY = previousLocations[index]["y"];
        let newX = (0.5 * (x + oldX));
        let newY = (0.5 * (y + oldY));
        // console.log("x=", x, ", oldX=", oldX, ", citySize=", citySize);
        // console.log("y=", y, ", oldY=", oldY, ", citySize=", citySize);
        if(x==0 && oldX==citySize - 1){
          // console.log("updating x", x, ", ", oldX);
          newX = oldX + 0.5;
        } else if (x==citySize - 1 && oldX==0){
          // console.log("updating x", x, ", ", oldX);
          newX = oldX - 0.5;
        };
        if(y==0 && oldY==citySize - 1){
          // console.log("updating y", y, ", ", oldY);
          newY = oldY + 0.5;
        } else if (y==citySize  - 1&& oldY==0){
          // console.log("updating y", y, ", ", oldY);
          newY = oldY - 0.5;
        };
        vehicleLocations.push({x: newX, y: newY});
      });
      self.postMessage([blockIndex, vehicleColors, vehicleLocations]);
      setTimeout(function(){
      //sleep
      }, 1000);
    };
    vehicleLocations = [];
    vehicleColors = [];
    blockResults.forEach((vehicle, index) => {
      vehicleColors.push(colors.get(vehicle[0]));
      vehicleLocations.push({x: vehicle[1][0], y: vehicle[1][1]});
    });
    self.postMessage([blockIndex, vehicleColors, vehicleLocations]);
    blockIndex = blockIndex + 1;
    if (blockIndex < frameCount){
      setTimeout(function(){runSimulationStep(vehicleLocations)}, 1000);
    };
    //    blockResults.destroy();
  } catch (error) {
    console.log("Error in runSimulationStep: ", error.message);
    self.postMessage({ error: error.message });
  }
}

self.onmessage = async (event) => {
  // make sure loading is done
  try {
    await pyodideReadyPromise;
    workerPackage.setup_simulation(citySize, vehicleCount);
    // runSimulation();
    blockIndex = 0;
    runSimulationStep(null);
  } catch (error) {
    self.postMessage({ error: error.message});
  }
};

