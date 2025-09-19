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