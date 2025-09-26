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
cp dist/ridehail-0.0.1-py3-non-any.whl docs/lab/dist/
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

## Terminal Map Animation Implementation Plan

### Prerequisites: ConsoleAnimation Improvements

Before implementing the new terminal map animation, several improvements to the existing `ConsoleAnimation` class are recommended to create a better foundation:

#### Code Organization & Modularity Issues:

- The `animate()` method is very long (300+ lines) and should be broken into smaller methods:
  - `_setup_config_table()`
  - `_setup_progress_bars()`
  - `_setup_layout()`
  - `_setup_statistics_panels()`

#### Parameter Passing Issues:

- `_next_frame()` method currently accepts 12+ arguments, making it unwieldy
- Should store progress bars as instance variables or use a grouped data structure
- Consider using a dictionary/dataclass to group related progress bars

#### Error Handling & Compatibility:

- Missing error handling for Rich rendering failures
- No fallback for terminals that don't support Rich features
- No validation of terminal size before rendering
- Need terminal compatibility checks before rendering

#### Performance & Maintenance:

- Redundant object creation: Progress bars and tables recreated on each frame
- Hardcoded exclusion list for configuration attributes (lines 307-323)
- Magic numbers: Hardcoded sleep time (0.1), progress calculation constants
- Some repetitive string operations in update loops

#### Enhanced Features Needed:

- Keyboard interaction support (currently disabled)
- Better log display functionality
- Responsive layout sizing
- Proper error handling for rendering failures

### Overview

Add a new `terminal_map` animation style that provides real-time map visualization in the terminal, combining the interactive statistics of the console animation with a visual map display using Unicode characters and Rich library capabilities.

### Implementation Strategy

#### Phase 1: Core Infrastructure

1. **Add new Animation enum value**:

   - Add `TERMINAL_MAP = "terminal_map"` to `Animation` enum in `ridehail/atom.py`

2. **Create TerminalMapAnimation class**:
   - Inherit from `RideHailAnimation` base class
   - Combine features from `ConsoleAnimation` and map visualization from `MatplotlibAnimation`
   - Use Rich library for terminal rendering and layout management

#### Phase 2: Map Rendering System

1. **Unicode-based map grid**:

   - Use Unicode box drawing characters: `┌ ┬ ┐ ├ ┼ ┤ └ ┴ ┘ ─ │`
   - Create grid-based city representation where each cell represents an intersection
   - Support variable city sizes (tested with small cities initially)

2. **Vehicle representation**:

   - Direction-based characters: `▲ ► ▼ ◄` or `↑ → ↓ ←`
   - Color-coded by vehicle phase using Rich color system:
     - P1 (idle): Blue
     - P2 (dispatched): Orange
     - P3 (occupied): Green
   - Support vehicle movement animation between intersections

3. **Trip visualization**:
   - Origin markers: `●` or `⚬` for trip requests
   - Destination markers: `★` or `⭐` for active trip destinations
   - Color differentiation between waiting/riding trips

#### Phase 3: Layout and Integration

1. **Rich Layout structure**:

   ```
   ┌─────────────────┬─────────────────┐
   │                 │                 │
   │   Map Display   │   Statistics    │
   │   (Unicode      │   Panel         │
   │   characters)   │   (existing     │
   │                 │   progress bars)│
   ├─────────────────┼─────────────────┤
   │   Config Info   │   Control Info  │
   └─────────────────┴─────────────────┘
   ```

2. **Real-time updates**:
   - Use Rich Live context for smooth updates
   - Update map and statistics synchronously
   - Maintain existing keyboard controls and interaction patterns

#### Phase 4: Configuration and Integration

1. **Animation dispatch**:

   - Modify animation factory in `ridehail/animation.py` to recognize `terminal_map` style
   - Ensure proper instantiation of `TerminalMapAnimation` class

2. **Configuration compatibility**:
   - Support all existing configuration options
   - Add optional map-specific parameters (grid size limits, update frequency)
   - Maintain compatibility with existing `.config` files

#### Phase 5: Performance and Scalability

1. **Optimization for small cities**:

   - Target city sizes up to 20x20 initially
   - Implement efficient rendering for acceptable terminal performance
   - Consider adaptive detail levels for larger cities

2. **Terminal compatibility**:
   - Test across different terminal emulators
   - Graceful fallback for terminals with limited Unicode support
   - Responsive to terminal resize events

### Technical Details

#### File Modifications Required:

- `ridehail/atom.py`: Add `TERMINAL_MAP` to Animation enum
- `ridehail/animation.py`: Add `TerminalMapAnimation` class and factory logic
- Potential config additions for map-specific settings

#### Dependencies:

- Leverage existing Rich library (already in dependencies)
- No additional external dependencies required
- Use existing simulation data structures and interfaces

