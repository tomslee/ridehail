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

1. **Local Development**: Build and serve the directory with any HTTP server
   ```bash
   # Build the wheel and manifest
   cd ../..  # Back to project root
   ./build.sh

   # Serve the lab directory
   cd docs/lab
   python -m http.server 8000

   # Or any other static file server
   ```

2. **Access**: Open `http://localhost:8000` in a web browser

### Deployment Process

**GitHub Pages deployment is fully automated via GitHub Actions:**

1. Push changes to `master` branch
2. GitHub Actions workflow (`.github/workflows/deploy-pages.yml`) automatically:
   - Builds the ridehail wheel using `build.sh`
   - Creates `manifest.json` with version info
   - Deploys `docs/lab/` directory to GitHub Pages
3. Site available at https://tomslee.github.io/ridehail/lab/

**Important Notes:**
- Wheel files (`*.whl`) and `manifest.json` are **NOT committed** to the repository
- They are build artifacts created during GitHub Actions deployment
- `docs/lab/dist/` directory is gitignored (built by CI/CD only)
- No manual steps needed for deployment—just push to master

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

#### Session 2025-09-18: Foundation and Slider Migration
- **Completed Phase 2: Foundation Setup** ✅
  - **Grid System Migration**: Replaced MDL grid with modern CSS Grid
  - **Layout Structure Migration**: Migrated from `mdl-layout` to modern layout patterns
  - **Tab Migration**: Implemented Material Design 3 compliant tabs
  - **Header/Navigation Migration**: Updated to MD3 standards with accessibility
- **Completed Phase 3.1: Slider Component Migration** ✅
  - **HTML Structure**: Replaced all 16 MDL sliders with MD3 slider structure
  - **CSS Implementation**: Added comprehensive MD3 slider styling with states, animations, and cross-browser support
  - **JavaScript Integration**: Added initialization function and visual state management
  - **Event Handling**: Maintained existing input handlers and functionality
  - **Color Fix**: Replaced undefined MD3 color variables with actual teal theme colors
  - **Double-thumb Fix**: Removed custom thumb divs to use only native browser slider thumbs
- **Benefits Achieved**:
  - Complete foundation migration enables incremental component updates
  - Modern, accessible slider components with Material Design 3 styling
  - Improved visual feedback and interaction states
  - Cross-browser compatibility with webkit and firefox support
- **Next Steps**: Complete Phase 3 by migrating remaining form controls (buttons, checkboxes)

### Future Sessions

Each migration session should:
1. **Document progress** in this log
2. **Test functionality** before and after migration
3. **Preserve existing behavior** and event handling
4. **Update any related JavaScript** that references changed classes/elements
5. **Verify accessibility** and responsive design

## Configuration File Upload/Download Implementation Plan - December 2024

### Overview
Enable users to save/load experiment configurations in desktop-compatible `.config` file format (INI-style) for cross-platform workflow support.

### Goals
- **Download**: Export current web lab settings as `.config` file compatible with desktop interface
- **Upload**: Import desktop `.config` files into web lab, automatically inferring appropriate scale preset
- **Compatibility**: Exact format match with desktop `.config` files (INI with sections)
- **Scale Handling**: Automatically infer scale (village/town/city) from loaded parameter values, clamp out-of-range values

### Implementation Steps

#### **Phase 1: Core Infrastructure** ✅ Planning

**Step 1.1: Create INI Parser/Generator Module**
- **File**: `docs/lab/js/config-file.js`
- **Functions**:
  - `parseINI(fileContent)` - Parse INI format to object with sections
  - `generateINI(sections)` - Convert object to INI string format
  - Handle comments (lines starting with `#`)
  - Handle section headers (`[SECTION_NAME]`)
  - Handle key-value pairs with proper type inference
- **Test**: Create sample config strings and verify round-trip parsing

**Step 1.2: Create Parameter Mapping Module**
- **File**: `docs/lab/js/config-mapping.js`
- **Functions**:
  - `webToDesktopConfig(labSimSettings)` - Map web settings → desktop config sections
  - `desktopToWebConfig(parsedINI)` - Map desktop config sections → web settings
- **Mapping Tables**:
  ```javascript
  const PARAM_MAPPING = {
    DEFAULT: {
      city_size: 'citySize',
      vehicle_count: 'vehicleCount',
      base_demand: 'requestRate',
      // ... complete mapping
    },
    EQUILIBRATION: { /* ... */ },
    ANIMATION: { /* ... */ },
    CITY_SCALE: { /* ... */ }
  };
  ```
