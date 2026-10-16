/**
 * Record a map as a video file (claude/animation-export-spec.md).
 *
 * Each map with a record button (the Experiment tab's map and the game's map;
 * see TARGETS) can be recorded: the button starts a MediaRecorder, and
 * pressing it again stops it and downloads the video (MP4 where the browser
 * can write it, else WebM). What is recorded is exactly what the map draws,
 * in real time: the vehicle and trip markers, the eased movement between
 * frames, canvas overlays such as the game's ring round the player's car, the
 * current theme. HTML overlays (the metrics panel, the game's offer card,
 * the button itself) are not included. One recording runs at a time.
 *
 * Frames are not taken from the map canvas directly. Each animation frame,
 * the map's plot area (Chart.js chartArea, the land square) is copied onto a
 * hidden recording canvas of fixed size, and that canvas is recorded. So:
 *  - the video is the map square only, with no transparent margins (which
 *    encode as black);
 *  - recording survives a Reset, a new shift or a resize, which re-create the
 *    Chart.js chart and its canvas: the copy just follows the current one.
 * The recording stops and saves when its map stops being shown: another tab
 * or game screen, or the Experiment display switched to Statistics.
 */

import { appState } from "./app-state.js";
import { CHART_TYPES } from "./config.js";
import { themeColor } from "./theme.js";
import { showError, showSuccess } from "./toast.js";

// The recordable maps. canvasId is the Chart.js map canvas, which initMap may
// replace; isShown says whether the map is still on show (the button is in
// the page layout, plus anything specific to the map)
const TARGETS = [
  {
    buttonId: "map-record-button",
    canvasId: "lab-map-chart-canvas",
    filePrefix: () => {
      const title = slug(appState.labSimSettings?.title);
      return `ridehail-map${title ? "-" + title : ""}`;
    },
    isShown: () => appState.labUISettings.chartType === CHART_TYPES.MAP,
  },
  {
    buttonId: "game-record-button",
    canvasId: "game-map-canvas",
    filePrefix: () => "ridehail-game",
    isShown: () => true,
  },
];

// Capture rate of the recording canvas, and the cap on its side in pixels
// (video encoders need even dimensions)
const CAPTURE_FPS = 30;
const MAX_SIDE = 1080;
// Preferred containers, best first: MP4 plays everywhere (Safari included);
// WebM is the fallback for browsers that can't write MP4
const MIME_TYPES = [
  "video/mp4;codecs=avc1",
  "video/mp4",
  "video/webm;codecs=vp9",
  "video/webm;codecs=vp8",
  "video/webm",
];

// The recording in progress (null when none): its target, button parts,
// MediaRecorder and recording canvas
let active = null;

function slug(text) {
  return String(text ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
}

function supportedMimeType() {
  if (!window.MediaRecorder) return null;
  return MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type)) ?? null;
}

// The Chart.js map on the target's canvas, when it is the current chart
function currentMapChart(target) {
  const chart = window.chart;
  if (!chart?.canvas || chart.canvas.id !== target.canvasId || !chart.chartArea) {
    return null;
  }
  return chart;
}

// The map's plot area in canvas pixels
function sourceRect(chart) {
  const ratio = chart.currentDevicePixelRatio || 1;
  const { left, top, width, height } = chart.chartArea;
  return {
    x: left * ratio,
    y: top * ratio,
    w: width * ratio,
    h: height * ratio,
  };
}

function evenSide(pixels) {
  const side = Math.min(Math.round(pixels), MAX_SIDE);
  return side - (side % 2);
}

function copyFrame() {
  active.frameRequest = requestAnimationFrame(copyFrame);
  // A button out of the layout (offsetParent null) means its tab or screen
  // is no longer shown
  if (active.button.offsetParent === null || !active.target.isShown()) {
    stopRecording();
    return;
  }
  const chart = currentMapChart(active.target);
  // Between a Reset's teardown and the new chart's first draw there is no
  // map: keep the last frame
  if (!chart) return;
  const src = sourceRect(chart);
  const canvas = active.canvas;
  const ctx = canvas.getContext("2d");
  ctx.fillStyle = themeColor("LAND");
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(
    chart.canvas,
    src.x,
    src.y,
    src.w,
    src.h,
    0,
    0,
    canvas.width,
    canvas.height,
  );
}

