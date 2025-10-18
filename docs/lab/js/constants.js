/**
 * Shared constants that can be safely imported in both main thread and web workers
 * This file contains only pure constants with no DOM dependencies
 */

export const SimulationActions = {
  Play: "play_arrow",
  Pause: "pause",
  Reset: "reset",
  SingleStep: "single-step",
  Update: "update",
  UpdateDisplay: "updateDisplay",
  Done: "pause",
  GetResults: "getResults",
};

export const CHART_TYPES = {
  MAP: "map",
  STATS: "stats",
  WHAT_IF: "whatif",
};

export const CITY_SCALE = {
  VILLAGE: "village",
  TOWN: "town",
  CITY: "city",
};

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
  ["WAITING", "rgba(215, 142, 0, 0.5)"],
  ["RIDING", "rgba(60, 179, 113, 0.5)"],
]);
