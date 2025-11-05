#!/usr/bin/env python3
"""Check vehicle density over time."""

import sys
sys.argv = ['test', 'feb_6_48.config']
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.atom import VehiclePhase, Equilibration

config = RideHailConfig(use_config_file=True)
config.time_blocks.value = 120
config.equilibration.value = Equilibration.PRICE

sim = RideHailSimulation(config)

# Track densities
densities = []
original_next_block = sim.next_block

def tracking_next_block(block=None, *args, **kwargs):
    result = original_next_block(block=block, *args, **kwargs)
    if block is not None:
        p1_vehicles = len([v for v in sim.vehicles if v.phase == VehiclePhase.P1])
        total_intersections = sim.city_size * sim.city_size
        density = p1_vehicles / total_intersections
        densities.append((block, p1_vehicles, density))
    return result

sim.next_block = tracking_next_block
sim.simulate()

print(f"City size: {sim.city_size}x{sim.city_size} = {sim.city_size*sim.city_size} intersections")
print("\nDensity progression:")
print("Block  | P1 vehicles | Density  | Status")
print("-------|-------------|----------|--------")
for block, p1_count, density in densities[::10]:  # Every 10th block
    status = "sparse (<0.05)" if density < 0.05 else "dense (>=0.05)"
    print(f"{block:6} | {p1_count:11} | {density:.4f}   | {status}")

# Check blocks 100-120
print("\nFocus on blocks 100-120:")
print("Block  | P1 vehicles | Density")
for block, p1_count, density in densities[100:120]:
    print(f"{block:6} | {p1_count:11} | {density:.4f}")
