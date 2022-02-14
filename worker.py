import sys
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation


def simulate():
    config = RideHailConfig()
    config.city_size.value = 8
    config.vehicle_count.value = 1
    config.base_demand.value = 0.5
    config.time_blocks.value = 10
    config.animate.value = False
    config.equilibrate.value = False
    config.run_sequence.value = False
    sim = RideHailSimulation(config)
    results = sim.simulate()
    return results
