/*
 * JavaScript webworker.js
 * from https://pyodide.org/en/stable/usage/webworker.html
 *
 * Setup your project to serve `webworker.js`. You should also serve
 * `pyodide.js`, and all its associated `.asm.js`, `.data`, `.json`,
 * and `.wasm` files as well:
 */

// Set one of these to load locally or from the CDN
const indexURL = "./pyodide/";
// const indexURL = "https://cdn.jsdelivr.net/pyodide/v0.19.0/full/";
importScripts(`${indexURL}pyodide.js`);
var citySize = 16;
var vehicleCount = 32;
var baseDemand = 2;
var frameIndex = 0;
var mapFrameCount = 20;
var messageFromWorker = {
  frameIndex: 0,
  results: {},
};

// duplicate from main.js to get around module problems for now
const ChartType = {
  map: "map",
  stats: "stats"
};

async function loadPyodideAndPackages() {
  self.pyodide = await loadPyodide({
    indexURL: indexURL,
  });
  await self.pyodide.loadPackage(["numpy", "micropip"]);
  await pyodide.runPythonAsync(`
      import micropip
      micropip.install('../dist/ridehail-0.0.1-py3-none-any.whl')
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

function runStatsSimulationStep(messageFromUI) {
  try {
    messageFromWorker = messageFromUI;
    let results = workerPackage.sim.next_frame(messageFromUI);
    results = results.toJs();
    self.postMessage(results);
    if ((results.get("block") < messageFromUI.timeBlocks &&
      messageFromUI.action == "play_arrow") ||
    (results.get("block") == 0 &&
      messageFromUI.action == "single-step")){
      // special case: do one step on first single-step action to avoid
      // resetting each time
      setTimeout(runStatsSimulationStep, messageFromUI.frameTimeout, messageFromUI);
    };
  } catch (error) {
    console.log("Error in runStatsSimulationStep: ", error.message);
    self.postMessage({error: error.message});
  }
}

function runMapSimulationStep(messageFromUI) {
  try {
    let results = workerPackage.sim.next_frame(messageFromUI);
    results = results.toJs();
    console.log("wo: results=", results);
    self.postMessage(results);
    if ((results.get("block") < (2 * messageFromUI.timeBlocks) &&
      messageFromUI.action == "play_arrow") ||
    (results.get("block") == 0 &&
      messageFromUI.action == "single-step")){
      // special case: do one step on first single-step action to avoid
      // resetting each time
      setTimeout(runMapSimulationStep, messageFromUI.frameTimeout, messageFromUI);
    };
  } catch (error) {
    console.log("Error in runSimulationStep: ", error.message);
    self.postMessage({error: error.message});
  }
}

function resetSimulation(messageFromUI){
  // clear all the timeouts
  let id = setTimeout(function() {}, 0);
  while (id--) {
    clearTimeout(id); // will do nothing if no timeout with id is present
  }
  if (messageFromUI.chartType == "Stats"){
    workerPackage.init_stats_simulation(messageFromUI);
  } else if (messageFromUI.chartType == "Map"){
    workerPackage.init_map_simulation(messageFromUI);
  } else {
    console.log(`unknown chart type:  ${messageFromUI.chartType}`);
  }
};

async function handlePyodideReady(){
  await pyodideReadyPromise;
  let message = new Map();
  message.set("text", "Pyodide loaded");
  self.postMessage(message);
};
handlePyodideReady();


// await pyodideReadyPromise;
  // self.onmessage = async (event) => {
self.onmessage = async (event) => {
  // make sure loading is done
  try {
    await pyodideReadyPromise;
    console.log("ww onmessage: ", event.data);
    messageFromUI = event.data
    frameIndex = 0;
    if (messageFromUI.action == "play_arrow" || messageFromUI.action == "single-step") {
      if (messageFromUI.chartType == "Map"){
        workerPackage.init_map_simulation(messageFromUI);
        runMapSimulationStep(messageFromUI);
      } else if (messageFromUI.chartType == "Stats"){
        if (messageFromUI.frameIndex == 0){
          // initialize only if it is a new simulation (frameIndex 0)
          workerPackage.init_stats_simulation(messageFromUI);
        }
        runStatsSimulationStep(messageFromUI);
      } else {
        console.log("unknown chart type ", event.data);
      }
    } else if (messageFromUI.action == "pause" ){
      // We don't know the actual timeout, but they are incrementing integers.
      // Set a new one to get the max value and then clear them all, 
      // as in https://stackoverflow.com/questions/8860188/javascript-clear-all-timeouts
      let id = setTimeout(function() {}, 0);
      while (id--) {
        clearTimeout(id); // will do nothing if no timeout with id is present
      }
      console.log("Cleared timeout");
    } else if (messageFromUI.action == "reset") {
      resetSimulation(messageFromUI);
    };
  } catch (error) {
    self.postMessage({ error: error.message});
  }
};