function fileName(target, mimeType) {
  const extension = mimeType.startsWith("video/mp4") ? "mp4" : "webm";
  const stamp = new Date()
    .toISOString()
    .slice(0, 19)
    .replace(/:/g, "-")
    .replace("T", "_");
  return `${target.filePrefix()}_${stamp}.${extension}`;
}

function download(blob, name) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = name;
  document.body.appendChild(link);
  link.click();
  link.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}

function formatElapsed(ms) {
  const seconds = Math.floor(ms / 1000);
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, "0")}`;
}

function setButtonState(button, recording) {
  const icon = button.querySelector(".map-record-button__icon");
  const label = button.querySelector(".map-record-button__time");
  button.classList.toggle("is-recording", recording);
  button.setAttribute("aria-pressed", String(recording));
  button.title = recording
    ? "Stop recording and download the video"
    : "Record the map as a video";
  icon.textContent = recording ? "stop_circle" : "videocam";
  label.textContent = recording ? "0:00" : "";
  label.hidden = !recording;
}

function startRecording(target, button) {
  const mimeType = supportedMimeType();
  const chart = currentMapChart(target);
  if (!mimeType || !chart) {
    showError("The map can't be recorded now");
    return;
  }
  const src = sourceRect(chart);
  const canvas = document.createElement("canvas");
  canvas.width = evenSide(src.w);
  canvas.height = evenSide(src.h);
  active = { target, button, canvas, chunks: [], frameRequest: null };
  copyFrame();

  let recorder;
  try {
    recorder = new MediaRecorder(canvas.captureStream(CAPTURE_FPS), {
      mimeType,
    });
  } catch (error) {
    console.error("map-recorder: MediaRecorder failed", error);
    cancelAnimationFrame(active.frameRequest);
    active = null;
    showError("The map can't be recorded in this browser");
    return;
  }
  const chunks = active.chunks;
  recorder.ondataavailable = (event) => {
    if (event.data.size > 0) chunks.push(event.data);
  };
  recorder.onstop = () => {
    const blob = new Blob(chunks, { type: mimeType });
    if (blob.size > 0) {
      const name = fileName(target, mimeType);
      download(blob, name);
      showSuccess(`Map video saved: ${name}`);
    }
  };
  active.recorder = recorder;
  // Collect data every second, so a long recording isn't held in one piece
  recorder.start(1000);
  const startTime = performance.now();
  setButtonState(button, true);
  const label = button.querySelector(".map-record-button__time");
  active.timerInterval = setInterval(() => {
    label.textContent = formatElapsed(performance.now() - startTime);
  }, 250);
}

export function stopRecording() {
  if (!active) return;
  const { recorder, button, frameRequest, timerInterval } = active;
  active = null;
  cancelAnimationFrame(frameRequest);
  clearInterval(timerInterval);
  if (recorder && recorder.state !== "inactive") recorder.stop();
  setButtonState(button, false);
}

export function isRecording() {
  return active !== null;
}

function toggleRecording(target, button) {
  if (active) {
    const wasThisMap = active.button === button;
    stopRecording();
    if (wasThisMap) return;
  }
  startRecording(target, button);
}

/**
 * Wire up the maps' record buttons. They stay hidden where the browser can't
 * record a canvas (no MediaRecorder or captureStream).
 */
export function initMapRecorder() {
  const canRecord =
    supportedMimeType() !== null &&
    typeof HTMLCanvasElement.prototype.captureStream === "function";
  for (const target of TARGETS) {
    const button = document.getElementById(target.buttonId);
    if (!button) continue;
    button.hidden = !canRecord;
    if (!canRecord) continue;
    setButtonState(button, false);
    button.addEventListener("click", () => toggleRecording(target, button));
  }
}