- **Test**: Map sample settings back and forth, verify no data loss

**Step 1.3: Scale Inference Logic**
- **File**: `docs/lab/js/scale-inference.js`
- **Functions**:
  - `inferScaleFromSettings(settings)` - Determine best-fit scale preset
  - `isWithinRange(settings, scaleConfig)` - Check if parameters fit scale ranges
  - `clampToScale(settings, scaleConfig)` - Adjust out-of-range values, return warnings
- **Logic**:
  1. Check if all parameters fit within village ranges → return 'village'
  2. Else check town ranges → return 'town'
  3. Else return 'city'
  4. For any out-of-range values, clamp to nearest valid range and collect warnings
- **Test**: Test various parameter combinations, verify correct scale inference

#### **Phase 2: Download Functionality**

**Step 2.1: Add Download UI**
- **File**: `docs/lab/index.html`
- **Location**: Add to top controls bar after "Mode" control
- **HTML**:
  ```html
  <div class="top-control">
    <div class="top-control__label">Configuration</div>
    <button class="app-button app-button--toolbar-icon" id="download-config" title="Download configuration">
      <i class="material-icons">download</i>
    </button>
  </div>
  ```
- **Test**: Verify button appears and is styled correctly

**Step 2.2: Implement Download Logic**
- **File**: `docs/lab/app.js`
- **Function**: `downloadConfiguration()`
- **Steps**:
  1. Get current `appState.labSimSettings`
  2. Convert to desktop config format using `webToDesktopConfig()`
  3. Generate INI string using `generateINI()`
  4. Create blob and download with filename `ridehail_lab_YYYYMMDD_HHMMSS.config`
- **Test**: Download config, verify format matches desktop `.config` files exactly

**Step 2.3: Verify Desktop Compatibility**
- **Test**: Load downloaded `.config` file in desktop app (`python run.py downloaded.config`)
- **Verify**: All parameters transferred correctly, simulation runs as expected

#### **Phase 3: Upload Functionality**

**Step 3.1: Add Upload UI**
- **File**: `docs/lab/index.html`
- **Location**: Next to download button in top controls
- **HTML**:
  ```html
  <label for="upload-config" class="app-button app-button--toolbar-icon" title="Upload configuration">
    <i class="material-icons">upload</i>
    <input type="file" id="upload-config" accept=".config" hidden>
  </label>
  ```
- **Test**: Verify upload icon appears, file picker opens on click

**Step 3.2: Implement File Reading**
- **File**: `docs/lab/app.js`
- **Function**: `handleConfigUpload(event)`
- **Steps**:
  1. Read file as text using FileReader API
  2. Parse INI format using `parseINI()`
  3. Convert to web settings using `desktopToWebConfig()`
  4. Pass to confirmation dialog
- **Test**: Upload test config, verify parsing succeeds

**Step 3.3: Create Confirmation Dialog**
- **File**: `docs/lab/index.html` + `docs/lab/style.css`
- **Component**: Modal dialog showing:
  - Configuration summary (key parameters)
  - Inferred scale preset
  - Any warnings (clamped values)
  - Confirm/Cancel buttons
- **HTML Structure**:
  ```html
  <div id="config-confirm-dialog" class="app-dialog" hidden>
    <div class="app-dialog__overlay"></div>
    <div class="app-dialog__content">
      <h3>Load Configuration?</h3>
      <div id="config-summary"></div>
      <div id="config-warnings"></div>
      <div class="app-dialog__actions">
        <button class="app-button app-button--toolbar">Cancel</button>
        <button class="app-button app-button--toolbar app-button--toolbar-primary">Load Configuration</button>
      </div>
    </div>
  </div>
  ```
- **Test**: Show dialog with sample data, verify styling and interactivity

**Step 3.4: Implement Configuration Application**
- **File**: `docs/lab/app.js`
- **Function**: `applyUploadedConfig(settings, inferredScale, warnings)`
- **Steps**:
  1. Infer scale and clamp values using `inferScaleFromSettings()` and `clampToScale()`
  2. Show confirmation dialog with summary
  3. On confirm:
     - Update scale radio button (triggers range updates)
     - Update all UI controls (sliders, inputs, checkboxes)
     - Update `appState.labSimSettings`
     - Reset simulation state
     - Show success toast with inferred scale
  4. On cancel: discard loaded settings
- **Test**: Apply config, verify all UI controls update correctly

**Step 3.5: Handle Edge Cases**
- **Scenarios to test**:
  - Missing parameters → use current values or defaults
  - Invalid values (non-numeric) → show error, don't apply
  - Empty file → show error message
  - Very large values → clamp and warn
  - Mixed simple/advanced mode parameters → detect and set mode correctly
