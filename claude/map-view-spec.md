# Map views: the grid drawn on a real city

Started 2026-10-28. Display only: the simulation, its coordinates and its
results are untouched. The first (and so far only) view is Toronto.

## Pieces

| Piece | Where |
|---|---|
| Generator (ward geojson -> view file) | `ridehail-toronto/bin/toronto_map_warp.py` |
| View file (web asset, not in the Python package; `build.sh` excludes `maps/` from the wheel's lab copy) | `docs/lab/maps/toronto.json`, fetched by `loadMapViews` in `map-view.js` for each view the toggle's buttons name |
| Toronto preset | `ridehail/presets.py` `CITY_PRESETS` (`--preset toronto-2026`; city presets are named <city>-<calibration>, with title and map view as metadata) |
| Web: city presets to the browser | `docs/lab/worker.py` `get_city_presets` (sent with "Pyodide loaded") |
| Web: projection and drawing | `docs/lab/modules/map-view.js` |
| Web: hooks in the map | `docs/lab/modules/map.js` (`_proj`, `_displayPoint`, `_chartPoints`, `redrawMapWithView`) |
| Web: followed car's route | `docs/lab/modules/game-map-overlay.js` (`setOverlayProjection`) |
| Web: controls | "City presets" group in the Saved dropdown (`js/saved-configs.js`); Grid / Toronto toggle on the map, top right beside the record button (`#map-view-toggle` in `.map-corner-controls`); wiring in `app.js` (`setLabMapView`, `syncMapViewControls`, `loadCityPreset`). Not on the phone tier |
| Tests | `test/test_map_views.py` |

Regenerate the view: in `ridehail-toronto`,
`uv run python bin/toronto_map_warp.py --json ../ridehail-simulation/docs/lab/maps/toronto.json`
(see the script's docstring; it refuses to write a view with folded cells).

## The warp

- The torus is cut open at its seams, which become the city boundary
  (north = Steeles, south = lakeshore, west/east = Etobicoke / Rouge).
- The grid is rolled north-south by the core's lower bound
  (`City.core_bounds()`), so the core sits on the lakeshore. The lake is not
  a barrier in the model (accepted limitation): a car crossing the top edge
  reappears at the lakeshore.
- The lattice (half-block resolution, 97x97 at city size 48) spans display
  grid coordinates -0.5 .. 47.5. The outer boundary is pinned to the city
  outline, the core's boundary to wards 10, 11, 13 (5.9% of the city's area
  for 25% of the grid); interior points by a harmonic (Laplace) solve then
  Winslow smoothing. A morphological opening (0.8 km) drops Leslie Spit and
  the Humber Bay points, and pinned arcs are smoothed (0.5 km): no folds.
- Coordinates are km in Toronto's street-grid frame (Steeles horizontal),
  41.5 x 20.8 km, so the map is about 2:1.
- The lattice is used in fractions of the city width, so the view works at
  any city size; the roll follows that size's core.
- Known quirk: ward 10 encloses the inner harbour and the Islands, so the
  core reaches over water.

## The web lab

- `map.js` keeps all its logic (edge-wrap teleports, highlight glides,
  headings, wrap detection) in display grid units; positions become km only
  where they are handed to Chart.js (`_chartPoints`). With no view `_proj` is
  null and every path is the plain grid's.
- A point half a block beyond an edge (an interpolated frame's car crossing
  it) is placed on the edge the car is heading for (`toDisplay` takes its
  direction), so the existing teleport logic wraps it as on the plain grid.
- Car headings follow the warped road (`headingAt`).
- Roads, wards, the area beyond the city (`MAP_OUTSIDE`) and the core are
  drawn by `createMapViewPlugin` into an offscreen canvas, redrawn only when
  size, theme, core or road width change. Heatmap cells are filled as warped
  outlines (`fillViewCells`).
- Controls (2026-10-28, revised to keep the control bar as it was): the
  Village/Town/City chips stay the only preset chips; real-city presets are
  an expandable "City presets" group in the Saved dropdown (loaded, never
  selected or deleted: the dropdown stays a pure picker). The map view is a
  Grid | Toronto toggle on the map itself, shown once the views have
  arrived: a display setting, live during a run, remembered per viewer in
  localStorage `labMapView`. A city preset with a map view switches to it;
  nothing switches it off but the toggle (Town on the Toronto map is fine).
- The Toronto preset borrows the City scale's slider ranges, overlays its
  values on a fresh `SimSettings` and loads through `setInitialValues(true,
  true)`; the Village/Town/City path is unchanged. It carries
  `minTripDistance` (no control shows it; the worker already accepts it), now
  saved and restored with the session.

Adding a city: its view file in `docs/lab/maps/`, a button in the map's
toggle (`#map-view-toggle`, `data-map-view="<name>"`), and its presets in
`CITY_PRESETS` with that `map_view`; `test/test_map_views.py` checks the
names agree.

## Recording a video

The map's Record button (`js/map-recorder.js`) records whatever the map
canvas draws, so a map view records as shown. The video keeps the map's
proportions, fitted within 1920 x 1080 (a square map: up to 1080 x 1080, as
before; Toronto: up to about 1920 x 960). If the view changes during a
recording, frames of the other shape are centred with a border. The
Grid | Toronto toggle sits beside the record button (`.map-corner-controls`)
and, like it, is not recorded. The command-line matplotlib export does not
draw map views (the display is web-only, by choice).

## The Toronto preset

`ridehail-toronto/simulation/toronto_2026.config` (all day 2026, Tier 1), in
Simple mode, which gives identical dynamics (the calibration sets no prices).
Reproduces P1/P2/P3 = 0.332/0.142/0.526 and mean wait 4.69 min with the
current simulator (2026-10-28). Without `min_trip_distance = 2`, P3 rises to
0.554. Economics are the shared preset values, as for the City. The preset is
a snapshot: rerunning the calibration does not update it.

## Status and decisions (2026-10-28: done, released and browser-tested)

Released at https://tomslee.net/ridehail (2026.10.28.6); the map, toggle and
City presets group work. Decisions taken along the way, to keep:

- Wrap-around through the lake is accepted: the model stays a simple torus
  for calibration and comparison between cities; geography is decoration.
- The display is web-only: no command-line / matplotlib map view, and no
  view data or display libraries in the Python package (shapely is a
  ridehail-toronto dependency only).
- The control bar stays as it was before Toronto: specialist features go in
  existing controls (a dropdown group, a map-corner overlay), not new
  sections or chips. A ribbon was discussed and judged premature.
- Village/Town/City stay the visible presets for first-time users; city
  presets are the expandable set.

Rejected or left alone: a Toronto preset chip and a "Map view" bar section
(cluttered the bar); separable warps only (items 1-3 of the first proposal,
superseded by the full warp); a five-ward core (wards 9-14: awkward shape,
folds); the phone tier (no route to Toronto); fixing the harbour quirk (needs
a shoreline dataset); cache-busting the worker URL (stale `webworker.js` from
the host's 10-minute cache can hide the City presets for a while after a
deploy; a hard refresh fixes it).

## Ideas for extending

- More calibrations as city presets: Toronto by date or hour
  (`toronto-2026-8am`), Chicago from its open data. Each is an entry in
  `CITY_PRESETS` (copy the values from the calibration config; check it
  reproduces, as for Toronto, and note `min_trip_distance`-style parameters
  the web lab has no control for: carry them as `CITY_PRESET_EXTRA_NAMES` in
  worker.py and in session save/restore).
- A Chicago map view: generalise `toronto_map_warp.py` (input geojson, core
  area names, corner choice, street-grid rotation; Chicago's grid is
  north-south, its core (the Loop) is on the lakeshore to the east, so the
  roll would be east-west), write `docs/lab/maps/chicago.json`, add a toggle
  button. `map-view.js` already handles any roll on y only: an x roll needs
  `rollX` in `MapProjection` (the view file carries `roll: [x, y]`).
- Sizing blocks to real demand (a density-equalising cartogram from FOIA
  pickups by ward) instead of the harmonic warp's even blocks.
