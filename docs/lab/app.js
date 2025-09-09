/* global Chart */

/*
 * Imports and exports from and to modules
 */

import {
  initCityChart,
  initPhasesChart,
  initTripChart,
  initIncomeChart,
} from "./modules/stats.js";
import { initMap } from "./modules/map.js";
import {
  initWhatIfPhasesChart,
  initWhatIfIncomeChart,
  initWhatIfWaitChart,
  initWhatIfNChart,
  initWhatIfDemandChart,
  initWhatIfPlatformChart,
  initWhatIfTables,
} from "./modules/whatif.js";

import { DOM_ELEMENTS } from "./js/dom-elements.js";
import {
  colors,
  SimulationActions,
  SCALE_CONFIGS,
  LAB_SETTINGS_CONFIG,
  CHART_TYPES,
} from "./js/config.js";
import {
  SimSettings,
  WhatIfSimSettingsDefault,
  createSettingsFromConfig,
} from "./js/sim-settings.js";
import { setupInputHandlers } from "./js/input-handlers.js";
import { MessageHandler } from "./js/message-handler.js";

// Tabs
DOM_ELEMENTS.collections.tabList.forEach(function (element) {
  // destroy any existing charts
  element.onclick = function (element) {
    if (window.chart instanceof Chart) {
      window.chart.destroy();
    }
    if (window.statsChart instanceof Chart) {
      window.statsChart.destroy();
    }
    switch (element.currentTarget.id) {
      case "tab-experiment":
        resetLabUIAndSimulation();
        break;
      case "tab-what-if":
        resetWhatIfUIAndSimulation();
        break;
      case "tab-read":
        break;
      case "tab-TO":
        break;
    }
  };
});

// File drop
// See https://developer.mozilla.org/en-US/docs/Web/API/HTML_Drag_and_Drop_API/File_drag_and_drop
/*
const dropZone = document.getElementById("drop-zone");
dropZone.ondrop = function (event) {
  event.dataTransfer.dropEffect = "move";
  // const data = event.dataTransfer.getData("text/plain");
  // console.log("Drop incoming: ", data);
  // event.target.textContent = data;
  event.preventDefault();
  // Prevent default behavior (Prevent file from being opened)

  if (event.dataTransfer.items) {
    var file;
    // Use DataTransferItemList interface to access the file(s)
    for (var i = 0; i < event.dataTransfer.items.length; i++) {
      // If dropped items aren't files, reject them
      if (event.dataTransfer.items[i].kind === "file") {
        file = event.dataTransfer.items[i].getAsFile();
        console.log("... file[" + i + "].name = " + file.name);
        console.log("... file[" + i + "].text = " + file.text);
        // only process the first file
        break;
      }
    }
    // read the file content asynchronously
    var fr = new FileReader();
    fr.onload = function (event) {
      let fileContent = event.target.result;
      let jsonDoc = JSON.parse(fileContent);
      labSimSettings = jsonDoc;
      labSimSettings.name = "labSimSettings";
      resetLabUIAndSimulation();
      console.log("labSimSettings=", labSimSettings);
    };
    fr.readAsText(file);
  } else {
    // Use DataTransfer interface to access the file(s)
    for (var j = 0; j < event.dataTransfer.files.length; j++) {
      console.log(
        "... file[" + j + "].name = " + event.dataTransfer.files[j].name
      );
    }
  }
};
dropZone.ondragover = function (event) {
  // Get the id of the target and add the moved element to the target's DOM
  // const data = ev.dataTransfer.getData("text/plain");
  // ev.target.appendChild(document.getElementById(data));
  event.preventDefault();
};
*/

/*
 * What if? tab
 */
var baselineData = null;

