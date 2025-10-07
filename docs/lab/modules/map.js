/* global Chart */
import { colors } from "../js/constants.js";
// const startTime = Date.now();

let citySize = 0;
let vehicleRadius = 16;

// Cache for vehicle canvas elements
const vehicleCanvasCache = new Map();

// Cache for person canvas elements
const personCanvasCache = new Map();

// Cache for house canvas elements
const houseCanvasCache = new Map();

// Track active pickup pulse animations
const activePickupPulses = [];

// Create a canvas-based vehicle point style with specific color
function createVehicleCanvas(color = "#ffff00", vehicleRadius = 8) {
  const canvas = document.createElement("canvas");
  const size = vehicleRadius * 2.5; // Canvas size based on vehicle radius
  canvas.width = size;
  canvas.height = size;

  const ctx = canvas.getContext("2d");
  const center = size / 2;

  // Save context and apply rotation
  ctx.save();
  ctx.translate(center, center);

  // Draw vehicle as rectangle
  const carLength = vehicleRadius * 1.6; // Front to back (long dimension)
  const carWidth = vehicleRadius * 1.0; // Side to side (short dimension)

  // Main car body (rounded rectangle) with specified color
  const cornerRadius = vehicleRadius * 0.2;
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.roundRect(
    -carWidth / 2,
    -carLength / 2,
    carWidth,
    carLength,
    cornerRadius
  );
  ctx.fill();
  ctx.strokeStyle = "grey";
  ctx.lineWidth = 1;
  ctx.stroke();

  // Wheels (small dark rectangles on sides)
  const wheelWidth = vehicleRadius * 0.2;
  const wheelLength = vehicleRadius * 0.4;
  const wheelOffset = carLength * 0.25; // Position wheels 25% from front/back
  ctx.fillStyle = "#333333";

  // Left wheels
  ctx.fillRect(
    -carWidth / 2 - wheelWidth / 2,
    -wheelOffset,
    wheelWidth,
    wheelLength
  );
  ctx.fillRect(
    -carWidth / 2 - wheelWidth / 2,
    wheelOffset - wheelLength,
    wheelWidth,
    wheelLength
  );

  // Right wheels
  ctx.fillRect(
    carWidth / 2 - wheelWidth / 2,
    -wheelOffset,
    wheelWidth,
    wheelLength
  );
  ctx.fillRect(
    carWidth / 2 - wheelWidth / 2,
    wheelOffset - wheelLength,
    wheelWidth,
    wheelLength
  );

  // Windshield area (larger, more defined front indicator)
  const windshieldWidth = carWidth * 0.6;
  const windshieldLength = vehicleRadius * 0.4;
  ctx.fillStyle = "#000000";
  ctx.beginPath();
  ctx.roundRect(
    -windshieldWidth / 2,
    -carLength / 2,
    windshieldWidth,
    windshieldLength,
    cornerRadius * 0.5
  );
  ctx.fill();

  ctx.restore();
  return canvas;
}

// Create a canvas-based person point style with specific color
function createPersonCanvas(color = "#95ff6bff", personRadius = 8) {
  const canvas = document.createElement("canvas");
  const size = personRadius * 2.5; // Canvas size based on person radius
  canvas.width = size;
  canvas.height = size;

  const ctx = canvas.getContext("2d");
  const center = size / 2;

  // Save context
  ctx.save();
  ctx.translate(center, center);

  // Draw person as head + shoulders silhouette
  const headRadius = personRadius * 0.4;
  const shoulderWidth = personRadius * 1.2;
  const shoulderHeight = personRadius * 0.6;
  const neckWidth = personRadius * 0.25;
  const neckHeight = personRadius * 0.3;

  // Draw shoulders (rounded rectangle base)
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.roundRect(
    -shoulderWidth / 2,
    headRadius + neckHeight - shoulderHeight / 2,
    shoulderWidth,
    shoulderHeight,
    personRadius * 0.15
  );
  ctx.fill();
  ctx.strokeStyle = "#333333";
  ctx.lineWidth = 1;
  ctx.stroke();

  // Draw neck (small rectangle connecting head to shoulders)
  ctx.fillStyle = color;
  ctx.fillRect(-neckWidth / 2, headRadius, neckWidth, neckHeight);

  // Draw head (circle)
  ctx.fillStyle = color;
  ctx.beginPath();
  ctx.arc(0, 0, headRadius, 0, 2 * Math.PI);
  ctx.fill();
  ctx.strokeStyle = "#333333";
  ctx.lineWidth = 1;
  ctx.stroke();

  ctx.restore();
  return canvas;
}

