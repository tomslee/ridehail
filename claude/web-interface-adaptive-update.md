# Web Interface: Adaptive Equilibration Default Update

**Date**: 2025-11-19
**Status**: Complete ✅

## Summary

Updated the web-based simulation interface (`docs/lab/`) to use automatic adaptive equilibration as the default, matching the Python CLI default.

## Changes Made

### File: `docs/lab/js/sim-settings.js`

**Line 46**: Changed default `equilibrationInterval` from 5 to 0

**Before**:
```javascript
this.equilibrationInterval = 5;
```

**After**:
```javascript
this.equilibrationInterval = 0; // Default: automatic adaptive convergence (Phase 1 & 2)
```

## Impact

### Web Interface Behavior

**Before** (old default):
- Web simulations with equilibration used fixed interval of 5 blocks
- Constant damping factor of 0.5
- No oscillation detection or gain scheduling

**After** (new default):
- Web simulations with equilibration use automatic adaptive mode
- Dynamic interval (3/7/20 blocks based on convergence state)
- Oscillation detection and adaptive damping (Phase 1)
- Gain scheduling for state-dependent control (Phase 2)
- No manual parameter tuning needed

### Data Flow

```
User enables equilibration in web UI
  ↓
SimSettings constructor sets equilibrationInterval = 0 (new default)
  ↓
Settings sent to Web Worker (worker.py)
  ↓
Worker.py passes to Python config: config.equilibration_interval.value = 0
  ↓
Python simulation uses adaptive mode (Phase 1 & 2 features activated)
```

### Consistency with Python CLI

✅ **Now Consistent**:
- Python CLI default: `equilibration_interval = 0` (automatic)
- Web interface default: `equilibrationInterval = 0` (automatic)
- Both platforms provide same default behavior
- Better user experience across interfaces

## User-Facing Changes

### Web Interface Users

**No UI changes**:
- No visible UI control for `equilibrationInterval` in web interface
- Change is transparent - simulations just work better!

**Benefits users will notice**:
- Faster convergence to equilibrium
- No oscillations in vehicle counts
- More stable equilibrium states
- Better results with default settings

### Configuration File Compatibility

**Upload .config files**:
- Files with `equilibration_interval = 5` → Web uses fixed mode (respects config)
- Files with `equilibration_interval = 0` → Web uses adaptive mode (respects config)
- Files without `equilibration_interval` → Web uses default (now 0 = adaptive)

**Download .config files**:
- Downloaded configs will have `equilibration_interval = 0` (new default)
- Compatible with Python CLI (same default)
- Can be edited to use fixed mode if desired

## Testing

### Verification Steps

1. ✅ **Default Simulation**:
   ```
   Open web interface → Enable equilibration → Run simulation
   Result: Uses automatic adaptive mode (equilibrationInterval = 0)
   ```

2. ✅ **Config Upload with Fixed Mode**:
   ```
   Upload .config with equilibration_interval = 5
   Result: Web respects config, uses fixed mode
   ```

3. ✅ **Config Upload with Adaptive Mode**:
   ```
   Upload .config with equilibration_interval = 0
   Result: Web respects config, uses adaptive mode
   ```

4. ✅ **Config Download**:
   ```
   Download config from web interface
   Result: equilibration_interval = 0 in downloaded file
   ```

5. ✅ **Round-Trip Compatibility**:
   ```
   Web → Download .config → Python CLI → Verify same behavior
   Python CLI → .config → Upload to Web → Verify same behavior
   ```

## Files Modified

1. **`docs/lab/js/sim-settings.js`** - Line 46
   - Changed `equilibrationInterval` default from 5 to 0
   - Added comment explaining automatic adaptive convergence

## Files Not Modified (Working Correctly)

1. **`docs/lab/worker.py`**
   - Passes `equilibrationInterval` value to Python config
   - No changes needed - correctly handles any value

2. **`docs/lab/js/config-mapping.js`**
   - Maps `equilibrationInterval` between web and desktop formats
   - No changes needed - mapping works for any value

3. **`docs/lab/index.html`**
   - No UI control for `equilibrationInterval`
   - No changes needed

## Technical Details

### SimSettings Class Hierarchy

**Base Class** (`SimSettings`):
```javascript
constructor() {
  // ...
  this.equilibrationInterval = 0; // ← Changed from 5 to 0
  // ...
}
```

**Derived Class** (`WhatIfSimSettingsDefault`):
- Does NOT override `equilibrationInterval`
- Inherits new default (0) from parent class
- ✅ Automatically uses adaptive mode

### No Breaking Changes

✅ **Backward Compatible**:
- Uploaded configs with explicit values still work
- Fixed mode (>0) still available via config files
- No changes to API or data structures
- No changes to UI or user workflow

## Documentation Updates

**Files Updated**:
1. `claude/adaptive-convergence-management.md` - Notes web interface uses same default
2. `claude/adaptive-convergence-implementation-summary.md` - Web interface section added
3. `claude/web-interface-adaptive-update.md` - **This document** (implementation details)

**Web Interface Documentation** (in `docs/lab/index.html`):
- Read tab already explains equilibration concepts
- No update needed - automatic mode is transparent to users
- Users don't need to know about `equilibrationInterval` parameter

## Benefits

### For Web Interface Users

✅ **Better Default Behavior**:
- Automatic optimal convergence
- No manual tuning needed
- Works well across different city sizes and configurations

✅ **Consistent Cross-Platform**:
- Web and Python CLI have same defaults
- Config files work identically on both platforms
- Documentation applies to both interfaces

### For Developers

✅ **Minimal Code Changes**:
- One-line change in one file
- No UI changes required
- No worker.py changes required
- No breaking changes

✅ **Clean Architecture**:
- Default set in one place (SimSettings constructor)
- Inherited by all derived classes
- Passed through to Python automatically

## Migration Notes

### For Existing Web Users

**No action needed!**

The change is transparent and improves results:
- Existing simulations will just converge better
- No UI changes to learn
- No workflow changes

### For Config File Users

**If you prefer old fixed mode** (rare):
1. Download your config from web interface
2. Edit the file: `equilibration_interval = 5`
3. Upload back to web interface
4. OR use Python CLI with `-ei 5` flag

**Most users**: Just enjoy better convergence!

## Related Changes

This update is part of a coordinated change across the entire ridehail project:

1. ✅ **Python Config** (`ridehail/config.py`) - Default changed to 0
2. ✅ **Python Implementation** (`ridehail/simulation.py`) - Adaptive mode implemented
3. ✅ **Web Interface** (`docs/lab/js/sim-settings.js`) - Default changed to 0 ← This document
4. ✅ **Documentation** (multiple files) - Updated to reflect new default

All components now use automatic adaptive equilibration by default! 🎉

---

**Change Date**: 2025-11-19
**Affected File**: `docs/lab/js/sim-settings.js` (line 46)
**Impact**: Better equilibration convergence in web interface
**Breaking Changes**: None
**Testing**: Complete ✅
