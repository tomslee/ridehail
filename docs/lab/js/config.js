import { DOM_ELEMENTS } from "./dom-elements.js";

export const colors = new Map([
  // Map
  ["ROAD", "rgba(232, 232, 232, 0.5)"],
  // Vehicles
  ["P1", "rgba(100, 149, 237, 0.5)"],
  ["P2", "rgba(215, 142, 0, 0.5)"],
  ["P3", "rgba(60, 179, 113, 0.5)"],
  ["IDLE", "rgba(100, 149, 237, 0.5)"],
  ["DISPATCHED", "rgba(215, 142, 0, 0.5)"],
  ["WITH_RIDER", "rgba(60, 179, 113, 0.5)"],
  ["PURPLE", "rgba(160, 109, 153, 0.5)"],
  ["SURPLUS", "rgba(237, 100, 149, 0.5)"],
  // Trips
  ["UNASSIGNED", "rgba(237, 100, 149, 0.5)"],
  ["WAITING", "rgba(237, 100, 149, 0.5)"],
  ["RIDING", "rgba(60, 179, 113, 0.5)"],
]);

export const SimulationActions = {
  Play: "play_arrow",
  Pause: "pause",
  Reset: "reset",
  SingleStep: "single-step",
  Update: "update",
  UpdateDisplay: "updateDisplay",
  Done: "pause",
};

export const CITY_SCALE = {
  VILLAGE: "village",
  TOWN: "town",
  CITY: "city",
};

// Configuration defaults, including each and every input control
export const SCALE_CONFIGS = {
  village: {
    scale: CITY_SCALE.VILLAGE,
    citySize: { value: 8, min: 4, max: 16, step: 2 },
    vehicleCount: { value: 8, min: 1, max: 16, step: 1 },
    requestRate: { value: 0.5, min: 0, max: 2, step: 0.1 },
    maxTripDistance: { value: 4, min: 1, max: 4, step: 1 },
    inhomogeneity: { value: 0.0, min: 0.0, max: 1.0, step: 0.1 },
    price: { value: 1.2, min: 0.0, max: 4.0, step: 0.1 },
    platformCommission: { value: 0.25, min: 0.0, max: 0.5, step: 0.01 },
    reservationWage: { value: 0.35, min: 0.0, max: 1.0, step: 0.05 },
    demandElasticity: { value: 0.0, min: 0.0, max: 2.0, step: 0.1 },
    meanVehicleSpeed: { value: 0.0, min: 0.0, max: 2.0, step: 0.1 },
    perKmPrice: { value: 0.8, min: 0.0, max: 1.2, step: 0.1 },
    perMinutePrice: { value: 0.2, min: 0.0, max: 0.4, step: 0.05 },
    perKmOpsCost: { value: 0.0, min: 0.0, max: 2.0, step: 0.1 },
    perHourOpportunityCost: { value: 10, min: 0, max: 30, step: 1 },
    frameTimeout: { value: 300, min: 0, max: 1000, step: 10 },
    smoothingWindow: { value: 20, min: 1, max: 32, step: 1 },
    displayRoadWidth: 10,
    displayVehicleRadius: 10,
  },
  town: {
    scale: CITY_SCALE.TOWN,
    citySize: { value: 24, min: 16, max: 48, step: 4 },
    vehicleCount: { value: 160, min: 8, max: 512, step: 8 },
    requestRate: { value: 8, min: 0, max: 48, step: 4 },
    maxTripDistance: { value: 24, min: 1, max: 24, step: 1 },
    inhomogeneity: { value: 0.0, min: 0.0, max: 1.0, step: 0.1 },
    price: { value: 1.2, min: 0.0, max: 4.0, step: 0.1 },
    platformCommission: { value: 0.25, min: 0.0, max: 0.5, step: 0.01 },
    reservationWage: { value: 0.35, min: 0.0, max: 1.0, step: 0.05 },
    demandElasticity: { value: 0.0, min: 0.0, max: 2.0, step: 0.1 },
    meanVehicleSpeed: { value: 0.0, min: 0.0, max: 2.0, step: 0.1 },
    perKmPrice: { value: 0.8, min: 0.0, max: 1.2, step: 0.1 },
    perMinutePrice: { value: 0.2, min: 0.0, max: 0.4, step: 0.05 },
    perKmOpsCost: { value: 0.0, min: 0.0, max: 2.0, step: 0.1 },
    perHourOpportunityCost: { value: 10, min: 0, max: 30, step: 1 },
    frameTimeout: { value: 300, min: 0, max: 1000, step: 10 },
    smoothingWindow: { value: 20, min: 1, max: 32, step: 1 },
    displayRoadWidth: 6,
    displayVehicleRadius: 6,
  },
  city: {
    scale: CITY_SCALE.CITY,
    citySize: { value: 48, min: 32, max: 64, step: 8 },
    vehicleCount: { value: 1760, min: 32, max: 6400, step: 16 },
    requestRate: { value: 48, min: 8, max: 196, step: 8 },
    maxTripDistance: { value: 48, min: 1, max: 48, step: 1 },
    inhomogeneity: { value: 0.0, min: 0.0, max: 1.0, step: 0.1 },
    price: { value: 1.2, min: 0.0, max: 4.0, step: 0.1 },
    platformCommission: { value: 0.25, min: 0.0, max: 0.5, step: 0.01 },
    reservationWage: { value: 0.35, min: 0.0, max: 1.0, step: 0.05 },
    demandElasticity: { value: 0.0, min: 0.0, max: 2.0, step: 0.1 },
    meanVehicleSpeed: { value: 0.0, min: 0.0, max: 2.0, step: 0.1 },
    perKmPrice: { value: 0.8, min: 0.0, max: 1.2, step: 0.1 },
    perMinutePrice: { value: 0.2, min: 0.0, max: 0.4, step: 0.05 },
    perKmOpsCost: { value: 0.0, min: 0.0, max: 2.0, step: 0.1 },
    perHourOpportunityCost: { value: 10, min: 0, max: 30, step: 1 },
    frameTimeout: { value: 300, min: 0, max: 1000, step: 10 },
    smoothingWindow: { value: 20, min: 1, max: 32, step: 1 },
    defaultReservationWage: 0.35,
    displayRoadWidth: 3,
    displayVehicleRadius: 3,
  },
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
  frameTimeout: {
    source: "input",
    element: "frameTimeout",
    parser: parseFloat,
  },
  action: {
    source: "custom",
    getter: () => DOM_ELEMENTS.controls.fabButton.firstElementChild.innerHTML,
  },
  chartType: {
    source: "custom",
    getter: () =>
      document.querySelector('input[type="radio"][name="chart-type"]:checked')
        ?.value || "map",
  },
};

export const CHART_TYPES = {
  MAP: "map",
  STATS: "stats",
  WHAT_IF: "whatif",
};
