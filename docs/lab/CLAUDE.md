# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a **Ridehail Laboratory** - a browser-based interactive simulation system for modeling ridehail (Uber/Lyft-style) transportation systems. The application runs entirely in the browser using Pyodide to execute Python simulation code client-side, with no server component required.

## Architecture

### Core Components

- **Frontend**: Vanilla JavaScript with Material Design Lite UI
- **Simulation Engine**: Python code running via Pyodide WebAssembly
- **Data Flow**: JavaScript ↔ Web Worker ↔ Python simulation

### Key Architecture Patterns

1. **Modular JavaScript Structure**:
   - `app.js` - Main application class and orchestration
   - `js/` - Core utilities (config, DOM elements, input handlers, settings)
   - `modules/` - Feature modules (map.js, stats.js, whatif.js)

2. **Web Worker Pattern**:
   - `webworker.js` - Handles Pyodide initialization and Python execution
   - `worker.py` - Python simulation wrapper for web interface
   - Enables non-blocking simulation execution

3. **Settings Management**:
   - Multiple simulation configurations (lab, baseline, comparison)
   - Scale-based presets (village, town, city)
   - Real-time parameter updates during simulation

4. **Chart System**:
   - Chart.js for statistics visualization
   - Canvas-based map rendering for vehicle/trip visualization
   - Dynamic chart switching between map and statistics views

### Key Files

- `index.html` - Complete single-page application with embedded documentation
- `app.js` - Main App class managing UI state and simulation control
- `worker.py` - Python simulation bridge using ridehail package
- `js/sim-settings.js` - Configuration and settings management
- `modules/whatif.js` - "What If" comparison functionality
- `modules/map.js` - Vehicle and trip visualization
- `modules/stats.js` - Statistical charts and analysis

## Development Workflow

### Running the Application

This is a client-side web application. To run:

1. **Local Development**: Serve the directory with any HTTP server
   ```bash
   # Python 3
   python -m http.server 8000

   # Node.js
   npx serve .

   # Or any other static file server
   ```

2. **Access**: Open `http://localhost:8000` in a web browser

### Key Development Areas

1. **UI Controls**: Sliders, radio buttons, and form inputs in `js/input-handlers.js`
2. **Simulation Parameters**: Scale configurations in `js/config.js`
3. **Visualization**: Chart initialization and updates in `modules/stats.js` and `modules/map.js`
4. **Python Bridge**: Simulation wrapper in `worker.py`

### No Build Process

- This is a vanilla JavaScript application with ES6 modules
- No bundling, compilation, or build steps required
- Dependencies loaded via CDN (Chart.js, Material Design Lite, Pyodide)
- Direct file editing and browser refresh for development

## Simulation System

### Three Tabs/Modes

1. **Experiment Tab**: Interactive simulation with real-time parameter adjustment
2. **What If Tab**: Side-by-side comparison of different scenarios
3. **Read Tab**: Documentation and model explanation

### Vehicle Phases (Core Concept)

- **P1 (Idle)**: Available vehicles driving randomly, waiting for assignment
- **P2 (Dispatched)**: Vehicle assigned to trip, driving to pickup location
- **P3 (With Rider)**: Vehicle carrying passenger to destination

### Key Parameters

- City size (blocks), vehicle count, request rate
- Fare structure (simple fare vs. distance+time components)
- Platform commission, reservation wage
- Entry/exit equilibration for driver economics

## Code Conventions

### JavaScript Style
- ES6 modules with explicit imports/exports
- Functional programming patterns where appropriate
- DOM manipulation through `DOM_ELEMENTS` centralized mapping
- Class-based organization for main App

### Naming Conventions
- camelCase for JavaScript variables and functions
- UPPER_CASE for constants and configuration objects
- Descriptive names reflecting domain concepts (e.g., `vehiclePhases`, `requestRate`)

### State Management
- Global simulation settings objects (`labSimSettings`, `whatIfSimSettingsBaseline`)
- Message passing between main thread and web worker
- UI state synchronized with simulation parameters

## Common Tasks

### Adding New Simulation Parameters

1. Add to scale configurations in `js/config.js`
2. Create UI controls in `index.html`
3. Add input handlers in `js/input-handlers.js`
4. Update `SimSettings` class in `js/sim-settings.js`
5. Modify Python bridge in `worker.py` to pass parameter to simulation

### Adding New Visualizations

1. Create chart initialization function in appropriate module (`modules/stats.js` or `modules/map.js`)
2. Add canvas element to `index.html`
3. Wire up chart switching logic in `app.js`
4. Handle data updates in message handler

### Modifying Simulation Logic

- Core simulation logic lives in separate `ridehail` Python package (not in this repository)
- This repository contains only the web interface wrapper
- Modify `worker.py` to adjust how simulation data is processed for web display

## Dependencies

### External Libraries (CDN)
- Chart.js - Data visualization
- Material Design Lite - UI components
- Pyodide - Python runtime in browser

### Python Dependencies
- `ridehail` package - Core simulation engine (separate repository)
- Standard library modules for data processing

