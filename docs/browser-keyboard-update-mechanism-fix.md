# Browser Keyboard Update Mechanism Fix - December 2024

## Problem Summary

Browser keyboard shortcuts (n/N for vehicle count, k/K for demand) were resetting the simulation to block 0 instead of incrementally updating the running simulation like the desktop version and slider controls do.

## Root Cause

The keyboard handlers in `docs/lab/js/keyboard-handler.js` were calling `this.app.resetLabUIAndSimulation()`, which:
1. Sets `action = SimulationActions.Reset`
2. Triggers `init_simulation()` in worker.py
3. Creates an entirely new `Simulation` object
4. Loses all simulation progress (resets to block 0)

This differed from:
- **Desktop behavior**: Uses `target_state` dictionary for incremental updates
- **Browser slider behavior**: Uses `SimulationActions.Update` → `update_options()` → sets `target_state`

## Solution Implemented

Changed keyboard handlers to use `this.app.updateSimulationOptions(SimulationActions.Update)` instead of `resetLabUIAndSimulation()`.

### Files Modified

**docs/lab/js/keyboard-handler.js** (4 methods):
- `_handleDecreaseVehicles()` - line 195
- `_handleIncreaseVehicles()` - line 216
- `_handleDecreaseDemand()` - line 237
- `_handleIncreaseDemand()` - line 258

**docs/browser-keyboard-extensions-implemented.md**:
- Updated documentation to reflect incremental update behavior
- Changed "Full simulation reset" to "Incremental update via `target_state` mechanism"

### How It Works Now

```javascript
// Before (incorrect):
this.app.resetLabUIAndSimulation();
// → Reset action → init_simulation() → new Simulation object

// After (correct):
this.app.updateSimulationOptions(SimulationActions.Update);
// → Update action → update_options() → sets target_state → _init_block() applies changes
```

## Update Flow

1. **Keyboard shortcut pressed** (e.g., 'n' to decrease vehicles)
2. **Handler updates UI** (slider value, display text, appState)
3. **Update action sent**: `this.app.updateSimulationOptions(SimulationActions.Update)`
4. **Worker receives Update action**: `webworker.js` calls `updateSimulation()`
5. **worker.py sets target_state**: `update_options()` sets `self.sim.target_state["vehicle_count"]`
6. **Next simulation step applies**: `_init_block()` in `ridehail/simulation.py` applies target_state
7. **Incremental vehicle adjustment**: Lines 1159-1172 add/remove vehicles as needed
8. **Simulation continues**: Progress preserved, block counter continues

## Behavior Comparison

| Aspect | Desktop | Browser (Slider) | Browser (Keyboard - Before) | Browser (Keyboard - After) |
|--------|---------|------------------|----------------------------|---------------------------|
| Mechanism | target_state | target_state | **Reset** | target_state ✅ |
| Vehicle handling | Incremental | Incremental | **Full recreation** | Incremental ✅ |
| Simulation progress | Preserved | Preserved | **Lost** | Preserved ✅ |
| Block counter | Continues | Continues | **Resets to 0** | Continues ✅ |

## Benefits

1. **Consistency**: Keyboard shortcuts now behave identically to slider controls
2. **Preserves Progress**: Simulation continues from current block, doesn't reset to 0
3. **Desktop Parity**: Browser keyboard behavior matches desktop keyboard behavior
4. **Smooth UX**: No jarring reset when adjusting parameters mid-simulation
5. **Incremental Updates**: Vehicles added/removed intelligently, trips adjusted properly

## Testing

Test that keyboard shortcuts preserve simulation progress:

1. Start simulation in browser lab
2. Let it run for several blocks (e.g., block 20+)
3. Press 'N' to increase vehicles
4. **Expected**: Block counter continues, vehicle count increases, simulation keeps running
5. **Before fix**: Block counter reset to 0, simulation restarted
6. **After fix**: Block counter continues (e.g., 21, 22, 23...), simulation preserved ✅

## Related Code References

- `ridehail/simulation.py:1087-1108` - Desktop target_state application in `_init_block()`
- `ridehail/simulation.py:1159-1172` - Desktop incremental vehicle add/remove logic
- `docs/lab/worker.py:177-189` - Browser `update_options()` sets target_state
- `docs/lab/webworker.js:233-234` - Update action handler
- `docs/lab/app.js:890-893` - `updateSimulationOptions()` method
- `docs/lab/js/input-handlers.js:49` - Slider handlers use Update action (reference implementation)

## Implementation Date

December 2024
