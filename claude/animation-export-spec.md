# Animation export for web pages (Quarto) - project log

Goal: put ridehail map animations into Quarto documents (HTML output), and
other web pages, efficiently. Started 2026-10-16.

## Options considered

1. **Pre-rendered video** from the matplotlib map (`-a map -aof run.mp4`),
   embedded with Quarto's `{{< video >}}` shortcode. **Done (Phase 1, below).**
2. matplotlib `to_jshtml()` in a Quarto Python cell: self-contained player, but
   every frame is a base64 PNG, so pages grow by MBs. Not pursued.
3. **Recorded trajectory + small JS player**: the simulation writes compact
   per-block JSON (vehicle positions/phases, trip origins/destinations, seeded);
   a canvas/OJS player reuses the web lab's drawing logic (midpoint direction
   changes, edge wrapping, shared palette) via a Quarto shortcode such as
   `{{< ridehail-map run.json >}}`. Tiny files, crisp, scrubbable, matches the
   lab exactly. Most work: needs a recorder and a Pyodide-free port of the
   drawing half of `docs/lab/modules/map.js`. Candidate Phase 2.
4. iframe of the live web lab: ~50 MB Pyodide per embed. Only for a single
   "try it yourself" embed.
5. Terminal look: asciinema recording of `-a terminal_map` + asciinema-player.

## Phase 1: video output (2026-10-16)

Usage:

```bash
python -m ridehail my.config -a map -b 100 -aof run.mp4    # or .webm / .gif
```

```markdown
{{< video run.mp4 >}}
<!-- or GIF-like: -->
<video src="run.mp4" autoplay loop muted playsinline width="500"></video>
```

What changed:

- `ridehail/animation/utils.py`: `make_output_writer()` picks the writer by
  extension (`OUTPUT_FILE_TYPES`), shared by the map/stats animation and the
  sequence animation. `.mp4` = H.264 yuv420p + `faststart`; `.webm` = VP9
  constant quality (crf 33); `.gif` = Pillow (no ImageMagick). ffmpeg writers
  pipe frames (`FFMpegWriter`) instead of writing a PNG per frame
  (`FFMpegFileWriter`). `OUTPUT_FPS = 10`.
- `ridehail/animation/matplotlib.py`:
  - Saving switches to the Agg backend (no window) and always uses a bounded
    frame count, `_frame_count()` = `(time_blocks + 1) * (interpolate + 1)` for
    the map. Previously, when a window existed, saving rendered 99,999 frames.
  - A no-op `init_func` so matplotlib's initial draw does not call
    `_next_frame` (which would advance the simulation an extra block).
  - Progress is printed every 50 frames.
  - A saved map fills its square frame (no right-hand margin).
  - Map colours come from `palette.py` (P1/P2/P3, waiting-rider pink for trip
    requests, P3 green for destinations), so a video matches the web lab and
    terminal. The matplotlib *stats* charts still use the seaborn palette.
- `ridehail/config.py`: `animation_output_file` validator - extension must be
  `.mp4`/`.webm`/`.gif`, and `time_blocks` must be > 0.

Measured (test.config, 8 blocks, 4 vehicles, 201 blocks = 404 frames,
800x800): mp4 274 KB (34 s), webm 162 KB (30 s), gif 1.3 MB (54 s).

## Phase 1b: Record button in the web lab (2026-10-16)

The matplotlib map is plain next to the web map (vehicle outlines, person and
house markers, eased movement), so the lab can now record its own map.

- `docs/lab/js/map-recorder.js` (`initMapRecorder`, called from `app.js`):
  a button at the top right of the map (`#map-record-button` in
  `components/experiment-tab.html`) starts/stops a `MediaRecorder`; on stop
  the video downloads as `ridehail-map-<title>_<timestamp>.mp4` (or `.webm`
  where the browser can't write MP4). The button shows elapsed time while
  recording and is hidden where `MediaRecorder`/`captureStream` are missing,
  and on the phone tier.
- Frames come from a hidden recording canvas, not the Chart.js canvas: each
  animation frame copies the map's `chartArea` (the land square) onto it,
  filled first with `themeColor("LAND")`. This avoids transparent margins
  (black in video) and keeps recording through a Reset or resize, which
  re-create the chart. HTML overlays (metrics panel, the button) are not
  recorded. Switching Display to Statistics stops and saves.
- Real-time capture at up to 30 fps, side capped at 1080 px (even sizes).
- Colour token `--lab-recording` (style.css token block) for the active state.
- Chrome's WebM has no duration metadata; `ffmpeg -i in.webm -c copy out.webm`
  fixes seeking. MP4 recordings are fragmented MP4, which browsers play.

Browser-tested and accepted by the user 2026-10-16; kept as is for now.

Game map (2026-10-16): the same button on the game's map (`#game-record-button`
in `components/game-tab.html`). `map-recorder.js` now has a `TARGETS` list
(button, map canvas id, file prefix, `isShown`); one recording at a time. A
recording stops and saves when its button leaves the layout (another tab or
game screen, e.g. the debrief at the end of a shift) or `isShown` fails
(Experiment display switched to Statistics). The game's canvas overlay (the
ring round the player's car) is recorded; the HTML offer card is not. Game
videos are named `ridehail-game_<timestamp>`. Awaiting the user's browser test.

## Loose ends / possible next steps

- fps is fixed at 10 (= 5 blocks/s with the default `interpolate = 1`); could
  become a config item if pacing needs tuning per document.
- Resolution is the figure size at 100 dpi (800x800 for a map); a `dpi`
  option would allow sharper renders.
- matplotlib stats charts are not on the shared palette.
- Phase 2 candidate: option 3 (trajectory JSON + JS player).
