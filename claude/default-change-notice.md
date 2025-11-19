# Default Behavior Change: Automatic Adaptive Equilibration

**Date**: 2025-11-19
**Impact**: Low (backward compatible)
**Type**: Configuration default change

## What Changed

The default value of `equilibration_interval` changed from **5** to **0**.

### Before (old default):
```ini
[EQUILIBRATION]
equilibration = price
# equilibration_interval not set → defaulted to 5 (fixed mode)
```

### After (new default):
```ini
[EQUILIBRATION]
equilibration = price
# equilibration_interval not set → defaults to 0 (automatic mode)
```

## Why This Change?

Automatic adaptive convergence provides better results in most scenarios:
- ✅ **Faster convergence** - Automatically finds optimal damping
- ✅ **No oscillations** - Detects and corrects oscillatory behavior
- ✅ **No manual tuning** - Adapts to different configurations
- ✅ **Better equilibrium** - Gain scheduling prevents overshooting

After implementing and testing Phases 1 & 2, we're confident automatic mode should be the default.

## Impact on Existing Configurations

### Minimal Impact - Fully Backward Compatible

**Configs with explicit `equilibration_interval` value**:
- ✅ No change - continue working exactly as before
- Example: `equilibration_interval = 5` → Still uses fixed mode

**Configs with empty/default `equilibration_interval`**:
- 🔄 Now use automatic mode instead of fixed interval 5
- ✅ Better convergence behavior (upgrade!)
- ⚠️ If you want old behavior: Add `equilibration_interval = 5`

## Migration Guide

### No Action Needed (Recommended)

Most users should **do nothing** and enjoy better convergence:
```bash
# Just run your existing configs - automatic mode is better!
python -m ridehail your_config.config -eq price
```

### To Keep Old Fixed Mode (Optional)

If you prefer the traditional fixed interval mode:

**Option 1: Update config file**
```ini
[EQUILIBRATION]
equilibration = price
equilibration_interval = 5  # Explicit fixed mode
```

**Option 2: Command line override**
```bash
python -m ridehail your_config.config -eq price -ei 5
```

## Testing the Change

### Test Automatic Mode (New Default)
```bash
# Create a simple config without equilibration_interval
cat > test_auto.config << EOF
[DEFAULT]
city_size = 16
vehicle_count = 20
base_demand = 1.5
time_blocks = 200

[EQUILIBRATION]
equilibration = price
# No equilibration_interval → uses automatic mode
EOF

# Run it
python -m ridehail test_auto.config
```

### Test Fixed Mode (Override)
```bash
# Same config, but force fixed mode
python -m ridehail test_auto.config -ei 5
```

### Compare Results
- Automatic mode typically converges faster
- Automatic mode shows no sustained oscillations
- Automatic mode adapts damping based on convergence state

## Technical Details

### What Automatic Mode Does

When `equilibration_interval = 0` (now default):

1. **Dynamic Interval Adjustment**
   - 3 blocks when far from equilibrium
   - 7 blocks during transition
   - 20 blocks when converged

2. **Oscillation Detection** (Phase 1)
   - Monitors sign changes in vehicle adjustments
   - Increases damping when oscillations detected
   - Decreases damping when convergence improving

3. **Gain Scheduling** (Phase 2)
   - 0.2× damping when converged (conservative)
   - 1.5× damping when far from equilibrium (aggressive)
   - 1.0× damping during transition (balanced)

### What Fixed Mode Does

When `equilibration_interval = 5` (or any positive value):

- Updates every N blocks (fixed interval)
- Uses constant damping factor (0.5)
- No automatic adjustment
- Traditional behavior

## Rollback Instructions

If you experience issues with automatic mode:

### Temporary Rollback (Command Line)
```bash
# Override to fixed mode for this run
python -m ridehail your_config.config -ei 5
```

### Permanent Rollback (Config File)
```ini
[EQUILIBRATION]
equilibration = price
equilibration_interval = 5  # Back to old default behavior
```

### Report Issues

If automatic mode doesn't work well for your use case:
1. Try adjusting other equilibration parameters first
2. Test with fixed mode to compare
3. Report the issue with your configuration

## Benefits of the New Default

### For New Users
- ✅ Better out-of-box experience
- ✅ No need to understand damping factors
- ✅ Works across different city sizes
- ✅ No manual parameter tuning

### For Existing Users
- ✅ Can keep old behavior with one line change
- ✅ Optional upgrade to better convergence
- ✅ No breaking changes to code or APIs
- ✅ Easy to test both modes

## Summary

| Aspect | Old Default (5) | New Default (0) |
|--------|-----------------|-----------------|
| Mode | Fixed interval | Automatic adaptive |
| Interval | Every 5 blocks | Dynamic (3/7/20) |
| Damping | Constant (0.5) | Adaptive |
| Oscillations | Possible | Detected & corrected |
| Tuning needed | Sometimes | No |
| Override? | N/A | `-ei 5` |

## Questions?

- **Documentation**: See `claude/adaptive-convergence-management.md`
- **Implementation**: See `claude/adaptive-convergence-implementation-summary.md`
- **Phase 2 Details**: See `claude/phase-2-gain-scheduling-summary.md`

---

**Change Date**: 2025-11-19
**Affected File**: `ridehail/config.py` (line 920: `default=0`)
**Impact**: Better convergence for most users, fully backward compatible
**Recommendation**: Accept new default unless you have specific reasons to use fixed mode
