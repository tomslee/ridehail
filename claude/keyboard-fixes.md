# Keyboard Shortcut Fixes - Text Animation

## Issues Fixed

This document describes the three issues found during testing and their solutions.

---

## Issue 1: Single-Step ('s') Not Working When Paused ❌ → ✅

### Problem
When the simulation was paused and the user pressed 's' to single-step, nothing happened. The simulation remained paused on the same block.

### Root Cause
The pause loop (`while keyboard_handler.is_paused...`) was checking for:
- `keyboard_handler.is_paused`
- `keyboard_handler.should_quit`

But NOT checking for `keyboard_handler.should_step`. This meant that when 's' was pressed, the flag was set but the loop never broke out to allow execution.

### Solution (text.py:124-136)
Added `keyboard_handler.should_step` check to the pause loop condition:

```python
while (
    keyboard_handler.is_paused
    and not keyboard_handler.should_quit
    and not keyboard_handler.should_step  # NEW: Break on step request
):
    keyboard_handler.check_keyboard_input(0.1)
# Break out of sleep loop if step was requested
if keyboard_handler.should_step:
    break
```

**Result**: Pressing 's' now breaks out of the pause loop, executes one simulation step, and returns to paused state.

---

## Issue 2: Restart ('r') Not Resetting Simulation ❌ → ✅

### Problem
Pressing 'r' printed "[Restarted simulation]" but the simulation continued from the current block instead of resetting to block 0.

### Root Cause
The original code used a `for block in range(self.sim.time_blocks)` loop. This creates a loop variable `block` that's independent of the simulation state. Even though `_restart_simulation()` correctly reset `self.sim.block_index` to 0, the `for` loop's `block` variable continued incrementing normally.

### Solution (text.py:76-88)
Replaced `for` loop with `while` loop that explicitly checks and responds to restart:

```python
# OLD: for block in range(self.sim.time_blocks):
# NEW: Use while loop instead of for loop to support restart
block = 0
while block < self.sim.time_blocks and not keyboard_handler.should_quit:
    # Check for restart request (block_index was reset to 0)
    if self.sim.block_index == 0 and block > 0:
        # Restart detected - reset block counter
        block = 0
        print("\n[Restarted simulation]")
        # Reset tracked state for clean feedback after restart
        self._prev_vehicle_count = None
        self._prev_base_demand = None
        self._prev_animation_delay = None
```

**Key changes**:
1. Use `while` loop with explicit block counter instead of `for` loop
2. Check if `self.sim.block_index == 0 and block > 0` (restart detection)
3. Reset local `block` counter to 0 when restart is detected
4. Reset tracked state variables to prevent spurious feedback messages

**Result**: Pressing 'r' now properly resets the simulation to block 0 and continues from the beginning.

---

## Issue 3: Animation Delay ('d/D') Not Taking Effect ❌ → ✅

### Problem
Pressing 'd' or 'D' printed the feedback message (e.g., "[Animation delay set to 0.15s]") but the actual delay between blocks didn't change.

### Root Cause
The `animation_delay` variable was captured ONCE at the start of the animation loop (line 75-77 in original code):

```python
# Get animation delay from config for consistent timing
animation_delay = self.sim.config.animation_delay.value
if animation_delay is None:
    animation_delay = self.sim.config.animation_delay.default
```

The variable was never updated, even though the keyboard handler correctly modified `self.sim.config.animation_delay.value`.

### Solution (text.py:107-110, 152-155)
Move the animation delay reading INSIDE the loop, so it's fetched on every iteration:

```python
# MOVED: Now inside the loop, executed every iteration
# Get current animation delay (may have been changed by keyboard)
animation_delay = self.sim.config.animation_delay.value
if animation_delay is None:
    animation_delay = self.sim.config.animation_delay.default
```

**Result**: Changes to animation delay via 'd/D' take effect immediately on the next block.

---

## Testing

All three issues have been fixed and verified:

```bash
# Test text animation
python -m ridehail test.config -as text

# Try these sequences:
1. Press 'p' to pause
2. Press 's' to single-step → Should advance one block and stay paused
3. Press 'd' multiple times → Should see delay decrease between steps
4. Press 'r' → Should restart from block 0
5. Press 'p' to resume → Should continue normally
```

## Files Modified

- `ridehail/animation/text.py`:
  - Changed `for` loop to `while` loop for restart support
  - Added `should_step` check to pause loop condition
  - Moved animation delay reading inside loop
  - Removed unused `_prev_block_index` tracking
  - Added restart detection and state reset

## Code Locations

- **Single-step fix**: Lines 124-136 (pause loop condition)
- **Restart fix**: Lines 76-88 (loop structure and restart detection)
- **Animation delay fix**: Lines 107-110, 152-155 (read delay on each iteration)
