#!/usr/bin/env python3
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.atom import Equilibration

config = RideHailConfig(use_config_file=False)
config.city_size.value = 12
config.vehicle_count.value = 30
config.base_demand.value = 2.0
config.time_blocks.value = 100
config.equilibration.value = Equilibration.PRICE
config.equilibration_interval.value = 5
config.random_number_seed.value = 42

sim = RideHailSimulation(config)

# Track vehicle count changes
vehicle_counts = []
original_next_block = sim.next_block

def tracking_next_block(*args, **kwargs):
    result = original_next_block(*args, **kwargs)
    vehicle_counts.append(len(sim.vehicles))
    return result

sim.next_block = tracking_next_block
sim.simulate()

changes = [i for i in range(1, len(vehicle_counts)) if vehicle_counts[i] != vehicle_counts[i-1]]
print(f'Vehicle count range: {min(vehicle_counts)} to {max(vehicle_counts)}')
print(f'Vehicle count at start: {vehicle_counts[0]}')
print(f'Vehicle count at end: {vehicle_counts[-1]}')
print(f'Number of blocks with vehicle count changes: {len(changes)}')
print(f'Blocks where changes occurred: {changes[:10]}...')  # First 10
