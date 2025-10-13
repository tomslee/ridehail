/**
 * Full-Screen Module - Canvas/Chart Full-Screen Display
 *
 * Provides full-screen overlay mode for charts and maps with:
 * - Double-click to enter full-screen
 * - Keyboard shortcuts (f, Esc, z)
 * - Mobile touch gestures (double-tap, swipe-down)
 * - Auto-hide controls
 */

import { showSuccess } from "./toast.js";

export class FullScreenManager {
  constructor() {
    this.overlay = document.getElementById("fullscreen-overlay");
    this.wrapper = document.getElementById("fullscreen-canvas-wrapper");
    this.controls = document.getElementById("fullscreen-controls");
    this.closeButton = document.getElementById("fullscreen-close-button");

    this.currentCanvas = null;
    this.currentElement = null; // Can be canvas or container element
    this.originalParent = null;
    this.isActive = false;
    this.controlsTimeout = null;

    this.setupEventListeners();
  }

  /**
   * Set up event listeners for full-screen controls
   */
  setupEventListeners() {
    // Close button
    if (this.closeButton) {
      this.closeButton.addEventListener("click", () => this.exit());
    }

    // Click outside canvas to exit
    if (this.overlay) {
      this.overlay.addEventListener("click", (e) => {
        if (e.target === this.overlay || e.target === this.wrapper) {
          this.exit();
        }
      });
    }

    // Mouse movement - show controls temporarily
    if (this.overlay) {
      this.overlay.addEventListener("mousemove", () => {
        this.showControls();
        this.scheduleControlsHide();
      });
    }

    // Prevent canvas clicks from closing
    if (this.wrapper) {
      this.wrapper.addEventListener("click", (e) => {
        e.stopPropagation();
      });
    }
  }

  /**
   * Enter full-screen mode with the specified canvas or element
   * @param {HTMLCanvasElement|HTMLElement} element - The canvas/element to display full-screen
   */
  enter(element) {
    if (!element || this.isActive) return;

    this.currentElement = element;
    this.originalParent = element.parentElement;

    // Track if this is a canvas (for resize logic)
    this.currentCanvas = element.tagName === "CANVAS" ? element : null;

    // Move element to full-screen wrapper
    this.wrapper.appendChild(element);

    // Show overlay with animation
    this.overlay.classList.add("active");
    this.isActive = true;

    // Update canvas/element size to fill available space
    if (this.currentCanvas) {
      this.resizeCanvas();
    } else {
      // For container elements, trigger resize of all child canvases
      this.resizeContainer(element);
    }

    // Schedule controls hide
    this.scheduleControlsHide();

    // Prevent body scrolling
    document.body.style.overflow = "hidden";
  }

  /**
   * Exit full-screen mode
   */
  exit() {
    if (!this.isActive || !this.currentElement || !this.originalParent) return;

    // Return element to original parent
    this.originalParent.appendChild(this.currentElement);

    // Hide overlay
    this.overlay.classList.remove("active");
    this.isActive = false;

    // Clear controls timeout
    if (this.controlsTimeout) {
      clearTimeout(this.controlsTimeout);
      this.controlsTimeout = null;
    }

    // Show controls again
    this.controls.classList.remove("fade-out");

    // Reset canvas/container size
    if (this.currentCanvas) {
      this.resizeCanvas();
    } else if (this.currentElement) {
      this.resizeContainer(this.currentElement);
    }

    this.currentCanvas = null;
    this.currentElement = null;
    this.originalParent = null;

    // Restore body scrolling
    document.body.style.overflow = "";
  }

  /**
   * Toggle full-screen mode
   * @param {HTMLCanvasElement|HTMLElement} element - The canvas/element to toggle
   */
  toggle(element) {
    if (this.isActive) {
      this.exit();
    } else {
      this.enter(element);
    }
  }

  /**
   * Resize container and all child canvases
   * @param {HTMLElement} container - Container element with charts
   */
  resizeContainer(container) {
    if (!container) return;

    // Find all canvases in the container and resize their charts
    const canvases = container.querySelectorAll("canvas");
    canvases.forEach((canvas) => {
      const chart = this.getChartFromCanvas(canvas);
      if (chart && chart.resize) {
        setTimeout(() => {
          chart.resize();
          chart.update("none");
        }, 100);
      }
    });
  }

  /**
   * Resize canvas to optimal size for full-screen
   */
  resizeCanvas() {
    if (!this.currentCanvas) return;

    // Trigger Chart.js resize and update
    const chart = this.getChartFromCanvas(this.currentCanvas);
    if (chart && chart.resize) {
      // Resize and then update to ensure custom pointStyles are preserved
      setTimeout(() => {
        chart.resize();
        chart.update("none"); // Update without animation to preserve styling
      }, 100);
    }
  }

