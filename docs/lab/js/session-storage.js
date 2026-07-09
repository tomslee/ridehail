/**
 * Session Storage Manager
 *
 * Provides localStorage-based session persistence for simulation settings.
 * Automatically saves and restores user configuration between browser sessions.
 */

const STORAGE_KEY_PREFIX = "ridehail_lab_";
const STORAGE_KEYS = {
  LAB_SETTINGS: `${STORAGE_KEY_PREFIX}lab_settings`,
  SCALE: `${STORAGE_KEY_PREFIX}scale`,
  UI_MODE: `${STORAGE_KEY_PREFIX}ui_mode`,
  CHART_TYPE: `${STORAGE_KEY_PREFIX}chart_type`,
  ZOOM_STATE: `${STORAGE_KEY_PREFIX}zoom_state`,
  LAST_SAVED: `${STORAGE_KEY_PREFIX}last_saved`,
  SAVED_CONFIGS: `${STORAGE_KEY_PREFIX}saved_configs`,
  ACTIVE_PROVENANCE: `${STORAGE_KEY_PREFIX}active_provenance`,
};

// Soft cap on the local "library" of named configurations. Each entry is a
// small JSON object (desktop-config shape), so this stays well under
// localStorage's ~5-10MB quota; it just guards against unbounded growth.
const MAX_SAVED_CONFIGS = 50;

