/*
 * Imports and exports from and to modules
 * Updated: 2024-12 - Full-screen loading overlay implementation
 * Updated: 2024-12 - Refactored Experiment tab into separate module
 */

import { ExperimentTab } from "./experiment-tab.js";
import { WhatIfTab } from "./whatif-tab.js";

import { DOM_ELEMENTS } from "./js/dom-elements.js";
import { colors } from "./js/constants.js";
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
import {
  webToDesktopConfig,
  desktopToWebConfig,
  validateDesktopConfig,
} from "./js/config-mapping.js";
import {
  inferAndClampSettings,
  getConfigSummary,
} from "./js/scale-inference.js";
import { showSuccess, showError, showWarning } from "./js/toast.js";
import { rotateTips } from "./js/loading-tips.js";
import { KeyboardHandler } from "./js/keyboard-handler.js";
import {
  saveLabSettings,
  saveUIState,
  loadLabSettings,
  loadUIState,
  hasSavedSession,
  getLastSavedDate,
} from "./js/session-storage.js";
import {
  FullScreenManager,
  addDoubleClickHandler,
  addMobileTouchHandlers,
  addFullScreenHint,
} from "./js/fullscreen.js";

// Initialize the unified app state
appState.initialize();

// Start loading overlay with rotating tips
const loadingOverlay = document.getElementById("loading-overlay");
const loadingTip = document.getElementById("loading-tip");
let tipRotationInterval = null;

if (loadingTip) {
  tipRotationInterval = rotateTips(loadingTip, 2500);
}

const messageHandler = new MessageHandler(
  handlePyodideReady,
  updateBlockCounters,
);

class App {
  constructor() {
    this.packageVersion = null; // Will be set from Python package
    this.init();
  }

  async init() {
    // Set application title with version
    this.setTitle();

    // Initialize full-screen manager (needed by tabs)
    this.fullScreenManager = new FullScreenManager();

    // Initialize Experiment tab
    this.experimentTab = new ExperimentTab(this, this.fullScreenManager);

    // Initialize What If tab
    this.whatIfTab = new WhatIfTab(this, this.fullScreenManager);

    // Move initialization code here gradually
    this.setupButtonHandlers();
    this.setupForEachHandlers();
    this.whatIfTab.setupEventHandlers();
    setupInputHandlers({
      updateSettings: (property, value) =>
        this.experimentTab.updateLabSimSettings(property, value),
      resetSimulation: () => this.experimentTab.resetUIAndSimulation(),
      updateSimulation: this.updateSimulationOptions,
      saveSettings: () => this.experimentTab.saveSessionSettings(),
      updateControlVisibility: () =>
        this.experimentTab.updateControlVisibility(),
    });
    initializeMD3Sliders();

    // Set up chart type and mode radio button handlers
    createChartTypeRadioHandler((value) =>
      this.experimentTab.updateChartType(value),
    );
    createModeRadioHandler((value) => this.experimentTab.updateMode(value));

    // Try to restore previous session
    this.restoreSession();

    this.experimentTab.setInitialValues(false);

    // Initialize keyboard handler with shared mappings
    this.keyboardHandler = new KeyboardHandler(this);
    await this.keyboardHandler.loadMappings();
  }

  /**
   * Set the application title
   */
  setTitle() {
    const titleElement = document.getElementById("app-title");
    if (titleElement) {
      titleElement.textContent = "Ridehail Laboratory";
    }
  }

  /**
   * Update version display with package version from Python
   */
  updateVersionDisplay() {
    const versionElement = document.getElementById("package-version");
    if (versionElement && this.packageVersion) {
      versionElement.textContent = `v${this.packageVersion}`;
    }
  }