- **Test**: Upload various malformed configs, verify graceful error handling

#### **Phase 4: Integration & Polish**

**Step 4.1: Add Visual Feedback**
- **File**: `docs/lab/js/toast.js` (new) + `docs/lab/style.css`
- **Component**: Toast notification system
- **Messages**:
  - "Configuration downloaded: ridehail_lab_[timestamp].config"
  - "Configuration loaded. Scale: [VILLAGE/TOWN/CITY]"
  - "Configuration loaded with adjustments: [list warnings]"
  - "Error loading configuration: [error message]"
- **Test**: Trigger all message types, verify appearance and auto-dismiss

**Step 4.2: DOM Elements Registration**
- **File**: `docs/lab/js/dom-elements.js`
- **Add**:
  ```javascript
  configControls: {
    downloadButton: document.getElementById('download-config'),
    uploadButton: document.getElementById('upload-config'),
    uploadInput: document.getElementById('upload-config'),
    confirmDialog: document.getElementById('config-confirm-dialog'),
    // ... dialog elements
  }
  ```
- **Test**: Verify all elements accessible via DOM_ELEMENTS

**Step 4.3: Event Handler Registration**
- **File**: `docs/lab/app.js` - in constructor
- **Add**:
  ```javascript
  DOM_ELEMENTS.configControls.downloadButton.addEventListener('click', () => {
    this.downloadConfiguration();
  });

  DOM_ELEMENTS.configControls.uploadInput.addEventListener('change', (e) => {
    this.handleConfigUpload(e);
  });
  ```
- **Test**: Click handlers fire correctly, no console errors

**Step 4.4: Complete Desktop Round-Trip Test**
- **Test Scenario 1**: Desktop → Web → Desktop
  1. Create config in desktop app
  2. Upload to web lab
  3. Modify parameters in web
  4. Download config
  5. Run in desktop app
  6. Verify: Same results

- **Test Scenario 2**: Web → Desktop → Web
  1. Configure in web lab (various scales)
  2. Download config
  3. Run in desktop app
  4. Upload same config back to web
  5. Verify: UI matches original state

**Step 4.5: Documentation**
- **File**: `docs/lab/index.html` - Read tab
- **Add section**: "Configuration Files"
  - Explain upload/download feature
  - Describe desktop compatibility
  - Note scale inference behavior
  - List any parameters not supported in web interface
- **Test**: Review documentation for clarity

#### **Phase 5: Advanced Features (Optional)**

**Step 5.1: Configuration Library**
- Store multiple configs in browser localStorage
- Quick load from saved configurations
- Share configs via URL parameters

**Step 5.2: Partial Config Import**
- Allow selective parameter import
- Merge with existing settings rather than replace

**Step 5.3: Config Validation UI**
- Show detailed validation results before applying
- Highlight which parameters will change

### Testing Checklist

**Unit Tests:**
- ✅ INI parser handles all format variations
- ✅ Parameter mapping bidirectional without data loss
- ✅ Scale inference correct for all parameter combinations
- ✅ Clamping logic produces valid values

**Integration Tests:**
- ✅ Download produces valid desktop-compatible files
- ✅ Upload reads desktop configs correctly
- ✅ UI updates reflect loaded configuration
- ✅ Simulation runs with loaded parameters

**Desktop Compatibility:**
- ✅ Round-trip: desktop → web → desktop preserves settings
- ✅ All parameter types handled (int, float, bool, enum)
- ✅ Section structure matches exactly

**Edge Cases:**
- ✅ Out-of-range values clamped with warnings
- ✅ Missing parameters handled gracefully
- ✅ Invalid file format shows error
- ✅ Large files handled efficiently

**User Experience:**
- ✅ Clear visual feedback for all actions
- ✅ Confirmation before overwriting settings
- ✅ Informative error messages
- ✅ Intuitive button placement and icons

### Session Log

_Document progress and discoveries here as implementation proceeds_

#### Session 2024-12-XX: Phase 1 - Core Infrastructure ✅

