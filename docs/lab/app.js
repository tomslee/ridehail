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
  applyPythonPresets,
  levelFromDelay,
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
  updateSliderFill,
  valueToLogSlider,
} from "./js/input-handlers.js";
import { MessageHandler } from "./js/message-handler.js";
import { appState } from "./js/app-state.js";
import { parseINI, generateINI, formatResultsSection } from "./js/config-file.js";
import {
  webToDesktopConfig,
  desktopToWebConfig,
  validateDesktopConfig,
} from "./js/config-mapping.js";
import {
  inferPresetFromSettings,
  getConfigSummary,
} from "./js/scale-inference.js";
import { showSuccess, showError, showWarning, showInfo } from "./js/toast.js";
import { initSimTitle } from "./js/sim-title.js";
import { initAllSliderDirectEdits } from "./js/slider-direct-edit.js";
import { initNavMenu } from "./js/nav-menu.js";
import {
  initSavedConfigs,
  setProvenance,
  PROVENANCE,
} from "./js/saved-configs.js";
import { rotateTips } from "./js/loading-tips.js";
import { KeyboardHandler } from "./js/keyboard-handler.js";
import {
  saveLabSettings,
  saveUIState,
  loadLabSettings,
  loadUIState,
  hasSavedSession,
  getLastSavedDate,
  clearSessionData,
} from "./js/session-storage.js";
import {
  FullScreenManager,
  addDoubleClickHandler,
  addMobileTouchHandlers,
  addFullScreenHint,
} from "./js/fullscreen.js";
import { fitMapToViewport } from "./modules/map.js";
import { initPhone } from "./js/phone.js";

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
  (helpData) => window.app?.experimentTab?.initSliderHelp(helpData),
  (configData) => window.app?.experimentTab?.initSliderConstraints(configData),
  // Preset values from Python: overlay them onto SCALE_CONFIGS before the DOM
  // controls are first populated by handlePyodideReady -> setInitialValues.
  applyPythonPresets,
);

/**
 * Human-readable title for a preset button, e.g. "town" -> "Town (Preset)".
 * Used as the scenario title when a preset is loaded (presets carry no title
 * field of their own).
 * @param {string} preset - "village" | "town" | "city"
 * @returns {string}
 */
function presetTitle(preset) {
  const name = preset ? preset.charAt(0).toUpperCase() + preset.slice(1) : "";
  return `${name} (Preset)`;
}

