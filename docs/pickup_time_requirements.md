# Pickup Time Feature - Requirements Document

**Date:** October 2025
**Author:** Requirements generated from user specification
**Status:** Draft for review

---

## Executive Summary

This document specifies requirements for adding realistic pickup behavior to the ridehail simulation. Currently, vehicles transition instantly from P2 (en route to pickup) to P3 (occupied with passenger) when arriving at trip origins. The new feature introduces a configurable delay representing the time required for passenger boarding.

---

## Current Behavior

### Phase Transition at Pickup (`ridehail/simulation.py:701-708`)

```python
if (
    vehicle.phase == VehiclePhase.P2
    and vehicle.location == vehicle.pickup_location
):
    # the vehicle has arrived at the pickup spot and picks up the rider
    vehicle.update_phase(to_phase=VehiclePhase.P3)
    trip.update_phase(to_phase=TripPhase.RIDING)
```

**Current Flow:**
1. Vehicle arrives at `pickup_location` while in P2 phase
2. **Immediately** transitions to P3 phase
3. Trip **immediately** transitions from WAITING to RIDING phase
4. Vehicle begins moving toward `dropoff_location` in next block

**Issue:** This instant transition is unrealistic. Real pickups require 10-60 seconds for:
- Passenger approach to vehicle
- Door opening/closing
- Luggage handling
- Seatbelt fastening
- Navigation confirmation

---

## Proposed Behavior

### Enhanced Pickup Flow with Dwell Time

1. Vehicle arrives at `pickup_location` while in P2 phase
2. Vehicle **remains stationary** at pickup location for `pickup_time` blocks
3. Vehicle **remains in P2 phase** during pickup dwell time
4. Trip **remains in WAITING phase** during pickup dwell time
5. After `pickup_time` blocks elapse:
   - Vehicle transitions to P3 phase
   - Trip transitions to RIDING phase
   - Vehicle resumes navigation toward `dropoff_location`

**Key Insight:** The passenger is "waiting" until they're actually seated and the vehicle begins moving toward the destination. P2 represents "dispatched but not yet transporting," which accurately describes the boarding period.

---

## Functional Requirements

### FR1: Configuration Parameter

**Name:** `pickup_time`
**Type:** `int`
**Default:** `1` (blocks)
**Min Value:** `0`
**Max Value:** `10` (reasonable upper bound)
**Config Section:** `[DEFAULT]`
**Command Line:** `-pt` or `--pickup_time`

**Description:**
Number of blocks a vehicle remains at the trip origin before transitioning to P3 phase.

- `pickup_time = 0`: Original instant pickup behavior (backward compatibility)
- `pickup_time = 1`: One block dwell time (suggested default for realism)
- `pickup_time > 1`: Extended boarding time (accessibility scenarios, etc.)

**Configuration Example:**
```ini
[DEFAULT]
pickup_time = 1
```

---

### FR2: Vehicle State Management

**New Vehicle Attribute:** `pickup_countdown`

**Type:** `int` or `None`
**Purpose:** Track remaining blocks before pickup completion

**State Machine:**

| Condition | `pickup_countdown` Value | Vehicle Phase | Vehicle Movement |
|-----------|--------------------------|---------------|------------------|
| Not at pickup location | `None` | P2 | Moving toward pickup |
| First block at pickup | `pickup_time` | P2 | Stationary |
| Waiting at pickup | `1...pickup_time-1` | P2 | Stationary |
| Pickup complete | `0` → `None` | P3 | Ready to move |

**Implementation Location:** `ridehail/atom.py:250-428` (Vehicle class)

---

### FR3: Simulation Logic Updates

**Location:** `ridehail/simulation.py:701-708`

**Current Logic:**
```python
if (
    vehicle.phase == VehiclePhase.P2
    and vehicle.location == vehicle.pickup_location
):
    vehicle.update_phase(to_phase=VehiclePhase.P3)
    trip.update_phase(to_phase=TripPhase.RIDING)
```

