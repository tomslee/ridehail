/**
 * KeyboardHandler - Centralized keyboard input management for browser
 *
 * Mirrors the Python KeyboardHandler architecture to provide consistent
 * keyboard handling across desktop and browser platforms.
 */

import { DOM_ELEMENTS } from "./dom-elements.js";
import { SimulationActions } from "./config.js";
import { appState } from "./app-state.js";
import { showSuccess } from "./toast.js";

export class KeyboardHandler {
  /**
   * Create a KeyboardHandler instance
   * @param {Object} app - Reference to main App instance for callbacks
   */
  constructor(app) {
    this.app = app;
    this.mappings = null;
    this.keyToAction = new Map();
    this.actionToMapping = new Map();
    this.setupListeners();
  }

  /**
   * Load keyboard mappings from JSON file
   */
  async loadMappings() {
    try {
      const response = await fetch("./js/keyboard-mappings.json");
      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }
      const data = await response.json();
      this.mappings = data.mappings;

      // Build lookup maps for performance
      this._buildCaches();

      return true;
    } catch (error) {
      console.error("✗ Failed to load keyboard mappings:", error);
      // Fall back to default behavior
      this.mappings = [];
      return false;
    }
  }

  /**
   * Build lookup caches for fast key->action mapping
   */
  _buildCaches() {
    this.keyToAction.clear();
    this.actionToMapping.clear();

    for (const mapping of this.mappings) {
      // Only cache browser-compatible mappings
      if (!mapping.platforms.includes("browser")) {
        continue;
      }

      this.actionToMapping.set(mapping.action, mapping);

      // Map each key to this action
      for (const key of mapping.keys) {
        this.keyToAction.set(key.toLowerCase(), mapping);
      }
    }
  }

  /**
   * Set up keyboard event listeners
   */
  setupListeners() {
    document.addEventListener("keyup", (event) => {
      this.handleKeyEvent(event);
    });
  }

  /**
   * Handle keyboard event
   * @param {KeyboardEvent} event - The keyboard event
   */
  handleKeyEvent(event) {
    // Special case: If help dialog is open, only handle Escape to close it
    const helpDialogOpen = DOM_ELEMENTS.keyboardHelp.dialog &&
                          !DOM_ELEMENTS.keyboardHelp.dialog.hasAttribute("hidden");
    if (helpDialogOpen) {
      if (event.key === "Escape") {
        event.preventDefault();
        this.app.hideKeyboardHelpDialog();
      }
      return; // Ignore all other keys while help is open
    }

    // Special case: Escape key exits full-screen if active
    if (
      event.key === "Escape" &&
      this.app.fullScreenManager &&
      this.app.fullScreenManager.isFullScreen()
    ) {
      event.preventDefault();
      this.app.fullScreenManager.exit();
      return;
    }

    // Ignore keypresses when focus is on input elements (except space for pause)
    const activeElement = document.activeElement;
    const isInputElement =
      activeElement &&
      (activeElement.tagName === "INPUT" ||
        activeElement.tagName === "TEXTAREA" ||
        activeElement.tagName === "SELECT" ||
        activeElement.isContentEditable);

    // Allow space key to work even in input elements (for pause/resume)
    if (isInputElement && event.key !== " ") {
      return;
    }

    const key = event.key.toLowerCase();

    // Get mapping for this key
    const mapping = this.keyToAction.get(key);
    if (!mapping) {
      return; // Key not mapped
    }

    // Prevent default behavior for mapped keys
    event.preventDefault();

    // Execute the action
    this.executeAction(mapping.action, mapping);
  }

  /**
   * Execute a keyboard action
   * @param {string} action - The action name
   * @param {Object} mapping - The key mapping object
   */
  executeAction(action, mapping) {
    switch (action) {
      case "pause":
        this._handlePause();
        break;

      case "step":
        this._handleStep();
        break;

      case "toggle_config_panel":
      case "toggle_zoom":
        this._handleToggleZoom();
        break;

      case "toggle_fullscreen":
        this._handleToggleFullScreen();
        break;

      case "decrease_vehicles":
        this._handleDecreaseVehicles(mapping.value);
        break;

      case "increase_vehicles":
        this._handleIncreaseVehicles(mapping.value);
        break;

      case "decrease_demand":
        this._handleDecreaseDemand(mapping.value);
        break;

      case "increase_demand":
        this._handleIncreaseDemand(mapping.value);
        break;

      case "decrease_animation_delay":
        this._handleDecreaseAnimationDelay(mapping.value);
        break;

      case "increase_animation_delay":
        this._handleIncreaseAnimationDelay(mapping.value);
        break;

      case "show_help":
      case "help":
        this._handleHelp();
        break;

      case "toggle_game":
        this._handleToggleGame();
        break;

      default:
        console.warn(`Unhandled action: ${action}`);
    }
  }

  /**
   * Handle pause/resume action
   */
  _handlePause() {
    // Delegate to app's FAB button handler
    this.app.experimentTab.clickFabButton();
  }

  /**
   * Handle single step action
   */
  _handleStep() {
    // Only step if simulation is paused (next step button enabled)
    if (!DOM_ELEMENTS.controls.nextStepButton.hasAttribute("disabled")) {
      appState.labSimSettings.action = SimulationActions.SingleStep;
      window.w.postMessage(appState.labSimSettings);
    }
  }

  /**
   * Handle toggle zoom action
   */
  _handleToggleZoom() {
    // Toggle visibility of zoom elements
    DOM_ELEMENTS.collections.zoom.forEach(function (element) {
      element.classList.toggle("hidden");
    });

    // Adjust column widths
    DOM_ELEMENTS.charts.chartColumn.classList.toggle("app-cell--6");
    DOM_ELEMENTS.charts.chartColumn.classList.toggle("app-cell--10");
    DOM_ELEMENTS.whatIf.chartColumn.classList.toggle("app-cell--8");
    DOM_ELEMENTS.whatIf.chartColumn.classList.toggle("app-cell--12");
  }

  /**
   * Handle toggle full-screen action
   */
  _handleToggleFullScreen() {
    if (!this.app.fullScreenManager) return;

    // If already in full-screen, exit
    if (this.app.fullScreenManager.isFullScreen()) {
      this.app.fullScreenManager.exit();
      return;
    }

    // Otherwise, get the currently visible chart canvas and enter
    const canvas = this._getCurrentVisibleCanvas();
    if (canvas) {
      this.app.fullScreenManager.toggle(canvas);
    }
  }

  /**
   * Get the currently visible chart canvas or container
   * @returns {HTMLCanvasElement|HTMLElement|null}
   */
  _getCurrentVisibleCanvas() {
    // Check if we're on Experience tab or What If tab
    const experimentTab = document.getElementById("scroll-tab-1");
    const whatIfTab = document.getElementById("scroll-tab-what-if");

    if (experimentTab && experimentTab.classList.contains("is-active")) {
      // Check if we're in stats mode - if so, return the chart-column container
      const chartTypeStats = document.getElementById("radio-chart-type-stats");
      if (chartTypeStats && chartTypeStats.checked) {
        // Stats mode - return chart column container for all charts together
        return document.getElementById("chart-column");
      } else {
        // Map mode - find the visible map canvas
        const canvases = experimentTab.querySelectorAll(".lab-chart-canvas");
        for (const canvas of canvases) {
          const parent = canvas.parentElement;
          if (
            parent &&
            !parent.hasAttribute("hidden") &&
            canvas.offsetParent !== null
          ) {
            return canvas;
          }
        }
      }
    } else if (whatIfTab && whatIfTab.classList.contains("is-active")) {
      // What If tab - return the chart column container for all charts together
      return document.getElementById("what-if-chart-column");
    }

    return null;
  }

  /**
   * Handle decrease vehicles action
   * @param {number} amount - Amount to decrease by
   */
  _handleDecreaseVehicles(amount) {
    const input = DOM_ELEMENTS.inputs.vehicleCount;
    const currentValue = parseInt(input.value);
    const newValue = Math.max(currentValue - amount, 0);

    // Update input and trigger change
    input.value = newValue;
    DOM_ELEMENTS.options.vehicleCount.innerHTML = newValue;
    appState.labSimSettings.vehicleCount = newValue;

    // Update simulation with new value (incremental, preserves progress)
    this.app.updateSimulationOptions(SimulationActions.Update);

    // Show feedback
    showSuccess(`Vehicles: ${newValue}`);
  }

  /**
   * Handle increase vehicles action
   * @param {number} amount - Amount to increase by
   */
  _handleIncreaseVehicles(amount) {
    const input = DOM_ELEMENTS.inputs.vehicleCount;
    const currentValue = parseInt(input.value);
    const newValue = currentValue + amount;

    // Update input and trigger change
    input.value = newValue;
    DOM_ELEMENTS.options.vehicleCount.innerHTML = newValue;
    appState.labSimSettings.vehicleCount = newValue;

    // Update simulation with new value (incremental, preserves progress)
    this.app.updateSimulationOptions(SimulationActions.Update);

    // Show feedback
    showSuccess(`Vehicles: ${newValue}`);
  }

  /**
   * Handle decrease demand action
   * @param {number} amount - Amount to decrease by
   */
  _handleDecreaseDemand(amount) {
    const input = DOM_ELEMENTS.inputs.requestRate;
    const currentValue = parseFloat(input.value);
    const newValue = Math.max((currentValue - amount).toFixed(1), 0);

    // Update input and trigger change
    input.value = newValue;
    DOM_ELEMENTS.options.requestRate.innerHTML = newValue;
    appState.labSimSettings.requestRate = parseFloat(newValue);

    // Update simulation with new value (incremental, preserves progress)
    this.app.updateSimulationOptions(SimulationActions.Update);

    // Show feedback
    showSuccess(`Demand: ${newValue}`);
  }

  /**
   * Handle increase demand action
   * @param {number} amount - Amount to increase by
   */
  _handleIncreaseDemand(amount) {
    const input = DOM_ELEMENTS.inputs.requestRate;
    const currentValue = parseFloat(input.value);
    const newValue = (currentValue + amount).toFixed(1);

    // Update input and trigger change
    input.value = newValue;
    DOM_ELEMENTS.options.requestRate.innerHTML = newValue;
    appState.labSimSettings.requestRate = parseFloat(newValue);

    // Update simulation with new value (incremental, preserves progress)
    this.app.updateSimulationOptions(SimulationActions.Update);

    // Show feedback
    showSuccess(`Demand: ${newValue}`);
  }

  /**
   * Handle decrease animation delay action
   * @param {number} amount - Amount to decrease by (seconds)
   */
  _handleDecreaseAnimationDelay(amount) {
    const input = DOM_ELEMENTS.inputs.animationDelay;
    const currentValueMs = parseInt(input.value);
    // Convert amount from seconds to milliseconds
    const amountMs = amount * 1000;
    const newValue = Math.max(currentValueMs - amountMs, 0);

    // Update input and display
    input.value = newValue;
    DOM_ELEMENTS.options.animationDelay.innerHTML = newValue;
    appState.labSimSettings.animationDelay = newValue;

    // Show feedback (convert to seconds for display)
    showSuccess(`Animation delay: ${(newValue / 1000).toFixed(2)}s`);
  }

  /**
   * Handle increase animation delay action
   * @param {number} amount - Amount to increase by (seconds)
   */
  _handleIncreaseAnimationDelay(amount) {
    const input = DOM_ELEMENTS.inputs.animationDelay;
    const currentValueMs = parseInt(input.value);
    // Convert amount from seconds to milliseconds
    const amountMs = amount * 1000;
    const newValue = Math.min(currentValueMs + amountMs, 1000); // Max 1000ms

    // Update input and display
    input.value = newValue;
    DOM_ELEMENTS.options.animationDelay.innerHTML = newValue;
    appState.labSimSettings.animationDelay = newValue;

    // Show feedback (convert to seconds for display)
    showSuccess(`Animation delay: ${(newValue / 1000).toFixed(2)}s`);
  }

  /**
   * Handle help action - show keyboard shortcuts dialog
   */
  _handleHelp() {
    // Save current pause state and pause simulation while help is shown
    const isPaused = !DOM_ELEMENTS.controls.nextStepButton.hasAttribute("disabled");
    this.app._helpPreviousPauseState = isPaused;

    // Pause simulation if not already paused
    if (!isPaused) {
      this.app.experimentTab.clickFabButton();
    }

    const browserMappings = this.getBrowserMappings();

    // Build shortcuts list HTML
    let html = "";
    for (const mapping of browserMappings) {
      const keys = mapping.keys.join(" / ");
      html += `<div class="keyboard-shortcut-item"><span class="keyboard-shortcut-keys">${keys}</span><span class="keyboard-shortcut-description"> - ${mapping.description}</span></div>`;
    }

    // Update dialog content
    DOM_ELEMENTS.keyboardHelp.shortcutsList.innerHTML = html;

    // Show dialog
    DOM_ELEMENTS.keyboardHelp.dialog.removeAttribute("hidden");
  }

  /**
   * Handle toggle game tab action
   */
  _handleToggleGame() {
    const gameTab = document.getElementById("tab-game");
    if (gameTab) {
      gameTab.classList.toggle("tab-hidden");

      // Show feedback
      const isVisible = !gameTab.classList.contains("tab-hidden");
      showSuccess(isVisible ? "Game tab shown" : "Game tab hidden");
    }
  }

  /**
   * Get mapping for a specific key
   * @param {string} key - The keyboard key
   * @returns {Object|null} The mapping object or null
   */
  getMappingForKey(key) {
    return this.keyToAction.get(key.toLowerCase()) || null;
  }

  /**
   * Get mapping for a specific action
   * @param {string} action - The action name
   * @returns {Object|null} The mapping object or null
   */
  getMappingForAction(action) {
    return this.actionToMapping.get(action) || null;
  }

  /**
   * Get all mappings for browser platform
   * @returns {Array} Array of mapping objects
   */
  getBrowserMappings() {
    if (!this.mappings) {
      return [];
    }
    return this.mappings.filter((m) => m.platforms.includes("browser"));
  }

  /**
   * Generate help text for keyboard shortcuts
   * @returns {string} Formatted help text
   */
  generateHelpText() {
    const browserMappings = this.getBrowserMappings();

    let text = "KEYBOARD SHORTCUTS:\n";
    text += "=".repeat(50) + "\n";

    for (const mapping of browserMappings) {
      const keys = mapping.keys.join("/");
      text += `  ${keys.padEnd(12)} - ${mapping.description}\n`;
    }

    text += "=".repeat(50);
    return text;
  }
}
