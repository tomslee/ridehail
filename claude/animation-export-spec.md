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

## Loose ends / possible next steps

- fps is fixed at 10 (= 5 blocks/s with the default `interpolate = 1`); could
  become a config item if pacing needs tuning per document.
- Resolution is the figure size at 100 dpi (800x800 for a map); a `dpi`
  option would allow sharper renders.
- matplotlib stats charts are not on the shared palette.
- Phase 2 candidate: option 3 (trajectory JSON + JS player).
