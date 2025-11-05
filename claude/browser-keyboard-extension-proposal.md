# Browser Keyboard Extension Proposal

## Current State

### Already in Browser

- **pause** (space, p) - Pause/Resume simulation
- **step** (s) - Single step forward when paused
- **toggle_zoom** (z) - Toggle zoom/hide UI elements

### Desktop-Only Shortcuts

- **quit** (q) - Not applicable to browser
- **decrease_vehicles** (n) - Could add to browser
- **increase_vehicles** (N) - Could add to browser
- **decrease_demand** (k) - Could add to browser
- **increase_demand** (K) - Could add to browser
- **decrease_animation_delay** (d) - Could add to browser
- **increase_animation_delay** (D) - Could add to browser
- **help** (h, ?) - Could add to browser

## Recommendations for Browser Extension

### ✅ Highly Recommended (High Value, Low Conflict)

#### 1. **Vehicle Count Adjustment** (n/N)

- **Keys**: n (decrease), N (increase)
- **Benefit**: Quick experimentation with fleet size
- **Implementation**: Update vehicle count slider + regenerate simulation
- **Conflict Risk**: LOW - n/N not typically used by browsers
- **User Value**: HIGH - Very common adjustment during exploration

#### 2. **Demand Adjustment** (k/K)

- **Keys**: k (decrease), K (increase)
- **Benefit**: Test different demand scenarios quickly
- **Implementation**: Update request rate slider + regenerate simulation
- **Conflict Risk**: LOW - k/K not browser shortcuts
- **User Value**: HIGH - Core parameter for experimentation

#### 3. **Animation Delay** (d/D)

- **Keys**: d (decrease/faster), D (increase/slower)
- **Benefit**: Adjust simulation speed on the fly
- **Implementation**: Update animation delay slider
- **Conflict Risk**: LOW - d/D not browser shortcuts
- **User Value**: MEDIUM - Useful for watching details vs. running fast

### 🤔 Consider Adding (Medium Value)

#### 4. **Help Overlay** (h or ?)

- **Keys**: h, ?
- **Benefit**: Show keyboard shortcuts in overlay
- **Implementation**: Modal dialog with keyboard shortcuts list
- **Conflict Risk**: MEDIUM - '?' might conflict with some browsers (search in page)
- **User Value**: MEDIUM - Nice to have, but shortcuts are simple
- **Recommendation**: Use only 'h', skip '?' to avoid conflicts

### ❌ Not Recommended

#### 5. **Quit** (q)

- **Reason**: Not applicable - users just close browser tab
- **Alternative**: Could map to "reset simulation" instead

## Implementation Priority

### Phase 1: Core Adjustments (Immediate)

1. Add vehicle count (n/N) to browser platform ✅
2. Add demand adjustment (k/K) to browser platform ✅
3. Add animation delay (d/D) to browser platform ✅

### Phase 2: Help System (Optional)

4. Add help overlay (h) to show keyboard shortcuts

## Technical Considerations

### Browser Keyboard Conflict Prevention

**Potential conflicts to handle**:

- **Space**: Can trigger page scroll
  - **Solution**: `event.preventDefault()` when simulation has focus
- **Question mark (?)**: Some browsers use for search
  - **Solution**: Skip '?' in browser, use only 'h' for help

### UI Updates Required

For each new shortcut, browser needs to:

1. **Update slider value** - Reflect keyboard change in UI
2. **Trigger input handler** - Same logic as slider change
3. **Update simulation** - Post message to web worker
4. **Show feedback** - Brief toast notification of change

### Example Implementation

**Adding vehicle count adjustment**:

```javascript
// In keyboard-handler.js
_handleDecreaseVehicles() {
    const currentValue = parseInt(DOM_ELEMENTS.inputs.vehicleCount.value);
    const newValue = Math.max(currentValue - 1, 0);

    // Update slider
    DOM_ELEMENTS.inputs.vehicleCount.value = newValue;
    DOM_ELEMENTS.options.vehicleCount.textContent = newValue;

    // Trigger update
    appState.labSimSettings.vehicleCount = newValue;
    this.app.resetLabUIAndSimulation();

    // Optional: Show toast notification
    showSuccess(`Vehicles: ${newValue}`);
}
```

## Proposed keyboard_mappings.py Changes

```python
# Change these from desktop-only to all platforms:

KeyMapping(
    action="decrease_vehicles",
    keys=["n"],
    description="Decrease vehicles by 1",
    platforms=["terminal", "textual", "browser"],  # Added "browser"
    value=1,
),
KeyMapping(
    action="increase_vehicles",
    keys=["N"],
    description="Increase vehicles by 1",
    platforms=["terminal", "textual", "browser"],  # Added "browser"
    shift_modifier=True,
    value=1,
),
KeyMapping(
    action="decrease_demand",
    keys=["k"],
    description="Decrease demand by 0.1",
    platforms=["terminal", "textual", "browser"],  # Added "browser"
    value=0.1,
),
KeyMapping(
    action="increase_demand",
    keys=["K"],
    description="Increase demand by 0.1",
    platforms=["terminal", "textual", "browser"],  # Added "browser"
    shift_modifier=True,
    value=0.1,
),
KeyMapping(
    action="decrease_animation_delay",
    keys=["d"],
    description="Decrease animation delay by 0.05s",
    platforms=["terminal", "textual", "browser"],  # Added "browser"
    value=0.05,
),
KeyMapping(
    action="increase_animation_delay",
    keys=["D"],
    description="Increase animation delay by 0.05s",
    platforms=["terminal", "textual", "browser"],  # Added "browser"
    shift_modifier=True,
    value=0.05,
),
KeyMapping(
    action="help",
    keys=["h"],  # Removed "?" to avoid browser conflicts
    description="Show keyboard shortcuts help",
    platforms=["terminal", "textual", "browser"],  # Added "browser"
),
```

## Benefits Summary

### User Experience

- **Faster experimentation** - No need to reach for sliders
- **Keyboard-only workflow** - Power users can stay on keyboard
- **Consistent with desktop** - Same muscle memory across platforms
- **Quick iterations** - Rapid parameter adjustment during exploration

### Implementation

- **Minimal code** - KeyboardHandler already structured for this
- **Reuses existing logic** - Same as slider change handlers
- **Low risk** - Keys unlikely to conflict with browsers
- **Easy to add more** - Framework supports arbitrary shortcuts

## Recommendation

**Implement Phase 1 immediately**: Add vehicle count (n/N), demand (k/K), and animation delay (d/D) to browser platform. These are high-value, low-risk additions that significantly improve the browser user experience.

**Consider Phase 2 later**: Add help overlay (h) if users request it, but it's not essential since the keyboard shortcuts are simple and consistent with desktop.
