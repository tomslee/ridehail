/* global Chart */
import {
  colors,
  CITY_CORE_FRACTION,
  INTERPOLATE_MAX_CITY_SIZE,
  MAP_CORE,
  WAITING_RIDER_COLOR,
} from "../js/constants.js";
import { chartBackgroundPlugin as mapBackgroundPlugin } from "../js/chart-plugins.js";
import {
  gameOverlayPlugin,
  pulseGameCar,
  setGameOverlay,
} from "./game-map-overlay.js";
import { drawMetricsSparkline } from "./metrics-sparkline.js";
// const startTime = Date.now();

let citySize = 0;
let vehicleRadius = 16;

/**
 * Compute map display sizing (road line width and vehicle/marker radius, both in
 * pixels) from the city size alone.
 *
 * The map canvas is a fixed square that is fit to the viewport, so a larger city
 * packs more blocks into the same space and each block is drawn smaller. Roads
 * and vehicles must shrink to match. This used to be a discrete per-preset
 * setting (Village=10, Town=6, City=3); it is now a continuous function of city
 * size, so it stays correct at every city size the (continuous) slider allows.
 *
 * The curve is anchored to the former preset values: ~144 / citySize reproduces
 * Town (24 -> 6) and City (48 -> 3), and the clamp keeps small cities legible
 * (Village 8 -> 10) without letting markers grow unbounded.
 *
 * @param {number} size - City size in blocks
 * @returns {{ vehicleRadius: number, roadWidth: number }}
 */
function computeMapDisplaySizing(size) {
  const px = Math.max(2, Math.min(10, Math.round(144 / size)));
  return { vehicleRadius: px, roadWidth: px };
}

// Above this vehicle count, per-vehicle car/person/house icons (canvas images
// with rotation transforms) are replaced with plain Chart.js vector point
// styles. Image-based pointStyles are drawn via ctx.translate/rotate/drawImage
// per point; at large fleet sizes (the "city" scale defaults to 1760) that
// dominates render time, while the icon detail itself stops being legible.
const SIMPLE_MARKER_VEHICLE_THRESHOLD = 24 * 24;

// Above this city size, vehicle movement snaps to its new position instead of
// easing over `animationDelay`, AND worker.py stops generating the
// interpolated mid-block frame entirely (see INTERPOLATE_MAX_CITY_SIZE in
// js/constants.js and Simulation.interpolate_frames in worker.py) - so every
// frame here is a real, distinct simulation block. With many intersections
// sharing the same canvas, the eased glide between adjacent intersections
// was too short to be visible but still cost a full Chart.js animation
// (requestAnimationFrame) loop redrawing every point ~15-20 times per
// logical update; the mid-block frame, shown as its own discrete snapped
// state once that easing was gone, read as a flicker rather than motion.
const SNAP_MOVEMENT_CITY_SIZE_THRESHOLD = INTERPOLATE_MAX_CITY_SIZE;

// Above SIMPLE_MARKER_VEHICLE_THRESHOLD vehicles, individual vehicle markers
// are replaced entirely with a density heatmap (see vehicleHeatmapPlugin):
// one fillRect per occupied grid cell instead of one drawImage/point per
// vehicle, so cost no longer scales with fleet size. Trip markers keep using
// the plain-circle/rect simple style at this threshold (see useSimpleMarkers
// below) - they're fewer and individually meaningful (waiting vs. en route).
// The "h" key (toggleHeatmapView) can override this auto behaviour in either
// direction for the current simulation - see _heatmapOverride below.

// Number of intersections per edge grouped into one heatmap cell. 1 = one
// cell per intersection (the original, most detailed behaviour). Heatmaps
// generally trade spatial resolution for a smoother, more legible density
// gradient - the same bin-width tradeoff as a histogram: too fine and most
// cells just show 0-1 vehicles (sparse/noisy), too coarse and distinct local
// patterns (a specific congested intersection, an idle cluster next to a
// busy one) blur together. Set to 1 to revert to per-intersection cells.
const HEATMAP_BLOCK_SIZE = 2;
const HEATMAP_MAX_ALPHA = 0.95;

// The cell density that maps to full opacity is not fixed - it adapts to
// each simulation's own observed range (see _updateHeatmapSaturation), so a
// sparse config (e.g. default "City") and a dense one both use the full
// light-to-dark spectrum instead of the sparse one reading as uniformly
// pale. This trades away cross-simulation comparability (two heatmaps can
// no longer be eyeballed against each other for absolute density) for
// legibility within a single run, which is the more useful read here.
//
// The adaptive saturation point is the HEATMAP_SATURATION_PERCENTILE-th
// percentile of currently-occupied cells' smoothed counts, not the bare
// max - a single outlier cell (one busy intersection) would otherwise wash
// out the contrast everywhere else. It rises immediately to a new peak but
// decays slowly when peaks recede (HEATMAP_SATURATION_DECAY), the same
// fast-attack/slow-release shape as an audio AGC, so ordinary frame-to-frame
// vehicle movement doesn't visibly flicker the color scale while it still
// tracks real shifts in density (e.g. as equilibration changes fleet size
// over a run).
const HEATMAP_SATURATION_PERCENTILE = 0.9;
const HEATMAP_SATURATION_DECAY = 0.98; // per-frame retention when relaxing downward
// Minimum saturation point, in (fractional, EMA-smoothed) vehicles per
// cell. Without a floor, a near-empty map (one or two vehicles total) would
// let a single fractional cell value saturate to full opacity, which reads
// as noise rather than density.
const HEATMAP_SATURATION_FLOOR = 1;

// In heatmap mode, trip markers are pared down rather than drawn at full
// per-vehicle-view size (see plotMap): RIDING markers are dropped entirely
// since they're redundant with the vehicle heatmap's own P3 (occupied)
// density, and WAITING/UNASSIGNED markers - the one signal the vehicle
// heatmap can't express, i.e. unserved demand - are shrunk to a small fixed
// dot in a single muted color instead of full-size person icons in their
// normal per-state colors. Reusing the UNASSIGNED/"SURPLUS" pink (already
// distinct from the P1/P2/P3 heatmap palette of blue/orange/green) at
// reduced alpha keeps these readable as a sparse demand overlay without
// looking like a second, competing density layer.
// Muted pink, shared with the normal-view trip-origin markers and the passenger
// Wait / requests chart series - see WAITING_RIDER_COLOR in constants.js.
const HEATMAP_TRIP_DOT_COLOR = WAITING_RIDER_COLOR;
const HEATMAP_TRIP_DOT_RADIUS = 3;

// In heatmap mode a frame can still name vehicles to draw individually, over
// the heatmap: the Game tab's player (eventData "game".player), or the car
// followed on the Experiment tab (eventData "followed", see
// _highlightedVehicles). They stay in the heatmap too (one car among
// thousands makes no visible difference). Big cities draw small cars, so
// these get at least this radius (px).
const HIGHLIGHT_MIN_RADIUS = 8;
// Highlighted cars' locations in the previous frame, by highlight key (see
// _highlightedVehicles), to spot a torus wrap (see plotMap)
let _prevHighlightLocations = new Map();
// Above SNAP_MOVEMENT_CITY_SIZE_THRESHOLD there is no interpolated mid-block
// frame, so each frame glides the highlighted cars a whole block, from the
// intersection they left to the one the frame reports. The midpoint frame's
// timing is recreated here for them (see _glideHighlights):
//   - heading: from the actual displacement, so the car faces the way it is
//     travelling (the frame's direction is the one chosen *at* the new
//     intersection, for the next leg: the car would turn a block early);
//   - colour, style and size: the frame's values are applied when the car
//     arrives (_highlightArrivalStyle, applied by a timer or by the next
//     frame, whichever comes first), as the even frame does;
//   - a torus wrap: glide off one edge, then in from the other.
// Last heading (rotation, degrees) by highlight key, kept while a car is
// stationary
let _highlightHeadings = new Map();
// {keys, colors, styles, radii} still to apply on arrival, or null
let _highlightArrivalStyle = null;
// Pending setTimeout ids for the current glide
let _highlightTimers = [];

