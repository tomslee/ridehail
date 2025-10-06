/*
 * Imports and exports from and to modules
 * Updated: 2024-12 - Full-screen loading overlay implementation
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
import { colors } from "./js/constants.js";
import { VERSION, LAST_MODIFIED } from "./js/version.js";
import {
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
  initializeMD3Sliders,
} from "./js/input-handlers.js";
import { MessageHandler } from "./js/message-handler.js";
import { appState } from "./js/app-state.js";
import { parseINI, generateINI } from "./js/config-file.js";
import { webToDesktopConfig, desktopToWebConfig, validateDesktopConfig } from "./js/config-mapping.js";
import { inferAndClampSettings, getConfigSummary } from "./js/scale-inference.js";
import { showSuccess, showError, showWarning } from "./js/toast.js";
import { rotateTips } from "./js/loading-tips.js";
import { KeyboardHandler } from "./js/keyboard-handler.js";
import {
  saveLabSettings,
  saveUIState,
  loadLabSettings,
  loadUIState,
  hasSavedSession,
  getLastSavedDate
} from "./js/session-storage.js";

// Initialize the unified app state
appState.initialize();

// Start loading overlay with rotating tips
const loadingOverlay = document.getElementById('loading-overlay');
const loadingTip = document.getElementById('loading-tip');
let tipRotationInterval = null;

if (loadingTip) {
  tipRotationInterval = rotateTips(loadingTip, 2500);
}

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

class App {
  constructor() {
    this.init();
  }

  async init() {
    // Set application title with version
    this.setTitle();

    // Move initialization code here gradually
    this.setupButtonHandlers();
    this.setupForEachHandlers();
    setupInputHandlers({
      updateSettings: this.updateLabSimSettings,
      resetSimulation: () => this.resetLabUIAndSimulation(),
      updateSimulation: this.updateSimulationOptions,
      saveSettings: () => this.saveSessionSettings(),
    });
    initializeMD3Sliders();

    // Try to restore previous session
    this.restoreSession();

    this.setInitialValues(false);

    // Initialize keyboard handler with shared mappings
    this.keyboardHandler = new KeyboardHandler(this);
    await this.keyboardHandler.loadMappings();
  }

  /**
   * Set the application title with version and last modified date
   */
  setTitle() {
    const titleElement = document.getElementById('app-title');
    if (titleElement) {
      titleElement.textContent = `Ridehail Laboratory v${VERSION} (${LAST_MODIFIED})`;
    }
  }

  /*
   * Resets the charts to initial state, and the control buttons
   * (reset, fab, nextstep)
   */
  setInitialValues(isReady = false) {
    const scale = appState.labSimSettings.scale;
    const scaleConfig = SCALE_CONFIGS[scale];
    appState.labSimSettings = new SimSettings(scaleConfig, "labSimSettings");
    w.postMessage(appState.labSimSettings);
    // reset complete
    appState.labUISettings.displayRoadWidth = scaleConfig.displayRoadWidth;
    appState.labUISettings.displayVehicleRadius =
      scaleConfig.displayVehicleRadius;
    this.setLabTopControls(isReady);
    this.setLabConfigControls(scaleConfig);
    this.initLabCharts();
  }

  setupButtonHandlers() {
    DOM_ELEMENTS.controls.resetButton.onclick = () =>
      this.resetLabUIAndSimulation();

    DOM_ELEMENTS.whatIf.resetButton.onclick = () =>
      this.resetWhatIfUIAndSimulation();

    DOM_ELEMENTS.configControls.downloadButton.onclick = () =>
      this.downloadConfiguration();

    DOM_ELEMENTS.configControls.uploadInput.onchange = (e) =>
      this.handleConfigUpload(e);

    // Drag and drop handlers for drop zone
    this.setupDropZone();

    DOM_ELEMENTS.configControls.confirmButton.onclick = () =>
      this.applyUploadedConfig();

    DOM_ELEMENTS.configControls.cancelButton.onclick = () =>
      this.hideConfigDialog();

    DOM_ELEMENTS.configControls.confirmDialog.querySelector('.app-dialog__overlay').onclick = () =>
      this.hideConfigDialog();

    if (DOM_ELEMENTS.keyboardHelp.closeButton) {
      DOM_ELEMENTS.keyboardHelp.closeButton.onclick = () =>
        this.hideKeyboardHelpDialog();
    }

    if (DOM_ELEMENTS.keyboardHelp.dialog) {
      DOM_ELEMENTS.keyboardHelp.dialog.querySelector('.app-dialog__overlay').onclick = () =>
        this.hideKeyboardHelpDialog();
    }

    DOM_ELEMENTS.controls.fabButton.onclick = () => {
      this.clickFabButton(
        DOM_ELEMENTS.controls.fabButton,
        appState.labSimSettings
      );
    };

    DOM_ELEMENTS.whatIf.baselineFabButton.onclick = () =>
      this.clickFabButton(
        DOM_ELEMENTS.whatIf.baselineFabButton,
        appState.whatIfSimSettingsBaseline
      );

    DOM_ELEMENTS.whatIf.comparisonFabButton.onclick = () =>
      this.clickFabButton(
        DOM_ELEMENTS.whatIf.comparisonFabButton,
        appState.whatIfSimSettingsComparison
      );

    DOM_ELEMENTS.controls.nextStepButton.onclick = () => {
      appState.labSimSettings.action = SimulationActions.SingleStep;
      w.postMessage(appState.labSimSettings);
    };
  }

  setupForEachHandlers() {
    const app = this;
    DOM_ELEMENTS.collections.tabList.forEach(function (element) {
      // destroy any existing charts
      element.onclick = (event) => {
        event.preventDefault(); // Prevent default anchor behavior

        // Update tab active states and ARIA attributes
        DOM_ELEMENTS.collections.tabList.forEach((tab) => {
          tab.classList.remove("is-active");
          tab.setAttribute("aria-selected", "false");
        });

        element.classList.add("is-active");
        element.setAttribute("aria-selected", "true");

        // Update tab panels
        document.querySelectorAll(".app-tab-panel").forEach((panel) => {
          panel.classList.remove("is-active");
        });

        const targetPanel = document.querySelector(
          element.getAttribute("href")
        );
        if (targetPanel) {
          targetPanel.classList.add("is-active");
        }

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
        appState.labSimSettings.scale = radio.value;
        this.setInitialValues(true);
        // Save scale change to session
        this.saveSessionSettings();
      })
    );

    // Keyboard handling is now managed by KeyboardHandler class
    // initialized in init() method

    DOM_ELEMENTS.whatIf.setComparisonButtons.forEach((element) => {
      element.addEventListener("click", (event) => {
        switch (event.currentTarget.id) {
          case "what-if-price-remove":
            if (appState.whatIfSimSettingsComparison.useCostsAndIncomes) {
              appState.whatIfSimSettingsComparison.perMinutePrice -= 0.1;
              // the price is ignored, but set it right for appearance's sake
              appState.whatIfSimSettingsComparison.price =
                appState.whatIfSimSettingsComparison.perMinutePrice +
                (appState.whatIfSimSettingsComparison.perKmPrice *
                  appState.whatIfSimSettingsComparison.meanVehicleSpeed) /
                  60.0;
            } else {
              appState.whatIfSimSettingsComparison.price -= 0.1;
            }
            appState.whatIfSimSettingsComparison.price =
              Math.round(appState.whatIfSimSettingsComparison.price * 10) / 10;
            break;
          case "what-if-price-add":
            if (appState.whatIfSimSettingsComparison.useCostsAndIncomes) {
              appState.whatIfSimSettingsComparison.perMinutePrice += 0.1;
              // the price is ignored, but set it right for appearance's sake
              appState.whatIfSimSettingsComparison.price =
                appState.whatIfSimSettingsComparison.perMinutePrice +
                (appState.whatIfSimSettingsComparison.perKmPrice *
                  appState.whatIfSimSettingsComparison.meanVehicleSpeed) /
                  60.0;
            } else {
              appState.whatIfSimSettingsComparison.price += 0.1;
            }
            appState.whatIfSimSettingsComparison.price =
              Math.round(appState.whatIfSimSettingsComparison.price * 10) / 10;
            break;
          case "what-if-commission-remove":
            appState.whatIfSimSettingsComparison.platformCommission -= 0.05;
            appState.whatIfSimSettingsComparison.platformCommission =
              Math.round(
                appState.whatIfSimSettingsComparison.platformCommission * 20
              ) / 20;
            break;
          case "what-if-commission-add":
            appState.whatIfSimSettingsComparison.platformCommission += 0.05;
            appState.whatIfSimSettingsComparison.platformCommission =
              Math.round(
                appState.whatIfSimSettingsComparison.platformCommission * 20
              ) / 20;
            break;
          case "what-if-reservation-wage-remove":
            if (appState.whatIfSimSettingsComparison.useCostsAndIncomes) {
              appState.whatIfSimSettingsComparison.perHourOpportunityCost -=
                60.0 * 0.01;
              appState.whatIfSimSettingsComparison.reservationWage =
                (appState.whatIfSimSettingsComparison.perHourOpportunityCost +
                  appState.whatIfSimSettingsComparison.perKmOpsCost *
                    appState.whatIfSimSettingsComparison.meanVehicleSpeed) /
                60.0;
            } else {
              appState.whatIfSimSettingsComparison.reservationWage -= 0.01;
            }
            appState.whatIfSimSettingsComparison.reservationWage =
              Math.round(
                appState.whatIfSimSettingsComparison.reservationWage * 100
              ) / 100;
            break;
          case "what-if-reservation-wage-add":
            if (appState.whatIfSimSettingsComparison.useCostsAndIncomes) {
              appState.whatIfSimSettingsComparison.perHourOpportunityCost +=
                60.0 * 0.01;
              appState.whatIfSimSettingsComparison.reservationWage =
                appState.whatIfSimSettingsComparison.perHourOpportunityCost /
                  60.0 +
                (appState.whatIfSimSettingsComparison.perKmOpsCost *
                  appState.whatIfSimSettingsComparison.meanVehicleSpeed) /
                  60.0;
            } else {
              appState.whatIfSimSettingsComparison.reservationWage =
                appState.whatIfSimSettingsComparison.reservationWage + 0.01;
            }
            appState.whatIfSimSettingsComparison.reservationWage =
              Math.round(
                appState.whatIfSimSettingsComparison.reservationWage * 100
              ) / 100;
            break;
          case "what-if-demand-remove":
            appState.whatIfSimSettingsComparison.requestRate -= 0.5;
            appState.whatIfSimSettingsComparison.requestRate =
              Math.round(
                appState.whatIfSimSettingsComparison.requestRate * 10
              ) / 10;
            break;
          case "what-if-demand-add":
            appState.whatIfSimSettingsComparison.requestRate += 0.5;
            appState.whatIfSimSettingsComparison.requestRate =
              Math.round(
                appState.whatIfSimSettingsComparison.requestRate * 10
              ) / 10;
            break;
        }
        this.updateWhatIfTopControlValues();
      });
    });

    DOM_ELEMENTS.whatIf.baselineRadios.forEach((radio) =>
      radio.addEventListener("change", () => {
        if (radio.value == "preset") {
          appState.whatIfSimSettingsBaseline = new WhatIfSimSettingsDefault();
          appState.whatIfSimSettingsBaseline.name = "whatIfSimSettingsBaseline";
          appState.whatIfSimSettingsComparison = new WhatIfSimSettingsDefault();
          appState.whatIfSimSettingsComparison.name =
            "whatIfSimSettingsComparison";
        } else if (radio.value == "lab") {
          appState.whatIfSimSettingsBaseline = Object.assign(
            {},
            appState.labSimSettings
          );
          appState.whatIfSimSettingsBaseline.chartType = CHART_TYPES.WHAT_IF;
          appState.whatIfSimSettingsBaseline.name = "whatIfSimSettingsBaseline";
          appState.whatIfSimSettingsBaseline.timeBlocks = 200;
          appState.whatIfSimSettingsBaseline.frameIndex = 0;
          appState.whatIfSimSettingsBaseline.animationDelay = 0;
          /*
      appState.whatIfSimSettingsBaseline.perMinutePrice = parseFloat(
        appState.whatIfSimSettingsBaseline.perMinutePrice
      );
      appState.whatIfSimSettingsBaseline.perKmPrice = parseFloat(
        appState.whatIfSimSettingsBaseline.perKmPrice
      );
      appState.whatIfSimSettingsBaseline.meanVehicleSpeed = parseFloat(
        appState.whatIfSimSettingsBaseline.meanVehicleSpeed
      );
      */
          // fix the price, even though it isn't used, as it appears in the buttons
          if (appState.whatIfSimSettingsBaseline.useCostsAndIncomes) {
            appState.whatIfSimSettingsBaseline.price =
              appState.whatIfSimSettingsBaseline.perMinutePrice +
              (appState.whatIfSimSettingsBaseline.perKmPrice *
                appState.whatIfSimSettingsBaseline.meanVehicleSpeed) /
                60.0;
            appState.whatIfSimSettingsBaseline.reservationWage =
              (appState.whatIfSimSettingsBaseline.perHourOpportunityCost +
                appState.whatIfSimSettingsBaseline.perKmOpsCost *
                  appState.whatIfSimSettingsBaseline.meanVehicleSpeed) /
              60.0;
          }
          appState.whatIfSimSettingsComparison = Object.assign(
            {},
            appState.whatIfSimSettingsBaseline
          );
          appState.whatIfSimSettingsComparison.name =
            "whatIfSimSettingsComparison";
        }
        this.updateWhatIfTopControlValues();
      })
    );
  }

  setLabTopControls(isReady = false) {
    // --- Set the state of the "top controls" in the bar above the text
    // Some settings are based on current labSimSettings
    if (isReady) {
      const icon = DOM_ELEMENTS.controls.fabButton.querySelector('.material-icons');
      const text = DOM_ELEMENTS.controls.fabButton.querySelector('.app-button__text');
      icon.innerHTML = SimulationActions.Play;
      if (text) text.textContent = 'Run';
      const buttonArray = ["resetButton", "fabButton", "nextStepButton"];
      buttonArray.forEach(function (value, index) {
        DOM_ELEMENTS.controls[value].removeAttribute("disabled");
      });
      DOM_ELEMENTS.displays.frameCount.innerHTML = 0;
    }
    // Set Scale radio buttons from current scale
    const scaleId = "radio-community-" + appState.labSimSettings.scale;
    const scaleEl = document.getElementById(scaleId).parentElement;
    scaleEl.style.backgroundColor = "#f0f3f3";
    scaleEl.checked = true;
    // scaleEl.click();
    // Set chart type radio buttons from current labSimSettings
    const chartTypeId = "radio-chart-type-" + appState.labSimSettings.chartType;
    const chartTypeEl = document.getElementById(chartTypeId).parentElement;
    chartTypeEl.checked = true;
    // Set simple / advanced mode radio buttons from current labSimSettings
    if (appState.labSimSettings.useCostsAndIncomes) {
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
      "animationDelay",
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
      optionElement.innerHTML = appState.labSimSettings[controlName];
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
          } else {
            div.setAttribute("hidden", "");
          }
          break;
        case 5:
          if (appState.labUISettings.chartType == CHART_TYPES.MAP) {
            div.removeAttribute("hidden");
          } else {
            div.setAttribute("hidden", "");
          }
          break;
      }
      i += 1;
    });
  }

  /**
   * Set the simulation back to frame zero, and update the UI controls
   * and charts to reflect this. Do not change any of the simulation
   * settings (parameters).
   */
  resetLabUIAndSimulation() {
    appState.labSimSettings.resetToStart();
    w.postMessage(appState.labSimSettings);
    this.setLabTopControls(true);
    this.initLabCharts();
  }

  /**
   * Download current lab settings as desktop-compatible .config file
   */
  downloadConfiguration() {
    // Convert web settings to desktop config format
    const desktopConfig = webToDesktopConfig(appState.labSimSettings);

    // Generate INI string
    const iniContent = generateINI(desktopConfig);

    // Create timestamp for filename
    const now = new Date();
    const timestamp = now.toISOString()
      .replace(/:/g, '-')
      .replace(/\..+/, '')
      .replace('T', '_');
    const filename = `ridehail_lab_${timestamp}.config`;

    // Create blob and download
    const blob = new Blob([iniContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);

    // Show success toast
    showSuccess(`Configuration downloaded: ${filename}`);
    console.log(`Configuration downloaded: ${filename}`);
  }

  /**
   * Handle configuration file upload
   */
  handleConfigUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const fileContent = e.target.result;

        // Parse INI file
        const parsedINI = parseINI(fileContent);

        // Validate config
        const validation = validateDesktopConfig(parsedINI);
        if (!validation.valid) {
          showError(`Invalid configuration file: ${validation.errors[0]}`);
          return;
        }

        // Convert to web settings
        const webConfig = desktopToWebConfig(parsedINI);

        // Infer scale and clamp values
        const { scale, clampedSettings, warnings } = inferAndClampSettings(webConfig);

        // Show confirmation dialog
        this.showConfigConfirmation(clampedSettings, scale, warnings);

      } catch (error) {
        showError(`Error reading configuration file: ${error.message}`);
        console.error(error);
      }
    };

    reader.readAsText(file);

    // Reset file input so same file can be selected again
    event.target.value = '';
  }

  /**
   * Setup drag and drop handlers for the drop zone
   */
  setupDropZone() {
    const dropZone = DOM_ELEMENTS.configControls.dropZone;
    if (!dropZone) return;

    // Prevent default drag behaviors on the whole document
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
      document.body.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
      }, false);
    });

    // Highlight drop zone when item is dragged over it
    ['dragenter', 'dragover'].forEach(eventName => {
      dropZone.addEventListener(eventName, () => {
        dropZone.classList.add('drag-over');
      }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
      dropZone.addEventListener(eventName, () => {
        dropZone.classList.remove('drag-over');
      }, false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', (e) => {
      const dt = e.dataTransfer;
      const files = dt.files;

      if (files.length > 0) {
        this.handleDroppedFile(files[0]);
      }
    }, false);

    // Also make the drop zone clickable to trigger file input
    dropZone.addEventListener('click', () => {
      DOM_ELEMENTS.configControls.uploadInput.click();
    }, false);
  }

  /**
   * Handle a file dropped onto the drop zone
   */
  handleDroppedFile(file) {
    // Check if it's a .config file
    if (!file.name.endsWith('.config')) {
      showError('Please drop a .config file');
      return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
      try {
        const fileContent = e.target.result;

        // Parse INI file
        const parsedINI = parseINI(fileContent);

        // Validate config
        const validation = validateDesktopConfig(parsedINI);
        if (!validation.valid) {
          showError(`Invalid configuration file: ${validation.errors[0]}`);
          return;
        }

        // Convert to web settings
        const webConfig = desktopToWebConfig(parsedINI);

        // Infer scale and clamp values
        const { scale, clampedSettings, warnings } = inferAndClampSettings(webConfig);

        // Show confirmation dialog
        this.showConfigConfirmation(clampedSettings, scale, warnings);

      } catch (error) {
        showError(`Error reading configuration file: ${error.message}`);
        console.error(error);
      }
    };

    reader.readAsText(file);
  }

  /**
   * Show configuration confirmation dialog
   */
  showConfigConfirmation(settings, scale, warnings) {
    const dialog = DOM_ELEMENTS.configControls.confirmDialog;
    const summary = DOM_ELEMENTS.configControls.configSummary;
    const warningsDiv = DOM_ELEMENTS.configControls.configWarnings;

    // Build summary
    const configSummary = getConfigSummary(settings, scale);
    const summaryHTML = `
      <dl>
        <dt>Scale:</dt>
        <dd>${configSummary.scale}</dd>
        <dt>City Size:</dt>
        <dd>${configSummary.citySize} blocks</dd>
        <dt>Vehicle Count:</dt>
        <dd>${configSummary.vehicleCount}</dd>
        <dt>Request Rate:</dt>
        <dd>${configSummary.requestRate} per block</dd>
        <dt>Equilibrate:</dt>
        <dd>${configSummary.equilibrate ? 'Yes' : 'No'}</dd>
        <dt>Mode:</dt>
        <dd>${configSummary.useCostsAndIncomes ? 'Costs & Incomes' : 'Simple Model'}</dd>
      </dl>
    `;
    summary.innerHTML = summaryHTML;

    // Build warnings
    if (warnings.length > 0) {
      const warningsHTML = `
        <strong>Adjustments made:</strong>
        <ul style="margin: 8px 0 0 0; padding-left: 20px;">
          ${warnings.map(w => `<li>${w.message}</li>`).join('')}
        </ul>
      `;
      warningsDiv.innerHTML = warningsHTML;
    } else {
      warningsDiv.innerHTML = '';
    }

    // Store settings for confirmation
    this.pendingConfig = { settings, scale, warnings };

    // Show dialog
    dialog.removeAttribute('hidden');
  }

  /**
   * Apply uploaded configuration
   */
  applyUploadedConfig() {
    if (!this.pendingConfig) return;

    const { settings, scale } = this.pendingConfig;

    // Update scale radio
    const scaleRadio = document.querySelector(`input[name="scale"][value="${scale}"]`);
    if (scaleRadio) {
      scaleRadio.checked = true;
      appState.labSimSettings.scale = scale;
    }

    // Update all settings
    Object.assign(appState.labSimSettings, settings);

    // Update UI mode radio
    const uiMode = settings.useCostsAndIncomes ? 'advanced' : 'simple';
    const uiModeRadio = document.querySelector(`input[name="ui-mode"][value="${uiMode}"]`);
    if (uiModeRadio) {
      uiModeRadio.checked = true;
    }

    // Update equilibrate checkbox
    DOM_ELEMENTS.checkboxes.equilibrate.checked = settings.equilibrate || false;

    // Trigger scale change to update ranges
    const scaleConfig = SCALE_CONFIGS[scale];
    this.setLabConfigControls(scaleConfig);

    // Update all input values
    this.updateAllUIControls(settings);

    // Reset simulation
    this.resetLabUIAndSimulation();

    // Hide dialog
    this.hideConfigDialog();

    // Show success toast
    const { warnings } = this.pendingConfig;
    if (warnings && warnings.length > 0) {
      showWarning(`Configuration loaded with adjustments (Scale: ${scale.toUpperCase()})`, 4000);
    } else {
      showSuccess(`Configuration loaded (Scale: ${scale.toUpperCase()})`);
    }
  }

  /**
   * Update all UI controls from settings
   */
  updateAllUIControls(settings) {
    // Update all sliders and their value displays
    const inputMap = {
      citySize: 'citySize',
      vehicleCount: 'vehicleCount',
      requestRate: 'requestRate',
      maxTripDistance: 'maxTripDistance',
      inhomogeneity: 'inhomogeneity',
      price: 'price',
      platformCommission: 'platformCommission',
      reservationWage: 'reservationWage',
      demandElasticity: 'demandElasticity',
      meanVehicleSpeed: 'meanVehicleSpeed',
      perKmPrice: 'perKmPrice',
      perMinutePrice: 'perMinutePrice',
      perKmOpsCost: 'perKmOpsCost',
      perHourOpportunityCost: 'perHourOpportunityCost',
      animationDelay: 'animationDelay',
      smoothingWindow: 'smoothingWindow',
    };

    for (const [inputKey, settingsKey] of Object.entries(inputMap)) {
      if (settings[settingsKey] !== undefined && DOM_ELEMENTS.inputs[inputKey]) {
        DOM_ELEMENTS.inputs[inputKey].value = settings[settingsKey];
        if (DOM_ELEMENTS.options[inputKey]) {
          DOM_ELEMENTS.options[inputKey].textContent = settings[settingsKey];
        }
      }
    }
  }

  /**
   * Hide configuration dialog
   */
  hideConfigDialog() {
    DOM_ELEMENTS.configControls.confirmDialog.setAttribute('hidden', '');
    this.pendingConfig = null;
  }

  hideKeyboardHelpDialog() {
    DOM_ELEMENTS.keyboardHelp.dialog.setAttribute('hidden', '');
  }

  toggleLabFabButton(button) {
    const icon = button.querySelector('.material-icons');
    const text = button.querySelector('.app-button__text');

    if (icon.innerHTML == SimulationActions.Play) {
      // The button shows the Play arrow. Toggle it to show Pause
      icon.innerHTML = SimulationActions.Pause;
      if (text) text.textContent = 'Pause';
      // While the simulation is playing, also disable Next Step
      DOM_ELEMENTS.controls.nextStepButton.setAttribute("disabled", "");
      DOM_ELEMENTS.collections.resetControls.forEach(function (element) {
        element.setAttribute("disabled", "");
      });
    } else {
      // The button shows Pause. Toggle it to show the Play arrow.
      icon.innerHTML = SimulationActions.Play;
      if (text) text.textContent = 'Run';
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
    // Read the button icon to see what the current state is.
    // If it is showing "play arrow", then the simulation is currently paused, so the action to take is to play.
    // If it is showing "pause", then the simulation is currently running, so the action to take is to pause.
    const icon = button.querySelector('.material-icons') || button.firstElementChild;
    if (icon.innerHTML == SimulationActions.Play) {
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

  updateMode(value) {
    this.updateLabSimSettings("uiMode", value);
    this.resetLabUIAndSimulation();
    const scale = appState.labSimSettings.scale;
    const scaleConfig = SCALE_CONFIGS[scale];
    this.setLabConfigControls(scaleConfig);
  }

  updateSimulationOptions(updateType) {
    appState.labSimSettings.action = updateType;
    w.postMessage(appState.labSimSettings);
  }

  updateLabSimSettings(property, value) {
    appState.labSimSettings[property] = value;
    // Auto-save to session storage whenever settings change
    saveLabSettings(appState.labSimSettings);
  }

  saveSessionSettings() {
    // Save both lab settings and UI state
    saveLabSettings(appState.labSimSettings);
    saveUIState({
      scale: appState.labSimSettings.scale,
      mode: appState.labSimSettings.useCostsAndIncomes ? 'advanced' : 'simple',
      chartType: appState.labUISettings.chartType,
    });
  }

  restoreSession() {
    // Check if we have saved session data
    if (!hasSavedSession()) {
      console.log('No saved session found - using defaults');
      return;
    }

    try {
      const savedSettings = loadLabSettings();
      const savedUIState = loadUIState();

      if (!savedSettings) return;

      const lastSaved = getLastSavedDate();
      console.log(`Restoring session from ${lastSaved ? lastSaved.toLocaleString() : 'unknown date'}`);

      // Restore UI state first (scale, mode, chart type)
      if (savedUIState) {
        // Restore scale
        if (savedUIState.scale) {
          const scaleRadio = document.getElementById(`radio-community-${savedUIState.scale}`);
          if (scaleRadio) {
            scaleRadio.checked = true;
            appState.labSimSettings.scale = savedUIState.scale;
          }
        }

        // Restore mode
        if (savedUIState.mode) {
          const modeRadio = document.getElementById(
            savedUIState.mode === 'advanced' ? 'radio-ui-mode-advanced' : 'radio-ui-mode-simple'
          );
          if (modeRadio) {
            modeRadio.checked = true;
          }
        }

        // Restore chart type
        if (savedUIState.chartType) {
          const chartTypeRadio = document.getElementById(`radio-chart-type-${savedUIState.chartType}`);
          if (chartTypeRadio) {
            chartTypeRadio.checked = true;
            appState.labUISettings.chartType = savedUIState.chartType;
          }
        }
      }

      // Restore settings values
      Object.keys(savedSettings).forEach(key => {
        if (appState.labSimSettings.hasOwnProperty(key)) {
          appState.labSimSettings[key] = savedSettings[key];
        }
      });

      // Update UI controls to match restored settings
      this.updateUIControlsFromSettings();

      console.log('Session restored successfully');
      showSuccess('Previous session restored');
    } catch (e) {
      console.error('Failed to restore session:', e);
      showWarning('Could not restore previous session');
    }
  }

  updateUIControlsFromSettings() {
    // Update all slider values and displays
    const sliderControls = [
      'citySize', 'vehicleCount', 'requestRate', 'maxTripDistance',
      'inhomogeneity', 'price', 'platformCommission', 'reservationWage',
      'demandElasticity', 'meanVehicleSpeed', 'perKmPrice', 'perMinutePrice',
      'perKmOpsCost', 'perHourOpportunityCost', 'animationDelay', 'smoothingWindow'
    ];

    sliderControls.forEach(controlName => {
      const inputElement = DOM_ELEMENTS.inputs[controlName];
      const optionElement = DOM_ELEMENTS.options[controlName];

      if (inputElement && appState.labSimSettings[controlName] !== undefined) {
        inputElement.value = appState.labSimSettings[controlName];
        if (optionElement) {
          optionElement.innerHTML = appState.labSimSettings[controlName];
        }
      }
    });

    // Update equilibrate checkbox
    if (DOM_ELEMENTS.checkboxes.equilibrate) {
      DOM_ELEMENTS.checkboxes.equilibrate.checked = appState.labSimSettings.equilibrate;
    }
  }

  toggleWhatIfFabButton(button) {
    const icon = button.querySelector('.material-icons');
    const text = button.querySelector('.app-button__text');

    if (icon.innerHTML == SimulationActions.Play) {
      icon.innerHTML = SimulationActions.Pause;
      if (text) {
        text.textContent = button == DOM_ELEMENTS.whatIf.baselineFabButton ? 'Pause Baseline' : 'Pause Comparison';
      }
      DOM_ELEMENTS.whatIf.setComparisonButtons.forEach(function (element) {
        element.setAttribute("disabled", "");
      });
      DOM_ELEMENTS.whatIf.baselineRadios.forEach((radio) => {
        radio.disabled = true;
      });
      if (button == DOM_ELEMENTS.whatIf.baselineFabButton) {
        DOM_ELEMENTS.whatIf.baselineFabButton.setAttribute("disabled", "");
        DOM_ELEMENTS.whatIf.comparisonFabButton.setAttribute("disabled", "");
      } else if (button == DOM_ELEMENTS.whatIf.comparisonFabButton) {
        DOM_ELEMENTS.whatIf.baselineFabButton.setAttribute("disabled", "");
      }
    } else if (icon.innerHTML == SimulationActions.Pause) {
      DOM_ELEMENTS.whatIf.setComparisonButtons.forEach(function (element) {
        element.removeAttribute("disabled");
      });
      if (button == DOM_ELEMENTS.whatIf.baselineFabButton) {
        // disable the baseline until a reset
        button.setAttribute("disabled", "");
        DOM_ELEMENTS.whatIf.comparisonFabButton.removeAttribute("disabled");
        const compIcon = DOM_ELEMENTS.whatIf.comparisonFabButton.querySelector('.material-icons');
        const compText = DOM_ELEMENTS.whatIf.comparisonFabButton.querySelector('.app-button__text');
        compIcon.innerHTML = SimulationActions.Play;
        if (compText) compText.textContent = 'Run Comparison';
      } else if (button == DOM_ELEMENTS.whatIf.comparisonFabButton) {
        // whatIfFabButton.removeAttribute("disabled");
        // whatIfFabButton.firstElementChild.innerHTML = SimulationActions.Play;
        // Require a reset before running the baseline again
        icon.innerHTML = SimulationActions.Play;
        if (text) text.textContent = 'Run Comparison';
      }
    }
  }

  resetWhatIfUIAndSimulation() {
    DOM_ELEMENTS.whatIf.frameCount.innerHTML = 0;
    appState.whatIfSimSettingsComparison.action = SimulationActions.Reset;
    w.postMessage(appState.whatIfSimSettingsComparison);
    DOM_ELEMENTS.whatIf.resetButton.removeAttribute("disabled");
    DOM_ELEMENTS.whatIf.baselineFabButton.removeAttribute("disabled");
    DOM_ELEMENTS.whatIf.comparisonFabButton.setAttribute("disabled", "");
    const baselineIcon = DOM_ELEMENTS.whatIf.baselineFabButton.querySelector('.material-icons');
    const baselineText = DOM_ELEMENTS.whatIf.baselineFabButton.querySelector('.app-button__text');
    baselineIcon.innerHTML = SimulationActions.Play;
    if (baselineText) baselineText.textContent = 'Run Baseline';
    DOM_ELEMENTS.whatIf.baselineRadios.forEach((radio) => {
      radio.disabled = false;
    });
    DOM_ELEMENTS.whatIf.baselinePreset.checked = true;
    appState.whatIfSimSettingsBaseline = new WhatIfSimSettingsDefault();
    appState.whatIfSimSettingsBaseline.name = "whatIfSimSettingsBaseline";
    appState.whatIfSimSettingsComparison = new WhatIfSimSettingsDefault();
    appState.whatIfSimSettingsComparison.name = "whatIfSimSettingsComparison";
    /* 
    appState.whatIfSimSettingsBaseline = Object.assign({}, labSimSettings);
    appState.whatIfSimSettingsComparison = Object.assign({}, appState.whatIfSimSettingsBaseline);
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
          appState.whatIfUISettings.ctxWhatIfN = canvas.getContext("2d");
          break;
        case 1:
          appState.whatIfUISettings.ctxWhatIfDemand = canvas.getContext("2d");
          break;
        case 2:
          appState.whatIfUISettings.ctxWhatIfPhases = canvas.getContext("2d");
          break;
        case 3:
          appState.whatIfUISettings.ctxWhatIfIncome = canvas.getContext("2d");
          break;
        case 4:
          appState.whatIfUISettings.ctxWhatIfWait = canvas.getContext("2d");
          break;
        case 5:
          appState.whatIfUISettings.ctxWhatIfPlatform = canvas.getContext("2d");
          break;
      }
      i += 1;
    });

    initWhatIfNChart(appState.whatIfUISettings);
    initWhatIfDemandChart(appState.whatIfUISettings);
    initWhatIfPhasesChart(appState.whatIfUISettings);
    initWhatIfIncomeChart(appState.whatIfUISettings);
    initWhatIfWaitChart(appState.whatIfUISettings);
    initWhatIfPlatformChart(appState.whatIfUISettings);
    initWhatIfTables();
  }

  updateWhatIfTopControlValues() {
    document.getElementById("what-if-price").innerHTML = new Intl.NumberFormat(
      "EN-CA",
      {
        style: "currency",
        currency: "CAD",
      }
    ).format(appState.whatIfSimSettingsComparison.price);
    let temperature =
      appState.whatIfSimSettingsComparison.price -
      appState.whatIfSimSettingsBaseline.price;
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
      Math.round(
        appState.whatIfSimSettingsComparison.platformCommission * 100
      ) + "%";
    temperature =
      appState.whatIfSimSettingsComparison.platformCommission -
      appState.whatIfSimSettingsBaseline.platformCommission;
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
      appState.whatIfSimSettingsComparison.vehicleCount;
    document.getElementById("what-if-reservation-wage").innerHTML =
      new Intl.NumberFormat("EN-CA", {
        style: "currency",
        currency: "CAD",
      }).format(appState.whatIfSimSettingsComparison.reservationWage * 60);
    temperature =
      appState.whatIfSimSettingsComparison.reservationWage -
      appState.whatIfSimSettingsBaseline.reservationWage;
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
      appState.whatIfSimSettingsComparison.requestRate * 60
    );
    temperature =
      appState.whatIfSimSettingsComparison.requestRate -
      appState.whatIfSimSettingsBaseline.requestRate;
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
// Note: DOMContentLoaded has already fired when this module loads (components load first)
// So we instantiate immediately
window.app = new App(); // Make it globally accessible during transition

export function handlePyodideReady() {
  // Stop rotating tips
  if (tipRotationInterval) {
    clearInterval(tipRotationInterval);
  }

  // Hide loading overlay with fade-out animation
  if (loadingOverlay) {
    loadingOverlay.classList.add('fade-out');
    // Remove from DOM after animation completes
    setTimeout(() => {
      loadingOverlay.style.display = 'none';
    }, 500);
  }

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
        frameIndex >= appState.labSimSettings.timeBlocks &&
        appState.labSimSettings.timeBlocks !== 0
      ) {
        appState.labSimSettings.action = SimulationActions.Done;
        w.postMessage(appState.labSimSettings);
        window.app.toggleLabFabButton(DOM_ELEMENTS.controls.fabButton);
      }
    },
    whatIfSimSettingsBaseline: () => {
      if (frameIndex % 10 === 0) {
        DOM_ELEMENTS.whatIf.frameCount.innerHTML = `${frameIndex}/${results.get(
          "time_blocks"
        )}`;
      }
      if (
        frameIndex >= appState.whatIfSimSettingsBaseline.timeBlocks &&
        appState.whatIfSimSettingsBaseline.timeBlocks !== 0
      ) {
        appState.whatIfSimSettingsBaseline.action = SimulationActions.Done;
        appState.setBaselineData(results);
        w.postMessage(appState.whatIfSimSettingsBaseline);
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
        frameIndex >= appState.whatIfSimSettingsComparison.timeBlocks &&
        appState.whatIfSimSettingsComparison.timeBlocks !== 0
      ) {
        appState.whatIfSimSettingsComparison.action = SimulationActions.Done;
        w.postMessage(appState.whatIfSimSettingsComparison);
        window.app.toggleWhatIfFabButton(
          DOM_ELEMENTS.whatIf.comparisonFabButton
        );
      }
    },
  };

  const updater = counterUpdaters[name];
  if (updater) {
    updater();
  } else {
    console.log(`No updater found for name: "${name}"`);
  }
}
