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
import { initMap, fitMapToViewport } from "./modules/map.js";
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
import { updateSimTitleDisplay } from "./js/sim-title.js";
import { markConfigDirty } from "./js/saved-configs.js";
import { updateSliderFill, updateSliderLimitFill, LOG_SLIDER_STEPS, getLogSliderValue, valueToLogSlider } from "./js/input-handlers.js";

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
    // Names of structural ("reset-on-change") parameters whose slider value has
    // been changed while a run was in progress and is therefore staged, waiting
    // to be applied by the next Reset. Drives the pending markers (see
    // markParamPending / clearPendingChanges).
    this.pendingParams = new Set();
  }

  /**
   * Initialize the Experiment tab with default values
   * @param {boolean} isReady - Whether Pyodide is ready
   */
  setInitialValues(isReady = false) {
    const scale = appState.labSimSettings.scale;
    // This rebuilds labSimSettings from scratch below, which would otherwise
    // silently discard a title restored from a previous session (or typed in
    // just before a scale change) - title is a scenario label, independent
    // of scale, so it should survive the rebuild.
    const previousTitle = appState.labSimSettings.title;
    const scaleConfig = SCALE_CONFIGS[scale];
    appState.labSimSettings = new SimSettings(scaleConfig, "labSimSettings");
    appState.labSimSettings.title = previousTitle || "";
    // Post a Reset (not the SimSettings default action of null, which the
    // worker's onmessage ignores): this re-initializes the worker's sim to the
    // new settings immediately. Previously a null action left any in-flight run
    // untouched, so loading a preset mid-run corrupted the display by drawing
    // the old simulation onto freshly re-created charts.
    appState.labSimSettings.action = SimulationActions.Reset;
    w.postMessage(appState.labSimSettings);
    // reset complete: back to a stopped run at block 0, and any staged
    // structural changes have been committed by this fresh initialization.
    this.clearPendingChanges();
    resetVehicleCountTracking();
    this.setLabTopControls(isReady);
    this.setLabConfigControls(scaleConfig);
    this.initLabCharts();
  }

  /**
   * Set the state of the top controls (reset, fab, next step buttons)
   * @param {boolean} isReady - Whether Pyodide is ready
   */
  setLabTopControls(isReady = false) {
    // Reaching here means the simulation is back to a fresh, stopped state
    // (initial load, Reset, or a finished timed run). Record that as the
    // single source of truth and re-enable the scenario-level control bar.
    this.setRunState("stopped");
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
    // Presets are momentary "load" buttons with no persistent selected state,
    // so there is nothing to restore here for the preset control.
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
   * Initialize the slider inputs and checkboxes from a config object.
   *
   * Slider ranges (min/max/step) are fixed and identical for every preset; the
   * config only supplies the starting value for each control. Loading a preset,
   * a saved config, or an uploaded file all flow through here.
   * @param {Object} scaleConfig - Config object ({ value, min, max, step } per control)
   */
  setLabConfigControls(scaleConfig) {
    // --- initialize slider inputs and options with min/max/step/value ---
    const sliderControls = [
      "citySize",
      "vehicleCount",
      "requestRate",
      "meanTripDistance",
      "inhomogeneity",
      "idleVehiclesMoving",
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

      if (inputElement.hasAttribute('data-log-min')) {
        const logMin = parseFloat(inputElement.dataset.logMin);
        const logMax = parseFloat(inputElement.dataset.logMax);
        Object.assign(inputElement, {
          min: 0, max: LOG_SLIDER_STEPS, step: 1,
          value: valueToLogSlider(config.value, logMin, logMax),
        });
      } else {
        Object.assign(inputElement, {
          min: config.min,
          max: config.max,
          step: config.step,
          value: config.value,
        });
      }
      optionElement.innerHTML = appState.labSimSettings[controlName];
      updateSliderFill(inputElement);
    });
    // Refresh the header title display to match the current settings
    // (covers initial load, scale change, mode change, and config upload)
    updateSimTitleDisplay(appState.labSimSettings.title);

    // Set equilibrate checkbox from labSimSettings (not scaleConfig which doesn't have it)
    DOM_ELEMENTS.checkboxes.equilibrate.checked = appState.labSimSettings.equilibrate || false;

    // Sync the equilibration string to match the checkbox state
    // This ensures consistency after initialization or reset
    appState.labSimSettings.equilibration = appState.labSimSettings.equilibrate ? "price" : "none";

    // Update visibility based on all conditions (mode + equilibrate)
    this.updateControlVisibility();

    // Sync the meanTripDistance forbidden zone to the current city size
    this.syncMeanTripDistanceLimit();
  }

  /**
   * Resolve the effective upper bound for a slider from the Python-provided
   * constraint metadata (worker.py::get_slider_config). A constraint of
   * { maxRelativeTo: "citySize", maxFraction: 0.5 } means "no greater than
   * floor(citySize * 0.5)". Returns NaN when no constraint is known (metadata
   * not yet loaded, or the parameter is unconstrained), which callers treat as
   * "no dynamic bound".
   * @param {string} jsName - camelCase parameter name
   * @returns {number} the resolved max, or NaN if unconstrained
   */
  resolveMaxConstraint(jsName) {
    const constraint = appState.sliderConstraints[jsName];
    if (!constraint || constraint.maxRelativeTo == null) return NaN;
    const baseValue = appState.labSimSettings[constraint.maxRelativeTo];
    if (baseValue == null) return NaN;
    return Math.floor(baseValue * constraint.maxFraction);
  }

  /**
   * Store slider constraint metadata from Python and re-render anything that
   * depends on it. Called once when the "Pyodide loaded" message arrives.
   * @param {Object} constraints - keyed by camelCase param name
   */
  initSliderConstraints(constraints) {
    appState.sliderConstraints = constraints || {};
    // The mean-trip-distance forbidden zone depends on the constraint, so
    // (re)draw it now that the real bound is known.
    this.syncMeanTripDistanceLimit();
  }

  syncMeanTripDistanceLimit() {
    const maxMtd = this.resolveMaxConstraint("meanTripDistance");
    const mtdInput = DOM_ELEMENTS.inputs.meanTripDistance;
    const overlay = document.getElementById("mean-trip-limit-overlay");

    // Until the Python constraint metadata has loaded there is no bound to
    // draw or enforce; leave the slider unrestricted and hide the band.
    if (isNaN(maxMtd)) {
      updateSliderLimitFill(mtdInput, 100);
      if (overlay) overlay.hidden = true;
      return;
    }

    const logMin = parseFloat(mtdInput.dataset.logMin);
    const logMax = parseFloat(mtdInput.dataset.logMax);

    // Update forbidden-zone colour band on the track
    const limitPos = valueToLogSlider(maxMtd, logMin, logMax);
    const limitPct = (limitPos / LOG_SLIDER_STEPS) * 100;
    updateSliderLimitFill(mtdInput, limitPct);

    // Position the hover-tooltip overlay over the forbidden zone
    if (overlay) {
      if (limitPct < 100) {
        overlay.style.left = `${limitPct}%`;
        overlay.hidden = false;
      } else {
        overlay.hidden = true;
      }
    }

    // Clamp value if it now exceeds the limit
    if (appState.labSimSettings.meanTripDistance > maxMtd) {
      appState.labSimSettings.meanTripDistance = maxMtd;
      mtdInput.value = limitPos;
      DOM_ELEMENTS.options.meanTripDistance.innerHTML = maxMtd;
      updateSliderFill(mtdInput);
    }
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

    // Auto-open "More settings" when equilibrate is turned on, so the
    // toggle has a visible effect (Economics group lives inside it).
    if (equilibrateChecked) {
      const moreSettings = document.getElementById("more-settings");
      if (moreSettings && !moreSettings.open) {
        moreSettings.open = true;
      }
    }
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
            // Size the map square to the available viewport space.
            requestAnimationFrame(() => fitMapToViewport());
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
    // The staged structural values (already stored in labSimSettings) have now
    // been committed by the reset, so clear the pending markers.
    this.clearPendingChanges();
    resetVehicleCountTracking();
    this.setLabTopControls(true);
    this.initLabCharts();
  }

  /**
   * Update the single run-state source of truth and reflect it in the
   * scenario-level control bar. Scenario changes (mode, presets, saved-config
   * load, config upload) are only meaningful against a sim that is not running,
   * so they are disabled while "running" and enabled when "paused" or
   * "stopped".
   * @param {"stopped"|"running"|"paused"} state
   */
  setRunState(state) {
    appState.simState = state;
    this.setControlBarEnabled(state !== "running");
  }

  /**
   * Enable or disable the scenario-level control-bar actions. Deliberately
   * leaves chart-type (a view-only toggle) and config download (a read-only
   * export) alone - both remain usable during a run.
   * @param {boolean} enabled
   */
  setControlBarEnabled(enabled) {
    const setDisabled = (element) => {
      if (!element) return;
      if (enabled) element.removeAttribute("disabled");
      else element.setAttribute("disabled", "");
    };
    DOM_ELEMENTS.collections.presetButtons.forEach(setDisabled);
    DOM_ELEMENTS.collections.uiModeRadios.forEach(setDisabled);
    setDisabled(DOM_ELEMENTS.configControls.uploadInput);
    setDisabled(DOM_ELEMENTS.savedConfigs.select);
    // A class on the top-controls container lets CSS grey the label-based
    // controls (the upload label and radio chips) whose underlying input can be
    // disabled but which the browser does not visually dim on its own.
    DOM_ELEMENTS.layout.topControls?.classList.toggle("is-run-locked", !enabled);
  }

  /**
   * Stage a structural parameter change made during a run. The value itself is
   * already stored in labSimSettings (by the input handler's updateSettings
   * call); here we only surface that a Reset is needed to apply it.
   * @param {string} settingName - camelCase parameter name
   */
  markParamPending(settingName) {
    this.pendingParams.add(settingName);
    const input = DOM_ELEMENTS.inputs[settingName];
    const card = input?.closest(".app-settings-card");
    if (card) card.classList.add("is-pending");
    this.updateResetPendingIndicator();
  }

  /**
   * Clear all staged structural changes and their markers. Called by any path
   * that re-initializes the simulation (Reset, preset/config load).
   */
  clearPendingChanges() {
    this.pendingParams.clear();
    document
      .querySelectorAll(".app-settings-card.is-pending")
      .forEach((card) => card.classList.remove("is-pending"));
    this.updateResetPendingIndicator();
  }

  /**
   * Highlight the Reset button while structural changes are staged, so the user
   * knows a Reset is required to apply them.
   */
  updateResetPendingIndicator() {
    const hasPending = this.pendingParams.size > 0;
    DOM_ELEMENTS.controls.resetButton?.classList.toggle(
      "has-pending",
      hasPending,
    );
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
      // While the simulation is playing, also disable Next Step. (Structural
      // settings sliders are NOT disabled any more: under Model B they stay
      // editable and stage their value until Reset.)
      DOM_ELEMENTS.controls.nextStepButton.setAttribute("disabled", "");
    } else {
      // The button shows Pause. Toggle it to show the Play arrow.
      icon.innerHTML = SimulationActions.Play;
      // if (text) text.textContent = 'Run';
      // While the simulation is Paused, also enable Reset and Next Step
      DOM_ELEMENTS.controls.nextStepButton.removeAttribute("disabled");
      DOM_ELEMENTS.controls.resetButton.removeAttribute("disabled");
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
    simSettings.citySize = getLogSliderValue(DOM_ELEMENTS.inputs.citySize);
    simSettings.vehicleCount = getLogSliderValue(DOM_ELEMENTS.inputs.vehicleCount);
    simSettings.requestRate = getLogSliderValue(DOM_ELEMENTS.inputs.requestRate);

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
      // The simulation is now live: lock the scenario-level control bar.
      this.setRunState("running");
    } else {
      // The button should be showing "Pause", and the action to take is to pause
      simSettings.action = SimulationActions.Pause;
      this.toggleLabFabButton(DOM_ELEMENTS.controls.fabButton);
      // Paused: the control bar becomes available again (scenario changes are
      // allowed while paused, and take effect with a reset).
      this.setRunState("paused");
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
    updateSliderFill(DOM_ELEMENTS.inputs.animationDelay);
    let chartType = appState.labUISettings.chartType;
    DOM_ELEMENTS.collections.statsDescriptions.forEach(function (element) {
      if (chartType == CHART_TYPES.STATS) {
        element.style.display = "block";
      } else {
        element.style.display = "none";
      }
    });
    this.initLabCharts();

    // If a simulation is currently running, switch which kind of frame the
    // worker produces (map vs stats) live, without re-initializing the sim.
    // The freshly created charts would otherwise stay empty: the frame loop
    // keys off currentSimSettings.chartType (see getNextFrame in webworker.js),
    // which only changes when a Play-type message arrives - so it keeps
    // producing the old chart type's frames until the next pause/resume.
    // UpdateDisplay re-claims the loop (dropping the in-flight old-type frame)
    // and restarts it as Play with the new chartType and animationDelay.
    //
    // Only meaningful while running: when paused there is no live loop to
    // redirect (and UpdateDisplay would resume the sim), and a paused run picks
    // up the new chart type on its own resume; when stopped there is no loop.
    if (appState.simState === "running") {
      appState.labSimSettings.action = SimulationActions.UpdateDisplay;
      w.postMessage(appState.labSimSettings);
    }
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
    // Flag divergence from whichever saved configuration is active, if any
    markConfigDirty();
  }

  /**
   * Save session settings (both lab settings and UI state)
   */
  /**
   * Populate slider help popovers with descriptions fetched from config.py via Pyodide.
   * Called once when the "Pyodide loaded" message arrives.
   * @param {Object} helpMap - keyed by camelCase param name, value is array of sentences
   */
  initSliderHelp(helpMap) {
    document
      .querySelectorAll(".app-settings-card__info[data-help-key]")
      .forEach((details) => {
        const sentences = helpMap[details.dataset.helpKey];
        if (!sentences?.length) return;
        const panel = details.querySelector(".app-info-popover__panel");
        if (panel) {
          // Join with spaces: config.py descriptions are sometimes split across
          // tuple elements as continuation fragments for CLI line-wrapping.
          panel.innerHTML = `<p>${sentences.map((s) => s.trim()).join(" ")}</p>`;
        }
      });
  }

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
      // A finished timed run is back to a stopped state: re-enable the
      // scenario-level control bar.
      this.setRunState("stopped");
    }
  }
}
