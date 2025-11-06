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
  LAST_SAVED: `${STORAGE_KEY_PREFIX}last_saved`,
};

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
      citySize: settings.citySize,
      vehicleCount: settings.vehicleCount,
      requestRate: settings.requestRate,
      equilibrate: settings.equilibrate,
      equilibration: settings.equilibration, // Save the string property as well
      price: settings.price,
      perKmPrice: settings.perKmPrice,
      perMinutePrice: settings.perMinutePrice,
      platformCommission: settings.platformCommission,
      reservationWage: settings.reservationWage,
      perKmOpsCost: settings.perKmOpsCost,
      perHourOpportunityCost: settings.perHourOpportunityCost,
      meanVehicleSpeed: settings.meanVehicleSpeed,
      inhomogeneity: settings.inhomogeneity,
      maxTripDistance: settings.maxTripDistance,
      demandElasticity: settings.demandElasticity,
      smoothingWindow: settings.smoothingWindow,
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
    return {
      scale: localStorage.getItem(STORAGE_KEYS.SCALE),
      mode: localStorage.getItem(STORAGE_KEYS.UI_MODE),
      chartType: localStorage.getItem(STORAGE_KEYS.CHART_TYPE),
    };
  } catch (e) {
    console.error("Failed to load UI state from localStorage:", e);
    return null;
  }
}

/**
 * Clear all saved session data
 * @returns {boolean} True if clear succeeded
 */
export function clearSessionData() {
  if (!isLocalStorageAvailable()) return false;

  try {
    Object.values(STORAGE_KEYS).forEach((key) => {
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
