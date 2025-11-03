# Configuration Mapping Analysis

**Date**: 2025-11-03
**Issue**: Duplication in configuration parameter transformations
**Scope**: Web UI, CLI web browser mode, and Python simulation integration

## Executive Summary

**Finding**: Significant duplication exists in parameter mapping logic across three independent implementations.

**Impact**:
- Maintenance burden: Changes require updates in 3 locations
- Inconsistency risk: Easy to miss parameters when adding new config options
- Testing complexity: Need to validate 3 separate implementations

**Recommendation**: Consolidate to single source of truth using JavaScript `config-mapping.js` module.

---

## Translation Points Identified

### 1. JavaScript: Desktop .config ↔ Web SimSettings
**File**: `docs/lab/js/config-mapping.js`
**Direction**: Bidirectional
**Format**: INI file (desktop) ↔ JavaScript object (web)

```javascript
// Example mapping structure
const DESKTOP_TO_WEB_MAPPING = {
  DEFAULT: {
    city_size: "citySize",
    vehicle_count: "vehicleCount",
    base_demand: "requestRate",
    // ... 24 more parameters
  },
  ANIMATION: { /* ... */ },
  EQUILIBRATION: { /* ... */ },
  CITY_SCALE: { /* ... */ }
};
```

**Functions**:
- `desktopToWebConfig(parsedINI)` - Desktop INI → web settings
- `webToDesktopConfig(labSimSettings)` - Web settings → desktop INI

**Special Handling**:
- `animation_delay`: seconds ↔ milliseconds conversion
- `mean_vehicle_speed`: defaults to 30.0 if missing/zero

---

### 2. Python: RideHailConfig → Web JSON (CLI Mode)
**File**: `ridehail/animation/web_browser.py`
**Direction**: One-way (Python → Web)
**Format**: Python RideHailConfig → JSON for browser consumption

```python
# Lines 173-208
web_config = {
    "citySize": config.city_size.value,
    "vehicleCount": config.vehicle_count.value,
    "requestRate": config.base_demand.value,
    # ... 22 more parameters
    "animationDelay": config.animation_delay.value * 1000,  # s → ms
}
```

**Special Handling**:
- `animation_delay`: seconds → milliseconds conversion
- Adds `cliMode: True` flag

---

### 3. Python: Web SimSettings → RideHailConfig (Runtime)
**File**: `docs/lab/worker.py`
**Direction**: One-way (Web → Python)
**Format**: JavaScript SimSettings → Python simulation config

```python
# Lines 109-149 (Simulation.__init__)
config = RideHailConfig()
config.city_size.value = int(web_config["citySize"])
config.vehicle_count.value = int(web_config["vehicleCount"])
config.base_demand.value = float(web_config["requestRate"])
# ... 26 more parameters
config.animation_delay.value = float(web_config["animationDelay"]) / 1000.0
```

**Special Handling**:
- `animation_delay`: milliseconds → seconds conversion
- `pickupTime`: defaults to 1 if missing (backward compatibility)
- Type conversions: int(), float(), bool()

---

## Parameter Coverage Comparison