class App {
  constructor() {
    this.packageVersion = null; // Will be set from Python package
    this.cliAutoStart = false; // Flag to auto-start simulation in CLI mode after Pyodide loads
    this.restoredSession = false; // True once a previous session's values were restored (see restoreSession)
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

    // Wire up the click-to-edit simulation title in the header
    initSimTitle(
      () => appState.labSimSettings.title,
      (newTitle) => this.experimentTab.updateLabSimSettings("title", newTitle),
    );

    // Wire up the external-links dropdown menu in the header
    initNavMenu();

    // Wire up the local saved-configurations library (top controls bar)
    initSavedConfigs({
      getTitle: () => appState.labSimSettings.title,
      getSettings: () => appState.labSimSettings,
      onLoad: (title, settings, scale, warnings) =>
        this.loadSavedConfiguration(title, settings, scale, warnings),
    });

    // Move initialization code here gradually
    this.setupButtonHandlers();
    this.setupForEachHandlers();
    this.whatIfTab.setupEventHandlers();
    setupInputHandlers({
      updateSettings: (property, value) =>
        this.experimentTab.updateLabSimSettings(property, value),
      resetSimulation: () => this.experimentTab.resetUIAndSimulation(),
      updateSimulation: this.updateSimulationOptions,
      markPending: (settingName) =>
        this.experimentTab.markParamPending(settingName),
      saveSettings: () => this.experimentTab.saveSessionSettings(),
      updateControlVisibility: () =>
        this.experimentTab.updateControlVisibility(),
    });
    initializeMD3Sliders();
    initAllSliderDirectEdits({
      "input-mean-trip-distance": {
        // Derive the upper bound from the Python-provided constraint metadata
        // (see worker.py::get_slider_config). Returns NaN until that metadata
        // arrives, which leaves the slider's static max in force; by the time
        // a user opens the editor, Pyodide has loaded and the real bound applies.
        getMax: () =>
          this.experimentTab.resolveMaxConstraint("meanTripDistance"),
      },
    });

    // Keep mean trip distance limit in sync whenever city size changes
    DOM_ELEMENTS.inputs.citySize.addEventListener('change', () => {
      this.experimentTab.syncMeanTripDistanceLimit();
    });

    // Set up chart type and mode radio button handlers
    createChartTypeRadioHandler((value) =>
      this.experimentTab.updateChartType(value),
    );
    createModeRadioHandler((value) => this.experimentTab.updateMode(value));

    // Check for CLI mode before restoring session
    // CLI mode takes precedence over saved session
    const cliMode = await this.checkAndHandleCLIMode();

    if (!cliMode) {
      // Only restore previous session if not in CLI mode. restoreSession()
      // populates labSimSettings from the autosave; setInitialValues then
      // builds the DOM controls and charts. Pass preserveValues so it keeps
      // the restored parameter values instead of resetting them to the scale
      // preset (which is what a fresh, session-less load wants).
      this.restoredSession = this.restoreSession();
      if (!this.restoredSession) {
        // A first-time visitor's default configuration is the Village preset,
        // so present it as one (title + provenance) for consistency with the
        // preset buttons - otherwise the header would read "Untitled" and edits
        // would show no "unsaved" dot. A restored session keeps its own title
        // and provenance (re-established in initSavedConfigs).
        appState.labSimSettings.title = presetTitle(appState.labSimSettings.scale);
      }
      this.experimentTab.setInitialValues(false, this.restoredSession);
      if (!this.restoredSession) {
        setProvenance({
          kind: PROVENANCE.PRESET,
          name: appState.labSimSettings.scale,
        });
      }
    }

    // Initialize keyboard handler with shared mappings
    this.keyboardHandler = new KeyboardHandler(this);
    await this.keyboardHandler.loadMappings();

    if (!cliMode) {
      // Restore zoom level from a previous session, if any. This can only
      // happen after the keyboard handler exists, since it owns zoom state.
      const savedUIState = loadUIState();
      if (savedUIState?.zoomState != null) {
        this.keyboardHandler.restoreZoomState(savedUIState.zoomState);
      }
    }

    // Activate the phone showcase tier (no-op on wider screens). Must come
    // after keyboardHandler + experimentTab exist, since the phone chrome
    // proxies onto them.
    initPhone(this);
  }

