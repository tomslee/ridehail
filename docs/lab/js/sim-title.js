/**
 * Simulation Title
 *
 * Click-to-edit document title shown in the header, parallel to the static
 * "Ridehail Laboratory" branding. Mirrors the desktop config's free-text
 * "title" field (ridehail/config.py), so a simulation carries the same
 * human-readable label across the desktop app, downloaded .config files,
 * and the browser tab.
 */

import { DOM_ELEMENTS } from "./dom-elements.js";

const APP_NAME = "Ridehail Laboratory";
const UNTITLED = "Untitled";

function applyTitleToDOM(title) {
  const { display } = DOM_ELEMENTS.simTitle;
  if (!display) return;

  // title may arrive as a non-string (e.g. an all-numeric title is parsed as
  // a Number when read back from an uploaded .config file's INI text).
  const trimmed = String(title ?? "").trim();
  display.textContent = trimmed || UNTITLED;
  display.classList.toggle("is-untitled", trimmed === "");
  document.title = trimmed ? `${trimmed} – ${APP_NAME}` : APP_NAME;
}

/**
 * Wire up click-to-edit behavior for the header title field.
 * @param {() => string} getTitle - Returns the current title (live read).
 * @param {(title: string) => void} onCommit - Called with the new title on commit.
 */
export function initSimTitle(getTitle, onCommit) {
  const { display, input } = DOM_ELEMENTS.simTitle;
  if (!display || !input) return;

  applyTitleToDOM(getTitle());

  function enterEditMode() {
    input.value = getTitle();
    display.hidden = true;
    input.hidden = false;
    input.focus();
    input.select();
  }

  function exitEditMode(commit) {
    input.hidden = true;
    display.hidden = false;
    if (commit) {
      const newTitle = input.value.trim();
      onCommit(newTitle);
      applyTitleToDOM(newTitle);
    }
  }

  display.addEventListener("click", enterEditMode);

  input.addEventListener("blur", () => exitEditMode(true));
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      input.blur(); // commits via the blur handler above
    } else if (event.key === "Escape") {
      event.preventDefault();
      input.value = getTitle();
      exitEditMode(false);
    }
  });
}

/**
 * Refresh the displayed title (e.g. after a session restore, scale change,
 * or config upload changes the underlying settings without going through
 * the click-to-edit flow).
 */
export function updateSimTitleDisplay(title) {
  applyTitleToDOM(title);
}