// Per-cell counts are smoothed across frames with an exponential moving
// average (see _updateHeatmapEMA) rather than redrawn from the raw
// instantaneous count: a single vehicle entering/leaving a cell would
// otherwise swing its alpha sharply at low saturation levels, which read as
// flicker rather than density. This is a different mechanism
// from the simulation's smoothingWindow (a server-side rolling average over
// a scalar block-rate stat, see ridehail/simulation.py) - there's no
// equivalent spatial-grid concept there to reuse.
const HEATMAP_EMA_DECAY = 0.65; // fraction of previous value retained per frame
const HEATMAP_EMA_EPSILON = 0.05; // below this, drop the cell rather than draw a near-invisible rect

// Manual override for heatmap mode, set by toggleHeatmapView() (bound to "h"
// in the Experiment map view). null = auto (use the vehicle-count threshold);
// true/false = force heatmap on/off regardless of vehicle count. Reset to
// auto whenever a new map is initialized (initMap).
let _heatmapOverride = null;
// Effective heatmap state from the most recent plotMap call, used by
// toggleHeatmapView() to know what to flip.
let _lastUseHeatmap = false;
// Most recent frame, cached so toggleHeatmapView() can force an immediate
// redraw even while the simulation is paused (plotMap otherwise only runs
// when a new frame arrives).
let _lastEventData = null;

// Cache for vehicle canvas elements
const vehicleCanvasCache = new Map();

// Cache for person canvas elements
const personCanvasCache = new Map();

// Cache for house canvas elements
const houseCanvasCache = new Map();

// Trip destination markers (RIDING) lag the rest of the trip display by one
// frame so a completed trip's house marker stays visible through the even-frame
// animation that carries the vehicle to the destination, disappearing only once
// the vehicle has arrived. Origins (UNASSIGNED/WAITING) need no such buffer:
// the worker sends identical trip data on each even/odd frame pair, so the
// origin set is unchanged within a pair and is applied directly every frame —
// which keeps the dispatch person icon in sync with the even-frame P2 color
// change. This holds the previous frame's rendered RIDING arrays.
let _prevRidingTrip = { locations: [], colors: [], styles: [], radii: [] };

// Metrics overlay state
const SPARKLINE_MAX = 80;
const SPARKLINE_COMPACT = { w: 120, h: 42 };
const SPARKLINE_SOLID_LINES = [
  { key: "p1", label: "P1", color: "rgb(100,149,237)" },
  { key: "p2", label: "P2", color: "rgb(215,142,0)" },
  { key: "p3", label: "P3", color: "rgb(60,179,113)" },
];
const SPARKLINE_DASHED_LINES = [{ key: "wait", label: "W", color: "rgb(210,60,60)" }];
let _sparklineHistory = [];
let _sparklineCtx = null;
// "compact" | "expanded" | "hidden"
let _overlayState = "compact";

// Parsed once at module load from the rgba() strings in js/constants.js, so
// the heatmap blend below has plain numeric channels to work with without
// re-parsing a string every frame.
function _parseRgbTriple(rgbaStr) {
  const m = rgbaStr.match(/rgba?\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)/);
  return m ? { r: +m[1], g: +m[2], b: +m[3] } : { r: 0, g: 0, b: 0 };
}
const PHASE_RGB = {
  P1: _parseRgbTriple(colors.get("P1")),
  P2: _parseRgbTriple(colors.get("P2")),
  P3: _parseRgbTriple(colors.get("P3")),
};

// Bin vehicles into HEATMAP_BLOCK_SIZE x HEATMAP_BLOCK_SIZE blocks of
// city-grid cells by phase count. Rounds (and wraps via modulo) straight from
// each vehicle's raw location every frame, which also means the chart.js
// edge-teleport dance (see the needsRefresh block in plotMap) simply isn't
// needed in heatmap mode - there's no scatter point position to overshoot
// and snap back.
function _computeVehicleHeatmapGrid(vehicles, citySize) {
  const grid = new Map(); // "blockX,blockY" -> {P1, P2, P3}
  vehicles.forEach((vehicle) => {
    const phase = vehicle.phase || vehicle[0];
    const location = vehicle.location || vehicle[1];
    const x = ((Math.round(location[0]) % citySize) + citySize) % citySize;
    const y = ((Math.round(location[1]) % citySize) + citySize) % citySize;
    const blockX = Math.floor(x / HEATMAP_BLOCK_SIZE);
    const blockY = Math.floor(y / HEATMAP_BLOCK_SIZE);
    const key = `${blockX},${blockY}`;
    let cell = grid.get(key);
    if (!cell) {
      cell = { P1: 0, P2: 0, P3: 0 };
      grid.set(key, cell);
    }
    cell[phase] = (cell[phase] || 0) + 1;
  });
  return grid;
}

// Smoothed cell counts, persisted across frames - "blockX,blockY" ->
// {P1, P2, P3} (fractional, unlike the raw integer counts from
// _computeVehicleHeatmapGrid).
// Cleared whenever heatmap mode is off (see plotMap) so a later re-enable
// starts fresh instead of resuming long-decayed history.
let _heatmapEMA = new Map();
// Adaptive saturation point for _heatmapCellColor (see constants above).
// null until the first occupied frame in the current simulation/heatmap
// session; reset alongside _heatmapEMA (initMap, and re-enabling heatmap
// mode) so a new run doesn't inherit a stale scale.
let _heatmapSaturationLevel = null;

// Blend each frame's raw counts into the persisted EMA in place and return
// it. Only touches cells that are currently occupied or were recently
// occupied (still decaying toward zero), so cost and memory scale with
// vehicle density, not city size - a sparse, very large city stays cheap.
function _updateHeatmapEMA(rawGrid) {
  // Decay every previously-tracked cell first, including ones with no
  // vehicles this frame, so a just-vacated cell fades out instead of
  // disappearing on the next frame.
  for (const [key, cell] of _heatmapEMA) {
    const raw = rawGrid.get(key);
    const next = {
      P1:
        HEATMAP_EMA_DECAY * cell.P1 + (1 - HEATMAP_EMA_DECAY) * (raw?.P1 || 0),
      P2:
        HEATMAP_EMA_DECAY * cell.P2 + (1 - HEATMAP_EMA_DECAY) * (raw?.P2 || 0),
      P3:
        HEATMAP_EMA_DECAY * cell.P3 + (1 - HEATMAP_EMA_DECAY) * (raw?.P3 || 0),
    };
    if (next.P1 + next.P2 + next.P3 < HEATMAP_EMA_EPSILON) {
      _heatmapEMA.delete(key);
    } else {
      _heatmapEMA.set(key, next);
    }
  }
  // Bring in cells that are newly occupied this frame and have no prior
  // smoothed history yet.
  for (const [key, cell] of rawGrid) {
    if (!_heatmapEMA.has(key)) {
      _heatmapEMA.set(key, {
        P1: (1 - HEATMAP_EMA_DECAY) * cell.P1,
        P2: (1 - HEATMAP_EMA_DECAY) * cell.P2,
        P3: (1 - HEATMAP_EMA_DECAY) * cell.P3,
      });
    }
  }
  return _heatmapEMA;
}

// Nearest-rank percentile of cell totals (P1+P2+P3) across occupied cells.
function _percentileOfCellTotals(grid, p) {
  const totals = [];
  for (const cell of grid.values()) {
    const total = cell.P1 + cell.P2 + cell.P3;
    if (total > 0) totals.push(total);
  }
  if (totals.length === 0) return 0;
  totals.sort((a, b) => a - b);
  const index = Math.min(totals.length - 1, Math.floor(p * totals.length));
  return totals[index];
}

// Update (and return) the adaptive saturation point from the current
// smoothed grid - see the HEATMAP_SATURATION_* constants for the
// fast-rise/slow-decay rationale. Leaves the level untouched on a fully
// empty grid (nothing to learn from) rather than decaying it toward zero.
function _updateHeatmapSaturation(grid) {
  const observed = _percentileOfCellTotals(grid, HEATMAP_SATURATION_PERCENTILE);
  if (observed === 0) return _heatmapSaturationLevel;
  if (_heatmapSaturationLevel === null || observed > _heatmapSaturationLevel) {
    _heatmapSaturationLevel = observed;
  } else {
    _heatmapSaturationLevel = Math.max(
      observed,
      _heatmapSaturationLevel * HEATMAP_SATURATION_DECAY,
    );
  }
  _heatmapSaturationLevel = Math.max(
    _heatmapSaturationLevel,
    HEATMAP_SATURATION_FLOOR,
  );
  return _heatmapSaturationLevel;
}

