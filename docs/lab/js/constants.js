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
  // Sent main-thread -> worker after a frame has been rendered (or dropped),
  // so the worker can produce the next one. See webworker.js for why.
  FrameAck: "frameAck",
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

// Above this city size, the map shows only real simulation blocks - no
// interpolated "mid-block" frame between them. Shared between map.js
// (rendering) and webworker.js (frame-count pacing, since interpolated runs
// need 2 frames per block and non-interpolated runs need only 1).
// worker.py duplicates this value (it can't import a JS module); keep them
// in sync if this changes.
export const INTERPOLATE_MAX_CITY_SIZE = 32;

export const colors = new Map([
  // Map: white streets read crisply over the cartographic "land" tone painted
  // by the mapBackground plugin (see modules/map.js).
  ["ROAD", "#ffffff"],
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
