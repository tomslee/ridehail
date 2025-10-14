/**
 * Toast Notification System
 * Provides temporary visual feedback messages
 */

/**
 * Show a toast notification
 * @param {string} message - The message to display
 * @param {string} type - Toast type: 'info', 'success', 'warning', 'error'
 * @param {number} duration - Duration in milliseconds (default 3000)
 */
export function showToast(message, type = "info", duration = 3000) {
  // Create toast element
  const toast = document.createElement("div");
  toast.className = `app-toast app-toast--${type}`;
  toast.textContent = message;

  // Add to container (create if doesn't exist)
  let container = document.getElementById("toast-container");
  if (!container) {
    container = document.createElement("div");
    container.id = "toast-container";
    container.className = "app-toast-container";
    document.body.appendChild(container);
  }

  container.appendChild(toast);

  // Trigger animation
  setTimeout(() => {
    toast.classList.add("app-toast--visible");
  }, 10);

  // Auto-dismiss
  setTimeout(() => {
    toast.classList.remove("app-toast--visible");
    setTimeout(() => {
      container.removeChild(toast);
      // Remove container if empty
      if (container.children.length === 0) {
        document.body.removeChild(container);
      }
    }, 300); // Match CSS transition duration
  }, duration);
}

/**
 * Show success toast (green)
 */
export function showSuccess(message, duration = 3000) {
  showToast(message, "success", duration);
}

/**
 * Show error toast (red)
 */
export function showError(message, duration = 4000) {
  showToast(message, "error", duration);
}

/**
 * Show warning toast (yellow)
 */
export function showWarning(message, duration = 3500) {
  showToast(message, "warning", duration);
}

/**
 * Show info toast (blue)
 */
export function showInfo(message, duration = 3000) {
  showToast(message, "info", duration);
}