DOM_ELEMENTS.whatIf.setComparisonButtons.forEach(function (element) {
  element.addEventListener("click", function () {
    switch (this.id) {
      case "what-if-price-remove":
        if (whatIfSimSettingsComparison.useCityScale) {
          whatIfSimSettingsComparison.perMinutePrice -= 0.1;
          // the price is ignored, but set it right for appearance's sake
          whatIfSimSettingsComparison.price =
            whatIfSimSettingsComparison.perMinutePrice +
            (whatIfSimSettingsComparison.perKmPrice *
              whatIfSimSettingsComparison.meanVehicleSpeed) /
              60.0;
        } else {
          whatIfSimSettingsComparison.price -= 0.1;
        }
        whatIfSimSettingsComparison.price =
          Math.round(whatIfSimSettingsComparison.price * 10) / 10;
        break;
      case "what-if-price-add":
        if (whatIfSimSettingsComparison.useCityScale) {
          whatIfSimSettingsComparison.perMinutePrice += 0.1;
          // the price is ignored, but set it right for appearance's sake
          whatIfSimSettingsComparison.price =
            whatIfSimSettingsComparison.perMinutePrice +
            (whatIfSimSettingsComparison.perKmPrice *
              whatIfSimSettingsComparison.meanVehicleSpeed) /
              60.0;
        } else {
          whatIfSimSettingsComparison.price += 0.1;
        }
        whatIfSimSettingsComparison.price =
          Math.round(whatIfSimSettingsComparison.price * 10) / 10;
        break;
      case "what-if-commission-remove":
        whatIfSimSettingsComparison.platformCommission -= 0.05;
        whatIfSimSettingsComparison.platformCommission =
          Math.round(whatIfSimSettingsComparison.platformCommission * 20) / 20;
        break;
      case "what-if-commission-add":
        whatIfSimSettingsComparison.platformCommission += 0.05;
        whatIfSimSettingsComparison.platformCommission =
          Math.round(whatIfSimSettingsComparison.platformCommission * 20) / 20;
        break;
      case "what-if-reservation-wage-remove":
        if (whatIfSimSettingsComparison.useCityScale) {
          whatIfSimSettingsComparison.perHourOpportunityCost -= 60.0 * 0.01;
          whatIfSimSettingsComparison.reservationWage =
            (whatIfSimSettingsComparison.perHourOpportunityCost +
              whatIfSimSettingsComparison.perKmOpsCost *
                whatIfSimSettingsComparison.meanVehicleSpeed) /
            60.0;
        } else {
          whatIfSimSettingsComparison.reservationWage -= 0.01;
        }
        whatIfSimSettingsComparison.reservationWage =
          Math.round(whatIfSimSettingsComparison.reservationWage * 100) / 100;
        break;
      case "what-if-reservation-wage-add":
        if (whatIfSimSettingsComparison.useCityScale) {
          whatIfSimSettingsComparison.perHourOpportunityCost += 60.0 * 0.01;
          whatIfSimSettingsComparison.reservationWage =
            whatIfSimSettingsComparison.perHourOpportunityCost / 60.0 +
            (whatIfSimSettingsComparison.perKmOpsCost *
              whatIfSimSettingsComparison.meanVehicleSpeed) /
              60.0;
        } else {
          whatIfSimSettingsComparison.reservationWage =
            whatIfSimSettingsComparison.reservationWage + 0.01;
        }
        whatIfSimSettingsComparison.reservationWage =
          Math.round(whatIfSimSettingsComparison.reservationWage * 100) / 100;
        break;
      case "what-if-demand-remove":
        whatIfSimSettingsComparison.requestRate -= 0.5;
        whatIfSimSettingsComparison.requestRate =
          Math.round(whatIfSimSettingsComparison.requestRate * 10) / 10;
        break;
      case "what-if-demand-add":
        whatIfSimSettingsComparison.requestRate += 0.5;
        whatIfSimSettingsComparison.requestRate =
          Math.round(whatIfSimSettingsComparison.requestRate * 10) / 10;
        break;
    }
    updateWhatIfTopControlValues();
  });
});

DOM_ELEMENTS.whatIf.baselineRadios.forEach((radio) =>
  radio.addEventListener("change", () => {
    if (radio.value == "preset") {
      whatIfSimSettingsBaseline = new WhatIfSimSettingsDefault();
      whatIfSimSettingsComparison = new WhatIfSimSettingsDefault();
    } else if (radio.value == "lab") {
      whatIfSimSettingsBaseline = Object.assign({}, labSimSettings);
      whatIfSimSettingsBaseline.chartType = CHART_TYPES.WHAT_IF;
      whatIfSimSettingsBaseline.name = "whatIfSimSettingsBaseline";
      whatIfSimSettingsBaseline.timeBlocks = 200;
      whatIfSimSettingsBaseline.frameIndex = 0;
      whatIfSimSettingsBaseline.frameTimeout = 0;
      /*
      whatIfSimSettingsBaseline.perMinutePrice = parseFloat(
        whatIfSimSettingsBaseline.perMinutePrice
      );
      whatIfSimSettingsBaseline.perKmPrice = parseFloat(
        whatIfSimSettingsBaseline.perKmPrice
      );
      whatIfSimSettingsBaseline.meanVehicleSpeed = parseFloat(
        whatIfSimSettingsBaseline.meanVehicleSpeed
      );
      */
      // fix the price, even though it isn't used, as it appears in the buttons
      if (whatIfSimSettingsBaseline.useCityScale) {
        whatIfSimSettingsBaseline.price =
          whatIfSimSettingsBaseline.perMinutePrice +
          (whatIfSimSettingsBaseline.perKmPrice *
            whatIfSimSettingsBaseline.meanVehicleSpeed) /
            60.0;
        whatIfSimSettingsBaseline.reservationWage =
          (whatIfSimSettingsBaseline.perHourOpportunityCost +
            whatIfSimSettingsBaseline.perKmOpsCost *
              whatIfSimSettingsBaseline.meanVehicleSpeed) /
          60.0;
      }
      whatIfSimSettingsComparison = Object.assign(
        {},
        whatIfSimSettingsBaseline
      );
      whatIfSimSettingsComparison.name = "whatIfSimSettingsComparison";
    }
    updateWhatIfTopControlValues();
  })
);

/*
 * Top-level controls (reset, play/pause, next step)
 */

function updateSimulationOptions(updateType) {
  labSimSettings.action = updateType;
  w.postMessage(labSimSettings);
}

function updateLabSimSettings(property, value) {
  labSimSettings[property] = value;
}

