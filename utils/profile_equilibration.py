#!/usr/bin/env python3
"""
Profile equilibration to find bottlenecks.
"""

import cProfile
import pstats
from io import StringIO
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.atom import Equilibration

def run_with_equilibration():
    """Run simulation with PRICE equilibration."""
    config = RideHailConfig(use_config_file=False)
    config.city_size.value = 12
    config.vehicle_count.value = 30
    config.base_demand.value = 2.0
    config.time_blocks.value = 100
    config.equilibration.value = Equilibration.PRICE
    config.equilibration_interval.value = 5
    config.random_number_seed.value = 42

    sim = RideHailSimulation(config)
    results = sim.simulate()
    return results

def main():
    print("Profiling PRICE equilibration...")
    print("=" * 60)

    profiler = cProfile.Profile()
    profiler.enable()
    run_with_equilibration()
    profiler.disable()

    # Print stats
    s = StringIO()
    stats = pstats.Stats(profiler, stream=s)
    stats.sort_stats('cumulative')
    stats.print_stats(30)  # Top 30 functions by cumulative time

    print(s.getvalue())

if __name__ == "__main__":
    main()
