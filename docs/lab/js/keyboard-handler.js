/**
 * KeyboardHandler - Centralized keyboard input management for browser
 *
 * Mirrors the Python KeyboardHandler architecture to provide consistent
 * keyboard handling across desktop and browser platforms.
 */

import { DOM_ELEMENTS } from "./dom-elements.js";
import { SimulationActions } from "./config.js";
import { appState } from "./app-state.js";

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
            const response = await fetch('./js/keyboard-mappings.json');
            const data = await response.json();
            this.mappings = data.mappings;

            // Build lookup maps for performance
            this._buildCaches();

            console.log(`Keyboard mappings loaded: ${this.mappings.length} actions`);
        } catch (error) {
            console.error('Failed to load keyboard mappings:', error);
            // Fall back to default behavior
            this.mappings = [];
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
            if (!mapping.platforms.includes('browser')) {
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
        const key = event.key.toLowerCase();

        // Get mapping for this key
        const mapping = this.keyToAction.get(key);
        if (!mapping) {
            return;  // Key not mapped
        }

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
            case 'pause':
                this._handlePause();
                break;

            case 'step':
                this._handleStep();
                break;

            case 'toggle_zoom':
                this._handleToggleZoom();
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
        this.app.clickFabButton(
            DOM_ELEMENTS.controls.fabButton,
            appState.labSimSettings
        );
    }

    /**
     * Handle single step action
     */
    _handleStep() {
        // Only step if simulation is paused (next step button enabled)
        if (!DOM_ELEMENTS.controls.nextStepButton.hasAttribute("disabled")) {
            appState.labSimSettings.action = SimulationActions.SingleStep;
            w.postMessage(appState.labSimSettings);
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
        return this.mappings.filter(m => m.platforms.includes('browser'));
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
