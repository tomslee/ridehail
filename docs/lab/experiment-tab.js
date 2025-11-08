/*
 * Experiment Tab Controller
 * Handles all functionality specific to the Experiment tab
 * Created: 2024-12 - Refactored from app.js
 */

import {
  initCityChart,
  initPhasesChart,
  initTripChart,
  initIncomeChart,
} from "./modules/stats.js";
import { initMap } from "./modules/map.js";
import { DOM_ELEMENTS } from "./js/dom-elements.js";
import { SimulationActions, SCALE_CONFIGS, CHART_TYPES } from "./js/config.js";
import { SimSettings } from "./js/sim-settings.js";
import { appState } from "./js/app-state.js";
import {
  addDoubleClickHandler,
  addMobileTouchHandlers,
} from "./js/fullscreen.js";
import { saveLabSettings, saveUIState } from "./js/session-storage.js";
import { resetVehicleCountTracking } from "./js/vehicle-count-monitor.js";

const labCanvasIDList = [
  "lab-city-chart-canvas",
  "lab-phases-chart-canvas",
  "lab-trip-chart-canvas",
  "lab-income-chart-canvas",
  "lab-map-chart-canvas",
  "lab-dummy-chart-canvas",
];

export class ExperimentTab {
  constructor(app, fullScreenManager) {
    this.app = app;
    this.fullScreenManager = fullScreenManager;
  }

  /**
   * Initialize the Experiment tab with default values
   * @param {boolean} isReady - Whether Pyodide is ready
   */
  setInitialValues(isReady = false) {
    const scale = appState.labSimSettings.scale;
    const scaleConfig = SCALE_CONFIGS[scale];
    appState.labSimSettings = new SimSettings(scaleConfig, "labSimSettings");
    w.postMessage(appState.labSimSettings);
    // reset complete
    resetVehicleCountTracking();
    appState.labUISettings.displayRoadWidth = scaleConfig.displayRoadWidth;
    appState.labUISettings.displayVehicleRadius =
      scaleConfig.displayVehicleRadius;
    this.setLabTopControls(isReady);
    this.setLabConfigControls(scaleConfig);
    this.initLabCharts();
  }

  /**
   * Set the state of the top controls (reset, fab, next step buttons)
   * @param {boolean} isReady - Whether Pyodide is ready
   */
  setLabTopControls(isReady = false) {
    // --- Set the state of the "top controls" in the bar above the text
    // Some settings are based on current labSimSettings
    if (isReady) {
      const icon =
        DOM_ELEMENTS.controls.fabButton.querySelector(".material-icons");
      const text =
        DOM_ELEMENTS.controls.fabButton.querySelector(".app-button__text");
      icon.innerHTML = SimulationActions.Play;
      // if (text) text.textContent = 'Run';
      const buttonArray = ["resetButton", "fabButton", "nextStepButton"];
      buttonArray.forEach(function (value, index) {
        DOM_ELEMENTS.controls[value].removeAttribute("disabled");
      });
      DOM_ELEMENTS.displays.blockCount.innerHTML = 0;
    }
    // Set Scale radio buttons from current scale
    const scaleId = "radio-community-" + appState.labSimSettings.scale;
    const scaleEl = document.getElementById(scaleId).parentElement;
    scaleEl.style.backgroundColor = "#f0f3f3";
    scaleEl.checked = true;
    // Set chart type radio buttons from current labSimSettings
    const chartTypeId = "radio-chart-type-" + appState.labSimSettings.chartType;
    const chartTypeEl = document.getElementById(chartTypeId).parentElement;
    chartTypeEl.checked = true;
    // Set simple / advanced mode radio buttons from current labSimSettings
    if (appState.labSimSettings.useCostsAndIncomes) {
      document.getElementById("radio-ui-mode-advanced").parentElement.checked =
        true;
    } else {
      document.getElementById("radio-ui-mode-simple").parentElement.checked =
        true;
    }
  }

