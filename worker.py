from ridehail.config import RideHailConfig
from ridehail.simulation import (RideHailSimulation)
from ridehail.atom import Direction
import copy
import numpy as np

sim = None
old_results = None
frame_index = 0


# Class to hold arrays to do smoothing averages
# From
# https://stackoverflow.com/questions/42771110/fastest-way-to-left-cycle-a-numpy-array-like-pop-push-for-a-queue
class CircularBuffer:
    def __init__(self, maxlen: int):
        # allocate the memory we need ahead of time
        self.max_length: int = maxlen
        self.queue_tail: int = maxlen - 1
        self.rec_queue = np.zeros(maxlen)
        self.queue_tail = maxlen - 1

    def to_array(self) -> np.array:
        head = (self.queue_tail + 1) % self.max_length
        return np.roll(self.rec_queue, -head)  # this will force a copy

    def enqueue(self, new_data: np.array) -> None:
        # move tail pointer forward then insert at the tail of the queue
        # to enforce max length of recording
        self.queue_tail = (self.queue_tail + 1) % self.max_length
        self.rec_queue[self.queue_tail] = new_data

    def peek(self) -> int:
        queue_head = (self.queue_tail + 1) % self.max_length
        return self.rec_queue[queue_head]

    def replace_item_at(self, index: int, new_value: int):
        loc = (self.queue_tail + 1 + index) % self.max_length
        self.rec_queue[loc] = new_value

    def item_at(self, index: int) -> int:
        # the item we want will be at head + index
        loc = (self.queue_tail + 1 + index) % self.max_length
        return self.rec_queue[loc]

    def __repr__(self):
        return "tail: " + str(self.queue_tail) + "\narray: " + str(
            self.rec_queue)

    def __str__(self):
        return "tail: " + str(self.queue_tail) + "\narray: " + str(
            self.rec_queue)
        # return str(self.to_array())


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
    print(f"worker.py says P3={results.end_state['vehicle_fraction_idle']}")
    return results.end_state


def setup_map_simulation(city_size, vehicle_count):
    # results = RideHailSimulationResults()
    global sim
    sim = MapSimulation(city_size, vehicle_count)


def setup_stats_simulation(city_size, vehicle_count):
    global sim
    sim = StatsSimulation(city_size, vehicle_count)


class MapSimulation():
    def __init__(self, city_size, vehicle_count):
        self.city_size = city_size
        self.vehicle_count = vehicle_count
        self.frame_index = 0
        self.old_results = None
        config = RideHailConfig()
        config.city_size.value = city_size
        config.vehicle_count.value = vehicle_count
        config.base_demand.value = 1.0
        config.time_blocks.value = 100
        config.animate.value = False
        config.equilibrate.value = False
        config.run_sequence.value = False
        config.interpolate.value = 0
        self.sim = RideHailSimulation(config)

    def next_frame(self):
        if self.frame_index % 2 == 0:
            # It's a real block: do the simulation
            # block_index = int(frame_index / 2)
            results = self.sim.next_block(output_file_handle=None,
                                          return_values="map")
            self.old_results = copy.deepcopy(results)
        else:
            for vehicle in self.old_results[1]:
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
            results = [0, [vehicle for vehicle in self.old_results[1]]]
        self.frame_index += 1
        return results[1]


class StatsSimulation():
    def __init__(self, city_size, vehicle_count, smoothing_window=5):
        self.city_size = city_size
        self.vehicle_count = vehicle_count
        self.frame_index = 0
        config = RideHailConfig()
        config.city_size.value = city_size
        config.vehicle_count.value = vehicle_count
        config.base_demand.value = 1.0
        config.time_blocks.value = 100
        config.animate.value = False
        config.equilibrate.value = False
        config.run_sequence.value = False
        config.interpolate.value = 0
        config.smoothing_window.value = smoothing_window
        self.sim = RideHailSimulation(config)
        self.p3_fraction = CircularBuffer(smoothing_window)

    # results = RideHailSimulationResults()

    def next_frame(self):
        results = self.sim.next_block(output_file_handle=None,
                                      return_values="stats")
        self.frame_index += 1
        return [results]