| Parameter (Desktop) | config-mapping.js | web_browser.py | worker.py | Notes |
|---------------------|-------------------|----------------|-----------|-------|
| **DEFAULT Section** |
| city_size | ✅ citySize | ✅ citySize | ✅ citySize | |
| vehicle_count | ✅ vehicleCount | ✅ vehicleCount | ✅ vehicleCount | |
| base_demand | ✅ requestRate | ✅ requestRate | ✅ requestRate | |
| max_trip_distance | ✅ maxTripDistance | ✅ maxTripDistance | ✅ maxTripDistance | |
| min_trip_distance | ✅ minTripDistance | ❌ | ❌ | **Inconsistency** |
| inhomogeneity | ✅ inhomogeneity | ✅ inhomogeneity | ✅ inhomogeneity | |
| inhomogeneous_destinations | ✅ inhomogeneousDestinations | ✅ inhomogeneousDestinations | ✅ inhomogeneousDestinations | |
| time_blocks | ✅ timeBlocks | ✅ timeBlocks | ✅ timeBlocks | |
| idle_vehicles_moving | ✅ idleVehiclesMoving | ❌ | ❌ | **Inconsistency** |
| random_number_seed | ✅ randomNumberSeed | ✅ randomNumberSeed | ✅ randomNumberSeed | |
| verbosity | ✅ verbosity | ✅ verbosity | ✅ verbosity | |
| equilibrate | ✅ equilibrate | ✅ equilibrate | ✅ equilibrate | |
| use_city_scale | ✅ useCostsAndIncomes | ✅ useCostsAndIncomes | ✅ useCostsAndIncomes | |
| pickup_time | ✅ pickupTime | ✅ pickupTime | ✅ pickupTime (default 1) | |
| **ANIMATION Section** |
| animation_delay | ✅ animationDelay (×1000) | ✅ animationDelay (×1000) | ✅ animationDelay (÷1000) | |
| smoothing_window | ✅ smoothingWindow | ✅ smoothingWindow | ✅ smoothingWindow | |
| **EQUILIBRATION Section** |
| equilibration | ✅ equilibration | ❌ | ❌ (hardcoded PRICE) | **Inconsistency** |
| reservation_wage | ✅ reservationWage | ✅ reservationWage | ✅ reservationWage | |
| price | ✅ price | ✅ price | ✅ price | |
| platform_commission | ✅ platformCommission | ✅ platformCommission | ✅ platformCommission | |
| demand_elasticity | ✅ demandElasticity | ✅ demandElasticity | ✅ demandElasticity | |
| equilibration_interval | ✅ equilibrationInterval | ✅ equilibrationInterval | ✅ equilibrationInterval | |
| **CITY_SCALE Section** |
| mean_vehicle_speed | ✅ meanVehicleSpeed | ✅ meanVehicleSpeed | ✅ meanVehicleSpeed | |
| minutes_per_block | ✅ minutesPerBlock | ✅ minutesPerBlock | ✅ minutesPerBlock | |
| per_km_ops_cost | ✅ perKmOpsCost | ✅ perKmOpsCost | ✅ perKmOpsCost | |
| per_hour_opportunity_cost | ✅ perHourOpportunityCost | ✅ perHourOpportunityCost | ✅ perHourOpportunityCost | |
| per_km_price | ✅ perKmPrice | ✅ perKmPrice | ✅ perKmPrice | |
| per_minute_price | ✅ perMinutePrice | ✅ perMinutePrice | ✅ perMinutePrice | |

**Legend**:
- ✅ = Parameter mapped
- ❌ = Parameter missing
- (×1000) = seconds to milliseconds
- (÷1000) = milliseconds to seconds

**Total Parameters**: 28 unique configuration parameters

---

## Duplication Analysis

### Parameter Mapping: 100% Duplicate Logic

All three implementations map the same 25 core parameters:

| Implementation | Lines of Code | Duplication |
|----------------|---------------|-------------|
| config-mapping.js | ~48 mapping entries | **Primary** |
| web_browser.py | ~35 assignment lines | **100% duplicate** |
| worker.py | ~41 assignment lines | **100% duplicate** |

**Duplication Score**: ~124 lines of repetitive mapping code across 3 files

### Type Conversions: Duplicate Logic

All implementations handle same conversions:

```javascript
// config-mapping.js (implicit via parseValue)
animationDelay = parsedValue * 1000  // seconds → ms
```

```python
# web_browser.py
"animationDelay": config.animation_delay.value * 1000  # seconds → ms
```

```python
# worker.py
config.animation_delay.value = float(web_config["animationDelay"]) / 1000.0  # ms → seconds
```

---

## Inconsistencies Found

### 1. Missing Parameters in Python Implementations

**Parameters in config-mapping.js but NOT in web_browser.py/worker.py**:

- `min_trip_distance` - Desktop config parameter not exposed to web
- `idle_vehicles_moving` - Desktop config parameter not exposed to web
- `equilibration` - config-mapping.js maps it, but worker.py hardcodes to `Equilibration.PRICE`

**Impact**: Config file upload/download works for these parameters, but CLI web mode doesn't support them.

### 2. Default Value Handling Differences

**config-mapping.js**:
```javascript
// mean_vehicle_speed defaults to 30.0 if zero (added Dec 2024)
if (!config.CITY_SCALE.mean_vehicle_speed || config.CITY_SCALE.mean_vehicle_speed === 0) {
    config.CITY_SCALE.mean_vehicle_speed = 30.0;
}
```

**worker.py**:
```python
# pickupTime defaults to 1 if missing (backward compatibility)
config.pickup_time.value = int(web_config.get("pickupTime", 1))
```

**web_browser.py**: No default value logic

