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

// Configuration defaults
export const SCALE_CONFIGS = {
  village: {
    citySize: { value: 8, min: 4, max: 16, step: 2 },
    vehicleCount: { value: 8, min: 1, max: 16, step: 1 },
    maxTripDistance: { value: 4, min: 1, max: 4, step: 1 },
    requestRate: { value: 0.5, min: 0, max: 2, step: 0.1 },
    demandElasticity: 0.0,
    roadWidth: 10,
    vehicleRadius: 10,
    defaultPrice: 1.2,
    defaultCommission: 0.25,
    defaultReservationWage: 0.35,
  },
  town: {
    citySize: { value: 24, min: 16, max: 64, step: 4 },
    vehicleCount: { value: 160, min: 8, max: 512, step: 8 },
    maxTripDistance: { value: 24, min: 1, max: 24, step: 1 },
    requestRate: { value: 8, min: 0, max: 48, step: 4 },
    demandElasticity: 0.0,
    roadWidth: 6,
    vehicleRadius: 6,
    defaultPrice: 1.2,
    defaultCommission: 0.25,
    defaultReservationWage: 0.35,
  },
  city: {
    citySize: { value: 48, min: 32, max: 64, step: 8 },
    vehicleCount: { value: 1760, min: 32, max: 6400, step: 16 },
    maxTripDistance: { value: 48, min: 1, max: 48, step: 1 },
    requestRate: { value: 48, min: 8, max: 196, step: 8 },
    demandElasticity: 0.0,
    roadWidth: 3,
    vehicleRadius: 3,
    defaultPrice: 1.2,
    defaultCommission: 0.25,
    defaultReservationWage: 0.35,
  },
};