// Count-weighted blend of the phase colors present in a cell, with opacity
// scaled by occupancy relative to the adaptive _heatmapSaturationLevel (see
// above) so empty/sparse areas stay subtle and the busiest cells in *this*
// simulation reach full opacity.
function _heatmapCellColor(cell) {
  const total = cell.P1 + cell.P2 + cell.P3;
  if (total === 0) return null;
  const r =
    (PHASE_RGB.P1.r * cell.P1 +
      PHASE_RGB.P2.r * cell.P2 +
      PHASE_RGB.P3.r * cell.P3) /
    total;
  const g =
    (PHASE_RGB.P1.g * cell.P1 +
      PHASE_RGB.P2.g * cell.P2 +
      PHASE_RGB.P3.g * cell.P3) /
    total;
  const b =
    (PHASE_RGB.P1.b * cell.P1 +
      PHASE_RGB.P2.b * cell.P2 +
      PHASE_RGB.P3.b * cell.P3) /
    total;
  const saturationLevel = _heatmapSaturationLevel || HEATMAP_SATURATION_FLOOR;
  const alpha = Math.min(total / saturationLevel, 1) * HEATMAP_MAX_ALPHA;
  return `rgba(${r | 0}, ${g | 0}, ${b | 0}, ${alpha.toFixed(3)})`;
}

// The EMA above already smooths cell *values* over time, but each redraw of
// the plugin's fillRect cells previously painted that EMA snapshot instantly
// - since this is a custom canvas plugin rather than a Chart.js-managed
// dataset, it gets none of the property tweening that eases vehicle marker
// x/y between frames. _heatmapGridFrom/_heatmapGridTo bracket the most
// recent transition (the blend last rendered, and the latest EMA snapshot
// it's easing towards); _heatmapAnimationTick advances a plain
// requestAnimationFrame loop that linearly interpolates between them and
// redraws, independent of Chart.js's own animation engine.
let _heatmapGridFrom = null;
let _heatmapGridTo = null;
let _heatmapTransitionStart = 0;
let _heatmapTransitionDuration = 0;
let _heatmapAnimating = false;

function _cloneHeatmapGrid(grid) {
  const clone = new Map();
  for (const [key, cell] of grid) {
    clone.set(key, { P1: cell.P1, P2: cell.P2, P3: cell.P3 });
  }
  return clone;
}

function _heatmapTransitionProgress() {
  if (_heatmapTransitionDuration <= 0) return 1;
  return Math.min(
    (performance.now() - _heatmapTransitionStart) / _heatmapTransitionDuration,
    1,
  );
}

// Blend of _heatmapGridFrom -> _heatmapGridTo at the current transition
// progress; this is what the plugin actually paints. Cells present in only
// one snapshot are treated as 0 in the other, so a newly-occupied cell fades
// in and a just-vacated one fades out rather than popping.
function _currentInterpolatedHeatmapGrid() {
  if (!_heatmapGridTo || !_heatmapGridFrom) return _heatmapGridTo;
  const t = _heatmapTransitionProgress();
  if (t >= 1) return _heatmapGridTo;
  const keys = new Set([..._heatmapGridFrom.keys(), ..._heatmapGridTo.keys()]);
  const blended = new Map();
  for (const key of keys) {
    const from = _heatmapGridFrom.get(key) || { P1: 0, P2: 0, P3: 0 };
    const to = _heatmapGridTo.get(key) || { P1: 0, P2: 0, P3: 0 };
    blended.set(key, {
      P1: from.P1 + (to.P1 - from.P1) * t,
      P2: from.P2 + (to.P2 - from.P2) * t,
      P3: from.P3 + (to.P3 - from.P3) * t,
    });
  }
  return blended;
}

function _heatmapAnimationTick() {
  if (!_lastUseHeatmap || !(window.chart instanceof Chart)) {
    _heatmapAnimating = false;
    return;
  }
  window.chart.draw();
  if (_heatmapTransitionProgress() < 1) {
    requestAnimationFrame(_heatmapAnimationTick);
  } else {
    _heatmapAnimating = false;
  }
}

// Called once per arriving frame in heatmap mode with the latest smoothed
// grid (see _updateHeatmapEMA). Retargets the in-flight transition to start
// from whatever is currently on screen, so a new frame arriving mid-fade
// redirects smoothly instead of jumping.
function _startHeatmapTransition(targetGrid, duration) {
  _heatmapGridFrom = _currentInterpolatedHeatmapGrid();
  _heatmapGridTo = _cloneHeatmapGrid(targetGrid);
  _heatmapTransitionStart = performance.now();
  _heatmapTransitionDuration = duration > 0 ? duration : 0;
  if (!_heatmapAnimating) {
    _heatmapAnimating = true;
    requestAnimationFrame(_heatmapAnimationTick);
  }
}

function _resetHeatmapTransition() {
  _heatmapGridFrom = null;
  _heatmapGridTo = null;
  _heatmapAnimating = false;
}

// Rotation (degrees, as in plotMap's addVehicle) for a one-block step of
// (dx, dy), or null for no step. A step longer than one block is a torus
// wrap, so the car is going the other way.
function _headingForStep(dx, dy) {
  if (Math.abs(dx) > 1) dx = -Math.sign(dx);
  if (Math.abs(dy) > 1) dy = -Math.sign(dy);
  if (dx > 0) return 90;
  if (dx < 0) return 270;
  if (dy > 0) return 0;
  if (dy < 0) return 180;
  return null;
}

function _sameKeys(a, b) {
  return a.length === b.length && a.every((key, i) => key === b[i]);
}

/**
 * The cars a frame highlights, as [position, key] pairs: position in the
 * frame's vehicle list, and a key that names the same car from frame to
 * frame. A followed car's position shifts when vehicles ahead of it in the
 * list are removed, so its key is its vehicle index; the game's fleet is
 * fixed.
 */
function _highlightedVehicles(eventData, vehicles) {
  const player = eventData.get("game")?.player;
  if (player != null && vehicles[player]) return [[player, "player"]];
  const followed = eventData.get("followed");
  if (followed?.position != null && vehicles[followed.position]) {
    return [[followed.position, `car ${followed.index}`]];
  }
  return [];
}

/**
 * Overlay state for the car followed on the Experiment tab (see
 * game-map-overlay.js), from a frame's "followed" (worker.py
 * Simulation._followed_payload), or null for none: its ring, and the rest of
 * its route as legs from the car. The ride is shown from dispatch, but as a
 * future leg until the pickup, when the map's house icon appears; so is a
 * forward-dispatched car's next pickup.
 * @param {boolean} useHeatmap - the map shows no rider or house icons
 */
function _followedOverlayState(followed, useHeatmap) {
  if (followed?.position == null) return null;
  const legs = [];
  if (followed.phase === "P2" && followed.pickup) {
    legs.push({ to: followed.pickup, kind: "pickup", future: false });
  }
  if (followed.phase !== "P1" && followed.dropoff) {
    legs.push({
      to: followed.dropoff,
      kind: "dropoff",
      future: followed.phase === "P2",
    });
  }
  if (followed.phase === "P3" && followed.next_pickup) {
    legs.push({ to: followed.next_pickup, kind: "pickup", future: true });
  }
  return {
    player: followed.position,
    citySize,
    phase: followed.phase,
    target: null,
    offer: null,
    legs,
    icons: !useHeatmap,
  };
}

function _applyHighlightStyle(style) {
  const dataset = window.chart.data.datasets[0];
  dataset.pointBackgroundColor = style.colors;
  dataset.pointStyle = style.styles;
  dataset.pointRadius = style.radii;
}

// setTimeout for the current glide, dropped if the map is rebuilt or
// destroyed (leaving the tab) meanwhile
function _scheduleHighlight(callback, delay) {
  const chart = window.chart;
  const id = setTimeout(() => {
    _highlightTimers = _highlightTimers.filter((t) => t !== id);
    if (window.chart === chart && chart.canvas) callback();
  }, delay);
  _highlightTimers.push(id);
}

function _cancelHighlightTimers() {
  _highlightTimers.forEach(clearTimeout);
  _highlightTimers = [];
}

function _resetHighlightGlide() {
  _cancelHighlightTimers();
  _prevHighlightLocations = new Map();
  _highlightHeadings = new Map();
  _highlightArrivalStyle = null;
}

