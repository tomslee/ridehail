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
} from "./session-storage.js";
import { parseINI, generateINI } from "./config-file.js";
import {
  webToDesktopConfig,
  desktopToWebConfig,
  validateDesktopConfig,
} from "./config-mapping.js";
import { inferAndClampSettings } from "./scale-inference.js";
import { showSuccess, showError } from "./toast.js";
import { initDetailsPopover } from "./nav-menu.js";
import { setTitleDirty } from "./sim-title.js";

const NONE_SELECTED = "";

// Id of the saved entry current settings were last loaded from or saved
// as, or null if there isn't one. Drives the title-bar "unsaved changes"
// dot: it only appears once there's an actual saved snapshot to diverge
// from, not just because the user has touched a slider.
let activeEntryId = null;

function setActiveEntry(entryId) {
  activeEntryId = entryId;
  setTitleDirty(false);
}

/**
 * Call when settings load from somewhere other than this saved-configs
 * library (e.g. a .config upload or CLI launch) - there's no longer a
 * known saved snapshot to compare against, so hide the dot rather than
 * leave it pointing at a now-unrelated entry.
 */
export function clearActiveSavedConfig() {
  setActiveEntry(null);
}

/**
 * Call whenever a user-driven settings change happens (slider, checkbox,
 * scale, title edit, ...). Only has a visible effect once a saved entry is
 * active - see activeEntryId above.
 */
export function markConfigDirty() {
  if (activeEntryId !== null) {
    setTitleDirty(true);
  }
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

  refresh();

  saveButton.addEventListener("click", () => {
    const title = (getTitle() || "").trim() || "Untitled";
    const iniContent = generateINI(webToDesktopConfig(getSettings()));
    const saved = saveNamedConfig(title, iniContent);
    if (saved) {
      refresh(saved.id);
      setActiveEntry(saved.id);
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
      const { scale, clampedSettings, warnings } =
        inferAndClampSettings(webConfig);
      onLoad(entry.title, clampedSettings, scale, warnings);
      setActiveEntry(entry.id);
    } catch (error) {
      showError(`Error loading saved configuration: ${error.message}`);
      console.error(error);
    }
  });

  deleteButton.addEventListener("click", () => {
    if (select.value === NONE_SELECTED) return;
    const entry = getSavedConfigs().find((c) => c.id === select.value);
    deleteSavedConfig(select.value);
    if (entry && entry.id === activeEntryId) {
      clearActiveSavedConfig();
    }
    refresh();
    if (entry) showSuccess(`Deleted "${entry.title}"`);
  });

  initDetailsPopover("saved-configs-info");
}
