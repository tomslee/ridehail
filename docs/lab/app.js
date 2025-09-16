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
  CITY_SCALE,
} from "./js/config.js";
import {
  SimSettings,
  WhatIfSimSettingsDefault,
  createSettingsFromConfig,
} from "./js/sim-settings.js";
import {
  setupInputHandlers,
  createChartTypeRadioHandler,
  createModeRadioHandler,
} from "./js/input-handlers.js";
import { MessageHandler } from "./js/message-handler.js";

// Global variables
let labSimSettings = new SimSettings(SCALE_CONFIGS.village, "labSimSettings");
let baselineData = null; // holds results for baseline run in WhatIf comparisons
let labUISettings = {
  ctxCity: DOM_ELEMENTS.canvases.labCity.getContext("2d"),
  ctxPhases: DOM_ELEMENTS.canvases.labPhases.getContext("2d"),
  ctxTrip: DOM_ELEMENTS.canvases.labTrip.getContext("2d"),
  ctxIncome: DOM_ELEMENTS.canvases.labIncome.getContext("2d"),
  ctxMap: DOM_ELEMENTS.canvases.labMap.getContext("2d"),
  chartType: CHART_TYPES.MAP,
  scle: CITY_SCALE.VILLAGE,
  displayVehicleRadius: 9,
  displayRoadWidth: 10,
};
const messageHandler = new MessageHandler(
  handlePyodideReady,
  updateFrameCounters
);
const labCanvasIDList = [
  "lab-city-chart-canvas",
  "lab-phases-chart-canvas",
  "lab-trip-chart-canvas",
  "lab-income-chart-canvas",
  "lab-map-chart-canvas",
  "lab-dummy-chart-canvas",
];
const whatIfCanvasIDList = [
  "what-if-phases-chart-canvas",
  "what-if-income-chart-canvas",
  "what-if-wait-chart-canvas",
  "what-if-n-chart-canvas",
  "what-if-platform-chart-canvas",
];
let whatIfUISettings = {
  ctxWhatIfN: DOM_ELEMENTS.whatIf.canvases.n.getContext("2d"),
  ctxWhatIfDemand: DOM_ELEMENTS.whatIf.canvases.demand.getContext("2d"),
  ctxWhatIfPhases: DOM_ELEMENTS.whatIf.canvases.phases.getContext("2d"),
  ctxWhatIfIncome: DOM_ELEMENTS.whatIf.canvases.income.getContext("2d"),
  ctxWhatIfWait: DOM_ELEMENTS.whatIf.canvases.wait.getContext("2d"),
  ctxWhatIfPlatform: DOM_ELEMENTS.whatIf.canvases.platform.getContext("2d"),
  chartType: CHART_TYPES.WHAT_IF,
  settingsTable: DOM_ELEMENTS.whatIf.settingsTable,
  measuresTable: DOM_ELEMENTS.whatIf.measuresTable,
};
let whatIfSimSettingsBaseline = new WhatIfSimSettingsDefault();
let whatIfSimSettingsComparison = new WhatIfSimSettingsDefault();
whatIfSimSettingsBaseline.name = "whatIfSimSettingsBaseline";
whatIfSimSettingsComparison.name = "whatIfSimSettingsComparison";

class App {
  constructor() {
    // Don't move globals yet - just reference them
    this.labSimsettings = labSimSettings;
    this.init();
  }

  init() {
    // Move initialization code here gradually
    this.setupButtonHandlers();
    this.setupForEachHandlers();
    setupInputHandlers({
      updateSettings: this.updateLabSimSettings,
      resetSimulation: () => this.resetLabUIAndSimulation(),
      updateSimulation: this.updateSimulationOptions,
    });
    this.setInitialValues(false);
  }

  /*
   * Resets the charts to initial state, and the control buttons
   * (reset, fab, nextstep) and status display (timeout, spinner)
   */
  setInitialValues(isReady = false) {
    const scale = labSimSettings.scale;
    const scaleConfig = SCALE_CONFIGS[scale];
    labSimSettings = new SimSettings(scaleConfig, "labSimSettings");
    w.postMessage(labSimSettings);
    // reset complete
    labUISettings.displayRoadWidth = scaleConfig.displayRoadWidth;
    labUISettings.displayVehicleRadius = scaleConfig.displayVehicleRadius;
    this.setLabTopControls(isReady);
    this.setLabConfigControls(scaleConfig);
    this.initLabCharts();
  }