// Glide the highlighted cars (dataset 0) one block, from their previous
// intersections to this frame's, over duration ms. Starting from `from`
// (rather than wherever the last glide left them) keeps a cut-short glide
// from carrying over. A car crossing the torus edge glides half a block off
// it, reappears half a block beyond the opposite edge, and glides in; any
// other car's two halves join into one straight glide.
function _glideHighlights(from, to, duration) {
  const chart = window.chart;
  const dataset = chart.data.datasets[0];
  chart.options.animation.duration = 0;
  dataset.data = from;
  chart.update("none");
  const wraps = to.map((p, i) => ({
    x: Math.abs(p.x - from[i].x) > 1,
    y: Math.abs(p.y - from[i].y) > 1,
  }));
  if (!wraps.some((w) => w.x || w.y)) {
    dataset.data = to;
    chart.options.animation.duration = duration;
    chart.update();
    return;
  }
  // The one-block step in the direction of travel
  const step = (a, b, wrapped) => (wrapped ? -Math.sign(b - a) : b - a);
  const steps = to.map((p, i) => ({
    dx: step(from[i].x, p.x, wraps[i].x),
    dy: step(from[i].y, p.y, wraps[i].y),
  }));
  const half = duration / 2;
  dataset.data = from.map((p, i) => ({
    x: p.x + steps[i].dx / 2,
    y: p.y + steps[i].dy / 2,
  }));
  chart.options.animation.duration = half;
  chart.update();
  _scheduleHighlight(() => {
    dataset.data = to.map((p, i) => ({
      x: p.x - steps[i].dx / 2,
      y: p.y - steps[i].dy / 2,
    }));
    chart.options.animation.duration = 0;
    chart.update("none");
    dataset.data = to;
    chart.options.animation.duration = half;
    chart.update();
  }, half);
}

const vehicleHeatmapPlugin = {
  id: "vehicleHeatmap",
  beforeDatasetsDraw(chart) {
    const grid = _currentInterpolatedHeatmapGrid();
    if (!grid) return;
    const { ctx, chartArea, scales } = chart;
    if (!chartArea) return;
    const blockWidthPx =
      Math.abs(scales.x.getPixelForValue(1) - scales.x.getPixelForValue(0)) *
      HEATMAP_BLOCK_SIZE;
    const blockHeightPx =
      Math.abs(scales.y.getPixelForValue(1) - scales.y.getPixelForValue(0)) *
      HEATMAP_BLOCK_SIZE;
    ctx.save();
    for (const [key, cell] of grid) {
      const color = _heatmapCellColor(cell);
      if (!color) continue;
      // key is a block index (see _computeVehicleHeatmapGrid); the block
      // spans city coordinates [x0 - 0.5, x0 + HEATMAP_BLOCK_SIZE - 0.5] in
      // each direction.
      const [blockX, blockY] = key.split(",").map(Number);
      const x0 = blockX * HEATMAP_BLOCK_SIZE;
      const y0 = blockY * HEATMAP_BLOCK_SIZE;
      const px = scales.x.getPixelForValue(x0 - 0.5);
      const py = scales.y.getPixelForValue(y0 + HEATMAP_BLOCK_SIZE - 0.5);
      ctx.fillStyle = color;
      ctx.fillRect(px, py, blockWidthPx, blockHeightPx);
    }
    ctx.restore();
  },
};

// Create a canvas-based vehicle point style with specific color
function createVehicleCanvas(color = "#ffff00", vehicleRadius = 8) {
  const canvas = document.createElement("canvas");
  const size = vehicleRadius * 2.5; // Canvas size based on vehicle radius
  canvas.width = size;
  canvas.height = size;

  const ctx = canvas.getContext("2d");
  const center = size / 2;

  // Save context and apply rotation
  ctx.save();
  ctx.translate(center, center);

  // Draw vehicle as rectangle
  const carLength = vehicleRadius * 1.6; // Front to back (long dimension)
  const carWidth = vehicleRadius * 1.0; // Side to side (short dimension)

  // Main car body (rounded rectangle) with specified color
  const cornerRadius = vehicleRadius * 0.2;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.roundRect(
    -carWidth / 2,
    -carLength / 2,
    carWidth,
    carLength,
    cornerRadius,
  );
  ctx.fill();
  ctx.strokeStyle = "grey";
  ctx.lineWidth = 1;
  ctx.stroke();

  // Wheels (small dark rectangles on sides)
  const wheelWidth = vehicleRadius * 0.2;
  const wheelLength = vehicleRadius * 0.4;
  const wheelOffset = carLength * 0.25; // Position wheels 25% from front/back
  ctx.fillStyle = "#333333";

  // Left wheels
  ctx.fillRect(
    -carWidth / 2 - wheelWidth / 2,
    -wheelOffset,
    wheelWidth,
    wheelLength,
  );
  ctx.fillRect(
    -carWidth / 2 - wheelWidth / 2,
    wheelOffset - wheelLength,
    wheelWidth,
    wheelLength,
  );

  // Right wheels
  ctx.fillRect(
    carWidth / 2 - wheelWidth / 2,
    -wheelOffset,
    wheelWidth,
    wheelLength,
  );
  ctx.fillRect(
    carWidth / 2 - wheelWidth / 2,
    wheelOffset - wheelLength,
    wheelWidth,
    wheelLength,
  );

  // Windshield area (larger, more defined front indicator)
  const windshieldWidth = carWidth * 0.6;
  const windshieldLength = vehicleRadius * 0.4;
  ctx.fillStyle = "#000000";
  ctx.beginPath();
  ctx.roundRect(
    -windshieldWidth / 2,
    -carLength / 2,
    windshieldWidth,
    windshieldLength,
    cornerRadius * 0.5,
  );
  ctx.fill();

  ctx.restore();
  return canvas;
}

// Create a canvas-based person point style with specific color
function createPersonCanvas(color = "#95ff6bff", personRadius = 8) {
  const canvas = document.createElement("canvas");
  const size = personRadius * 2.5; // Canvas size based on person radius
  canvas.width = size;
  canvas.height = size;

  const ctx = canvas.getContext("2d");
  const center = size / 2;

  // Save context
  ctx.save();
  ctx.translate(center, center);

  // Draw person as head + shoulders silhouette
  const headRadius = personRadius * 0.4;
  const shoulderWidth = personRadius * 1.2;
  const shoulderHeight = personRadius * 0.6;
  const neckWidth = personRadius * 0.25;
  const neckHeight = personRadius * 0.3;

  // Draw shoulders (rounded rectangle base)
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.roundRect(
    -shoulderWidth / 2,
    headRadius + neckHeight - shoulderHeight / 2,
    shoulderWidth,
    shoulderHeight,
    personRadius * 0.15,
  );
  ctx.fill();
  ctx.strokeStyle = "#333333";
  ctx.lineWidth = 1;
  ctx.stroke();

  // Draw neck (small rectangle connecting head to shoulders)
  ctx.fillStyle = color;
  ctx.fillRect(-neckWidth / 2, headRadius, neckWidth, neckHeight);

  // Draw head (circle)
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(0, 0, headRadius, 0, 2 * Math.PI);
  ctx.fill();
  ctx.strokeStyle = "#333333";
  ctx.lineWidth = 1;
  ctx.stroke();

  ctx.restore();
  return canvas;
}

// Get cached vehicle canvas or create new one
function getCachedVehicleCanvas(color, vehicleRadius) {
  const key = `${color}_${vehicleRadius}`;
  if (!vehicleCanvasCache.has(key)) {
    vehicleCanvasCache.set(key, createVehicleCanvas(color, vehicleRadius));
  }
  return vehicleCanvasCache.get(key);
}

