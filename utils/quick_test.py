#!/usr/bin/env python3
"""Quick test: 120 vs 130 blocks"""

import time
import sys
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.atom import Equilibration

def quick_run(blocks, equilibration):
    old_argv = sys.argv
    sys.argv = ['test', 'feb_6_48.config']
    config = RideHailConfig(use_config_file=True)
    config.time_blocks.value = blocks
    config.equilibration.value = equilibration
    sys.argv = old_argv

    sim = RideHailSimulation(config)
    start = time.time()
    sim.simulate()
    return time.time() - start

print("Quick test: 120 vs 130 blocks with feb_6_48.config")
print("=" * 60)

for blocks in [120, 130]:
    print(f"\nBlocks: {blocks}")
    t_no = quick_run(blocks, Equilibration.NONE)
    print(f"  Without equilibration: {t_no:.1f}s")
    t_yes = quick_run(blocks, Equilibration.PRICE)
    print(f"  With equilibration:    {t_yes:.1f}s (slowdown: {t_yes/t_no:.2f}x)")
    print(f"  Overhead:   +{t_yes-t_no:.1f}s")