// Get cached vehicle canvas or create new one
function getCachedVehicleCanvas(color, vehicleRadius) {
  const key = `${color}_${vehicleRadius}`;
  if (!vehicleCanvasCache.has(key)) {
    vehicleCanvasCache.set(key, createVehicleCanvas(color, vehicleRadius));
  }
  return vehicleCanvasCache.get(key);
}

// Create a canvas-based house point style with specific color
function createHouseCanvas(color = "#4ecdc4", houseRadius = 8) {
  const canvas = document.createElement("canvas");
  const size = houseRadius * 2.5; // Canvas size based on house radius
  canvas.width = size;
  canvas.height = size;

  const ctx = canvas.getContext("2d");
  const center = size / 2;

  // Save context
  ctx.save();
  ctx.translate(center, center);

  // Draw house as rectangle base + triangle roof
  const houseWidth = houseRadius * 1.3;
  const houseHeight = houseRadius * 0.8;
  const roofHeight = houseRadius * 0.6;

  // Draw main house body (rectangle)
  ctx.fillStyle = color;
  ctx.fillRect(-houseWidth / 2, -houseHeight / 2 + roofHeight / 2, houseWidth, houseHeight);
  ctx.strokeStyle = "#333333";
  ctx.lineWidth = 1;
  ctx.strokeRect(-houseWidth / 2, -houseHeight / 2 + roofHeight / 2, houseWidth, houseHeight);

  // Draw roof (triangle)
  ctx.fillStyle = color; // Same color as house body
  ctx.beginPath();
  ctx.moveTo(0, -houseHeight / 2 - roofHeight / 2); // Top point of roof
  ctx.lineTo(-houseWidth / 2 - houseRadius * 0.1, -houseHeight / 2 + roofHeight / 2); // Left base
  ctx.lineTo(houseWidth / 2 + houseRadius * 0.1, -houseHeight / 2 + roofHeight / 2); // Right base
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "#333333";
  ctx.lineWidth = 1;
  ctx.stroke();

  // Draw door (small rectangle in center of house)
  const doorWidth = houseWidth * 0.25;
  const doorHeight = houseHeight * 0.4;
  ctx.fillStyle = "#654321"; // Dark brown door
  ctx.fillRect(-doorWidth / 2, houseHeight / 2 - doorHeight + roofHeight / 2, doorWidth, doorHeight);

  // Draw window (small square)
  const windowSize = houseWidth * 0.15;
  ctx.fillStyle = "#87CEEB"; // Light blue window
  ctx.fillRect(houseWidth * 0.15, -houseHeight * 0.1 + roofHeight / 2, windowSize, windowSize);
  ctx.strokeStyle = "#333333";
  ctx.lineWidth = 1;
  ctx.strokeRect(houseWidth * 0.15, -houseHeight * 0.1 + roofHeight / 2, windowSize, windowSize);

  ctx.restore();
  return canvas;
}

// Get cached person canvas or create new one
function getCachedPersonCanvas(color, personRadius) {
  const key = `${color}_${personRadius}`;
  if (!personCanvasCache.has(key)) {
    personCanvasCache.set(key, createPersonCanvas(color, personRadius));
  }
  return personCanvasCache.get(key);
}

// Get cached house canvas or create new one
function getCachedHouseCanvas(color, houseRadius) {
  const key = `${color}_${houseRadius}`;
  if (!houseCanvasCache.has(key)) {
    houseCanvasCache.set(key, createHouseCanvas(color, houseRadius));
  }
  return houseCanvasCache.get(key);
}

