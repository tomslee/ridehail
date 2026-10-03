/**
 * Game tab map overlay: a Chart.js plugin, registered on the map by initMap,
 * that draws on top of the vehicles
 *   - a ring around the player's car, at its *animated* position (so it
 *     follows the car smoothly between frames), and on request
 *     (pulseGameCar) a short "here you are" pulse of expanding rings,
 *   - while an offer is on screen: a dimming wash over the city, and the
 *     offered route car -> pickup -> drop-off,
 *   - otherwise, a light guide line to where the player is heading (pickup
 *     while dispatched, drop-off with a rider).
 *
 * The plugin draws nothing unless the Game tab has set state with
 * setGameOverlay(), so it is inert on the Experiment tab's map.
 */

import { colors } from "../js/constants.js";

let _state = null;
// performance.now() when the current pulse started, or null
let _pulseStart = null;
let _pulseFrame = null;

/**
 * @param {object|null} state - null to switch the overlay off, or
 *   {player, citySize, phase, target, offer}: player is the vehicle index;
 *   target is the [x, y] the player is heading to (or null); offer is the
 *   pending offer from worker.py (with pickup and dropoff), or null.
 */
export function setGameOverlay(state) {
  _state = state;
  if (state === null && _pulseFrame !== null) {
    // The game stopped (its map may be about to be destroyed): no more draws
    cancelAnimationFrame(_pulseFrame);
    _pulseFrame = null;
    _pulseStart = null;
  }
}

// Violet: a colour nothing else on the map uses (phases, waiting riders,
// downtown), so the player's car stands out. Matches --game-you in style.css.
const RING_COLOR = "#7c3aed";
const HALO_COLOR = "rgba(255, 255, 255, 0.95)";
// The pulse: PULSE_RINGS rings, PULSE_STAGGER_MS apart, each growing from
// the ring's size to PULSE_GROW times it and fading out over PULSE_RING_MS
const PULSE_RINGS = 3;
const PULSE_STAGGER_MS = 250;
const PULSE_RING_MS = 1000;
const PULSE_GROW = 3;
const PULSE_MS = (PULSE_RINGS - 1) * PULSE_STAGGER_MS + PULSE_RING_MS;
const PULSE_RGB = "124, 58, 237"; // RING_COLOR
// Light enough that the offered route, drawn over it, stays easy to see
const DIM_COLOR = "rgba(20, 24, 33, 0.14)";
const PICKUP_COLOR = "rgba(237, 100, 149, 1)";
const DROPOFF_COLOR = "rgba(60, 179, 113, 1)";

/**
 * Play a short "here you are" pulse around the player's car (about 1.5 s).
 * The map is redrawn every animation frame while it plays; with reduced
 * motion, or with no map (phones), it does nothing.
 */
export function pulseGameCar() {
  if (!window.chart || window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
    return;
  }
  _pulseStart = performance.now();
  if (_pulseFrame !== null) return; // already animating: just restart
  const step = () => {
    window.chart?.draw();
    if (_pulseStart !== null && performance.now() - _pulseStart < PULSE_MS) {
      _pulseFrame = requestAnimationFrame(step);
    } else {
      _pulseStart = null;
      _pulseFrame = null;
      window.chart?.draw(); // clear the last ring
    }
  };
  _pulseFrame = requestAnimationFrame(step);
}

/** Expanding, fading rings around (x, y), if a pulse is playing. */
function drawPulse(ctx, x, y, ringRadius) {
  if (_pulseStart === null) return;
  const elapsed = performance.now() - _pulseStart;
  for (let i = 0; i < PULSE_RINGS; i++) {
    const t = (elapsed - i * PULSE_STAGGER_MS) / PULSE_RING_MS;
    if (t <= 0 || t >= 1) continue;
    const eased = 1 - (1 - t) ** 2; // fast out, slowing as it grows
    ctx.lineWidth = 4 * (1 - t) + 1;
    ctx.strokeStyle = `rgba(${PULSE_RGB}, ${0.85 * (1 - t)})`;
    ctx.beginPath();
    ctx.arc(x, y, ringRadius * (1 + (PULSE_GROW - 1) * eased), 0, 2 * Math.PI);
    ctx.stroke();
  }
}

/** Pixel position of city coordinates. */
function toPixel(chart, point) {
  return {
    x: chart.scales.x.getPixelForValue(point[0]),
    y: chart.scales.y.getPixelForValue(point[1]),
  };
}

/**
 * The shortest torus displacement from a to b, in city units, so that a
 * route drawn across an edge goes the short way (as the cars do).
 */
function torusDelta(a, b, size) {
  return [0, 1].map((i) => {
    let d = b[i] - a[i];
    if (d > size / 2) d -= size;
    if (d < -size / 2) d += size;
    return d;
  });
}

/**
 * Draw a dashed segment from city point a along the torus-shortest path to
 * b. If it leaves the city, draw the wrapped continuation from the opposite
 * edge too (the canvas is clipped to the chart area).
 */
