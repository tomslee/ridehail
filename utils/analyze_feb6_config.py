#!/usr/bin/env python3
"""
Analyze the feb_6_48.config to verify dispatch call hypothesis.
"""

import time
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.atom import TripPhase

def analyze_simulation(config_file, time_blocks, equilibrate):
    """Run simulation and track key metrics."""
    import sys

    # Temporarily modify sys.argv to pass config file
    old_argv = sys.argv
    sys.argv = ['analyze', config_file]

    config = RideHailConfig(use_config_file=True)
    config.time_blocks.value = time_blocks
    config.equilibrate.value = equilibrate
    config.animate.value = False  # Disable animation for cleaner output

    sys.argv = old_argv

    print(f"   [Config loaded: vehicles={config.vehicle_count.value}, demand={config.base_demand.value}, city_size={config.city_size.value}]")

    sim = RideHailSimulation(config)

    # Track metrics
    vehicle_counts = []
    unassigned_counts = []
    dispatch_call_count = 0
    block_times = []

    # Monkey patch to count dispatch calls
    from ridehail.dispatch import Dispatch
    original_dispatch = Dispatch._dispatch_vehicle_default
    def counting_dispatch(self, *args, **kwargs):
        nonlocal dispatch_call_count
        dispatch_call_count += 1
        return original_dispatch(self, *args, **kwargs)
    Dispatch._dispatch_vehicle_default = counting_dispatch

    # Track per-block metrics
    original_next_block = sim.next_block
    def tracking_next_block(block=None, *args, **kwargs):
        block_start = time.time()
        result = original_next_block(block=block, *args, **kwargs)
        block_end = time.time()

        vehicle_counts.append(len(sim.vehicles))
        unassigned = len([t for t in sim.trips.values() if t.phase == TripPhase.UNASSIGNED])
        unassigned_counts.append(unassigned)
        block_times.append(block_end - block_start)

        return result

    sim.next_block = tracking_next_block

    # Run simulation
    start_time = time.time()
    sim.simulate()
    total_time = time.time() - start_time

    # Restore original
    Dispatch._dispatch_vehicle_default = original_dispatch

    return {
        'total_time': total_time,
        'vehicle_counts': vehicle_counts,
        'unassigned_counts': unassigned_counts,
        'dispatch_calls': dispatch_call_count,
        'total_trips': sim.next_trip_id,
        'block_times': block_times,
    }

print("Analyzing feb_6_48.config...")
print("=" * 80)

# Test 1: 120 blocks without equilibration
print("\n1. Running with -b 120 (WITHOUT -e)...")
result_no_equil = analyze_simulation('feb_6_48.config', 120, False)
print(f"   Total time: {result_no_equil['total_time']:.2f}s")
print(f"   Total trips: {result_no_equil['total_trips']}")
print(f"   Dispatch calls: {result_no_equil['dispatch_calls']}")
print(f"   Vehicle count: {result_no_equil['vehicle_counts'][0]} -> {result_no_equil['vehicle_counts'][-1]}")
print(f"   Max unassigned trips: {max(result_no_equil['unassigned_counts'])}")
print(f"   Avg unassigned trips: {sum(result_no_equil['unassigned_counts'])/len(result_no_equil['unassigned_counts']):.1f}")

# Test 2: 120 blocks with equilibration
print("\n2. Running with -b 120 -e (WITH equilibration)...")
result_with_equil = analyze_simulation('feb_6_48.config', 120, True)
print(f"   Total time: {result_with_equil['total_time']:.2f}s")
print(f"   Total trips: {result_with_equil['total_trips']}")
print(f"   Dispatch calls: {result_with_equil['dispatch_calls']}")
print(f"   Vehicle count: {result_with_equil['vehicle_counts'][0]} -> {result_with_equil['vehicle_counts'][-1]}")
print(f"   Max unassigned trips: {max(result_with_equil['unassigned_counts'])}")
print(f"   Avg unassigned trips: {sum(result_with_equil['unassigned_counts'])/len(result_with_equil['unassigned_counts']):.1f}")

# Analyze block-by-block timing for equilibration case
print("\n3. Block timing analysis (WITH equilibration)...")
print(f"   Blocks 0-49 avg time: {sum(result_with_equil['block_times'][:50])/50*1000:.1f}ms")
print(f"   Blocks 50-99 avg time: {sum(result_with_equil['block_times'][50:100])/50*1000:.1f}ms")
print(f"   Blocks 100-119 avg time: {sum(result_with_equil['block_times'][100:120])/20*1000:.1f}ms")
print(f"   Slowest block: {max(result_with_equil['block_times'])*1000:.1f}ms")

# Analyze unassigned trip buildup over time
print("\n4. Unassigned trip buildup (WITH equilibration)...")
print(f"   Blocks 0-49 avg unassigned: {sum(result_with_equil['unassigned_counts'][:50])/50:.1f}")
print(f"   Blocks 50-99 avg unassigned: {sum(result_with_equil['unassigned_counts'][50:100])/50:.1f}")
print(f"   Blocks 100-119 avg unassigned: {sum(result_with_equil['unassigned_counts'][100:120])/20:.1f}")

print("\n" + "=" * 80)
print("COMPARISON:")
print(f"  Time ratio (with/without equil): {result_with_equil['total_time']/result_no_equil['total_time']:.2f}x")
print(f"  Dispatch call ratio: {result_with_equil['dispatch_calls']/result_no_equil['dispatch_calls']:.1f}x")
print(f"  Avg unassigned ratio: {(sum(result_with_equil['unassigned_counts'])/len(result_with_equil['unassigned_counts']))/(sum(result_no_equil['unassigned_counts'])/len(result_no_equil['unassigned_counts']) or 0.01):.1f}x")
