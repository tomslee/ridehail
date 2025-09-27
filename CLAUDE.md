# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a ridehail simulation project that models the dynamics of ride-hailing services. The simulation supports multiple visualization modes, can run sequences of simulations, and includes both desktop and browser-based interfaces.

## Core Architecture

### Main Components

- **`run.py`**: Entry point that orchestrates simulations based on configuration files
- **`ridehail/`**: Core simulation package containing:
  - `config.py`: Configuration system with validation and parameter management
  - `simulation.py`: Core simulation engine
  - `animation.py`: Visualization components (console, matplotlib)
  - `dispatch.py`: Vehicle dispatch logic
  - `sequence.py`: Multi-simulation sequence runner
  - `atom.py`: Core data structures and enums

### Configuration System

The project uses a robust configuration system centered around `.config` files:

- Configuration files define simulation parameters (see examples: `test.config`, `metro.config`, `city.config`)
- Command-line arguments can override config file settings
- The `ConfigItem` class manages parameter validation, types, and defaults

## Development Commands

### Running Simulations

```bash
# Basic simulation run
python run.py <config_file>.config
# OR with uv
uv run run.py <config_file>.config

# Create new config file
python run.py -wc my_simulation.config

# Run with command line overrides (example: disable graphics)
python run.py <config_file>.config -dr None

# Get help on command line options
python run.py --help

# Run with profiling
python run.py --profile <config_file>.config
```

### Package Management

```bash
# Install dependencies
pip install -r requirements.txt
# OR with uv
uv pip install -r requirements.txt

# Build package
python -m build
# OR with uv
uv build --wheel --package ridehail

# Install built package
pip install dist/ridehail-0.1.0-py3-none-any.whl --force-reinstall
# OR with uv
uv pip install dist/ridehail-0.1.0-py3-none-any.whl --force-reinstall
```

### Testing

```bash
# Run tests (basic test files exist)
python -m pytest test/
python test_config_loading.py
python test_config_validation.py
```

### Linting and Code Quality

```bash
# Run ruff (configured in dependencies)
ruff check .
ruff format .
```

### Web Interface (Browser Lab)

```bash
# Build and serve the browser version
cp dist/ridehail-0.1.0-py3-non-any.whl docs/lab/dist/
cd docs/lab
python -m http.server
# Then navigate to http://localhost:8000
```

## Key Configuration Parameters

The simulation supports various configuration options including:

- City boundaries and map settings
- Vehicle fleet size and dispatch algorithms
- Animation styles (none, console, matplotlib)
- Sequence running for parameter sweeps
- Profiling and performance analysis

## File Structure Conventions

- Configuration files use `.config` extension and are stored in project root
- Test files follow `test_*.py` naming convention
- Documentation is in `docs/` directory
- Plotting utilities are in `plot/` directory
- Browser lab interface files are in `docs/lab/`

## Important Notes

- The project supports both traditional Python virtual environments and modern tools like `uv`
- Configuration validation is strict - invalid parameters will raise `ConfigValidationError`
- The browser interface uses Pyodide to run Python code client-side
- Profiling can be enabled with the `--profile` flag for performance analysis

## Textual Migration Progress Log

### Key Architecture Patterns

- Animation classes inherit from `TextualBasedAnimation` → `RideHailAnimation`
- App classes inherit from Textual's `App`
- Apps receive animation instance via constructor to access all config attributes
- Configuration integration: `-tx` flag toggles Textual mode with full backward compatibility

## Textual Native Animation Migration Plan - September 2025 🎯

While implementing this plan, Claude should not run tests that use Textual libraries as they pollute the claude prompt environment. Instead, when it's time for a test to be run, I (the Claude user, not Claude) should run it from a separate console.

### Overview

Planned migration from manual interpolation system to Textual's native animation capabilities, incorporating insights from Chart.js implementation in `docs/lab/modules/map.js`.

### Key Insight: Half-Way Point Animation Strategy

Analysis of the Chart.js implementation revealed a critical pattern for smooth vehicle animations:

**Chart.js Pattern** (`docs/lab/modules/map.js:263-271`):

