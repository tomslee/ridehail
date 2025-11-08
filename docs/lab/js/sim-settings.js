import { DOM_ELEMENTS } from "./dom-elements.js";
import { CHART_TYPES, SCALE_CONFIGS, SimulationActions } from "./config.js";

/**
 * @Class
 * Container for simulation settings, which will be posted to webworker to
 * interact with the pyodide python module
 */
export class SimSettings {
  /**
   * For now, a set of "reasonable" defaults are set on initialization. It
   * would be good to have these chosen in a less arbitrary fashion.
   */
  constructor(scaleConfig = SCALE_CONFIGS.village, name = "labSimSettings") {
    this.name = name;
    this.scale = scaleConfig.scale;
    this.citySize = scaleConfig.citySize.value;
    this.vehicleCount = scaleConfig.vehicleCount.value;
    this.requestRate = scaleConfig.requestRate.value;
    this.maxTripDistance = scaleConfig.maxTripDistance.value;
    this.inhomogeneity = scaleConfig.inhomogeneity.value;
    this.price = scaleConfig.price.value;
    this.platformCommission = scaleConfig.platformCommission.value;
    this.reservationWage = scaleConfig.reservationWage.value;
    this.demandElasticity = scaleConfig.demandElasticity.value;
    this.minutesPerBlock = 1;
    this.meanVehicleSpeed = scaleConfig.meanVehicleSpeed.value;
    this.perKmPrice = scaleConfig.perKmPrice.value;
    this.perMinutePrice = scaleConfig.perMinutePrice.value;
    this.perKmOpsCost = scaleConfig.perKmOpsCost.value;
    this.perHourOpportunityCost = scaleConfig.perHourOpportunityCost.value;
    this.animationDelay = scaleConfig.animationDelay.value;
    this.smoothingWindow = scaleConfig.smoothingWindow.value;
    this.verbosity = 0;
    this.timeBlocks = 0;
    this.frameIndex = 0;
    this.blockIndex = 0;
    this.useCostsAndIncomes = false;
    this.action = null;
    this.chartType = CHART_TYPES.MAP;
    this.inhomogeneousDestinations = false;
    this.idleVehiclesMoving = true;
    this.randomNumberSeed = 87;
    this.equilibrate = false; // Boolean for UI checkbox (backward compatibility)
    this.equilibration = "none"; // String for actual equilibration method (none/price/supply)
    this.equilibrationInterval = 5;
    this.pickupTime = 1;
  }

  // Validation method
  validate() {
    const errors = [];
    if (this.citySize <= 0) errors.push("City size must be positive");
    if (this.vehicleCount < 0)
      errors.push("Vehicle count must be non-negative");
    if (this.requestRate < 0) errors.push("Request rate must be non-negative");
    return errors;
  }

  // reset to initial state, but keeping the configuration items the same
  resetToStart() {
    this.action = SimulationActions.Reset;
    this.frameIndex = 0;
    this.blockIndex = 0;
    this.timeBlocks = 0; // Clear time limit on reset
  }
}

export class WhatIfSimSettingsDefault extends SimSettings {
  constructor() {
    super();
    this.name = "whatIfSimSettingsDefault";
    this.citySize = 24;
    this.vehicleCount = 160;
    this.requestRate = 8;
    this.timeBlocks = 200;
    this.smoothingWindow = 50;
    this.useCostsAndIncomes = false;
    this.platformCommission = 0.25;
    this.price = 0.6;
    this.reservationWage = 0.21;
    this.inhomogeneity = 0.5;
    this.meanVehicleSpeed = 30;
    this.equilibrate = true; // Boolean for UI checkbox - WhatIf uses equilibration by default
    this.equilibration = "price"; // String for actual equilibration method - WhatIf defaults to price
    this.perKmPrice = 0.8;
    this.perMinutePrice = 0.2;
    this.perKmOpsCost = 0.25;
    this.perHourOpportunityCost = 5.0;
    this.action =
      DOM_ELEMENTS.whatIf.baselineFabButton.firstElementChild.innerHTML;
    this.animationDelay = 0;
    this.chartType = CHART_TYPES.WHAT_IF;
    this.pickupTime = 1;
  }
}

// Settings factory
export function createSettingsFromConfig(config, domElements) {
  const settings = new SimSettings();

  Object.entries(config).forEach(([key, spec]) => {
    try {
      if (spec.value !== undefined) {
        settings[key] = spec.value;
      } else if (spec.source === "input") {
        const element = domElements.inputs[spec.element];
        if (element) {
          settings[key] = spec.parser
            ? spec.parser(element.value)
            : element.value;
        }
      } else if (spec.source === "custom" && spec.getter) {
        settings[key] = spec.getter();
      }
    } catch (error) {
      console.warn(`Failed to initialize setting '${key}':`, error);
    }
  });

  return settings;
}
