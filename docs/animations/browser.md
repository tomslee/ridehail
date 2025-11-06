# Browser-Based Animations

Browser-based animations provide interactive visualizations using Chart.js in your local browser. These modes automatically start a local HTTP server and open your browser.

## Installation

```bash
pip install ridehail
```

No additional dependencies needed - uses Python's built-in HTTP server and standard library.

## Web Map Mode

Interactive vehicle and trip visualization in your browser.

### Usage

```bash
python -m ridehail config.config -a web_map
```

**What happens:**
1. Starts local HTTP server (usually port 41967)
2. Opens browser automatically to `http://localhost:41967`
3. Displays interactive Chart.js visualization
4. Same interface as the [online lab](../lab/index.html)

### Display Elements

**Interactive Map:**
- City grid with roads and intersections
- Vehicles as colored markers:
  - **Blue** - P1 (Idle)
  - **Orange** - P2 (Dispatched)
  - **Green** - P3 (Occupied)
- Trip markers for origins and destinations
- Zoom and pan controls
- Smooth animations

**Statistics Panel:**
- Current time block
- Phase fractions (P1/P2/P3 percentages)
- Wait time and ride time averages
- Trip completion rate
- Vehicle count

### Browser Controls

**Mouse:**
- Scroll to zoom
- Click and drag to pan
- Hover over vehicles for details

**UI Controls:**
- Play/pause button
- Speed adjustment slider
- Reset simulation button
- Parameter adjustment controls

### Configuration

```ini
[ANIMATION]
animation = web_map
animation_delay = 0.1
```

Command-line:
```bash
python -m ridehail config.config -a web_map
```

### Best For

- Interactive exploration with mouse controls
- Better graphics quality than terminal
- Cross-platform compatibility (works anywhere)
- Teaching demonstrations
- Presentations
- No matplotlib dependencies needed

### Advantages Over Terminal Map

| Feature | web_map | terminal_map |
|---------|---------|--------------|
| Graphics quality | High (Canvas/SVG) | Text-based |
| Mouse interaction | ✅ Zoom, pan | ❌ |
| Color depth | Millions | 256 colors |
| Window size | Flexible | Terminal size |
| Works over SSH | ❌ Needs X11/browser | ✅ Native |
| Animation smoothness | Excellent | Good |

## Web Stats Mode

Statistical charts and graphs in your browser.

### Usage

```bash
python -m ridehail config.config -a web_stats
```

**What happens:**
1. Starts local HTTP server
2. Opens browser to statistics view
3. Displays Chart.js line charts and graphs

### Display Elements

**Interactive Charts:**
- **Phase Fractions Chart**: P1/P2/P3 percentages over time
- **Trip Metrics Chart**: Wait times and ride times
- **Utilization Charts**: Vehicle efficiency metrics
- **Economic Charts**: Earnings, costs (if equilibration enabled)

**Features:**
- Hover for exact values
- Legend toggle (click to hide/show series)
- Zoom in on time ranges
- Export chart as PNG

### Configuration

```ini
[ANIMATION]
animation = web_stats
animation_delay = 0.1
results_window = 60  # Rolling window size
```

### Best For

- Statistical analysis with better charts than terminal
- Interactive data exploration
- Clean, modern UI for reports
- Multi-metric comparison
- Export-quality charts

### Advantages Over Terminal Stats

| Feature | web_stats | terminal_stats |
|---------|-----------|----------------|
| Chart types | Line, bar, scatter | Line only |
| Interactivity | Hover, zoom, pan | Keyboard only |
| Export | PNG download | Screenshot only |
| Multi-chart | Multiple plots | Single plot |
| Styling | Customizable CSS | Terminal colors |

## Port Configuration

By default, web animations use port **41967**. If this port is in use:

**Automatic fallback:**
The server will try ports 41968, 41969, etc. until it finds an available port.

**Manual port specification:**
```bash
# Not yet implemented - uses automatic fallback
```

