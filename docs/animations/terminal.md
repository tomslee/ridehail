# Terminal Animations

Terminal-based animations using the Textual framework provide rich, real-time visualizations that work over SSH and require no graphical environment.

## Installation

```bash
pip install ridehail[terminal]
```

This installs:

- `textual` - Modern terminal UI framework
- `textual-plotext` - Terminal chart integration
- `plotext` - Terminal plotting library
- `rich` - Terminal formatting

## Terminal Map Mode

Real-time vehicle and trip visualization in your terminal.

### Usage

```bash
python -m ridehail config.config -a terminal_map
```

### Display Elements

**Map Grid:**

- Grid represents city blocks
- Intersections are vehicle/trip locations
- Roads connect intersections

**Vehicles (◆):**

- **Blue** - P1 (Idle): Available, driving randomly
- **Orange** - P2 (Dispatched): En route to pickup
- **Green** - P3 (Occupied): Carrying passenger

**Trip Markers:**

- `○` - Trip origin (passenger waiting)
- `●` - Trip destination

**Statistics Panel (right side):**

- Current time block
- Phase fractions (P1/P2/P3 percentages)
- Wait time and ride time averages
- Trip completion rate
- Vehicle count (if equilibration enabled)

### Keyboard Controls

| Key       | Action                     |
| --------- | -------------------------- |
| `Space`   | Pause/resume simulation    |
| `+` / `-` | Adjust animation speed     |
| `v` / `V` | Increase/decrease vehicles |
| `d` / `D` | Increase/decrease demand   |
| `r`       | Reset simulation           |
| `q`       | Quit                       |
| `a`       | Toggle animation mode      |

### Configuration

```ini
[ANIMATION]
animation = terminal_map
animation_delay = 0.1  # Update interval in seconds
results_window = 60    # Statistics smoothing window
```

### Best For

- Development and debugging
- Real-time vehicle tracking
- Understanding dispatch behavior
- Visual confirmation of parameters
- Small to medium city sizes (6-16 blocks)

### Limitations

- Performance degrades with very large cities (>20 blocks)
- Terminal size must accommodate map + statistics panel
- Colors may vary based on terminal color scheme

## Terminal Console Mode

Simple text-based output with progress bars.

### Usage

```bash
python -m ridehail config.config -a console
```

### Display Elements

**Progress Bars:**

- P1 (Idle) - Blue bar showing idle vehicle fraction
- P2 (Dispatched) - Orange bar showing dispatched fraction
- P3 (Occupied) - Green bar showing occupied fraction

**Metrics:**

- Wait time - Average passenger wait (blocks)
- Ride time - Average trip duration (blocks)
- Block counter - Current simulation time
- Trip counter - Completed trips

### Keyboard Controls

| Key       | Action                     |
| --------- | -------------------------- |
| `Space`   | Pause/resume simulation    |
| `+` / `-` | Adjust speed               |
| `v` / `V` | Increase/decrease vehicles |
| `d` / `D` | Increase/decrease demand   |
| `r`       | Reset simulation           |
| `q`       | Quit                       |

### Configuration

```ini
[ANIMATION]
animation = console
animation_delay = 0.1
results_window = 60
```

### Best For

- Quick simulation checks
- Minimal terminal real estate
- Focus on metrics over visualization
- Remote servers with limited terminal capabilities
- Any city size (no map rendering)

## Terminal Stats Mode

Real-time line charts using plotext.

### Usage

```bash
python -m ridehail config.config -a terminal_stats
```

### Display Elements

**Charts:**

- **Phase Fractions Chart**: Lines showing P1/P2/P3 percentages over time
  - Blue line: P1 (Idle)
  - Orange line: P2 (Dispatched)
  - Green line: P3 (Occupied)
- **Trip Metrics Chart**: Wait time and ride time trends

**Statistics Panel:**

- Current block
- Phase fractions
- Average wait/ride times
- Trip rate