```javascript
if (frameIndex % 2 != 0) {
  // interpolation point: change directions and trip marker location
  window.chart.data.datasets[0].rotation = vehicleRotations;
  window.chart.data.datasets[0].pointStyle = vehicleStyles;
}
```

**Key Discovery**: The browser implementation uses explicit midpoint frames (e.g., (3,2) → (3.5,2) → (4,2)) to handle:

- Vehicle direction changes during transit
- Phase color updates at logical moments
- Trip marker timing synchronization

### Migration Benefits

- **Smoother animations** using Textual's native easing functions
- **Better performance** by eliminating complex interpolation calculations
- **Cleaner architecture** with individual vehicle widgets vs. monolithic rendering
- **Enhanced visual effects** (pulsing trips, scaling state changes)
- **Proper vehicle orientation** with midpoint direction updates

### Step-by-Step Implementation Plan

#### Phase 1: Foundation & Architecture

**Step 1: Create Layer-Based Widget Architecture** ✅ **COMPLETED**

- ✅ Replace monolithic `MapWidget` with composable layers
- ✅ Create `StaticMapGrid`, `VehicleLayer`, `TripMarkerLayer`, `MapContainer`
- ✅ **CRITICAL FIX**: Corrected coordinate system scaling issue - reverted to working `MapWidget`
- ✅ **Validation**: Same visual output as current implementation with proper full-screen scaling

**Step 2: Implement Static Map Grid**

- Extract road/intersection rendering into `StaticMapGrid` widget
- Remove vehicle/trip rendering - static background only
- **Validation**: Grid displays correctly without vehicles/trips

**Step 3: Create Individual Vehicle Widgets**

- Replace bulk vehicle rendering with `VehicleWidget` instances
- Each widget handles single vehicle with positioning
- **Validation**: Vehicles appear at correct positions (no animation yet)

#### Phase 2: Animation Integration

**Step 4: Enhanced Textual Animation with Midpoint Strategy**

**Step 5: Remove Manual Interpolation System**

- Eliminate `_interpolation()`, `get_interpolated_position()`, `_create_interpolated_vehicle_positions()`
- Remove `frame_index` reactive attribute and manual calculations
- Remove interpolation logic from `simulation_step()`
- **Enhanced Removal**: With midpoint strategy, can remove even more complexity
- **Validation**: Animation remains smooth, performance improved

#### Phase 3: Enhancement & Polish

**Step 6: Enhanced Visual Effects**

- Add pulsing animations for waiting trips
- Implement scaling effects for vehicle state changes
- Add fade/appear effects for trip markers
- **Validation**: Enhanced visual feedback without affecting core functionality

**Step 7: Performance Optimization**

- Remove now-unnecessary performance optimizations from manual system
- Remove `COLORED_VEHICLES` pre-formatting (individual widgets handle styling)
- Remove `_create_trip_markers_map()` caching
- Simplify update logic in `simulation_step()`
- **Validation**: Performance maintained or improved, cleaner code

### Validation Strategy

**Test Commands**:

```bash
# Basic functionality
python run.py test.config -as terminal_map -tx

# Small city performance
python run.py dispatch.config -as terminal_map -tx

# Larger city scaling
python run.py metro.config -as terminal_map -tx
```

**Success Criteria Per Step**:

1. **Visual Parity**: Each step maintains same visual output as previous
2. **Performance**: No degradation in animation smoothness
3. **Functionality**: All keyboard controls and simulation features work
4. **Enhanced Animation**: Proper vehicle orientation changes at midpoints
5. **Error Handling**: Graceful handling of edge cases

### Implementation Notes

Coordinate systems:

- Remember that there are two coordinate systems at work.
  - One is the simulation (or City) coordinate system: both x and y values go from 0 to city_size with roads in a grid at the integer values, and intersections where x and y are both integers. Vehicles move from intersection to intersection with each simulation step, but "interpolation" has been introduced to compute intermediate points for smoother display. The interpolation may not be of use here except for the benefits of a half-way point (see below).
  - The second is the display coordinate system: a set of characters on the terminal display. At each character location there is an intersection, a road, or a space (the area between roads). Vehicles and trip end points occur only on roads of course.