  /**
   * Set the configuration controls (sliders, checkboxes) based on scale config
   * @param {Object} scaleConfig - Scale configuration object
   */
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
      "animationDelay",
      "smoothingWindow",
      "pickupTime",
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
      optionElement.innerHTML = appState.labSimSettings[controlName];
    });
    // Set equilibrate checkbox from labSimSettings (not scaleConfig which doesn't have it)
    DOM_ELEMENTS.checkboxes.equilibrate.checked = appState.labSimSettings.equilibrate || false;

    // Sync the equilibration string to match the checkbox state
    // This ensures consistency after initialization or reset
    appState.labSimSettings.equilibration = appState.labSimSettings.equilibrate ? "price" : "none";

    // Update visibility based on all conditions (mode + equilibrate)
    this.updateControlVisibility();
  }

  /**
   * Update control visibility based on all conditions (ui mode + equilibrate state)
   * Evaluates combined visibility rules for controls with multiple class-based conditions
   */
  updateControlVisibility() {
    const uiMode = DOM_ELEMENTS.collections.getSelectedUiMode();
    const equilibrateChecked = DOM_ELEMENTS.checkboxes.equilibrate.checked;

    // Evaluate each control based on ALL its classes
    document.querySelectorAll(".ui-ridehail-settings").forEach((element) => {
      const isSimpleOnly = element.classList.contains("ui-mode-simple");
      const isAdvancedOnly = element.classList.contains("ui-mode-advanced");
      const requiresEquilibrate = element.classList.contains(
        "ui-mode-equilibrate",
      );

      let shouldShow = true;

      // Check mode condition (if control has a mode restriction)
      if (isSimpleOnly && uiMode === "advanced") shouldShow = false;
      if (isAdvancedOnly && uiMode === "simple") shouldShow = false;

      // Check equilibrate condition (if control requires equilibrate)
      if (requiresEquilibrate && !equilibrateChecked) shouldShow = false;

      element.style.display = shouldShow ? "block" : "none";
    });
  }

  /**
   * Initialize or reinitialize all charts for the Experiment tab
   */
  initLabCharts() {
    // Charts
    // Remove any existing canvases
    document
      .querySelectorAll(".lab-chart-canvas")
      .forEach((canvas) => canvas.remove());

    // Clean up any existing full-screen handlers and hints on chart-column
    const chartColumn = DOM_ELEMENTS.charts.chartColumn;
    if (chartColumn) {
      // Remove double-click handler
      if (chartColumn._fullscreenDblClickHandler) {
        chartColumn.removeEventListener(
          "dblclick",
          chartColumn._fullscreenDblClickHandler,
        );
        delete chartColumn._fullscreenDblClickHandler;
      }
      // Remove touch handler
      if (chartColumn._fullscreenTouchHandler) {
        chartColumn.removeEventListener(
          "touchend",
          chartColumn._fullscreenTouchHandler,
        );
        delete chartColumn._fullscreenTouchHandler;
      }
      // Remove hint
      const existingHint = chartColumn.querySelector(".fullscreen-hint");
      if (existingHint) {
        existingHint.remove();
      }
      // Reset cursor
      chartColumn.style.cursor = "";
    }

    let i = 0;
    const self = this; // Preserve 'this' context for inner function
    DOM_ELEMENTS.collections.canvasParents.forEach(function (div) {
      let canvas = document.createElement("canvas");
      canvas.setAttribute("class", "lab-chart-canvas");
      canvas.setAttribute("id", labCanvasIDList[i]);
      switch (i) {
        case 0:
          if (appState.labUISettings.chartType == CHART_TYPES.STATS) {
            div.removeAttribute("hidden");
            div.appendChild(canvas);
            appState.labUISettings.ctxCity = canvas.getContext("2d");
            initCityChart(appState.labUISettings, appState.labSimSettings);
          } else {
            div.setAttribute("hidden", "");
          }
          break;
        case 1:
          if (appState.labUISettings.chartType == CHART_TYPES.STATS) {
            div.removeAttribute("hidden");
            div.appendChild(canvas);
            appState.labUISettings.ctxPhases = canvas.getContext("2d");
            initPhasesChart(appState.labUISettings, appState.labSimSettings);
          } else {
            div.setAttribute("hidden", "");
          }
          break;
        case 2:
          if (appState.labUISettings.chartType == CHART_TYPES.STATS) {
            div.removeAttribute("hidden");
            div.appendChild(canvas);
            appState.labUISettings.ctxTrip = canvas.getContext("2d");
            initTripChart(appState.labUISettings, appState.labSimSettings);
          } else {
            div.setAttribute("hidden", "");
          }
          break;
        case 3:
          if (appState.labUISettings.chartType == CHART_TYPES.STATS) {
            div.removeAttribute("hidden");
            div.appendChild(canvas);
            appState.labUISettings.ctxIncome = canvas.getContext("2d");
            initIncomeChart(appState.labUISettings, appState.labSimSettings);
          } else {
            div.setAttribute("hidden", "");
          }
          break;
        case 4:
          if (appState.labUISettings.chartType == CHART_TYPES.MAP) {
            div.removeAttribute("hidden");
            div.appendChild(canvas);
            appState.labUISettings.ctxMap = canvas.getContext("2d");
            initMap(appState.labUISettings, appState.labSimSettings);
            // Add full-screen handlers for map only
            addDoubleClickHandler(canvas, self.fullScreenManager);
            addMobileTouchHandlers(canvas, self.fullScreenManager);
          } else {
            div.setAttribute("hidden", "");
          }
          break;
        case 5:
          if (appState.labUISettings.chartType == CHART_TYPES.MAP) {
            appState.labSimSettings.resetToStart();
            div.removeAttribute("hidden");
          } else {
            div.setAttribute("hidden", "");
          }
          break;
      }
      i += 1;
    });

    // For stats mode, add full-screen handler to the chart-column container
    if (appState.labUISettings.chartType == CHART_TYPES.STATS) {
      const chartColumn = DOM_ELEMENTS.charts.chartColumn;
      if (chartColumn) {
        addDoubleClickHandler(chartColumn, self.fullScreenManager);
        addMobileTouchHandlers(chartColumn, self.fullScreenManager);
      }
    }
  }

  /**
   * Set the simulation back to block zero, and update the UI controls
   * and charts to reflect this. Do not change any of the simulation
   * settings (parameters).
   */
  resetUIAndSimulation() {
    appState.labSimSettings.resetToStart();
    w.postMessage(appState.labSimSettings);
    resetVehicleCountTracking();
    this.setLabTopControls(true);
    this.initLabCharts();
  }

  /**
   * Toggle the Lab FAB button between Play and Pause states
   * @param {HTMLElement} button - The FAB button element
   */
  toggleLabFabButton(button) {
    const icon = button.querySelector(".material-icons");
    const text = button.querySelector(".app-button__text");

    if (icon.innerHTML == SimulationActions.Play) {
      // The button shows the Play arrow. Toggle it to show Pause
      icon.innerHTML = SimulationActions.Pause;
      //if (text) text.textContent = 'Pause';
      // While the simulation is playing, also disable Next Step
      DOM_ELEMENTS.controls.nextStepButton.setAttribute("disabled", "");
      DOM_ELEMENTS.collections.resetControls.forEach(function (element) {
        element.setAttribute("disabled", "");
      });
    } else {
      // The button shows Pause. Toggle it to show the Play arrow.
      icon.innerHTML = SimulationActions.Play;
      // if (text) text.textContent = 'Run';
      // While the simulation is Paused, also enable Reset and Next Step
      DOM_ELEMENTS.controls.nextStepButton.removeAttribute("disabled");
      DOM_ELEMENTS.controls.resetButton.removeAttribute("disabled");
      DOM_ELEMENTS.collections.resetControls.forEach(function (element) {
        element.removeAttribute("disabled");
      });
    }
  }

  /**
   * Handle click on the Lab FAB button
   */
  clickFabButton() {
    const simSettings = appState.labSimSettings;

    // Record current UI controls state in simSettings
    simSettings.chartType = document.querySelector(
      'input[type="radio"][name="chart-type"]:checked',
    ).value;
    simSettings.citySize = parseInt(DOM_ELEMENTS.inputs.citySize.value);
    simSettings.vehicleCount = parseInt(DOM_ELEMENTS.inputs.vehicleCount.value);
    simSettings.requestRate = parseFloat(DOM_ELEMENTS.inputs.requestRate.value);

    // Read the button icon to see what the current state is.
    // If it is showing "play arrow", then the simulation is currently paused,
    // so the action to take is to play.
    // If it is showing "pause", then the simulation is currently running,
    // so the action to take is to pause.
    const icon =
      DOM_ELEMENTS.controls.fabButton.querySelector(".material-icons");
    if (icon.innerHTML == SimulationActions.Play) {
      // If the button is showing "Play", then the action to take is play
      simSettings.action = SimulationActions.Play;
      this.toggleLabFabButton(DOM_ELEMENTS.controls.fabButton);
    } else {
      // The button should be showing "Pause", and the action to take is to pause
      simSettings.action = SimulationActions.Pause;
      this.toggleLabFabButton(DOM_ELEMENTS.controls.fabButton);
    }
    w.postMessage(simSettings);
  }

  /**
   * Update the chart type (map vs stats)
   * @param {string} value - The chart type value
   */
  updateChartType(value) {
    // "value" comes in as a string from the UI world
    if (value == CHART_TYPES.STATS) {
      appState.labUISettings.chartType = CHART_TYPES.STATS;
      appState.labSimSettings.chartType = CHART_TYPES.STATS;
      this.saveSessionSettings();
    } else if (value == CHART_TYPES.MAP) {
      appState.labUISettings.chartType = CHART_TYPES.MAP;
      appState.labSimSettings.chartType = CHART_TYPES.MAP;
      this.saveSessionSettings();
    } else if (value == CHART_TYPES.WHAT_IF) {
      appState.labUISettings.chartType = CHART_TYPES.WHAT_IF;
      appState.labSimSettings.chartType = CHART_TYPES.WHAT_IF;
      this.saveSessionSettings();
    }
    if (appState.labUISettings.chartType == CHART_TYPES.STATS) {
      DOM_ELEMENTS.inputs.animationDelay.value = 0;
      appState.labSimSettings.animationDelay = 0;
    } else if (appState.labUISettings.chartType == CHART_TYPES.MAP) {
      DOM_ELEMENTS.inputs.animationDelay.value = 400;
      appState.labSimSettings.animationDelay = 400;
    }
    DOM_ELEMENTS.options.animationDelay.innerHTML =
      DOM_ELEMENTS.inputs.animationDelay.value;
    let chartType = appState.labUISettings.chartType;
    DOM_ELEMENTS.collections.statsDescriptions.forEach(function (element) {
      if (chartType == CHART_TYPES.STATS) {
        element.style.display = "block";
      } else {
        element.style.display = "none";
      }
    });
    this.initLabCharts();
  }

  /**
   * Update the UI mode (simple vs advanced)
   * @param {string} value - The mode value
   */
  updateMode(value) {
    this.updateLabSimSettings("uiMode", value);
    this.resetUIAndSimulation();
    const scale = appState.labSimSettings.scale;
    const scaleConfig = SCALE_CONFIGS[scale];
    this.setLabConfigControls(scaleConfig);
  }

  /**
   * Update a lab simulation setting
   * @param {string} property - The property name
   * @param {*} value - The new value
   */
  updateLabSimSettings(property, value) {
    appState.labSimSettings[property] = value;
    // Auto-save to session storage whenever settings change
    saveLabSettings(appState.labSimSettings);
  }

  /**
   * Save session settings (both lab settings and UI state)
   */
  saveSessionSettings() {
    // Save both lab settings and UI state
    saveLabSettings(appState.labSimSettings);
    saveUIState({
      scale: appState.labSimSettings.scale,
      mode: appState.labSimSettings.useCostsAndIncomes ? "advanced" : "simple",
      chartType: appState.labUISettings.chartType,
    });
  }

  /**
   * Update block counter display and handle simulation completion
   * @param {Map} results - Results from Python simulation
   */
  updateBlockCounter(results) {
    const frameIndex = results.get("frame");
    const blockIndex = results.get("block");
    const timeBlocks = results.get("time_blocks");

    // Show "N/Ntotal" format when time_blocks > 0, otherwise just "N"
    if (timeBlocks > 0) {
      DOM_ELEMENTS.displays.blockCount.innerHTML = `${blockIndex}/${timeBlocks}`;
    } else {
      DOM_ELEMENTS.displays.blockCount.innerHTML = blockIndex;
    }

    appState.labSimSettings.frameIndex = frameIndex;
    if (
      blockIndex >= appState.labSimSettings.timeBlocks &&
      appState.labSimSettings.timeBlocks !== 0
    ) {
      appState.labSimSettings.action = SimulationActions.Done;
      w.postMessage(appState.labSimSettings);
      this.toggleLabFabButton(DOM_ELEMENTS.controls.fabButton);
    }
  }
}