// Create a canvas-based house point style with specific color
function createHouseCanvas(color = "#4ecdc4", houseRadius = 8) {
  const canvas = document.createElement("canvas");
  const size = houseRadius * 2.5; // Canvas size based on house radius
  canvas.width = size;
  canvas.height = size;

  const ctx = canvas.getContext("2d");
  const center = size / 2;

  // Save context
  ctx.save();
  ctx.translate(center, center);

  // Draw house as rectangle base + triangle roof
  const houseWidth = houseRadius * 1.3;
  const houseHeight = houseRadius * 0.8;
  const roofHeight = houseRadius * 0.6;

  // Draw main house body (rectangle)
  ctx.fillStyle = color;
  ctx.fillRect(
    -houseWidth / 2,
    -houseHeight / 2 + roofHeight / 2,
    houseWidth,
    houseHeight,
  );
  ctx.strokeStyle = "#333333";
  ctx.lineWidth = 1;
  ctx.strokeRect(
    -houseWidth / 2,
    -houseHeight / 2 + roofHeight / 2,
    houseWidth,
    houseHeight,
  );

  // Draw roof (triangle)
  ctx.fillStyle = color; // Same color as house body
  ctx.beginPath();
  ctx.moveTo(0, -houseHeight / 2 - roofHeight / 2); // Top point of roof
  ctx.lineTo(
    -houseWidth / 2 - houseRadius * 0.1,
    -houseHeight / 2 + roofHeight / 2,
  ); // Left base
  ctx.lineTo(
    houseWidth / 2 + houseRadius * 0.1,
    -houseHeight / 2 + roofHeight / 2,
  ); // Right base
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "#333333";
  ctx.lineWidth = 1;
  ctx.stroke();

  // Draw door (small rectangle in center of house)
  const doorWidth = houseWidth * 0.25;
  const doorHeight = houseHeight * 0.4;
  ctx.fillStyle = "#654321"; // Dark brown door
  ctx.fillRect(
    -doorWidth / 2,
    houseHeight / 2 - doorHeight + roofHeight / 2,
    doorWidth,
    doorHeight,
  );

  // Draw window (small square)
  const windowSize = houseWidth * 0.15;
  ctx.fillStyle = "#87CEEB"; // Light blue window
  ctx.fillRect(
    houseWidth * 0.15,
    -houseHeight * 0.1 + roofHeight / 2,
    windowSize,
    windowSize,
  );
  ctx.strokeStyle = "#333333";
  ctx.lineWidth = 1;
  ctx.strokeRect(
    houseWidth * 0.15,
    -houseHeight * 0.1 + roofHeight / 2,
    windowSize,
    windowSize,
  );

  ctx.restore();
  return canvas;
}

// Get cached person canvas or create new one
function getCachedPersonCanvas(color, personRadius) {
  const key = `${color}_${personRadius}`;
  if (!personCanvasCache.has(key)) {
    personCanvasCache.set(key, createPersonCanvas(color, personRadius));
  }
  return personCanvasCache.get(key);
}

// Get cached house canvas or create new one
function getCachedHouseCanvas(color, houseRadius) {
  const key = `${color}_${houseRadius}`;
  if (!houseCanvasCache.has(key)) {
    houseCanvasCache.set(key, createHouseCanvas(color, houseRadius));
  }
  return houseCanvasCache.get(key);
}

// ── Downtown core shading ───────────────────────────────────────────────────
// When inhomogeneity > 0, extra trip requests start in the central square of
// the city. mapCorePlugin shades that square in MAP_CORE, above the land and
// below the road grid (it runs straight after mapBackgroundPlugin, before the
// scales draw). _coreShading is {low, high}, the first intersection inside
// the core and the first one past it on each axis, or null for no shading.
let _coreShading = null;

function _updateCoreShading(size, inhomogeneity) {
  if (!size || !(inhomogeneity > 0)) {
    _coreShading = null;
    return;
  }
  // Same arithmetic as the simulation: City.two_zone_size and the
  // randrange() bounds in City.set_location (ridehail/atom.py)
  const zone = Math.floor(size * CITY_CORE_FRACTION);
  _coreShading = {
    low: Math.floor((size - zone) / 2),
    high: Math.floor((size + zone) / 2),
  };
}

const mapCorePlugin = {
  id: "mapCore",
  beforeDraw(chart) {
    if (!_coreShading || !chart.chartArea) return;
    const { x, y } = chart.scales;
    // Half a block beyond the outermost core intersections on each side, so
    // the shading covers the core's blocks, not just its intersections
    const x0 = x.getPixelForValue(_coreShading.low - 0.5);
    const x1 = x.getPixelForValue(_coreShading.high - 0.5);
    const y0 = y.getPixelForValue(_coreShading.low - 0.5);
    const y1 = y.getPixelForValue(_coreShading.high - 0.5);
    const { ctx } = chart;
    ctx.save();
    ctx.fillStyle = MAP_CORE;
    ctx.fillRect(Math.min(x0, x1), Math.min(y0, y1), Math.abs(x1 - x0), Math.abs(y1 - y0));
    ctx.restore();
  },
};

export function initMap(uiSettings, simSettings) {
  // data sets:
  // [0] - vehicles
  // [1] - trips
  citySize = simSettings.citySize;
  _updateCoreShading(citySize, simSettings.inhomogeneity);
  // Road width and vehicle radius are derived continuously from the city size
  // (see computeMapDisplaySizing) rather than from a per-preset UI setting.
  const displaySizing = computeMapDisplaySizing(citySize);
  vehicleRadius = displaySizing.vehicleRadius;
  const roadWidth = displaySizing.roadWidth;

  const mapOptions = {
    // Data is already in Chart.js's internal {x,y} format (vehicleLocations /
    // tripLocations) and the scales below set fixed min/max, so skip the
    // per-frame data parsing. (normalized:true is intentionally NOT set: scatter
    // points are not unique/sorted by index and it can mis-render.)
    parsing: false,
    // resize behaviour
    responsive: true,
    maintainAspectRatio: true,
    aspectRatio: 1,
    layout: {
      padding: 0,
      autoPadding: false,
    },
    scales: {
      x: {
        min: -0.5,
        max: citySize - 0.5,
        border: { display: false },
        grid: {
          lineWidth: roadWidth,
          color: colors.get("ROAD"),
          //drawOnChartArea: true,
          drawTicks: false,
        },
        type: "linear",
        ticks: {
          display: false,
          includeBounds: false,
          maxTicksLimits: citySize,
          drawTicks: false,
          stepSize: 0.5,
          callback: function (tick, index) {
            return index % 2 != 0 ? "" : null;
          },
        },
      },
      y: {
        min: -0.5,
        max: citySize - 0.5,
        border: { display: false },
        grid: {
          lineWidth: roadWidth,
          color: colors.get("ROAD"),
          drawTicks: false,
        },
        type: "linear",
        ticks: {
          display: false,
          includeBounds: false,
          maxTicksLimits: citySize,
          drawTicks: false,
          stepSize: 0.5,
          callback: function (value, index, ticks) {
            return index % 2 != 0 ? "" : null;
          },
        },
      },
    },
    elements: {
      line: {
        borderWidth: 0,
        tension: 0.4,
      },
    },
    transitions: {
      duration: 0,
      easing: "linear",
      delay: 0,
      loop: false,
    },
    animation: {
      duration: 0,
      easing: "linear",
      delay: 0,
      loop: false,
      // onComplete: function(animation){
      // animation.chart.data.datasets[0].pointBackgroundColor = 'rgba(0, 255, 0, 0.8)';
      // }
    },
    animations: {
      properties: ["x", "y"],
    },
    plugins: {
      legend: {
        display: false,
      },
      datalabels: {
        display: false,
      },
    },
  };

  const mapConfig = {
    type: "scatter",
    data: {
      datasets: [
        {
          // vehicles
          data: null,
          pointStyle: [], // Will be populated with individual vehicle canvases
          pointRadius: vehicleRadius,
          borderColor: "grey",
          borderWidth: 1,
          hoverRadius: 16,
        },
        {
          // trips
          data: null,
          pointStyle: "circle",
          pointRadius: vehicleRadius,
          borderColor: "grey",
          borderWidth: 1,
        },
      ],
    },
    options: mapOptions,
    // gameOverlayPlugin draws nothing unless the Game tab sets its state
    // Order matters: the core shading is painted over the land background
    plugins: [
      mapBackgroundPlugin,
      mapCorePlugin,
      vehicleHeatmapPlugin,
      gameOverlayPlugin,
    ],
  };
  //options: {}

  if (window.chart instanceof Chart) {
    window.chart.destroy();
  }

  // A new map starts without the Game tab's overlay; the Game tab sets it
  // after calling initMap.
  setGameOverlay(null);
  window.chart = new Chart(uiSettings.ctxMap, mapConfig);
  _resetHeatmapTransition();
  _heatmapEMA.clear();
  _heatmapSaturationLevel = null;
  _heatmapOverride = null;
  _lastEventData = null;
  _prevRidingTrip = { locations: [], colors: [], styles: [], radii: [] };
  _resetHighlightGlide();

  _sparklineHistory = [];
  _sparklineCtx = document.getElementById("map-sparkline")?.getContext("2d");
  const overlay = document.getElementById("map-metrics-overlay");
  if (overlay) {
    if (!overlay.dataset.clickHandlerAdded) {
      overlay.addEventListener("click", _toggleOverlayExpanded);
      overlay.dataset.clickHandlerAdded = "true";
    }
    _applyOverlayState(overlay, document.getElementById("map-sparkline"));
  }
}

