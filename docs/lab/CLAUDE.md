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

## Notes

- Simulation runs entirely client-side for privacy and scalability
- No backend server or database required
- Educational/research tool for exploring ridehail system dynamics
- Performance considerations: simulation complexity limited by browser JavaScript/WASM capabilities