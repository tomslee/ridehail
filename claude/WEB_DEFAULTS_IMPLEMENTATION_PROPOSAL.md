# Web Application: Default vs Explicit Value Tracking

## Overview

Implement a system in the web application that parallels the Python configuration behavior: distinguish between "using default value" and "explicitly set value" for simulation parameters.

## Current Architecture Analysis

### JavaScript Layer (`sim-settings.js`)

**Current Behavior**:
```javascript
constructor(scaleConfig = SCALE_CONFIGS.village) {
  this.citySize = scaleConfig.citySize.value;        // Always explicitly set
  this.vehicleCount = scaleConfig.vehicleCount.value; // Always explicitly set
  this.requestRate = scaleConfig.requestRate.value;   // Always explicitly set
  // ... all parameters explicitly initialized
}
```

**Problem**: All values are explicitly set from scale configs, preventing runtime-computed defaults.

### Python Bridge Layer (`worker.py`)

**Current Behavior**:
```python
config.city_size.value = int(web_config["citySize"])          # Explicit
config.vehicle_count.value = int(web_config["vehicleCount"])  # Explicit
config.base_demand.value = float(web_config["requestRate"])   # Explicit (prevents smart default)
# ... all values explicitly set
```

**Problem**: Python config system can't distinguish "user set" from "scale default", preventing smart defaults like `base_demand = vehicle_count / city_size`.

## Proposed Architecture

### Design Principles

1. **Parallel Python Behavior**: Mirror the `explicitly_set` flag system from `ridehail/config.py`
2. **Backward Compatible**: Existing code continues to work without modification
3. **Minimal Changes**: Leverage existing scale config system
4. **Clear Semantics**: `null`/`undefined` means "use default", actual value means "explicitly set"

### Three-State Value System

Each parameter can be in one of three states:
- `null` or `undefined` → Use default (not explicitly set)
- Actual value → Explicitly set by user
- Scale config value → Initially set by scale, but overridable

### Implementation Strategy

#### Phase 1: JavaScript Settings Class Enhancement

**File**: `docs/lab/js/sim-settings.js`

**Add Explicit Tracking**:
```javascript
export class SimSettings {
  constructor(scaleConfig = SCALE_CONFIGS.village, name = "labSimSettings") {
    this.name = name;
    this.scale = scaleConfig.scale;

    // Parameters with smart defaults - initialize as null (use default)
    this._citySize = null;
    this._vehicleCount = null;
    this._requestRate = null;  // Smart default: vehicle_count / city_size
    this._maxTripDistance = null; // Smart default: city_size

    // Parameters with static defaults - initialize with values
    this.minutesPerBlock = 1;
    this.inhomogeneity = scaleConfig.inhomogeneity.value;
    this.price = scaleConfig.price.value;
    // ... other parameters with static defaults

    // Store scale config for default lookups
    this._scaleConfig = scaleConfig;

    // Track which parameters were explicitly set by user
    this._explicitlySet = new Set();
  }

  // Getters/setters with default fallback
  get citySize() {
    return this._citySize !== null
      ? this._citySize
      : this._scaleConfig.citySize.value;
  }

  set citySize(value) {
    this._citySize = value;
    this._explicitlySet.add('citySize');
  }

  get requestRate() {
    if (this._requestRate !== null) {
      return this._requestRate;
    }
    // Smart default: vehicle_count / city_size
    return this.vehicleCount / this.citySize;
  }

  set requestRate(value) {
    this._requestRate = value;
    this._explicitlySet.add('requestRate');
  }

  // Check if parameter was explicitly set
  isExplicitlySet(paramName) {
    return this._explicitlySet.has(paramName);
  }

  // Clear explicit flag (revert to default)
  revertToDefault(paramName) {
    this[`_${paramName}`] = null;
    this._explicitlySet.delete(paramName);
  }

  // Serialize for worker (only include explicitly set values)
  toWorkerConfig() {
    const config = {
      // Always include required parameters
      scale: this.scale,
      name: this.name,
      // ... other always-required params
    };

    // Only include explicitly set parameters
    if (this.isExplicitlySet('citySize')) {
      config.citySize = this.citySize;
    }
    if (this.isExplicitlySet('requestRate')) {
      config.requestRate = this.requestRate;
    }
    // ... etc

    return config;
  }
}
```

#### Phase 2: Python Bridge Modification

**File**: `docs/lab/worker.py`

