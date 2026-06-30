import { DOM_ELEMENTS } from "./dom-elements.js";
import { SimulationActions } from "./config.js";

// Event handler factories to reduce repetition
/*
 * The handler factory for most inputs returns the results of
 * an inline function that carries out a selection of common
 * operations, depending on the arguments in the call.
 */

export const createInputHandler = (
  settingName,
  options = {},
  dependencies = {},
) => {
  const {
    parser = parseFloat,
    requiresReset = false,
    customLogic = null,
    targetProperty = settingName,
    liveUpdateCondition = null,
  } = options;

  const { updateSettings, resetSimulation, updateSimulation } = dependencies;

  return function () {
    const value = parser(this.value);

    // Apply custom logic if provided
    if (customLogic) {
      value = customLogic.call(this, value);
    }

    // Update SimSettings through injected function
    if (updateSettings) {
      updateSettings(targetProperty, value);
    }

    // Update UI display
    const optionElement = DOM_ELEMENTS.options[settingName];
    if (optionElement) {
      optionElement.innerHTML = value;
    }

    // Call appropriate update function
    if (requiresReset && resetSimulation) {
      resetSimulation();
    } else if (updateSimulation) {
      updateSimulation(SimulationActions.Update);
    }
  };
};

/*
 * Special handler factory for inputs that need custom validation/processing
 * This just returns the results of a handler that is supplied in the
 * function call, so I think it's really just done for consistency
 */
const createSpecialInputHandler = (customHandler) => {
  return customHandler;
};

/*
 * Now define actual handlers for each of the UI elements.
 */