**Proposed Logic:**
```python
if (
    vehicle.phase == VehiclePhase.P2
    and vehicle.location == vehicle.pickup_location
):
    if vehicle.pickup_countdown is None:
        # First arrival at pickup location
        if self.config.pickup_time > 0:
            vehicle.pickup_countdown = self.config.pickup_time
        else:
            # Instant pickup (backward compatibility)
            vehicle.update_phase(to_phase=VehiclePhase.P3)
            trip.update_phase(to_phase=TripPhase.RIDING)
    elif vehicle.pickup_countdown > 0:
        # Decrement countdown each block
        vehicle.pickup_countdown -= 1
        if vehicle.pickup_countdown == 0:
            # Pickup complete, transition phases
            vehicle.update_phase(to_phase=VehiclePhase.P3)
            trip.update_phase(to_phase=TripPhase.RIDING)
            vehicle.pickup_countdown = None
```

---

### FR4: Vehicle Movement During Pickup

**Location:** `ridehail/atom.py:372-392` (`Vehicle.update_location()`)

**Current Logic (lines 380-386):**
```python
elif self.phase == VehiclePhase.P2 and self.location == self.pickup_location:
    # the vehicle is at the pickup location:
    # do not move. Usually picking up is handled
    # at the end of the previous block: this
    # code should run only when the vehicle
    # is at the pickup location when called
    pass
```

**Proposed Enhancement:**
```python
elif self.phase == VehiclePhase.P2 and self.location == self.pickup_location:
    # Vehicle at pickup location performing boarding
    # Do not move until pickup_countdown reaches 0
    pass
```

**Note:** Existing code already handles stationary behavior correctly. The countdown mechanism in FR3 ensures the vehicle remains stationary for the full `pickup_time` duration.

---

### FR5: Vehicle Direction Handling

**Location:** `ridehail/atom.py:341-370` (`Vehicle.update_direction()`)

**Analysis:** Current code navigates toward `pickup_location` when in P2 phase (lines 346-349). When `location == pickup_location`, navigation returns `None` or maintains current direction.

**Requirement:** No changes needed. Direction updates are suspended when vehicle is stationary at pickup location.

---

### FR6: Initialization and Reset

**Vehicle Initialization (`ridehail/atom.py:267-290`):**

Add to `Vehicle.__init__()`:
```python
self.pickup_countdown = None
```

**Vehicle Phase Update (`ridehail/atom.py:301-339`):**

When transitioning **from** P3 → P1 or P3 → P2 (trip completion), ensure:
```python
self.pickup_countdown = None  # Reset for next trip
```

---

### FR7: Metrics and History Tracking

**Impact on Existing Metrics:**

| Metric | Impact | Notes |
|--------|--------|-------|
| `VEHICLE_TIME_P2` | **Increases** | P2 time now includes boarding duration |
| `TRIP_WAIT_TIME` | **Increases** | Wait time now includes boarding duration |
| `TRIP_AWAITING_TIME` | **Increases** | Trip remains WAITING during boarding |
| `VEHICLE_TIME_P3` | Unchanged | P3 starts only after boarding complete |
| `TRIP_RIDING_TIME` | Unchanged | Riding starts only after boarding complete |

**User Communication:** These changes reflect **more accurate** real-world metrics. Previous metrics under-counted true passenger wait times.

**No Code Changes Required:** Existing history tracking (`ridehail/simulation.py`) automatically captures phase durations correctly.

---

## Non-Functional Requirements

### NFR1: Backward Compatibility

**Requirement:** Simulations with `pickup_time = 0` must produce identical results to current implementation.

**Test Case:**
```bash
# Run current version
python -m ridehail test.config -o results_current.json

# Run new version with pickup_time = 0
python -m ridehail test.config -pt 0 -o results_new.json

# Results should be identical
diff results_current.json results_new.json
```

---

### NFR2: Performance