function toggleWhatIfFabButton(button) {
  if (button.firstElementChild.innerHTML == SimulationActions.Play) {
    button.firstElementChild.innerHTML = SimulationActions.Pause;
    DOM_ELEMENTS.whatIf.setComparisonButtons.forEach(function (element) {
      element.setAttribute("disabled", "");
    });
    DOM_ELEMENTS.whatIf.baselineRadios.forEach((radio) => {
      radio.parentNode.MaterialRadio.disable();
    });
    if (button == DOM_ELEMENTS.whatIf.fabButton) {
      DOM_ELEMENTS.whatIf.fabButton.setAttribute("disabled", "");
      DOM_ELEMENTS.whatIf.comparisonButton.setAttribute("disabled", "");
    } else if (button == DOM_ELEMENTS.whatIf.comparisonButton) {
      DOM_ELEMENTS.whatIf.fabButton.setAttribute("disabled", "");
    }
  } else if (button.firstElementChild.innerHTML == SimulationActions.Pause) {
    DOM_ELEMENTS.whatIf.setComparisonButtons.forEach(function (element) {
      element.removeAttribute("disabled");
    });
    if (button == DOM_ELEMENTS.whatIf.fabButton) {
      // disable the baseline until a reset
      button.setAttribute("disabled", "");
      DOM_ELEMENTS.whatIf.comparisonButton.removeAttribute("disabled");
      DOM_ELEMENTS.whatIf.comparisonButton.firstElementChild.innerHTML =
        SimulationActions.Play;
    } else if (button == DOM_ELEMENTS.whatIf.comparisonButton) {
      // whatIfFabButton.removeAttribute("disabled");
      // whatIfFabButton.firstElementChild.innerHTML = SimulationActions.Play;
      // Require a reset before running the baseline again
      button.firstElementChild.innerHTML = SimulationActions.Play;
    }
  }
}

function resetWhatIfUIAndSimulation() {
  DOM_ELEMENTS.displays.frameCount.innerHTML = 0;
  whatIfSimSettingsComparison.action = SimulationActions.Reset;
  w.postMessage(whatIfSimSettingsComparison);
  DOM_ELEMENTS.whatIf.resetButton.removeAttribute("disabled");
  DOM_ELEMENTS.whatIf.fabButton.removeAttribute("disabled");
  DOM_ELEMENTS.whatIf.comparisonButton.setAttribute("disabled", "");
  DOM_ELEMENTS.whatIf.fabButton.firstElementChild.innerHTML =
    SimulationActions.Play;
  DOM_ELEMENTS.whatIf.baselineRadios.forEach((radio) => {
    radio.parentNode.MaterialRadio.enable();
  });
  document
    .getElementById("what-if-radio-baseline-preset")
    .parentNode.MaterialRadio.check();
  whatIfSimSettingsBaseline = new WhatIfSimSettingsDefault();
  whatIfSimSettingsBaseline.name = "whatIfSimSettingsBaseline";
  whatIfSimSettingsComparison = new WhatIfSimSettingsDefault();
  whatIfSimSettingsComparison.name = "whatIfSimSettingsComparison";
  /* 
    whatIfSimSettingsBaseline = Object.assign({}, labSimSettings);
    whatIfSimSettingsComparison = Object.assign({}, whatIfSimSettingsBaseline);
  */
  DOM_ELEMENTS.whatIf.setComparisonButtons.forEach(function (element) {
    element.setAttribute("disabled", "");
  });
  updateWhatIfTopControlValues();

  // Charts
  baselineData = null;
  // Remove the canvases
  //
  document.querySelectorAll(".what-if-chart-canvas").forEach((e) => e.remove());
  let canvasIDList = [
    "what-if-phases-chart-canvas",
    "what-if-income-chart-canvas",
    "what-if-wait-chart-canvas",
    "what-if-n-chart-canvas",
    "what-if-platform-chart-canvas",
  ];
  let i = 0;
  document.querySelectorAll(".what-if-canvas-parent").forEach(function (e) {
    let canvas = document.createElement("canvas");
    canvas.setAttribute("class", "what-if-chart-canvas");
    canvas.setAttribute("id", canvasIDList[i]);
    e.appendChild(canvas);
    switch (i) {
      case 0:
        whatIfUISettings.ctxWhatIfN = canvas.getContext("2d");
        break;
      case 1:
        whatIfUISettings.ctxWhatIfDemand = canvas.getContext("2d");
        break;
      case 2:
        whatIfUISettings.ctxWhatIfPhases = canvas.getContext("2d");
        break;
      case 3:
        whatIfUISettings.ctxWhatIfIncome = canvas.getContext("2d");
        break;
      case 4:
        whatIfUISettings.ctxWhatIfWait = canvas.getContext("2d");
        break;
      case 5:
        whatIfUISettings.ctxWhatIfPlatform = canvas.getContext("2d");
        break;
    }
    i += 1;
  });

  initWhatIfNChart(baselineData, whatIfUISettings);
  initWhatIfDemandChart(baselineData, whatIfUISettings);
  initWhatIfPhasesChart(baselineData, whatIfUISettings);
  initWhatIfIncomeChart(baselineData, whatIfUISettings);
  initWhatIfWaitChart(baselineData, whatIfUISettings);
  initWhatIfPlatformChart(baselineData, whatIfUISettings);
  initWhatIfTables();
}

