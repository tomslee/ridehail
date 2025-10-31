#!/usr/bin/env python3
"""
Test performance scaling with increasing block counts.
"""

import time
import sys
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.atom import TripPhase

def run_simulation(config_file, time_blocks, equilibrate):
    """Run simulation and return timing."""
    # Temporarily modify sys.argv to pass config file
    old_argv = sys.argv
    sys.argv = ['test', config_file]

    config = RideHailConfig(use_config_file=True)
    config.time_blocks.value = time_blocks
    config.equilibrate.value = equilibrate
    config.animate.value = False

    sys.argv = old_argv

    sim = RideHailSimulation(config)

    # Track unassigned trips in later blocks
    unassigned_late = []
    original_next_block = sim.next_block
    def tracking_next_block(block=None, *args, **kwargs):
        result = original_next_block(block=block, *args, **kwargs)
        if block and block >= 100:
            unassigned = len([t for t in sim.trips.values() if t.phase == TripPhase.UNASSIGNED])
            unassigned_late.append(unassigned)
        return result

    sim.next_block = tracking_next_block

    start = time.time()
    sim.simulate()
    elapsed = time.time() - start

    avg_unassigned_late = sum(unassigned_late) / len(unassigned_late) if unassigned_late else 0

    return elapsed, len(sim.vehicles), avg_unassigned_late

print("Testing performance scaling with block count...")
print("=" * 80)

test_blocks = [120, 200, 300, 500]

for blocks in test_blocks:
    print(f"\nTesting with -b {blocks}:")

    # Without equilibration
    time_no_eq, _, _ = run_simulation('feb_6_48.config', blocks, False)
    print(f"  Without -e: {time_no_eq:.1f}s")

    # With equilibration
    time_eq, final_vehicles, avg_unassigned = run_simulation('feb_6_48.config', blocks, True)
    print(f"  With -e:    {time_eq:.1f}s (slowdown: {time_eq/time_no_eq:.2f}x)")
    print(f"              Final vehicles: {final_vehicles}, Avg unassigned (blocks 100+): {avg_unassigned:.0f}")
    print(f"  Difference: {time_eq - time_no_eq:.1f}s")
