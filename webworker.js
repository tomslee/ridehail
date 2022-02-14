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
  worker_pkg = pyodide.pyimport("worker");
}
let pyodideReadyPromise = loadPyodideAndPackages();

function pythonTask() {
  try {
    x = x + 1;
    // let data = worker_pkg.do_something(x, y);
    let config = worker_pkg.setup().toJs();
    // let config_name = config.get("name");
    let jsconfig = config.toJs();
    let what = JSON.parse(JSON.stringify(config))
    //data = data.toJS();
    console.log("In pythonTask, config = ", config);
    // console.log("In pythonTask, name = ", config_name);
    console.log("In pythonTask, jsconfig = ", jsconfig);
    console.log("In pythonTask, what = ", what);
    let type = config.type
    console.log("In pythonTask, type = ", type);
    // console.log("In pythonTask, globals = ", self.pyodide.globals.data);
    self.postMessage(data);
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
    worker_pkg = pyodide.pyimport("worker");
    // let data = worker_pkg.do_something(2, 6);
    // console.log("In onmessage, data = ", data);
    // self.postMessage({ data });
    pythonTask();
  } catch (error) {
    self.postMessage({ error: error.message});
  }
};

