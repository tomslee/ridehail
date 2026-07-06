/**
 * Slider Direct Edit
 *
 * Makes the numeric value display at the top-right of each slider label
 * clickable, swapping it for a small number input so the user can type an
 * exact value. Mirrors the click-to-edit pattern from sim-title.js.
 *
 * Works for both log-scale sliders (data-log-min/max attributes) and ordinary
 * linear sliders (native min/max/step attributes). On commit the entered value
 * is clamped to the valid range, converted to the appropriate slider position,
 * and a synthetic "change" event is dispatched so all existing handlers fire.
 */

import { valueToLogSlider, updateSliderFill } from "./input-handlers.js";

/**
 * @param {HTMLInputElement} sliderEl
 * @param {HTMLElement} valueSpanEl
 * @param {object} [options]
 * @param {() => number} [options.getMax] - Returns a dynamic upper bound that
 *   overrides (tightens) the slider's static maximum. Called fresh on each
 *   edit-open so it always reflects current state (e.g. citySize / 2 for
 *   mean trip distance).
 */
function initSliderDirectEdit(sliderEl, valueSpanEl, options = {}) {
  if (!sliderEl || !valueSpanEl) return;

  // Inject a hidden number input as a sibling after the value span (still
  // inside the label, so it inherits flex alignment).
  const input = document.createElement("input");
  input.type = "number";
  input.className = "slider-value-input";
  input.hidden = true;
  input.step = "any";

  const labelTextEl = valueSpanEl
    .closest("label")
    ?.querySelector(".app-settings-card__label-text");
  if (labelTextEl) {
    input.setAttribute(
      "aria-label",
      `${labelTextEl.textContent.trim()} (enter exact value)`,
    );
  }

  valueSpanEl.insertAdjacentElement("afterend", input);
  valueSpanEl.classList.add("slider-value-editable");
  valueSpanEl.title = "Click to enter exact value";

  const isLogSlider = "logMin" in sliderEl.dataset;
  let isEditing = false;

  // Resolve the effective maximum, honouring any dynamic override.
  function effectiveMax(staticMax) {
    if (!options.getMax) return staticMax;
    const dynamic = options.getMax();
    return isNaN(dynamic) ? staticMax : Math.min(staticMax, dynamic);
  }

  function enterEditMode() {
    if (isEditing || sliderEl.disabled) return;
    isEditing = true;

    // Set range constraints for browser validation tooltip, applying any
    // dynamic max so the browser's own out-of-range hint is accurate.
    if (isLogSlider) {
      input.min = sliderEl.dataset.logMin;
      input.max = effectiveMax(parseFloat(sliderEl.dataset.logMax));
    } else {
      input.min = sliderEl.min;
      input.max = effectiveMax(parseFloat(sliderEl.max));
    }

    input.value = valueSpanEl.textContent.trim();
    valueSpanEl.hidden = true;
    input.hidden = false;
    input.focus();
    input.select();
  }

  function exitEditMode(commit) {
    if (!isEditing) return;
    isEditing = false;

    input.hidden = true;
    valueSpanEl.hidden = false;

    if (!commit) return;

    const raw = parseFloat(input.value);
    if (isNaN(raw)) return;

    if (isLogSlider) {
      // logMin/logMax define the slider's full value range and the mapping
      // from value to slider position. A dynamic getMax (e.g. citySize / 2)
      // only tightens the *value* bound for clamping — it must NOT be used as
      // the range for the position conversion, or the clamped value maps to
      // the wrong slider position (and back to the untightened max value).
      const logMin = parseFloat(sliderEl.dataset.logMin);
      const logMax = parseFloat(sliderEl.dataset.logMax);
      const clampMax = effectiveMax(logMax);
      const clamped = Math.max(logMin, Math.min(clampMax, raw));
      sliderEl.value = valueToLogSlider(clamped, logMin, logMax);
    } else {
      const min = parseFloat(sliderEl.min);
      const max = effectiveMax(parseFloat(sliderEl.max));
      let clamped = raw;
      if (!isNaN(min)) clamped = Math.max(min, clamped);
      if (!isNaN(max)) clamped = Math.min(max, clamped);
      sliderEl.value = clamped;
    }

    updateSliderFill(sliderEl);
    sliderEl.dispatchEvent(new Event("change", { bubbles: true }));
  }

  // Span click → enter edit mode; stop propagation so the label doesn't
  // redirect the click to the associated range input.
  valueSpanEl.addEventListener("click", (e) => {
    e.stopPropagation();
    enterEditMode();
  });

  // Prevent clicks on the number input from bubbling to the label either.
  input.addEventListener("click", (e) => e.stopPropagation());

  // Blur commits (Enter triggers blur; Escape exits without commit).
  input.addEventListener("blur", () => exitEditMode(true));

  input.addEventListener("keydown", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      input.blur(); // commit via blur handler
    } else if (e.key === "Escape") {
      e.preventDefault();
      exitEditMode(false);
    }
  });
}

/**
 * @param {Object.<string, {getMax?: () => number}>} [overrides]
 *   Per-slider-id options, e.g. { "input-mean-trip-distance": { getMax: () => citySize / 2 } }
 */
export function initAllSliderDirectEdits(overrides = {}) {
  const pairs = [
    ["input-city-size",                 "option-city-size"],
    ["input-vehicle-count",             "option-vehicle-count"],
    ["input-request-rate",              "option-request-rate"],
    ["input-mean-trip-distance",        "option-mean-trip-distance"],
    ["input-inhomogeneity",             "option-inhomogeneity"],
    ["input-pickup-time",               "option-pickup-time"],
    ["input-idle-vehicles-moving",      "option-idle-vehicles-moving"],
    ["input-mean-vehicle-speed",        "option-mean-vehicle-speed"],
    ["input-demand-elasticity",         "option-demand-elasticity"],
    ["input-price",                     "option-price"],
    ["input-per-km-price",              "option-per-km-price"],
    ["input-per-minute-price",          "option-per-minute-price"],
    ["input-platform-commission",       "option-platform-commission"],
    ["input-reservation-wage",          "option-reservation-wage"],
    ["input-per-hour-opportunity-cost", "option-per-hour-opportunity-cost"],
    ["input-per-km-ops-cost",           "option-per-km-ops-cost"],
    ["input-animation-delay",           "option-animation-delay"],
    ["input-smoothing-window",          "option-smoothing-window"],
  ];

  for (const [sliderId, spanId] of pairs) {
    initSliderDirectEdit(
      document.getElementById(sliderId),
      document.getElementById(spanId),
      overrides[sliderId] ?? {},
    );
  }
}
