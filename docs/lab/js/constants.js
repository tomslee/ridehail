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

// Direction A (cartographic): a soft "land" tone behind the map, modelled on
// Google Maps' default urban roadmap — a cool pale neutral grey land with
// mid-grey streets (the "ROAD" colour below). The land is kept distinctly
// paler than the roads so streets read with clear contrast, and a touch
// deeper than the cream viewport so the map square sits within the page.
// Consumed by the mapBackground Chart.js plugin in modules/map.js, which
// paints a vertical gradient from MAP_LAND_TOP to MAP_LAND_BOTTOM.
export const MAP_LAND_TOP = "#e2e8f0";
export const MAP_LAND_BOTTOM = "#e2e8f0";

export const colors = new Map([
  // Map: mid-grey streets read crisply over the pale "land" tone above.
  // Google Maps' own white local-road fill has no contrast on its own; what
  // reads as "the road" at normal zoom is the grey casing/arterial stroke,
  // so a flat single-tier road grid (no hierarchy here) needs to carry that
  // grey directly.
  ["ROAD", "#fcfcfc"],
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