function updateWhatIfTopControlValues() {
  document.getElementById("what-if-price").innerHTML = new Intl.NumberFormat(
    "EN-CA",
    {
      style: "currency",
      currency: "CAD",
    }
  ).format(whatIfSimSettingsComparison.price);
  let temperature =
    whatIfSimSettingsComparison.price - whatIfSimSettingsBaseline.price;
  let backgroundColor = "#f0f3f3";
  if (temperature > 0.01) {
    backgroundColor = colors.get("WAITING");
  } else if (temperature < -0.01) {
    backgroundColor = colors.get("IDLE");
  } else {
    backgroundColor = "transparent";
  }
  document.getElementById("what-if-price").style.backgroundColor =
    backgroundColor;
  if (temperature < -0.01 || temperature > 0.01) {
    document.getElementById("what-if-price").style.fontWeight = "bold";
  } else {
    document.getElementById("what-if-price").style.fontWeight = "normal";
  }
  document.getElementById("what-if-commission").innerHTML =
    Math.round(whatIfSimSettingsComparison.platformCommission * 100) + "%";
  temperature =
    whatIfSimSettingsComparison.platformCommission -
    whatIfSimSettingsBaseline.platformCommission;
  if (temperature > 0.01) {
    backgroundColor = colors.get("WAITING");
  } else if (temperature < -0.01) {
    backgroundColor = colors.get("IDLE");
  } else {
    backgroundColor = "transparent";
  }
  document.getElementById("what-if-commission").style.backgroundColor =
    backgroundColor;
  if (temperature < -0.01 || temperature > 0.01) {
    document.getElementById("what-if-commission").style.fontWeight = "bold";
  } else {
    document.getElementById("what-if-commission").style.fontWeight = "normal";
  }
  document.getElementById("what-if-cap").innerHTML =
    whatIfSimSettingsComparison.vehicleCount;
  document.getElementById("what-if-reservation-wage").innerHTML =
    new Intl.NumberFormat("EN-CA", {
      style: "currency",
      currency: "CAD",
    }).format(whatIfSimSettingsComparison.reservationWage * 60);
  temperature =
    whatIfSimSettingsComparison.reservationWage -
    whatIfSimSettingsBaseline.reservationWage;
  if (temperature > 0.001) {
    backgroundColor = colors.get("WAITING");
  } else if (temperature < -0.001) {
    backgroundColor = colors.get("IDLE");
  } else {
    backgroundColor = "transparent";
  }
  document.getElementById("what-if-reservation-wage").style.backgroundColor =
    backgroundColor;
  if (temperature < -0.001 || temperature > 0.001) {
    document.getElementById("what-if-reservation-wage").style.fontWeight =
      "bold";
  } else {
    document.getElementById("what-if-reservation-wage").style.fontWeight =
      "normal";
  }
  document.getElementById("what-if-demand").innerHTML = Math.round(
    whatIfSimSettingsComparison.requestRate * 60
  );
  temperature =
    whatIfSimSettingsComparison.requestRate -
    whatIfSimSettingsBaseline.requestRate;
  if (temperature > 0.01) {
    backgroundColor = colors.get("WAITING");
  } else if (temperature < -0.01) {
    backgroundColor = colors.get("IDLE");
  } else {
    backgroundColor = "transparent";
  }
  document.getElementById("what-if-demand").style.backgroundColor =
    backgroundColor;
  if (temperature < -0.01 || temperature > 0.01) {
    document.getElementById("what-if-demand").style.fontWeight = "bold";
  } else {
    document.getElementById("what-if-demand").style.fontWeight = "normal";
  }
}