### Keyboard Controls

| Key       | Action                     |
| --------- | -------------------------- |
| `Space`   | Pause/resume               |
| `+` / `-` | Adjust speed               |
| `v` / `V` | Increase/decrease vehicles |
| `d` / `D` | Increase/decrease demand   |
| `r`       | Reset (clears charts)      |
| `q`       | Quit                       |

### Configuration

```ini
[ANIMATION]
animation = terminal_stats
animation_delay = 0.1
results_window = 60  # Rolling window for chart display
```

The `results_window` parameter determines how many recent blocks are shown in the charts (default 60).

### Best For

- Observing trends over time
- Identifying equilibration dynamics
- Statistical analysis during simulation
- Medium to large city sizes (no map rendering overhead)
- Parameter adjustment observation

## Terminal Sequence Mode

Visualize parameter sweep progress with scatter plots.

### Usage

```bash
python -m ridehail sequence_config.config -a terminal_sequence
```

### Display Elements

**Scatter Plots:**

- **Phase Fractions vs. Parameter**: Shows P1/P2/P3 percentages for each parameter value
- **Trip Metrics vs. Parameter**: Shows wait/ride times vs. parameter

**Progress Indicator:**

- Current simulation in sequence
- Parameter value being tested
- Completion status

### Keyboard Controls

| Key     | Action                            |
| ------- | --------------------------------- |
| `Space` | Pause/resume sequence progression |
| `r`     | Restart sequence from beginning   |
| `q`     | Quit                              |

### Configuration

```ini
[DEFAULT]
city_size = 10
base_demand = 3.0
time_blocks = 400
animation = terminal_sequence

[SEQUENCE]
sequence_variable = vehicle_count
sequence_start = 20
sequence_end = 120
sequence_step = 10
```

### Best For

- Parameter optimization
- Sensitivity analysis
- Finding optimal configurations
- Understanding parameter relationships
- Visual progress monitoring for long sequences

## Terminal Requirements

### Minimum Terminal Size

- **console**: 80×24 (standard)
- **terminal_map**: 120×40 (depends on city size)
- **terminal_stats**: 120×30
- **terminal_sequence**: 120×30

### Recommended Terminals

**Linux:**

- GNOME Terminal
- Konsole
- Alacritty
- kitty

**macOS:**

- iTerm2
- Terminal.app
- Alacritty

**Windows:**

- Windows Terminal (recommended)
- ConEmu
- Alacritty

### Color Support

All modes require 256-color or true-color terminal support. Most modern terminals support this by default.

Verify with:

```bash
echo $TERM
# Should show: xterm-256color or similar
```

### SSH Usage

Terminal animations work perfectly over SSH:

```bash
ssh user@server
python -m ridehail config.config -a terminal_stats
```

No X11 forwarding or graphical environment needed.

## Troubleshooting

### Terminal Too Small

Error: "Terminal size insufficient for map display"

**Solution**: Resize terminal window or reduce `city_size` in config.

### Missing Dependencies

Warning: "Textual dependencies not found"

**Solution**:

```bash
pip install ridehail[terminal]
```

### Animation Flickering

Issue: Screen flickers during updates

**Solution**: Increase `animation_delay`:

```bash
python -m ridehail config.config -a terminal_map -ad 0.2
```

### Colors Not Showing

Issue: No colors, or wrong colors

**Solution**:

1. Check terminal supports 256 colors
2. Try different terminal emulator
3. Check `$TERM` environment variable

### Performance Issues

Issue: Animation stutters or lags

**Solution**:

- Reduce `city_size`
- Increase `animation_delay`
- Switch to `console` or `terminal_stats`
- Use `animation = none` for large simulations

## Next Steps

- **[Desktop Animations](desktop.md)** - Matplotlib visualization guide
- **[Animation Overview](overview.md)** - Compare all animation modes
- **[Quick Start](../quickstart.md)** - Get started quickly
