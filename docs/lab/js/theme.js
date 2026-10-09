/* global Chart */
/**
 * Light / dark theme (claude/dark-mode-spec.md).
 *
 * The viewer chooses "system" (follow the OS), "light" or "dark"; the choice
 * is stored in localStorage, apart from the session settings, so resetting a
 * configuration never resets it. A light or dark choice is applied as
 * <html data-theme="...">, which sets CSS color-scheme and so picks a side of
 * every light-dark() token in style.css. "system" removes the attribute.
 * The inline script in index.html's <head> applies the stored choice before
 * first paint; this module takes over from there.
 *
 * Canvas code can't use the CSS tokens, so it calls themeColor(), which reads
 * THEME_COLORS (js/constants.js) for the resolved theme. On every change of
 * the resolved theme this module updates the Chart.js defaults, redraws every
 * chart, and dispatches a "themechange" event on document (detail:
 * {theme: "light" | "dark"}) for code that caches colours.
 */
import { THEME_COLORS } from "./constants.js";
import { initDetailsPopover } from "./nav-menu.js";

// Keep in step with the inline script in index.html's <head>
const THEME_STORAGE_KEY = "ridehail.theme";
const CHOICES = ["system", "light", "dark"];
// The header button shows the theme on screen: a sun or a moon
const ICONS = { light: "light_mode", dark: "dark_mode" };
const darkQuery = window.matchMedia("(prefers-color-scheme: dark)");

let resolved = computeResolvedTheme();

function computeResolvedTheme() {
  const attr = document.documentElement.dataset.theme;
  if (attr === "light" || attr === "dark") return attr;
  return darkQuery.matches ? "dark" : "light";
}

/** The theme in effect: "light" or "dark". */
export function resolvedTheme() {
  return resolved;
}

/** A canvas colour from THEME_COLORS for the theme in effect. */
export function themeColor(name) {
  return THEME_COLORS[resolved][name];
}

/** The stored choice: "system", "light" or "dark". */
export function getThemeChoice() {
  try {
    const stored = localStorage.getItem(THEME_STORAGE_KEY);
    if (CHOICES.includes(stored)) return stored;
  } catch (e) {
    // Storage unavailable (private window, blocked site data): use the OS
  }
  return "system";
}

/** Store and apply a choice of "system", "light" or "dark". */
export function setThemeChoice(choice) {
  if (!CHOICES.includes(choice)) return;
  try {
    if (choice === "system") {
      localStorage.removeItem(THEME_STORAGE_KEY);
    } else {
      localStorage.setItem(THEME_STORAGE_KEY, choice);
    }
  } catch (e) {
    // Not stored; still applied for this page
  }
  const root = document.documentElement;
  // Suppress the page's colour transitions so it changes all at once
  root.classList.add("theme-switching");
  if (choice === "system") {
    delete root.dataset.theme;
  } else {
    root.dataset.theme = choice;
  }
  requestAnimationFrame(() =>
    requestAnimationFrame(() => root.classList.remove("theme-switching")),
  );
  updateBrowserThemeColor(choice);
  refreshResolvedTheme();
  updateThemeMenu();
}

// The header theme menu (#app-theme-menu): the button's icon shows the theme
// on screen, and the System / Light / Dark items tick the stored choice.
function updateThemeMenu() {
  const choice = getThemeChoice();
  const menu = document.getElementById("app-theme-menu");
  if (!menu) return;
  const icon = menu.querySelector("summary .material-icons");
  if (icon) icon.textContent = ICONS[resolved];
  menu.querySelectorAll("[data-theme-choice]").forEach((item) => {
    item.setAttribute(
      "aria-checked",
      String(item.dataset.themeChoice === choice),
    );
  });
}

// The phone browser's toolbar colour (<meta name="theme-color">): the two
// tags follow the OS through their media queries, so a light or dark choice
// sets both to that theme's colour, and "system" restores them.
function updateBrowserThemeColor(choice) {
  document.querySelectorAll('meta[name="theme-color"]').forEach((meta) => {
    const ownTheme = meta.media.includes("dark") ? "dark" : "light";
    meta.content = meta.dataset[choice === "system" ? ownTheme : choice];
  });
}

function applyChartDefaults() {
  if (typeof Chart === "undefined") return;
  Chart.defaults.color = themeColor("CHART_TEXT");
  Chart.defaults.borderColor = themeColor("CHART_GRID");
}

function refreshResolvedTheme() {
  const next = computeResolvedTheme();
  if (next === resolved) return;
  resolved = next;
  applyChartDefaults();
  document.dispatchEvent(
    new CustomEvent("themechange", { detail: { theme: resolved } }),
  );
  // Chart colours are scriptable options that call themeColor(), so an
  // update re-resolves them. Listeners above clear their caches first.
  if (typeof Chart !== "undefined") {
    Object.values(Chart.instances).forEach((chart) => chart.update("none"));
  }
}

/** Wire up the header theme menu and follow OS changes. Call once at start-up. */
export function initTheme() {
  applyChartDefaults();
  updateBrowserThemeColor(getThemeChoice());
  updateThemeMenu();
  initDetailsPopover("app-theme-menu");
  const menu = document.getElementById("app-theme-menu");
  menu?.querySelectorAll("[data-theme-choice]").forEach((item) => {
    item.addEventListener("click", (event) => {
      setThemeChoice(item.dataset.themeChoice);
      menu.open = false;
      // Return keyboard focus to the button (detail is 0 for a click made
      // with Enter or Space), without leaving a focus ring after a mouse click
      if (event.detail === 0) menu.querySelector("summary")?.focus();
    });
  });
  // A "system" viewer follows an OS switch live
  darkQuery.addEventListener("change", () => {
    refreshResolvedTheme();
    updateThemeMenu();
  });
}
