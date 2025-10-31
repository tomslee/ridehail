#!/usr/bin/env python3
"""
Quick benchmark to measure equilibration performance impact.
"""

import time
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.atom import Equilibration

def benchmark_config(equilibrate, equilibration_type=Equilibration.PRICE):
    """Run a simulation and return timing stats."""
    config = RideHailConfig(use_config_file=False)
    config.city_size.value = 12
    config.vehicle_count.value = 30
    config.base_demand.value = 2.0
    config.time_blocks.value = 100
    config.animate.value = False
    config.equilibrate.value = equilibrate
    config.equilibration.value = equilibration_type
    config.equilibration_interval.value = 5
    config.random_number_seed.value = 42

    sim = RideHailSimulation(config)

    start_time = time.time()
    results = sim.simulate()
    end_time = time.time()

    return end_time - start_time

def main():
    print("Benchmarking equilibration performance...")
    print("=" * 60)

    # Baseline: no equilibration
    print("\n1. Running WITHOUT equilibration...")
    time_no_equil = benchmark_config(equilibrate=False)
    print(f"   Time: {time_no_equil:.3f} seconds")

    # With PRICE equilibration
    print("\n2. Running WITH PRICE equilibration...")
    time_price_equil = benchmark_config(equilibrate=True, equilibration_type=Equilibration.PRICE)
    print(f"   Time: {time_price_equil:.3f} seconds")

    # With WAIT_FRACTION equilibration
    print("\n3. Running WITH WAIT_FRACTION equilibration...")
    time_wait_equil = benchmark_config(equilibrate=True, equilibration_type=Equilibration.WAIT_FRACTION)
    print(f"   Time: {time_wait_equil:.3f} seconds")

    print("\n" + "=" * 60)
    print("RESULTS:")
    print(f"  No equilibration:        {time_no_equil:.3f}s (baseline)")
    print(f"  PRICE equilibration:     {time_price_equil:.3f}s ({time_price_equil/time_no_equil:.2f}x slower)")
    print(f"  WAIT_FRACTION equil:     {time_wait_equil:.3f}s ({time_wait_equil/time_no_equil:.2f}x slower)")
    print(f"  Overhead (PRICE):        {time_price_equil - time_no_equil:.3f}s")
    print(f"  Overhead (WAIT_FRAC):    {time_wait_equil - time_no_equil:.3f}s")

if __name__ == "__main__":
    main()
