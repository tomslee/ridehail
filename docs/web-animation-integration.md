# Web Animation Integration: Design Document

**Date**: 2025-11-02
**Status**: Proposal / Design Phase
**Author**: Analysis by Claude Code

## Executive Summary

This document explores integrating web-based animations (map and statistics charts) with the command-line interface, enabling users to run `python run.py config.config -as web_map` and view the browser-based visualization from `docs/lab/` locally.

**Recommendation**: Implement **Approach 2 (Local Web Server)** using Python's built-in HTTP server with automatic browser launch and config parameter passing.

---

## Table of Contents

1. [Background](#background)
2. [Current Architecture](#current-architecture)
3. [Proposed Approaches](#proposed-approaches)
4. [Detailed Comparison](#detailed-comparison)
5. [Recommended Implementation](#recommended-implementation)
6. [Technical Specifications](#technical-specifications)
7. [User Experience Flow](#user-experience-flow)
8. [Implementation Plan](#implementation-plan)
9. [Alternative Approaches](#alternative-approaches)
10. [Open Questions](#open-questions)

---

## Background

### Current Animation System

The ridehail simulation currently supports multiple animation styles:

**Terminal-based** (using Textual or Rich):
- `-as console` - Progress bars showing vehicle phases
- `-as terminal_map` - ASCII map with vehicle movements
- `-as terminal_stats` - Line charts using plotext
- `-as terminal_sequence` - Parameter sweep visualizations

**GUI-based** (using Matplotlib):
- `-as map` - Matplotlib map visualization
- `-as stats` - Matplotlib statistics charts

**Web-based** (separate deployment):
- Public site: https://tomslee.github.io/ridehail
- Interactive simulation with Chart.js visualizations
- Map view (vehicle movements) and stats view (time-series charts)
- Runs entirely in browser using Pyodide (Python in WebAssembly)

### Motivation

Users may want to leverage the web interface's advantages from the CLI:

1. **Rich interactivity**: Chart.js provides smooth, responsive charts with zoom, pan, hover tooltips
2. **Better visualizations**: Higher quality rendering than terminal ASCII art
3. **Modern UI**: Material Design interface with responsive controls
4. **Cross-platform**: Consistent rendering across operating systems
5. **Shareable**: Can capture screenshots or share browser window
6. **Unified workflow**: Use CLI for scripting/automation but web UI for visualization

---

## Current Architecture

### CLI Flow

```
┌─────────────┐
│   run.py    │
└──────┬──────┘
       │
       ├─ Parse config file
       ├─ Create RideHailSimulation
       │
       v
┌──────────────────────┐
│ Animation Factory    │
│ (animation/utils.py) │
└──────┬───────────────┘
       │
       ├─ Terminal animations (Textual/Rich)
       ├─ Matplotlib animations
       └─ Text output
```

### Web Flow

```
┌──────────────┐         ┌──────────────┐
│  Browser UI  │◄────────┤  app.js      │
│ (Chart.js)   │         │ (JS controls)│
└──────┬───────┘         └──────┬───────┘
       │                        │
       │ postMessage            │ postMessage
       │                        │
       v                        v
┌─────────────────────────────────────┐
│      webworker.js                   │
│      (Pyodide environment)          │
└──────┬──────────────────────────────┘
       │
       ├─ Load ridehail wheel
       ├─ Import worker.py
       │
       v
┌──────────────────────┐
│  worker.py           │
│  (Python bridge)     │
└──────┬───────────────┘
       │
       v
┌──────────────────────┐
│ RideHailSimulation   │
│ (core package)       │
└──────────────────────┘
```

---

## Proposed Approaches

### Approach 1: Remote Upload to Public Site

**Description**: CLI opens browser to https://tomslee.github.io/ridehail and programmatically uploads the config file using the existing upload functionality.

**Implementation Strategy**:
1. Open browser to public URL
2. Use browser automation (Selenium/Playwright) to:
   - Wait for page load
   - Trigger file upload dialog
   - Upload config file
   - Start simulation

### Approach 2: Local Web Server

**Description**: CLI starts a local HTTP server serving `docs/lab/`, opens browser to `http://localhost:PORT`, and passes config parameters via URL or pre-loaded file.

**Implementation Strategy**:
1. Find available port
2. Start Python HTTP server serving `docs/lab/`
3. Pass config to browser via:
   - URL parameters (base64-encoded config)
   - Write config to known location in `docs/lab/`
   - Session storage pre-population
4. Open browser automatically
5. Server runs until simulation completes or user closes

---

## Detailed Comparison

| Aspect | Approach 1: Remote Upload | Approach 2: Local Server | Winner |
|--------|--------------------------|-------------------------|--------|
| **Privacy** | Config uploaded to public site | All data stays local | 🏆 Local |
| **Internet Required** | Yes | No (works offline) | 🏆 Local |
| **Implementation Complexity** | High (browser automation) | Medium (HTTP server + browser launch) | 🏆 Local |
| **Reliability** | Depends on external service | Self-contained | 🏆 Local |
| **Security** | CORS issues, automation detection | No CORS issues | 🏆 Local |
| **User Experience** | Slower (network), may fail if site down | Fast, reliable | 🏆 Local |
| **Dependencies** | Selenium/Playwright | Built-in Python modules | 🏆 Local |
| **Development Testing** | Harder to test/debug | Easy to test locally | 🏆 Local |
| **Shareability** | Can generate shareable URL | Local only | ⚖️ Remote |
| **Maintenance** | Depends on public site structure | Self-contained | 🏆 Local |

**Score**: Local Server wins 9/10 categories

---

## Recommended Implementation

### Why Local Server?

1. **Privacy-preserving**: No data leaves user's machine
2. **Simpler architecture**: Uses Python built-in modules (`http.server`, `webbrowser`)
3. **Reliable**: No dependency on external service or internet connection
4. **Consistent with CLI philosophy**: Local execution and control
5. **Better developer experience**: Easier to test and debug
6. **Offline capable**: Works without internet access
7. **Security**: Avoids CORS issues and browser automation complexity

### High-Level Architecture

```
┌─────────────────────────────────────────────────────────┐
│                      run.py                             │
│                                                         │
│  ┌─────────────────────────────────────────────────┐   │
│  │  Animation Factory (-as web_map / -as web_stats)│   │
│  └─────┬───────────────────────────────────────────┘   │
│        │                                                │
│        v                                                │
│  ┌─────────────────────────────────────────────────┐   │
│  │     WebAnimation class                          │   │
│  │  1. Start HTTP server (threading.Thread)        │   │
│  │  2. Prepare config (write to docs/lab/config/)  │   │
│  │  3. Open browser (webbrowser.open)              │   │
│  │  4. Monitor simulation (WebSocket/polling)      │   │
│  │  5. Cleanup on exit                             │   │
│  └─────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────┘
                           │
                           │ HTTP on localhost:PORT
                           v
                    ┌──────────────────┐
                    │     Browser      │
                    │  (localhost:PORT)│
                    └──────┬───────────┘
                           │
                           │ Loads docs/lab/index.html
                           v
                    ┌──────────────────┐
                    │   Web UI         │
                    │  - Auto-loads    │
                    │    config        │
                    │  - Starts sim    │
                    │  - Chart.js viz  │
                    └──────────────────┘
```

---

## Technical Specifications

### New Animation Classes

**File**: `ridehail/animation/web_browser.py`

```python
from ridehail.animation.base import RideHailAnimation
import http.server
import threading
import webbrowser
import socketserver
import json
import os
from pathlib import Path

class WebBrowserAnimation(RideHailAnimation):
    """
    Base class for web browser animations.
    Starts local HTTP server and opens browser to view simulation.
    """

    def __init__(self, sim, chart_type="map"):
        super().__init__(sim)
        self.chart_type = chart_type  # "map" or "stats"
        self.port = self._find_free_port()
        self.server = None
        self.server_thread = None
        self.lab_dir = Path(__file__).parent.parent.parent / "docs" / "lab"

    def _find_free_port(self):
        """Find an available port for HTTP server"""
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            s.listen(1)
            port = s.getsockname()[1]
        return port

    def _prepare_config(self):
        """Write config to location browser can load"""
        config_dir = self.lab_dir / "config"
        config_dir.mkdir(exist_ok=True)

        # Convert simulation config to web format
        config_data = {
            "citySize": self.sim.config.city_size.value,
            "vehicleCount": self.sim.config.vehicle_count.value,
            "requestRate": self.sim.config.base_demand.value,
            # ... map all config parameters
        }

        # Write as JSON for browser to load
        config_file = config_dir / "cli_config.json"
        with open(config_file, 'w') as f:
            json.dump(config_data, f)

        return config_file

    def _start_server(self):
        """Start HTTP server in background thread"""
        os.chdir(self.lab_dir)
        handler = http.server.SimpleHTTPRequestHandler

        self.server = socketserver.TCPServer(("", self.port), handler)
        self.server_thread = threading.Thread(target=self.server.serve_forever)
        self.server_thread.daemon = True
        self.server_thread.start()

        print(f"Started web server at http://localhost:{self.port}")

    def _open_browser(self):
        """Open browser to simulation page"""
        url = f"http://localhost:{self.port}/?chartType={self.chart_type}&autoLoad=cli_config.json"
        webbrowser.open(url)

    def start_simulation(self):
        """Initialize and start the web browser simulation"""
        try:
            self._prepare_config()
            self._start_server()
            self._open_browser()

            print(f"\nSimulation running in browser at http://localhost:{self.port}")
            print("Close browser or press Ctrl+C to exit...")

            # Keep alive while browser is open
            # Could implement WebSocket for two-way communication
            while True:
                self.server.handle_request()

        except KeyboardInterrupt:
            print("\nShutting down web server...")
            self.cleanup()

    def cleanup(self):
        """Shutdown server and cleanup resources"""
        if self.server:
            self.server.shutdown()
            self.server.server_close()

        # Remove temporary config file
        config_file = self.lab_dir / "config" / "cli_config.json"
        if config_file.exists():
            config_file.unlink()

class WebMapAnimation(WebBrowserAnimation):
    """Web browser animation with map visualization"""
    def __init__(self, sim):
        super().__init__(sim, chart_type="map")

class WebStatsAnimation(WebBrowserAnimation):
    """Web browser animation with stats charts"""
    def __init__(self, sim):
        super().__init__(sim, chart_type="stats")
```

### Integration with Animation Factory

**File**: `ridehail/animation/utils.py`

```python
def create_animation_factory(animation_style, sim):
    """Factory function to create the appropriate animation instance"""
    from ridehail.atom import Animation

    # ... existing animation styles ...

    elif animation_style == Animation.WEB_MAP:
        from .web_browser import WebMapAnimation
        return WebMapAnimation(sim)
    elif animation_style == Animation.WEB_STATS:
        from .web_browser import WebStatsAnimation
        return WebStatsAnimation(sim)
```

### Add to Animation Enum

**File**: `ridehail/atom.py`

```python
class Animation(Enum):
    # ... existing values ...
    WEB_MAP = "web_map"
    WEB_STATS = "web_stats"
```

### Browser-Side Auto-Load

**File**: `docs/lab/app.js`

Enhance to support URL parameters:

```javascript
// Check for CLI auto-load parameters
const urlParams = new URLSearchParams(window.location.search);
if (urlParams.has('autoLoad')) {
  const configFile = urlParams.get('autoLoad');
  const chartType = urlParams.get('chartType') || 'map';

  // Load config from server
  fetch(`./config/${configFile}`)
    .then(response => response.json())
    .then(config => {
      // Apply config to lab settings
      applyConfigFromCLI(config);

      // Set chart type
      setChartType(chartType);

      // Auto-start simulation
      setTimeout(() => {
        startSimulation();
      }, 1000);
    })
    .catch(error => {
      console.error('Failed to load CLI config:', error);
    });
}
```

---

## User Experience Flow

### Command Execution

```bash
$ python run.py city.config -as web_map
```

### What Happens

1. **CLI starts**:
   ```
   Ridehail Simulation
   Loading configuration from city.config...
   Starting web server on http://localhost:8374...
   Opening browser...
   ```

2. **Browser opens automatically** showing the simulation:
   - Map view already loaded (for `-as web_map`)
   - Config pre-loaded from city.config
   - Simulation starts automatically
   - User sees familiar Chart.js visualization

3. **Simulation runs**:
   - User can interact with web controls (pause, reset, parameter adjustments)
   - CLI terminal shows: "Simulation running. Press Ctrl+C to stop."

4. **Exit**:
   - User closes browser OR presses Ctrl+C in terminal
   - Server shuts down gracefully
   - Temporary files cleaned up

### Example Session

```bash
$ python run.py metro.config -as web_map

Ridehail Simulation v0.2.12
===========================

Loading configuration from metro.config
  City size: 20x20
  Vehicles: 50
  Base demand: 8.0

Starting local web server...
  Server: http://localhost:8374
  Lab directory: /home/user/ridehail-simulation/docs/lab

Preparing configuration for browser...
  Config written to: docs/lab/config/cli_config.json

Opening browser...
  URL: http://localhost:8374/?chartType=map&autoLoad=cli_config.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Simulation running in browser
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

View at: http://localhost:8374

Press Ctrl+C to stop server and exit...

[Server logs appear here as browser makes requests]

^C
Shutting down web server...
Cleaning up temporary files...
Done.
```

---

## Implementation Plan

### Phase 1: Core Infrastructure ✅ **Planning**

#### Step 1.1: Create Base Web Animation Class
- **File**: `ridehail/animation/web_browser.py`
- **Tasks**:
  - Implement `WebBrowserAnimation` base class
  - Port finding logic (`_find_free_port()`)
  - HTTP server initialization (`_start_server()`)
  - Browser launching (`_open_browser()`)
  - Cleanup handling
- **Test**: Start server manually, verify browser opens

#### Step 1.2: Configuration Conversion
- **Function**: `_prepare_config()`
- **Tasks**:
  - Map all simulation config parameters to web format
  - Write JSON to `docs/lab/config/cli_config.json`
  - Handle special cases (enums, paths, etc.)
- **Test**: Verify generated JSON matches web UI expectations

#### Step 1.3: Create Specific Animation Classes
- **Classes**: `WebMapAnimation`, `WebStatsAnimation`
- **Tasks**:
  - Inherit from `WebBrowserAnimation`
  - Set appropriate chart_type
  - Override any specific behavior
- **Test**: Instantiate both classes, verify configuration

### Phase 2: Browser Auto-Load ✅ **Planning**

#### Step 2.1: URL Parameter Handling
- **File**: `docs/lab/app.js`
- **Tasks**:
  - Parse URL parameters (`?chartType=map&autoLoad=cli_config.json`)
  - Load config from `./config/` directory
  - Apply settings to `labSimSettings`
  - Update UI controls to match
- **Test**: Open browser with URL params manually, verify config loads

#### Step 2.2: Auto-Start Logic
- **Tasks**:
  - Detect CLI-launched session via URL parameter
  - Auto-start simulation after config loads
  - Set initial chart type (map vs stats)
  - Disable initial loading overlay faster
- **Test**: Verify simulation starts automatically with correct settings

#### Step 2.3: Visual Feedback
- **Tasks**:
  - Show "Loaded from CLI" indicator in UI
  - Display notice that server is controlled by CLI
  - Update title bar to show "CLI Mode"
- **Test**: Check visual indicators appear correctly

### Phase 3: Integration ✅ **Planning**

#### Step 3.1: Add to Animation Factory
- **File**: `ridehail/animation/utils.py`
- **Tasks**:
  - Import web animation classes
  - Add cases for `Animation.WEB_MAP` and `Animation.WEB_STATS`
  - Handle import errors gracefully
- **Test**: Verify factory creates correct class instances

#### Step 3.2: Add Animation Enum Values
- **File**: `ridehail/atom.py`
- **Tasks**:
  - Add `WEB_MAP = "web_map"`
  - Add `WEB_STATS = "web_stats"`
- **Test**: Verify enums accessible and serializable

#### Step 3.3: Update Configuration System
- **File**: `ridehail/config.py`
- **Tasks**:
  - Add new animation styles to choices
  - Update help text for `-as` parameter
  - Add any web-specific config options
- **Test**: Verify `-as web_map` accepted as valid option

### Phase 4: Server Management ✅ **Planning**

#### Step 4.1: Graceful Shutdown
- **Tasks**:
  - Handle Ctrl+C (KeyboardInterrupt)
  - Shutdown server cleanly
  - Close any open WebSocket connections
  - Remove temporary config files
- **Test**: Press Ctrl+C, verify clean shutdown without errors

#### Step 4.2: Server Monitoring
- **Tasks**:
  - Detect when browser window closes
  - Option to auto-shutdown server when browser closes
  - Keep-alive mechanism if long-running simulation
- **Test**: Close browser, verify server detects and optionally shuts down

#### Step 4.3: Error Handling
- **Tasks**:
  - Handle port already in use
  - Handle docs/lab directory not found
  - Handle browser launch failures
  - Provide clear error messages
- **Test**: Test various failure scenarios, verify error messages

### Phase 5: Advanced Features (Optional)

#### Step 5.1: Two-Way Communication
- **Implementation**: WebSocket connection between CLI and browser
- **Features**:
  - CLI can monitor simulation progress
  - CLI can send commands to browser (pause, reset, etc.)
  - Browser can report back to CLI (results, errors)
- **Benefit**: More integrated experience, CLI remains responsive

#### Step 5.2: Results Export
- **Features**:
  - Automatically download results when simulation completes
  - Save to file specified in CLI args
  - Export charts as images
- **Benefit**: Fully automated workflow

#### Step 5.3: Headless Mode
- **Implementation**: Run web simulation without visible browser
- **Uses**: Automated testing, CI/CD, batch processing
- **Tools**: Selenium with headless Chrome/Firefox
- **Benefit**: Generate web-quality visualizations in scripts

---

## Alternative Approaches

### 3. Hybrid Approach

**Description**: Offer both local and remote options

**Implementation**:
```bash
# Local server (default)
python run.py config.config -as web_map

# Remote upload
python run.py config.config -as web_map --remote

# Or separate command
python run.py config.config --web-upload
```

**Pros**:
- Flexibility for users to choose
- Remote option useful for sharing results

**Cons**:
- More code to maintain
- Complexity in supporting both modes

### 4. Embedded Browser

**Description**: Embed Chromium in Python app (via CEF or similar)

**Pros**:
- No external browser dependency
- Full control over environment
- Can look like native desktop app

**Cons**:
- Large dependency (Chromium Embedded Framework ~100MB)
- Complex build process
- Platform-specific binaries
- Overkill for this use case

### 5. Generate Static HTML

**Description**: Generate standalone HTML file with embedded data and scripts

**Pros**:
- Shareable single file
- No server needed
- Works offline forever

**Cons**:
- Large file size (includes all simulation data)
- No interactivity during simulation
- Pre-render all frames or lose animation

---

## Open Questions

### 1. Server Lifecycle

**Question**: Should the server shut down automatically when browser closes, or stay running?

**Options**:
- **Auto-shutdown**: More user-friendly, prevents orphaned processes
- **Keep running**: Allows refreshing browser, multiple browser windows
- **Configurable**: `--web-keep-alive` flag

**Recommendation**: Auto-shutdown by default, with `--web-keep-alive` flag for power users

### 2. Config File Location

**Question**: Where should the temporary config file be written?

**Options**:
- `docs/lab/config/cli_config.json` (as proposed)
- `~/.ridehail/web_cache/config.json` (user config directory)
- `tmpfile.NamedTemporaryFile()` (OS temp directory)

**Recommendation**: `docs/lab/config/` directory:
- Pros: Simple, no path issues, easy cleanup
- Cons: Requires write access to package directory
- Alternative: Create `.gitignore`d `config/` directory on first use

### 3. Progress Monitoring

**Question**: Should CLI show simulation progress, or just "Server running"?

**Options**:
- **Silent**: Just "Server running..."
- **Basic**: Show block count via polling
- **Full**: WebSocket connection showing real-time updates in terminal
- **Hybrid**: Option to enable verbose monitoring

**Recommendation**: Basic block count polling:
```
Simulation running | Block: 42 | http://localhost:8374
```

### 4. Result Handling

**Question**: What happens to simulation results?

**Options**:
- Stay in browser only (user can download manually)
- Automatically save to file specified by CLI
- Offer both via `--output` parameter

**Recommendation**: Respect existing `--output` parameter:
- If specified: Auto-download results when simulation completes
- If not specified: Results stay in browser, user can download manually

### 5. Multiple Simultaneous Simulations

**Question**: Can users run multiple `-as web_*` commands concurrently?

**Implementation**:
- Each gets unique port (already handled by `_find_free_port()`)
- Each gets unique config file (use PID or timestamp in filename)
- Server cleanup must be process-specific

**Recommendation**: Support multiple concurrent simulations:
```bash
# Terminal 1
python run.py config1.config -as web_map

# Terminal 2 (different port, different browser window)
python run.py config2.config -as web_stats
```

### 6. Dependencies

**Question**: Does this require additional Python packages?

**Current solution uses**:
- `http.server` (built-in)
- `webbrowser` (built-in)
- `threading` (built-in)
- `json` (built-in)
- `socketserver` (built-in)

**Recommendation**: No additional dependencies required! ✅

### 7. Windows Compatibility

**Question**: Does this work on Windows?

**Considerations**:
- `webbrowser.open()` - ✅ Cross-platform
- `http.server` - ✅ Cross-platform
- Path handling - Need `pathlib` for cross-platform paths
- Port binding - ✅ Same on all platforms

**Recommendation**: Should work on all platforms with no platform-specific code needed

---

## Testing Strategy

### Unit Tests

**File**: `test/test_web_animation.py`

```python
def test_find_free_port():
    """Port finder returns available port"""

def test_config_conversion():
    """Config converts correctly to web format"""

def test_server_starts():
    """HTTP server starts successfully"""

def test_browser_opens():
    """Browser launch doesn't error"""

def test_cleanup():
    """Cleanup removes temp files and shuts down server"""
```

### Integration Tests

```bash
# Basic functionality
python run.py test.config -as web_map
# Verify: Browser opens, config loads, map displays

python run.py test.config -as web_stats
# Verify: Browser opens, config loads, stats chart displays

# Shutdown handling
python run.py test.config -as web_map
# Press Ctrl+C
# Verify: Clean shutdown, no errors, temp files removed

# Multiple concurrent
python run.py config1.config -as web_map &
python run.py config2.config -as web_stats &
# Verify: Both work on different ports without conflict
```

### Cross-Platform Testing

- ✅ Linux (Ubuntu, Fedora)
- ✅ macOS (Intel, Apple Silicon)
- ✅ Windows (Windows 10, Windows 11)

---

## Success Criteria

### Minimum Viable Product (MVP)

- ✅ User runs `python run.py config.config -as web_map`
- ✅ Browser opens automatically to local server
- ✅ Config pre-loaded correctly
- ✅ Map visualization displays
- ✅ User can interact with web controls
- ✅ Ctrl+C cleanly shuts down
- ✅ No additional dependencies required

### Enhanced Version

- ✅ All MVP criteria
- ✅ `-as web_stats` works for statistics view
- ✅ CLI shows block count progress
- ✅ Auto-shutdown when browser closes
- ✅ Multiple concurrent simulations supported
- ✅ Results auto-save if `--output` specified

### Future Vision

- ✅ All Enhanced criteria
- ✅ WebSocket for two-way CLI ↔ browser communication
- ✅ CLI can pause/resume browser simulation
- ✅ Headless mode for scripting
- ✅ Chart export automation

---

## Conclusion

We recommend implementing **Approach 2: Local Web Server** because it provides the best balance of:

- **Simplicity**: Uses built-in Python modules
- **Privacy**: No data leaves local machine
- **Reliability**: No external dependencies
- **User Experience**: Fast, smooth, local execution
- **Maintainability**: Self-contained, easy to test

The implementation is straightforward, requires no additional dependencies, and integrates cleanly with the existing animation system. Users get the benefits of the rich web interface while maintaining the convenience and scripting power of the command-line interface.

### Next Steps

1. **Approval**: Review this document and approve the approach
2. **Implementation**: Follow Phase 1-4 implementation plan
3. **Testing**: Cross-platform testing on Linux, macOS, Windows
4. **Documentation**: Update user docs and CLAUDE.md
5. **Optional**: Consider Phase 5 advanced features based on user feedback

---

## Appendix: Related Files

### Files to Modify

- `ridehail/animation/web_browser.py` (new)
- `ridehail/animation/utils.py` (add factory cases)
- `ridehail/atom.py` (add enum values)
- `ridehail/config.py` (add animation choices)
- `docs/lab/app.js` (add URL parameter handling)
- `docs/lab/.gitignore` (ignore config/ directory)

### Files to Reference

- `ridehail/animation/base.py` - Base animation class interface
- `ridehail/animation/terminal_map.py` - Example animation implementation
- `docs/lab/worker.py` - Config parameter mapping reference
- `docs/lab/js/config-mapping.js` - Desktop ↔ web config conversion

---

**Document Version**: 1.0
**Last Updated**: 2025-11-02
**Status**: Ready for review and approval