function drawSegment(chart, a, b, size) {
  const d = torusDelta(a, b, size);
  const end = [a[0] + d[0], a[1] + d[1]];
  const shifts = [[0, 0]];
  const shift = [0, 1].map((i) =>
    end[i] > size - 0.5 ? -size : end[i] < -0.5 ? size : 0,
  );
  if (shift[0] || shift[1]) {
    shifts.push(shift);
  }
  const ctx = chart.ctx;
  for (const [sx, sy] of shifts) {
    const p0 = toPixel(chart, [a[0] + sx, a[1] + sy]);
    const p1 = toPixel(chart, [end[0] + sx, end[1] + sy]);
    ctx.beginPath();
    ctx.moveTo(p0.x, p0.y);
    ctx.lineTo(p1.x, p1.y);
    ctx.stroke();
  }
}

function drawMarker(chart, point, color, radius, square) {
  const ctx = chart.ctx;
  const p = toPixel(chart, point);
  ctx.save();
  ctx.setLineDash([]);
  ctx.lineWidth = 3;
  ctx.strokeStyle = HALO_COLOR;
  ctx.fillStyle = color;
  ctx.beginPath();
  if (square) {
    ctx.rect(p.x - radius, p.y - radius, 2 * radius, 2 * radius);
  } else {
    ctx.arc(p.x, p.y, radius, 0, 2 * Math.PI);
  }
  ctx.fill();
  ctx.stroke();
  ctx.restore();
}

export const gameOverlayPlugin = {
  id: "gameOverlay",
  afterDatasetsDraw(chart) {
    const state = _state;
    if (!state || state.player == null) return;
    // In heatmap mode the vehicle dataset holds only the highlighted cars,
    // and vehicleIndexes maps its points back to vehicle indexes (map.js)
    const indexes = chart.data.datasets[0]?.vehicleIndexes;
    const point = indexes ? indexes.indexOf(state.player) : state.player;
    const element = chart.getDatasetMeta(0)?.data?.[point];
    if (!element) return;
    // Animated (in-flight) position, not the frame's target position
    const { x, y } = element.getProps(["x", "y"], false);
    if (!Number.isFinite(x) || !Number.isFinite(y)) return;
    const radius = element.options?.radius || 8;
    const size = state.citySize;
    // The player's car in city units, from its animated pixel position
    const car = [
      chart.scales.x.getValueForPixel(x),
      chart.scales.y.getValueForPixel(y),
    ];
    const area = chart.chartArea;
    const ctx = chart.ctx;

    ctx.save();
    ctx.beginPath();
    ctx.rect(area.left, area.top, area.right - area.left, area.bottom - area.top);
    ctx.clip();

    if (state.offer) {
      ctx.fillStyle = DIM_COLOR;
      ctx.fillRect(area.left, area.top, area.right - area.left, area.bottom - area.top);
      ctx.lineCap = "round";
      ctx.setLineDash([radius * 0.8, radius * 0.6]);
      // Pickup leg: car -> pickup
      ctx.lineWidth = Math.max(2, radius * 0.35);
      ctx.strokeStyle = colors.get("P2").replace("0.5)", "1)");
      drawSegment(chart, car, state.offer.pickup, size);
      // Paid leg: pickup -> drop-off
      ctx.lineWidth = Math.max(3, radius * 0.5);
      ctx.strokeStyle = DROPOFF_COLOR;
      drawSegment(chart, state.offer.pickup, state.offer.dropoff, size);
      drawMarker(chart, state.offer.pickup, PICKUP_COLOR, radius * 0.7, false);
      drawMarker(chart, state.offer.dropoff, DROPOFF_COLOR, radius * 0.7, true);
    } else if (state.target) {
      ctx.setLineDash([radius * 0.5, radius * 0.5]);
      ctx.lineWidth = 2;
      ctx.strokeStyle =
        state.phase === "P3" ? DROPOFF_COLOR : colors.get("P2").replace("0.5)", "1)");
      drawSegment(chart, car, state.target, size);
      drawMarker(
        chart,
        state.target,
        state.phase === "P3" ? DROPOFF_COLOR : PICKUP_COLOR,
        radius * 0.45,
        state.phase === "P3",
      );
    }

    // The player's car: violet ring with a white halo either side (so it
    // shows on the grey land and on downtown), drawn last so it stays
    // visible above the dimming wash
    ctx.setLineDash([]);
    drawPulse(ctx, x, y, radius * 2);
    ctx.lineWidth = 8;
    ctx.strokeStyle = HALO_COLOR;
    ctx.beginPath();
    ctx.arc(x, y, radius * 2, 0, 2 * Math.PI);
    ctx.stroke();
    ctx.lineWidth = 4;
    ctx.strokeStyle = RING_COLOR;
    ctx.stroke();
    ctx.restore();
  },
};