- It is best to carry out most calculations in the city coordinae system where possible.
- The transformation between city and display coordinate systems is computed by horizontal_spacing and vertical_spacing, which is the number of characters (in either direction) per unit of city coordinates.

**Half-Way Point Specific Benefits**:

- **Vehicle Orientation**: Direction changes visible at intersection centers, not random points
- **State Synchronization**: Phase colors update at logical moments during transit
- **Trip Marker Timing**: Origins/destinations appear at proper intersection points
- **Performance**: Eliminates complex interpolation math, lets Textual handle smooth movement

**Files to Modify**:

- `ridehail/animation/textual_map.py`: Complete migration from lines 27-499
- Remove manual interpolation system (lines 103-154, 182-198)
- Replace reactive `frame_index` with callback-based animations

**Risk Mitigation**:

- Each step preserves working animation system
- Can revert any step independently
- Keep current implementation as `TextualMapAnimationLegacy` during migration

### Session Planning

This migration may take several sessions. Each session should:

1. Focus on 1-2 steps maximum for thorough testing
2. Document progress and any discoveries in this section
3. Test extensively before proceeding to next step
4. Update this plan if new insights emerge during implementation

**Recommended Session Breakdown**:

- **Session 1**: Steps 1-2 (Foundation)
- **Session 2**: Step 3-4 (Individual widgets + basic animation)
- **Session 3**: Step 5 (Remove interpolation system)
- **Session 4**: Steps 6-7 (Polish and optimization)

### Future Session Log

_Document progress, discoveries, and any plan modifications here_

**September 2025 - Phase 1 Step 1 Completion:**

- ✅ Successfully implemented layer-based architecture foundation
- ✅ **Key Discovery**: Coordinate system scaling is critical - display coordinates vs city coordinates
- ✅ **Resolution**: Maintained working `MapWidget` while new layers are in development
- ✅ **Next Steps**: Focus on Step 2 (Static Map Grid) with proper coordinate transformation
- ✅ **Architecture Created**: `StaticMapGrid`, `VehicleLayer`, `TripMarkerLayer`, `MapContainer` classes ready for enhancement

**Key Insight for Next Session**: The `MapContainer._create_composed_display()` method needs the same coordinate transformation fix that was applied to `StaticMapGrid.render()`. The display-to-city coordinate mapping (`city_x = x / h_spacing`) is essential for proper scaling.

- Do not run simulations with python and textual, because they produce pollution in the claude prompt.

## Current Session Status - December 2024

### Textual Native Animation Migration: Step 5 Complete ✅

**Current Status**: Step 5 Enhanced Native Animation Implementation Complete

#### What We've Accomplished:
- ✅ **Steps 1-4**: Successfully completed foundation, static grid, individual widgets, and basic native animation
- ✅ **Step 5**: Enhanced MapWidget with timer-based native animation system
- ✅ **Type Compatibility**: Resolved Textual 0.70.0+ animation system conflicts (ScalarOffset vs Offset issues)
- ✅ **Benefits Preserved**: Midpoint strategy, two-stage movement, CSS transitions, state management

#### Key Implementation Details:
- **Animation Method**: Timer-based with CSS transitions (not `styles.animate()` due to type conflicts)
- **Midpoint Strategy**: Direction changes at intersection centers via `set_timer()` callbacks
- **Toggle Feature**: 'a' key switches between legacy interpolation and native animation modes
- **Compatibility**: Works with Textual 0.70.0+ (no Scalar imports needed - they were removed from public API)

#### Technical Solution:
**Problem**: Textual's animation system expected consistent types but we had `ScalarOffset` (internal) vs `Offset` (created) mismatches
**Solution**: Use CSS transitions with timer callbacks instead of `styles.animate()`:
```python
# Stage 1: Move to midpoint
self.styles.offset = Offset(int(mid_x), int(mid_y))
self.styles.transitions = {"offset": f"{duration/2}s"}
self.set_timer(duration/2, self._midpoint_state_update)
```