  /**
   * Get Chart.js instance from canvas element
   * @param {HTMLCanvasElement} canvas
   * @returns {Chart|null}
   */
  getChartFromCanvas(canvas) {
    if (!canvas) return null;

    // Chart.js stores instance as canvas.chart or via Chart.getChart()
    if (typeof Chart !== "undefined" && Chart.getChart) {
      return Chart.getChart(canvas);
    }

    return null;
  }

  /**
   * Show controls
   */
  showControls() {
    this.controls.classList.remove("fade-out");
  }

  /**
   * Schedule controls to hide after delay
   */
  scheduleControlsHide() {
    if (this.controlsTimeout) {
      clearTimeout(this.controlsTimeout);
    }

    this.controlsTimeout = setTimeout(() => {
      if (this.isActive) {
        this.controls.classList.add("fade-out");
      }
    }, 2000);
  }

  /**
   * Check if currently in full-screen mode
   * @returns {boolean}
   */
  isFullScreen() {
    return this.isActive;
  }

  /**
   * Get current full-screen canvas
   * @returns {HTMLCanvasElement|null}
   */
  getCurrentCanvas() {
    return this.currentCanvas;
  }
}

/**
 * Add double-click handler to canvas for full-screen
 * @param {HTMLCanvasElement|HTMLElement} element - Canvas or container element
 * @param {FullScreenManager} manager - Full-screen manager instance
 */
export function addDoubleClickHandler(element, manager) {
  if (!element || !manager) return;

  // Remove any existing handler to avoid duplicates
  if (element._fullscreenDblClickHandler) {
    element.removeEventListener("dblclick", element._fullscreenDblClickHandler);
  }

  // Create and store the handler
  const handler = (e) => {
    e.preventDefault();
    manager.toggle(element);
  };
  element._fullscreenDblClickHandler = handler;

  // Add the handler
  element.addEventListener("dblclick", handler);

  // Add cursor style hint
  element.style.cursor = "pointer";
}

/**
 * Add mobile touch gesture handlers
 * @param {HTMLCanvasElement|HTMLElement} element - Canvas or container element
 * @param {FullScreenManager} manager - Full-screen manager instance
 */
export function addMobileTouchHandlers(element, manager) {
  if (!element || !manager) return;

  // Remove any existing handler to avoid duplicates
  if (element._fullscreenTouchHandler) {
    element.removeEventListener("touchend", element._fullscreenTouchHandler);
  }

  let lastTap = 0;

  // Create and store the handler
  const touchHandler = (e) => {
    const currentTime = new Date().getTime();
    const tapInterval = currentTime - lastTap;

    if (tapInterval < 300 && tapInterval > 0) {
      // Double-tap detected
      e.preventDefault();
      manager.toggle(element);
      lastTap = 0;
    } else {
      lastTap = currentTime;
    }
  };
  element._fullscreenTouchHandler = touchHandler;

  // Double-tap detection
  element.addEventListener("touchend", touchHandler);

  // Swipe-down gesture when in full-screen (on overlay, not element)
  // This is set up once on the overlay itself, not per-element
  if (manager.overlay && !manager.overlay._fullscreenSwipeHandlersAdded) {
    let touchStartY = 0;

    manager.overlay.addEventListener(
      "touchstart",
      (e) => {
        touchStartY = e.touches[0].clientY;
      },
      { passive: true },
    );

    manager.overlay.addEventListener(
      "touchmove",
      (e) => {
        if (!manager.isActive) return;

        const touchY = e.touches[0].clientY;
        const deltaY = touchY - touchStartY;

        // Swipe down by at least 100px from top third of screen
        if (touchStartY < window.innerHeight / 3 && deltaY > 100) {
          manager.exit();
        }
      },
      { passive: true },
    );

    manager.overlay._fullscreenSwipeHandlersAdded = true;
  }
}

/**
 * Add full-screen hint indicator to element
 * @param {HTMLElement} element - Element to add hint to
 */
export function addFullScreenHint(element) {
  if (!element) return;

  // Remove any existing hint to avoid duplicates
  const existingHint = element.querySelector(".fullscreen-hint");
  if (existingHint) {
    existingHint.remove();
  }

  const hint = document.createElement("div");
  hint.className = "fullscreen-hint";
  hint.textContent = "Double-click for full-screen";
  element.style.position = "relative";
  element.appendChild(hint);
}
