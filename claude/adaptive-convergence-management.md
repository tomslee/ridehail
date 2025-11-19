# Adaptive Convergence Management Implementation Plan

**Date**: 2025-11-19
**Status**: Phase 1 Implemented ✅ (Bug Fix Applied 2025-11-19)

## Problem Statement

The ridehail simulation equilibration system uses two fixed parameters that require "goldilocks" values:

1. **`equilibration_interval`** (config parameter): How often to adjust vehicle count (default: 5 blocks)
2. **`EQUILIBRATION_DAMPING_FACTOR`** (code constant): How aggressively to change vehicle count (value: 0.5)

These parameters need careful tuning:
- **Too slow/small**: Convergence takes unnecessarily long
- **Too fast/large**: System oscillates and may never converge

## Solution: Adaptive Convergence Management

Implement automatic parameter management using well-known control theory algorithms.

---

## Architecture Overview

### Key Insight: Close the Loop

The simulation already has `ConvergenceTracker` (in `ridehail/convergence.py`) that monitors system state but doesn't feedback into the control system. The solution is to **close this loop** by using convergence metrics to adjust equilibration behavior dynamically.

### Special Configuration Value

**`equilibration_interval = 0`** triggers automatic convergence management:
- System dynamically adjusts both damping factor and update interval
- Adapts to system state and convergence progress
- Eliminates need for manual tuning

---

## Implementation Phases

### Phase 1: Adaptive Damping with Oscillation Detection ✅

**Status**: IMPLEMENTED

**Goal**: Automatically find optimal damping factor by detecting and responding to oscillations.

**Algorithms**:

1. **Oscillation Detection**
   - Monitor sign changes in vehicle increments
   - Count consecutive oscillations
   - Trigger damping increase after 3 consecutive oscillations

2. **Adaptive Damping (Trust Region Strategy)**
   - Increase damping conservatively when oscillating (×1.5)
   - Decrease damping aggressively when improving (×0.7)
   - "Delayed gratification" approach from Levenberg-Marquardt algorithm

3. **Convergence-Based Interval Adjustment**
   - Use shorter intervals when far from equilibrium
   - Use longer intervals when converged
   - Reduces computational overhead while maintaining stability

**Implementation Details**:

New simulation attributes:
```python
self.damping_factor = 0.5  # Dynamic instead of constant
self.adaptive_equilibration_interval = 5  # Dynamic update frequency
self.previous_vehicle_increment = 0
self.previous_vehicle_increment_sign = 0
self.oscillation_count = 0
self.consecutive_improvements = 0
self.previous_convergence_residual = float('inf')
```

Adaptive interval logic:
```python
if convergence_tracker.is_converged:
    interval = 20  # Infrequent adjustments when stable
elif max_rms_residual > 0.1:
    interval = 3   # Frequent adjustments when far from equilibrium
else:
    interval = 7   # Moderate frequency during transition
```

Oscillation detection:
```python
if sign(current_increment) != sign(previous_increment) and both != 0:
    oscillation_count += 1
    if oscillation_count >= 3:
        damping_factor *= 1.5  # Increase damping
        oscillation_count = 0
```

Improvement-based damping reduction:
```python
if current_residual < previous_residual * 0.95:
    consecutive_improvements += 1
    if consecutive_improvements >= 2:
        damping_factor *= 0.7  # Decrease damping aggressively
```

**Benefits**:
- Self-tuning system finds optimal damping automatically
- Prevents persistent oscillations
- Faster convergence when system is responsive
- Minimal code complexity

**Files Modified**:
- `ridehail/simulation.py`: Added adaptive equilibration logic
- `ridehail/config.py`: Updated help text for `equilibration_interval`

---

### Phase 2: Gain Scheduling Based on Convergence State

**Status**: PLANNED

**Goal**: Use different control strategies in different operating regimes.

**Algorithm**:
```python
# In _equilibrate_supply()
if self.convergence_tracker.is_converged:
    # Very small adjustments near equilibrium
    effective_damping = self.damping_factor * 0.2
elif self.convergence_tracker.max_rms_residual > 0.15:
    # Aggressive adjustments when far from equilibrium
    effective_damping = self.damping_factor * 1.5
else:
    # Normal adjustments in transition region
    effective_damping = self.damping_factor
```

**Benefits**:
- Different behavior near vs. far from equilibrium
- Combines well with Phase 1 adaptive damping
- Prevents over-correction when nearly converged

**Complexity**: Low (10-20 lines)

---

### Phase 3: Full PID Controller

**Status**: FUTURE CONSIDERATION

**Goal**: Add integral and derivative terms to the current proportional-only controller.

**Current Formula**:
```
Δv = K_p × v × error
```

**PID Formula**:
```
Δv = K_p × error + K_i × Σ(error) + K_d × (error - previous_error)
```

**Benefits**:
- **Integral term**: Eliminates steady-state error
- **Derivative term**: Reduces overshoot

**Challenges**:
- Requires maintaining error history
- More complex tuning (3 parameters instead of 1)
- May not be necessary if Phases 1-2 perform well

**Complexity**: Medium (~50 lines)

---

## Technical Background

### Control Theory Algorithms Researched

1. **PID Control** - Classic proportional-integral-derivative controller
   - Most widely used in industrial control systems
   - Proven effectiveness for steady-state convergence