## Server Details

### HTTP Server

- Uses Python's built-in `http.server`
- Single-threaded, suitable for single user
- Serves files from `docs/lab/` directory
- Automatically shuts down when simulation ends

### Security

- **Localhost only**: Server binds to 127.0.0.1
- **Not accessible from network**: Safe for sensitive data
- **Temporary**: Server stops when simulation ends
- **No authentication**: Only accessible from local machine

### Manual Control

**View server output:**
```bash
python -m ridehail config.config -a web_map
# Server logs appear in terminal
```

**Stop server:**
- Close the terminal
- Press Ctrl+C
- Close the browser (simulation continues until terminal closed)

## Browser Compatibility

### Recommended Browsers

**Desktop:**
- Google Chrome (recommended)
- Mozilla Firefox
- Microsoft Edge
- Safari

**Mobile:**
- Works on mobile browsers but UI optimized for desktop

### Requirements

- Modern browser with JavaScript enabled
- HTML5 Canvas support
- ES6 JavaScript support (2015+)

All modern browsers support these features.

## Comparing Browser Options

### Local Browser Animations (web_map, web_stats)

**Advantages:**
- ✅ Full simulation speed (native Python)
- ✅ Access to all configuration options
- ✅ Works offline
- ✅ Can modify source code
- ✅ Better for large simulations

**Disadvantages:**
- ❌ Requires Python installation
- ❌ Need to install ridehail package

### Online Lab (https://tomslee.github.io/ridehail/lab/)

**Advantages:**
- ✅ No installation needed
- ✅ Try immediately
- ✅ Share via URL
- ✅ Cross-platform (phones, tablets)

**Disadvantages:**
- ❌ Slower (Pyodide WebAssembly overhead)
- ❌ Limited configuration options
- ❌ Requires internet connection
- ❌ Not suitable for large simulations

## Troubleshooting

### Browser Doesn't Open

**Problem:** Server starts but browser doesn't open automatically

**Solution:**
1. Check terminal for URL (e.g., `http://localhost:41967`)
2. Manually open browser and navigate to that URL
3. Or use: `python -m webbrowser http://localhost:41967`

### Port Already in Use

**Problem:** Error message about port 41967 in use

**Solution:**
- Server automatically tries next port (41968, etc.)
- Check terminal output for actual port being used
- Navigate to the displayed URL

### Connection Refused

**Problem:** Browser shows "Connection refused" or similar error

**Solution:**
1. Ensure simulation is still running (check terminal)
2. Check firewall isn't blocking localhost connections
3. Try refreshing browser
4. Restart simulation

### Charts Not Displaying

**Problem:** Browser opens but charts are blank or broken

**Solution:**
1. Check browser console for JavaScript errors (F12)
2. Ensure browser supports modern JavaScript (ES6+)
3. Try a different browser
4. Check internet connection (Chart.js CDN needs to load)

### Slow Performance

**Problem:** Animation stutters or lags in browser

**Solution:**
- Reduce `city_size` in configuration
- Increase `animation_delay` for fewer updates
- Close other browser tabs/applications
- Use hardware-accelerated browser

## Customization

### Styling

The web interface uses Material Design Lite. To customize:

1. Locate `docs/lab/style.css` in the installation
2. Modify CSS as needed
3. Refresh browser

### Chart Options

Chart.js options can be customized in `docs/lab/modules/map.js` and `docs/lab/modules/stats.js`.

### Server Configuration

Advanced users can modify `ridehail/animation/web_browser.py` to:
- Change default port
- Add SSL/HTTPS
- Customize HTTP headers
- Add CORS headers for development

## Next Steps

- **[Animation Overview](overview.md)** - Compare all animation modes
- **[Terminal Animations](terminal.md)** - SSH-friendly alternatives
- **[Desktop Animations](desktop.md)** - Publication-quality figures
- **[Online Lab](../lab/index.html)** - Try without installation
