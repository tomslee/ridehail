#!/usr/bin/env python3
"""Test which dispatch mode is being used."""

import sys
sys.argv = ['test', 'feb_6_48.config']
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.atom import Equilibration

config = RideHailConfig(use_config_file=True)
config.time_blocks.value = 120
config.equilibration.value = Equilibration.PRICE

sim = RideHailSimulation(config)

# Monkey patch to track which dispatch method is used
dispatch_modes = []
from ridehail.dispatch import Dispatch

original_sparse = Dispatch._dispatch_vehicle_sparse
original_dense = Dispatch._dispatch_vehicle_dense

def tracking_sparse(self, *args, **kwargs):
    dispatch_modes.append('sparse')
    return original_sparse(self, *args, **kwargs)

def tracking_dense(self, *args, **kwargs):
    dispatch_modes.append('dense')
    return original_dense(self, *args, **kwargs)

Dispatch._dispatch_vehicle_sparse = tracking_sparse
Dispatch._dispatch_vehicle_dense = tracking_dense

# Run simulation
sim.simulate()

# Restore
Dispatch._dispatch_vehicle_sparse = original_sparse
Dispatch._dispatch_vehicle_dense = original_dense

# Analyze
sparse_count = dispatch_modes.count('sparse')
dense_count = dispatch_modes.count('dense')

print(f"Total dispatch calls: {len(dispatch_modes)}")
print(f"  Sparse algorithm: {sparse_count}")
print(f"  Dense algorithm: {dense_count}")

# Check when mode switched
if sparse_count > 0 and dense_count > 0:
    first_sparse = dispatch_modes.index('sparse')
    print(f"First sparse call at dispatch #{first_sparse}")