2. **Trust Region Methods** - Adaptive damping from optimization theory
   - Levenberg-Marquardt algorithm approach
   - "Delayed gratification" damping adjustment

3. **Gain Scheduling** - State-dependent parameter adjustment
   - Different gains for different operating points
   - Common in nonlinear system control

4. **Ziegler-Nichols Tuning** - Empirical PID parameter determination
   - Classical method for finding optimal PID gains
   - Requires inducing controlled oscillations

5. **Adaptive Control** - Online parameter adjustment
   - Lyapunov stability theory based
   - Guarantees convergence under appropriate conditions

### References

- Levenberg-Marquardt Algorithm (damped least-squares method)
- Trust Region Methods (Cornell Computational Optimization)
- Adaptive Gain-Scheduling Control (ScienceDirect research)
- PID Auto-Tuning surveys (Academia.edu)

---

## Testing Strategy

### Test Scenarios

1. **Oscillation Prone Configuration**
   - High initial damping that would normally oscillate
   - Verify system self-corrects

2. **Slow Convergence Configuration**
   - Low initial damping
   - Verify system speeds up appropriately

3. **Multiple Equilibration Methods**
   - Test with `equilibration = "price"`
   - Test with `equilibration = "wait_fraction"`

4. **Different City Sizes**
   - Small cities (10×10)
   - Medium cities (32×32)
   - Large cities (50×50)

### Success Criteria

- No sustained oscillations (>3 consecutive sign changes)
- Convergence achieved within reasonable time
- Damping factor stabilizes to appropriate range (0.1-1.0)
- Adaptive interval adjusts based on convergence state

### Test Commands

```bash
# Automatic adaptive management
python -m ridehail test.config -eq price -ei 0

# Traditional fixed parameters (for comparison)
python -m ridehail test.config -eq price -ei 5

# With terminal stats visualization
python -m ridehail test.config -eq price -ei 0 -a terminal_stats
```

---

## Configuration Integration

### Parameter: `equilibration_interval`

**Default**: 5 (traditional fixed interval)

**Special Value**: 0 (automatic adaptive management)

**Help Text**:
```
-ei N, --equilibration_interval N
    Adjust supply and demand every N blocks when equilibrating.
    Set to 0 for automatic adaptive convergence management.
    (int, default 5, range: 0-100)
```

### Backward Compatibility

- Existing configs with `equilibration_interval > 0` use fixed interval (no behavior change)
- `equilibration_interval = 0` enables new adaptive system
- Users can opt-in to adaptive management

---

## Future Enhancements

### Advanced Oscillation Detection

- Detect oscillation amplitude, not just frequency
- Use Fast Fourier Transform (FFT) to identify periodic patterns
- Distinguish between healthy convergence and problematic oscillations

### Machine Learning Parameter Tuning

- Learn optimal damping factors from simulation history
- Predict convergence time based on configuration
- Recommend configuration adjustments

### Multi-Metric Optimization

- Balance convergence speed vs. stability
- Optimize for specific metrics (vehicle utilization, wait times)
- Pareto-optimal control strategies

### Adaptive Equilibration Method Selection

- Automatically choose between "price" and "wait_fraction" equilibration
- Switch methods based on convergence progress
- Hybrid approaches combining multiple methods

---

## Implementation Notes

### Code Location

**Primary Implementation**: `ridehail/simulation.py`
- `__init__()`: Initialize adaptive parameters
- `_equilibrate_supply()`: Core adaptive logic
- `_restart_simulation()`: Reset adaptive state

**Configuration**: `ridehail/config.py`
- `equilibration_interval`: Updated help text

**Convergence Tracking**: `ridehail/convergence.py`
- No changes needed (already provides metrics)

### Performance Impact

- Negligible computational overhead
- Additional state tracking: ~6 float/int attributes
- Logic executed only during equilibration blocks
- No impact on non-equilibrating simulations

### Maintenance Considerations

- Damping factor bounds: [0.05, 2.0] prevent extreme values
- Interval bounds: [3, 20] balance responsiveness and stability
- Logging adaptive decisions aids debugging
- Consider adding adaptive metrics to output files

---

## Success Metrics

### Quantitative

- Convergence time: Reduce by 20-40% vs. fixed parameters
- Oscillation frequency: Eliminate sustained oscillations
- Parameter robustness: Work across wide range of configurations
- User satisfaction: Reduce need for manual tuning

### Qualitative

- "Set and forget" convergence management
- Predictable behavior across configurations
- Transparent adaptive decisions (via logging)
- Smooth transition from far-from-equilibrium to converged states

---

## Version History

- **2025-11-19**: Bug fix applied - Division by zero when `equilibration_interval = 0`
  - Fixed `CircularBuffer(0)` error in `__init__()` and `_restart_simulation()`
  - Use buffer size of 20 (max adaptive interval) in adaptive mode
  - Verified with `test/equilibration.config`
- **2025-11-19**: Phase 1 implemented (adaptive damping + oscillation detection)
- **2025-11-19**: Initial plan documented

## Testing Status

✅ **Tested Successfully**:
- `test/equilibration.config` - Runs with `equilibration_interval = 0`
- `adaptive_test.config` - Example configuration works correctly
- Code compiles without syntax errors
- No divide by zero errors

📋 **Recommended Testing**:
- Test with different city sizes
- Test with both `equilibration = "price"` and `equilibration = "wait_fraction"`
- Long-running simulations to verify stability
- Compare convergence time vs. fixed parameters