**Requirement:** Addition of pickup countdown logic must not measurably degrade simulation performance.

**Rationale:** Countdown is a simple integer decrement per vehicle per block. Overhead is O(n) where n = vehicle count, same as existing phase checks.

---

### NFR3: Configuration Validation

**Requirement:** Invalid `pickup_time` values must trigger clear error messages.

**Implementation:** Use `ConfigItem` validation (see `ridehail/config.py:84-150`):
```python
pickup_time = ConfigItem(
    name="pickup_time",
    type=int,
    default=1,
    min_value=0,
    max_value=10,
    description=[
        "Number of blocks a vehicle dwells at trip origin during passenger boarding.",
        "0 = instant pickup (original behavior)",
        "1 = one block dwell time (recommended default)",
        ">1 = extended boarding time"
    ],
    help="Pickup dwell time in blocks",
    short_form="-pt",
    config_section="DEFAULT",
    weight=450,  # Position after min_trip_distance, before max_trip_distance
)
```

---

### NFR4: Animation Compatibility

**Requirement:** All animation modes must correctly display vehicles during pickup dwell time.

**Affected Animations:**
- `console`: Vehicle should remain blue/P2 color during pickup
- `terminal_map`: Vehicle should remain at pickup location, displayed with P2 styling
- `map`: Desktop map should show stationary P2 vehicle at trip origin
- `stats`: P2 fraction should increase appropriately

**Implementation Note:** Animations read `vehicle.phase` and `vehicle.location`. No animation code changes required—visual behavior automatically reflects new pickup mechanics.

---

## Implementation Plan

### Phase 1: Core Mechanics (Essential)

1. **Add configuration parameter** (`ridehail/config.py`)
   - Define `pickup_time` ConfigItem
   - Add to argument parser

2. **Update Vehicle class** (`ridehail/atom.py`)
   - Add `pickup_countdown` attribute to `__init__()`
   - Reset countdown in `update_phase()` when appropriate

3. **Update simulation logic** (`ridehail/simulation.py`)
   - Implement countdown mechanism at pickup location
   - Maintain phase transitions during countdown

4. **Update config templates**
   - Add `pickup_time` parameter to `test.config` and other example configs

### Phase 2: Testing & Validation

5. **Unit tests**
   - Test countdown initialization
   - Test countdown decrement
   - Test phase transitions after countdown
   - Test backward compatibility with `pickup_time = 0`

6. **Integration tests**
   - Run full simulations with various `pickup_time` values
   - Verify metrics reflect longer wait times
   - Verify animations display correctly

7. **Regression testing**
   - Confirm existing tests pass with default `pickup_time = 1`
   - Confirm exact parity with `pickup_time = 0`

### Phase 3: Documentation

8. **Update documentation**
   - User guide explaining pickup time parameter
   - Migration notes for interpreting metrics changes
   - Example use cases (accessibility scenarios, etc.)

---

## Test Cases

### TC1: Instant Pickup (Backward Compatibility)

**Config:** `pickup_time = 0`
**Expected:** Vehicle transitions immediately from P2 to P3 at pickup location
**Verification:** Results identical to current implementation

---

### TC2: One Block Pickup (Default)

**Config:** `pickup_time = 1`
**Scenario:** Vehicle arrives at pickup location at block 100

**Expected Timeline:**
- Block 100: Vehicle arrives, `pickup_countdown = 1`, phase = P2, stationary
- Block 101: `pickup_countdown = 0`, phase transitions to P3, vehicle begins moving to destination
- Block 102: Vehicle moving toward destination, phase = P3

**Verification:**
- `VEHICLE_TIME_P2` increases by 1 block
- `TRIP_WAIT_TIME` increases by 1 block
- Animation shows vehicle stationary at pickup for 1 block

---

### TC3: Multi-Block Pickup

**Config:** `pickup_time = 3`
**Scenario:** Vehicle arrives at pickup location at block 200