/**
 * Size the (square) map to the largest square that fits the chart column's
 * available content box: side = min(width, height) - padding. This makes the
 * map fill the limiting viewport dimension (vertical or horizontal) and centre
 * in the leftover space of the other, across all zoom levels.
 *
 * The map is otherwise sized by width alone (CSS aspect-ratio + Chart.js
 * responsive sizing), so it ignores the freed vertical space when the page
 * header / controls are hidden by zoom. We measure and set explicit pixel
 * dimensions instead, then let Chart.js resize to the new container.
 */
export function fitMapToViewport() {
  const chartColumn = document.getElementById("chart-column");
  const mapParent = document.querySelector(".lab-map-canvas-parent");
  if (!chartColumn || !mapParent) return;

  // No-op when the map isn't the visible chart (stats mode hides the parent)
  // or the Experiment tab isn't active.
  if (mapParent.hidden || mapParent.offsetParent === null) return;

  const pad = 16; // small breathing room around the map
  const available = Math.min(chartColumn.clientWidth, chartColumn.clientHeight);
  const side = Math.max(0, available - pad);
  if (side === 0) return;

  mapParent.style.width = `${side}px`;
  mapParent.style.height = `${side}px`;

  requestAnimationFrame(() => {
    if (window.chart instanceof Chart) {
      window.chart.resize();
      window.chart.update("none");
    }
  });
}

/**
 * Update map visualization with current simulation state
 *
 * Renders vehicles and trip markers on the map. When a vehicle arrives at a
 * trip origin to pick up a passenger (pickup_countdown > 0), both the vehicle
 * and the trip marker are enlarged by 50% to subtly highlight the pickup moment.
 *
 * @param {Map} eventData - Simulation frame data containing vehicles, trips, and metadata
 */