  /**
   * Set the application title
   */
  setTitle() {
    // Targets the nested text span, not #app-title itself, so the
    // package-version span nested alongside it isn't wiped out.
    const titleElement = document.getElementById("app-title-text");
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

  /**
   * Check for CLI mode and handle config auto-load
   *
   * Parses URL parameters to detect CLI-launched sessions:
   *   ?chartType=map&autoLoad=cli_config.json
   *
   * Returns: true if CLI mode detected and handled, false otherwise
   */
  async checkAndHandleCLIMode() {
    const urlParams = new URLSearchParams(window.location.search);
    const autoLoad = urlParams.get('autoLoad');
    const chartType = urlParams.get('chartType');

    if (!autoLoad) {
      return false; // Not CLI mode
    }

    console.log(`CLI mode detected: autoLoad=${autoLoad}, chartType=${chartType}`);

    try {
      // Clear any saved session data to prevent conflicts with CLI config
      clearSessionData();
      console.log('Cleared saved session data for CLI mode');

      // Show CLI mode indicator
      this.showCLIModeIndicator();

      // Load config from server
      const response = await fetch(`./config/${autoLoad}`);
      if (!response.ok) {
        throw new Error(`Failed to load config: ${response.status} ${response.statusText}`);
      }

      const config = await response.json();
      console.log('CLI config loaded successfully:', config);
      console.log('Config values - citySize:', config.citySize, 'vehicleCount:', config.vehicleCount);

      // Apply config (similar to uploaded config, but skip confirmation dialog)
      console.log('Applying CLI config...');
      await this.applyCLIConfig(config, chartType);
      console.log('CLI config applied successfully');

      // Show success message
      showSuccess('Configuration loaded from CLI');

      return true; // CLI mode handled
    } catch (error) {
      console.error('Error loading CLI config:', error);
      showError(`Failed to load CLI configuration: ${error.message}`);
      return false;
    }
  }

  /**
   * Apply configuration from CLI (no confirmation dialog)
   */
  async applyCLIConfig(config, chartType) {
    console.log('applyCLIConfig called with config:', config);

    // Record the nearest preset (for session/reference only; values are used
    // exactly and no preset button holds a selected state)
    const scale = inferPresetFromSettings(config);
    appState.labSimSettings.scale = scale;

    // Update all settings
    Object.assign(appState.labSimSettings, config);

    // A URL-launched config isn't tied to a saved-library entry, so record
    // "url" provenance: clears the "unsaved" dot and the dropdown selection.
    setProvenance({ kind: PROVENANCE.URL });

    // Set chart type if specified
    if (chartType) {
      const chartTypeRadio = document.querySelector(
        `input[name="chart-type"][value="${chartType}"]`
      );
      if (chartTypeRadio) {
        chartTypeRadio.checked = true;
        const chartTypeValue = chartType === 'map' ? CHART_TYPES.MAP : CHART_TYPES.STATS;
        appState.labSimSettings.chartType = chartTypeValue;
        appState.labUISettings.chartType = chartTypeValue; // Also set UI settings for chart initialization
      }
    }

    // Update UI mode radio
    const uiMode = config.useCostsAndIncomes ? 'advanced' : 'simple';
    const uiModeRadio = document.querySelector(`input[name="ui-mode"][value="${uiMode}"]`);
    if (uiModeRadio) {
      uiModeRadio.checked = true;
    }

    // Update equilibrate checkbox
    DOM_ELEMENTS.checkboxes.equilibrate.checked = config.equilibrate || false;

    // Reset the control ranges/visibility, then apply the loaded values
    this.experimentTab.setLabConfigControls(SCALE_CONFIGS[scale]);

    // Update all input values
    this.updateAllUIControls(config);

    // Initialize charts and controls for CLI mode
    this.experimentTab.setLabTopControls(false);
    this.experimentTab.initLabCharts();

    // Wait a bit for UI to update
    await new Promise(resolve => setTimeout(resolve, 500));

    // Set flag to auto-start when Pyodide is ready
    this.cliAutoStart = true;
    console.log('CLI config applied - will auto-start when Pyodide is ready');
  }

  /**
   * Show CLI mode indicator in the UI
   */
  showCLIModeIndicator() {
    const titleElement = document.getElementById("app-title-text");
    if (titleElement) {
      titleElement.textContent = "Ridehail Laboratory [CLI Mode]";
      // titleElement.style.color = "#4CAF50"; // Green to indicate CLI mode
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

    // Animation speed: click cycles Slow -> Normal -> Fast -> Max -> (wrap);
    // scrolling over the button fine-tunes without wrapping (up = faster).
    if (DOM_ELEMENTS.controls.speedButton) {
      DOM_ELEMENTS.controls.speedButton.onclick = () =>
        this.experimentTab.stepSpeed(1, { wrap: true });
      DOM_ELEMENTS.controls.speedButton.addEventListener(
        "wheel",
        (e) => {
          e.preventDefault();
          this.experimentTab.stepSpeed(e.deltaY < 0 ? 1 : -1);
        },
        { passive: false },
      );
    }
  }

  setupForEachHandlers() {
    const app = this;

    // Re-fit the map square whenever the viewport changes size (debounced).
    let resizeTimer = null;
    window.addEventListener("resize", () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => fitMapToViewport(), 100);
    });

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

    DOM_ELEMENTS.collections.presetButtons.forEach((button) =>
      button.addEventListener("click", () => {
        // Presets are momentary "load" buttons: clicking one loads its set of
        // starting values for a new simulation. It does not hold a selected
        // state - the values are the user's to edit freely afterwards.
        const preset = button.dataset.preset;
        appState.labSimSettings.scale = preset;
        // A preset is a fresh start, so it overwrites any prior title with a
        // "<Name> (Preset)" label. setInitialValues preserves this title
        // across its rebuild (and refreshes the header display).
        appState.labSimSettings.title = presetTitle(preset);
        this.experimentTab.setInitialValues(true);
        // Save the loaded preset to session (records the last preset applied)
        this.experimentTab.saveSessionSettings();
        // Establish preset provenance: clears the "unsaved" dot and resets the
        // saved-config dropdown to its placeholder (this is not a saved entry).
        setProvenance({ kind: PROVENANCE.PRESET, name: preset });
      }),
    );

    // Keyboard handling is now managed by KeyboardHandler class
    // initialized in init() method

    // What If event handlers are now in whatIfTab.setupEventHandlers()
  }