- **Completed**:
  - ✅ **Step 1.1**: Created INI parser/generator module (`js/config-file.js`)
    - `parseINI()` - Parses INI format with sections, comments, key-value pairs
    - `generateINI()` - Generates INI format from object structure
    - `parseValue()` - Type inference (string, number, boolean, null)
    - `getINIValue()` - Safe value extraction with defaults
  - ✅ **Step 1.2**: Created parameter mapping module (`js/config-mapping.js`)
    - `DESKTOP_TO_WEB_MAPPING` - Complete mapping tables for all parameters
    - `desktopToWebConfig()` - Desktop INI → web SimSettings conversion
    - `webToDesktopConfig()` - Web SimSettings → desktop INI conversion
    - `validateDesktopConfig()` - Config validation with errors/warnings
    - Special handling: animation_delay unit conversion (seconds ↔ milliseconds)
  - ✅ **Step 1.3**: Created scale inference module (`js/scale-inference.js`)
    - `inferScaleFromSettings()` - Automatic scale detection (village/town/city)
    - `isWithinRange()` - Check if parameters fit scale ranges
    - `clampToScale()` - Adjust out-of-range values with warnings
    - `inferAndClampSettings()` - Combined inference and clamping
    - `getConfigSummary()` - Format summary for display
  - ✅ **Testing**: Created comprehensive test files
    - `tests/test-config-file.html` - INI parser unit tests (8 tests)
    - `tests/test-phase1.html` - Integration tests (10 tests covering full workflow)

- **Discovered**:
  - Round-trip conversion (web → desktop → web) preserves all parameter values
  - Scale inference successfully identifies smallest scale that accommodates all parameters
  - Clamping system provides detailed warnings for adjusted values
  - Boolean values handled correctly: `True/False` (Python) ↔ `true/false` (JavaScript)
  - Empty INI values (`key =`) correctly parsed as empty strings

- **Next Steps**:
  - Phase 2: Download Functionality (3 steps)
  - Phase 3: Upload Functionality (5 steps)
  - Phase 4: Integration & Polish (5 steps)

#### Session 2024-12-XX: Phase 2 - Download Functionality ✅

- **Completed**:
  - ✅ **Step 2.1**: Added download UI button
    - Added Configuration control to top controls bar in `index.html`
    - Download icon button with Material Icons
    - Registered in `dom-elements.js` as `configControls.downloadButton`
  - ✅ **Step 2.2**: Implemented download logic
    - Created `downloadConfiguration()` method in `app.js`
    - Imports config-file and config-mapping modules
    - Converts web settings to desktop format using `webToDesktopConfig()`
    - Generates INI string using `generateINI()`
    - Creates timestamped filename: `ridehail_lab_YYYY-MM-DD_HH-MM-SS.config`
    - Downloads as blob with proper MIME type
    - Wired up click handler in `setupButtonHandlers()`
  - ✅ **Step 2.3**: Ready for desktop compatibility testing

- **Implementation Details**:
  - Timestamp format: ISO 8601 with colons replaced by dashes for filename safety
  - Blob download uses standard browser File API
  - Console logging for debugging
  - Clean URL revocation to prevent memory leaks

- **Testing Ready**:
  - Download button appears in top controls
  - Clicking triggers config file download
  - File format matches desktop `.config` structure
  - Ready for Step 2.3: Load downloaded file in desktop app to verify compatibility

- **Testing Results** ✅:
  - Downloaded config successfully tested with desktop app
  - **Issue Found & Fixed**: `mean_vehicle_speed` was 0 in web scale configs, causing desktop validation to fail
  - **Solution**: Added default value handling in `webToDesktopConfig()` - defaults to 30.0 km/h if 0 or missing
  - Desktop compatibility confirmed: Web → Desktop works correctly

- **Next Steps**:
  - Proceed to Phase 3: Upload Functionality

#### Session 2024-12-XX: Phase 3 - Upload Functionality ✅

- **Completed**:
  - ✅ **Step 3.1**: Added upload UI button
    - Upload icon button next to download button in Configuration control
    - Hidden file input with `.config` file filter
    - Wrapped buttons in `.app-button-group` for visual grouping
  - ✅ **Step 3.2**: Implemented file reading
    - `handleConfigUpload()` method reads file using FileReader API
    - Parses INI format with `parseINI()`
    - Validates config with `validateDesktopConfig()`
    - Converts to web settings with `desktopToWebConfig()`
    - Infers scale and clamps values with `inferAndClampSettings()`
    - Error handling for invalid files
  - ✅ **Step 3.3**: Created confirmation dialog
    - Modal dialog with overlay (`app-dialog` component)
    - Configuration summary shows: scale, city size, vehicle count, request rate, equilibrate, mode
    - Warnings section displays any clamped values in yellow alert box
    - Confirm/Cancel buttons
    - Complete CSS styling for modal, overlay, summary, warnings
  - ✅ **Step 3.4**: Implemented configuration application
    - `applyUploadedConfig()` applies settings on confirmation
    - Updates scale radio and triggers range updates
    - Updates UI mode radio (Simple/Advanced)
    - Updates equilibrate checkbox
    - Updates all slider values and displays
    - Resets simulation with new settings
    - Hides dialog after application
  - ✅ **Step 3.5**: Edge case handling
    - File validation catches invalid configs
    - Missing parameters handled gracefully
    - Out-of-range values clamped with warnings
    - File input reset allows re-upload of same file
    - Overlay click dismisses dialog

