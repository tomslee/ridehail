from ridehail.config import RideHailConfig
from ridehail.simulation import (RideHailSimulation)
from ridehail.atom import Direction
import copy

config = RideHailConfig()
sim = None
old_results = None
frame_index = 0


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
    config.interpolate.value = 0
    sim = RideHailSimulation(config)
    # results = RideHailSimulationResults()


def next_frame():
    global sim, old_results, config, frame_index
    if frame_index % 2 == 0:
        # It's a real block: do the simulation
        # block_index = int(frame_index / 2)
        results = sim.next_block(
            output_file_handle=None,
            # block=block_index,
            return_values="map")
        old_results = copy.deepcopy(results)
    else:
        for vehicle in old_results[1]:
            direction = vehicle[2]
            if direction == Direction.NORTH:
                vehicle[1][1] += 0.5
            elif direction == Direction.EAST:
                vehicle[1][0] += 0.5
            elif direction == Direction.SOUTH:
                vehicle[1][1] -= 0.5
            elif direction == Direction.WEST:
                vehicle[1][0] -= 0.5
            # vehicle[1][0] = vehicle[1][0] % config.city_size.value
            # vehicle[1][1] = vehicle[1][1] % config.city_size.value
        results = [0, [vehicle for vehicle in old_results[1]]]
    frame_index += 1
    return results[1]