export function plotMap(eventData) {
  try {
    if (eventData != null) {
      if (eventData.size < 2) {
        console.log("m: error? ", eventData);
      }
      _lastEventData = eventData;
      // Inhomogeneity is a live setting, so follow it every frame
      _updateCoreShading(citySize, eventData.get("inhomogeneity"));
      let frameIndex = eventData.get("frame");
      // Vehicle data format: [phase.name, location, direction, pickup_countdown]
      let vehicles = eventData.get("vehicles");
      let animationDelay = eventData.get("animationDelay");
      const useSimpleMarkers =
        vehicles.length > SIMPLE_MARKER_VEHICLE_THRESHOLD;
      // Same threshold as useSimpleMarkers: above it, vehicles are painted as
      // a density heatmap instead of individual points (see
      // vehicleHeatmapPlugin). Trip markers still use the plain-circle/rect
      // style controlled by useSimpleMarkers above. _heatmapOverride (set by
      // toggleHeatmapView, bound to "h") lets the user force either mode
      // regardless of vehicle count.
      const useHeatmap =
        _heatmapOverride !== null ? _heatmapOverride : useSimpleMarkers;
      _lastUseHeatmap = useHeatmap;
      // The car followed on the Experiment tab ("i"), if any. Game frames
      // leave the overlay to game-tab.js.
      if (!eventData.has("game")) {
        setGameOverlay(
          _followedOverlayState(eventData.get("followed"), useHeatmap),
        );
      }
      const snapMovement = citySize > SNAP_MOVEMENT_CITY_SIZE_THRESHOLD;
      let vehicleLocations = [];
      let vehicleColors = [];
      let vehicleStyles = [];
      let vehicleRotations = [];
      let vehicleRadii = [];
      // Vehicle data format: [phase, location, direction, pickup_countdown]
      // as an array, or the same fields as an object
      const addVehicle = (vehicle, radius, simple) => {
        const phase = vehicle.phase || vehicle[0];
        const location = vehicle.location || vehicle[1];
        const direction = vehicle.direction || vehicle[2];
        const pickupCountdown =
          vehicle.pickup_countdown !== undefined
            ? vehicle.pickup_countdown
            : vehicle[3] !== undefined
              ? vehicle[3]
              : null;

        const phaseColor = colors.get(phase);
        vehicleColors.push(phaseColor);
        vehicleLocations.push({ x: location[0], y: location[1] });

        // Check if vehicle is at pickup location (pickup_countdown > 0)
        // When true, enlarge the vehicle to highlight the pickup moment
        const isAtPickup =
          pickupCountdown !== null &&
          pickupCountdown !== undefined &&
          pickupCountdown > 0;

        // Increase vehicle size by 50% during pickup for visual emphasis
        const effectiveRadius = isAtPickup ? radius * 1.5 : radius;
        vehicleRadii.push(effectiveRadius);

        if (simple) {
          vehicleStyles.push("circle");
        } else {
          const vehicleCanvas = getCachedVehicleCanvas(
            phaseColor,
            effectiveRadius,
          );
          vehicleStyles.push(vehicleCanvas);
        }

        let rot = 0;
        if (direction == "NORTH") {
          rot = 0;
        } else if (direction == "EAST") {
          rot = 90;
        } else if (direction == "SOUTH") {
          rot = 180;
        } else if (direction == "WEST") {
          rot = 270;
        }
        vehicleRotations.push(rot);
      };
      // Positions (in the vehicle list) of the cars drawn individually over
      // the heatmap (see HIGHLIGHT_MIN_RADIUS), and their keys (see
      // _highlightedVehicles); null when every vehicle is drawn
      let highlighted = null;
      let highlightKeys = null;
      // A highlighted car crossed the torus edge since the last frame, so
      // snap it rather than glide it across the whole map
      let highlightWrapped = false;
      // Where each highlighted car was in the previous frame (or is now, if
      // it is new), for _glideHighlights
      const highlightFrom = [];
      if (useHeatmap) {
        const rawGrid = _computeVehicleHeatmapGrid(vehicles, citySize);
        _updateHeatmapEMA(rawGrid);
        _updateHeatmapSaturation(_heatmapEMA);
        _startHeatmapTransition(_heatmapEMA, animationDelay);
        const highlights = _highlightedVehicles(eventData, vehicles);
        highlighted = highlights.map(([position]) => position);
        highlightKeys = highlights.map(([, key]) => key);
        const highlightRadius = Math.max(vehicleRadius, HIGHLIGHT_MIN_RADIUS);
        const nextLocations = new Map();
        const nextHeadings = new Map();
        highlights.forEach(([position, key]) => {
          addVehicle(vehicles[position], highlightRadius, false);
          const i = vehicleLocations.length - 1;
          const location = vehicleLocations[i];
          const prev = _prevHighlightLocations.get(key);
          if (
            prev &&
            (Math.abs(location.x - prev.x) > 1 ||
              Math.abs(location.y - prev.y) > 1)
          ) {
            highlightWrapped = true;
          }
          if (snapMovement) {
            // Face the way the car moves this frame (see
            // _highlightHeadings); a stationary car keeps its heading
            const heading = prev
              ? _headingForStep(location.x - prev.x, location.y - prev.y)
              : null;
            vehicleRotations[i] =
              heading ?? _highlightHeadings.get(key) ?? vehicleRotations[i];
            nextHeadings.set(key, vehicleRotations[i]);
          }
          highlightFrom.push(prev ?? location);
          nextLocations.set(key, location);
        });
        _prevHighlightLocations = nextLocations;
        _highlightHeadings = nextHeadings;
      } else {
        _resetHeatmapTransition();
        // Drop smoothed history while not in heatmap mode, so re-enabling it
        // later (toggleHeatmapView) starts from a clean, empty grid rather
        // than resuming stale decayed counts.
        _heatmapEMA.clear();
        _heatmapSaturationLevel = null;
        _resetHighlightGlide();
        // useHeatmap vehicles never reach this branch - they're binned into
        // _heatmapEMA above instead. But useSimpleMarkers can still be true
        // here (heatmap manually toggled off above its vehicle-count
        // threshold via toggleHeatmapView/"h"), so fall back to the same
        // plain-circle style trip markers use at that threshold rather than
        // the per-vehicle canvas icon, which doesn't scale to that count.
        vehicles.forEach((vehicle) =>
          addVehicle(vehicle, vehicleRadius, useSimpleMarkers),
        );
      }

      // Build a set of pickup locations to match with trip markers
      // This allows us to enlarge trip markers when a vehicle is picking up at that location
      const pickupLocations = new Set();
      vehicles.forEach((vehicle) => {
        const pickupCountdown =
          vehicle.pickup_countdown !== undefined
            ? vehicle.pickup_countdown
            : vehicle[3] !== undefined
              ? vehicle[3]
              : null;
        if (
          pickupCountdown !== null &&
          pickupCountdown !== undefined &&
          pickupCountdown > 0
        ) {
          const loc = vehicle.location || vehicle[1];
          pickupLocations.add(`${loc[0]},${loc[1]}`);
        }
      });

      // Process trip markers (trip origins and destinations)
      // Built into two separate arrays so each can be cached at its own
      // frame parity (see the cache-update block below the loop).
      let trips = eventData.get("trips");
      let originLocations = [], originColors = [], originStyles = [], originRadii = [];
      let ridingLocations = [], ridingColors = [], ridingStyles = [], ridingRadii = [];
      trips.forEach((trip) => {
        /* Trip phases: INACTIVE = 0, UNASSIGNED = 1, WAITING = 2
                      RIDING = 3, COMPLETED = 4, CANCELLED = 5 */
        if (trip[0] == "UNASSIGNED" || trip[0] == "WAITING") {
          const tripLoc = { x: trip[1][0], y: trip[1][1] };
          originLocations.push(tripLoc);

          if (useHeatmap) {
            // Muted fixed-size dot instead of a full person icon - see
            // HEATMAP_TRIP_DOT_COLOR above.
            originColors.push(HEATMAP_TRIP_DOT_COLOR);
            originStyles.push("circle");
            originRadii.push(HEATMAP_TRIP_DOT_RADIUS);
            return;
          }

          // Waiting riders are always drawn in the shared waiting-rider color
          // (muted pink) rather than the per-state pink/amber phase color, so a
          // waiting rider reads the same regardless of dispatch state; the "a
          // car is arriving here" cue is carried by the 1.5x marker enlargement
          // below (isBeingPickedUp) instead of a color change.
          const tripColor = WAITING_RIDER_COLOR;
          originColors.push(tripColor);

          // Enlarge trip marker if a vehicle is picking up at this location
          const isBeingPickedUp = pickupLocations.has(
            `${tripLoc.x},${tripLoc.y}`,
          );
          const effectiveRadius = isBeingPickedUp
            ? vehicleRadius * 1.5
            : vehicleRadius;
          originRadii.push(effectiveRadius);

          if (useSimpleMarkers) {
            // Plain vector point for trip origins (passengers waiting)
            originStyles.push("circle");
          } else {
            // Use person canvas for trip origins (passengers waiting)
            const personCanvas = getCachedPersonCanvas(
              tripColor,
              effectiveRadius,
            );
            originStyles.push(personCanvas);
          }
        } else if (trip[0] == "RIDING") {
          // Dropped entirely in heatmap mode - redundant with the vehicle
          // heatmap's own P3 (occupied) density.
          if (useHeatmap) return;
          ridingLocations.push({ x: trip[2][0], y: trip[2][1] });
          const tripColor = colors.get(trip[0]);
          ridingColors.push(tripColor);
          ridingRadii.push(vehicleRadius);
          if (useSimpleMarkers) {
            // Plain vector point for trip destinations (riders in transit)
            ridingStyles.push("rect");
          } else {
            // Use house canvas for trip destinations
            const houseCanvas = getCachedHouseCanvas(tripColor, vehicleRadius);
            ridingStyles.push(houseCanvas);
          }
        }
      });

      // Origins are applied directly (no buffering): the worker sends the same
      // trip data on both frames of an even/odd pair, so the origin set never
      // changes within a pair, and applying it every frame keeps the dispatch
      // person icon in sync with the even-frame P2 color change.
      // Destinations are lagged by one frame so a RIDING house marker survives
      // the even-frame animation that carries the vehicle to it, disappearing
      // only on the following frame once the vehicle has arrived. snapMovement
      // emits no interpolated frames, so the lag is bypassed there.
      const ridingTrip = snapMovement
        ? {
            locations: ridingLocations,
            colors: ridingColors,
            styles: ridingStyles,
            radii: ridingRadii,
          }
        : _prevRidingTrip;
      _prevRidingTrip = {
        locations: ridingLocations,
        colors: ridingColors,
        styles: ridingStyles,
        radii: ridingRadii,
      };
      const tripLocations = [...originLocations, ...ridingTrip.locations];
      const tripColors = [...originColors, ...ridingTrip.colors];
      const tripStyles = [...originStyles, ...ridingTrip.styles];
      const tripRadii = [...originRadii, ...ridingTrip.radii];
      // Update chart with vehicle and trip data.
      // Even frames carry pending_results from worker.py: real block positions
      // with vehicle phases and trip list both from the same simulation block.
      // Odd frames carry midpoint positions with the *previous* block's trips
      // deliberately held back (worker.py line 443).
      // Trip markers are always applied here; their timing is set above, where
      // origins use the current frame and destinations lag by one frame.
      window.chart.data.datasets[1].pointBackgroundColor = tripColors;
      window.chart.data.datasets[1].pointStyle = tripStyles;
      window.chart.data.datasets[1].pointRadius = tripRadii;
      window.chart.data.datasets[1].animationDuration = 0;
      window.chart.data.datasets[1].data = tripLocations;
      _cancelHighlightTimers();
      // A whole-block glide of the highlighted cars (see _highlightHeadings):
      // from the second frame on, while the same cars are highlighted
      const glide =
        useHeatmap &&
        snapMovement &&
        frameIndex != 0 &&
        animationDelay > 0 &&
        highlighted.length > 0 &&
        _highlightArrivalStyle !== null &&
        _sameKeys(_highlightArrivalStyle.keys, highlightKeys);
      const arrivalStyle = {
        keys: highlightKeys,
        colors: vehicleColors,
        styles: vehicleStyles,
        radii: vehicleRadii,
      };
      if (glide) {
        // Set off in the style the car had on reaching its last
        // intersection, and take this frame's style on arriving at the next
        _applyHighlightStyle(_highlightArrivalStyle);
        _highlightArrivalStyle = arrivalStyle;
        window.chart.data.datasets[0].rotation = vehicleRotations;
        window.chart.data.datasets[0].vehicleIndexes = highlighted;
        _glideHighlights(highlightFrom, vehicleLocations, animationDelay);
        _scheduleHighlight(() => {
          _applyHighlightStyle(arrivalStyle);
          window.chart.options.animation.duration = 0;
          window.chart.update("none");
        }, animationDelay);
      } else {
        _highlightArrivalStyle =
          useHeatmap && snapMovement ? arrivalStyle : null;
        // Vehicle color/style: even frames only (pending_results carries
        // synchronized vehicle phase + trips from the same simulation block).
        // In heatmap mode these arrays hold only the highlighted cars.
        if (snapMovement || frameIndex % 2 == 0) {
          window.chart.data.datasets[0].pointBackgroundColor = vehicleColors;
          window.chart.data.datasets[0].pointStyle = vehicleStyles;
          window.chart.data.datasets[0].pointRadius = vehicleRadii;
        }
        // Vehicle rotation: odd frames carry prev_dir — the direction actually
        // being traveled this half-step — so the turn becomes visible exactly
        // when the vehicle starts moving away from the intersection, not during
        // the animation arriving at it. Frame 0 is included for the initial render.
        if (snapMovement || frameIndex % 2 != 0 || frameIndex === 0) {
          window.chart.data.datasets[0].rotation = vehicleRotations;
        }
        window.chart.options.animation.duration = 0;
        window.chart.update("none");
        // In heatmap mode vehicles are painted by vehicleHeatmapPlugin from the
        // interpolated heatmap grid (see _currentInterpolatedHeatmapGrid), and
        // dataset 0 holds only the highlighted cars, if any. vehicleIndexes
        // maps its points back to vehicle indexes (game-map-overlay.js).
        window.chart.data.datasets[0].data = vehicleLocations;
        window.chart.data.datasets[0].vehicleIndexes = highlighted;
        if (useHeatmap) {
          // The few highlighted cars glide even where snapMovement holds the
          // full fleet still: without interpolated frames each frame moves
          // them one block, so only a torus wrap needs a snap.
          window.chart.options.animation.duration =
            frameIndex == 0 || highlightWrapped ? 0 : animationDelay;
        } else if (
          frameIndex == 0 ||
          snapMovement ||
          // Vehicles were removed, shifting the cars after them along the
          // list: each point now belongs to a different car, which would
          // glide in from its predecessor's place (see worker.py)
          eventData.get("reindexed")
        ) {
          window.chart.options.animation.duration = 0;
        } else {
          window.chart.options.animation.duration = animationDelay;
        }

        window.chart.update();
      }
      // Same reasoning as the snapMovement check above: without interpolated
      // frames, every frame is a real block worth recording, not just evens.
      if (snapMovement || frameIndex % 2 === 0) {
        _updateMetricsOverlay(eventData);
      }
      // Edge-wrap teleport: only relevant to scatter-point vehicles (in
      // heatmap mode, the highlighted ones), whose interpolated position can
      // overshoot the chart's coordinate range and needs an instant snap
      // back. Heatmap cells are rebinned straight from raw (modulo-wrapped)
      // location every frame, so there's no equivalent overshoot to correct.
      let needsRefresh = false;
      let updatedLocations = [];
      vehicleLocations.forEach((vehicle) => {
        let newX = vehicle.x;
        let newY = vehicle.y;
        if (vehicle.x > citySize - 0.6) {
          // going off the right side
          newX = -0.5;
          needsRefresh = true;
        }
        if (vehicle.x < -0.1) {
          // going off the left side
          newX = citySize - 0.5;
          needsRefresh = true;
        }
        if (vehicle.y > citySize - 0.9) {
          // going off the top
          newY = -0.5;
          needsRefresh = true;
        }
        if (vehicle.y < -0.1) {
          // going off the bottom
          newY = citySize - 0.5;
          needsRefresh = true;
        }
        updatedLocations.push({ x: newX, y: newY });
      });
      if (needsRefresh == true) {
        // Reappear on the opposite  side of the chart
        // time = Math.round((Date.now() - startTime) / 100) * 100;
        // console.log("m (", time, "): Edge-updated chart: locations[0] = ", updatedLocations[0]);
        window.chart.data.datasets[0].pointBackgroundColor = vehicleColors;
        window.chart.data.datasets[0].pointStyle = vehicleStyles;
        window.chart.data.datasets[0].rotation = vehicleRotations;
        window.chart.update("none");
        window.chart.data.datasets[0].data = updatedLocations;
        window.chart.data.datasets[0].pointBackgroundColor = vehicleColors;
        window.chart.data.datasets[0].pointStyle = vehicleStyles;
        window.chart.update("none");
      }
    }
  } catch (error) {
    console.log("Error in plotMap: ", error.message);
    console.error("-- stack trace:", error.stack);
  }
}