/**
 * Detect new pickup events and create pulse animations
 * @param {Array} vehicles - Array of vehicle data [phase, location, direction, pickup_countdown]
 * @param {number} animationDelay - Animation delay in milliseconds
 */
function detectAndAnimatePickups(vehicles, animationDelay) {
  vehicles.forEach((vehicle) => {
    const pickupCountdown = vehicle[3];

    // Detect first frame of pickup (pickup_countdown just became > 0)
    // This happens when vehicle first arrives at pickup location
    if (pickupCountdown !== null && pickupCountdown > 0) {
      const location = vehicle[1];

      // Check if we already have a pulse at this location (avoid duplicates)
      const existingPulse = activePickupPulses.find(
        p => p.x === location[0] && p.y === location[1] && p.age < 100
      );

      if (!existingPulse) {
        // Create new pulse animation
        const waitingColor = colors.get("WAITING"); // Passenger waiting color
        activePickupPulses.push({
          x: location[0],
          y: location[1],
          age: 0,
          maxAge: animationDelay * 0.8, // Pulse duration ~0.8 of animation delay
          color: waitingColor,
          initialRadius: vehicleRadius * 0.8,
          maxRadius: vehicleRadius * 2.5,
        });
      }
    }
  });
}

/**
 * Update pickup pulse animations and render to chart
 */
function updatePickupPulses() {
  const pulseData = [];
  const pulseRadii = [];
  const pulseColors = [];
  const pulseBorders = [];

  // Update each pulse and prepare render data
  for (let i = activePickupPulses.length - 1; i >= 0; i--) {
    const pulse = activePickupPulses[i];
    pulse.age += 16; // Increment age (~16ms per frame assuming 60fps)

    if (pulse.age >= pulse.maxAge) {
      // Remove completed pulses
      activePickupPulses.splice(i, 1);
      continue;
    }

    // Calculate animation progress (0 to 1)
    const progress = pulse.age / pulse.maxAge;

    // Ease-out function for smooth deceleration
    const easeOut = 1 - Math.pow(1 - progress, 2);

    // Animate radius (expand)
    const radius = pulse.initialRadius + (pulse.maxRadius - pulse.initialRadius) * easeOut;

    // Animate opacity (fade out)
    const opacity = 1 - progress;

    // Convert hex color to rgba with opacity
    const rgbaColor = hexToRgba(pulse.color, opacity * 0.6);
    const rgbaBorder = hexToRgba(pulse.color, opacity * 0.8);

    pulseData.push({ x: pulse.x, y: pulse.y });
    pulseRadii.push(radius);
    pulseColors.push(rgbaColor);
    pulseBorders.push(rgbaBorder);
  }

  // Update chart dataset
  window.chart.data.datasets[2].data = pulseData;
  window.chart.data.datasets[2].pointRadius = pulseRadii;
  window.chart.data.datasets[2].pointBackgroundColor = pulseColors;
  window.chart.data.datasets[2].borderColor = pulseBorders;
}

/**
 * Convert hex color to rgba with opacity
 * @param {string} hex - Hex color code
 * @param {number} alpha - Opacity (0-1)
 * @returns {string} rgba color string
 */
function hexToRgba(hex, alpha) {
  // Remove # if present
  hex = hex.replace('#', '');

  // Parse hex to RGB
  const r = parseInt(hex.substring(0, 2), 16);
  const g = parseInt(hex.substring(2, 4), 16);
  const b = parseInt(hex.substring(4, 6), 16);

  return `rgba(${r}, ${g}, ${b}, ${alpha})`;
}

