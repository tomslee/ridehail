/**
 * Educational loading tips for the Ridehail Laboratory
 *
 * Tips are categorized by length:
 * - Desktop: Longer, more detailed tips
 * - Mobile: Shorter, concise tips
 */

export const LOADING_TIPS = {
  desktop: [
    "Initializing Python environment in your browser using Pyodide...",
    "Loading simulation engine... Each block represents one minute of travel time",
    "Did you know? Vehicles in P1 (blue) are idle and waiting for assignment",
    "Did you know? Vehicles in P2 (orange) are en route to pick up passengers",
    "Did you know? Vehicles in P3 (green) are busy carrying passengers",
    "Tip: Press 'z' on your keyboard to zoom the map once loaded",
    "Tip: Press 'p' to pause and resume the simulation at any time",
    "Tip: Press 's' when paused to step forward one frame at a time",
    "The simulation runs entirely in your browser - no data is sent to any server",
    "You can experiment freely - the simulation resets when you refresh the page",
    "Try different city scales: Village (small), Town (medium), or City (large)",
    "Switch between Map view and Statistics view to see different aspects of the system",
    "Enable 'Free entry & exit' to simulate driver economics and market equilibrium",
    "The 'What If?' tab lets you compare different policy scenarios side-by-side",
    "Each simulation block represents both distance traveled and time elapsed",
    "Wait times, driver income, and utilization all interact in complex ways",
  ],
  mobile: [
    "Initializing Python environment...",
    "Loading simulation engine...",
    "Each block = one minute of travel",
    "P1 (blue) = idle vehicles",
    "P2 (orange) = en route to pickup",
    "P3 (green) = carrying passengers",
    "Runs entirely in your browser",
    "Experiment freely - nothing is saved",
    "Try different city scales",
    "Switch between Map and Stats",
    "Free entry/exit simulates driver economics",
  ],
};

/**
 * Get a random loading tip based on screen size
 * @returns {string} A random loading tip
 */
export function getRandomTip() {
  const isMobile = window.innerWidth <= 840;
  const tips = isMobile ? LOADING_TIPS.mobile : LOADING_TIPS.desktop;
  const randomIndex = Math.floor(Math.random() * tips.length);
  return tips[randomIndex];
}

/**
 * Rotate through loading tips with animation
 * @param {HTMLElement} tipElement - The element to update with tips
 * @param {number} interval - Milliseconds between tip rotations
 * @returns {number} Interval ID for clearing
 */
export function rotateTips(tipElement, interval = 2000) {
  if (!tipElement) return null;

  // Set initial tip
  tipElement.textContent = getRandomTip();

  // Rotate tips
  return setInterval(() => {
    // Fade out
    tipElement.style.opacity = "0";

    // Change text and fade in after brief delay
    setTimeout(() => {
      tipElement.textContent = getRandomTip();
      tipElement.style.opacity = "1";
    }, 300);
  }, interval);
}