  setupButtonHandlers() {
    DOM_ELEMENTS.controls.resetButton.onclick = () =>
      this.resetLabUIAndSimulation();

    DOM_ELEMENTS.whatIf.resetButton.onclick = () =>
      this.resetWhatIfUIAndSimulation();

    DOM_ELEMENTS.controls.fabButton.onclick = () => {
      this.clickFabButton(DOM_ELEMENTS.controls.fabButton, labSimSettings);
    };

    DOM_ELEMENTS.whatIf.baselineFabButton.onclick = () =>
      this.clickFabButton(
        DOM_ELEMENTS.whatIf.baselineFabButton,
        whatIfSimSettingsBaseline
      );

    DOM_ELEMENTS.whatIf.comparisonFabButton.onclick = () =>
      this.clickFabButton(
        DOM_ELEMENTS.whatIf.comparisonFabButton,
        whatIfSimSettingsComparison
      );

    DOM_ELEMENTS.controls.nextStepButton.onclick = () => {
      labSimSettings.action = SimulationActions.SingleStep;
      w.postMessage(labSimSettings);
    };
  }

  setupForEachHandlers() {
    const app = this;
    DOM_ELEMENTS.collections.tabList.forEach(function (element) {
      // destroy any existing charts
      element.onclick = (event) => {
        if (window.chart instanceof Chart) {
          window.chart.destroy();
        }
        if (window.statsChart instanceof Chart) {
          window.statsChart.destroy();
        }
        switch (event.currentTarget.id) {
          case "tab-experiment":
            app.resetLabUIAndSimulation();
            break;
          case "tab-what-if":
            app.resetWhatIfUIAndSimulation();
            break;
          case "tab-read":
            break;
          case "tab-TO":
            break;
        }
      };
    });

    DOM_ELEMENTS.collections.scaleRadios.forEach((radio) =>
      radio.addEventListener("change", () => {
        // any change of scale demands a new set of values
        labSimSettings.scale = radio.value;
        this.setInitialValues(true);
      })
    );

    document.addEventListener("keyup", function (event) {
      if (event.key === "z" || event.key === "Z") {
        // zoom
        DOM_ELEMENTS.collections.zoom.forEach(function (element) {
          element.classList.toggle("hidden");
        });
        // reset column widths
        DOM_ELEMENTS.charts.chartColumn.classList.toggle("mdl-cell--6-col");
        DOM_ELEMENTS.charts.chartColumn.classList.toggle("mdl-cell--10-col");
        DOM_ELEMENTS.whatIf.chartColumn.classList.toggle("mdl-cell--8-col");
        DOM_ELEMENTS.whatIf.chartColumn.classList.toggle("mdl-cell--12-col");
      } else if (event.key === "p" || event.key === "P") {
        this.clickFabButton(DOM_ELEMENTS.controls.fabButton, labSimSettings);
      }
    });

    DOM_ELEMENTS.whatIf.setComparisonButtons.forEach(function (element) {
      element.addEventListener("click", function () {
        switch (this.id) {
          case "what-if-price-remove":
            if (whatIfSimSettingsComparison.useCostsAndIncomes) {
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
            if (whatIfSimSettingsComparison.useCostsAndIncomes) {
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
              Math.round(whatIfSimSettingsComparison.platformCommission * 20) /
              20;
            break;
          case "what-if-commission-add":
            whatIfSimSettingsComparison.platformCommission += 0.05;
            whatIfSimSettingsComparison.platformCommission =
              Math.round(whatIfSimSettingsComparison.platformCommission * 20) /
              20;
            break;
          case "what-if-reservation-wage-remove":
            if (whatIfSimSettingsComparison.useCostsAndIncomes) {
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
              Math.round(whatIfSimSettingsComparison.reservationWage * 100) /
              100;
            break;
          case "what-if-reservation-wage-add":
            if (whatIfSimSettingsComparison.useCostsAndIncomes) {
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
              Math.round(whatIfSimSettingsComparison.reservationWage * 100) /
              100;
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
        this.updateWhatIfTopControlValues();
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
          if (whatIfSimSettingsBaseline.useCostsAndIncomes) {
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
        this.updateWhatIfTopControlValues();
      })
    );
  }

  setLabTopControls(isReady = False) {
    // --- Set the state of the "top controls" in the bar above the text
    // Some settings are based on current labSimSettings
    if (isReady) {
      DOM_ELEMENTS.displays.spinner.classList.remove("is-active");
      DOM_ELEMENTS.displays.spinner.style.display = "none";
      DOM_ELEMENTS.controls.fabButton.firstElementChild.innerHTML =
        SimulationActions.Play;
      const buttonArray = ["resetButton", "fabButton", "nextStepButton"];
      buttonArray.forEach(function (value, index) {
        DOM_ELEMENTS.controls[value].removeAttribute("disabled");
      });
      DOM_ELEMENTS.displays.frameCount.innerHTML = 0;
    }
    // Set Scale radio buttons from current scale
    const scaleId = "radio-community-" + labSimSettings.scale;
    const scaleEl = document.getElementById(scaleId).parentElement;
    scaleEl.style.backgroundColor = "#f0f3f3";
    scaleEl.checked = true;
    // scaleEl.click();
    // Set chart type radio buttons from current labSimSettings
    const chartTypeId = "radio-chart-type-" + labSimSettings.chartType;
    const chartTypeEl = document.getElementById(chartTypeId).parentElement;
    chartTypeEl.checked = true;
    // Set simple / advanced mode radio buttons from current labSimSettings
    if (labSimSettings.useCostsAndIncomes) {
      document.getElementById(
        "radio-ui-mode-advanced"
      ).parentElement.checked = true;
    } else {
      document.getElementById(
        "radio-ui-mode-simple"
      ).parentElement.checked = true;
    }
    // define the listener for the chart type handler, which calls back
    // to updateChartType defined in this file
    createChartTypeRadioHandler((value) => this.updateChartType(value));
    createModeRadioHandler((value) => this.updateMode(value));
  }

  setLabConfigControls(scaleConfig) {
    // --- initialize slider inputs and options with min/max/step/value ---
    const sliderControls = [
      "citySize",
      "vehicleCount",
      "requestRate",
      "maxTripDistance",
      "inhomogeneity",
      "price",
      "platformCommission",
      "reservationWage",
      "demandElasticity",
      "meanVehicleSpeed",
      "perKmPrice",
      "perMinutePrice",
      "perKmOpsCost",
      "perHourOpportunityCost",
      "frameTimeout",
      "smoothingWindow",
    ];
    sliderControls.forEach((controlName) => {
      const inputElement = DOM_ELEMENTS.inputs[controlName];
      const optionElement = DOM_ELEMENTS.options[controlName];
      const config = scaleConfig[controlName];

      Object.assign(inputElement, {
        min: config.min,
        max: config.max,
        step: config.step,
        value: config.value,
      });
      optionElement.innerHTML = labSimSettings[controlName];
    });
    DOM_ELEMENTS.checkboxes.equilibrate.checked = scaleConfig.equilibrate;

    /* Controls are either advanced (only), simple (only) or both */
    // const uiMode = document.querySelector(
    // 'input[type="radio"][name="ui-mode"]:checked'
    // ).value;
    const uiMode = DOM_ELEMENTS.collections.getSelectedUiMode();
    DOM_ELEMENTS.collections.simpleControls.forEach(function (element) {
      if (uiMode == "advanced") {
        element.style.display = "none";
      } else {
        element.style.display = "block";
      }
    });
    DOM_ELEMENTS.collections.advancedControls.forEach(function (element) {
      if (uiMode == "advanced") {
        element.style.display = "block";
      } else {
        element.style.display = "none";
      }
    });
  }

  initLabCharts() {
    // Charts
    // Remove any existing canvases
    document
      .querySelectorAll(".lab-chart-canvas")
      .forEach((canvas) => canvas.remove());
    let i = 0;
    DOM_ELEMENTS.collections.canvasParents.forEach(function (div) {
      let canvas = document.createElement("canvas");
      canvas.setAttribute("class", "lab-chart-canvas");
      canvas.setAttribute("id", labCanvasIDList[i]);
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

  resetLabUIAndSimulation() {
    labSimSettings.resetToStart();
    w.postMessage(labSimSettings);
    this.initLabCharts();
  }

  toggleLabFabButton(button) {
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

  clickFabButton(button, simSettings) {
    // This function handles both the fabButtons on the Experiment tab and the What If? tab.
    if (button == DOM_ELEMENTS.controls.fabButton) {
      // record current UI controls state in simSettings
      simSettings.frameIndex = DOM_ELEMENTS.displays.frameCount.innerHTML;
      simSettings.chartType = document.querySelector(
        'input[type="radio"][name="chart-type"]:checked'
      ).value;
      simSettings.citySize = parseInt(DOM_ELEMENTS.inputs.citySize.value);
      simSettings.vehicleCount = parseInt(
        DOM_ELEMENTS.inputs.vehicleCount.value
      );
      simSettings.requestRate = parseFloat(
        DOM_ELEMENTS.inputs.requestRate.value
      );
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
    if (button == DOM_ELEMENTS.whatIf.baselineFabButton) {
      this.toggleWhatIfFabButton(button);
    } else if (button == DOM_ELEMENTS.whatIf.comparisonFabButton) {
      this.toggleWhatIfFabButton(button);
    } else if (button == DOM_ELEMENTS.controls.fabButton) {
      this.toggleLabFabButton(button);
    }
  }

  updateChartType(value) {
    // "value" comes in as a string from the UI world
    if (value == CHART_TYPES.STATS) {
      labUISettings.chartType = CHART_TYPES.STATS;
      labSimSettings.chartType = CHART_TYPES.STATS;
    } else if (value == CHART_TYPES.MAP) {
      labUISettings.chartType = CHART_TYPES.MAP;
      labSimSettings.chartType = CHART_TYPES.MAP;
    } else if (value == CHART_TYPES.WHAT_IF) {
      labUISettings.chartType = CHART_TYPES.WHAT_IF;
      labSimSettings.chartType = CHART_TYPES.WHAT_IF;
    }
    if (labUISettings.chartType == CHART_TYPES.STATS) {
      DOM_ELEMENTS.inputs.frameTimeout.value = 0;
      labSimSettings.frameTimeout = 0;
    } else if (labUISettings.chartType == CHART_TYPES.MAP) {
      DOM_ELEMENTS.inputs.frameTimeout.value = 400;
      labSimSettings.frameTimeout = 400;
    }
    DOM_ELEMENTS.options.frameTimeout.innerHTML =
      DOM_ELEMENTS.inputs.frameTimeout.value;
    let chartType = labUISettings.chartType;
    DOM_ELEMENTS.collections.statsDescriptions.forEach(function (element) {
      if (chartType == CHART_TYPES.STATS) {
        element.style.display = "block";
      } else {
        element.style.display = "none";
      }
    });
    this.initLabCharts();
  }

  updateMode(value) {
    this.updateLabSimSettings("uiMode", value);
    this.resetLabUIAndSimulation();
    const scale = labSimSettings.scale;
    const scaleConfig = SCALE_CONFIGS[scale];
    this.setLabConfigControls(scaleConfig);
  }

  updateSimulationOptions(updateType) {
    labSimSettings.action = updateType;
    w.postMessage(labSimSettings);
  }

  updateLabSimSettings(property, value) {
    labSimSettings[property] = value;
  }

  toggleWhatIfFabButton(button) {
    if (button.firstElementChild.innerHTML == SimulationActions.Play) {
      button.firstElementChild.innerHTML = SimulationActions.Pause;
      DOM_ELEMENTS.whatIf.setComparisonButtons.forEach(function (element) {
        element.setAttribute("disabled", "");
      });
      DOM_ELEMENTS.whatIf.baselineRadios.forEach((radio) => {
        radio.parentNode.MaterialRadio.disable();
      });
      if (button == DOM_ELEMENTS.whatIf.baselineFabButton) {
        DOM_ELEMENTS.whatIf.baselineFabButton.setAttribute("disabled", "");
        DOM_ELEMENTS.whatIf.comparisonFabButton.setAttribute("disabled", "");
      } else if (button == DOM_ELEMENTS.whatIf.comparisonFabButton) {
        DOM_ELEMENTS.whatIf.baselineFabButton.setAttribute("disabled", "");
      }
    } else if (button.firstElementChild.innerHTML == SimulationActions.Pause) {
      DOM_ELEMENTS.whatIf.setComparisonButtons.forEach(function (element) {
        element.removeAttribute("disabled");
      });
      if (button == DOM_ELEMENTS.whatIf.baselineFabButton) {
        // disable the baseline until a reset
        button.setAttribute("disabled", "");
        DOM_ELEMENTS.whatIf.comparisonFabButton.removeAttribute("disabled");
        DOM_ELEMENTS.whatIf.comparisonFabButton.firstElementChild.innerHTML =
          SimulationActions.Play;
      } else if (button == DOM_ELEMENTS.whatIf.comparisonFabButton) {
        // whatIfFabButton.removeAttribute("disabled");
        // whatIfFabButton.firstElementChild.innerHTML = SimulationActions.Play;
        // Require a reset before running the baseline again
        button.firstElementChild.innerHTML = SimulationActions.Play;
      }
    }
  }

  resetWhatIfUIAndSimulation() {
    DOM_ELEMENTS.whatIf.frameCount.innerHTML = 0;
    whatIfSimSettingsComparison.action = SimulationActions.Reset;
    w.postMessage(whatIfSimSettingsComparison);
    DOM_ELEMENTS.whatIf.resetButton.removeAttribute("disabled");
    DOM_ELEMENTS.whatIf.baselineFabButton.removeAttribute("disabled");
    DOM_ELEMENTS.whatIf.comparisonFabButton.setAttribute("disabled", "");
    DOM_ELEMENTS.whatIf.baselineFabButton.firstElementChild.innerHTML =
      SimulationActions.Play;
    DOM_ELEMENTS.whatIf.baselineRadios.forEach((radio) => {
      radio.parentNode.MaterialRadio.enable();
    });
    DOM_ELEMENTS.whatIf.baselinePreset.parentNode.MaterialRadio.check();
    whatIfSimSettingsBaseline = new WhatIfSimSettingsDefault();
    whatIfSimSettingsComparison = new WhatIfSimSettingsDefault();
    whatIfSimSettingsComparison.name = "whatIfSimSettingsComparison";
    /* 
    whatIfSimSettingsBaseline = Object.assign({}, labSimSettings);
    whatIfSimSettingsComparison = Object.assign({}, whatIfSimSettingsBaseline);
  */
    DOM_ELEMENTS.whatIf.setComparisonButtons.forEach(function (element) {
      element.setAttribute("disabled", "");
    });
    this.updateWhatIfTopControlValues();

    // Charts
    // Remove the canvases
    document
      .querySelectorAll(".what-if-chart-canvas")
      .forEach((e) => e.remove());

    // Create new canvases
    let i = 0;
    DOM_ELEMENTS.whatIf.canvasParents.forEach(function (e) {
      let canvas = document.createElement("canvas");
      canvas.setAttribute("class", "what-if-chart-canvas");
      canvas.setAttribute("id", whatIfCanvasIDList[i]);
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

    initWhatIfNChart(whatIfUISettings);
    initWhatIfDemandChart(whatIfUISettings);
    initWhatIfPhasesChart(whatIfUISettings);
    initWhatIfIncomeChart(whatIfUISettings);
    initWhatIfWaitChart(whatIfUISettings);
    initWhatIfPlatformChart(whatIfUISettings);
    initWhatIfTables();
  }

  updateWhatIfTopControlValues() {
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
} // App

// Create single instance but keep globals accessible
document.addEventListener("DOMContentLoaded", () => {
  window.app = new App(); // Make it globally accessible });during transition
});

export function handlePyodideReady() {
  window.app.setInitialValues(true);
  window.app.resetWhatIfUIAndSimulation();
}

export function updateFrameCounters(results) {
  const frameIndex = results.get("block");
  const name = results.get("name");
  const counterUpdaters = {
    labSimSettings: () => {
      DOM_ELEMENTS.displays.frameCount.innerHTML = frameIndex;
      if (
        frameIndex >= labSimSettings.timeBlocks &&
        labSimSettings.timeBlocks !== 0
      ) {
        labSimSettings.action = SimulationActions.Done;
        w.postMessage(labSimSettings);
        window.app.toggleLabFabButton();
      }
    },
    whatIfSimSettingsBaseline: () => {
      if (frameIndex % 10 === 0) {
        DOM_ELEMENTS.whatIf.frameCount.innerHTML = `${frameIndex}/${results.get(
          "time_blocks"
        )}`;
      }
      if (
        frameIndex >= whatIfSimSettingsBaseline.timeBlocks &&
        whatIfSimSettingsBaseline.timeBlocks !== 0
      ) {
        whatIfSimSettingsBaseline.action = SimulationActions.Done;
        baselineData = results;
        w.postMessage(whatIfSimSettingsBaseline);
        window.app.toggleWhatIfFabButton(DOM_ELEMENTS.whatIf.baselineFabButton);
      }
    },
    whatIfSimSettingsComparison: () => {
      if (frameIndex % 10 === 0) {
        DOM_ELEMENTS.whatIf.frameCount.innerHTML = `${frameIndex} / ${results.get(
          "time_blocks"
        )}`;
      }
      if (
        frameIndex >= whatIfSimSettingsComparison.timeBlocks &&
        whatIfSimSettingsComparison.timeBlocks !== 0
      ) {
        whatIfSimSettingsComparison.action = SimulationActions.Done;
        w.postMessage(whatIfSimSettingsComparison);
        window.app.toggleWhatIfFabButton(
          DOM_ELEMENTS.whatIf.comparisonFabButton
        );
      }
    },
  };

  const updater = counterUpdaters[name];
  if (updater) {
    updater();
  }
}