- **Implementation Details**:
  - **Modal Dialog**: Fixed position, centered, semi-transparent overlay, z-index 1000
  - **Summary Display**: Definition list format with key parameters
  - **Warning System**: Yellow alert box with list of adjustments
  - **Scale Inference**: Automatically selects village/town/city based on parameter ranges
  - **UI Synchronization**: All controls update to reflect loaded configuration
  - **Event Handlers**: Upload change, confirm click, cancel click, overlay click

- **Files Modified**:
  - `index.html` - Upload button, confirmation dialog HTML
  - `style.css` - Button group, modal dialog styles
  - `js/dom-elements.js` - Registered upload controls and dialog elements
  - `app.js` - Upload handling, dialog display, config application, UI updates

- **Testing Ready**:
  - Upload button appears next to download button
  - File picker accepts .config files
  - Confirmation dialog shows config summary and warnings
  - Config applies correctly on confirmation
  - All UI controls update to match loaded config

- **Next Steps**:
  - Test upload with various config files (desktop configs, downloaded configs)
  - Verify round-trip: Web → Download → Upload → Web
  - Proceed to Phase 4: Integration & Polish

## Session Persistence - December 2024 ✅

**Status**: Implemented and functional

**Overview**: Browser localStorage-based automatic session persistence that saves and restores user configuration between visits.

### Features

- **Automatic Saving**: Settings saved to localStorage whenever they change
- **Automatic Restoration**: Previous session restored on page load
- **No Sign-In Required**: Pure client-side persistence using browser storage
- **Complements Download/Upload**: Works alongside .config file download/upload for more permanent records

### Implementation

**Files**:
- `js/session-storage.js` - Core localStorage persistence module
- `app.js` - Integration with App class (save/restore methods)
- `js/input-handlers.js` - Auto-save triggers on input changes

**Saved Data**:
- All simulation parameters (city size, vehicle count, request rate, fares, costs, etc.)
- UI state (scale: village/town/city, mode: simple/advanced, chart type: map/stats)
- Last saved timestamp

**Key Functions**:
- `saveLabSettings(settings)` - Save simulation settings to localStorage
- `saveUIState(uiState)` - Save UI state (scale, mode, chart type)
- `loadLabSettings()` - Load saved settings
- `loadUIState()` - Load saved UI state
- `hasSavedSession()` - Check if saved data exists
- `clearSessionData()` - Clear all saved data

### Behavior

**On Parameter Change**:
- Any slider/input change triggers `updateLabSimSettings()` → auto-saves to localStorage
- Scale/mode/chart type changes trigger `saveSessionSettings()` → saves both settings and UI state
- Equilibrate checkbox change triggers save via `updateSettings` callback

**On Page Load**:
- `restoreSession()` checks for saved data via `hasSavedSession()`
- If found, restores settings and UI state
- Updates all UI controls to match restored values
- Shows "Previous session restored" toast notification
- If not found, uses default scale (village) configuration

**Error Handling**:
- Gracefully handles localStorage unavailable (incognito mode, browser settings)
- Catches and logs parse errors if saved data is corrupted
- Falls back to defaults if restoration fails

### Privacy & Limitations

**Privacy**:
- All data stored locally in browser localStorage
- No server communication for session data
- Data never leaves user's device
- Cleared when user clears browser data

**Limitations**:
- Tied to specific browser and device
- Cleared if user clears browser data
- Not shared across devices/browsers
- For more permanent/portable records, use download/upload .config files

### Future Enhancements (Optional)

- Export/import session data between browsers via URL parameters
- Multiple saved "profiles" that user can name and switch between
- Session expiration (auto-clear old sessions)
- Sync across devices via optional cloud storage (requires sign-in)

## Notes

- Simulation runs entirely client-side for privacy and scalability
- No backend server or database required
- Educational/research tool for exploring ridehail system dynamics
- Performance considerations: simulation complexity limited by browser JavaScript/WASM capabilities
- Session persistence uses localStorage for automatic state preservation between visits