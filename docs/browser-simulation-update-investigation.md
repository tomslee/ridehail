# Browser Simulation Update Mechanism Investigation - December 2024

## Investigation Request

Examine how updated values (e.g., vehicle count from keyboard shortcuts) get passed to a running simulation in the web version, specifically looking at the mechanism in `ridehail/simulation.py` around line 1112 in `_init_block()` and after.

## Key Question

Does the browser version properly use the same `target_state` mechanism as the desktop version for incremental parameter updates?

## Answer: Yes and No

The browser **does have** the `target_state` mechanism implemented, but keyboard shortcuts were **not using it correctly**.

## Desktop Mechanism (Reference Implementation)

### Flow
```
KeyboardHandler (simulation.py:138-166)
  ↓ Sets self.sim.target_state["vehicle_count"]
  ↓
simulation.next_block()
  ↓ Calls _init_block()
  ↓
_init_block() (lines 1087-1108)
  ↓ Applies target_state: setattr(self, attr, self.target_state[attr])
  ↓
Vehicle count handling (lines 1159-1172)
  ↓ If count increased: Add new Vehicle objects
  ↓ If count decreased: Call _remove_vehicles()
  ↓
Simulation continues with updated vehicle count
```

### Code References

**ridehail/simulation.py:1087-1108** - target_state application:
```python
def _init_block(self, block):
    # Apply target_state values
    for attr in self.__dict__.keys():
        if (isinstance(self.__dict__[attr], (int, float, str, bool))
            or attr not in self.target_state.keys()):
            continue
        if val != self.target_state[attr]:
            setattr(self, attr, self.target_state[attr])
```

**ridehail/simulation.py:1159-1172** - Incremental vehicle adjustment:
```python
if not self.equilibrate or self.equilibration == Equilibration.NONE:
    old_vehicle_count = len(self.vehicles)
    vehicle_diff = self.vehicle_count - old_vehicle_count
    if vehicle_diff > 0:
        for d in range(vehicle_diff):
            self.vehicles.append(Vehicle(...))
    elif vehicle_diff < 0:
        removed_vehicles = self._remove_vehicles(-vehicle_diff)
```

## Browser Mechanisms (Two Paths)

### Path 1: Slider Controls (Correct - Uses target_state)

```
Input handler (input-handlers.js:49)
  ↓ Updates appState.labSimSettings.vehicleCount
  ↓ Calls updateSimulation(SimulationActions.Update)
  ↓
webworker.js (line 233-234)
  ↓ Receives Update action
  ↓ Calls updateSimulation(simSettings)
  ↓
worker.py:update_options() (lines 177-189)
  ↓ Sets self.sim.target_state["vehicle_count"]
  ↓
Next simulation step
  ↓ Calls sim.next_block() → _init_block()
  ↓ Applies target_state (same as desktop)
  ↓
Simulation continues with updated count
```

**worker.py:177-189** - Browser update_options:
```python
def update_options(self, message_from_ui):
    options = message_from_ui.to_py()
    self.sim.target_state["vehicle_count"] = int(options["vehicleCount"])
    self.sim.target_state["base_demand"] = float(options["requestRate"])
    # ... other parameters
```

### Path 2: Keyboard Shortcuts (Incorrect - Was Using Reset)

**Before Fix:**
```
KeyboardHandler (keyboard-handler.js:195)
  ↓ Updates appState.labSimSettings.vehicleCount
  ↓ Calls this.app.resetLabUIAndSimulation()  ← WRONG
  ↓
app.js:resetLabUIAndSimulation()
  ↓ Sets action = SimulationActions.Reset
  ↓
webworker.js (line 247-250)
  ↓ Receives Reset action
  ↓ Calls resetSimulation() → init_simulation()
  ↓
worker.py:init_simulation() (line 10-13)
  ↓ Creates NEW Simulation object ← PROBLEM
  ↓
Simulation resets to block 0 (all progress lost)
```

**After Fix:**
```
KeyboardHandler (keyboard-handler.js:195)
  ↓ Updates appState.labSimSettings.vehicleCount
  ↓ Calls this.app.updateSimulationOptions(SimulationActions.Update)  ← FIXED
  ↓
Same flow as sliders (Path 1 above)
  ↓
Simulation continues with updated count ✅
```

## Investigation Findings

### What Was Discovered

1. **Browser HAS target_state mechanism**: Fully implemented in `worker.py:update_options()` (lines 177-189)
2. **Sliders USE target_state correctly**: Input handlers call `updateSimulation(SimulationActions.Update)`
3. **Keyboard shortcuts DID NOT use target_state**: They called `resetLabUIAndSimulation()` instead
4. **Reset action creates new simulation**: Completely discards running simulation, resets to block 0
5. **Update action uses target_state**: Incremental changes, preserves simulation progress

### Code Evidence

**webworker.js shows both paths:**
```javascript
// Update action (correct path)
} else if (simSettings.action == SimulationActions.Update) {
    updateSimulation(simSettings);  // → update_options() → target_state

// Reset action (wrong path for keyboard)
} else if (simSettings.action == SimulationActions.Reset ||
           simSettings.action == SimulationActions.Done) {
    resetSimulation(simSettings);   // → init_simulation() → new object
```

### Comparison Table

| Component | Desktop | Browser (Slider) | Browser (Keyboard Before) | Browser (Keyboard After) |
|-----------|---------|------------------|--------------------------|-------------------------|
| Update mechanism | target_state | target_state | Reset (new object) | target_state ✅ |
| Code path | KeyboardHandler → target_state | Input handler → Update → update_options | KeyboardHandler → Reset → init_simulation | KeyboardHandler → Update → update_options ✅ |
| Vehicle handling | Incremental add/remove | Incremental add/remove | Full recreation | Incremental add/remove ✅ |
| Simulation state | Continues (preserves block) | Continues (preserves block) | Resets (block → 0) | Continues (preserves block) ✅ |
| Progress preservation | Yes | Yes | No | Yes ✅ |

## Root Cause

The keyboard handlers were implemented to call `resetLabUIAndSimulation()`, which was designed for UI reset scenarios (like changing city size), not for incremental parameter updates. The method name itself suggests "reset" behavior.

The correct method `updateSimulationOptions()` existed and was used by slider controls, but keyboard handlers weren't using it.

## Resolution

Changed keyboard handlers to use `updateSimulationOptions(SimulationActions.Update)` instead of `resetLabUIAndSimulation()`.

**Files modified:**
- `docs/lab/js/keyboard-handler.js` - 4 handler methods updated
- `docs/browser-keyboard-extensions-implemented.md` - Documentation updated

## Lessons Learned

1. **Method naming matters**: `resetLabUIAndSimulation()` name clearly indicates reset behavior
2. **Consistent patterns**: Sliders and keyboard should use same update mechanism
3. **Browser has full feature parity**: The `target_state` mechanism exists and works correctly
4. **Investigation value**: Understanding both code paths revealed the discrepancy

## Related Documentation

- `docs/browser-keyboard-update-mechanism-fix.md` - Implementation details of the fix
- `docs/browser-keyboard-extensions-implemented.md` - Updated keyboard shortcuts documentation

## Investigation Date

December 2024
