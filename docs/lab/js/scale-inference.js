/**
 * Scale Inference Logic
 * Determines appropriate scale preset (village/town/city) from configuration parameters
 * and handles clamping of out-of-range values
 */

import { SCALE_CONFIGS } from "./config.js";

/**
 * Check if settings fit within a scale's parameter ranges
 * @param {Object} settings - Settings object to check
 * @param {Object} scaleConfig - Scale configuration (from SCALE_CONFIGS)
 * @returns {boolean} True if all parameters fit within scale ranges
 */
export function isWithinRange(settings, scaleConfig) {
  // List of parameters to check for range compatibility
  const paramsToCheck = [
    "citySize",
    "vehicleCount",
    "requestRate",
    "maxTripDistance",
  ];

  for (const param of paramsToCheck) {
    const value = settings[param];
    const config = scaleConfig[param];

    // Skip if parameter not present in settings
    if (value === undefined || value === null) continue;

    // Skip if scale config doesn't define this parameter
    if (!config || config.min === undefined || config.max === undefined)
      continue;

    // Check if value is within range
    if (value < config.min || value > config.max) {
      return false;
    }
  }

  return true;
}

/**
 * Infer the best-fit scale preset from settings
 * Prefers the smallest scale that can accommodate all parameters
 * @param {Object} settings - Settings object
 * @returns {string} Scale name: 'village', 'town', or 'city'
 */
export function inferScaleFromSettings(settings) {
  // Try scales in order from smallest to largest
  const scales = ["village", "town", "city"];

  for (const scale of scales) {
    if (isWithinRange(settings, SCALE_CONFIGS[scale])) {
      return scale;
    }
  }

  // If no scale fits, default to city (largest)
  return "city";
}

/**
 * Clamp settings values to fit within scale ranges
 * @param {Object} settings - Settings object to clamp
 * @param {string} scaleName - Scale name ('village', 'town', 'city')
 * @returns {Object} { clampedSettings, warnings }
 *   - clampedSettings: Settings with values clamped to scale ranges
 *   - warnings: Array of warning messages for clamped values
 */
export function clampToScale(settings, scaleName) {
  const scaleConfig = SCALE_CONFIGS[scaleName];
  const clampedSettings = { ...settings };
  const warnings = [];

  // Parameters that should be clamped
  const paramsToClamp = [
    "citySize",
    "vehicleCount",
    "requestRate",
    "maxTripDistance",
    "inhomogeneity",
    "price",
    "platformCommission",
    "reservationWage",
    "demandElasticity",
    "meanVehicleSpeed",
    "perKmPrice",
    "perMinutePrice",
    "perKmOpsCost",
    "perHourOpportunityCost",
    "animationDelay",
    "smoothingWindow",
  ];

  for (const param of paramsToClamp) {
    const value = settings[param];
    const config = scaleConfig[param];

    // Skip if parameter not present or no config
    if (value === undefined || value === null || !config) continue;

    // Skip if no min/max defined
    if (config.min === undefined || config.max === undefined) continue;

    let clamped = value;
    let wasModified = false;

    // Clamp to minimum
    if (value < config.min) {
      clamped = config.min;
      wasModified = true;
    }

    // Clamp to maximum
    if (value > config.max) {
      clamped = config.max;
      wasModified = true;
    }

    // Record warning if value was modified
    if (wasModified) {
      clampedSettings[param] = clamped;
      warnings.push({
        param,
        original: value,
        clamped: clamped,
        message: `${param} adjusted from ${value} to ${clamped} (${scaleName.toUpperCase()} range: ${config.min}-${config.max})`,
      });
    }
  }

  return { clampedSettings, warnings };
}

/**
 * Infer scale and clamp settings in one operation
 * @param {Object} settings - Settings object
 * @returns {Object} { scale, clampedSettings, warnings }
 */
export function inferAndClampSettings(settings) {
  const scale = inferScaleFromSettings(settings);
  const { clampedSettings, warnings } = clampToScale(settings, scale);

  return {
    scale,
    clampedSettings,
    warnings,
  };
}

/**
 * Get a summary of key parameters for display
 * @param {Object} settings - Settings object
 * @param {string} scale - Scale name
 * @returns {Object} Summary object with formatted values
 */
export function getConfigSummary(settings, scale) {
  return {
    scale: scale.toUpperCase(),
    citySize: settings.citySize,
    vehicleCount: settings.vehicleCount,
    requestRate: settings.requestRate,
    maxTripDistance: settings.maxTripDistance || "Auto",
    inhomogeneity: settings.inhomogeneity,
    equilibrate: settings.equilibrate,
    useCostsAndIncomes: settings.useCostsAndIncomes,
    price: settings.price,
    platformCommission: settings.platformCommission,
    reservationWage: settings.reservationWage,
  };
}
