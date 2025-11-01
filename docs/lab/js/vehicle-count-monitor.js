/**
 * Vehicle Count Monitor
 *
 * Monitors vehicle count changes during equilibration and displays
 * toast notifications when the fleet size changes.
 */

import { showInfo } from "./toast.js";
import { appState } from "./app-state.js";

// Debouncing state for notification display
let lastNotificationTime = 0;
let queuedNotificationTimeout = null;
const NOTIFICATION_COOLDOWN = 2000; // 2 seconds minimum between notifications
const NOTIFICATION_DURATION = 4000; // 4 seconds display time

/**
 * Check if vehicle count has changed and show notification if appropriate
 * @param {Map} results - Simulation results from worker
 */
export function checkVehicleCountChange(results) {
  // Only monitor when equilibrate is enabled
  const equilibrate = results.get("equilibrate");
  if (!equilibrate) {
    return;
  }

  const currentCount = results.get("vehicle_count");
  if (currentCount === undefined) {
    return;
  }

  // Initialize on first run
  if (!appState.hasPreviousVehicleCount()) {
    appState.previousVehicleCount = currentCount;
    return;
  }

  const previousCount = appState.previousVehicleCount;

  // Check for change
  if (currentCount !== previousCount) {
    showVehicleCountNotification(currentCount, previousCount);
    appState.previousVehicleCount = currentCount;
  }
}

/**
 * Show toast notification for vehicle count change with debouncing
 * @param {number} currentCount - New vehicle count
 * @param {number} previousCount - Previous vehicle count
 */
function showVehicleCountNotification(currentCount, previousCount) {
  const now = Date.now();

  // Check cooldown period
  if (now - lastNotificationTime < NOTIFICATION_COOLDOWN) {
    // Queue a delayed notification instead of showing immediately
    clearTimeout(queuedNotificationTimeout);
    queuedNotificationTimeout = setTimeout(() => {
      showVehicleCountNotificationImmediate(currentCount);
    }, NOTIFICATION_COOLDOWN - (now - lastNotificationTime));
    return;
  }

  showVehicleCountNotificationImmediate(currentCount);
}

/**
 * Show the notification immediately (internal function)
 * @param {number} currentCount - Current vehicle count
 */
function showVehicleCountNotificationImmediate(currentCount) {
  const message = `Fleet size: ${currentCount} vehicle${currentCount !== 1 ? "s" : ""} operating`;
  showInfo(message, NOTIFICATION_DURATION);
  lastNotificationTime = Date.now();
}

/**
 * Reset vehicle count tracking (call on simulation reset)
 * Clears the previous count so next frame won't trigger a change notification
 */
export function resetVehicleCountTracking() {
  appState.previousVehicleCount = null;
  // Also clear any queued notifications
  if (queuedNotificationTimeout) {
    clearTimeout(queuedNotificationTimeout);
    queuedNotificationTimeout = null;
  }
  // Reset cooldown timer so next notification isn't delayed
  lastNotificationTime = 0;
}
