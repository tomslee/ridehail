/**
 * External Links Menu
 *
 * The header's "Home/About/Essays/.../GitHub/License" links are collapsed
 * into a single <details>/<summary> dropdown so they don't compete with the
 * simulation title for header width. <details> has no native "close on
 * outside click" behavior, so this module adds it.
 */

export function initNavMenu() {
  const menu = document.getElementById("app-nav-menu");
  if (!menu) return;

  document.addEventListener("click", (event) => {
    if (menu.open && !menu.contains(event.target)) {
      menu.open = false;
    }
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && menu.open) {
      menu.open = false;
      menu.querySelector("summary")?.focus();
    }
  });

  menu.querySelectorAll("a").forEach((link) => {
    link.addEventListener("click", () => {
      menu.open = false;
    });
  });
}