  setupButtonHandlers() {
    DOM_ELEMENTS.controls.resetButton.onclick = () =>
      this.experimentTab.resetUIAndSimulation();

    DOM_ELEMENTS.whatIf.resetButton.onclick = () =>
      this.whatIfTab.resetUIAndSimulation();

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

    DOM_ELEMENTS.configControls.confirmDialog.querySelector(
      ".app-dialog__overlay",
    ).onclick = () => this.hideConfigDialog();

    if (DOM_ELEMENTS.keyboardHelp.closeButton) {
      DOM_ELEMENTS.keyboardHelp.closeButton.onclick = () =>
        this.hideKeyboardHelpDialog();
    }

    if (DOM_ELEMENTS.keyboardHelp.dialog) {
      DOM_ELEMENTS.keyboardHelp.dialog.querySelector(
        ".app-dialog__overlay",
      ).onclick = () => this.hideKeyboardHelpDialog();
    }

    DOM_ELEMENTS.controls.fabButton.onclick = () => {
      this.experimentTab.clickFabButton();
    };

    DOM_ELEMENTS.whatIf.baselineFabButton.onclick = () =>
      this.whatIfTab.clickFabButton(
        DOM_ELEMENTS.whatIf.baselineFabButton,
        appState.whatIfSimSettingsBaseline,
      );

    DOM_ELEMENTS.whatIf.comparisonFabButton.onclick = () =>
      this.whatIfTab.clickFabButton(
        DOM_ELEMENTS.whatIf.comparisonFabButton,
        appState.whatIfSimSettingsComparison,
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
          element.getAttribute("href"),
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
            app.experimentTab.resetUIAndSimulation();
            break;
          case "tab-what-if":
            app.whatIfTab.resetUIAndSimulation();
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
        this.experimentTab.setInitialValues(true);
        // Save scale change to session
        this.experimentTab.saveSessionSettings();
      }),
    );

    // Keyboard handling is now managed by KeyboardHandler class
    // initialized in init() method

    // What If event handlers are now in whatIfTab.setupEventHandlers()
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
    const timestamp = now
      .toISOString()
      .replace(/:/g, "-")
      .replace(/\..+/, "")
      .replace("T", "_");
    const filename = `ridehail_lab_${timestamp}.config`;

    // Create blob and download
    const blob = new Blob([iniContent], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
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
        const { scale, clampedSettings, warnings } =
          inferAndClampSettings(webConfig);

        // Show confirmation dialog
        this.showConfigConfirmation(clampedSettings, scale, warnings);
      } catch (error) {
        showError(`Error reading configuration file: ${error.message}`);
        console.error(error);
      }
    };

    reader.readAsText(file);

    // Reset file input so same file can be selected again
    event.target.value = "";
  }

  /**
   * Setup drag and drop handlers for the drop zone
   */
  setupDropZone() {
    const dropZone = DOM_ELEMENTS.configControls.dropZone;
    if (!dropZone) return;

    // Prevent default drag behaviors on the whole document
    ["dragenter", "dragover", "dragleave", "drop"].forEach((eventName) => {
      document.body.addEventListener(
        eventName,
        (e) => {
          e.preventDefault();
          e.stopPropagation();
        },
        false,
      );
    });

    // Highlight drop zone when item is dragged over it
    ["dragenter", "dragover"].forEach((eventName) => {
      dropZone.addEventListener(
        eventName,
        () => {
          dropZone.classList.add("drag-over");
        },
        false,
      );
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropZone.addEventListener(
        eventName,
        () => {
          dropZone.classList.remove("drag-over");
        },
        false,
      );
    });

    // Handle dropped files
    dropZone.addEventListener(
      "drop",
      (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;

        if (files.length > 0) {
          this.handleDroppedFile(files[0]);
        }
      },
      false,
    );

    // Also make the drop zone clickable to trigger file input
    dropZone.addEventListener(
      "click",
      () => {
        DOM_ELEMENTS.configControls.uploadInput.click();
      },
      false,
    );
  }

  /**
   * Handle a file dropped onto the drop zone
   */
  handleDroppedFile(file) {
    // Check if it's a .config file
    if (!file.name.endsWith(".config")) {
      showError("Please drop a .config file");
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
        const { scale, clampedSettings, warnings } =
          inferAndClampSettings(webConfig);

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
        <dd>${configSummary.equilibrate ? "Yes" : "No"}</dd>
        <dt>Mode:</dt>
        <dd>${configSummary.useCostsAndIncomes ? "Costs & Incomes" : "Simple Model"}</dd>
      </dl>
    `;
    summary.innerHTML = summaryHTML;

    // Build warnings
    if (warnings.length > 0) {
      const warningsHTML = `
        <strong>Adjustments made:</strong>
        <ul style="margin: 8px 0 0 0; padding-left: 20px;">
          ${warnings.map((w) => `<li>${w.message}</li>`).join("")}
        </ul>
      `;
      warningsDiv.innerHTML = warningsHTML;
    } else {
      warningsDiv.innerHTML = "";
    }

    // Store settings for confirmation
    this.pendingConfig = { settings, scale, warnings };

    // Show dialog
    dialog.removeAttribute("hidden");
  }

  /**
   * Apply uploaded configuration
   */
  applyUploadedConfig() {
    if (!this.pendingConfig) return;

    const { settings, scale } = this.pendingConfig;

    // Update scale radio
    const scaleRadio = document.querySelector(
      `input[name="scale"][value="${scale}"]`,
    );
    if (scaleRadio) {
      scaleRadio.checked = true;
      appState.labSimSettings.scale = scale;
    }

    // Update all settings
    Object.assign(appState.labSimSettings, settings);

    // Update UI mode radio
    const uiMode = settings.useCostsAndIncomes ? "advanced" : "simple";
    const uiModeRadio = document.querySelector(
      `input[name="ui-mode"][value="${uiMode}"]`,
    );
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
      showWarning(
        `Configuration loaded with adjustments (Scale: ${scale.toUpperCase()})`,
        4000,
      );
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
      citySize: "citySize",
      vehicleCount: "vehicleCount",
      requestRate: "requestRate",
      maxTripDistance: "maxTripDistance",
      inhomogeneity: "inhomogeneity",
      price: "price",
      platformCommission: "platformCommission",
      reservationWage: "reservationWage",
      demandElasticity: "demandElasticity",
      meanVehicleSpeed: "meanVehicleSpeed",
      perKmPrice: "perKmPrice",
      perMinutePrice: "perMinutePrice",
      perKmOpsCost: "perKmOpsCost",
      perHourOpportunityCost: "perHourOpportunityCost",
      animationDelay: "animationDelay",
      smoothingWindow: "smoothingWindow",
    };

    for (const [inputKey, settingsKey] of Object.entries(inputMap)) {
      if (
        settings[settingsKey] !== undefined &&
        DOM_ELEMENTS.inputs[inputKey]
      ) {
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
    DOM_ELEMENTS.configControls.confirmDialog.setAttribute("hidden", "");
    this.pendingConfig = null;
  }

  hideKeyboardHelpDialog() {
    DOM_ELEMENTS.keyboardHelp.dialog.setAttribute("hidden", "");
  }

  updateSimulationOptions(updateType) {
    appState.labSimSettings.action = updateType;
    w.postMessage(appState.labSimSettings);
  }

  restoreSession() {
    // Check if we have saved session data
    if (!hasSavedSession()) {
      console.log("No saved session found - using defaults");
      return;
    }

    try {
      const savedSettings = loadLabSettings();
      const savedUIState = loadUIState();

      if (!savedSettings) return;

      const lastSaved = getLastSavedDate();
      console.log(
        `Restoring session from ${lastSaved ? lastSaved.toLocaleString() : "unknown date"}`,
      );

      // Restore UI state first (scale, mode, chart type)
      if (savedUIState) {
        // Restore scale
        if (savedUIState.scale) {
          const scaleRadio = document.getElementById(
            `radio-community-${savedUIState.scale}`,
          );
          if (scaleRadio) {
            scaleRadio.checked = true;
            appState.labSimSettings.scale = savedUIState.scale;
          }
        }

        // Restore mode
        if (savedUIState.mode) {
          const modeRadio = document.getElementById(
            savedUIState.mode === "advanced"
              ? "radio-ui-mode-advanced"
              : "radio-ui-mode-simple",
          );
          if (modeRadio) {
            modeRadio.checked = true;
          }
        }

        // Restore chart type
        if (savedUIState.chartType) {
          const chartTypeRadio = document.getElementById(
            `radio-chart-type-${savedUIState.chartType}`,
          );
          if (chartTypeRadio) {
            chartTypeRadio.checked = true;
            appState.labUISettings.chartType = savedUIState.chartType;
          }
        }
      }

      // Restore settings values
      Object.keys(savedSettings).forEach((key) => {
        if (appState.labSimSettings.hasOwnProperty(key)) {
          appState.labSimSettings[key] = savedSettings[key];
        }
      });

      // Update UI controls to match restored settings
      this.updateUIControlsFromSettings();

      console.log("Session restored successfully");
      showSuccess("Previous session restored");
    } catch (e) {
      console.error("Failed to restore session:", e);
      showWarning("Could not restore previous session");
    }
  }

  updateUIControlsFromSettings() {
    // Update all slider values and displays
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

      if (inputElement && appState.labSimSettings[controlName] !== undefined) {
        inputElement.value = appState.labSimSettings[controlName];
        if (optionElement) {
          optionElement.innerHTML = appState.labSimSettings[controlName];
        }
      }
    });

    // Update equilibrate checkbox
    if (DOM_ELEMENTS.checkboxes.equilibrate) {
      DOM_ELEMENTS.checkboxes.equilibrate.checked =
        appState.labSimSettings.equilibrate;
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
    loadingOverlay.classList.add("fade-out");
    // Remove from DOM after animation completes
    setTimeout(() => {
      loadingOverlay.style.display = "none";
    }, 500);
  }

  window.app.experimentTab.setInitialValues(true);
  window.app.whatIfTab.resetUIAndSimulation();
}

export function updateBlockCounters(results) {
  const frameIndex = results.get("frame");
  const name = results.get("name");

  // Extract and store package version on first frame
  if (frameIndex === 0 && results.has("version")) {
    const version = results.get("version");
    if (window.app && version) {
      window.app.packageVersion = version;
      window.app.updateVersionDisplay();
    }
  }

  const counterUpdaters = {
    labSimSettings: () => {
      window.app.experimentTab.updateBlockCounter(results);
    },
    whatIfSimSettingsBaseline: () => {
      window.app.whatIfTab.updateBaselineBlockCounter(results);
    },
    whatIfSimSettingsComparison: () => {
      window.app.whatIfTab.updateComparisonBlockCounter(results);
    },
  };

  const updater = counterUpdaters[name];
  if (updater) {
    updater();
  } else {
    console.log(`No updater found for name: "${name}"`);
  }
}
