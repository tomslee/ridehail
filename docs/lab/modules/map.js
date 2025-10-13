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
    cornerRadius,
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
    wheelLength,
  );
  ctx.fillRect(
    -carWidth / 2 - wheelWidth / 2,
    wheelOffset - wheelLength,
    wheelWidth,
    wheelLength,
  );

  // Right wheels
  ctx.fillRect(
    carWidth / 2 - wheelWidth / 2,
    -wheelOffset,
    wheelWidth,
    wheelLength,
  );
  ctx.fillRect(
    carWidth / 2 - wheelWidth / 2,
    wheelOffset - wheelLength,
    wheelWidth,
    wheelLength,
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
    cornerRadius * 0.5,
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
    personRadius * 0.15,
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
  ctx.fillRect(
    -houseWidth / 2,
    -houseHeight / 2 + roofHeight / 2,
    houseWidth,
    houseHeight,
  );
  ctx.strokeStyle = "#333333";
  ctx.lineWidth = 1;
  ctx.strokeRect(
    -houseWidth / 2,
    -houseHeight / 2 + roofHeight / 2,
    houseWidth,
    houseHeight,
  );

  // Draw roof (triangle)
  ctx.fillStyle = color; // Same color as house body
  ctx.beginPath();
  ctx.moveTo(0, -houseHeight / 2 - roofHeight / 2); // Top point of roof
  ctx.lineTo(
    -houseWidth / 2 - houseRadius * 0.1,
    -houseHeight / 2 + roofHeight / 2,
  ); // Left base
  ctx.lineTo(
    houseWidth / 2 + houseRadius * 0.1,
    -houseHeight / 2 + roofHeight / 2,
  ); // Right base
  ctx.closePath();
  ctx.fill();
  ctx.strokeStyle = "#333333";
  ctx.lineWidth = 1;
  ctx.stroke();

  // Draw door (small rectangle in center of house)
  const doorWidth = houseWidth * 0.25;
  const doorHeight = houseHeight * 0.4;
  ctx.fillStyle = "#654321"; // Dark brown door
  ctx.fillRect(
    -doorWidth / 2,
    houseHeight / 2 - doorHeight + roofHeight / 2,
    doorWidth,
    doorHeight,
  );

  // Draw window (small square)
  const windowSize = houseWidth * 0.15;
  ctx.fillStyle = "#87CEEB"; // Light blue window
  ctx.fillRect(
    houseWidth * 0.15,
    -houseHeight * 0.1 + roofHeight / 2,
    windowSize,
    windowSize,
  );
  ctx.strokeStyle = "#333333";
  ctx.lineWidth = 1;
  ctx.strokeRect(
    houseWidth * 0.15,
    -houseHeight * 0.1 + roofHeight / 2,
    windowSize,
    windowSize,
  );

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

/**
 * Update map visualization with current simulation state
 *
 * Renders vehicles and trip markers on the map. When a vehicle arrives at a
 * trip origin to pick up a passenger (pickup_countdown > 0), both the vehicle
 * and the trip marker are enlarged by 50% to subtly highlight the pickup moment.
 *
 * @param {Map} eventData - Simulation frame data containing vehicles, trips, and metadata
 */
export function plotMap(eventData) {
  try {
    if (eventData != null) {
      if (eventData.size < 2) {
        console.log("m: error? ", eventData);
      }
      let frameIndex = eventData.get("frame");
      // Vehicle data format: [phase.name, location, direction, pickup_countdown]
      let vehicles = eventData.get("vehicles");
      let animationDelay = eventData.get("animationDelay");
      let vehicleLocations = [];
      let vehicleColors = [];
      let vehicleStyles = [];
      let vehicleRotations = [];
      let vehicleRadii = [];
      vehicles.forEach((vehicle) => {
        // Handle both array format [phase, location, direction, pickup_countdown]
        // and object format {phase, location, direction, pickup_countdown}
        const phase = vehicle.phase || vehicle[0];
        const location = vehicle.location || vehicle[1];
        const direction = vehicle.direction || vehicle[2];
        const pickupCountdown =
          vehicle.pickup_countdown !== undefined
            ? vehicle.pickup_countdown
            : vehicle[3] !== undefined
              ? vehicle[3]
              : null;

        const phaseColor = colors.get(phase);
        vehicleColors.push(phaseColor);
        vehicleLocations.push({ x: location[0], y: location[1] });

        // Check if vehicle is at pickup location (pickup_countdown > 0)
        // When true, enlarge the vehicle to highlight the pickup moment
        const isAtPickup =
          pickupCountdown !== null &&
          pickupCountdown !== undefined &&
          pickupCountdown > 0;

        // Increase vehicle size by 50% during pickup for visual emphasis
        const effectiveRadius = isAtPickup
          ? vehicleRadius * 1.5
          : vehicleRadius;
        vehicleRadii.push(effectiveRadius);

        // Create individual vehicle canvas with phase-specific color and size
        const vehicleCanvas = getCachedVehicleCanvas(
          phaseColor,
          effectiveRadius,
        );
        vehicleStyles.push(vehicleCanvas);

        let rot = 0;
        if (direction == "NORTH") {
          rot = 0;
        } else if (direction == "EAST") {
          rot = 90;
        } else if (direction == "SOUTH") {
          rot = 180;
        } else if (direction == "WEST") {
          rot = 270;
        }
        vehicleRotations.push(rot);
      });

      // Build a set of pickup locations to match with trip markers
      // This allows us to enlarge trip markers when a vehicle is picking up at that location
      const pickupLocations = new Set();
      vehicles.forEach((vehicle) => {
        const pickupCountdown =
          vehicle.pickup_countdown !== undefined
            ? vehicle.pickup_countdown
            : vehicle[3] !== undefined
              ? vehicle[3]
              : null;
        if (
          pickupCountdown !== null &&
          pickupCountdown !== undefined &&
          pickupCountdown > 0
        ) {
          const loc = vehicle.location || vehicle[1];
          pickupLocations.add(`${loc[0]},${loc[1]}`);
        }
      });

      // Process trip markers (trip origins and destinations)
      let trips = eventData.get("trips");
      let tripLocations = [];
      let tripColors = [];
      let tripStyles = [];
      let tripRadii = [];
      trips.forEach((trip) => {
        /* Trip phases: INACTIVE = 0, UNASSIGNED = 1, WAITING = 2
                      RIDING = 3, COMPLETED = 4, CANCELLED = 5 */
        if (trip[0] == "UNASSIGNED" || trip[0] == "WAITING") {
          const tripLoc = { x: trip[1][0], y: trip[1][1] };
          tripLocations.push(tripLoc);
          const tripColor = colors.get(trip[0]);
          tripColors.push(tripColor);

          // Enlarge trip marker if a vehicle is picking up at this location
          const isBeingPickedUp = pickupLocations.has(
            `${tripLoc.x},${tripLoc.y}`,
          );
          const effectiveRadius = isBeingPickedUp
            ? vehicleRadius * 1.5
            : vehicleRadius;
          tripRadii.push(effectiveRadius);

          // Use person canvas for trip origins (passengers waiting)
          const personCanvas = getCachedPersonCanvas(
            tripColor,
            effectiveRadius,
          );
          tripStyles.push(personCanvas);
        } else if (trip[0] == "RIDING") {
          tripLocations.push({ x: trip[2][0], y: trip[2][1] });
          const tripColor = colors.get(trip[0]);
          tripColors.push(tripColor);
          tripRadii.push(vehicleRadius);
          // Use house canvas for trip destinations
          const houseCanvas = getCachedHouseCanvas(tripColor, vehicleRadius);
          tripStyles.push(houseCanvas);
        }
      });
      // Update chart with vehicle and trip data
      // Individual point radii allow for dynamic sizing during pickup events
      if (frameIndex % 2 != 0) {
        // Interpolation point: update directions, trip marker locations, and sizes
        window.chart.data.datasets[1].pointBackgroundColor = tripColors;
        window.chart.data.datasets[1].pointStyle = tripStyles;
        window.chart.data.datasets[1].pointRadius = tripRadii;
        window.chart.data.datasets[1].animationDuration = 0;
        window.chart.data.datasets[1].data = tripLocations;
        window.chart.data.datasets[0].rotation = vehicleRotations;
        window.chart.data.datasets[0].pointStyle = vehicleStyles;
        window.chart.data.datasets[0].pointRadius = vehicleRadii;
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
      window.chart.data.datasets[0].pointRadius = vehicleRadii;

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