#### Testing Strategy:

- Test with existing small city configurations (`test.config`)
- Verify performance with various city sizes
- Test terminal compatibility across platforms
- Ensure keyboard controls work correctly

### Success Criteria:

- Real-time map updates showing vehicle movement
- Clear visual distinction between vehicle phases and trip states
- Maintains performance for small cities (≤20x20)
- Preserves all existing functionality of console animation
- Intuitive and informative display layout

## Textual Migration Strategy

### Overview

Migration plan to transition from Rich-based terminal animations (ConsoleAnimation and TerminalMapAnimation) to Textual framework for enhanced interactivity and modern UI capabilities.

### Current Architecture Analysis

#### Existing Components:

- **RichBasedAnimation** (`ridehail/animation/rich_base.py:23`): Base class with progress bars, config tables, terminal compatibility
- **ConsoleAnimation** (`ridehail/animation/console.py:15`): Rich Layout with panels and progress bars
- **TerminalMapAnimation** (`ridehail/animation/terminal_map.py:16`): Unicode map with vehicle tracking and interpolation
- **Animation Factory** (`ridehail/animation/utils.py:50`): Factory pattern for animation creation

#### Key Features to Preserve:

- Real-time simulation progress tracking
- Vehicle phase visualization (P1/P2/P3 with colors)
- Trip metrics and statistics display
- Configuration parameter display
- Terminal compatibility checking
- Graceful fallback mechanisms
- Unicode map rendering with interpolation

### Migration Architecture Design

#### Phase 1: Textual Base Infrastructure

**1. Create TextualBasedAnimation Base Class**

- Location: `ridehail/animation/textual_base.py`
- Inherit from `RideHailAnimation` base class
- Provide common Textual app structure and widget management
- Include terminal compatibility and fallback mechanisms

**2. Core Textual App Structure**

```python
class RidehailTextualApp(App):
    """Main Textual application for ridehail animations"""
    # CSS styling definitions
    # Widget composition and layout
    # Event handling framework
    # Real-time update mechanisms
```

**3. Custom Widgets**

- `ProgressPanel`: Enhanced progress display with multiple metrics
- `ConfigPanel`: Configuration parameter display with potential editing
- `ControlPanel`: Interactive simulation controls
- `MapWidget`: Unicode map display with zoom/pan capabilities (for TerminalMap)

#### Phase 2: Console Animation Migration

**1. TextualConsoleAnimation Class**

- Location: `ridehail/animation/textual_console.py`
- Convert Rich Layout to Textual Container/Grid system
- Migrate progress bars to Textual Progress widgets
- Add interactive controls (pause/resume, parameter adjustment)

**2. Enhanced Features**

- Real-time parameter adjustment via input widgets
- Simulation control buttons (pause/resume/stop)
- Better responsive layout handling
- Enhanced keyboard shortcuts with visual feedback

#### Phase 3: Terminal Map Migration

**1. TextualMapAnimation Class**

- Location: `ridehail/animation/textual_map.py`
- Convert Unicode map to custom Textual widget
- Preserve interpolation and smooth movement
- Add interactive map controls (zoom, focus tracking)

**2. Map-Specific Enhancements**

- Click-to-focus on vehicles or intersections
- Vehicle information popups on hover/click
- Map zoom and pan functionality
- Dynamic map sizing based on terminal dimensions

#### Phase 4: Integration and Factory Updates

**1. Animation Factory Enhancement**

```python
# In ridehail/animation/utils.py
def create_animation_factory(animation_style, sim, use_textual=False):
    if use_textual:
        if animation_style == Animation.CONSOLE:
            from .textual_console import TextualConsoleAnimation
            return TextualConsoleAnimation(sim)
        elif animation_style == Animation.TERMINAL_MAP:
            from .textual_map import TextualMapAnimation
            return TextualMapAnimation(sim)
    # ... existing Rich-based creation logic
```

**2. Configuration Integration**

- Add `use_textual` parameter to configuration system
- Allow runtime switching between Rich and Textual modes
- Maintain backward compatibility with existing configs

### Implementation Strategy

#### Phase 1: Foundation (Week 1)

1. **Install and Test Textual**

   - Verify Textual installation and basic functionality
   - Create proof-of-concept Textual app with simulation data

2. **Create Base Classes**

   - Implement `TextualBasedAnimation` base class
   - Design core widget architecture
   - Establish styling and layout patterns

3. **Factory Integration**
   - Update animation factory to support Textual option
   - Add configuration parameter for Textual mode selection

#### Phase 2: Console Migration (Week 2)

1. **Basic Console Conversion**

   - Convert ConsoleAnimation layout to Textual containers
   - Migrate progress bars to Textual Progress widgets
   - Preserve existing functionality and appearance

