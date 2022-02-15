from ridehail.config import RideHailConfig
from ridehail.simulation import (RideHailSimulation)

config = RideHailConfig()
sim = None


def simulate(vehicle_count):
    config.city_size.value = 8
    config.vehicle_count.value = vehicle_count
    config.base_demand.value = 1.0
    config.time_blocks.value = 100
    config.animate.value = False
    config.equilibrate.value = False
    config.run_sequence.value = False
    sim = RideHailSimulation(config)
    results = sim.simulate()
    print(f"worker.py says P3={results.end_state['vehicle_fraction_idle']}")
    return results.end_state


def setup_simulation(city_size, vehicle_count):
    global sim
    config.city_size.value = city_size
    config.vehicle_count.value = vehicle_count
    config.base_demand.value = 1.0
    config.time_blocks.value = 100
    config.animate.value = False
    config.equilibrate.value = False
    config.run_sequence.value = False
    sim = RideHailSimulation(config)
    # results = RideHailSimulationResults()


def next_block(block_index):
    global sim
    # block_results = sim.next_block(output_file_handle=None,
    #                               block=block_index,
    #                              return_values="stats")
    block_results = sim.next_block(output_file_handle=None,
                                   block=block_index,
                                   return_values="map")
    # print(f"worker.py says vehicles={block_results}")
    return block_results