// input-handlers.js
export function setupInputHandlers(dependencies) {
  DOM_ELEMENTS.inputs.citySize.onchange = createInputHandler(
    "citySize",
    {
      parser: () => getLogSliderValue(DOM_ELEMENTS.inputs.citySize),
      requiresReset: true,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.vehicleCount.onchange = createInputHandler(
    "vehicleCount",
    { parser: () => getLogSliderValue(DOM_ELEMENTS.inputs.vehicleCount) },
    dependencies,
  );

  DOM_ELEMENTS.inputs.meanTripDistance.onchange = createInputHandler(
    "meanTripDistance",
    {
      parser: () => getLogSliderValue(DOM_ELEMENTS.inputs.meanTripDistance),
      requiresReset: true,
      /*
      customLogic: function (value) {
        // Apply the validation/clamping logic
        const clampedValue = Math.min(value, labSimSettings.citySize);

        // Update the actual input element to reflect the clamped value
        this.value = clampedValue;

        // Return the clamped value to be stored in settings
        return clampedValue;
      }, 
      */
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.requestRate.onchange = createInputHandler(
    "requestRate",
    {
      parser: () => getLogSliderValue(DOM_ELEMENTS.inputs.requestRate),
      requiresReset: false,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.inhomogeneity.onchange = createInputHandler(
    "inhomogeneity",
    {
      parser: parseFloat,
      requiresReset: false,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.idleVehiclesMoving.onchange = createInputHandler(
    "idleVehiclesMoving",
    {
      parser: parseFloat,
      requiresReset: false,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.meanVehicleSpeed.onchange = createInputHandler(
    "meanVehicleSpeed",
    {
      parser: parseFloat,
      requiresReset: true,
    },
    dependencies,
  );

  // Fares and wages
  // price is updated live (applies in non-city-scale mode; in city-scale mode the
  // core recomputes it from per-km/per-minute prices each block).
  DOM_ELEMENTS.inputs.price.onchange = createInputHandler(
    "price",
    {
      parser: parseFloat,
      requiresReset: false,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.perKmPrice.onchange = createInputHandler(
    "perKmPrice",
    {
      parser: parseFloat,
      requiresReset: true,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.perMinutePrice.onchange = createInputHandler(
    "perMinutePrice",
    {
      parser: parseFloat,
      requiresReset: true,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.demandElasticity.onchange = createInputHandler(
    "demandElasticity",
    {
      parser: parseFloat,
      requiresReset: false,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.platformCommission.onchange = createInputHandler(
    "platformCommission",
    {
      parser: parseFloat,
      requiresReset: false,
    },
    dependencies,
  );

  // reservation_wage is updated live (applies in non-city-scale mode; in
  // city-scale mode the core recomputes it from the cost inputs each block).
  DOM_ELEMENTS.inputs.reservationWage.onchange = createInputHandler(
    "reservationWage",
    {
      parser: parseFloat,
      requiresReset: false,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.perKmOpsCost.onchange = createInputHandler(
    "perKmOpsCost",
    {
      parser: parseFloat,
      requiresReset: true,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.perHourOpportunityCost.onchange = createInputHandler(
    "perHourOpportunityCost",
    {
      parser: parseFloat,
      requiresReset: true,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.animationDelay.onchange = createInputHandler(
    "animationDelay",
    {
      parser: parseFloat,
      requiresReset: false,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.smoothingWindow.onchange = createInputHandler(
    "smoothingWindow",
    {
      parser: parseInt,
      requiresReset: true,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.pickupTime.onchange = createInputHandler(
    "pickupTime",
    {
      parser: parseInt,
      requiresReset: true,
    },
    dependencies,
  );

  // Equilibrate checkbox handler
  DOM_ELEMENTS.checkboxes.equilibrate.onchange = function () {
    const value = this.checked;

    if (dependencies.updateSettings) {
      // Update boolean property for backward compatibility
      dependencies.updateSettings("equilibrate", value);
      // Update string property (the actual parameter used by worker.py)
      // When checked: equilibration="price", when unchecked: equilibration="none"
      dependencies.updateSettings("equilibration", value ? "price" : "none");
    }

    // Update all control visibility based on new equilibrate state
    if (dependencies.updateControlVisibility) {
      dependencies.updateControlVisibility();
    }

    // Apply the equilibration change live (no reset): worker.py update_options
    // pushes the new equilibration mode into the sim's target_state.
    if (dependencies.updateSimulation) {
      dependencies.updateSimulation(SimulationActions.Update);
    }
  };
} // setupInputHandlers

export const LOG_SLIDER_STEPS = 1000;

export function logSliderToValue(position, logMin, logMax, decimals = 0) {
  if (position <= 0) return logMin;
  const raw = logMin * Math.pow(logMax / logMin, position / LOG_SLIDER_STEPS);
  return decimals === 0 ? Math.round(raw) : parseFloat(raw.toFixed(decimals));
}

export function updateSliderLimitFill(slider, limitPct) {
  const track = slider.parentElement?.querySelector('.app-slider-track');
  if (!track) return;
  track.style.setProperty('--limit-percentage', `${limitPct}%`);
}

export function getLogSliderValue(element) {
  const logMin = parseFloat(element.dataset.logMin);
  const logMax = parseFloat(element.dataset.logMax);
  const decimals = parseInt(element.dataset.logDecimals || '0');
  return logSliderToValue(parseInt(element.value), logMin, logMax, decimals);
}

export function valueToLogSlider(value, logMin, logMax) {
  if (value <= logMin) return 0;
  return Math.round(Math.log(value / logMin) / Math.log(logMax / logMin) * LOG_SLIDER_STEPS);
}

/**
 * Recompute a single Material Design 3 slider's track fill (the
 * blue/grey divider) from its current min/max/value.
 *
 * The native thumb position is drawn by the browser directly from
 * slider.value/min/max, but the colored track fill is a CSS custom
 * property we maintain by hand. Anywhere code sets slider.value (or
 * min/max) without going through a user "input"/"change" event - e.g.
 * scale switches, config upload, session restore, keyboard shortcuts -
 * this must be called afterward or the track fill goes stale relative
 * to the thumb.
 * @param {HTMLInputElement} slider
 */
export function updateSliderFill(slider) {
  if (!slider) return;
  const track = slider.parentElement?.querySelector(".app-slider-track");
  if (!track) return;

  const min = parseFloat(slider.min) || 0;
  const max = parseFloat(slider.max) || 100;
  const value = parseFloat(slider.value) || 0;
  const percentage = ((value - min) / (max - min)) * 100;

  track.style.setProperty("--fill-percentage", `${percentage}%`);
}

/**
 * Initialize Material Design 3 slider visual elements
 * Updates the track fill and thumb position based on slider value
 */
export function initializeMD3Sliders() {
  const sliders = document.querySelectorAll(".app-slider");

  sliders.forEach((slider) => {
    // Update on load
    updateSliderFill(slider);

    // Update on change
    slider.addEventListener("input", () => updateSliderFill(slider));
    slider.addEventListener("change", () => updateSliderFill(slider));
  });
}

/**
 * Creates event listeners for the chart type radio buttons.
 * @param {function(string): void} onChartTypeChange - The
 * callback function to execute when the chart type changes.
 * It receives the new chart type value as an argument.
 */
export const createChartTypeRadioHandler = (onChartTypeChange) => {
  DOM_ELEMENTS.collections.chartTypeRadios.forEach((radio) =>
    radio.addEventListener("change", () => {
      // When a change occurs, simply call the provided function with the radio's value.
      if (radio.checked) {
        onChartTypeChange(radio.value);
      }
    }),
  );
};

export const createModeRadioHandler = (onModeChange) => {
  DOM_ELEMENTS.collections.uiModeRadios.forEach((radio) =>
    radio.addEventListener("change", () => {
      // When a change occurs, simply call the provided function with the radio's value.
      if (radio.checked) {
        onModeChange(radio.value);
      }
    }),
  );
};
