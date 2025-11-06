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
      parser: parseInt,
      requiresReset: true,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.vehicleCount.onchange = createInputHandler(
    "vehicleCount",
    {
      parser: parseInt,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.maxTripDistance.onchange = createInputHandler(
    "maxTripDistance",
    {
      parser: parseInt,
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
      parser: parseFloat,
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

  DOM_ELEMENTS.inputs.meanVehicleSpeed.onchange = createInputHandler(
    "meanVehicleSpeed",
    {
      parser: parseFloat,
      requiresReset: true,
    },
    dependencies,
  );

  // Fares and wages
  DOM_ELEMENTS.inputs.price.onchange = createInputHandler(
    "price",
    {
      parser: parseFloat,
      requiresReset: true,
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
      requiresReset: true,
    },
    dependencies,
  );

  DOM_ELEMENTS.inputs.reservationWage.onchange = createInputHandler(
    "reservationWage",
    {
      parser: parseFloat,
      requiresReset: true,
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

    if (dependencies.resetSimulation) {
      dependencies.resetSimulation();
    }
  };
} // setupInputHandlers

/**
 * Initialize Material Design 3 slider visual elements
 * Updates the track fill and thumb position based on slider value
 */
export function initializeMD3Sliders() {
  const sliders = document.querySelectorAll(".app-slider");

  sliders.forEach((slider) => {
    const container = slider.parentElement;
    const track = container.querySelector(".app-slider-track");

    function updateSliderVisuals() {
      const min = parseFloat(slider.min) || 0;
      const max = parseFloat(slider.max) || 100;
      const value = parseFloat(slider.value) || 0;
      const percentage = ((value - min) / (max - min)) * 100;

      // Update track fill
      track.style.setProperty("--fill-percentage", `${percentage}%`);
    }

    // Update on load
    updateSliderVisuals();

    // Update on change
    slider.addEventListener("input", updateSliderVisuals);
    slider.addEventListener("change", updateSliderVisuals);
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
