# Performance Profiling Analysis - October 2025

## Executive Summary

Profiling of the Toronto coarse configuration (3,000 vehicles, 500 blocks, 22.85s elapsed time) reveals that **dispatch operations consume 48% of total execution time (27 seconds)**, making spatial indexing the highest-priority optimization target.

## Configuration Profiled

- **Config**: `cities/toronto/coarse.config`
- **City Size**: 40×40 blocks
- **Vehicle Count**: 3,000 (equilibrating from initial value)
- **Time Blocks**: 500
- **Base Demand**: 100 trips/block
- **Elapsed Time**: 22.85 seconds
- **Profiling Command**: `uv run python -m cProfile -o profile_output.prof -m ridehail cities/toronto/coarse.config`

## Performance Breakdown

### Top Bottlenecks by Time

| Function | Time (s) | % Total | Calls | Calls/Block | Location |
|----------|----------|---------|-------|-------------|----------|
| `distance()` | 12.09 | 21.4% | 25.5M | 51,000 | `atom.py:481` |
| `dispatch_distance()` | 7.69 | 13.6% | 25.5M | 51,000 | `atom.py:499` |
| `_dispatch_vehicle_sparse()` | 7.26 | 12.9% | 48.1k | 96 | `dispatch.py:144` |
| `update_direction()` | 1.90 | 3.4% | 1.6M | 3,200 | `atom.py:355` |
| `update_location()` | 1.79 | 3.2% | 1.6M | 3,200 | `atom.py:386` |
| `_update_history()` | 1.63 | 2.9% | 500 | 1 | `simulation.py:1126` |
| `_init_block()` | 1.48 | 2.6% | 500 | 1 | `simulation.py:1025` |

### Time Distribution by Component

| Component | Time (s) | % of Total |
|-----------|----------|------------|
| **Dispatch Operations** | 27.04 | 47.9% |
| Vehicle Movement | 3.69 | 6.5% |
| History Updates | 1.63 | 2.9% |
| Block Initialization | 1.48 | 2.6% |
| Other (imports, equilibration, etc.) | 22.62 | 40.1% |

## Key Insights

### 1. Dispatch Operations Dominate (47.9% of time)

The dispatch system makes **51,000 distance calculations per block** to find the closest vehicle for each trip request:

- **Current Algorithm**: `_dispatch_vehicle_sparse()` performs O(n) linear search through all available vehicles
- **Scaling Issue**: With 3,000 vehicles and ~100 trips/block, this requires ~300,000 vehicle-trip comparisons per block
- **Distance Calculations**: Each comparison calls `dispatch_distance()` → `distance()`, accounting for 35% of total time

**Code Reference**: `dispatch.py:144-182`
```python
for vehicle in dispatchable_vehicles_list:
    dispatch_distance = city.dispatch_distance(
        location_from=vehicle.location,
        current_direction=vehicle.direction,
        location_to=trip.origin,
        vehicle_phase=vehicle.phase,
        threshold=current_minimum,
    )
```

### 2. Distance Calculation is Simple But Frequent

The `distance()` function (`atom.py:481-497`) implements Manhattan distance with torus wrapping:

- **Algorithm**: 8 lines of Python with `abs()` and `min()` operations
- **Frequency**: Called 51,000 times per block
- **Optimization**: Already uses early termination with threshold parameter
- **Efficiency**: Cannot be significantly optimized in isolation

### 3. Vehicle Movement is Already Efficient (6.5% of time)

Despite 3,200 calls per block per function, `update_direction()` and `update_location()` only consume 6.5% of time. This suggests:
- Movement logic is well-optimized
- No need for immediate optimization here
- Focus should remain on dispatch

## Optimization Recommendations

### Priority 1: Spatial Indexing for Vehicle Dispatch ⭐⭐⭐

**Impact**: High (potential 10-20x speedup for dispatch operations)
**Complexity**: Moderate
**Scaling**: Critical for larger fleets (>5,000 vehicles)

**Current Approach**: `_dispatch_vehicle_sparse()` uses O(n) linear search

**Recommended Approaches**:

1. **Grid-Based Spatial Index** (Simple, Good for Uniform Distribution)
   - Partition city into grid cells (e.g., 8×8 = 64 cells for 40×40 city)
   - Maintain dict mapping cell → list of vehicles in that cell
   - Search nearby cells first (expanding ring search)
   - **Pros**: Simple to implement, O(1) cell lookup
   - **Cons**: Less efficient for clustered vehicles

2. **Quadtree** (Better for Non-Uniform Distribution)
   - Hierarchical spatial partitioning
   - Dynamically adjusts to vehicle density
   - **Pros**: Efficient for clustered distributions
   - **Cons**: More complex to implement and maintain

3. **K-D Tree** (Optimal for Nearest-Neighbor Queries)
   - Binary space partitioning optimized for nearest-neighbor searches
   - **Pros**: O(log n) search time
   - **Cons**: Requires rebuilding or rebalancing as vehicles move

**Note**: Current code already collects `vehicles_at_location` (dispatch.py:74) but only tracks exact intersection positions. A grid-based index with larger cells would be more effective.

### Priority 2: Distance Calculation Optimization

**Impact**: Medium (2-3x speedup potential)
**Complexity**: Low to Moderate

**Options**:
1. **Memoization**: Cache recent distance calculations
   - Use LRU cache for frequently computed pairs
   - May have limited benefit if vehicle positions change constantly

2. **Vectorization**: Use NumPy for batch distance calculations
   - Compute distances for all vehicles to a trip in one vectorized operation
   - Trade memory for speed

3. **Lookup Tables**: Pre-compute distances for small cities
   - Only viable for small city sizes (<20×20)

### Priority 3: Profiling with Larger Scales

**Recommended Tests**:
- 10,000 vehicles to see if dispatch becomes even more dominant
- Larger city sizes (80×80) to test scaling behavior
- Different dispatch algorithms under various conditions

## What's Already Working Well

- ✅ **Early termination** in dispatch when distance == 1 (dispatch.py:173)
- ✅ **Threshold parameter** reduces unnecessary full distance calculations
- ✅ **Torus wrapping** has minimal overhead despite being called 51k times/block
- ✅ **Vehicle movement** is efficient relative to call frequency
- ✅ **Dense dispatch method** exists (`_dispatch_vehicle_dense()`) but isn't used in this config

## Future Work

1. **Benchmark spatial indexing implementations** against current linear search
2. **Profile memory usage** to understand tradeoffs of caching/indexing
3. **Test with heterogeneous vehicle distributions** (clustered vs. uniform)
4. **Consider hybrid approaches** that switch between sparse/dense methods based on vehicle density
5. **Evaluate using Cython or Numba** for distance calculations if they remain a bottleneck after spatial indexing

## Profiling Artifacts

All profiling data saved in:
- `profile_output.prof` - Raw cProfile data
- `analyze_profile.py` - Detailed analysis script
- `profile_summary.py` - Summary report script

**Regenerate Analysis**:
```bash
# Re-run profiling
uv run python -m cProfile -o profile_output.prof -m ridehail cities/toronto/coarse.config

# Analyze results
uv run python analyze_profile.py
uv run python profile_summary.py
```

---

**Analysis Date**: October 24, 2025
**Ridehail Version**: 2025.10.21
**Python Version**: 3.12
**Analyst**: Claude Code (Sonnet 4.5)