function resetLabUIAndSimulation() {
  DOM_ELEMENTS.controls.resetButton.removeAttribute("disabled");
  DOM_ELEMENTS.controls.nextStepButton.removeAttribute("disabled");
  DOM_ELEMENTS.controls.fabButton.removeAttribute("disabled");
  DOM_ELEMENTS.controls.fabButton.firstElementChild.innerHTML =
    SimulationActions.Play;
  DOM_ELEMENTS.displays.spinner.classList.remove("is-active");
  DOM_ELEMENTS.displays.spinner.style.display = "none";
  DOM_ELEMENTS.options.frameTimeout.innerHTML =
    DOM_ELEMENTS.inputs.frameTimeout.value;
  labSimSettings.action = SimulationActions.Reset;
  w.postMessage(labSimSettings);
  labSimSettings.frameIndex = 0;
  DOM_ELEMENTS.displays.frameCount.innerHTML = labSimSettings.frameIndex;
  DOM_ELEMENTS.displays.spinner.style.display = "none";
  /* Simple or advanced? */
  labUIMode.updateUI();

  // Charts
  baselineData = null;
  // Remove the canvases
  let canvasIDList = [
    "pg-city-chart-canvas",
    "pg-phases-chart-canvas",
    "pg-trip-chart-canvas",
    "pg-income-chart-canvas",
    "pg-map-chart-canvas",
    "pg-dummy-chart-canvas",
  ];
  document
    .querySelectorAll(".pg-chart-canvas")
    .forEach((canvas) => canvas.remove());
  let i = 0;
  document.querySelectorAll(".pg-canvas-parent").forEach(function (div) {
    let canvas = document.createElement("canvas");
    canvas.setAttribute("class", "pg-chart-canvas");
    canvas.setAttribute("id", canvasIDList[i]);
    switch (i) {
      case 0:
        if (labUISettings.chartType == CHART_TYPES.STATS) {
          div.removeAttribute("hidden");
          div.appendChild(canvas);
          labUISettings.ctxCity = canvas.getContext("2d");
          initCityChart(labUISettings, labSimSettings);
        } else {
          div.setAttribute("hidden", "");
        }
        break;
      case 1:
        if (labUISettings.chartType == CHART_TYPES.STATS) {
          div.removeAttribute("hidden");
          div.appendChild(canvas);
          labUISettings.ctxPhases = canvas.getContext("2d");
          initPhasesChart(labUISettings, labSimSettings);
        } else {
          div.setAttribute("hidden", "");
        }
        break;
      case 2:
        if (labUISettings.chartType == CHART_TYPES.STATS) {
          div.removeAttribute("hidden");
          div.appendChild(canvas);
          labUISettings.ctxTrip = canvas.getContext("2d");
          initTripChart(labUISettings, labSimSettings);
        } else {
          div.setAttribute("hidden", "");
        }
        break;
      case 3:
        if (labUISettings.chartType == CHART_TYPES.STATS) {
          div.removeAttribute("hidden");
          div.appendChild(canvas);
          labUISettings.ctxIncome = canvas.getContext("2d");
          initIncomeChart(labUISettings, labSimSettings);
        } else {
          div.setAttribute("hidden", "");
        }
        break;
      case 4:
        if (labUISettings.chartType == CHART_TYPES.MAP) {
          div.removeAttribute("hidden");
          div.appendChild(canvas);
          labUISettings.ctxMap = canvas.getContext("2d");
          initMap(labUISettings, labSimSettings);
        } else {
          div.setAttribute("hidden", "");
        }
        break;
      case 5:
        if (labUISettings.chartType == CHART_TYPES.MAP) {
          div.removeAttribute("hidden");
        } else {
          div.setAttribute("hidden", "");
        }
        break;
    }
    i += 1;
  });
}

DOM_ELEMENTS.controls.resetButton.onclick = function () {
  resetLabUIAndSimulation();
};

DOM_ELEMENTS.whatIf.resetButton.onclick = function () {
  resetWhatIfUIAndSimulation();
};

function toggleLabFabButton(button) {
  if (button.firstElementChild.innerHTML == SimulationActions.Play) {
    // The button shows the Play arrow. Toggle it to show Pause
    button.firstElementChild.innerHTML = SimulationActions.Pause;
    // While the simulation is playing, also disable Next Step
    DOM_ELEMENTS.controls.nextStepButton.setAttribute("disabled", "");
    DOM_ELEMENTS.collections.resetControls.forEach(function (element) {
      element.setAttribute("disabled", "");
    });
  } else {
    // The button shows Pause. Toggle it to show the Play arrow.
    button.firstElementChild.innerHTML = SimulationActions.Play;
    // While the simulation is Paused, also enable Reset and Next Step
    DOM_ELEMENTS.controls.nextStepButton.removeAttribute("disabled");
    DOM_ELEMENTS.controls.resetButton.removeAttribute("disabled");
    DOM_ELEMENTS.collections.resetControls.forEach(function (element) {
      element.removeAttribute("disabled");
    });
  }
}

function clickFabButton(button, simSettings) {
  // This function handles both the fabButtons on the Experiment tab and the What If? tab.
  if (button == DOM_ELEMENTS.controls.fabButton) {
    // record current state
    simSettings.frameIndex = DOM_ELEMENTS.displays.frameCount.innerHTML;
    simSettings.chartType = document.querySelector(
      'input[type="radio"][name="chart-type"]:checked'
    ).value;
    simSettings.citySize = parseInt(DOM_ELEMENTS.inputs.citySize.value);
    simSettings.vehicleCount = parseInt(DOM_ELEMENTS.inputs.vehicleCount.value);
    simSettings.requestRate = parseFloat(DOM_ELEMENTS.inputs.requestRate.value);
  }
  if (button.firstElementChild.innerHTML == SimulationActions.Play) {
    // If the button is showing "Play", then the action to take is play
    simSettings.action = SimulationActions.Play;
  } else {
    // The button should be showing "Pause", and the action to take is to pause
    simSettings.action = SimulationActions.Pause;
  }
  w.postMessage(simSettings);
  // Now make the button look different
  if (button == DOM_ELEMENTS.whatIf.fabButton) {
    toggleWhatIfFabButton(button);
  } else if (button == DOM_ELEMENTS.whatIf.comparisonButton) {
    toggleWhatIfFabButton(button);
  } else if (button == DOM_ELEMENTS.controls.fabButton) {
    toggleLabFabButton(button);
  }
}

DOM_ELEMENTS.controls.fabButton.onclick = function () {
  clickFabButton(DOM_ELEMENTS.controls.fabButton, labSimSettings);
};

DOM_ELEMENTS.whatIf.fabButton.onclick = function () {
  clickFabButton(DOM_ELEMENTS.whatIf.fabButton, whatIfSimSettingsBaseline);
};

DOM_ELEMENTS.whatIf.comparisonButton.onclick = function () {
  clickFabButton(
    DOM_ELEMENTS.whatIf.comparisonButton,
    whatIfSimSettingsComparison
  );
};

