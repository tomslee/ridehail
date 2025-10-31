#!/usr/bin/env python3
"""
Test to verify that pickup_time affects simulation statistics,
not just visual output.
"""
import sys
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation

def run_test_simulation(pickup_time_value):
    """Run a simulation with specified pickup_time and return key metrics"""
    # Create config without loading from file or command line
    config = RideHailConfig(use_config_file=False)

    # Set essential parameters for a minimal test
    config.pickup_time.value = pickup_time_value
    config.animation_style.value = "none"
    config.animate.value = False
    config.time_blocks.value = 100
    config.random_number_seed.value = 42

    # Basic city parameters
    config.city_size.value = 10
    config.vehicle_count.value = 10
    config.base_demand.value = 2.0

    # Create and run simulation
    sim = RideHailSimulation(config)
    results_obj = sim.simulate()

    # Get result measures as a dictionary
    measures = results_obj.get_result_measures()

    # Extract key metrics that should be affected by pickup_time
    return {
        'pickup_time': pickup_time_value,
        'vehicle_p2_fraction': measures.get('VEHICLE_FRACTION_P2', 0),
        'trip_wait_time': measures.get('TRIP_MEAN_WAIT_TIME', 0),
        'vehicle_p3_fraction': measures.get('VEHICLE_FRACTION_P3', 0),
        'trip_ride_time': measures.get('TRIP_MEAN_RIDE_TIME', 0),
    }

def main():
    print("Testing pickup_time parameter effect on simulation statistics...\n")

    # Test with pickup_time = 0 (instant pickup)
    print("Running simulation with pickup_time = 0...")
    results_0 = run_test_simulation(0)

    # Test with pickup_time = 3 (3 block dwell time)
    print("Running simulation with pickup_time = 3...")
    results_3 = run_test_simulation(3)

    print("\n" + "="*70)
    print("RESULTS COMPARISON")
    print("="*70)

    print(f"\n{'Metric':<30} {'pickup_time=0':>15} {'pickup_time=3':>15} {'Difference':>10}")
    print("-"*70)

    metrics = [
        ('vehicle_p2_fraction', 'Vehicle P2 Fraction'),
        ('trip_wait_time', 'Trip Wait Time'),
        ('vehicle_p3_fraction', 'Vehicle P3 Fraction'),
        ('trip_ride_time', 'Trip Ride Time'),
    ]

    for key, label in metrics:
        val_0 = results_0[key]
        val_3 = results_3[key]
        diff = val_3 - val_0
        print(f"{label:<30} {val_0:>15.4f} {val_3:>15.4f} {diff:>+10.4f}")

    print("\n" + "="*70)
    print("ANALYSIS")
    print("="*70)

    # Check if pickup_time affected the metrics
    p2_fraction_increased = results_3['vehicle_p2_fraction'] > results_0['vehicle_p2_fraction']
    wait_time_increased = results_3['trip_wait_time'] > results_0['trip_wait_time']
    p3_fraction_unchanged = abs(results_3['vehicle_p3_fraction'] - results_0['vehicle_p3_fraction']) < 0.05

    print("\nExpected behavior (from pickup_time_requirements.md):")
    print("  - Vehicle P2 fraction should INCREASE (vehicles pause at pickup)")
    print("  - Trip wait time should INCREASE (includes pickup dwell time)")
    print("  - Vehicle P3 fraction should be UNCHANGED (riding time unaffected)")

    print("\nActual behavior:")
    print(f"  - Vehicle P2 fraction increased: {'✓ YES' if p2_fraction_increased else '✗ NO'}")
    print(f"  - Trip wait time increased: {'✓ YES' if wait_time_increased else '✗ NO'}")
    p3_change = results_3['vehicle_p3_fraction'] - results_0['vehicle_p3_fraction']
    p3_status = '✓ YES' if p3_fraction_unchanged else f'✗ NO (changed by {p3_change:.4f})'
    print(f"  - Vehicle P3 fraction unchanged: {p3_status}")

    print("\n" + "="*70)
    if p2_fraction_increased and wait_time_increased:
        print("CONCLUSION: pickup_time IS affecting simulation statistics ✓")
        print("The parameter is working correctly in the core simulation logic.")
    else:
        print("CONCLUSION: pickup_time is NOT affecting simulation statistics ✗")
        print("This indicates a bug in the core simulation implementation.")
    print("="*70)

if __name__ == "__main__":
    main()