#### Files Modified:
- `ridehail/animation/textual_map.py`: Enhanced `VehicleWidget` with timer-based animation, `MapWidget` with dual-mode support

#### Next Session Tasks:
1. **User Testing**: Validate native animation works without errors when toggling with 'a' key
2. **If Successful**: Proceed to Step 6 (Enhanced Visual Effects) and Step 7 (Performance Optimization)
3. **If Issues**: Debug and refine the timer-based animation approach

#### Test Command:
```bash
python run.py test.config -as terminal_map -tx
# Press 'a' to toggle to native animation mode
# Should show smooth vehicle movement with direction changes at intersection midpoints
```

The implementation preserves all Chart.js-inspired midpoint benefits while solving the ScalarOffset type conflicts through Textual's CSS transition system.

## Chart.js Torus Edge Handling Logic - September 2025 🔄

### Analysis of Chart.js Implementation

**Source**: `docs/lab/modules/map.js:454-493`

The Chart.js implementation in the browser lab provides a robust solution for handling vehicles that cross torus boundaries (wrapping from one edge of the map to the opposite edge) without creating visual anomalies where vehicles appear to "streak" across the entire map.

### Core Strategy: Two-Phase Update with Animation Suppression

#### Phase 1: Edge Detection (Lines 456-480)

After normal position updates, the system checks each vehicle against boundary thresholds:

```javascript
// Boundary detection with buffer zones
if (vehicle.x > citySize - 0.6) {      // Right edge
    newX = -0.5;                       // Teleport to left side
    needsRefresh = true;
}
if (vehicle.x < -0.1) {                // Left edge
    newX = citySize - 0.5;             // Teleport to right side
    needsRefresh = true;
}
if (vehicle.y > citySize - 0.9) {      // Top edge
    newY = -0.5;                       // Teleport to bottom
    needsRefresh = true;
}
if (vehicle.y < -0.1) {                // Bottom edge
    newY = citySize - 0.5;             // Teleport to top
    needsRefresh = true;
}
```

#### Phase 2: Instant Teleportation (Lines 481-493)

When edge crossing is detected (`needsRefresh = true`):

```javascript
// CRITICAL: Suppress animations for instant teleportation
window.chart.update("none");                    // Disable animations
window.chart.data.datasets[0].data = updatedLocations;  // Update positions
window.chart.update("none");                    // Render instantly
```

### Key Technical Features

#### Animation Suppression
- **Method**: `chart.update("none")` bypasses Chart.js smooth animations
- **Effect**: Vehicles appear instantly at opposite edge without visual movement
- **Timing**: Applied specifically when edge crossing occurs, not during normal movement

#### Boundary Buffer Zones
- **Purpose**: Clean detection without edge case flickering
- **Implementation**: Slightly offset from exact boundaries (e.g., `-0.1` instead of `0`)
- **Benefit**: Prevents vehicles from oscillating at exact boundary values

#### Integration with Two-Frame System
- **Compatibility**: Works within existing two-frame-per-block animation system
- **Timing**: Edge detection occurs after normal position updates
- **Scope**: Applied to both interpolation frames (odd `frameIndex`) and regular frames

### Benefits for Terminal Map Implementation

#### Visual Quality
- **Elimination of Streaking**: Prevents vehicles from visually "traveling" across entire map
- **Instant Appearance**: Vehicles appear seamlessly at opposite edge
- **Direction Preservation**: Vehicle orientation maintained during teleportation

#### Performance Characteristics
- **Minimal Overhead**: Edge detection only when boundaries are approached
- **Efficient Updates**: Animation suppression avoids expensive smooth transitions
- **Scalable**: Works regardless of city size or vehicle count

#### User Experience
- **Seamless Wrapping**: Torus topology appears natural and continuous
- **No Visual Artifacts**: Clean transitions without animation glitches
- **Predictable Behavior**: Consistent handling across all edge cases

### Implementation Guidance for Textual Terminal Map