**Expected Timeline:**
- Block 200: Vehicle arrives, `pickup_countdown = 3`, phase = P2, stationary
- Block 201: `pickup_countdown = 2`, phase = P2, stationary
- Block 202: `pickup_countdown = 1`, phase = P2, stationary
- Block 203: `pickup_countdown = 0`, phase transitions to P3, vehicle begins moving
- Block 204: Vehicle moving toward destination, phase = P3

---

### TC4: Forward Dispatch During Pickup

**Config:** `pickup_time = 2`, `dispatch_method = forward_dispatch`
**Scenario:** Vehicle at pickup location with `pickup_countdown = 2` receives forward dispatch for another trip

**Expected:** Forward dispatch assignment is accepted, stored in `vehicle.forward_dispatch_trip_index`, but does not interrupt current pickup countdown

**Verification:** After completing current trip, vehicle transitions to P2 for forward-dispatched trip with fresh countdown

---

### TC5: Multiple Vehicles, Staggered Pickups

**Config:** `pickup_time = 2`, `vehicle_count = 3`
**Scenario:** Three vehicles arrive at respective pickups at blocks 50, 51, 52

**Expected:** Each vehicle independently completes its 2-block pickup countdown before transitioning to P3

---

## Edge Cases

### EC1: Vehicle Spawns at Pickup Location

**Scenario:** Dispatch assigns vehicle that is already at pickup location (distance = 0)

**Expected:** Countdown begins immediately in same block as dispatch

**Current Code:** `update_location()` prevents movement when `location == pickup_location` (line 380), so countdown can proceed normally

---

### EC2: Simulation Reset During Pickup

**Scenario:** User presses 'r' (reset) while vehicle has `pickup_countdown = 2`

**Expected:** Vehicle reinitialized with `pickup_countdown = None`

**Implementation:** Reset calls `Vehicle.__init__()`, which initializes `pickup_countdown = None`

---

### EC3: Invalid Configuration Values

**Scenario:** User specifies `pickup_time = -1` or `pickup_time = 100`

**Expected:** Configuration validation error with clear message

**Implementation:** `ConfigItem` with `min_value=0, max_value=10` enforces bounds

---

## Metrics Changes Summary

### Affected Metrics

**Increase proportionally to `pickup_time`:**
- Vehicle P2 time (`VEHICLE_TIME_P2`)
- Trip wait time (`TRIP_WAIT_TIME`, `TRIP_AWAITING_TIME`)
- Vehicle P2 fraction (`VEHICLE_FRACTION_P2`)
- Trip wait fraction (`TRIP_MEAN_WAIT_FRACTION`, `TRIP_MEAN_WAIT_FRACTION_TOTAL`)

**Unchanged:**
- Vehicle P3 time (boarding is not transporting)
- Trip riding time (same as P3 time)
- Trip distance (same route, just delayed start)
- Vehicle P1 time (indirect: less time available for P1)

**User Impact:** Published results using new default `pickup_time = 1` will show slightly higher wait times (~1 block increase). This represents **more accurate real-world metrics**, not a regression.

---

## Migration Guidance for Users

### For Existing Research

**Option 1: Maintain Historical Parity**
```bash
# Use pickup_time = 0 to exactly replicate previous results
python -m ridehail my_config.config -pt 0
```

**Option 2: Adopt Realistic Metrics**
```bash
# Use pickup_time = 1 (new default) for more accurate modeling
python -m ridehail my_config.config
```

Add note to publications: "Version X.Y.Z introduced realistic pickup dwell time. Results use `pickup_time = 1`, increasing reported wait times by ~1 block per trip compared to earlier versions."

---

## Dependencies

### Modified Files

- `ridehail/atom.py`: Vehicle class updates
- `ridehail/simulation.py`: Pickup countdown logic
- `ridehail/config.py`: Configuration parameter
- `*.config`: Example configuration files
- `docs/`: User documentation

### No Changes Required