**Update Config Mapping**:
```python
def __init__(self, settings):
    web_config = settings.to_py()
    config = RideHailConfig(use_config_file=False)

    # Required parameters - always set
    config.city_size.value = int(web_config["citySize"])
    config.vehicle_count.value = int(web_config["vehicleCount"])

    # Optional parameters - only set if present (explicitly set)
    if "requestRate" in web_config:
        config.base_demand.value = float(web_config["requestRate"])
        config.base_demand.explicitly_set = True
    # else: base_demand will use smart default (vehicle_count / city_size)

    if "maxTripDistance" in web_config:
        config.max_trip_distance.value = int(web_config["maxTripDistance"])
        config.max_trip_distance.explicitly_set = True
    # else: max_trip_distance will use smart default (city_size)

    # Static defaults - always set
    config.inhomogeneity.value = float(web_config.get("inhomogeneity", 0.5))
    config.price.value = float(web_config.get("price", 1.2))
    # ... etc
```

#### Phase 3: UI Interaction Enhancement

**File**: `docs/lab/js/input-handlers.js`

**Add "Reset to Default" Functionality**:
```javascript
// Add reset button next to sliders for parameters with smart defaults
function addResetButton(inputElement, paramName) {
  const resetBtn = document.createElement('button');
  resetBtn.className = 'app-button app-button--icon-small';
  resetBtn.innerHTML = '<i class="material-icons">restart_alt</i>';
  resetBtn.title = 'Reset to default';
  resetBtn.onclick = () => {
    appState.labSimSettings.revertToDefault(paramName);
    updateInputDisplay(inputElement, paramName);
  };
  inputElement.parentElement.appendChild(resetBtn);
}

// Visual indicator for default vs explicit values
function updateInputDisplay(inputElement, paramName) {
  const isExplicit = appState.labSimSettings.isExplicitlySet(paramName);
  if (isExplicit) {
    inputElement.classList.add('explicit-value');
    inputElement.classList.remove('default-value');
  } else {
    inputElement.classList.add('default-value');
    inputElement.classList.remove('explicit-value');
  }
}
```

**CSS Styling** (`docs/lab/style.css`):
```css
/* Visual distinction for default vs explicit values */
input.default-value {
  border-left: 3px solid var(--md-sys-color-tertiary);
}

input.explicit-value {
  border-left: 3px solid var(--md-sys-color-primary);
}

.parameter-info {
  font-size: 0.875rem;
  color: var(--md-sys-color-on-surface-variant);
}

.parameter-info.using-default::before {
  content: "Using default: ";
  font-style: italic;
}
```

## Parameters to Track

### Smart Defaults (Initialize as `null`)

These parameters have runtime-computed defaults:

1. **`requestRate` (base_demand)**
   - **Default**: `vehicleCount / citySize`
   - **Description**: Computed from current vehicle/city settings

2. **`maxTripDistance`**
   - **Default**: `citySize`
   - **Description**: Scales with city size

### Static Defaults (Initialize with values)

These parameters have constant defaults that don't depend on other parameters:

- `inhomogeneity`: 0.5
- `price`: 1.2
- `platformCommission`: 0.25
- `reservationWage`: 0.35
- `demandElasticity`: 0.0
- `minutesPerBlock`: 1
- `meanVehicleSpeed`: 30.0
- `pickupTime`: 1
- `equilibrationInterval`: 0
- `smoothingWindow`: 20
- ... etc

## Configuration File Integration

### Download Behavior (`config-file.js`)

When downloading `.config` files:
```javascript
function webToDesktopConfig(labSimSettings) {
  const config = {
    DEFAULT: {},
    ANIMATION: {},
    EQUILIBRATION: {},
    // ...
  };

  // Only write explicitly set parameters
  config.DEFAULT.city_size = labSimSettings.citySize; // Always included
  config.DEFAULT.vehicle_count = labSimSettings.vehicleCount; // Always included

  if (labSimSettings.isExplicitlySet('requestRate')) {
    config.DEFAULT.base_demand = labSimSettings.requestRate;
  } else {
    // Leave empty to use default
    config.DEFAULT.base_demand = '';
  }

  return config;
}
```

### Upload Behavior (`config-file.js`)

