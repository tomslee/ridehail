// JavaScript webworker.js
// from https://pyodide.org/en/stable/usage/webworker.html

// Setup your project to serve `webworker.js`. You should also serve
// `pyodide.js`, and all its associated `.asm.js`, `.data`, `.json`,
// and `.wasm` files as well:
importScripts("./pyodide/pyodide.js");
var workerPackage;
var vehicleCount = 0;
var blockIndex = 0;

async function loadPyodideAndPackages() {
  self.pyodide = await loadPyodide({
    // indexURL: "https://cdn.jsdelivr.net/pyodide/v0.19.0/full/",
    indexURL: "./pyodide/",
  });
  await self.pyodide.loadPackage(["numpy", "micropip"]);
  // await pyodide.runPythonAsync(`
      // from pyodide.http import pyfetch
      // response = await pyfetch("./dist/ridehail.tar.gz")
      // await response.unpack_archive()
   // `);
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


function runSimulationStep() {
  try {
    let blockResults = workerPackage.next_block(blockIndex).toJs();
    console.log("runSimulationStep # ", blockIndex, "blockResults=", blockResults);
    self.postMessage([blockIndex, blockResults]);
    blockIndex = blockIndex + 1;
    setTimeout(function(){runSimulationStep()}, 10);
  } catch (error) {
    self.postMessage({ error: error.message });
  }
}

self.onmessage = async (event) => {
  // make sure loading is done
  try {
    await pyodideReadyPromise;
    vehicleCount = 8;
    workerPackage.setup_simulation(vehicleCount);
    // runSimulation();
    runSimulationStep()
  } catch (error) {
    self.postMessage({ error: error.message});
  }
};