DOM_ELEMENTS.controls.nextStepButton.onclick = function () {
  labSimSettings.action = SimulationActions.SingleStep;
  w.postMessage(labSimSettings);
};

/*
 * UI Mode radio buttons and their actions
 */

class UIMode {
  /*
   * Represents the controls that toggle the ui mode between basic
   * (in which the "per block" model is used), and advanced, in which
   * the "city scale" units are used
   */
  constructor(labUIsettings, labSimSettings) {
    this.uiSettings = labUISettings;
    this.simSettings = labSimSettings;
    this.advancedControls = document.querySelectorAll(".ui-mode-advanced");
    this.equilibrateControls = document.querySelectorAll(
      ".ui-mode-equilibrate"
    );
    this.simpleControls = document.querySelectorAll(".ui-mode-simple");
    this.uiMode = document.querySelector(
      'input[type="radio"][name="ui-mode"]:checked'
    ).value;
    this.uiModeRadios = document.querySelectorAll(
      'input[type=radio][name="ui-mode"]'
    );
    this.uiModeRadios.forEach((radio) =>
      radio.addEventListener("change", () => {
        this.uiMode = radio.value;
        // I don't think this is needed because it is called from
        // resetLabUIAndSimulation
        // this.updateUI(radio.value);
        resetLabUIAndSimulation();
      })
    );
  }

  updateUI() {
    // this.uiSettings.uiMode = value;
    /* Controls are either advanced (only), simple (only) or both */
    let uiMode = this.uiMode;
    this.simpleControls.forEach(function (element) {
      if (uiMode == "advanced") {
        element.style.display = "none";
      } else {
        element.style.display = "block";
      }
    });
    this.advancedControls.forEach(function (element) {
      if (uiMode == "advanced") {
        element.style.display = "block";
      } else {
        element.style.display = "none";
      }
    });
    /* uimSettings do not use all parameters. Set them to null */
    if (uiMode == "advanced") {
      this.simSettings.useCityScale = true;
      // max trip distance cannoe be bigger than citySize
      this.simSettings.maxTripDistance = parseInt(
        DOM_ELEMENTS.inputs.maxTripDistance.value
      );
    } else if (uiMode == "simple") {
      this.simSettings.useCityScale = false;
      labSimSettings.maxTripDistance = null;
    }
    /* Update ridehail inputs to reflect current labSimSettings */
    let id = "radio-community-" + labSimSettings.scaleType;
    let el = document.getElementById(id).parentElement;
    el.style.backgroundColor = "#f0f3f3";
    el.checked = true;
    el.click();
    id = "radio-chart-type-" + labSimSettings.chartType;
    el = document.getElementById(id).parentElement;
    el.checked = true;
    if (labSimSettings.useCityScale) {
      document.getElementById(
        "radio-ui-mode-advanced"
      ).parentElement.checked = true;
    } else {
      document.getElementById(
        "radio-ui-mode-simple"
      ).parentElement.checked = true;
    }
    DOM_ELEMENTS.inputs.citySize.value = labSimSettings.citySize;
    DOM_ELEMENTS.options.citySize.innerHTML = labSimSettings.citySize;
    DOM_ELEMENTS.inputs.requestRate.value = labSimSettings.requestRate;
    DOM_ELEMENTS.options.requestRate.innerHTML = labSimSettings.requestRate;
    DOM_ELEMENTS.inputs.vehicleCount.value = labSimSettings.vehicleCount;
    DOM_ELEMENTS.options.vehicleCount.innerHTML = labSimSettings.vehicleCount;
    if (labSimSettings.equilibrate) {
      document.getElementById("checkbox-equilibrate").checked = true;
    }
  }
}

var labUISettings = {
  ctxCity: DOM_ELEMENTS.canvases.pgCity.getContext("2d"),
  ctxPhases: DOM_ELEMENTS.canvases.pgPhases.getContext("2d"),
  ctxTrip: DOM_ELEMENTS.canvases.pgTrip.getContext("2d"),
  ctxIncome: DOM_ELEMENTS.canvases.pgIncome.getContext("2d"),
  ctxMap: DOM_ELEMENTS.canvases.pgMap.getContext("2d"),
  chartType: CHART_TYPES.MAP,
  vehicleRadius: 9,
  roadWidth: 10,
};

class ChartType {
  constructor(uiSettings, simSettings) {
    this.uiSettings = uiSettings;
    this.simSettings = simSettings;
    this.chartTypeRadios = document.querySelectorAll(
      'input[type=radio][name="chart-type"]'
    );
    this.chartTypeRadios.forEach((radio) =>
      radio.addEventListener("change", () =>
        this.updateChartType(radio.value, labSimSettings, labUISettings)
      )
    );
  }

