/**
 * Parameter Mapping Between Web and Desktop Configurations
 * Maps between web SimSettings format and desktop .config file format
 */

import { getINIValue } from "./config-file.js";

/**
 * Mapping from desktop config parameters to web SimSettings properties
 * Structure: { SECTION_NAME: { desktop_key: 'webPropertyName' } }
 */
const DESKTOP_TO_WEB_MAPPING = {
  DEFAULT: {
    city_size: "citySize",
    vehicle_count: "vehicleCount",
    base_demand: "requestRate",
    inhomogeneity: "inhomogeneity",
    inhomogeneous_destinations: "inhomogeneousDestinations",
    max_trip_distance: "maxTripDistance",
    min_trip_distance: "minTripDistance",
    time_blocks: "timeBlocks",
    idle_vehicles_moving: "idleVehiclesMoving",
    random_number_seed: "randomNumberSeed",
    verbosity: "verbosity",
    equilibrate: "equilibrate",
    use_city_scale: "useCostsAndIncomes",
    pickup_time: "pickupTime",
  },
  ANIMATION: {
    animation_delay: "animationDelay",
    smoothing_window: "smoothingWindow",
  },
  EQUILIBRATION: {
    equilibration: "equilibration",
    reservation_wage: "reservationWage",
    price: "price",
    platform_commission: "platformCommission",
    demand_elasticity: "demandElasticity",
    equilibration_interval: "equilibrationInterval",
  },
  CITY_SCALE: {
    mean_vehicle_speed: "meanVehicleSpeed",
    minutes_per_block: "minutesPerBlock",
    per_km_ops_cost: "perKmOpsCost",
    per_hour_opportunity_cost: "perHourOpportunityCost",
    per_km_price: "perKmPrice",
    per_minute_price: "perMinutePrice",
  },
};

/**
 * Reverse mapping from web to desktop (generated from above)
 */
export const WEB_TO_DESKTOP_MAPPING = {};
for (const [section, mappings] of Object.entries(DESKTOP_TO_WEB_MAPPING)) {
  for (const [desktopKey, webKey] of Object.entries(mappings)) {
    WEB_TO_DESKTOP_MAPPING[webKey] = { section, key: desktopKey };
  }
}

/**
 * Convert desktop config (parsed INI) to web SimSettings format
 * @param {Object} parsedINI - Parsed INI configuration object
 * @returns {Object} Settings object compatible with SimSettings
 */
export function desktopToWebConfig(parsedINI) {
  const webConfig = {};

  // Process each section and map to web properties
  for (const [section, mappings] of Object.entries(DESKTOP_TO_WEB_MAPPING)) {
    if (!parsedINI[section]) continue;

    for (const [desktopKey, webKey] of Object.entries(mappings)) {
      const value = getINIValue(parsedINI, section, desktopKey);
      if (value !== null) {
        webConfig[webKey] = value;
      }
    }
  }

  // Special handling for animation_delay (seconds to milliseconds)
  if (webConfig.animationDelay !== undefined) {
    webConfig.animationDelay = webConfig.animationDelay * 1000;
  }

  // Special handling for equilibration: sync boolean and string properties
  // If equilibration string is set, derive the boolean equilibrate from it
  if (webConfig.equilibration !== undefined) {
    const equilibrationLower = String(webConfig.equilibration).toLowerCase();
    // equilibrate checkbox is true if equilibration is anything except "none"
    webConfig.equilibrate = equilibrationLower !== "none";
  } else if (webConfig.equilibrate !== undefined) {
    // If only equilibrate boolean is set, derive equilibration string
    webConfig.equilibration = webConfig.equilibrate ? "price" : "none";
  }

  return webConfig;
}

/**
 * Convert web SimSettings to desktop config format
 * @param {Object} labSimSettings - Web lab settings object
 * @returns {Object} Config sections for INI generation
 */
