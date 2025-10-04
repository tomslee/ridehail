# Keyboard Input Mechanisms Analysis

## Current State

### 1. Browser/Web Interface (`docs/lab/app.js`)
**Location**: Lines 223-246
**Method**: Single `document.addEventListener("keyup")` event listener
**Keys Supported**:
- `z/Z` - Toggle zoom (show/hide UI elements, adjust chart columns)
- `p/P` - Pause/Resume simulation (triggers FAB button click)
- `s/S` - Single step (when paused)

**Implementation**: Direct DOM manipulation and simulation state updates via web worker messages.

### 2. Desktop Terminal Interface (`ridehail/simulation.py`)
**Location**: Lines 46-230 (`KeyboardHandler` class)
**Method**: Two modes:
- **Non-blocking termios mode**: Uses `select()` to check stdin without blocking (Unix/Linux/macOS)
- **UI event mode**: `handle_ui_action()` method for Textual UI callbacks

**Keys Supported** (termios mode):
- `q` or Ctrl+C - Quit
- `space` - Pause/Resume
- `n/N` - Decrease/Increase vehicles
- `k/K` - Decrease/Increase demand
- `d/D` - Decrease/Increase animation delay
- `h/?` - Show help

**Implementation**:
- `_handle_key()` for direct terminal input
- `handle_ui_action()` for Textual UI bindings
- Both modify `sim.target_state` and `sim.config` directly

### 3. Textual UI (`ridehail/animation/textual_base.py`)
**Location**: Lines 274-460
**Method**: Textual's BINDINGS system + action methods
**Keys Supported**: Same as termios mode (delegated to KeyboardHandler)

**Implementation**:
- BINDINGS list maps keys to action names
- `action_*()` methods call `sim.get_keyboard_handler().handle_ui_action()`
- Fully integrated with central KeyboardHandler

## Key Differences

### Architecture
1. **Browser**: Event-driven JavaScript with direct DOM access
2. **Terminal**: Polling-based with termios raw mode (non-blocking stdin)
3. **Textual**: Event-driven Python framework with bindings declarative system

### State Management
1. **Browser**: State in JavaScript (`appState`), messages to Python worker
2. **Terminal/Textual**: Shared `KeyboardHandler` modifies simulation state directly

### Key Overlap
- **Pause** exists in both (browser: `p`, terminal: `space`)
- **Browser has zoom** - no terminal equivalent (UI-specific)
- **Terminal has vehicle/demand adjustment** - browser uses sliders instead

## Unification Possibilities

### ❌ Not Feasible (High Complexity)
**Full unification across browser and terminal** would require:
- Abstracting JavaScript event system and Python termios/Textual systems
- Creating a platform-agnostic key binding layer
- Bridging fundamentally different execution contexts (browser JS vs. Python process)
- **Complexity Cost**: Very high, minimal benefit

### ✅ Already Unified (Desktop Side)
**Terminal and Textual already share implementation:**
- Both use the same `KeyboardHandler` class
- Textual UI actions delegate to `handle_ui_action()`
- Single source of truth for keyboard behavior on desktop
- **Status**: ✅ Complete unification achieved

### 🤔 Possible Low-Complexity Improvements

#### 1. **Standardize Key Bindings Across Platforms** (Documentation)
Create a single reference document listing all keyboard shortcuts:
- Clearly mark which keys work where (browser-only, terminal-only, both)
- Helps maintain consistency as features are added
- **Complexity**: Very low (documentation only)

#### 2. **Extract Key Mapping Configuration**
Both systems could share a common key mapping definition:

```python
# ridehail/keyboard_mappings.py
KEYBOARD_MAPPINGS = {
    "pause": {"keys": ["space", "p"], "description": "Pause/Resume simulation"},
    "quit": {"keys": ["q"], "description": "Quit simulation"},
    "step": {"keys": ["s"], "description": "Single step (when paused)"},
    "increase_vehicles": {"keys": ["N"], "description": "Increase vehicles +1"},
    "decrease_vehicles": {"keys": ["n"], "description": "Decrease vehicles -1"},
    # ... etc
}
```

This could be:
- Imported by Python KeyboardHandler to configure bindings
- Exported to JSON for browser to import
- Used to auto-generate help text and documentation

**Benefits**:
- Single source of truth for key mappings
- Easier to maintain consistency
- Auto-generate help screens

**Complexity**: Low-medium
- Requires refactoring both systems to use shared config
- But each keeps its own event handling mechanism

#### 3. **Browser-Side Keyboard Handler Class** (Parallel Structure)
Create a JavaScript equivalent of KeyboardHandler:

```javascript
// docs/lab/js/keyboard-handler.js
class KeyboardHandler {
    constructor(app) {
        this.app = app;
        this.setupListeners();
    }

    handleKey(event) {
        const action = this.getActionForKey(event.key);
        if (action) {
            this.executeAction(action);
        }
    }

    // Parallel to Python's handle_ui_action()
    executeAction(action) { /* ... */ }
}
```

**Benefits**:
- Mirrors desktop architecture in browser
- Easier to understand for developers familiar with desktop side
- Centralized keyboard handling logic

**Complexity**: Low
- Refactor existing event listener into class
- Structure matches existing Python code
- No new functionality, just reorganization

## Recommendation

### Implement Option 2 + 3 (Low-Medium Complexity)

**Phase 1: Extract Key Mappings** (1-2 hours)
1. Create `ridehail/keyboard_mappings.py` with canonical key definitions
2. Update `KeyboardHandler` to use these mappings
3. Export to JSON for browser consumption
4. Update help text generation to use mappings

**Phase 2: Browser KeyboardHandler Class** (2-3 hours)
1. Create `docs/lab/js/keyboard-handler.js`
2. Move keyboard event handling from `app.js` into new class
3. Structure to mirror Python KeyboardHandler API
4. Import key mappings from JSON

**Benefits**:
- ✅ Single source of truth for key bindings
- ✅ Consistent architecture across platforms
- ✅ Easier maintenance and feature additions
- ✅ Auto-generated documentation possibilities
- ✅ Low risk (refactoring, not rewriting)

**What NOT to do**:
- ❌ Try to create cross-platform event abstraction layer
- ❌ Unify JavaScript and Python execution contexts
- ❌ Replace working platform-specific mechanisms

## Current Status Summary

**Desktop (Terminal + Textual)**: ✅ Already unified via KeyboardHandler
**Browser**: ❌ Independent implementation, no shared code
**Cross-platform**: ❌ Not unified, but could share key mapping definitions

**Best Path Forward**: Extract key mappings as shared configuration, create parallel KeyboardHandler structure in browser to match desktop architecture.
