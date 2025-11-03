# Keyboard Shortcuts - Text Animation

This document describes the keyboard shortcuts available in text animation mode (`-as text`).

## Implementation Summary

The text animation now supports the same keyboard shortcuts as the terminal-based animations (terminal_map, terminal_console, terminal_stats). All shortcuts are defined in `ridehail/keyboard_mappings.py` and handled by `ridehail.simulation.KeyboardHandler`.

## Available Shortcuts

| Key            | Action            | Description                                       |
| -------------- | ----------------- | ------------------------------------------------- |
| `p` or `space` | Pause/Resume      | Pause or resume the simulation                    |
| `s`            | Step              | Execute single simulation step (only when paused) |
| `r`            | Restart           | Restart simulation from beginning                 |
| `n`            | Decrease Vehicles | Decrease vehicle count by 1                       |
| `N`            | Increase Vehicles | Increase vehicle count by 1                       |
| `k`            | Decrease Demand   | Decrease demand by 0.1                            |
| `K`            | Increase Demand   | Increase demand by 0.1                            |
| `d`            | Decrease Delay    | Decrease animation delay by 0.05s                 |
| `D`            | Increase Delay    | Increase animation delay by 0.05s                 |
| `q`            | Quit              | Exit the simulation                               |

## User Feedback

When shortcuts are used, the text animation prints feedback messages on new lines:

```
[Paused - press space/p to resume, s to step, r to restart]
[Vehicles increased to 6]
[Demand set to 1.20]
[Animation delay set to 0.15s]
[Restarted simulation]
```

These messages appear above the status line, which continues to update normally with `\r` (carriage return) to show the current simulation state.

## Technical Details

### Implementation

1. **State Tracking**: The `TextAnimation` class tracks previous values of:

   - Vehicle count (`_prev_vehicle_count`)
   - Base demand (`_prev_base_demand`)
   - Animation delay (`_prev_animation_delay`)
   - Block index (`_prev_block_index`)

2. **Change Detection**: The `_check_and_print_keyboard_actions()` method:

   - Compares current values with previous values
   - Prints feedback messages when changes are detected
   - Uses `\n` for feedback (new line) to preserve the single-line status display

3. **Integration**: Called at the start of each simulation loop iteration, after keyboard input checking but before simulation step execution.

### Code Location

- Main implementation: `ridehail/animation/text.py`

  - `TextAnimation.__init__()`: Initialize state tracking
  - `TextAnimation._check_and_print_keyboard_actions()`: Detect and report changes
  - `TextAnimation.animate()`: Integration into simulation loop

- Keyboard handling: `ridehail/simulation.py`

  - `KeyboardHandler`: Centralized keyboard input processing
  - All action logic (pause, restart, adjust parameters, etc.)

- Keyboard mappings: `ridehail/keyboard_mappings.py`
  - Single source of truth for all keyboard shortcuts
  - Shared across text, terminal, and browser interfaces

## Testing

Run the validation script:

```bash
python test_text_keyboard.py
```

Manual testing:

```bash
python -m ridehail test.config -as text
# Try each keyboard shortcut and verify feedback messages appear
```

## Comparison with Terminal Animations

| Feature              | Text Mode              | Terminal Mode (Textual)            |
| -------------------- | ---------------------- | ---------------------------------- |
| Keyboard shortcuts   | Same                   | Same                               |
| Feedback mechanism   | Text messages          | Visual UI updates                  |
| Underlying handler   | `KeyboardHandler`      | `KeyboardHandler` (via UI actions) |
| Configuration source | `keyboard_mappings.py` | `keyboard_mappings.py`             |

Both modes use the same centralized keyboard handling logic, ensuring consistent behavior across all animation styles.