export function webToDesktopConfig(labSimSettings) {
  const config = {
    DEFAULT: {},
    ANIMATION: {},
    EQUILIBRATION: {},
    CITY_SCALE: {},
  };

  // Map each web property to its desktop location
  for (const [webKey, value] of Object.entries(labSimSettings)) {
    const mapping = WEB_TO_DESKTOP_MAPPING[webKey];
    if (mapping) {
      const { section, key } = mapping;
      config[section][key] = value;
    }
  }

  // Special handling for animation_delay (milliseconds to seconds)
  if (config.ANIMATION.animation_delay !== undefined) {
    config.ANIMATION.animation_delay = config.ANIMATION.animation_delay / 1000;
  }

  // Special handling for meanVehicleSpeed (default to 30 km/h if 0 or missing)
  if (
    !config.CITY_SCALE.mean_vehicle_speed ||
    config.CITY_SCALE.mean_vehicle_speed === 0
  ) {
    config.CITY_SCALE.mean_vehicle_speed = 30.0;
  }

  // Default values for parameters that may be missing (matching worker.py defaults)
  if (config.DEFAULT.min_trip_distance === undefined) {
    config.DEFAULT.min_trip_distance = 0;
  }
  if (config.DEFAULT.idle_vehicles_moving === undefined) {
    config.DEFAULT.idle_vehicles_moving = true;
  }
  if (config.DEFAULT.pickup_time === undefined) {
    config.DEFAULT.pickup_time = 1;
  }
  if (
    config.EQUILIBRATION &&
    config.EQUILIBRATION.equilibration === undefined
  ) {
    config.EQUILIBRATION.equilibration = "PRICE";
  }

  // Add metadata
  const timestamp = new Date().toISOString().replace("T", " ").substring(0, 19);
  config.DEFAULT.title = `Web Lab Configuration (${timestamp})`;

  // Set reasonable defaults for desktop-only parameters
  config.DEFAULT.run_sequence = false;
  config.ANIMATION.animation = "none";
  config.ANIMATION.interpolate = 0;

  return config;
}

/**
 * Get list of all web properties that can be mapped to/from desktop
 * @returns {string[]} Array of web property names
 */
export function getMappedWebProperties() {
  return Object.keys(WEB_TO_DESKTOP_MAPPING);
}

/**
 * Validate that a parsed config has required sections and parameters
 * @param {Object} parsedINI - Parsed INI configuration
 * @returns {Object} { valid: boolean, errors: string[], warnings: string[] }
 */
export function validateDesktopConfig(parsedINI) {
  const errors = [];
  const warnings = [];

  // Check for DEFAULT section (required)
  if (!parsedINI.DEFAULT) {
    errors.push("Missing required [DEFAULT] section");
  } else {
    // Check for critical parameters
    const requiredParams = ["city_size", "vehicle_count", "base_demand"];
    for (const param of requiredParams) {
      const value = getINIValue(parsedINI, "DEFAULT", param);
      if (value === null) {
        warnings.push(`Missing or empty parameter: ${param}`);
      }
    }
  }

  // Validate numeric ranges for key parameters
  if (parsedINI.DEFAULT) {
    const citySize = getINIValue(parsedINI, "DEFAULT", "city_size");
    if (citySize !== null && (citySize < 2 || citySize > 200)) {
      warnings.push(`city_size (${citySize}) outside typical range [2-200]`);
    }

    const vehicleCount = getINIValue(parsedINI, "DEFAULT", "vehicle_count");
    if (vehicleCount !== null && vehicleCount < 0) {
      errors.push(`vehicle_count (${vehicleCount}) cannot be negative`);
    }

    const baseDemand = getINIValue(parsedINI, "DEFAULT", "base_demand");
    if (baseDemand !== null && baseDemand < 0) {
      errors.push(`base_demand (${baseDemand}) cannot be negative`);
    }
  }

  return {
    valid: errors.length === 0,
    errors,
    warnings,
  };
}
