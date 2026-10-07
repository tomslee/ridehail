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
  // Game tab: the player's answer to a pending offer, and the end-of-shift
  // results request. See webworker.js (offer hold) and worker.py
  // (GameSimulation).
  GameDecision: "gameDecision",
  GetGameResults: "getGameResults",
  // Experiment map: follow a car ({choice: "random"}) or stop ({choice:
  // null}). See worker.py Simulation.follow_vehicle.
  FollowVehicle: "followVehicle",
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
// worker.py duplicates this value (it can't import a JS module);
// test/test_web_lab_constants.py checks that they agree.
export const INTERPOLATE_MAX_CITY_SIZE = 32;

/**
 * Frames drawn per simulation block for a given city size. At/below
 * INTERPOLATE_MAX_CITY_SIZE the map draws an interpolated mid-block frame (2
 * frames/block); above it, only real blocks (1 frame/block), as worker.py
 * produces them.
 * @param {number} citySize
 * @returns {number} 1 or 2
 */
export function framesPerBlock(citySize) {
  return citySize <= INTERPOLATE_MAX_CITY_SIZE ? 2 : 1;
}

// Direction A (cartographic): a soft "land" tone behind the map, modelled on
// Google Maps' default urban roadmap — a cool pale neutral grey land with
// mid-grey streets (the "ROAD" colour below). The land is kept distinctly
// paler than the roads so streets read with clear contrast, and a touch
// deeper than the cream viewport so the map square sits within the page.
// Consumed by the mapBackground Chart.js plugin in modules/map.js, which
// paints a vertical gradient from MAP_LAND_TOP to MAP_LAND_BOTTOM.
export const MAP_LAND_TOP = "#e2e8f0";
export const MAP_LAND_BOTTOM = "#e2e8f0";

// The "downtown" core: when inhomogeneity > 0, extra trip requests start in
// the central square of the city (ridehail/atom.py City.set_location), and
// the map shades it a little darker than the land above so that you can see
// where. CITY_CORE_FRACTION mirrors City.TWO_ZONE_LENGTH: keep them in sync.
// export const MAP_CORE = "#d5dce6";
// Halfway between the land (#e2e8f0) and the lab's steel blue (#7facca)
export const MAP_CORE = "#b0cadd";
export const CITY_CORE_FRACTION = 0.5;

// Canonical "waiting rider" / unmet-demand color. Shared by the map trip-origin
// markers, the heatmap trip dots, and the passenger-Wait / requests chart series
// so a waiting rider reads the same everywhere. Deliberately NOT the colors-map
// "WAITING" token below: that amber is reused as a warm "value went up" highlight
// in the What If? settings tables (see whatif-tab.js / whatif.js) and must stay
// amber to keep its warm-up / cool-down meaning.
export const WAITING_RIDER_COLOR = "rgba(237, 100, 149, 0.45)";

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