export function initMap(uiSettings, simSettings) {
  // data sets:
  // [0] - vehicles
  // [1] - trips
  citySize = simSettings.citySize;
  vehicleRadius = uiSettings.displayVehicleRadius;

  const mapOptions = {
    // resize behaviour
    responsive: true,
    maintainAspectRatio: true,
    aspectRatio: 1,
    layout: {
      padding: 0,
      autoPadding: false,
    },
    scales: {
      x: {
        min: -0.5,
        max: citySize - 0.5,
        border: { display: false },
        grid: {
          lineWidth: uiSettings.displayRoadWidth,
          color: colors.get("ROAD"),
          //drawOnChartArea: true,
          drawTicks: false,
        },
        type: "linear",
        ticks: {
          display: false,
          includeBounds: false,
          maxTicksLimits: citySize,
          drawTicks: false,
          stepSize: 0.5,
          callback: function (tick, index) {
            return index % 2 != 0 ? "" : null;
          },
        },
      },
      y: {
        min: -0.5,
        max: citySize - 0.5,
        border: { display: false },
        grid: {
          lineWidth: uiSettings.displayRoadWidth,
          color: colors.get("ROAD"),
          drawTicks: false,
        },
        type: "linear",
        ticks: {
          display: false,
          includeBounds: false,
          maxTicksLimits: citySize,
          drawTicks: false,
          stepSize: 0.5,
          callback: function (value, index, ticks) {
            return index % 2 != 0 ? "" : null;
          },
        },
      },
    },
    elements: {
      line: {
        borderWidth: 0,
        tension: 0.4,
      },
    },
    transitions: {
      duration: 0,
      easing: "linear",
      delay: 0,
      loop: false,
    },
    animation: {
      duration: 0,
      easing: "linear",
      delay: 0,
      loop: false,
      // onComplete: function(animation){
      // animation.chart.data.datasets[0].pointBackgroundColor = 'rgba(0, 255, 0, 0.8)';
      // }
    },
    animations: {
      properties: ["x", "y"],
    },
    plugins: {
      legend: {
        display: false,
      },
      datalabels: {
        display: false,
      },
    },
  };

  const mapConfig = {
    type: "scatter",
    data: {
      datasets: [
        {
          // vehicles
          data: null,
          pointStyle: [], // Will be populated with individual vehicle canvases
          pointRadius: uiSettings.displayVehicleRadius,
          borderColor: "grey",
          borderWidth: 1,
          hoverRadius: 16,
        },
        {
          // trips
          data: null,
          pointStyle: "circle",
          pointRadius: uiSettings.displayVehicleRadius,
          borderColor: "grey",
          borderWidth: 1,
        },
        {
          // pickup pulse rings
          data: [],
          pointStyle: "circle",
          pointRadius: [],
          pointBackgroundColor: [],
          borderColor: [],
          borderWidth: 2,
          hoverRadius: 0,
        },
      ],
    },
    options: mapOptions,
  };
  //options: {}

  if (window.chart instanceof Chart) {
    window.chart.destroy();
  }

  window.chart = new Chart(uiSettings.ctxMap, mapConfig);
}

