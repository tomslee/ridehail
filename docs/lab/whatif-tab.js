/*
 * What If Tab Controller
 * Handles all functionality specific to the What If comparison tab
 * Created: 2024-12 - Refactored from app.js
 */

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
import { SimulationActions, CHART_TYPES } from "./js/config.js";
import { WhatIfSimSettingsDefault } from "./js/sim-settings.js";
import { appState } from "./js/app-state.js";
import {
  addDoubleClickHandler,
  addMobileTouchHandlers,
} from "./js/fullscreen.js";

const whatIfCanvasIDList = [
  "what-if-phases-chart-canvas",
  "what-if-income-chart-canvas",
  "what-if-wait-chart-canvas",
  "what-if-n-chart-canvas",
  "what-if-platform-chart-canvas",
];

export class WhatIfTab {
  constructor(app, fullScreenManager) {
    this.app = app;
    this.fullScreenManager = fullScreenManager;
  }

  /**
   * Setup What If-specific event handlers
   * Called during app initialization
   */
  setupEventHandlers() {
    // Price adjustment buttons
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
                appState.whatIfSimSettingsComparison.platformCommission * 20,
              ) / 20;
            break;
          case "what-if-commission-add":
            appState.whatIfSimSettingsComparison.platformCommission += 0.05;
            appState.whatIfSimSettingsComparison.platformCommission =
              Math.round(
                appState.whatIfSimSettingsComparison.platformCommission * 20,
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
                appState.whatIfSimSettingsComparison.reservationWage * 100,
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
                appState.whatIfSimSettingsComparison.reservationWage * 100,
              ) / 100;
            break;
          case "what-if-demand-remove":
            appState.whatIfSimSettingsComparison.requestRate -= 0.5;
            appState.whatIfSimSettingsComparison.requestRate =
              Math.round(
                appState.whatIfSimSettingsComparison.requestRate * 10,
              ) / 10;
            break;
          case "what-if-demand-add":
            appState.whatIfSimSettingsComparison.requestRate += 0.5;
            appState.whatIfSimSettingsComparison.requestRate =
              Math.round(
                appState.whatIfSimSettingsComparison.requestRate * 10,
              ) / 10;
            break;
        }
        this.updateTopControlValues();
      });
    });

    // Baseline radio buttons (preset vs lab settings)
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
            appState.labSimSettings,
          );
          appState.whatIfSimSettingsBaseline.chartType = CHART_TYPES.WHAT_IF;
          appState.whatIfSimSettingsBaseline.name = "whatIfSimSettingsBaseline";
          appState.whatIfSimSettingsBaseline.timeBlocks = 200;
          appState.whatIfSimSettingsBaseline.frameIndex = 0;
          appState.whatIfSimSettingsBaseline.animationDelay = 0;
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
            appState.whatIfSimSettingsBaseline,
          );
          appState.whatIfSimSettingsComparison.name =
            "whatIfSimSettingsComparison";
        }
        this.updateTopControlValues();
      }),
    );
  }

  /**
   * What If button state management functions
   * Clear, explicit state transitions for the What If workflow
   */

  setButtonsInitialState() {
    // Initial state: baseline enabled, comparison disabled
    const baselineIcon =
      DOM_ELEMENTS.whatIf.baselineFabButton.querySelector(".material-icons");
    const baselineText =
      DOM_ELEMENTS.whatIf.baselineFabButton.querySelector(".app-button__text");
    const comparisonIcon =
      DOM_ELEMENTS.whatIf.comparisonFabButton.querySelector(".material-icons");
    const comparisonText =
      DOM_ELEMENTS.whatIf.comparisonFabButton.querySelector(
        ".app-button__text",
      );

    DOM_ELEMENTS.whatIf.baselineFabButton.removeAttribute("disabled");
    baselineIcon.innerHTML = SimulationActions.Play;
    // if (baselineText) baselineText.textContent = 'Run Baseline';

    DOM_ELEMENTS.whatIf.comparisonFabButton.setAttribute("disabled", "");
    comparisonIcon.innerHTML = SimulationActions.Play;
    // if (comparisonText) comparisonText.textContent = 'Run Comparison';

    // Enable reset button
    DOM_ELEMENTS.whatIf.resetButton.removeAttribute("disabled");

    // Disable comparison controls initially
    DOM_ELEMENTS.whatIf.setComparisonButtons.forEach((el) =>
      el.setAttribute("disabled", ""),
    );
    DOM_ELEMENTS.whatIf.baselineRadios.forEach(
      (radio) => (radio.disabled = false),
    );
  }

  setButtonsBaselineRunning() {
    // During baseline: baseline enabled (for pause), comparison disabled
    const baselineIcon =
      DOM_ELEMENTS.whatIf.baselineFabButton.querySelector(".material-icons");
    const baselineText =
      DOM_ELEMENTS.whatIf.baselineFabButton.querySelector(".app-button__text");

    baselineIcon.innerHTML = SimulationActions.Pause;
    if (baselineText) baselineText.textContent = "Baseline";

    DOM_ELEMENTS.whatIf.baselineFabButton.removeAttribute("disabled");
    DOM_ELEMENTS.whatIf.comparisonFabButton.setAttribute("disabled", "");

    // Disable reset button during simulation
    DOM_ELEMENTS.whatIf.resetButton.setAttribute("disabled", "");

    // Disable controls during simulation
    DOM_ELEMENTS.whatIf.setComparisonButtons.forEach((el) =>
      el.setAttribute("disabled", ""),
    );
    DOM_ELEMENTS.whatIf.baselineRadios.forEach(
      (radio) => (radio.disabled = true),
    );
  }

  setButtonsBaselinePaused() {
    // Baseline paused: baseline enabled (to resume), comparison disabled
    const baselineIcon =
      DOM_ELEMENTS.whatIf.baselineFabButton.querySelector(".material-icons");
    const baselineText =
      DOM_ELEMENTS.whatIf.baselineFabButton.querySelector(".app-button__text");

    baselineIcon.innerHTML = SimulationActions.Play;
    // if (baselineText) baselineText.textContent = 'Run Baseline';

    DOM_ELEMENTS.whatIf.baselineFabButton.removeAttribute("disabled");
    DOM_ELEMENTS.whatIf.comparisonFabButton.setAttribute("disabled", "");

    // Enable reset button
    DOM_ELEMENTS.whatIf.resetButton.removeAttribute("disabled");

    // Disable comparison controls (baseline not complete)
    DOM_ELEMENTS.whatIf.setComparisonButtons.forEach((el) =>
      el.setAttribute("disabled", ""),
    );
    DOM_ELEMENTS.whatIf.baselineRadios.forEach(
      (radio) => (radio.disabled = false),
    );
  }

  setButtonsBaselineComplete() {
    // Baseline complete: baseline disabled, comparison enabled
    const baselineIcon =
      DOM_ELEMENTS.whatIf.baselineFabButton.querySelector(".material-icons");
    const baselineText =
      DOM_ELEMENTS.whatIf.baselineFabButton.querySelector(".app-button__text");
    const comparisonIcon =
      DOM_ELEMENTS.whatIf.comparisonFabButton.querySelector(".material-icons");
    const comparisonText =
      DOM_ELEMENTS.whatIf.comparisonFabButton.querySelector(
        ".app-button__text",
      );

    DOM_ELEMENTS.whatIf.baselineFabButton.setAttribute("disabled", "");
    baselineIcon.innerHTML = SimulationActions.Play;
    // if (baselineText) baselineText.textContent = 'Run Baseline';

    DOM_ELEMENTS.whatIf.comparisonFabButton.removeAttribute("disabled");
    comparisonIcon.innerHTML = SimulationActions.Play;
    // if (comparisonText) comparisonText.textContent = 'Run Comparison';

    // Enable reset button
    DOM_ELEMENTS.whatIf.resetButton.removeAttribute("disabled");

    // Enable comparison controls
    DOM_ELEMENTS.whatIf.setComparisonButtons.forEach((el) =>
      el.removeAttribute("disabled"),
    );
  }

  setButtonsComparisonRunning() {
    // During comparison: comparison enabled (for pause), baseline disabled
    const comparisonIcon =
      DOM_ELEMENTS.whatIf.comparisonFabButton.querySelector(".material-icons");
    const comparisonText =
      DOM_ELEMENTS.whatIf.comparisonFabButton.querySelector(
        ".app-button__text",
      );

    comparisonIcon.innerHTML = SimulationActions.Pause;
    // if (comparisonText) comparisonText.textContent = 'Run Comparison';

    DOM_ELEMENTS.whatIf.baselineFabButton.setAttribute("disabled", "");
    DOM_ELEMENTS.whatIf.comparisonFabButton.removeAttribute("disabled");

    // Disable reset button during simulation
    DOM_ELEMENTS.whatIf.resetButton.setAttribute("disabled", "");

    // Disable controls during simulation
    DOM_ELEMENTS.whatIf.setComparisonButtons.forEach((el) =>
      el.setAttribute("disabled", ""),
    );
  }

  setButtonsComparisonPaused() {
    // Comparison paused: comparison enabled (to resume), baseline disabled
    const comparisonIcon =
      DOM_ELEMENTS.whatIf.comparisonFabButton.querySelector(".material-icons");
    const comparisonText =
      DOM_ELEMENTS.whatIf.comparisonFabButton.querySelector(
        ".app-button__text",
      );

    comparisonIcon.innerHTML = SimulationActions.Play;
    // if (comparisonText) comparisonText.textContent = 'Run Comparison';

    DOM_ELEMENTS.whatIf.baselineFabButton.setAttribute("disabled", "");
    DOM_ELEMENTS.whatIf.comparisonFabButton.removeAttribute("disabled");

    // Enable reset button
    DOM_ELEMENTS.whatIf.resetButton.removeAttribute("disabled");

    // Enable comparison controls
    DOM_ELEMENTS.whatIf.setComparisonButtons.forEach((el) =>
      el.removeAttribute("disabled"),
    );
  }

  setButtonsComparisonComplete() {
    // Comparison complete: baseline disabled, comparison enabled (allow re-run)
    const comparisonIcon =
      DOM_ELEMENTS.whatIf.comparisonFabButton.querySelector(".material-icons");
    const comparisonText =
      DOM_ELEMENTS.whatIf.comparisonFabButton.querySelector(
        ".app-button__text",
      );

    comparisonIcon.innerHTML = SimulationActions.Play;
    // if (comparisonText) comparisonText.textContent = 'Run Comparison';

    DOM_ELEMENTS.whatIf.baselineFabButton.setAttribute("disabled", "");
    DOM_ELEMENTS.whatIf.comparisonFabButton.removeAttribute("disabled");

    // Enable reset button
    DOM_ELEMENTS.whatIf.resetButton.removeAttribute("disabled");

    // Enable comparison controls
    DOM_ELEMENTS.whatIf.setComparisonButtons.forEach((el) =>
      el.removeAttribute("disabled"),
    );
  }

  /**
   * Handle click on What If FAB buttons (baseline or comparison)
   * @param {HTMLElement} button - The button that was clicked
   * @param {Object} simSettings - The simulation settings to use
   */
  clickFabButton(button, simSettings) {
    // Read the button icon to see what the current state is.
    // If it is showing "play arrow", then the simulation is currently paused,
    // so the action to take is to play.
    // If it is showing "pause", then the simulation is currently running,
    // so the action to take is to pause.
    const icon =
      button.querySelector(".material-icons") || button.firstElementChild;
    if (icon.innerHTML == SimulationActions.Play) {
      // If the button is showing "Play", then the action to take is play
      simSettings.action = SimulationActions.Play;

      // For comparison button, check if we need to reset from a completed state
      if (button == DOM_ELEMENTS.whatIf.comparisonFabButton) {
        if (simSettings.frameIndex >= simSettings.timeBlocks) {
          // Simulation has completed, reset it before starting again
          simSettings.frameIndex = 0;
          simSettings.action = SimulationActions.Reset;
          w.postMessage(simSettings);
          // Now set action back to Play for the subsequent run
          simSettings.action = SimulationActions.Play;
        }
        this.setButtonsComparisonRunning();
      } else if (button == DOM_ELEMENTS.whatIf.baselineFabButton) {
        this.setButtonsBaselineRunning();
      }
    } else {
      // The button should be showing "Pause", and the action to take is to pause
      simSettings.action = SimulationActions.Pause;

      if (button == DOM_ELEMENTS.whatIf.baselineFabButton) {
        // Paused baseline: allow resuming baseline
        this.setButtonsBaselinePaused();
      } else if (button == DOM_ELEMENTS.whatIf.comparisonFabButton) {
        // Paused comparison: allow resuming comparison
        this.setButtonsComparisonPaused();
      }
    }
    w.postMessage(simSettings);
  }

  /**
   * Reset UI and simulation to initial state
   */
  resetUIAndSimulation() {
    DOM_ELEMENTS.whatIf.blockCount.innerHTML = 0;
    appState.whatIfSimSettingsComparison.action = SimulationActions.Reset;
    w.postMessage(appState.whatIfSimSettingsComparison);

    // Set initial button states
    this.setButtonsInitialState();

    // Reset baseline radio selection
    DOM_ELEMENTS.whatIf.baselinePreset.checked = true;

    // Reset settings to defaults
    appState.whatIfSimSettingsBaseline = new WhatIfSimSettingsDefault();
    appState.whatIfSimSettingsBaseline.name = "whatIfSimSettingsBaseline";
    appState.whatIfSimSettingsComparison = new WhatIfSimSettingsDefault();
    appState.whatIfSimSettingsComparison.name = "whatIfSimSettingsComparison";

    this.updateTopControlValues();

    // Charts
    // Remove the canvases
    document
      .querySelectorAll(".what-if-chart-canvas")
      .forEach((e) => e.remove());

    // Create new canvases
    let i = 0;
    const self = this; // Preserve 'this' context for inner function
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

    // Add full-screen handler to the what-if-chart-column container (not individual charts)
    const whatIfChartColumn = DOM_ELEMENTS.whatIf.chartColumn;
    if (whatIfChartColumn) {
      addDoubleClickHandler(whatIfChartColumn, self.fullScreenManager);
      addMobileTouchHandlers(whatIfChartColumn, self.fullScreenManager);
    }

    initWhatIfNChart(appState.whatIfUISettings);
    initWhatIfDemandChart(appState.whatIfUISettings);
    initWhatIfPhasesChart(appState.whatIfUISettings);
    initWhatIfIncomeChart(appState.whatIfUISettings);
    initWhatIfWaitChart(appState.whatIfUISettings);
    initWhatIfPlatformChart(appState.whatIfUISettings);
    initWhatIfTables();
  }

  /**
   * Update the top control values display (price, commission, etc.)
   */
  updateTopControlValues() {
    DOM_ELEMENTS.whatIf.price.innerHTML = new Intl.NumberFormat("EN-CA", {
      style: "currency",
      currency: "CAD",
    }).format(appState.whatIfSimSettingsComparison.price);
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
    DOM_ELEMENTS.whatIf.price.style.backgroundColor = backgroundColor;
    if (temperature < -0.01 || temperature > 0.01) {
      DOM_ELEMENTS.whatIf.price.style.fontWeight = "bold";
    } else {
      DOM_ELEMENTS.whatIf.price.style.fontWeight = "normal";
    }
    DOM_ELEMENTS.whatIf.commission.innerHTML =
      Math.round(
        appState.whatIfSimSettingsComparison.platformCommission * 100,
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
    DOM_ELEMENTS.whatIf.commission.style.backgroundColor = backgroundColor;
    if (temperature < -0.01 || temperature > 0.01) {
      DOM_ELEMENTS.whatIf.commission.style.fontWeight = "bold";
    } else {
      DOM_ELEMENTS.whatIf.commission.style.fontWeight = "normal";
    }
    document.getElementById("what-if-cap").innerHTML =
      appState.whatIfSimSettingsComparison.vehicleCount;
    DOM_ELEMENTS.whatIf.reservationWage.innerHTML = new Intl.NumberFormat(
      "EN-CA",
      {
        style: "currency",
        currency: "CAD",
      },
    ).format(appState.whatIfSimSettingsComparison.reservationWage * 60);
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
    DOM_ELEMENTS.whatIf.reservationWage.style.backgroundColor = backgroundColor;
    if (temperature < -0.001 || temperature > 0.001) {
      DOM_ELEMENTS.whatIf.reservationWage.style.fontWeight = "bold";
    } else {
      DOM_ELEMENTS.whatIf.reservationWage.style.fontWeight = "normal";
    }
    DOM_ELEMENTS.whatIf.demand.innerHTML = Math.round(
      appState.whatIfSimSettingsComparison.requestRate * 60,
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
    DOM_ELEMENTS.whatIf.demand.style.backgroundColor = backgroundColor;
    if (temperature < -0.01 || temperature > 0.01) {
      DOM_ELEMENTS.whatIf.demand.style.fontWeight = "bold";
    } else {
      DOM_ELEMENTS.whatIf.demand.style.fontWeight = "normal";
    }
  }

  /**
   * Update baseline block counter display
   * @param {Map} results - Results from Python simulation
   */
  updateBaselineBlockCounter(results) {
    const frameIndex = results.get("frame");
    if (frameIndex % 10 === 0) {
      // blockIndex should match frameIndex for stats
      const blockIndex = frameIndex;
      DOM_ELEMENTS.whatIf.blockCount.innerHTML = `${blockIndex}/${results.get(
        "time_blocks",
      )}`;
      appState.whatIfSimSettingsBaseline.frameIndex = frameIndex;
    }
    if (
      frameIndex >= appState.whatIfSimSettingsBaseline.timeBlocks &&
      appState.whatIfSimSettingsBaseline.timeBlocks !== 0
    ) {
      appState.whatIfSimSettingsBaseline.action = SimulationActions.Done;
      appState.setBaselineData(results);
      w.postMessage(appState.whatIfSimSettingsBaseline);
      this.setButtonsBaselineComplete();
    }
  }

  /**
   * Update comparison block counter display
   * @param {Map} results - Results from Python simulation
   */
  updateComparisonBlockCounter(results) {
    const frameIndex = results.get("frame");
    if (frameIndex % 10 === 0) {
      const blockIndex = frameIndex;
      DOM_ELEMENTS.whatIf.blockCount.innerHTML = `${frameIndex} / ${results.get(
        "time_blocks",
      )}`;
      appState.whatIfSimSettingsComparison.frameIndex = frameIndex;
    }
    if (
      frameIndex >= appState.whatIfSimSettingsComparison.timeBlocks &&
      appState.whatIfSimSettingsComparison.timeBlocks !== 0
    ) {
      appState.whatIfSimSettingsComparison.action = SimulationActions.Done;
      w.postMessage(appState.whatIfSimSettingsComparison);
      this.setButtonsComparisonComplete();
    }
  }
}
