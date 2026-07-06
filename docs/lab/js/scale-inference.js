/**
 * Preset Inference Logic
 *
 * When a configuration is loaded from outside the UI (an uploaded .config file,
 * a saved-library entry, or a CLI launch), we highlight the preset radio
 * (Village/Town/City) whose starting point is closest to the loaded values.
 *
 * This is purely cosmetic: presets are only starting points, so a loaded config
 * keeps its exact values. Nothing is clamped or adjusted to a preset's range -
 * every control is continuous across its full range.
 */

import { SCALE_CONFIGS } from "./config.js";

/**
 * Infer which preset a set of settings is closest to, for radio highlighting.
 * Uses city size as the distinguishing dimension (the presets are ordered
 * Village < Town < City by city size).
 * @param {Object} settings - Settings object
 * @returns {string} Preset name: 'village', 'town', or 'city'
 */
export function inferPresetFromSettings(settings) {
  const citySize = settings.citySize;
  if (citySize === undefined || citySize === null) {
    return "village";
  }

  let bestScale = "village";
  let bestDistance = Infinity;
  for (const [scale, config] of Object.entries(SCALE_CONFIGS)) {
    const distance = Math.abs(config.citySize.value - citySize);
    if (distance < bestDistance) {
      bestDistance = distance;
      bestScale = scale;
    }
  }
  return bestScale;
}

/**
 * Get a summary of key parameters for display in the load-configuration dialog.
 * @param {Object} settings - Settings object
 * @param {string} scale - Preset name (nearest preset, for display only)
 * @returns {Object} Summary object with formatted values
 */
export function getConfigSummary(settings, scale) {
  return {
    title: settings.title || "Untitled",
    scale: scale.toUpperCase(),
    citySize: settings.citySize,
    vehicleCount: settings.vehicleCount,
    requestRate: settings.requestRate,
    meanTripDistance: settings.meanTripDistance || "Auto",
    inhomogeneity: settings.inhomogeneity,
    equilibrate: settings.equilibrate,
    useCostsAndIncomes: settings.useCostsAndIncomes,
    price: settings.price,
    platformCommission: settings.platformCommission,
    reservationWage: settings.reservationWage,
  };
}
