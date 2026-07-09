/**
 * Saved Configurations
 *
 * A small client-side "library" of named configurations, stored in
 * localStorage and listed in a dropdown next to the simulation title.
 * Complements (does not replace) the desktop-compatible .config
 * download/upload feature: each entry is stored as the same INI text a
 * downloaded file would contain (via generateINI/webToDesktopConfig) and
 * loaded back through parseINI/desktopToWebConfig - the same round trip
 * the upload feature already uses - so a saved entry behaves identically
 * to a downloaded-then-reuploaded file. It lives only in this browser,
 * though - see the info popover text below for the caveats shown to users.
 */

import { DOM_ELEMENTS } from "./dom-elements.js";
import {
  getSavedConfigs,
  saveNamedConfig,
  deleteSavedConfig,
  saveProvenance,
  loadProvenance,
} from "./session-storage.js";
import { parseINI, generateINI } from "./config-file.js";
import {
  webToDesktopConfig,
  desktopToWebConfig,
  validateDesktopConfig,
} from "./config-mapping.js";
import { inferPresetFromSettings } from "./scale-inference.js";
import { showSuccess, showError } from "./toast.js";
import { initDetailsPopover } from "./nav-menu.js";
import { setTitleDirty } from "./sim-title.js";

const NONE_SELECTED = "";

// Kinds of configuration provenance - where the active settings came from.
// "saved" carries an id; "preset"/"url" carry a name; "none" is the pre-load
// fallback with no baseline to diverge from.
export const PROVENANCE = {
  SAVED: "saved",
  PRESET: "preset",
  FILE: "file",
  URL: "url",
  NONE: "none",
};

// The active configuration's provenance and whether it has been edited since
// it was established. Together these drive the title-bar "unsaved changes" dot
// and the "Saved" dropdown selection - see setProvenance / markConfigDirty.
// Identity lives in the title bar; the dropdown is a pure picker that only
// shows a selection when a saved-library entry is genuinely active.
let activeProvenance = { kind: PROVENANCE.NONE };
let isDirty = false;

// Set once initSavedConfigs runs, so setProvenance() (called from elsewhere -
// preset clicks, uploads, URL launches) can keep the dropdown in sync.
let refreshSelect = null;

function persistProvenance() {
  saveProvenance({ ...activeProvenance, dirty: isDirty });
}

function applyProvenanceToDropdown() {
  if (!refreshSelect) return;
  // Pure picker: only reflect a genuinely-active saved entry; every other
  // provenance falls back to the "Load saved configuration…" placeholder.
  refreshSelect(
    activeProvenance.kind === PROVENANCE.SAVED
      ? activeProvenance.id
      : NONE_SELECTED,
  );
}

/**
 * Establish a fresh configuration provenance. Called by every path that loads
 * a configuration from a distinct source (saved entry, preset button, uploaded
 * or URL-launched file). Resets the "unsaved" dot to clean, re-selects (or
 * clears) the dropdown, and persists the new provenance.
 * @param {{kind: string, id?: string, name?: string}} provenance
 */
export function setProvenance(provenance) {
  activeProvenance = provenance || { kind: PROVENANCE.NONE };
  isDirty = false;
  setTitleDirty(false);
  applyProvenanceToDropdown();
  persistProvenance();
}

/**
 * Call whenever a user-driven settings change happens (slider, checkbox,
 * scale, title edit, ...). Marks the active configuration as diverged from its
 * baseline. Has no effect before any source is established (kind "none").
 */
export function markConfigDirty() {
  if (activeProvenance.kind === PROVENANCE.NONE || isDirty) return;
  isDirty = true;
  setTitleDirty(true);
  persistProvenance();
}

function populateSelect(select, configs, keepSelectedId) {
  select.innerHTML = "";

  const placeholder = document.createElement("option");
  placeholder.value = NONE_SELECTED;
  placeholder.textContent = configs.length
    ? "Load saved configuration…"
    : "No saved configurations";
  select.appendChild(placeholder);

  configs.forEach((config) => {
    const option = document.createElement("option");
    option.value = config.id;
    option.textContent = config.title;
    select.appendChild(option);
  });

  select.value = configs.some((c) => c.id === keepSelectedId)
    ? keepSelectedId
    : NONE_SELECTED;
}