  /**
   * Download current lab settings as desktop-compatible .config file with results
   */
  async downloadConfiguration() {
    try {
      // Convert web settings to desktop config format
      const desktopConfig = webToDesktopConfig(appState.labSimSettings);

      // Generate INI string
      let iniContent = generateINI(desktopConfig);

      // Request simulation results from worker (if simulation has run)
      const results = await messageHandler.requestSimulationResults();

      // Append [RESULTS] section if results are available
      if (results && Object.keys(results).length > 0) {
        const resultsSection = formatResultsSection(results);
        iniContent += resultsSection;
        console.log("Added [RESULTS] section to configuration file");
      }

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
    } catch (error) {
      console.error("Error downloading configuration:", error);
      showError("Failed to download configuration");
    }
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

        // A .config without a title field gets the filename as its scenario
        // label, rather than a bare "Untitled" that hides where it came from.
        if (!webConfig.title) {
          webConfig.title = file.name.replace(/\.config$/i, "");
        }

        // Highlight the nearest preset (values are used exactly, not clamped)
        const scale = inferPresetFromSettings(webConfig);

        // Show confirmation dialog
        this.showConfigConfirmation(webConfig, scale, []);
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
    // Loading a configuration re-initializes the simulation, so it is only
    // allowed when a run is not in progress. The upload button/input is
    // disabled while running, but a drag-and-drop can still reach here.
    if (appState.simState === "running") {
      showInfo("Pause the simulation to load a configuration");
      return;
    }
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

        // A .config without a title field gets the filename as its scenario
        // label, rather than a bare "Untitled" that hides where it came from.
        if (!webConfig.title) {
          webConfig.title = file.name.replace(/\.config$/i, "");
        }

        // Highlight the nearest preset (values are used exactly, not clamped)
        const scale = inferPresetFromSettings(webConfig);

        // Show confirmation dialog
        this.showConfigConfirmation(webConfig, scale, []);
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
        <dt>Title:</dt>
        <dd>${configSummary.title}</dd>
        <dt>Nearest preset:</dt>
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
   * Apply settings + scale to the running UI/simulation. Shared by uploaded
   * .config files and entries loaded from the local saved-configurations
   * library, which both produce the same {settings, scale} shape via
   * desktopToWebConfig() + inferPresetFromSettings(). The scale is recorded as
   * the nearest preset (for session/reference only); the settings are applied
   * exactly and no preset button holds a selected state.
   */
  applySettingsAndScale(settings, scale) {
    // Record the nearest preset (reference only)
    appState.labSimSettings.scale = scale;

    // Update all settings
    Object.assign(appState.labSimSettings, settings);

    // Seed the map speed level from the loaded animationDelay (ms) so an
    // imported/saved config lands on the nearest cycle stop. setLabTopControls
    // (via resetUIAndSimulation below) then derives the delay + button label.
    if (settings.animationDelay !== undefined) {
      appState.labUISettings.speedLevel = {
        ...appState.labUISettings.speedLevel,
        map: levelFromDelay(settings.animationDelay, "map"),
      };
    }

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

    // Reset the control ranges/visibility, then apply the loaded values
    this.experimentTab.setLabConfigControls(SCALE_CONFIGS[scale]);

    // Update all input values
    this.updateAllUIControls(settings);

    // Reset simulation
    this.experimentTab.resetUIAndSimulation();
  }

  /**
   * Apply uploaded configuration
   */
  applyUploadedConfig() {
    if (!this.pendingConfig) return;

    const { settings, scale } = this.pendingConfig;
    this.applySettingsAndScale(settings, scale);
    // An uploaded config isn't tied to a saved-library entry, so record "file"
    // provenance: clears the "unsaved" dot and the dropdown selection.
    setProvenance({ kind: PROVENANCE.FILE });
    this.hideConfigDialog();

    showSuccess("Configuration loaded");
  }

  /**
   * Load a named configuration from the local saved-configurations library.
   */
  loadSavedConfiguration(title, settings, scale) {
    this.applySettingsAndScale(settings, scale);
    showSuccess(`Loaded "${title}"`);
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
      meanTripDistance: "meanTripDistance",
      inhomogeneity: "inhomogeneity",
      idleVehiclesMoving: "idleVehiclesMoving",
      price: "price",
      platformCommission: "platformCommission",
      reservationWage: "reservationWage",
      demandElasticity: "demandElasticity",
      meanVehicleSpeed: "meanVehicleSpeed",
      perKmPrice: "perKmPrice",
      perMinutePrice: "perMinutePrice",
      perKmOpsCost: "perKmOpsCost",
      perHourOpportunityCost: "perHourOpportunityCost",
      smoothingWindow: "smoothingWindow",
    };
    // animationDelay has no slider; its speed level is seeded from the loaded
    // delay in applySettingsAndScale().

    for (const [inputKey, settingsKey] of Object.entries(inputMap)) {
      if (
        settings[settingsKey] !== undefined &&
        DOM_ELEMENTS.inputs[inputKey]
      ) {
        const inputEl = DOM_ELEMENTS.inputs[inputKey];
        const actualValue = settings[settingsKey];
        if (inputEl.hasAttribute('data-log-min')) {
          const logMin = parseFloat(inputEl.dataset.logMin);
          const logMax = parseFloat(inputEl.dataset.logMax);
          inputEl.value = valueToLogSlider(actualValue, logMin, logMax);
        } else {
          inputEl.value = actualValue;
        }
        if (DOM_ELEMENTS.options[inputKey]) {
          DOM_ELEMENTS.options[inputKey].textContent = actualValue;
        }
        updateSliderFill(inputEl);
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

    // Restore pause state after help is dismissed
    // If simulation was running before help (isPaused was false), resume it
    if (this._helpPreviousPauseState === false) {
      const currentlyPaused = !DOM_ELEMENTS.controls.nextStepButton.hasAttribute("disabled");
      // Only resume if still paused (don't toggle if user manually resumed while help was open)
      if (currentlyPaused) {
        this.experimentTab.clickFabButton();
      }
    }
    // Clear the saved state
    this._helpPreviousPauseState = undefined;
  }

  updateSimulationOptions(updateType) {
    appState.labSimSettings.action = updateType;
    w.postMessage(appState.labSimSettings);
  }

  /**
   * Restore the autosaved session into appState.labSimSettings (parameter
   * values plus scale/mode/chart type). The caller then runs
   * setInitialValues(preserveValues=true), which builds the DOM controls and
   * charts from these restored values. Returns true when a session was
   * restored, false otherwise (so the caller can fall back to a fresh preset).
   * @returns {boolean}
   */
  restoreSession() {
    // Check if we have saved session data
    if (!hasSavedSession()) {
      console.log("No saved session found - using defaults");
      return false;
    }

    try {
      const savedSettings = loadLabSettings();
      const savedUIState = loadUIState();

      if (!savedSettings) return false;

      const lastSaved = getLastSavedDate();
      console.log(
        `Restoring session from ${lastSaved ? lastSaved.toLocaleString() : "unknown date"}`,
      );

      // Restore the parameter values into labSimSettings.
      Object.keys(savedSettings).forEach((key) => {
        if (appState.labSimSettings.hasOwnProperty(key)) {
          appState.labSimSettings[key] = savedSettings[key];
        }
      });

      // Restore scale/mode/chart type, which live in the separate UI-state
      // store rather than the settings blob. setInitialValues -> setLabTopControls
      // reads these back off labSimSettings to set the radios, so write them
      // here rather than poking the radios directly.
      if (savedUIState) {
        if (savedUIState.scale) {
          appState.labSimSettings.scale = savedUIState.scale;
        }
        // Prefer the value saved with the settings blob (new sessions); fall
        // back to the UI-state mode string for sessions saved before
        // useCostsAndIncomes was persisted with the settings.
        if (savedUIState.mode) {
          appState.labSimSettings.useCostsAndIncomes =
            savedUIState.mode === "advanced";
        }
        if (savedUIState.chartType) {
          appState.labSimSettings.chartType = savedUIState.chartType;
          appState.labUISettings.chartType = savedUIState.chartType;
        }
        // Per-mode speed levels; merge over defaults so a partial/legacy blob
        // still yields a full { map, stats } object.
        if (savedUIState.speedLevel) {
          appState.labUISettings.speedLevel = {
            ...appState.labUISettings.speedLevel,
            ...savedUIState.speedLevel,
          };
        }
      }

      console.log("Session restored successfully");
      showSuccess("Previous session restored");
      return true;
    } catch (e) {
      console.error("Failed to restore session:", e);
      showWarning("Could not restore previous session");
      return false;
    }
  }

} // App

// Create single instance but keep globals accessible
// Note: DOMContentLoaded has already fired when this module loads (components load first)
// So we instantiate immediately
window.app = new App(); // Make it globally accessible during transition

export function handlePyodideReady(version) {
  // Stop rotating tips
  if (tipRotationInterval) {
    clearInterval(tipRotationInterval);
  }

  // Show the version as soon as Pyodide reports it, rather than waiting for
  // the first simulation frame (results["version"] in worker.py) - otherwise
  // the header shows no version at all until a simulation is started.
  if (version) {
    window.app.packageVersion = version;
    window.app.updateVersionDisplay();
  }

  // Hide loading overlay with fade-out animation
  if (loadingOverlay) {
    loadingOverlay.classList.add("fade-out");
    // Remove from DOM after animation completes
    setTimeout(() => {
      loadingOverlay.style.display = "none";
    }, 500);
  }

  // Only call setInitialValues if not in CLI mode (CLI mode already set values).
  // Preserve restored session values here too: this second init (now that
  // Pyodide is ready) would otherwise reset them to the scale preset.
  if (!window.app.cliAutoStart) {
    window.app.experimentTab.setInitialValues(true, window.app.restoredSession);
  }

  window.app.whatIfTab.resetUIAndSimulation();

  // Phone: the map is JS-sized to the chart column, so re-fit once the phone
  // layout and charts have settled (dvh/safe-area resolution, autoplay). Cheap
  // and phone-only; desktop already fits via initLabCharts + the resize listener.
  if (document.body.classList.contains("is-phone")) {
    requestAnimationFrame(() => fitMapToViewport());
    setTimeout(() => fitMapToViewport(), 300);
    setTimeout(() => fitMapToViewport(), 900);
  }

  // Phone showcase: auto-play the demo so a first-time visitor immediately sees
  // the city come alive. Only on the phone tier, only for a fresh visit (a
  // restored session keeps its own stopped/paused state), and never under
  // prefers-reduced-motion — where the "tap play" hint stays instead. Reuses
  // the normal Play path (clickFabButton) so run-state/provenance stay correct.
  if (
    !window.app.cliAutoStart &&
    document.body.classList.contains("is-phone") &&
    !window.app.restoredSession &&
    !window.matchMedia("(prefers-reduced-motion: reduce)").matches
  ) {
    setTimeout(() => window.app.experimentTab.clickFabButton(), 400);
  }

  // Auto-start simulation if in CLI mode
  if (window.app.cliAutoStart) {
    console.log('Pyodide ready - auto-starting CLI simulation...');
    // Enable buttons before auto-starting so they're clickable
    window.app.experimentTab.setLabTopControls(true);
    setTimeout(() => {
      window.app.experimentTab.clickFabButton();
      console.log('CLI simulation started');
    }, 1000); // Small delay to ensure everything is fully initialized
  }
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
