import { DOM_ELEMENTS } from "./dom-elements.js";
import { CHART_TYPES } from "./config.js";

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
  constructor() {
    this.name = "SimSettings";
    this.citySize = 4;
    this.vehicleCount = 1;
    this.requestRate = 0.1;
    this.smoothingWindow = 20;
    this.maxTripDistance = null;
    this.inhomogeneity = 0;
    this.inhomogeneousDestinations = false;
    this.idleVehiclesMoving = true;
    this.randomNumberSeed = 87;
    this.equilibrate = false;
    this.equilibration = "price";
    this.equilibrationInterval = 5;
    this.demandElasticity = 0.0;
    this.price = 1.0;
    this.platformCommission = 0;
    this.reservationWage = 0;
    this.useCityScale = false;
    this.minutesPerBlock = 1;
    this.meanVehicleSpeed = 30.0;
    this.perKmPrice = 0.18;
    this.perMinutePrice = 0.81;
    this.perKmOpsCost = 0.2;
    this.perHourOpportunityCost = 10;
    this.verbosity = 0;
    this.timeBlocks = 0;
    this.frameIndex = 0;
    this.frameTimeout = 0;
    this.action = null;
    this.scaleType = "village";
    this.chartType = CHART_TYPES.MAP;
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
    this.useCityScale = false;
    this.platformCommission = 0.25;
    this.price = 0.6;
    this.reservationWage = 0.21;
    this.inhomogeneity = 0.5;
    this.meanVehicleSpeed = 30;
    this.equilibrate = true;
    this.perKmPrice = 0.8;
    this.perMinutePrice = 0.2;
    this.perKmOpsCost = 0.25;
    this.perHourOpportunityCost = 5.0;
    this.action = DOM_ELEMENTS.whatIf.fabButton.firstElementChild.innerHTML;
    this.frameTimeout = 0;
    this.chartType = CHART_TYPES.WHAT_IF;
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