When uploading `.config` files:
```javascript
function desktopToWebConfig(parsedINI) {
  const settings = new SimSettings();

  // Required parameters
  settings.citySize = getINIValue(parsedINI, 'DEFAULT', 'city_size');
  settings.vehicleCount = getINIValue(parsedINI, 'DEFAULT', 'vehicle_count');

  // Optional parameters - only set if present and non-empty
  const baseDemand = getINIValue(parsedINI, 'DEFAULT', 'base_demand');
  if (baseDemand !== null && baseDemand !== '') {
    settings.requestRate = baseDemand;
  }
  // else: requestRate stays null, will use default

  return settings;
}
```

## UI Enhancement Ideas

### Visual Feedback

1. **Input Field Styling**:
   - Default values: Subtle tertiary color border
   - Explicit values: Primary color border
   - Tooltip: "Using default: {computed_value}" or "Explicitly set"

2. **Reset Buttons**:
   - Small icon button next to parameters with smart defaults
   - Only visible when value is explicitly set
   - Click to revert to default

3. **Info Icons**:
   - Hover to see current default value and formula
   - "Request rate default: vehicle_count / city_size = 8 / 8 = 1.0"

### Configuration Dialog Enhancement

When displaying uploaded config:
```
Configuration Summary:
- City Size: 32 (explicit)
- Vehicle Count: 64 (explicit)
- Request Rate: 2.0 (default: would be 64/32 = 2.0)
                  ↑ exact match, but still explicit
- Max Trip Distance: (using default: 32)
```

## Migration Path

### Phase 1: Infrastructure (No user-visible changes)
1. Add private `_paramName` properties to `SimSettings`
2. Add `_explicitlySet` Set to track state
3. Implement getters/setters with default fallback
4. Update `worker.py` to handle optional parameters

### Phase 2: Behavior Change (Smart defaults work)
1. Initialize smart default parameters as `null`
2. Update config file upload/download to preserve explicit state
3. Test that Python smart defaults activate correctly

### Phase 3: UI Enhancements (User-facing features)
1. Add visual indicators for default vs explicit
2. Add reset buttons for smart default parameters
3. Add tooltips showing current default values
4. Update documentation

## Benefits

1. **Consistency**: Web and desktop apps behave identically
2. **Flexibility**: Users can rely on smart defaults or override them
3. **Clarity**: Visual distinction between default and explicit values
4. **Maintainability**: Configuration files are cleaner (fewer explicit values)
5. **Correctness**: Smart defaults update automatically when dependencies change

## Testing Strategy

### Unit Tests

```javascript
// Test default behavior
const settings = new SimSettings();
assert(settings.isExplicitlySet('requestRate') === false);
assert(settings.requestRate === settings.vehicleCount / settings.citySize);

// Test explicit setting
settings.requestRate = 5.0;
assert(settings.isExplicitlySet('requestRate') === true);
assert(settings.requestRate === 5.0);

// Test revert to default
settings.revertToDefault('requestRate');
assert(settings.isExplicitlySet('requestRate') === false);
assert(settings.requestRate === settings.vehicleCount / settings.citySize);
```

### Integration Tests

1. **Round-trip test**: Web → Download → Upload → Web
   - Explicit values preserved
   - Default values preserved as defaults

2. **Desktop compatibility**: Web → Download → Desktop → Upload → Web
   - Behavior matches desktop app
   - Smart defaults computed identically

3. **Scale change test**: Change scale, verify defaults update
   - Default parameters adjust to new scale
   - Explicit parameters remain unchanged

## Open Questions

1. **Scale Config Interaction**: When user changes scale (village → town), should explicit values be preserved or reverted to defaults?
   - **Option A**: Preserve explicit values, clamp to new range
   - **Option B**: Revert all to defaults for new scale
   - **Recommendation**: Option A (preserve user intent)

2. **Session Storage**: Should `explicitly_set` state be saved in localStorage?
   - **Recommendation**: Yes, save state as `{value: 5.0, explicit: true}` objects

3. **Mobile UI**: How to show reset buttons on small screens?
   - **Recommendation**: Long-press or swipe gesture to reset

## Implementation Effort Estimate

- **Phase 1 (Infrastructure)**: 4-6 hours
  - `sim-settings.js` refactoring
  - `worker.py` optional parameter handling
  - Unit tests

- **Phase 2 (Behavior)**: 2-3 hours
  - Config file integration
  - Integration tests

- **Phase 3 (UI)**: 4-6 hours
  - Visual indicators
  - Reset buttons
  - Tooltips
  - Documentation

**Total**: 10-15 hours of development work
