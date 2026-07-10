/**
 * Phone showcase tier.
 *
 * A curated, touch-first presentation of the Experiment tab for narrow
 * screens (portrait phones). It does NOT reimplement the simulation: every
 * phone affordance is a thin proxy onto the existing controls and handlers, so
 * the desktop/tablet experience is completely untouched and the two run in the
 * same DOM.
 *
 * What it does when `body.is-phone` is active (matchMedia, ≤600px):
 *  - relocates the "key" setting cards (data-phone-priority="key": Vehicles and
 *    Trip requests) into the bottom sheet, and moves them back when leaving the
 *    tier (resize / rotation safe);
 *  - wires the bottom action bar (play/pause, reset, map/stats, full screen,
 *    help) and the sheet's preset chips to the real controls;
 *  - mirrors the real FAB's play/pause icon + disabled state onto the phone
 *    play button, and the chart-type radios onto the segmented control;
 *  - drives the draggable bottom sheet (peek ⇄ full detents).
 *
 * Autoplay of the demo and the reduced-motion hint live in app.js
 * (handlePyodideReady), since they are timed off Pyodide readiness. See the
 * "PHONE SHOWCASE TIER" block in style.css for the presentation, and the phone
 * chrome markup in index.html.
 */

import { fitMapToViewport } from "../modules/map.js";
import { appState } from "./app-state.js";

const PHONE_MQ = "(max-width: 600px)";
const SHEET_PEEK_PX = 112; // must roughly match --phone-sheet-peek in style.css

let app = null;
let relocated = []; // [{ node, parent, next }] for restoring key cards

/**
 * Initialize the phone tier. Safe to call once, after the tab components and
 * the App (with keyboardHandler + experimentTab) exist.
 * @param {object} appInstance - the App instance (needs experimentTab + keyboardHandler)
 */
export function initPhone(appInstance) {
  app = appInstance;

  wireActionBar();
  wirePresetChips();
  wireSheet();
  wireStateMirrors();

  const mq = window.matchMedia(PHONE_MQ);
  const apply = (isPhone) => (isPhone ? enterPhone() : leavePhone());
  apply(mq.matches);
  // Safari <14 uses the deprecated addListener signature; addEventListener is
  // fine on every browser that can run Pyodide, so keep it simple.
  mq.addEventListener("change", (e) => apply(e.matches));
}

// ── Tier enter / leave ──────────────────────────────────────────────────────

function enterPhone() {
  document.body.classList.add("is-phone");
  // "Pre-run" = the demo has not started yet; drives the play hint. Cleared the
  // first time the sim runs (see mirrorFab).
  const running = app?.experimentTab && appSimState() === "running";
  document.body.classList.toggle("phone-prerun", !running);
  relocateKeyCards();
  syncSegmented();
  mirrorFab();
  requestAnimationFrame(fitMapToViewport);
}

function leavePhone() {
  document.body.classList.remove("is-phone", "phone-prerun");
  restoreKeyCards();
  requestAnimationFrame(fitMapToViewport);
}

// ── Key-card relocation (real controls, so values/handlers are preserved) ────

function relocateKeyCards() {
  if (relocated.length) return; // already relocated
  const body = document.getElementById("phone-sheet-body");
  if (!body) return;
  document
    .querySelectorAll('#column-2 [data-phone-priority="key"]')
    .forEach((card) => {
      relocated.push({ node: card, parent: card.parentNode, next: card.nextSibling });
      body.appendChild(card);
    });
}

function restoreKeyCards() {
  // Restore in reverse document order so a card whose original next-sibling was
  // itself relocated (Vehicles' next is Trip requests) finds that anchor back
  // in place before it is reinserted.
  for (let i = relocated.length - 1; i >= 0; i--) {
    const { node, parent, next } = relocated[i];
    if (next && next.parentNode === parent) parent.insertBefore(node, next);
    else parent.appendChild(node);
  }
  relocated = [];
}

// ── Bottom action bar (proxies onto existing behaviour) ──────────────────────

function wireActionBar() {
  on("phone-play", () => app?.experimentTab?.clickFabButton());
  on("phone-reset", () => {
    if (!document.getElementById("reset-button")?.hasAttribute("disabled")) {
      app?.experimentTab?.resetUIAndSimulation();
    }
  });
  // Reuse the exact keyboard actions so full-screen canvas detection and the
  // help dialog (with its pause/resume bookkeeping) behave identically.
  on("phone-fullscreen", () =>
    app?.keyboardHandler?.executeAction("toggle_fullscreen"),
  );
  on("phone-help", () => app?.keyboardHandler?.executeAction("show_help"));

  document.querySelectorAll("#phone-bar .phone-seg").forEach((seg) => {
    seg.addEventListener("click", () => selectChartType(seg.dataset.chartType));
  });
}

/**
 * Drive the real chart-type radios so updateChartType (and the worker
 * UpdateDisplay handoff) run exactly as they do on desktop.
 */
function selectChartType(type) {
  const radio = document.getElementById(`radio-chart-type-${type}`);
  if (!radio || radio.checked) return;
  radio.checked = true; // same-name radios auto-uncheck the sibling
  radio.dispatchEvent(new Event("change", { bubbles: true }));
  syncSegmented();
  requestAnimationFrame(fitMapToViewport);
}