  updateChartType(value) {
    // "value" comes in as a string from the UI world
    if (value == CHART_TYPES.STATS) {
      this.uiSettings.chartType = CHART_TYPES.STATS;
      this.simSettings.chartType = CHART_TYPES.STATS;
    } else if (value == CHART_TYPES.MAP) {
      this.uiSettings.chartType = CHART_TYPES.MAP;
      this.simSettings.chartType = CHART_TYPES.MAP;
    } else if (value == CHART_TYPES.WHAT_IF) {
      this.uiSettings.chartType = CHART_TYPES.WHAT_IF;
      this.simSettings.chartType = CHART_TYPES.WHAT_IF;
    }
    if (this.uiSettings.chartType == CHART_TYPES.STATS) {
      DOM_ELEMENTS.inputs.frameTimeout.value = 0;
      this.simSettings.frameTimeout = 0;
    } else if (this.uiSettings.chartType == CHART_TYPES.MAP) {
      DOM_ELEMENTS.inputs.frameTimeout.value = 400;
      this.simSettings.frameTimeout = 400;
    }
    DOM_ELEMENTS.options.frameTimeout.innerHTML =
      DOM_ELEMENTS.inputs.frameTimeout.value;
    let chartType = this.uiSettings.chartType;
    let statsDescriptions = document.querySelectorAll(".pg-stats-descriptions");
    statsDescriptions.forEach(function (element) {
      if (chartType == CHART_TYPES.STATS) {
        element.style.display = "block";
      } else {
        element.style.display = "none";
      }
    });
    resetLabUIAndSimulation();
  }
}

class CityScale {
  constructor() {
    const scaleRadios = document.querySelectorAll(
      'input[type=radio][name="scale"]'
    );
    scaleRadios.forEach((radio) =>
      radio.addEventListener("change", () =>
        this.updateOptionsForScale(radio.value)
      )
    );
  }

  updateOptionsForScale(scale) {
    DOM_ELEMENTS.inputs.citySize.min = SCALE_CONFIGS[scale].citySize.min;
    DOM_ELEMENTS.inputs.citySize.max = SCALE_CONFIGS[scale].citySize.max;
    DOM_ELEMENTS.inputs.citySize.step = SCALE_CONFIGS[scale].citySize.step;
    DOM_ELEMENTS.inputs.citySize.value = SCALE_CONFIGS[scale].citySize.value;
    DOM_ELEMENTS.options.citySize.innerHTML =
      SCALE_CONFIGS[scale].citySize.value;
    DOM_ELEMENTS.inputs.vehicleCount.min =
      SCALE_CONFIGS[scale].vehicleCount.min;
    DOM_ELEMENTS.inputs.vehicleCount.max =
      SCALE_CONFIGS[scale].vehicleCount.max;
    DOM_ELEMENTS.inputs.vehicleCount.step =
      SCALE_CONFIGS[scale].vehicleCount.step;
    DOM_ELEMENTS.inputs.vehicleCount.value =
      SCALE_CONFIGS[scale].citySize.value;
    DOM_ELEMENTS.options.vehicleCount.innerHTML =
      SCALE_CONFIGS[scale].vehicleCount.value;
    DOM_ELEMENTS.inputs.maxTripDistance.min =
      SCALE_CONFIGS[scale].maxTripDistance.min;
    DOM_ELEMENTS.inputs.maxTripDistance.max =
      SCALE_CONFIGS[scale].maxTripDistance.max;
    DOM_ELEMENTS.inputs.maxTripDistance.step =
      SCALE_CONFIGS[scale].maxTripDistance.step;
    DOM_ELEMENTS.inputs.maxTripDistance.value =
      SCALE_CONFIGS[scale].maxTripDistance.value;
    DOM_ELEMENTS.options.maxTripDistance.innerHTML =
      SCALE_CONFIGS[scale].maxTripDistance.value;
    DOM_ELEMENTS.inputs.requestRate.min = SCALE_CONFIGS[scale].requestRate.min;
    DOM_ELEMENTS.inputs.requestRate.max = SCALE_CONFIGS[scale].requestRate.max;
    DOM_ELEMENTS.inputs.requestRate.step =
      SCALE_CONFIGS[scale].requestRate.step;
    DOM_ELEMENTS.inputs.requestRate.value =
      SCALE_CONFIGS[scale].requestRate.value;
    DOM_ELEMENTS.options.requestRate.innerHTML =
      SCALE_CONFIGS[scale].requestRate.value;
    DOM_ELEMENTS.inputs.price.value = SCALE_CONFIGS[scale].defaultPrice;
    DOM_ELEMENTS.options.price.innerHTML = SCALE_CONFIGS[scale].defaultPrice;
    DOM_ELEMENTS.inputs.platformCommission.value =
      SCALE_CONFIGS[scale].defaultCommission;
    DOM_ELEMENTS.options.platformCommission.innerHTML =
      SCALE_CONFIGS[scale].defaultCommission;
    DOM_ELEMENTS.inputs.reservationWage.value =
      SCALE_CONFIGS[scale].defaultReservationWage;
    DOM_ELEMENTS.options.reservationWage.innerHTML =
      SCALE_CONFIGS[scale].defaultReservationWage;
    DOM_ELEMENTS.inputs.demandElasticity.value =
      SCALE_CONFIGS[scale].demandElasticity;
    DOM_ELEMENTS.options.demandElasticity.innerHTML =
      SCALE_CONFIGS[scale].demandElasticity;
    labUISettings.roadWidth = SCALE_CONFIGS[scale].roadWidth;
    labUISettings.vehicleRadius = SCALE_CONFIGS[scale].vehicleRadius;
    labSimSettings.action = SimulationActions.Reset;
    labSimSettings.frameIndex = 0;
    labSimSettings.scaleType = scale;
    labSimSettings.chartType = CHART_TYPES.MAP;
    labSimSettings.citySize = SCALE_CONFIGS[scale].citySize.value;
    resetLabUIAndSimulation();
  }
}

