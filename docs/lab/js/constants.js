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

// The downtown core: when inhomogeneity > 0, extra trip requests start in the
// central square of the city (ridehail/atom.py City.set_location), and the map
// shades it (THEME_COLORS CORE). CITY_CORE_FRACTION mirrors
// City.TWO_ZONE_LENGTH: keep them in sync.
export const CITY_CORE_FRACTION = 0.5;

// Colours drawn on canvases (the map, Chart.js charts, sparklines), one table
// per theme (claude/dark-mode-spec.md). Canvas code can't use the CSS tokens in
// style.css, so it reads these, via themeColor() in js/theme.js. The CSS
// domain tokens (--lab-p1 etc.) must agree with the *_SOLID values here;
// test/test_web_lab_theme_tokens.py checks. The light P1/P2/P3/wait hues are
// the unified palette shared with ridehail/animation/palette.py.
//
// Map: Direction A (cartographic) - a soft "land" tone behind the map,
// modelled on Google Maps' default urban roadmap, with near-white streets. At
// night (dark) the land is slate and the streets a lighter slate, so roads
// still read lighter than the land, as in Google Maps' night style. CORE sits
// between the land and the lab's steel blue (#7facca). The chart background
// plugin (js/chart-plugins.js) paints LAND behind every chart.
//
// Phase colours: the light theme draws them at 0.5 alpha over pale land. Over
// dark land, half-transparent colours turn muddy, so the dark theme uses lifted
// hues at higher alpha.
//
// WAITING_RIDER is the canonical "waiting rider" / unmet-demand colour, shared
// by the map trip-origin markers, the heatmap trip dots, and the
// passenger-Wait / requests chart series. Deliberately NOT the "WAITING" token:
// that amber is reused as a warm "value went up" highlight in the What If?
// settings tables and must stay amber.
//
// P3_SMALL_CITY / P3_LARGE_CITY: occupied cars change with city size (see
// mapVehicleColor in modules/map.js). In light they deepen so idle reads as a
// pale "empty" car and occupied as a solid "full" one; in dark the lightness
// cue inverts, so occupied cars brighten instead.
export const THEME_COLORS = {
  light: {
    LAND: "#e2e8f0",
    CORE: "#b0cadd",
    ROAD: "#fcfcfc",
    CHART_TEXT: "#666",
    CHART_GRID: "rgba(0, 0, 0, 0.1)",
    // Vehicles
    P1: "rgba(100, 149, 237, 0.5)",
    P2: "rgba(215, 142, 0, 0.5)",
    P3: "rgba(60, 179, 113, 0.5)",
    IDLE: "rgba(100, 149, 237, 0.5)",
    DISPATCHED: "rgba(215, 142, 0, 0.5)",
    WITH_RIDER: "rgba(60, 179, 113, 0.5)",
    PURPLE: "rgba(160, 109, 153, 0.5)",
    SURPLUS: "rgba(237, 100, 149, 0.5)",
    // Trips
    UNASSIGNED: "rgba(237, 100, 149, 0.5)",
    WAITING: "rgba(215, 142, 0, 0.5)",
    RIDING: "rgba(60, 179, 113, 0.5)",
    WAITING_RIDER: "rgba(237, 100, 149, 0.45)",
    // Opaque phase colours: lines, outlines, legends
    P1_SOLID: "rgb(100, 149, 237)",
    P2_SOLID: "rgb(215, 142, 0)",
    P3_SOLID: "rgb(60, 179, 113)",
    WAIT_SOLID: "rgb(237, 100, 149)",
    // The Wait line of the map metrics sparkline
    WAIT_METRIC: "rgb(210, 60, 60)",
    SPARKLINE_GRID: "rgba(0, 0, 0, 0.07)",
    P3_SMALL_CITY: [60, 179, 113, 0.5],
    P3_LARGE_CITY: [46, 139, 87, 0.9],
    // Map icons: wheels and person / house outlines (SPRITE_INK), the car
    // and plain-marker outline (ICON_OUTLINE), and the car's windshield,
    // which marks its front
    SPRITE_INK: "#333333",
    ICON_OUTLINE: "grey",
    WINDSHIELD: "#000000",
    // Game overlay (modules/game-map-overlay.js)
    YOU: "#7c3aed",
    YOU_TEXT: "#ffffff",
    HALO: "rgba(255, 255, 255, 0.95)",
    DIM: "rgba(20, 24, 33, 0.14)",
  },
  dark: {
    LAND: "#1e2530",
    CORE: "#2c3e52",
    ROAD: "#3a4452",
    CHART_TEXT: "#aab2bd",
    CHART_GRID: "rgba(255, 255, 255, 0.12)",
    P1: "rgba(126, 166, 240, 0.7)",
    P2: "rgba(232, 166, 42, 0.7)",
    P3: "rgba(79, 196, 136, 0.7)",
    IDLE: "rgba(126, 166, 240, 0.7)",
    DISPATCHED: "rgba(232, 166, 42, 0.7)",
    WITH_RIDER: "rgba(79, 196, 136, 0.7)",
    PURPLE: "rgba(196, 140, 188, 0.7)",
    SURPLUS: "rgba(240, 122, 165, 0.7)",
    UNASSIGNED: "rgba(240, 122, 165, 0.7)",
    WAITING: "rgba(232, 166, 42, 0.7)",
    RIDING: "rgba(79, 196, 136, 0.7)",
    WAITING_RIDER: "rgba(240, 122, 165, 0.65)",
    P1_SOLID: "rgb(126, 166, 240)",
    P2_SOLID: "rgb(232, 166, 42)",
    P3_SOLID: "rgb(79, 196, 136)",
    WAIT_SOLID: "rgb(240, 122, 165)",
    WAIT_METRIC: "rgb(240, 112, 112)",
    SPARKLINE_GRID: "rgba(255, 255, 255, 0.1)",
    P3_SMALL_CITY: [79, 196, 136, 0.7],
    P3_LARGE_CITY: [125, 228, 168, 0.95],
    SPRITE_INK: "#cfd5dd",
    ICON_OUTLINE: "#cfd5dd",
    WINDSHIELD: "#f3f4f6",
    YOU: "#a78bfa",
    YOU_TEXT: "#1e1533",
    HALO: "rgba(18, 22, 28, 0.9)",
    DIM: "rgba(0, 0, 0, 0.4)",
  },
};
