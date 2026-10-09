# Web Lab Dark Mode - Specification

Status: complete - implemented, browser-tested and accepted by Tom, 2026-10-09.
Scope: the browser lab, `docs/lab/` only. The terminal animations are out of
scope, except that the shared phase palette (`ridehail/animation/palette.py`)
stays in step with the web light theme (a test checks).

## 1. Goals

- Light, dark, and "follow the system" themes, switchable at any time,
  including while a simulation runs, without a reset or reload.
- One place to define each colour. Components refer to colours by *role*
  ("surface", "text", "border"), never by value.
- Domain colours (the P1/P2/P3 phases and the waiting rider) keep their meaning
  in both themes. Where the light theme encodes meaning in *lightness*, the dark
  theme re-derives it rather than copying it.
- No flash of the wrong theme on page load.

Non-goals: a high-contrast theme, user-customisable colours, theming the
matplotlib or terminal front-ends.

## 2. Decisions (Tom, 2026-10-09)

1. Parchment text columns: **lamp-lit** in dark (warm dark surface, cream ink).
2. What If? raised/lowered highlights: **keep amber / blue** with darker tints
   in dark. (They are amber/blue, from the WAITING/IDLE colours - not teal, as
   the first draft said.)
3. Read-tab screenshots: **leave** (that page will change anyway).
4. Dark map: occupied (P3) cars **brighten** with city size instead of
   deepening.
5. A chosen theme is **stored** for future visits. First-time visitors at
   first followed the OS; Tom then made **Light the default** (clearer and
   more mature than the dark theme many would get from System), so System is
   now an explicit choice.
6. Older Safari (before 17.5, no `light-dark()`) does not matter.

## 3. Techniques

### 3.1 `color-scheme` + `light-dark()`

Each themed CSS token is declared once, with both values:

```css
:root                     { color-scheme: light dark; }  /* follow the OS */
:root[data-theme="light"] { color-scheme: light; }       /* stored choice */
:root[data-theme="dark"]  { color-scheme: dark; }
:root { --md-surface: light-dark(#ffffff, #1b2129); }
```

`color-scheme` also themes native form controls, scrollbars and `<select>`
popups. No duplicated `@media (prefers-color-scheme)` blocks.

### 3.2 Token block, with Material 3 role names

All CSS colour values live in one block at the top of `style.css`, between
the `/* @theme-tokens-begin */` and `/* @theme-tokens-end */` markers.
Everything else uses tokens or `color-mix()` of them. Role names follow the
MD3 colour roles (`--md-surface`, `--md-on-surface`, `--md-outline-variant`,
`--md-secondary-container`, `--md-inverse-surface`, `--md-scrim`, ...);
lab-specific roles use `--lab-*` (`--lab-accent`, `--lab-page-top`,
`--lab-manuscript-*`, `--lab-track`, `--lab-p1`..`--lab-wait`, `--lab-you`,
`--lab-whatif-up/down`, ...). The block's comments describe each group.

Mapping notes from the conversion:

- Primary (steel blue `#7facca`, buttons and sliders) is the same in both
  themes. Secondary (teal, the header bar) deepens in dark.
- `--lab-accent` (teal) replaces the many `rgba(0, 150, 136, a)` focus/hover
  rings and tints, lightened in dark so rings stay visible.
- White-on-header overlays are `color-mix()` of `--md-on-secondary`;
  black shadows are `color-mix()` of `--md-shadow`; zebra stripes, dividers
  and disabled fills are `color-mix()` of `--md-on-surface` (so they flip in
  dark).
- Toasts use the MD3 inverse surface (dark toast by day, light by night);
  state-coloured toasts keep white text.
