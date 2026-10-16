/**
 * Record the Experiment tab's map as a video file (claude/animation-export-spec.md).
 *
 * The record button on the map starts a MediaRecorder; pressing it again
 * stops it and downloads the video (MP4 where the browser can write it, else
 * WebM). What is recorded is exactly what the map draws, in real time: the
 * vehicle and trip markers, the eased movement between frames, the current
 * theme. HTML overlays (the metrics panel, this button) are not included.
 *
 * Frames are not taken from the map canvas directly. Each animation frame,
 * the map's plot area (Chart.js chartArea, the land square) is copied onto a
 * hidden recording canvas of fixed size, and that canvas is recorded. So:
 *  - the video is the map square only, with no transparent margins (which
 *    encode as black);
 *  - recording survives a Reset or a resize, which re-create the Chart.js
 *    chart and its canvas: the copy just follows the current one.
 * Switching the display to Statistics stops the recording and saves it.
 */

import { appState } from "./app-state.js";
import { CHART_TYPES } from "./config.js";
import { themeColor } from "./theme.js";
import { showError, showSuccess } from "./toast.js";

const MAP_CANVAS_ID = "lab-map-chart-canvas";
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

let recorder = null;
let chunks = [];
let recordCanvas = null;
let frameRequest = null;
let startTime = 0;
let timerInterval = null;
let button = null;
let label = null;
let icon = null;

function supportedMimeType() {
  if (!window.MediaRecorder) return null;
  return MIME_TYPES.find((type) => MediaRecorder.isTypeSupported(type)) ?? null;
}

// The Chart.js map, when it is the one being shown on the Experiment tab
function currentMapChart() {
  const chart = window.chart;
  if (!chart?.canvas || chart.canvas.id !== MAP_CANVAS_ID || !chart.chartArea) {
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
  frameRequest = requestAnimationFrame(copyFrame);
  if (appState.labUISettings.chartType !== CHART_TYPES.MAP) {
    stopRecording();
    return;
  }
  const chart = currentMapChart();
  // Between a Reset's teardown and the new chart's first draw there is no
  // map: keep the last frame
  if (!chart) return;
  const src = sourceRect(chart);
  const ctx = recordCanvas.getContext("2d");
  ctx.fillStyle = themeColor("LAND");
  ctx.fillRect(0, 0, recordCanvas.width, recordCanvas.height);
  ctx.drawImage(
    chart.canvas,
    src.x,
    src.y,
    src.w,
    src.h,
    0,
    0,
    recordCanvas.width,
    recordCanvas.height,
  );
}

function fileName(mimeType) {
  const extension = mimeType.startsWith("video/mp4") ? "mp4" : "webm";
  const title = String(appState.labSimSettings?.title ?? "")
    .trim()
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "");
  const stamp = new Date()
    .toISOString()
    .slice(0, 19)
    .replace(/:/g, "-")
    .replace("T", "_");
  return `ridehail-map${title ? "-" + title : ""}_${stamp}.${extension}`;
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

function setButtonState(recording) {
  button.classList.toggle("is-recording", recording);
  icon.textContent = recording ? "stop_circle" : "videocam";
  button.setAttribute("aria-pressed", String(recording));
  button.title = recording
    ? "Stop recording and download the video"
    : "Record the map as a video";
  label.textContent = recording ? "0:00" : "";
  label.hidden = !recording;
}

function startRecording() {
  const mimeType = supportedMimeType();
  const chart = currentMapChart();
  if (!mimeType || !chart) {
    showError("The map can't be recorded in this browser");
    return;
  }
  const src = sourceRect(chart);
  recordCanvas = document.createElement("canvas");
  recordCanvas.width = evenSide(src.w);
  recordCanvas.height = evenSide(src.h);
  copyFrame();

  chunks = [];
  try {
    recorder = new MediaRecorder(recordCanvas.captureStream(CAPTURE_FPS), {
      mimeType,
    });
  } catch (error) {
    console.error("map-recorder: MediaRecorder failed", error);
    cancelAnimationFrame(frameRequest);
    showError("The map can't be recorded in this browser");
    return;
  }
  recorder.ondataavailable = (event) => {
    if (event.data.size > 0) chunks.push(event.data);
  };
  recorder.onstop = () => {
    const blob = new Blob(chunks, { type: mimeType });
    chunks = [];
    if (blob.size > 0) {
      const name = fileName(mimeType);
      download(blob, name);
      showSuccess(`Map video saved: ${name}`);
    }
  };
  // Collect data every second, so a long recording isn't held in one piece
  recorder.start(1000);
  startTime = performance.now();
  setButtonState(true);
  timerInterval = setInterval(() => {
    label.textContent = formatElapsed(performance.now() - startTime);
  }, 250);
}

export function stopRecording() {
  if (!recorder) return;
  cancelAnimationFrame(frameRequest);
  clearInterval(timerInterval);
  if (recorder.state !== "inactive") recorder.stop();
  recorder = null;
  recordCanvas = null;
  setButtonState(false);
}

export function isRecording() {
  return recorder !== null;
}

export function toggleRecording() {
  if (recorder) {
    stopRecording();
  } else {
    startRecording();
  }
}

/**
 * Wire up the map's record button. Hidden where the browser can't record a
 * canvas (no MediaRecorder or captureStream).
 */
export function initMapRecorder() {
  button = document.getElementById("map-record-button");
  label = document.getElementById("map-record-time");
  icon = button?.querySelector(".map-record-button__icon");
  if (!button || !label || !icon) return;
  const canRecord =
    supportedMimeType() !== null &&
    typeof HTMLCanvasElement.prototype.captureStream === "function";
  button.hidden = !canRecord;
  if (!canRecord) return;
  setButtonState(false);
  button.addEventListener("click", toggleRecording);
}