// Handle map simSettings
export function plotMap(eventData) {
  try {
    if (eventData != null) {
      if (eventData.size < 2) {
        console.log("m: error? ", eventData);
      }
      // console.log("In plotMap: eventData=", eventData);
      // "block": integer,
      let frameIndex = eventData.get("block");
      //  "vehicles": [[phase.name, location, direction],...],
      let vehicles = eventData.get("vehicles");
      let animationDelay = eventData.get("animationDelay");
      let vehicleLocations = [];
      let vehicleColors = [];
      let vehicleStyles = [];
      let vehicleRotations = [];
      vehicles.forEach((vehicle) => {
        const phaseColor = colors.get(vehicle[0]);
        vehicleColors.push(phaseColor);
        vehicleLocations.push({ x: vehicle[1][0], y: vehicle[1][1] });

        // Create individual vehicle canvas with phase-specific color
        const vehicleCanvas = getCachedVehicleCanvas(phaseColor, vehicleRadius);
        vehicleStyles.push(vehicleCanvas);

        let rot = 0;
        if (vehicle[2] == "NORTH") {
          rot = 0;
        } else if (vehicle[2] == "EAST") {
          rot = 90;
        } else if (vehicle[2] == "SOUTH") {
          rot = 180;
        } else if (vehicle[2] == "WEST") {
          rot = 270;
        }
        vehicleRotations.push(rot);
      });
      // "trips": [[phase.name, origin, destination, distance],...],
      let trips = eventData.get("trips");
      let tripLocations = [];
      let tripColors = [];
      let tripStyles = [];
      trips.forEach((trip) => {
        // console.log("trip=", trip);
        /* Trip phases: INACTIVE = 0, UNASSIGNED = 1, WAITING = 2
                      RIDING = 3, COMPLETED = 4, CANCELLED = 5
    */
        if (trip[0] == "UNASSIGNED" || trip[0] == "WAITING") {
          tripLocations.push({ x: trip[1][0], y: trip[1][1] });
          const tripColor = colors.get(trip[0]);
          tripColors.push(tripColor);
          // Use person canvas for trip origins (passengers waiting)
          const personCanvas = getCachedPersonCanvas(tripColor, vehicleRadius);
          tripStyles.push(personCanvas);
        } else if (trip[0] == "RIDING") {
          tripLocations.push({ x: trip[2][0], y: trip[2][1] });
          const tripColor = colors.get(trip[0]);
          tripColors.push(tripColor);
          // Use house canvas for trip destinations
          const houseCanvas = getCachedHouseCanvas(tripColor, vehicleRadius);
          tripStyles.push(houseCanvas);
        }
      });
      // let time = Math.round((Date.now() - startTime) / 100) * 100;
      // console.log("m (", time, "): Regular-updated chart: locations[0] = ", locations[0]);
      if (frameIndex % 2 != 0) {
        // interpolation point: change directions and trip marker location
        window.chart.data.datasets[1].pointBackgroundColor = tripColors;
        window.chart.data.datasets[1].pointStyle = tripStyles;
        window.chart.data.datasets[1].animationDuration = 0;
        window.chart.data.datasets[1].data = tripLocations;
        window.chart.data.datasets[0].rotation = vehicleRotations;
        window.chart.data.datasets[0].pointStyle = vehicleStyles;
      }
      window.chart.options.animation.duration = 0;
      window.chart.update("none");
      window.chart.data.datasets[0].data = vehicleLocations;
      if (frameIndex == 0) {
        window.chart.options.animation.duration = 0;
      } else {
        window.chart.options.animation.duration = animationDelay;
      }
      window.chart.data.datasets[0].pointBackgroundColor = vehicleColors;
      window.chart.data.datasets[0].pointStyle = vehicleStyles;

      // Detect new pickups and create pulse animations
      detectAndAnimatePickups(vehicles, animationDelay);

      // Update pickup pulse animations
      updatePickupPulses();

      window.chart.update();
      let needsRefresh = false;
      let updatedLocations = [];
      vehicleLocations.forEach((vehicle) => {
        let newX = vehicle.x;
        let newY = vehicle.y;
        if (vehicle.x > citySize - 0.6) {
          // going off the right side
          newX = -0.5;
          needsRefresh = true;
        }
        if (vehicle.x < -0.1) {
          // going off the left side
          newX = citySize - 0.5;
          needsRefresh = true;
        }
        if (vehicle.y > citySize - 0.9) {
          // going off the top
          newY = -0.5;
          needsRefresh = true;
        }
        if (vehicle.y < -0.1) {
          // going off the bottom
          newY = citySize - 0.5;
          needsRefresh = true;
        }
        updatedLocations.push({ x: newX, y: newY });
      });
      if (needsRefresh == true) {
        // Reappear on the opposite  side of the chart
        // time = Math.round((Date.now() - startTime) / 100) * 100;
        // console.log("m (", time, "): Edge-updated chart: locations[0] = ", updatedLocations[0]);
        window.chart.data.datasets[0].pointBackgroundColor = vehicleColors;
        window.chart.data.datasets[0].pointStyle = vehicleStyles;
        window.chart.data.datasets[0].rotation = vehicleRotations;
        window.chart.update("none");
        window.chart.data.datasets[0].data = updatedLocations;
        window.chart.data.datasets[0].pointBackgroundColor = vehicleColors;
        window.chart.data.datasets[0].pointStyle = vehicleStyles;
        window.chart.update("none");
      }
    }
  } catch (error) {
    console.log("Error in plotMap: ", error.message);
    console.error("-- stack trace:", error.stack);
  }
}