#### Core Pattern to Adopt
```python
# 1. Detect edge crossings after position updates
if needs_edge_wrapping(vehicle_positions):
    # 2. Calculate teleport destinations
    wrapped_positions = calculate_wrapped_positions(vehicle_positions)

    # 3. Suppress animations and update instantly
    update_vehicle_positions_instantly(wrapped_positions)

    # 4. Resume normal animation for subsequent frames
```

#### Critical Requirements
- **Instant Updates**: Use non-animated position changes for edge wrapping
- **Buffer Zones**: Implement boundary detection with slight offsets
- **State Preservation**: Maintain vehicle direction and phase during teleportation
- **Integration**: Ensure compatibility with existing two-frame animation system

This Chart.js pattern provides a proven approach for solving torus wrapping anomalies that can be adapted to the Textual terminal map animation system.

### Trip Marker Timing Fix - September 2025 ✅

**Problem Solved**: Trip origin markers were disappearing one frame (half a simulation step) before vehicles reached intersections, causing visual disconnect in the two-frame animation system.

**Chart.js Solution Applied** (`docs/lab/modules/map.js:434-442`):
- Trip data collection occurs on every frame
- Trip marker display updates occur ONLY on odd frames (`frameIndex % 2 != 0`)
- This synchronizes marker state changes with intersection midpoints

**Implementation** (`ridehail/animation/textual_map.py:720-723`):
```python
# Chart.js pattern: Only update display on odd frames (interpolation points)
if frame_index % 2 != 0:
    # interpolation point: change trip marker location and styles
    self._update_trip_marker_display(trip_data, map_size, h_spacing, v_spacing)
```

**Result**: Trip markers now change state at intersection centers, maintaining visual synchronization with vehicle animations and matching Chart.js behavior exactly.

## Current Status - December 2024 ✅

### Major Migration Completed

**Textual as Default Animation System** - Successfully migrated from Rich-based terminal animations to Textual framework as the primary system:

✅ **Removed -tx Option**: The `use_textual` parameter has been completely removed from configuration and command-line arguments
✅ **Default Terminal Animations**: Both `console` and `terminal_map` now default to their Textual implementations
✅ **Fallback System**: Rich-based animations remain as fallbacks for compatibility
✅ **Frame Timeout Integration**: Proper `frame_timeout` parameter flow maintained for terminal map animations

**Enhanced Progress Bar Colors** - Updated TextualConsoleAnimation with proper vehicle status visualization:

✅ **P1 (Idle)**: Deep sky blue color for both progress bars and labels
✅ **P2 (Dispatched)**: Goldenrod color (enhanced from basic orange)
✅ **P3 (Occupied)**: Lime green color for both progress bars and labels
✅ **Additional Styling**: Enhanced wait time (salmon) and ride time (lime green) colors for better visual distinction

### Current Working Commands

```bash
# Console animation (now defaults to Textual)
python run.py test.config -as console

# Terminal map animation (now defaults to Textual)
python run.py test.config -as terminal_map

# Other animation styles (matplotlib-based)
python run.py test.config -as map
python run.py test.config -as stats
```

### Files Updated in Latest Session

- `ridehail/animation/utils.py`: Removed `use_textual` parameter, made Textual default
- `run.py`: Updated to use simplified animation factory call
- `ridehail/config.py`: Removed `use_textual` configuration parameter and `-tx` flag
- `ridehail/animation/__init__.py`: Updated documentation to reflect Textual as primary
- `ridehail/animation/textual_console.py`: Enhanced progress bar colors and comprehensive styling

### Next Steps: Performance Optimization 🚀

**Upcoming Focus**: Performance optimization questions and improvements for the animation system.

**Key Areas for Optimization**:
- Animation rendering performance for larger city sizes
- Memory usage optimization for long-running simulations
- Frame rate optimization for smoother user experience
- CPU usage reduction during intensive animation sequences
- Terminal compatibility and rendering efficiency improvements

**Architecture Status**:
- Textual migration complete and stable
- Native animation system working with midpoint strategy
- Enhanced visual feedback and color coding implemented
- Ready for performance analysis and optimization phase