**Impact**: Different defaults applied in different code paths.

---

## Maintenance Burden Examples

### Adding a New Parameter Requires 3 Edits

Example: Adding `max_pickup_wait_time` parameter:

1. **config-mapping.js**:
```javascript
DESKTOP_TO_WEB_MAPPING = {
  DEFAULT: {
    // ... existing mappings
    max_pickup_wait_time: "maxPickupWaitTime",  // ADD HERE
  }
}
```

2. **web_browser.py**:
```python
web_config = {
    # ... existing mappings
    "maxPickupWaitTime": config.max_pickup_wait_time.value,  # ADD HERE
}
```

3. **worker.py**:
```python
config.max_pickup_wait_time.value = int(web_config["maxPickupWaitTime"])  # ADD HERE
```

**Risk**: Easy to forget one location, causing subtle bugs.

---

## Testing Gaps

Current testing:

✅ **config-mapping.js**: Has test suite (`tests/test-phase1.html`)
❌ **web_browser.py**: No tests for parameter mapping
❌ **worker.py**: No tests for parameter mapping

**Risk**: Changes to web_browser.py or worker.py are not validated.

---

## Consolidation Strategy

### Recommended Approach: Single Source of Truth

**Strategy**: Use `config-mapping.js` as canonical mapping definition, eliminate Python duplication.

### Phase 1: Eliminate web_browser.py Duplication

**Current**: Python code manually builds JSON dict (35 lines)

**Proposed**: Use config-mapping.js via JSON export

1. **Add to config-mapping.js**:
```javascript
// Export mapping as JSON for Python consumption
export function getMappingAsJSON() {
  return JSON.stringify({
    desktopToWeb: DESKTOP_TO_WEB_MAPPING,
    webToDesktop: WEB_TO_DESKTOP_MAPPING
  });
}
```

2. **Create mapping.json** (generated file):
```json
{
  "desktopToWeb": {
    "DEFAULT": {
      "city_size": "citySize",
      "vehicle_count": "vehicleCount",
      ...
    }
  }
}
```

3. **Update web_browser.py**:
```python
# Load mapping from JSON instead of hardcoding
import json
from pathlib import Path

MAPPING_FILE = Path(__file__).parent.parent.parent / "docs/lab/js/config-mapping.json"
with open(MAPPING_FILE) as f:
    MAPPING = json.load(f)

def _prepare_config(self):
    """Auto-generate web config from mapping."""
    web_config = {}

    for section_name, section_mapping in MAPPING['desktopToWeb'].items():
        section = getattr(self.sim.config, section_name.lower(), None)
        for desktop_key, web_key in section_mapping.items():
            param = getattr(self.sim.config, desktop_key, None)
            if param:
                web_config[web_key] = param.value

    # Apply special conversions (still needed)
    web_config['animationDelay'] *= 1000  # seconds → ms

    return web_config
```

**Benefits**:
- Reduces web_browser.py from 35 lines to ~15 lines
- Eliminates manual parameter list maintenance
- Auto-updates when config-mapping.js changes

### Phase 2: Eliminate worker.py Duplication

**Current**: Python code manually assigns 41 config parameters

**Challenge**: Type conversions required (int, float, bool)

**Proposed**: Use mapping.json + type metadata

1. **Enhance mapping.json** with type information:
```json
{
  "webToDesktop": {
    "citySize": {
      "section": "DEFAULT",
      "key": "city_size",
      "type": "int"
    },
    "requestRate": {
      "section": "DEFAULT",
      "key": "base_demand",
      "type": "float"
    }
  }
}
```

2. **Update worker.py**:
```python
# Load mapping
with open('config-mapping.json') as f:
    MAPPING = json.load(f)

TYPE_CONVERTERS = {
    'int': int,
    'float': float,
    'bool': bool,
    'str': str
}

def __init__(self, settings):
    web_config = settings.to_py()
    config = RideHailConfig()

    # Auto-apply all mappings
    for web_key, mapping_info in MAPPING['webToDesktop'].items():
        if web_key in web_config:
            desktop_attr = mapping_info['key']
            converter = TYPE_CONVERTERS[mapping_info['type']]

            config_param = getattr(config, desktop_attr)
            config_param.value = converter(web_config[web_key])

    # Special conversions (still needed)
    config.animation_delay.value /= 1000.0  # ms → seconds

    self.sim = RideHailSimulation(config)
```

