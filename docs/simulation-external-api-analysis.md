# RideHailSimulation External API Analysis

**Date:** 2025-01-13
**Purpose:** Document which methods and attributes of `RideHailSimulation` are accessed from outside the class to inform API design decisions.

## Overview

The `RideHailSimulation` class (`ridehail/simulation.py`) is the core simulation engine. This analysis identifies its external API surface to:
1. Distinguish genuinely public methods from those that could be marked private
2. Evaluate opportunities to centralize or standardize access patterns
3. Document the intended external interface

## Public Methods Called Externally

### 1. `simulate()` - Main simulation runner
**Purpose:** Runs the complete simulation loop with keyboard handling, file output, and result collection.

**Called from:**
- `ridehail/__main__.py:51` - When animation is disabled (`Animation.NONE`)
- `run.py:52` - When animation is disabled
- `ridehail/sequence.py:233` - For each simulation in a parameter sweep sequence
- Test files (`test/test_simulation.py`)

**Status:** ✅ **Should remain public** - Primary entry point for standalone simulations.

**Signature:**
```python
def simulate(self) -> RideHailSimulationResults
```

---

### 2. `next_block()` - Single simulation step execution
**Purpose:** Execute one block (time step) of simulation, optionally return state for visualization.

**Called from:**
- `docs/lab/worker.py:181` - Web worker for browser interface
- Animation classes (via `ridehail.animation.base.RideHailAnimation` and subclasses):
  - `ridehail/animation/matplotlib.py` - Matplotlib animations
  - `ridehail/animation/terminal_base.py` - Textual-based animations
  - `ridehail/animation/terminal_map.py` - Terminal map visualization
  - `ridehail/animation/terminal_stats.py` - Terminal statistics charts
- Internal call from `simulate()` method at line 682, 719

**Status:** ✅ **Should remain public** - Essential for animation systems and external drivers.

**Signature:**
```python
def next_block(
    self,
    jsonl_file_handle=None,
    csv_file_handle=None,
    block=None,
    return_values=None,
) -> dict
```

**Calling Patterns:**

1. **Simple pattern** (animations): `sim.next_block()` - uses defaults
2. **Explicit pattern** (web interface):
   ```python
   sim.next_block(
       jsonl_file_handle=None,
       csv_file_handle=None,
       return_values="map",  # or "stats"
   )
   ```

---

### 3. `get_keyboard_handler()` - Keyboard control access
**Purpose:** Lazy initialization and retrieval of keyboard handler for interactive control.

**Called from:**
- Animation classes that implement keyboard-driven controls

**Status:** ✅ **Should remain public** - Standard accessor pattern for optional feature.

**Signature:**
```python
def get_keyboard_handler(self) -> KeyboardHandler
```

---

### 4. `vehicle_utility()` - Economic utility calculation
**Purpose:** Calculate driver utility/surplus per block based on busy fraction.

**Called from:**
- `ridehail/simulation.py:1095` - Internal calculation in `_update_measures()`
- `ridehail/simulation.py:1464` - Internal equilibration in `_equilibrate_supply()`
- `ridehail/animation/terminal_stats.py` - Utility chart calculations
- `ridehail/animation/matplotlib.py` - Utility plot calculations

**Status:** ✅ **Should remain public** - Used by animation/visualization systems for economic analysis.

**Signature:**
```python
def vehicle_utility(self, busy_fraction: float) -> float
```

**Formula:**
```python
return (
    self.price * (1.0 - self.platform_commission) * busy_fraction
    - self.reservation_wage
)
```

---

### 5. `convert_units()` - Unit conversion helper
**Purpose:** Convert between city scale units (blocks, minutes, hours, km, rates).

**Called from:**
- Internal usage throughout `simulation.py` for unit conversions (lines 528, 531, 533, 545, 548, 1138, 1143, 1147, 1153, 1158, 1163, 1168, 1173, 1257, 1262, 1273, 1277)
- Test files (`test/test_conversion.py`)

**Status:** ✅ **Should remain public** - Useful utility for external analysis and testing.

**Signature:**
```python
def convert_units(
    self,
    in_value: float,
    from_unit: CityScaleUnit,
    to_unit: CityScaleUnit
) -> float | None
```

**Supported Units:**
- Time: `MINUTE`, `HOUR`, `BLOCK`
- Distance: `KM`, `BLOCK`
- Rates: `PER_MINUTE`, `PER_HOUR`, `PER_BLOCK`, `PER_KM`

---

## Attributes Accessed Externally

The simulation object is designed as an observable data container. External code (primarily animations and web interface) accesses attributes directly.

### Configuration & Parameters (Read Access)
Accessed primarily for display and state management:

- `sim.config` - Full configuration object (all animation classes, worker.py)
- `sim.city_size` - City grid size
- `sim.vehicle_count` - Number of vehicles
- `sim.base_demand` - Trip request rate
- `sim.time_blocks` - Total simulation duration
- `sim.price`, `sim.platform_commission`, `sim.reservation_wage` - Economic parameters
- `sim.equilibrate`, `sim.equilibration` - Equilibration settings
- `sim.dispatch_method`, `sim.forward_dispatch_bias` - Dispatch algorithm settings
- `sim.city` - City object with topology and probability distributions

### Runtime State (Read Access)
Accessed for visualization and analysis:

- `sim.vehicles` - List of `Vehicle` objects (animations render vehicle positions/phases)
- `sim.trips` - Dictionary of `Trip` objects (animations render trip origins/destinations)
- `sim.block_index` - Current simulation block number
- `sim.history_buffer` - Rolling window statistics (animation classes for charts)

### Dynamic Control (Write Access)
Modified for interactive parameter adjustment:

- `sim.target_state` - Dictionary for runtime parameter updates
  - Modified by: keyboard handlers (`simulation.py:KeyboardHandler`), animation event handlers
  - Applied at: start of each block in `_init_block()` (line 1221)
  - Supported parameters: `vehicle_count`, `base_demand`, `city_size`, `equilibrate`, etc.

### Output Configuration (Read Access)
- `sim.jsonl_file`, `sim.csv_file` - Output file paths
- `sim.title` - Simulation title for display

---

## Private Methods (Not Called Externally)

All methods prefixed with `_` are correctly used only within the `RideHailSimulation` class:

- `_set_output_files()` - Output file path configuration
- `_validate_options()` - Parameter validation and constraint enforcement
- `_create_metadata_record()` - Metadata generation for JSONL output
- `_restart_simulation()` - Reset simulation state (called via keyboard handler)
- `_update_state()` - State dictionary assembly for output
- `_update_measures()` - Calculate rolling statistics
- `_request_trips()` - Generate new trip requests
- `_cancel_requests()` - Cancel timed-out requests
- `_init_block()` - Block initialization and parameter updates
- `_update_history()` - History buffer updates
- `_collect_garbage()` - Periodic cleanup of completed trips
- `_remove_vehicles()` - Vehicle removal during equilibration
- `_equilibrate_supply()` - Supply/demand equilibration
- `_demand()` - Demand calculation with elasticity
- `_flatten_end_state()` - Hierarchical to flat data conversion for CSV

---

## Architecture Assessment

### Current Design: Observable Data Container

The `RideHailSimulation` object serves as an observable data container for visualization systems. This design is appropriate because:

✅ **Simpler and more Pythonic** - Direct attribute access is idiomatic
✅ **Better performance** - No method call overhead in tight animation loops
✅ **Clear intent** - Attributes are meant to be observable
✅ **Already well-designed** - Separation between public (observable) and private (implementation)

### Alternative: Method-Based Access (Not Recommended)

Could create getter methods:
```python
def get_vehicle_states(self) -> List[VehicleState]: ...
def get_trip_states(self) -> Dict[int, TripState]: ...
def get_simulation_metrics(self) -> Dict[str, float]: ...
def update_target_parameter(self, name: str, value: Any) -> None: ...
```

**Why not recommended:**
- Adds unnecessary indirection
- No encapsulation benefits (data is meant to be exposed)
- Worse performance for animation frame rates
- More complex API without clear advantages

---

## Recommendations

### 1. Keep Current Public Methods
All currently public methods serve legitimate external needs:
- ✅ `simulate()` - Main entry point
- ✅ `next_block()` - Animation/web interface driver
- ✅ `get_keyboard_handler()` - Interactive control
- ✅ `vehicle_utility()` - Economic visualization
- ✅ `convert_units()` - Unit conversion utility

### 2. No Methods Need Privatization
The original analysis suggested marking `vehicle_utility()` as private, but it's correctly used by animation classes for economic analysis visualizations.

### 3. Document Calling Patterns
The two `next_block()` calling patterns should be clearly documented:

**Pattern 1: Animation Driver (simple)**
```python
# For animations running their own loop
state = sim.next_block()
```

**Pattern 2: External Driver (explicit)**
```python
# For web interface or external control
state = sim.next_block(
    jsonl_file_handle=None,
    csv_file_handle=None,
    return_values="map",  # or "stats" for different data
    dispatch=Dispatch()
)
```

### 4. Keep Direct Attribute Access
Continue allowing direct access to:
- Configuration: `sim.config`, `sim.city_size`, etc.
- State: `sim.vehicles`, `sim.trips`, `sim.block_index`
- Control: `sim.target_state` (for runtime updates)

This pattern is intentional and appropriate for this architecture.

### 5. Maintain Clear Public/Private Separation
Continue using `_` prefix for internal methods. All current private methods are correctly scoped.

---

## External Callers by Module

### Animation System
**Base Class:** `ridehail/animation/base.py`
- Accesses: `sim.target_state` (keyboard handlers)
- Calls: `next_block()` (indirectly via subclasses)

**Matplotlib:** `ridehail/animation/matplotlib.py`
- Accesses: `sim.config`, `sim.vehicles`, `sim.trips`, `sim.history_buffer`
- Calls: `next_block()`, `vehicle_utility()`

**Terminal (Textual):** `ridehail/animation/terminal_*.py`
- Accesses: `sim.config`, `sim.vehicles`, `sim.trips`, `sim.city_size`, `sim.block_index`
- Calls: `next_block()`, `vehicle_utility()` (terminal_stats.py)

### Web Interface
**Worker:** `docs/lab/worker.py`
- Accesses: `sim.config`, `sim.vehicles`, `sim.trips`, `sim.target_state`
- Calls: `next_block(return_values="map")` or `next_block(return_values="stats")`

### Entry Points
**Main:** `ridehail/__main__.py`, `run.py`
- Calls: `simulate()` (when animation disabled)

**Sequence:** `ridehail/sequence.py`
- Calls: `simulate()` (for each simulation in sweep)

### Tests
**Unit Tests:** `test/test_simulation.py`, `test/test_conversion.py`
- Calls: `simulate()`, `convert_units()`

---

## Summary

The `RideHailSimulation` class has a well-designed external API:

**Public Methods (5):**
- All serve legitimate external needs
- No changes recommended
- Clear separation from private methods

**Attribute Access:**
- Direct access pattern is appropriate for this use case
- No encapsulation needed - object is an observable data container
- Performance benefits for animation frame rates

**API Stability:**
- Current interface is stable and well-used
- No breaking changes recommended
- Documentation improvements suggested for calling patterns

The simulation object successfully serves its dual role as:
1. Standalone simulation engine (via `simulate()`)
2. Observable data container for visualization systems (via direct attribute access and `next_block()`)
