/**
 * <details>/<summary> Popover Helper
 *
 * <details> has no native "close on outside click" or "close on Escape"
 * behavior, so this module adds it. Used by the header's "Home/About/.../
 * GitHub/License" links menu (collapsed so they don't compete with the
 * simulation title for header width) and by other click-to-reveal popovers
 * (e.g. the saved-configurations info tooltip).
 */

export function initDetailsPopover(detailsId) {
  const menu = document.getElementById(detailsId);
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

export function initNavMenu() {
  initDetailsPopover("app-nav-menu");
}