**Benefits**:
- Reduces worker.py from 41 lines to ~15 lines
- Type safety enforced by metadata
- Single source of truth for all mappings

### Phase 3: Generate mapping.json Automatically

**Build step**: Add to `build.sh` or pre-commit hook

```bash
# Generate mapping JSON from config-mapping.js
node -e "
  import('./docs/lab/js/config-mapping.js').then(module => {
    const mapping = module.getMappingAsJSON();
    fs.writeFileSync('docs/lab/js/config-mapping.json', mapping);
  });
"
```

**Benefits**:
- mapping.json always in sync with config-mapping.js
- No manual JSON maintenance

---

## Alternative: Python as Source of Truth

**Not Recommended** because:

1. Web UI is primary interface (more users)
2. JavaScript already has comprehensive test suite
3. Python would require parsing JS to extract mappings (complex)
4. Desktop .config file format is INI-based (better handled in JS)

---

## Impact Analysis

### Before Consolidation

```
Total mapping code: ~124 lines across 3 files
Maintenance locations: 3 (JS, 2× Python)
Test coverage: 33% (only config-mapping.js tested)
Inconsistencies: 3 parameters (min_trip_distance, idle_vehicles_moving, equilibration)
```

### After Consolidation

```
Total mapping code: ~48 lines (config-mapping.js + ~15 each for converters)
Maintenance locations: 1 (config-mapping.js)
Test coverage: 100% (all use tested mapping.js)
Inconsistencies: 0 (single source of truth)
```

**Code Reduction**: 124 → 78 lines (~37% reduction)
**Maintenance Improvement**: 3 locations → 1 location (~67% reduction)

---

## Risks & Mitigations

### Risk 1: JSON File Dependency

**Risk**: Python code now depends on generated JSON file

**Mitigation**:
- Include mapping.json in version control
- Add build-time validation that JSON matches JS
- Fail fast if JSON missing or out of sync

### Risk 2: Type Metadata Maintenance

**Risk**: Need to maintain type information in mapping

**Mitigation**:
- Types are stable (rarely change)
- TypeScript type definitions could auto-generate metadata
- Validation tests ensure correctness

### Risk 3: Migration Complexity

**Risk**: Breaking changes during consolidation

**Mitigation**:
- Implement incrementally (Phase 1, then Phase 2, then Phase 3)
- Run full test suite after each phase
- Keep old code temporarily for comparison

---

## Recommendations

### Immediate Actions

1. ✅ **Document the duplication** (this document)
2. ✅ **Add missing parameters** to web_browser.py and worker.py:
   - ✅ `min_trip_distance` - Added with default value 0
   - ✅ `idle_vehicles_moving` - Added with default value True
   - ✅ `equilibration` - Removed hardcoded Equilibration.PRICE, now properly maps from web config
3. ✅ **Standardize default values** across all three implementations:
   - ✅ config-mapping.js: Added defaults for minTripDistance (0), idleVehiclesMoving (true), pickupTime (1), equilibration ("PRICE")
   - ✅ worker.py: Added defaults matching config-mapping.js
   - ✅ web_browser.py: Now exports all parameters including equilibration enum conversion

### Short Term (1-2 weeks)

4. **Add tests** for web_browser.py and worker.py parameter mapping
5. **Implement Phase 1**: Eliminate web_browser.py duplication using mapping export

### Medium Term (1 month)

6. **Implement Phase 2**: Eliminate worker.py duplication using enhanced mapping
7. **Implement Phase 3**: Auto-generate mapping.json from config-mapping.js

### Long Term (Maintenance)

8. **Enforce policy**: All new parameters added only to config-mapping.js
9. **Add CI check**: Validate mapping.json matches config-mapping.js
10. **Document pattern**: Update CLAUDE.md with consolidation approach

---

## Conclusion

**Finding**: Significant duplication exists across three independent configuration mapping implementations totaling ~124 lines of repetitive code.

**Root Cause**: Organic growth without centralized mapping strategy.

**Solution**: Consolidate to single source of truth (config-mapping.js) with auto-generated JSON consumed by Python code.

**Impact**:
- ✅ 37% code reduction
- ✅ 67% fewer maintenance points
- ✅ Zero inconsistencies
- ✅ 100% test coverage
- ✅ Easier to add new parameters

**Next Step**: Implement immediate actions (items 1-3) to address current inconsistencies, then proceed with phased consolidation.