function syncSegmented() {
  const active = document.querySelector(
    'input[name="chart-type"]:checked',
  )?.value;
  document.querySelectorAll("#phone-bar .phone-seg").forEach((seg) => {
    const on = seg.dataset.chartType === active;
    seg.classList.toggle("is-active", on);
    seg.setAttribute("aria-pressed", on ? "true" : "false");
  });
}

// ── Preset chips (in the sheet) ──────────────────────────────────────────────

function wirePresetChips() {
  document.querySelectorAll("#phone-sheet .phone-preset-chip").forEach((chip) => {
    chip.addEventListener("click", () => loadPreset(chip.dataset.phonePreset));
  });
}

/**
 * Load a preset via its real button. Presets are scenario-level and thus
 * disabled while a run is live (Model B), so pause first — pausing re-enables
 * the control bar synchronously — then click the real button.
 */
function loadPreset(name) {
  const realBtn = document.getElementById(`preset-${name}`);
  if (!realBtn) return;
  if (realBtn.hasAttribute("disabled") && appSimState() === "running") {
    app?.experimentTab?.clickFabButton(); // pause → setControlBarEnabled(true)
  }
  if (!realBtn.hasAttribute("disabled")) realBtn.click();
}

// ── State mirrors (real controls → phone chrome) ─────────────────────────────

function wireStateMirrors() {
  const fab = document.getElementById("fab-button");
  if (fab) {
    const obs = new MutationObserver(mirrorFab);
    obs.observe(fab, {
      attributes: true,
      attributeFilter: ["disabled"],
      childList: true,
      subtree: true,
      characterData: true,
    });
  }
  document
    .querySelectorAll('input[name="chart-type"]')
    .forEach((r) => r.addEventListener("change", syncSegmented));
}

/** Mirror the real FAB (icon + disabled) onto the phone play button. */
function mirrorFab() {
  const fab = document.getElementById("fab-button");
  const play = document.getElementById("phone-play");
  if (!fab || !play) return;
  const icon = fab.querySelector(".material-icons")?.innerHTML ?? "play_arrow";
  const phoneIcon = play.querySelector(".material-icons");
  if (phoneIcon) phoneIcon.innerHTML = icon;
  play.disabled = fab.hasAttribute("disabled");
  // Once the sim is actually running (icon shows "pause"), the demo has begun:
  // drop the pre-run hint for good.
  if (icon === "pause") document.body.classList.remove("phone-prerun");
}

// ── Bottom sheet (peek ⇄ full, tap + drag) ───────────────────────────────────

function wireSheet() {
  const sheet = document.getElementById("phone-sheet");
  const handle = document.getElementById("phone-sheet-handle");
  if (!sheet || !handle) return;

  const setDetent = (full) => {
    sheet.classList.toggle("is-full", full);
    sheet.classList.toggle("is-peek", !full);
    handle.setAttribute("aria-expanded", full ? "true" : "false");
    requestAnimationFrame(fitMapToViewport);
  };

  handle.addEventListener("click", (e) => {
    if (handle._dragged) {
      handle._dragged = false;
      return; // the pointerup after a drag shouldn't also toggle
    }
    e.preventDefault();
    setDetent(!sheet.classList.contains("is-full"));
  });

  // Pointer drag with snap-to-nearest-detent.
  let startY = 0;
  let baseOffset = 0;
  let height = 0;
  let dragging = false;

  const offsetForState = (full) => (full ? 0 : Math.max(0, height - SHEET_PEEK_PX));

  handle.addEventListener("pointerdown", (e) => {
    dragging = true;
    handle._dragged = false;
    startY = e.clientY;
    height = sheet.offsetHeight;
    baseOffset = offsetForState(sheet.classList.contains("is-full"));
    sheet.classList.add("is-dragging"); // disables the transition while dragging
    handle.setPointerCapture(e.pointerId);
  });

  handle.addEventListener("pointermove", (e) => {
    if (!dragging) return;
    const dy = e.clientY - startY;
    if (Math.abs(dy) > 4) handle._dragged = true;
    const offset = clamp(baseOffset + dy, 0, Math.max(0, height - SHEET_PEEK_PX));
    sheet.style.transform = `translateY(${offset}px)`;
  });

  const endDrag = (e) => {
    if (!dragging) return;
    dragging = false;
    sheet.classList.remove("is-dragging");
    sheet.style.transform = ""; // hand back to the class-based transform
    const dy = e.clientY - startY;
    // Snap on intent: a decisive drag wins, otherwise keep the current state.
    if (dy < -32) setDetent(true);
    else if (dy > 32) setDetent(false);
    else setDetent(sheet.classList.contains("is-full"));
  };
  handle.addEventListener("pointerup", endDrag);
  handle.addEventListener("pointercancel", endDrag);
}

// ── helpers ──────────────────────────────────────────────────────────────────

function on(id, fn) {
  const el = document.getElementById(id);
  if (el) el.addEventListener("click", fn);
}

function appSimState() {
  // Single source of run-state truth ("stopped" | "running" | "paused").
  return appState.simState;
}

function clamp(v, lo, hi) {
  return Math.min(Math.max(v, lo), hi);
}
