import sys
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation


def simulate(vehicle_count):
    config = RideHailConfig()
    config.city_size.value = 8
    config.vehicle_count.value = vehicle_count
    config.base_demand.value = 1.0
    config.time_blocks.value = 100
    config.animate.value = False
    config.equilibrate.value = False
    config.run_sequence.value = False
    sim = RideHailSimulation(config)
    results = sim.simulate()
    # print(f"worker.py says {results.end_state}")
    return results.end_state