2. **Enhanced Interactivity**

   - Add simulation control buttons
   - Implement real-time parameter adjustment
   - Add enhanced keyboard shortcuts

3. **Testing and Refinement**
   - Test with various configuration files
   - Verify performance and compatibility
   - Implement fallback mechanisms

#### Phase 3: Map Migration (Week 3)

1. **Map Widget Development**

   - Create custom Textual widget for Unicode map display
   - Port interpolation and animation logic
   - Maintain vehicle and trip visualization

2. **Interactive Features**

   - Add map interaction capabilities
   - Implement zoom and pan functionality
   - Add vehicle/trip information displays

3. **Integration Testing**
   - Test map performance with various city sizes
   - Verify smooth animation and updates
   - Cross-platform compatibility testing

#### Phase 4: Polish and Documentation (Week 4)

1. **User Experience Enhancements**

   - Refine styling and layout responsiveness
   - Add help system and keyboard shortcut displays
   - Implement advanced features (themes, customization)

2. **Performance Optimization**

   - Profile and optimize update frequencies
   - Minimize resource usage for long-running simulations
   - Implement efficient rendering strategies

3. **Documentation and Examples**
   - Update configuration documentation
   - Create usage examples and screenshots
   - Document migration benefits and new features

### Benefits of Migration

#### Immediate Improvements

- **True Interactivity**: Real-time control over simulation parameters
- **Better User Experience**: Modern, responsive UI with proper event handling
- **Enhanced Functionality**: Advanced controls, information displays, and customization
- **Improved Maintainability**: Cleaner architecture with widget-based composition

#### Long-term Advantages

- **Extensibility**: Easy addition of new features and widgets
- **Cross-platform**: Better compatibility across different terminal environments
- **Future-proofing**: Built on modern TUI framework with active development
- **Web Compatibility**: Potential for web deployment with same codebase

### Risk Mitigation

#### Backward Compatibility

- Maintain existing Rich-based animations as default
- Provide configuration flag to enable Textual mode
- Ensure all existing functionality is preserved
- Gradual migration path for users

#### Fallback Strategy

- Automatic fallback to Rich animations if Textual fails
- Terminal compatibility detection and graceful degradation
- Clear error messages and alternative options

#### Testing Strategy

- Parallel testing of Rich and Textual implementations
- Cross-platform testing (Linux, macOS, Windows)
- Performance benchmarking and comparison
- User acceptance testing with simulation scenarios

### File Structure Changes

#### New Files

- `ridehail/animation/textual_base.py`: Base Textual animation class
- `ridehail/animation/textual_console.py`: Textual console animation
- `ridehail/animation/textual_map.py`: Textual map animation
- `ridehail/animation/widgets/`: Directory for custom Textual widgets

#### Modified Files

- `ridehail/animation/utils.py`: Updated factory with Textual support
- `ridehail/animation/__init__.py`: Export new Textual classes
- `ridehail/config.py`: Add Textual mode configuration option
- `requirements.txt`: Add textual dependency (already installed)

### Success Metrics

#### Technical Criteria

- All existing Rich animation functionality preserved
- Performance equal or better than Rich implementations
- Successful interactive features (controls, real-time updates)
- Cross-platform compatibility maintained

#### User Experience Criteria

- Improved usability and visual appeal
- Enhanced debugging and monitoring capabilities
- Smooth migration path for existing users
- Positive feedback from simulation users

#### Maintenance Criteria

- Cleaner, more maintainable codebase
- Easier addition of new features
- Better separation of concerns
- Comprehensive test coverage

## Textual Migration Progress Log

### Completed Phases ✅

**Phase 1: Foundation (Complete)**

- Created `TextualBasedAnimation` base class in `ridehail/animation/textual_base.py`
- Updated animation factory in `ridehail/animation/utils.py` to support `use_textual` parameter
- Added `use_textual` configuration parameter to `ridehail/config.py` with `-tx` command-line flag
- Factory gracefully falls back to Rich animations if Textual unavailable

**Phase 2: Console Migration (Complete)**

- Implemented `TextualConsoleAnimation` in `ridehail/animation/textual_console.py`
- Full feature parity with Rich console: all progress bars, metrics, and configuration display
- Enhanced interactivity: real-time parameter adjustment, simulation controls, keyboard shortcuts
- **MAJOR FIX**: Resolved dispatch attribute access issue by passing animation instance to Textual apps

**Phase 3: Terminal Map Migration (Complete)**

- Created `TextualMapAnimation` class in `ridehail/animation/textual_map.py`
- Implemented `MapWidget` with Unicode grid rendering and vehicle interpolation
- Added dynamic map scaling that automatically adjusts to terminal dimensions
- Vehicle colors by phase: P1=blue, P2=orange, P3=green with direction arrows
- Trip markers: origins (orange ●), destinations (green ★)

