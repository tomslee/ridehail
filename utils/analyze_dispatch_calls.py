#!/usr/bin/env python3
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.atom import Equilibration, TripPhase

def count_operations(equilibrate, equilibration_type=None):
    config = RideHailConfig(use_config_file=False)
    config.city_size.value = 12
    config.vehicle_count.value = 30
    config.base_demand.value = 2.0
    config.time_blocks.value = 100
    config.animate.value = False
    config.equilibrate.value = equilibrate
    if equilibration_type:
        config.equilibration.value = equilibration_type
    config.equilibration_interval.value = 5
    config.random_number_seed.value = 42

    sim = RideHailSimulation(config)

    # Track dispatch calls
    dispatch_call_count = 0
    unassigned_trip_counts = []

    original_next_block = sim.next_block
    def tracking_next_block(*args, **kwargs):
        nonlocal dispatch_call_count
        result = original_next_block(*args, **kwargs)
        unassigned = len([t for t in sim.trips.values() if t.phase == TripPhase.UNASSIGNED])
        unassigned_trip_counts.append(unassigned)
        return result

    sim.next_block = tracking_next_block

    # Monkey patch dispatch to count calls
    from ridehail.dispatch import Dispatch
    original_dispatch = Dispatch._dispatch_vehicle_default
    def counting_dispatch(self, *args, **kwargs):
        nonlocal dispatch_call_count
        dispatch_call_count += 1
        return original_dispatch(self, *args, **kwargs)
    Dispatch._dispatch_vehicle_default = counting_dispatch

    sim.simulate()

    # Restore original
    Dispatch._dispatch_vehicle_default = original_dispatch

    return {
        'dispatch_calls': dispatch_call_count,
        'total_trips': sim.next_trip_id,
        'max_unassigned': max(unassigned_trip_counts) if unassigned_trip_counts else 0,
        'avg_unassigned': sum(unassigned_trip_counts) / len(unassigned_trip_counts) if unassigned_trip_counts else 0
    }

print("Analyzing dispatch operations...")
print("=" * 60)

no_equil = count_operations(False)
print(f"\nNo equilibration:")
print(f"  Dispatch calls: {no_equil['dispatch_calls']}")
print(f"  Total trips: {no_equil['total_trips']}")
print(f"  Max unassigned at once: {no_equil['max_unassigned']}")
print(f"  Avg unassigned per block: {no_equil['avg_unassigned']:.1f}")

price_equil = count_operations(True, Equilibration.PRICE)
print(f"\nPRICE equilibration:")
print(f"  Dispatch calls: {price_equil['dispatch_calls']}")
print(f"  Total trips: {price_equil['total_trips']}")
print(f"  Max unassigned at once: {price_equil['max_unassigned']}")
print(f"  Avg unassigned per block: {price_equil['avg_unassigned']:.1f}")

print(f"\nRatio (PRICE/None): {price_equil['dispatch_calls'] / no_equil['dispatch_calls']:.1f}x dispatch calls")
