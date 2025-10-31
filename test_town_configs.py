#!/usr/bin/env python3
"""
Test to verify pickup_time is being read from town config files
and affects simulation results.
"""
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
import sys

def test_config_file(config_file):
    """Test a single config file and return key metrics"""
    print(f"\n{'='*70}")
    print(f"Testing: {config_file}")
    print(f"{'='*70}")

    # Override sys.argv to simulate command line
    original_argv = sys.argv.copy()
    sys.argv = ['test', config_file]

    try:
        config = RideHailConfig()

        # Check if pickup_time was read correctly
        print(f"Config pickup_time value: {config.pickup_time.value}")

        # Create simulation
        sim = RideHailSimulation(config)

        # Check if it was transferred to simulation
        print(f"Simulation pickup_time value: {sim.pickup_time}")

        # Run simulation
        print("Running simulation...")
        results_obj = sim.simulate()
        measures = results_obj.get_result_measures()

        return {
            'config_file': config_file,
            'pickup_time_config': config.pickup_time.value,
            'pickup_time_sim': sim.pickup_time,
            'vehicle_p2_fraction': measures.get('VEHICLE_FRACTION_P2', 0),
            'trip_wait_time': measures.get('TRIP_MEAN_WAIT_TIME', 0),
            'vehicle_p3_fraction': measures.get('VEHICLE_FRACTION_P3', 0),
        }
    finally:
        sys.argv = original_argv

def main():
    print("Testing pickup_time parameter in town config files...")

    # Test both config files
    results_town3 = test_config_file('local/town3.config')
    results_town4 = test_config_file('local/town4.config')

    print(f"\n{'='*70}")
    print("COMPARISON")
    print(f"{'='*70}\n")

    print(f"{'Config File':<25} {'town3.config':>20} {'town4.config':>20}")
    print("-"*70)
    print(f"{'pickup_time (config):':<25} {results_town3['pickup_time_config']:>20} {results_town4['pickup_time_config']:>20}")
    print(f"{'pickup_time (sim):':<25} {results_town3['pickup_time_sim']:>20} {results_town4['pickup_time_sim']:>20}")
    print()
    print(f"{'Vehicle P2 Fraction:':<25} {results_town3['vehicle_p2_fraction']:>20.4f} {results_town4['vehicle_p2_fraction']:>20.4f}")
    print(f"{'Trip Wait Time:':<25} {results_town3['trip_wait_time']:>20.4f} {results_town4['trip_wait_time']:>20.4f}")
    print(f"{'Vehicle P3 Fraction:':<25} {results_town3['vehicle_p3_fraction']:>20.4f} {results_town4['vehicle_p3_fraction']:>20.4f}")

    print(f"\n{'='*70}")
    print("ANALYSIS")
    print(f"{'='*70}\n")

    # Check if pickup_time values are different
    pickup_diff = results_town4['pickup_time_config'] != results_town3['pickup_time_config']
    print(f"pickup_time values are different: {pickup_diff}")

    if pickup_diff:
        # Check if results are different
        p2_diff = abs(results_town4['vehicle_p2_fraction'] - results_town3['vehicle_p2_fraction'])
        wait_diff = abs(results_town4['trip_wait_time'] - results_town3['trip_wait_time'])

        print(f"  P2 fraction difference: {p2_diff:.4f}")
        print(f"  Wait time difference: {wait_diff:.4f}")

        if p2_diff > 0.01 or wait_diff > 0.5:
            print("\n✓ PASS: pickup_time IS affecting simulation results")
        else:
            print("\n✗ FAIL: pickup_time is NOT affecting simulation results")
            print("  (Results are too similar despite different pickup_time values)")
    else:
        print("\n⚠ WARNING: Both configs have same pickup_time value")

    print(f"{'='*70}\n")

if __name__ == "__main__":
    main()