function generateConfigId() {
  return typeof crypto !== "undefined" && crypto.randomUUID
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(36).slice(2)}`;
}

/**
 * Check if localStorage is available and working
 * @returns {boolean} True if localStorage is available
 */
function isLocalStorageAvailable() {
  try {
    const test = "__storage_test__";
    localStorage.setItem(test, test);
    localStorage.removeItem(test);
    return true;
  } catch (e) {
    return false;
  }
}

/**
 * Save simulation settings to localStorage
 * @param {SimSettings} settings - Settings object to save
 * @returns {boolean} True if save succeeded
 */
export function saveLabSettings(settings) {
  if (!isLocalStorageAvailable()) {
    console.warn("localStorage not available - session persistence disabled");
    return false;
  }

  try {
    // Extract only the serializable properties we care about
    const settingsToSave = {
      title: settings.title,
      citySize: settings.citySize,
      vehicleCount: settings.vehicleCount,
      requestRate: settings.requestRate,
      equilibrate: settings.equilibrate,
      equilibration: settings.equilibration, // Save the string property as well
      useCostsAndIncomes: settings.useCostsAndIncomes,
      price: settings.price,
      perKmPrice: settings.perKmPrice,
      perMinutePrice: settings.perMinutePrice,
      baseFare: settings.baseFare,
      platformCommission: settings.platformCommission,
      reservationWage: settings.reservationWage,
      perKmOpsCost: settings.perKmOpsCost,
      perHourOpportunityCost: settings.perHourOpportunityCost,
      meanVehicleSpeed: settings.meanVehicleSpeed,
      inhomogeneity: settings.inhomogeneity,
      idleVehiclesMoving: settings.idleVehiclesMoving,
      meanTripDistance: settings.meanTripDistance,
      demandElasticity: settings.demandElasticity,
      smoothingWindow: settings.smoothingWindow,
      pickupTime: settings.pickupTime,
      animationDelay: settings.animationDelay,
    };

    localStorage.setItem(
      STORAGE_KEYS.LAB_SETTINGS,
      JSON.stringify(settingsToSave),
    );
    localStorage.setItem(STORAGE_KEYS.LAST_SAVED, new Date().toISOString());
    return true;
  } catch (e) {
    console.error("Failed to save settings to localStorage:", e);
    return false;
  }
}

/**
 * Save UI state (scale, mode, chart type)
 * @param {Object} uiState - UI state to save
 * @param {string} uiState.scale - Current scale (village/town/city)
 * @param {string} uiState.mode - Current mode (simple/advanced)
 * @param {string} uiState.chartType - Current chart type (map/stats)
 * @param {number} uiState.zoomState - Current zoom level (0=normal, 1=mid, 2=max)
 * @returns {boolean} True if save succeeded
 */
export function saveUIState(uiState) {
  if (!isLocalStorageAvailable()) return false;

  try {
    if (uiState.scale) {
      localStorage.setItem(STORAGE_KEYS.SCALE, uiState.scale);
    }
    if (uiState.mode) {
      localStorage.setItem(STORAGE_KEYS.UI_MODE, uiState.mode);
    }
    if (uiState.chartType) {
      localStorage.setItem(STORAGE_KEYS.CHART_TYPE, uiState.chartType);
    }
    // zoomState 0 ("normal") is a valid, common value — use != null rather
    // than a truthy check so resetting zoom is persisted, not skipped.
    if (uiState.zoomState != null) {
      localStorage.setItem(STORAGE_KEYS.ZOOM_STATE, uiState.zoomState);
    }
    return true;
  } catch (e) {
    console.error("Failed to save UI state to localStorage:", e);
    return false;
  }
}

/**
 * Load simulation settings from localStorage
 * @returns {Object|null} Saved settings object or null if not found/invalid
 */
export function loadLabSettings() {
  if (!isLocalStorageAvailable()) return null;

  try {
    const settingsJSON = localStorage.getItem(STORAGE_KEYS.LAB_SETTINGS);
    if (!settingsJSON) return null;

    const settings = JSON.parse(settingsJSON);
    const lastSaved = localStorage.getItem(STORAGE_KEYS.LAST_SAVED);

    console.log("Loaded saved settings from", lastSaved || "unknown date");
    return settings;
  } catch (e) {
    console.error("Failed to load settings from localStorage:", e);
    return null;
  }
}

/**
 * Load UI state from localStorage
 * @returns {Object|null} UI state object or null if not found
 */
export function loadUIState() {
  if (!isLocalStorageAvailable()) return null;

  try {
    const zoomState = localStorage.getItem(STORAGE_KEYS.ZOOM_STATE);
    return {
      scale: localStorage.getItem(STORAGE_KEYS.SCALE),
      mode: localStorage.getItem(STORAGE_KEYS.UI_MODE),
      chartType: localStorage.getItem(STORAGE_KEYS.CHART_TYPE),
      zoomState: zoomState != null ? Number(zoomState) : null,
    };
  } catch (e) {
    console.error("Failed to load UI state from localStorage:", e);
    return null;
  }
}

/**
 * Clear all saved session data (autosaved settings and UI state).
 *
 * Deliberately leaves the named saved-configurations library (see
 * getSavedConfigs/saveNamedConfig/deleteSavedConfig below) untouched: a CLI
 * launch or a stale-session reset shouldn't silently delete configurations
 * the user explicitly chose to keep.
 * @returns {boolean} True if clear succeeded
 */
export function clearSessionData() {
  if (!isLocalStorageAvailable()) return false;

  try {
    Object.entries(STORAGE_KEYS).forEach(([name, key]) => {
      if (name === "SAVED_CONFIGS") return;
      localStorage.removeItem(key);
    });
    console.log("Session data cleared");
    return true;
  } catch (e) {
    console.error("Failed to clear session data:", e);
    return false;
  }
}

/**
 * List named configurations saved to the local library, most recently
 * saved first.
 * @returns {Array<{id: string, title: string, savedAt: string, config: string}>} config is INI text (see saveNamedConfig)
 */
export function getSavedConfigs() {
  if (!isLocalStorageAvailable()) return [];

  try {
    const json = localStorage.getItem(STORAGE_KEYS.SAVED_CONFIGS);
    const configs = json ? JSON.parse(json) : [];
    return configs.sort((a, b) => b.savedAt.localeCompare(a.savedAt));
  } catch (e) {
    console.error("Failed to read saved configurations:", e);
    return [];
  }
}

/**
 * Save a named configuration to the local library. Saving under a title
 * that already exists overwrites that entry (acts as "Save", not
 * "Save As").
 * @param {string} title
 * @param {string} configText - INI text, e.g. generateINI(webToDesktopConfig(settings))
 * @returns {{id: string, title: string, savedAt: string, config: string}|null}
 */
export function saveNamedConfig(title, configText) {
  if (!isLocalStorageAvailable()) {
    console.warn(
      "localStorage not available - cannot save named configuration",
    );
    return null;
  }

  try {
    const configs = getSavedConfigs();
    const existing = configs.find((c) => c.title === title);
    const entry = {
      id: existing ? existing.id : generateConfigId(),
      title,
      savedAt: new Date().toISOString(),
      config: configText,
    };
    const remaining = configs.filter((c) => c.id !== entry.id);
    const next = [...remaining, entry].slice(-MAX_SAVED_CONFIGS);
    localStorage.setItem(STORAGE_KEYS.SAVED_CONFIGS, JSON.stringify(next));
    return entry;
  } catch (e) {
    console.error("Failed to save named configuration:", e);
    return null;
  }
}

/**
 * Delete a named configuration from the local library.
 * @param {string} id
 * @returns {boolean} True if delete succeeded
 */
export function deleteSavedConfig(id) {
  if (!isLocalStorageAvailable()) return false;

  try {
    const configs = getSavedConfigs().filter((c) => c.id !== id);
    localStorage.setItem(STORAGE_KEYS.SAVED_CONFIGS, JSON.stringify(configs));
    return true;
  } catch (e) {
    console.error("Failed to delete saved configuration:", e);
    return false;
  }
}

/**
 * Persist the current session's configuration "provenance" - where the active
 * settings came from (a saved-library entry, a preset button, an uploaded or
 * URL-launched file, or nothing) plus whether they have been edited since. Lets
 * the "Saved" dropdown re-select the right entry and the title-bar "unsaved"
 * dot reappear after a page reload. Pass null/undefined to clear.
 * @param {{kind: string, id?: string, name?: string, dirty?: boolean}|null} provenance
 * @returns {boolean} True if save succeeded
 */
export function saveProvenance(provenance) {
  if (!isLocalStorageAvailable()) return false;

  try {
    if (provenance) {
      localStorage.setItem(
        STORAGE_KEYS.ACTIVE_PROVENANCE,
        JSON.stringify(provenance),
      );
    } else {
      localStorage.removeItem(STORAGE_KEYS.ACTIVE_PROVENANCE);
    }
    return true;
  } catch (e) {
    console.error("Failed to save configuration provenance:", e);
    return false;
  }
}

/**
 * @returns {{kind: string, id?: string, name?: string, dirty?: boolean}|null}
 *   The provenance saved by saveProvenance, or null.
 */
export function loadProvenance() {
  if (!isLocalStorageAvailable()) return null;
  try {
    const json = localStorage.getItem(STORAGE_KEYS.ACTIVE_PROVENANCE);
    return json ? JSON.parse(json) : null;
  } catch (e) {
    console.error("Failed to load configuration provenance:", e);
    return null;
  }
}

/**
 * Check if saved session data exists
 * @returns {boolean} True if saved data exists
 */
export function hasSavedSession() {
  if (!isLocalStorageAvailable()) return false;
  return localStorage.getItem(STORAGE_KEYS.LAB_SETTINGS) !== null;
}

/**
 * Get the date when settings were last saved
 * @returns {Date|null} Last saved date or null if not available
 */
export function getLastSavedDate() {
  if (!isLocalStorageAvailable()) return null;

  const lastSaved = localStorage.getItem(STORAGE_KEYS.LAST_SAVED);
  return lastSaved ? new Date(lastSaved) : null;
}
