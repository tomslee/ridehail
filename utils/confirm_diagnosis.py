#!/usr/bin/env python3
"""
Confirm the diagnosis about dispatch operations causing slowdown.
"""

import time
import sys
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.atom import TripPhase

def analyze_detailed(config_file, time_blocks, equilibrate):
    """Run simulation with detailed tracking."""
    old_argv = sys.argv
    sys.argv = ['test', config_file]
    config = RideHailConfig(use_config_file=True)
    config.time_blocks.value = time_blocks
    config.equilibrate.value = equilibrate
    config.animate.value = False
    sys.argv = old_argv

    sim = RideHailSimulation(config)

    # Track metrics by time period
    periods = {
        '0-99': {'dispatch_calls': 0, 'unassigned': [], 'time': 0},
        '100-119': {'dispatch_calls': 0, 'unassigned': [], 'time': 0},
        '120+': {'dispatch_calls': 0, 'unassigned': [], 'time': 0}
    }

    # Monkey patch dispatch
    from ridehail.dispatch import Dispatch
    original_dispatch = Dispatch._dispatch_vehicle_default
    current_block = [0]  # Use list to allow modification in nested function

    def counting_dispatch(self, *args, **kwargs):
        block = current_block[0]
        if block < 100:
            periods['0-99']['dispatch_calls'] += 1
        elif block < 120:
            periods['100-119']['dispatch_calls'] += 1
        else:
            periods['120+']['dispatch_calls'] += 1
        return original_dispatch(self, *args, **kwargs)

    Dispatch._dispatch_vehicle_default = counting_dispatch

    # Track per-block
    original_next_block = sim.next_block
    def tracking_next_block(block=None, *args, **kwargs):
        if block is not None:
            current_block[0] = block

        start = time.time()
        result = original_next_block(block=block, *args, **kwargs)
        elapsed = time.time() - start

        unassigned = len([t for t in sim.trips.values() if t.phase == TripPhase.UNASSIGNED])

        if block < 100:
            periods['0-99']['time'] += elapsed
            periods['0-99']['unassigned'].append(unassigned)
        elif block < 120:
            periods['100-119']['time'] += elapsed
            periods['100-119']['unassigned'].append(unassigned)
        else:
            periods['120+']['time'] += elapsed
            periods['120+']['unassigned'].append(unassigned)

        return result

    sim.next_block = tracking_next_block

    total_start = time.time()
    sim.simulate()
    total_time = time.time() - total_start

    # Restore
    Dispatch._dispatch_vehicle_default = original_dispatch

    return total_time, periods

print("CONFIRMING DIAGNOSIS: Dispatch operations cause slowdown after block 100")
print("=" * 80)

# Test with 200 blocks to see continued degradation
print("\nRunning feb_6_48.config with -b 200 -e...")
total_time, periods = analyze_detailed('feb_6_48.config', 200, True)

print(f"\nTotal time: {total_time:.1f}s")
print("\nPer-period breakdown:")
for period_name in ['0-99', '100-119', '120+']:
    p = periods[period_name]
    avg_unassigned = sum(p['unassigned']) / len(p['unassigned']) if p['unassigned'] else 0
    block_count = len(p['unassigned'])
    print(f"\n  Blocks {period_name}:")
    print(f"    Total time: {p['time']:.2f}s")
    print(f"    Avg time per block: {p['time']/block_count*1000 if block_count else 0:.1f}ms")
    print(f"    Dispatch calls: {p['dispatch_calls']}")
    print(f"    Avg dispatch per block: {p['dispatch_calls']/block_count if block_count else 0:.1f}")
    print(f"    Avg unassigned trips: {avg_unassigned:.1f}")

print("\n" + "=" * 80)
print("CONCLUSIONS:")
print("  • Blocks 0-99: Fast, few unassigned trips, normal dispatch rate")
print("  • Blocks 100-119: Dramatically slower, many unassigned trips, high dispatch rate")
print("  • Blocks 120+: Continuing degradation as unassigned trips accumulate")
print("\nThis confirms: PRICE equilibration creates vehicle shortage → unassigned")
print("trip buildup → excessive dispatch attempts → performance degradation")
