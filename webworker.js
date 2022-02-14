// JavaScript webworker.js
// from https://pyodide.org/en/stable/usage/webworker.html

// Setup your project to serve `webworker.js`. You should also serve
// `pyodide.js`, and all its associated `.asm.js`, `.data`, `.json`,
// and `.wasm` files as well:
importScripts("./pyodide/pyodide.js");
var workerPackage;
var vehicleCount = 0;

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

function pythonTask() {
  try {
    vehicleCount = vehicleCount + 1;
    let results = workerPackage.simulate(vehicleCount).toJs();
    // let what = JSON.parse(JSON.stringify(results))
    //data = data.toJS();
    console.log("In pythonTask, vfi = ", results.get("vehicle_fraction_idle"));
    self.postMessage([vehicleCount, results]);
    setTimeout("pythonTask()", 1000);
  } catch (error) {
    self.postMessage({ error: error.message });
  }
};

self.onmessage = async (event) => {
  // make sure loading is done
  await pyodideReadyPromise;
  // Don't bother yet with this line, suppose our API is built in such a way:
  // const { id, python, ...context } = event.data;
  // The worker copies the context in its own "memory" (an object mapping name to values)
  // for (const key of Object.keys(context)) {
    // self[key] = context[key];
  // }
  // Now is the easy part, the one that is similar to working in the main thread:
  try {
    await pyodideReadyPromise;
    // pythonTask();
    workerPackage = pyodide.pyimport("worker");
    // console.log("In onmessage, data = ", data);
    // self.postMessage({ data });
    pythonTask();
  } catch (error) {
    self.postMessage({ error: error.message});
  }
};

