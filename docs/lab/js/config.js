import { DOM_ELEMENTS } from "./dom-elements.js";
import { SimulationActions, CITY_SCALE, CHART_TYPES } from "./constants.js";

// Re-export constants for backward compatibility
export { SimulationActions, CITY_SCALE, CHART_TYPES };

// Fixed slider ranges (min/max/step) and default values for every control.
//
// These ranges are the SAME for every preset: the Village/Town/City choice no
// longer narrows or widens a slider's range. All of these controls are now
// continuous across their full range, so a preset only supplies a starting
// *value* (see PRESET_VALUES below), never a range.
const SLIDER_CONFIG = {
  // The first four are log-scale sliders whose actual range lives in the HTML
  // (data-log-min / data-log-max in components/experiment-tab.html); the
  // min/max here mirror those for reference only.
  citySize: { value: 8, min: 4, max: 64, step: 2 },
  vehicleCount: { value: 8, min: 1, max: 10000, step: 1 },
  requestRate: { value: 1.0, min: 0.1, max: 300, step: 0.1 },
  meanTripDistance: { value: 4, min: 1, max: 32, step: 1 },
  inhomogeneity: { value: 0.5, min: 0.0, max: 1.0, step: 0.1 },
  idleVehiclesMoving: { value: 1.0, min: 0.0, max: 1.0, step: 0.05 },
  price: { value: 1.2, min: 0.0, max: 4.0, step: 0.1 },
  platformCommission: { value: 0.25, min: 0.0, max: 0.5, step: 0.01 },
  reservationWage: { value: 0.35, min: 0.0, max: 1.0, step: 0.05 },
  demandElasticity: { value: 0.0, min: 0.0, max: 2.0, step: 0.1 },
  meanVehicleSpeed: { value: 30.0, min: 10.0, max: 50.0, step: 5 },
  perKmPrice: { value: 0.8, min: 0.0, max: 1.2, step: 0.1 },
  perMinutePrice: { value: 0.18, min: 0.0, max: 0.4, step: 0.02 },
  baseFare: { value: 3.0, min: 0.0, max: 10.0, step: 0.5 },
  perKmOpsCost: { value: 0.3, min: 0.0, max: 2.0, step: 0.1 },
  perHourOpportunityCost: { value: 6, min: 0, max: 30, step: 1 },
  animationDelay: { value: 300, min: 0, max: 1000, step: 10 },
  smoothingWindow: { value: 24, min: 2, max: 64, step: 2 },
  pickupTime: { value: 1, min: 0, max: 5, step: 1 },
};

// Preset scale labels. Selecting Village/Town/City loads a starting-point set of
// parameter values. Those VALUES are no longer kept here: they are the single
// source of truth in the Python package (ridehail/presets.py, shared with the
// desktop `--preset` CLI option) and arrive over postMessage once Pyodide has
// loaded, via applyPythonPresets() below (worker.py::get_presets ->
// webworker.js). Until then SCALE_CONFIGS holds the generic SLIDER_CONFIG
// defaults as a bootstrap; the loading overlay hides the UI during that window,
// and the DOM controls are only populated (setInitialValues) after the presets
// have been applied. Only the `scale` label needs to be known synchronously.
const PRESET_VALUES = {
  village: { scale: CITY_SCALE.VILLAGE },
  town: { scale: CITY_SCALE.TOWN },
  city: { scale: CITY_SCALE.CITY },
};

/**
 * Build a full config object for a preset by combining the fixed slider ranges
 * (SLIDER_CONFIG) with the preset's starting values. Each control ends up as
 * { value, min, max, step }. Before the Python presets arrive, `value` is the
 * generic SLIDER_CONFIG default (identical across scales); applyPythonPresets()
 * later overwrites each `value` with the authoritative per-scale number. The
 * `scale` label is carried through for the UI radio buttons.
 */
