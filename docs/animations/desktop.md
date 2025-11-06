# Desktop Animations

Desktop visualizations using matplotlib provide high-quality, publication-ready figures and detailed analysis capabilities.

## Installation

```bash
pip install ridehail[desktop]
```

This installs:

- `matplotlib` - Plotting library
- `seaborn` - Statistical visualization
- `scipy` - Scientific computing
- `pandas` - Data analysis

## Map Mode

Animated vehicle and trip visualization in a desktop window.

### Usage

```bash
python -m ridehail config.config -a map
```

### Display Elements

**Map Window:**

- City grid with roads and intersections
- Vehicles shown as colored markers:
  - **Blue** - P1 (Idle)
  - **Orange** - P2 (Dispatched)
  - **Green** - P3 (Occupied)
- Trip markers:
  - Light markers: Origins
  - Dark markers: Destinations

**Title Bar:**

- Simulation title (from config)
- Current time block
- Key statistics

### Controls

**Window Controls:**

- Close window to end simulation
- Matplotlib toolbar for zoom, pan, save

**Keyboard:**

- Depends on matplotlib backend
- Limited interactivity compared to terminal modes

### Configuration

```ini
[ANIMATION]
animation = map
animation_delay = 0.1
```

### Saving Figures

Use matplotlib's save button in the toolbar to export:

- PNG (high quality)
- PDF (vector, publication-ready)
- SVG (scalable vector graphics)

### Best For

- Publication-quality figures
- Detailed visual analysis
- Frame-by-frame inspection (using pause/step)
- Exporting visualizations
- Small to medium city sizes (6-20 blocks)

### Limitations

- Slower than terminal animations
- Requires graphical environment (no SSH without X11)
- Higher memory usage
- Less responsive keyboard controls

## Stats Mode

Statistical charts and graphs in desktop windows.

### Usage

```bash
python -m ridehail config.config -a stats
```

### Display Elements

**Multiple Windows/Subplots:**

1. **Phase Fractions Over Time**:
   - Line chart showing P1/P2/P3 percentages
   - Legend with color coding

2. **Trip Metrics**:
   - Wait time trend
   - Ride time trend

3. **Vehicle Utilization**:
   - Distribution histograms
   - Summary statistics

**Updates:**

- Charts update dynamically during simulation
- Rolling window displays recent history
- Statistics calculated over `results_window` blocks

### Configuration

```ini
[ANIMATION]
animation = stats
animation_delay = 0.1
results_window = 60  # History length for charts
```

### Best For

- Statistical analysis during simulation
- Identifying trends and patterns
- Comparing multiple metrics simultaneously
- Exporting charts for reports
- Any city size (no map rendering)

### Saving Charts

Use matplotlib toolbar to save individual charts:

```python
# Or programmatically after simulation:
import matplotlib.pyplot as plt
plt.savefig('simulation_stats.png', dpi=300, bbox_inches='tight')
```

## Matplotlib Backends

Matplotlib uses different backends for rendering. The default is usually appropriate, but you can specify:

### Common Backends

**Interactive (GUI):**

- `TkAgg` - Tk/Tcl (default on many systems)
- `Qt5Agg` - Qt5 (recommended for Linux)
- `MacOSX` - Native macOS backend

**Non-Interactive:**

- `Agg` - PNG output only, no window
- `PDF` - Direct PDF generation
- `SVG` - Direct SVG generation

### Specifying Backend

**Environment Variable:**

```bash
export MPLBACKEND=Qt5Agg
python -m ridehail config.config -a map
```

**Python Script:**

```python
import matplotlib
matplotlib.use('Qt5Agg')
```

### Qt Library Conflicts

If you encounter Qt version conflicts:

```
Cannot mix incompatible Qt library (5.15.3) with this library (5.15.17)
```

**Solution 1: Virtual Environment**

```bash
python -m venv ridehail_env
source ridehail_env/bin/activate  # Windows: ridehail_env\Scripts\activate
pip install ridehail[desktop]
python -m ridehail config.config -a map
```