// Compute expanded canvas size: fill essentially the whole map (map is square).
// Width leaves room for the overlay's left offset (6px) and 8px horizontal
// padding on each side. The HTML phase-label row is hidden in expanded mode (the
// labels move onto the chart), so the only vertical overhead is the bottom anchor
// (~5% + 4px) plus the overlay's vertical padding (~16px).
function _getExpandedCanvasSize() {
  const containerW =
    document.getElementById("map-metrics-overlay")?.parentElement
      ?.clientWidth ?? 440;
  const w = Math.max(containerW - 28, 200);
  const h = Math.max(Math.round(containerW * 0.95) - 16, 60);
  return { w, h };
}

function _updateMetricsOverlay(eventData) {
  const p1 = eventData.get("VEHICLE_FRACTION_P1") ?? 0;
  const p2 = eventData.get("VEHICLE_FRACTION_P2") ?? 0;
  const p3 = eventData.get("VEHICLE_FRACTION_P3") ?? 0;
  const waitFrac = eventData.get("TRIP_MEAN_WAIT_FRACTION_TOTAL");

  _sparklineHistory.push({ p1, p2, p3, wait: waitFrac ?? 0 });
  if (_sparklineHistory.length > SPARKLINE_MAX) _sparklineHistory.shift();

  const pct = (v) => Math.round(v * 100) + "%";
  document.getElementById("map-metric-p1").textContent = "P1 " + pct(p1);
  document.getElementById("map-metric-p2").textContent = "P2 " + pct(p2);
  document.getElementById("map-metric-p3").textContent = "P3 " + pct(p3);
  document.getElementById("map-metric-wait").textContent =
    waitFrac != null && waitFrac > 0 ? "Wait " + pct(waitFrac) : "Wait --";

  _drawSparkline();
}

function _applyOverlayState(overlay, canvas) {
  if (!overlay || !canvas) return;
  if (_overlayState === "hidden") {
    overlay.setAttribute("hidden", "");
    return;
  }
  overlay.removeAttribute("hidden");
  const expanded = _overlayState === "expanded";
  const sc = expanded ? _getExpandedCanvasSize() : SPARKLINE_COMPACT;
  canvas.width = sc.w;
  canvas.height = sc.h;
  overlay.classList.toggle("expanded", expanded);
  overlay.title = expanded ? "Click to collapse" : "Click to expand";
  _drawSparkline();
}

function _toggleOverlayExpanded() {
  // Click on overlay cycles only between compact and expanded (never hidden)
  _overlayState = _overlayState === "expanded" ? "compact" : "expanded";
  const overlay = document.getElementById("map-metrics-overlay");
  const canvas = document.getElementById("map-sparkline");
  _applyOverlayState(overlay, canvas);
}

export function cycleThumbnailState() {
  const states = ["compact", "expanded", "hidden"];
  const i = states.indexOf(_overlayState);
  _overlayState = states[(i + 1) % 3];
  const overlay = document.getElementById("map-metrics-overlay");
  const canvas = document.getElementById("map-sparkline");
  _applyOverlayState(overlay, canvas);
  return _overlayState;
}

/**
 * Manually toggle between the vehicle density heatmap and the per-vehicle
 * icon/trip-marker view, overriding the automatic vehicle-count threshold
 * for the rest of the current simulation (reset on the next initMap). Forces
 * an immediate redraw from the most recent frame so the change is visible
 * even while paused.
 * @returns {boolean} true if the map is now showing the heatmap, false if showing vehicles
 */
/**
 * Show a newly followed car (or none) on the frame already on screen, from
 * the worker's reply to a FollowVehicle message (see keyboard-handler.js),
 * so that it appears at once even while paused; frames carry it from then
 * on. Over the heatmap the car is drawn individually, so the frame is
 * redrawn; otherwise the overlay alone changes.
 * @param {object|null} followed - as a frame's "followed"
 */
export function showFollowedVehicle(followed) {
  if (_lastEventData == null || _lastEventData.has("game")) return;
  _lastEventData.set("followed", followed);
  if (_lastUseHeatmap) {
    plotMap(_lastEventData);
  } else {
    setGameOverlay(_followedOverlayState(followed, false));
    window.chart?.draw();
  }
  if (followed?.position != null) pulseGameCar();
}

export function toggleHeatmapView() {
  _heatmapOverride = !_lastUseHeatmap;
  if (_lastEventData != null) {
    plotMap(_lastEventData);
  }
  return _heatmapOverride;
}

function _drawSparkline() {
  const expanded = _overlayState === "expanded";
  // In expanded mode, a right-hand gutter holds end-of-line value labels
  // (matching the desktop charts, where labels sit at the right end of each
  // line rather than in a separate legend below the chart); the compact view
  // keeps the HTML phase labels above the chart.
  drawMetricsSparkline(_sparklineCtx, _sparklineHistory, {
    solidLines: SPARKLINE_SOLID_LINES,
    dashedLines: SPARKLINE_DASHED_LINES,
    labels: expanded,
    labelFont: 13,
    gutter: 64,
    lineWidth: expanded ? 2 : 1.5,
  });
}