## Material Design Migration

### Migration Overview

**Goal**: Migrate from deprecated Material Design Lite (MDL) to Material Design 3 (Material Web Components)

**Strategy**: Gradual component replacement maintaining existing functionality

**Current Status**: Planning and standardization phase

### Migration Plan

#### Phase 1: Standardization ✅ **COMPLETED**
- **Date**: 2025-09-18
- **Slider standardization**: All 16 form sliders now follow consistent HTML structure
  - Unified CSS classes: `class="mdl-slider mdl-js-slider"`
  - Consistent label attributes: `for="input-*"`
  - Standardized container pattern with help text
- **Benefits**: Template-driven migration approach now possible

#### Phase 2: Foundation Setup (Layout-First Approach)
**CRITICAL**: Layout must be migrated first due to JavaScript dependencies

**Priority Order** (based on dependencies analysis):
1. **Grid System** - Replace `mdl-grid`/`mdl-cell` with modern CSS Grid/Flexbox
   - **Critical dependency**: Zoom functionality toggles `mdl-cell--*-col` classes
   - **JavaScript impact**: `app.js:175-178` must be updated
2. **Layout Structure** - Replace `mdl-layout` with modern layout patterns
3. **Tabs** - Replace `mdl-layout__tab-bar` with Material Design 3 tabs
4. **Header/Navigation** - Update header and navigation structure

#### Phase 3: Component Migration
**Priority Order** (after foundation is stable):
1. **Sliders** (16 components) - High impact, now standardized, contained within layout
2. **Buttons** (FAB, reset, navigation) - Medium complexity
3. **Cards** (control panels, charts) - Medium complexity

#### Phase 4: Testing and Polish
- Cross-browser compatibility testing
- Accessibility improvements
- Performance optimization
- Visual design refinements

### Component Inventory

#### Current MDL Usage (~149 references across 5 files):

**Foundation Level (Migrate First)**:
- **Grid**: `mdl-grid`, `mdl-cell`, `mdl-cell--*-col` (21 references)
  - **JavaScript dependency**: Zoom feature in `app.js:175-178`
- **Layout**: `mdl-layout`, `mdl-layout__header`, `mdl-layout__content`
- **Tabs**: `mdl-layout__tab-bar`, `mdl-layout__tab`, `mdl-layout__tab-panel`
- **Navigation**: `mdl-navigation`, `mdl-layout__header-row`

**Component Level (Migrate After Foundation)**:
- **Form Controls**: `mdl-slider`, `mdl-checkbox`, `mdl-radio`
- **Buttons**: `mdl-button`, `mdl-button--fab`, `mdl-button--mini-fab`
- **Cards**: `mdl-card`, `mdl-card__title`, `mdl-card__supporting-text`

#### Standardized Components:
- ✅ **Sliders**: 16 components with consistent structure ready for template migration
- ⚠️ **Grid Dependencies**: JavaScript code depends on `mdl-cell--*-col` classes for zoom functionality

### Technical Approach

#### Material Web Components Integration
- Use official Material Design 3 web components
- Maintain vanilla JavaScript approach (no framework required)
- Progressive enhancement - replace components incrementally
- Preserve existing event handlers and functionality

#### Migration Template Patterns

**Grid System Migration**:
```html
<!-- MDL Grid (current) -->
<div class="mdl-grid">
  <div class="mdl-cell mdl-cell--6-col">Content</div>
</div>

<!-- Modern CSS Grid (target) -->
<div class="app-grid">
  <div class="app-cell app-cell--6">Content</div>
</div>
```

**Component Migration (after foundation)**:
```html
<!-- MDL Slider (current) -->
<input class="mdl-slider mdl-js-slider" type="range" min="4" max="16" value="8" step="2">

<!-- Material Web Slider (target) -->
<md-slider min="4" max="16" value="8" step="2"></md-slider>
```

### Session Log

#### Session 2025-09-18: Planning and Standardization
- **Completed**:
  - Project assessment and migration scope analysis
  - Comprehensive slider HTML structure audit
  - Standardization of all 16 sliders to consistent pattern
  - Layout dependency analysis and migration order revision
  - Creation of comprehensive migration documentation
- **Benefits Achieved**:
  - Eliminated inconsistencies in form controls
  - Enabled template-driven migration approach
  - Identified critical JavaScript dependencies (zoom functionality)
  - Established layout-first migration strategy
- **Key Discovery**: JavaScript zoom feature depends on MDL grid classes, requiring foundation-first approach
- **Next Steps**: Begin Phase 2 with grid system migration to resolve JavaScript dependencies

### Future Sessions

Each migration session should:
1. **Document progress** in this log
2. **Test functionality** before and after migration
3. **Preserve existing behavior** and event handling
4. **Update any related JavaScript** that references changed classes/elements
5. **Verify accessibility** and responsive design

## Notes

- Simulation runs entirely client-side for privacy and scalability
- No backend server or database required
- Educational/research tool for exploring ridehail system dynamics
- Performance considerations: simulation complexity limited by browser JavaScript/WASM capabilities