**Solution 2: Different Backend**

```bash
export MPLBACKEND=TkAgg
python -m ridehail config.config -a map
```

**Solution 3: System Package Cleanup**

```bash
# Remove conflicting system Qt packages (Ubuntu/Debian)
sudo apt remove python3-pyqt5
pip install ridehail[desktop]
```

## Performance Considerations

### Desktop vs. Terminal

Desktop matplotlib animations are slower than terminal modes:

| Aspect            | Desktop (matplotlib) | Terminal (textual) |
| ----------------- | -------------------- | ------------------ |
| Frame rate        | 5-15 FPS             | 20-40 FPS          |
| Startup time      | 2-5 seconds          | <1 second          |
| Memory usage      | Higher               | Lower              |
| CPU usage         | Higher               | Lower              |
| Export quality    | Excellent            | Limited            |
| SSH compatibility | Requires X11         | Native             |

### Performance Tips

**For large cities:**

- Use `stats` instead of `map` (no spatial rendering)
- Increase `animation_delay` to reduce frame rate
- Consider `animation = none` for maximum speed

**For long simulations:**

- Use terminal modes for real-time monitoring
- Save results to file
- Analyze with desktop tools afterward

**For analysis:**

- Run with `animation = none`
- Export results as JSON/CSV
- Create charts from output data offline

## Headless Environments

For servers without displays:

### Option 1: Non-Interactive Backend

```bash
export MPLBACKEND=Agg
python -m ridehail config.config -a none
# Then create charts from output files
```

### Option 2: X11 Forwarding over SSH

```bash
# On server
export DISPLAY=localhost:10.0
python -m ridehail config.config -a map

# Connect with X11 forwarding
ssh -X user@server
python -m ridehail config.config -a map
```

### Option 3: Use Terminal Modes

```bash
# Recommended for remote servers
python -m ridehail config.config -a terminal_stats
```

## Customizing Plots

### Figure Size

Set in matplotlib rcParams:

```python
import matplotlib.pyplot as plt
plt.rcParams['figure.figsize'] = (12, 8)
```

### DPI (Resolution)

```python
plt.rcParams['figure.dpi'] = 150  # Higher = more detailed
```

### Style

```python
plt.style.use('seaborn-v0_8')  # Or other style
```

### Colors

Edit source code in `ridehail/animation/` to customize color schemes.

## Exporting Results

### During Simulation

Use matplotlib toolbar "Save" button:

- PNG: Raster format, good for web/presentations
- PDF: Vector format, publication quality
- SVG: Scalable vector, web-compatible

### After Simulation

Results are saved to JSON files (if configured). Create custom plots:

```python
import json
import matplotlib.pyplot as plt

with open('simulation_output.json') as f:
    data = json.load(f)

plt.plot(data['time'], data['p1_fraction'], label='P1 (Idle)')
plt.plot(data['time'], data['p2_fraction'], label='P2 (Dispatched)')
plt.plot(data['time'], data['p3_fraction'], label='P3 (Occupied)')
plt.xlabel('Time Block')
plt.ylabel('Fraction of Vehicles')
plt.legend()
plt.title('Vehicle Phase Distribution')
plt.savefig('custom_analysis.png', dpi=300, bbox_inches='tight')
plt.show()
```

## Comparing with Terminal

### When to Use Desktop

- Need publication-quality output
- Exporting figures for reports/papers
- Detailed frame-by-frame analysis
- Prefer traditional matplotlib interface
- Working on local machine with GUI

### When to Use Terminal

- Remote server access (SSH)
- Development and debugging
- Real-time monitoring needs
- Faster iteration cycles
- Resource-constrained environments
- Want keyboard controls for parameter adjustment

## Next Steps

- **[Terminal Animations](terminal.md)** - Faster, SSH-friendly alternatives
- **[Animation Overview](overview.md)** - Compare all animation modes
- **[Configuration](../configuration/overview.md)** - Animation settings