/**
 * Wire up the "Saved" top control: a dropdown of named local configurations
 * plus save/delete buttons and an info popover explaining storage trust.
 *
 * @param {Object} handlers
 * @param {() => string} handlers.getTitle - Current simulation title (used as the save name).
 * @param {() => Object} handlers.getSettings - Current appState.labSimSettings.
 * @param {(title: string, settings: Object, scale: string, warnings: Array) => void} handlers.onLoad
 */
export function initSavedConfigs({ getTitle, getSettings, onLoad }) {
  const { select, saveButton, deleteButton } = DOM_ELEMENTS.savedConfigs;
  if (!select || !saveButton || !deleteButton) return;

  function refresh(selectedId = NONE_SELECTED) {
    populateSelect(select, getSavedConfigs(), selectedId);
    deleteButton.disabled = select.value === NONE_SELECTED;
  }
  // Expose the dropdown refresh so setProvenance() (driven from preset clicks,
  // uploads and URL launches) can keep the selection truthful.
  refreshSelect = refresh;

  // A fresh page load restores settings from the autosaved session (see
  // app.js restoreSession), but that's a snapshot of values, not a pointer
  // back to the source they came from. Re-establish the stored provenance
  // here: re-select the saved entry (if it still exists) and restore the
  // "unsaved" dot, so the dropdown and dot survive a reload rather than
  // resetting to a clean placeholder.
  const stored = loadProvenance();
  if (stored && stored.kind === PROVENANCE.SAVED) {
    const entry = getSavedConfigs().find((c) => c.id === stored.id);
    if (entry) {
      activeProvenance = { kind: PROVENANCE.SAVED, id: entry.id };
      isDirty = !!stored.dirty;
      refresh(entry.id);
      setTitleDirty(isDirty);
    } else {
      // The saved entry was deleted in another tab/session; drop back to a
      // clean, source-less state rather than point at a missing id.
      refresh(NONE_SELECTED);
    }
  } else if (stored) {
    activeProvenance = { kind: stored.kind, name: stored.name };
    isDirty = !!stored.dirty;
    refresh(NONE_SELECTED);
    setTitleDirty(isDirty);
  } else {
    refresh(NONE_SELECTED);
  }

  saveButton.addEventListener("click", () => {
    const title = (getTitle() || "").trim() || "Untitled";
    const iniContent = generateINI(webToDesktopConfig(getSettings()));
    const saved = saveNamedConfig(title, iniContent);
    if (saved) {
      refresh(saved.id);
      setProvenance({ kind: PROVENANCE.SAVED, id: saved.id });
      showSuccess(`Saved "${title}" in this browser`);
    }
  });

  select.addEventListener("change", () => {
    deleteButton.disabled = select.value === NONE_SELECTED;
    if (select.value === NONE_SELECTED) return;

    const entry = getSavedConfigs().find((c) => c.id === select.value);
    if (!entry) return;

    try {
      if (typeof entry.config !== "string") {
        // Entries saved by an older, pre-fix version of this feature stored
        // a typed object instead of INI text. Nothing to recover - ask the
        // user to redo the save rather than guess at a silent migration.
        throw new Error(
          `"${entry.title}" was saved in an outdated format - delete it and save again`,
        );
      }

      const parsedINI = parseINI(entry.config);
      const validation = validateDesktopConfig(parsedINI);
      if (!validation.valid) {
        showError(
          `Saved configuration "${entry.title}" is invalid: ${validation.errors[0]}`,
        );
        return;
      }

      const webConfig = desktopToWebConfig(parsedINI);
      const scale = inferPresetFromSettings(webConfig);
      onLoad(entry.title, webConfig, scale, []);
      setProvenance({ kind: PROVENANCE.SAVED, id: entry.id });
    } catch (error) {
      showError(`Error loading saved configuration: ${error.message}`);
      console.error(error);
    }
  });

  deleteButton.addEventListener("click", () => {
    if (select.value === NONE_SELECTED) return;
    const entry = getSavedConfigs().find((c) => c.id === select.value);
    deleteSavedConfig(select.value);
    if (
      entry &&
      activeProvenance.kind === PROVENANCE.SAVED &&
      entry.id === activeProvenance.id
    ) {
      // The active entry is gone; keep its (still-loaded) settings but detach
      // them from the now-missing entry so the dot/dropdown stop pointing at it.
      setProvenance({ kind: PROVENANCE.NONE });
    }
    refresh();
    if (entry) showSuccess(`Deleted "${entry.title}"`);
  });

  initDetailsPopover("saved-configs-info");
}