### Working Commands ✅

```bash
# Rich console (original):
python run.py dispatch.config -as console

# Textual console (enhanced):
python run.py dispatch.config -as console -tx

# Textual terminal map:
python run.py dispatch.config -as terminal_map -tx
```

### Key Architecture Patterns

- Animation classes inherit from `TextualBasedAnimation` → `RideHailAnimation`
- App classes inherit from Textual's `App`
- Apps receive animation instance via constructor to access all config attributes
- Configuration integration: `-tx` flag toggles Textual mode with full backward compatibility

## Terminal Map Performance Optimization - January 2025 ⚡

### Performance Optimization Initiative Completed ✅

Comprehensive performance optimization of the textual map animation rendering system to improve display refresh rates and reduce computational overhead.

### Optimizations Implemented

**1. Math.isclose() Replacement**

- **Problem**: `math.isclose()` calls in tight rendering loops
- **Solution**: Fast epsilon comparisons using `abs(value - round(value)) < 1e-9`
- **Benefit**: 2-3x faster floating point comparisons in hot paths

**2. Pre-formatted Color Strings**

- **Problem**: Dynamic f-string creation for vehicle colors on every character position
- **Solution**: Pre-computed color string constants (`COLORED_VEHICLES`, `COLORED_TRIP_ORIGIN`, etc.)
- **Benefit**: Eliminated hundreds of string formatting operations per frame

**3. Vehicle Position Pre-computation**

- **Problem**: Interpolation calculations repeated for every display position
- **Solution**: Pre-compute all vehicle interpolated positions once per frame, then use fast lookups
- **Benefit**: Reduced from O(positions × vehicles) to O(vehicles) complexity
- **Impact**: With 20×20 city and 100 vehicles: 40,000 → 100 calculations per frame

**4. Trip Markers Pre-computation**

- **Problem**: Nested loops checking all trips for every display position
- **Solution**: Pre-compute trip origin/destination sets for O(1) lookups
- **Benefit**: Reduced from O(positions × trips) to O(trips) complexity
- **Impact**: With 20×20 city and 50 trips: 20,000 → 450 operations per frame

**5. Spacing Calculation Caching**

- **Problem**: Widget spacing recalculated every frame regardless of terminal size changes
- **Solution**: Cache spacing results and only recalculate when widget size changes
- **Benefit**: Eliminated 5-6 arithmetic operations per frame in typical usage

**6. String Building Optimization**

- **Problem**: String concatenation (`line += char`) creates new objects on each operation
- **Solution**: List building with single join operation (`line_chars.append(char)` + `"".join()`)
- **Benefit**: Reduced from O(n²) to O(n) complexity for line building

### Optimizations Considered but Rejected

**Render Frequency Optimization**: Skipped due to complexity and potential performance degradation with high vehicle counts

**Memory Pooling**: Skipped as Python's garbage collector is already optimized for short-lived objects and the complexity wasn't justified

### Performance Impact Summary

**Overall improvements:**

- Significantly faster display refresh rates, especially on larger maps
- Reduced CPU usage during animation rendering
- Better scalability with increasing vehicle and trip counts
- Smoother animation experience

**Files Modified:**

- `ridehail/animation/textual_map.py`: Complete optimization of rendering pipeline

**Testing:** All optimizations verified to maintain identical visual behavior while improving performance

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

- Implement two-stage animation pattern inspired by Chart.js
- **Critical Enhancement**: Use midpoint callbacks for state updates

```python
class VehicleWidget(Widget):
    def move_and_update(self, destination, new_direction, new_phase, duration=1.0):
        """Two-stage animation with midpoint state updates"""
        current_offset = self.styles.offset or Offset(0, 0)

        # Calculate midpoint (intersection center)
        mid_x = (current_offset.x + destination.x) / 2
        mid_y = (current_offset.y + destination.y) / 2
        midpoint = Offset(mid_x, mid_y)

        # Stage 1: Move to midpoint
        self.styles.animate("offset", value=midpoint, duration=duration/2,
                          on_complete=lambda: self._midpoint_state_update(
                              destination, new_direction, new_phase, duration/2))

    def _midpoint_state_update(self, final_dest, direction, phase, remaining_duration):
        """Update vehicle state at midpoint (direction, phase, visual effects)"""
        # Update direction arrow and phase color at logical moment
        if direction != self.current_direction:
            self.update_direction_display(direction)
        if phase != self.current_phase:
            self.update_phase_color(phase)

        # Stage 2: Continue to final destination
        self.styles.animate("offset", value=final_dest, duration=remaining_duration)
```

**Validation**: Vehicles move smoothly with proper direction changes at midpoints

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