- Animation modules (automatically reflect phase/position changes)
- Dispatch logic (countdown is transparent to dispatch)
- History/metrics tracking (automatically captures phase durations)
- Equilibration logic (operates on aggregate metrics)

---

## Future Enhancements (Out of Scope)

### Dropoff Time

Similar enhancement for passenger egress at destination:
- Vehicle remains in P3 at `dropoff_location` for `dropoff_time` blocks
- Trip remains in RIDING phase during dropoff

**Difference:** Dropoff occurs during P3 (passenger still in vehicle), unlike pickup which occurs during P2.

### Variable Pickup Time

Pickup time could vary by:
- Time of day (rush hour delays)
- Trip distance (more luggage for longer trips)
- Vehicle type (accessibility vehicles require more time)

### Stochastic Pickup Time

Draw `pickup_time` from distribution (e.g., Normal(μ=1, σ=0.5)) rather than fixed value.

---

## Conclusion

The pickup time feature adds realism to the simulation with minimal implementation complexity. The design maintains full backward compatibility while providing more accurate metrics for research and analysis. The suggested default of `pickup_time = 1` reflects typical real-world boarding durations of 10-60 seconds (mapping to 1-2 blocks depending on `minutes_per_block` configuration).

---

## Appendices

### Appendix A: Related Code Locations

| Component | File | Lines | Purpose |
|-----------|------|-------|---------|
| Vehicle class | `ridehail/atom.py` | 250-428 | Vehicle state and methods |
| Pickup transition | `ridehail/simulation.py` | 701-708 | Current instant pickup logic |
| Vehicle movement | `ridehail/atom.py` | 372-392 | Movement prevention at pickup |
| Configuration | `ridehail/config.py` | 236-456 | ConfigItem definitions |
| Config file | `test.config` | 1-457 | Example configuration |

### Appendix B: Configuration File Entry

**Generated entry for `test.config`:**

```ini
# ----------------------------------------------------------------------------
# pickup time (int, default 1)
# Number of blocks a vehicle dwells at trip origin during passenger boarding.
# 0 = instant pickup (original behavior)
# 1 = one block dwell time (recommended default)
# >1 = extended boarding time (accessibility scenarios, etc.)
# ----------------------------------------------------------------------------

pickup_time = 1
```

**Suggested insertion point:** After `min_trip_distance` (line 66), before `max_trip_distance` (line 73)

### Appendix C: Phase Transition Diagram

```
Current Behavior:
┌──────┐  Dispatch   ┌──────┐  Arrive at   ┌──────┐  Arrive at   ┌──────┐
│  P1  │────────────>│  P2  │──Pickup─────>│  P3  │───Dropoff───>│  P1  │
└──────┘             └──────┘   (instant)   └──────┘             └──────┘
   ↑                                                                  │
   └──────────────────────────────────────────────────────────────────┘

Proposed Behavior with pickup_time = 2:
┌──────┐  Dispatch   ┌──────┐  Arrive at   ┌──────┐  Block 1   ┌──────┐  Block 2   ┌──────┐  Dropoff   ┌──────┐
│  P1  │────────────>│  P2  │───Pickup────>│  P2  │───────────>│  P2  │───────────>│  P3  │───────────>│  P1  │
└──────┘             └──────┘  (stationary) └──────┘            └──────┘            └──────┘            └──────┘
   ↑                           countdown=2   countdown=1         countdown=0                                │
   └────────────────────────────────────────────────────────────────────────────────────────────────────────┘
                                                                            ↑
                                                                            └─ Phase transition when countdown reaches 0
```

### Appendix D: References

- **Insurance industry phase definitions:** VehiclePhase enum docstring (`ridehail/atom.py:62-75`)
- **Current pickup handling:** `ridehail/simulation.py:697-716`
- **Configuration system:** `ridehail/config.py:29-150` (ConfigItem class)
- **Vehicle state machine:** `ridehail/atom.py:301-339` (Vehicle.update_phase())
