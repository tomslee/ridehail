// JavaScript webworker.js
// from https://pyodide.org/en/stable/usage/webworker.html

// Setup your project to serve `webworker.js`. You should also serve
// `pyodide.js`, and all its associated `.asm.js`, `.data`, `.json`,
// and `.wasm` files as well:
importScripts("./pyodide/pyodide.js");
var worker_pkg;
var x = 0;
var y = 0;

async function loadPyodideAndPackages() {
  self.pyodide = await loadPyodide({
    // indexURL: "https://cdn.jsdelivr.net/pyodide/v0.19.0/full/",
    indexURL: "./pyodide/",
  });
  await self.pyodide.loadPackage(["numpy"]);
  await pyodide.runPythonAsync(`
      from pyodide.http import pyfetch
      response = await pyfetch("./worker.py")
      with open("worker.py", "wb") as f:
         f.write(await response.bytes())
   `);
  worker_pkg = pyodide.pyimport("worker");
}
let pyodideReadyPromise = loadPyodideAndPackages();

function pythonTask() {
  try {
    x = x + 0.1;
    y = y - 0.05;
    // let data = worker_pkg.do_something(x, y);
    let data = worker_pkg.return_sin(x).toJs();
    //data = data.toJS();
    console.log("In pythonTask, data[0] = ", data[0]);
    console.log("In pythonTask, data[1] = ", data[1]);
    // console.log("In pythonTask, globals = ", self.pyodide.globals.data);
    self.postMessage(data);
    setTimeout("pythonTask()", 100);
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
    worker_pkg = pyodide.pyimport("worker");
    // let data = worker_pkg.do_something(2, 6);
    // console.log("In onmessage, data = ", data);
    // self.postMessage({ data });
    pythonTask();
  } catch (error) {
    self.postMessage({ error: error.message});
  }
};