- A "text version" of a hue (the game log's up/down figures) is
  `color-mix(hue 75%, var(--md-on-surface))`: darker by day, lighter by night.
- Removed value-named and legacy tokens (`--surface-white`, `--text-white`,
  `--surface-dark`, `--md3-*`, `--game-p1..`, unused `--state-*` etc.).

### 3.3 Canvas colours: `THEME_COLORS` + `themeColor()`

Canvas code (map, Chart.js, sparklines, game overlay) can't use CSS tokens,
and reading them with `getComputedStyle` would return the unresolved text
`"light-dark(...)"`. So canvas colours live in `THEME_COLORS = {light, dark}`
in `js/constants.js` (still DOM-free; the worker imports that file), read
through `themeColor(name)` in `js/theme.js`.

- **Chart.js:** dataset colours and datalabel colours are *scriptable
  options* (`backgroundColor: () => themeColor("IDLE")`), so a plain
  `chart.update()` re-resolves them. `Chart.defaults.color` and
  `Chart.defaults.borderColor` (tick text, grid lines) are set from
  `CHART_TEXT` / `CHART_GRID`. On a theme change `theme.js` updates the
  defaults and calls `update("none")` on every `Chart.instances` entry.
- **Map:** land, core and roads are read at draw time. Vehicle and trip
  colours and icons are baked into each frame's datasets, so on `themechange`
  `map.js` clears its icon caches and redraws the last frame (as
  `toggleHeatmapView` does), without adding a duplicate sparkline point.
- **CSS legends** that show domain colours use `--lab-p1` etc.;
  `test/test_web_lab_theme_tokens.py` checks those tokens agree with
  `THEME_COLORS` in both themes, and that the light values agree with
  `palette.py`.

### 3.4 Theme state (`js/theme.js`)

- Stored choice `"system" | "light" | "dark"` in `localStorage` key
  `ridehail.theme` (absent, or storage unavailable = light), separate from
  session settings.
- Light or dark is `data-theme` on `<html>`; "system" removes it, so
  `color-scheme: light dark` defers to the OS.
- A blocking inline script at the top of `<head>` applies the stored choice
  before the stylesheet paints (no flash). A test checks its key matches.
- `<meta name="color-scheme">`, and two `theme-color` metas (one per OS
  scheme) that `theme.js` points at the chosen theme's header colour.
- System viewers follow an OS switch live (`matchMedia` change listener).
- Every change of the *resolved* theme dispatches `themechange` on
  `document` (`detail.theme`). Listeners: `map.js` (redraw), `game-tab.js`
  (fleet chart redraw).
- During a switch the `theme-switching` class suppresses CSS transitions for
  two frames so the page changes at once.

### 3.5 Considered and not adopted

- Swapping whole stylesheets; `filter: invert()`; Tailwind `dark:` variants.
- `@property` registration of tokens so `getComputedStyle` resolves them:
  heavier, and the JS tables are simpler for the hot map render loop.
- `chartjs-plugin-colorschemes` (commented out in `index.html`): unmaintained
  for Chart.js 4.

## 4. "Theme-ready" rule and lint

- CSS colour values only inside the token block; JS colour values only in
  `THEME_COLORS`.
- "Colour values" includes all 148 CSS named colours (the first version of
  the lint knew only a few, and missed `lightgrey`).
- Exceptions carry a `theme-exempt` comment on the line. Current exemptions:
  the house icon's door and window (`modules/map.js`), which are drawn the
  same in both themes. (The car's windshield was exempt at first, but black
  vanished on the dark map: it is now `WINDSHIELD`, near-white in dark.)
- `test/test_web_lab_theme_tokens.py` enforces both rules, that both themes
  define the same names, the CSS/JS/palette agreement, and the storage key.

## 5. Theme-selection UI

- A header menu (`#app-theme-menu`), left of the hamburger menu and built the
  same way (a `<details>` popover, `initDetailsPopover` in `js/nav-menu.js`),
  inside a `.app-header-actions` wrapper that takes over the hamburger's old
  tablet/phone ordering rules.
- The button's icon shows the theme on screen (sun `light_mode` / moon
  `dark_mode`). The menu lists **System** (`computer` icon), **Light** and
  **Dark** as `menuitemradio` items, with a tick on the stored choice.
