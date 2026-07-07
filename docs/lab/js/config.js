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

// Preset starting values. Selecting Village/Town/City simply loads one of these
// value sets as a starting point for a new simulation. A preset only overrides
// the values listed here; every other control keeps its default from
// SLIDER_CONFIG. Presets no longer set slider ranges or map display sizing.
// Geometry (vehicleCount, requestRate) is calibrated against the phase relation
// P3 = requestRate * meanTripDistance / vehicleCount (meanTripDistance =
// citySize / 2). Town and City target a healthy idle fraction with P3 ~= 0.45,
// but the Village is deliberately a *sparse* case: only 6 vehicles in an 8x8
// grid (a realistic village fleet), which settles around P1 ~= 0.34,
// P3 ~= 0.34 with a high but bounded wait fraction. Pushing the Village demand
// higher to lift P3 hits a P1 -> 0 collapse cliff (~requestRate 0.75), so we
// keep it at requestRate 0.5 where all four mode/equilibration combinations stay
// stable with P1 > 0. The Village also runs homogeneous (inhomogeneity 0) as it
// is too small for the two-zone split to be meaningful.
// The per-preset perHourOpportunityCost sets the Costs & Incomes entry/exit
// equilibrium; it decreases with city size to offset the fixed $3 base fare,
// which is a larger share of short (Village) fares. See the preset-calibration
// notes.
const PRESET_VALUES = {
  village: {
    scale: CITY_SCALE.VILLAGE,
    citySize: 8,
    vehicleCount: 6,
    requestRate: 0.5,
    meanTripDistance: 4,
    inhomogeneity: 0.0,
    perHourOpportunityCost: 13,
  },
  town: {
    scale: CITY_SCALE.TOWN,
    citySize: 24,
    vehicleCount: 120,
    requestRate: 5.0,
    meanTripDistance: 12,
    perHourOpportunityCost: 6,
  },
  city: {
    scale: CITY_SCALE.CITY,
    citySize: 48,
    vehicleCount: 1200,
    requestRate: 24.0,
    meanTripDistance: 24,
    perHourOpportunityCost: 4,
  },
};

/**
 * Build a full config object for a preset by combining the fixed slider ranges
 * (SLIDER_CONFIG) with the preset's starting values (PRESET_VALUES). Each
 * control ends up as { value, min, max, step }; only `value` differs between
 * presets. The `scale` label is carried through for the UI radio buttons.
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

// Merge fixed ranges with per-preset starting values
export const SCALE_CONFIGS = {
  village: buildScaleConfig("village"),
  town: buildScaleConfig("town"),
  city: buildScaleConfig("city"),
};

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