function buildScaleConfig(presetName) {
  const presetValues = PRESET_VALUES[presetName];
  const config = { scale: presetValues.scale };
  for (const [param, range] of Object.entries(SLIDER_CONFIG)) {
    const overrideValue = presetValues[param];
    config[param] = {
      ...range,
      value: overrideValue !== undefined ? overrideValue : range.value,
    };
  }
  return config;
}

// Fixed slider ranges, with generic bootstrap values overwritten per-scale by
// applyPythonPresets() once the Python presets arrive.
export const SCALE_CONFIGS = {
  village: buildScaleConfig("village"),
  town: buildScaleConfig("town"),
  city: buildScaleConfig("city"),
};

/**
 * Overlay the authoritative preset values from Python (ridehail/presets.py, via
 * worker.py::get_presets) onto SCALE_CONFIGS. Called once, from the "Pyodide
 * loaded" message handler, before the DOM controls are first populated. Only
 * `value` is changed; the fixed min/max/step ranges stay as defined here. Keys
 * with no matching SLIDER_CONFIG control are ignored.
 *
 * @param {Object} pyPresets - { village: { citySize: 8, ... }, town: {...}, ... }
 */
export function applyPythonPresets(pyPresets) {
  if (!pyPresets) {
    console.error(
      "applyPythonPresets: no preset values received from Python; " +
        "presets will show generic default values.",
    );
    return;
  }
  for (const [scale, values] of Object.entries(pyPresets)) {
    const scaleConfig = SCALE_CONFIGS[scale];
    if (!scaleConfig || !values) continue;
    for (const [param, value] of Object.entries(values)) {
      if (scaleConfig[param] && typeof scaleConfig[param] === "object") {
        scaleConfig[param].value = value;
      }
    }
  }
}

/*
 * The settings Config lists each setting for a SimSettings object and either
 * provides a value or specifies that it comes from the UI (with some
 * guidance information in the form of a parser)
 */
export const LAB_SETTINGS_CONFIG = {
  name: { value: "labSimSettings" },
  citySize: { source: "input", element: "citySize", parser: parseInt },
  vehicleCount: { source: "input", element: "vehicleCount", parser: parseInt },
  requestRate: { source: "input", element: "requestRate", parser: parseFloat },
  smoothingWindow: {
    source: "input",
    element: "smoothingWindow",
    parser: parseInt,
  },
  useCostsAndIncomes: { value: false },
  platformCommission: {
    source: "input",
    element: "platformCommission",
    parser: parseFloat,
  },
  price: { source: "input", element: "price", parser: parseFloat },
  reservationWage: {
    source: "input",
    element: "reservationWage",
    parser: parseFloat,
  },
  meanVehicleSpeed: {
    source: "input",
    element: "meanVehicleSpeed",
    parser: parseFloat,
  },
  perKmPrice: { source: "input", element: "perKmPrice", parser: parseFloat },
  perMinutePrice: {
    source: "input",
    element: "perMinutePrice",
    parser: parseFloat,
  },
  baseFare: { source: "input", element: "baseFare", parser: parseFloat },
  perKmOpsCost: {
    source: "input",
    element: "perKmOpsCost",
    parser: parseFloat,
  },
  perHourOpportunityCost: {
    source: "input",
    element: "perHourOpportunityCost",
    parser: parseFloat,
  },
  animationDelay: {
    source: "input",
    element: "animationDelay",
    parser: parseFloat,
  },
  pickupTime: {
    source: "input",
    element: "pickupTime",
    parser: parseInt,
  },
  action: {
    source: "custom",
    getter: () => {
      const icon =
        DOM_ELEMENTS.controls.fabButton.querySelector(".material-icons");
      return icon
        ? icon.innerHTML
        : DOM_ELEMENTS.controls.fabButton.firstElementChild.innerHTML;
    },
  },
  chartType: {
    source: "custom",
    getter: () =>
      document.querySelector('input[type="radio"][name="chart-type"]:checked')
        ?.value || "map",
  },
};