- The first version was a single button cycling System -> Light -> Dark; Tom
  found the System icon (`brightness_auto`, a sun with an "A") unreadable and
  the unlabelled cycle confusing, so it became this labelled menu.
- The header stays visible on phones, so the same menu serves the phone tier.
- No keyboard shortcut.

## 6. Dark-theme colour choices (starting points, tune by eye)

| | Light | Dark |
|---|---|---|
| Page | cream `#faf7f0 -> #f3ece0` | slate `#171b21 -> #12161c` |
| Surface | `#ffffff` | `#1b2129` |
| Control bar (CONTROLS / BLOCK / PRESETS) | cool grey `#f1f5f9 -> #e2e8f0` | dark grey `#323a46 -> #29303a` (first version was too close to the page) |
| Header | teal `#009688` | deep teal `#00695f` |
| Map land / core / roads | `#e2e8f0` / `#b0cadd` / `#fcfcfc` | `#1e2530` / `#2c3e52` / `#3a4452` |
| Phase fills (charts, map) | 0.5 alpha | lifted hues, 0.7 alpha |
| P3 by city size (map) | `(60,179,113,.5)` -> `(46,139,87,.9)` | `(79,196,136,.7)` -> `(125,228,168,.95)` |
| Icon outlines / wheels | `#333333` (car outline grey) | `#cfd5dd` |
| Car windshield (front marker) | black | near-white `#f3f4f6` |
| Parchment columns | `#fefdfa -> #fbf8f1`, ink `#3c2e1e` | lamp-lit `#231e18 -> #1c1814`, ink `#e8dcc4` |
| Game ring ("you") | `#7c3aed`, white label text | `#a78bfa`, dark label text |
| Game marker halo | white | dark slate |
| Game offer dim layer | 14% near-black | 40% black |
| On/off switch track / thumb | `#e5e7eb` / white | `#5b6573` / `#e5e7eb` (was dark-on-dark, hard to see) |

## 7. Visible changes in the light theme

The conversion is meant to leave the light theme as it was, but merging
near-duplicate values into shared tokens moved a few by a shade:

- Body text default `#222` (was the browser's black where nothing set it).
- `#f5f5f5` -> `#f3f4f6`; `#111827` text -> `#1f2937`; `#666`/`#777` ->
  `#6b7280`; `#424242` -> `#374151`; `#cbd5e1` -> `#d1d5db`; `#f8fafc` ->
  `#f9fafb`; `#757575` -> `#6b7280`; the control panel's bottom rule
  `#94a3b8` -> `#6b7280` (at 0.5 opacity).
- Legacy MD3 slider rules (mostly overridden) used purple `#6750a4`; now
  steel blue. The game timeout banner is 80% black, not 85% slate.
- Game debrief time-split bars are opaque, not 0.9 alpha.
- The Experiment map's drop shadow is gone (Tom: "too fussy"); the Game map
  gains the same thin light outline (`--lab-chart-outline`, `#d3d3d3` in
  both themes) that the Experiment map and charts have.
- **Bug fix:** `.drop-zone` was missing a semicolon after its `border`, which
  silently dropped both its dashed border and its rounded corners; both now
  apply.

## 8. Testing (Tom, in the browser)

Toggle the header button through all three states on each tab, while
stopped, paused and running:

- Experiment: map (icons, heatmap mode "h", followed car "i", downtown core
  with inhomogeneity > 0, metrics overlay compact/expanded), Statistics charts,
  parchment column, sliders/steppers/chips/toggles, toasts, upload dialog.
- What If?: charts, raised/lowered highlights on steppers and the settings
  table.
- Game: setup cards, offer card and map overlay, status bar, fleet chart,
  debrief, leaderboards.
- Phone width: header button, bottom bar and sheet.
- Reload with each stored choice: no flash; "system" follows an OS switch live.