/*
 * Capture keypress events
 */

document.addEventListener("keyup", function (event) {
  if (event.key === "z" || event.key === "Z") {
    // zoom
    const elementList = document.querySelectorAll(".ui-zoom-hide");
    elementList.forEach(function (element) {
      if (element.style.display == "none") {
        element.style.display = "block";
      } else {
        element.style.display = "none";
      }
    });
    let element = document.getElementById("chart-column");
    element.classList.toggle("mdl-cell--5-col");
    element.classList.toggle("mdl-cell--10-col");
    element = document.getElementById("what-if-chart-column");
    element.classList.toggle("mdl-cell--8-col");
    element.classList.toggle("mdl-cell--12-col");
  } else if (event.key === "p" || event.key === "P") {
    clickFabButton(DOM_ELEMENTS.controls.fabButton, labSimSettings);
  }
});

var labSimSettings = createSettingsFromConfig(
  LAB_SETTINGS_CONFIG,
  DOM_ELEMENTS
);

var labUIMode = new UIMode(labUISettings, labSimSettings);
var chartType = new ChartType(labUISettings, labSimSettings);
var cityScale = new CityScale();

const whatIfSettingsTable = document.getElementById("what-if-table-settings");
const whatIfMeasuresTable = document.getElementById("what-if-table-measures");
var whatIfUISettings = {
  ctxWhatIfN: DOM_ELEMENTS.whatIf.canvases.n.getContext("2d"),
  ctxWhatIfDemand: DOM_ELEMENTS.whatIf.canvases.demand.getContext("2d"),
  ctxWhatIfPhases: DOM_ELEMENTS.whatIf.canvases.phases.getContext("2d"),
  ctxWhatIfIncome: DOM_ELEMENTS.whatIf.canvases.income.getContext("2d"),
  ctxWhatIfWait: DOM_ELEMENTS.whatIf.canvases.wait.getContext("2d"),
  ctxWhatIfPlatform: DOM_ELEMENTS.whatIf.canvases.platform.getContext("2d"),
  chartType: CHART_TYPES.WHAT_IF,
  cityScale: cityScale,
  settingsTable: whatIfSettingsTable,
  measuresTable: whatIfMeasuresTable,
};

var whatIfSimSettingsBaseline = new WhatIfSimSettingsDefault();
var whatIfSimSettingsComparison = new WhatIfSimSettingsDefault();
whatIfSimSettingsBaseline.name = "whatIfSimSettingsBaseline";
whatIfSimSettingsComparison.name = "whatIfSimSettingsComparison";

window.onload = function () {
  //resetLabUIAndSimulation();
};

document.addEventListener("DOMContentLoaded", () => {
  setupInputHandlers({
    updateSettings: updateLabSimSettings,
    resetSimulation: resetLabUIAndSimulation,
    updateSimulation: updateSimulationOptions,
  });
});

/*
 * Interaction with web worker
 */
// Initialize the message handler
const messageHandler = new MessageHandler(
  handlePyodideReady,
  updateFrameCounters
);

export function handlePyodideReady() {
  resetLabUIAndSimulation();
  resetWhatIfUIAndSimulation();
}

export function updateFrameCounters(resultsMap) {
  const frameIndex = resultsMap.get("block");
  const name = resultsMap.get("name");
  const counterUpdaters = {
    labSimSettings: () => {
      DOM_ELEMENTS.displays.frameCount.innerHTML = frameIndex;
      if (
        frameIndex >= labSimSettings.timeBlocks &&
        labSimSettings.timeBlocks !== 0
      ) {
        labSimSettings.action = SimulationActions.Done;
        w.postMessage(labSimSettings);
        toggleLabFabButton();
      }
    },
    whatIfSimSettingsBaseline: () => {
      if (frameIndex % 10 === 0) {
        document.getElementById(
          "what-if-frame-count"
        ).innerHTML = `${frameIndex}/${resultsMap.get("time_blocks")}`;
      }
      if (
        frameIndex >= whatIfSimSettingsBaseline.timeBlocks &&
        whatIfSimSettingsBaseline.timeBlocks !== 0
      ) {
        whatIfSimSettingsBaseline.action = SimulationActions.Done;
        whatIfController.baselineData = resultsMap;
        w.postMessage(whatIfSimSettingsBaseline);
        toggleWhatIfFabButton(DOM_ELEMENTS.whatIf.fabButton);
      }
    },
    whatIfSimSettingsComparison: () => {
      if (frameIndex % 10 === 0) {
        document.getElementById(
          "what-if-frame-count"
        ).innerHTML = `${frameIndex} / ${resultsMap.get("time_blocks")}`;
      }
      if (
        frameIndex >= whatIfSimSettingsComparison.timeBlocks &&
        whatIfSimSettingsComparison.timeBlocks !== 0
      ) {
        whatIfSimSettingsComparison.action = SimulationActions.Done;
        w.postMessage(whatIfSimSettingsComparison);
        toggleWhatIfFabButton(DOM_ELEMENTS.whatIf.comparisonButton);
      }
    },
  };

  const updater = counterUpdaters[name];
  if (updater) {
    updater();
  }
}
