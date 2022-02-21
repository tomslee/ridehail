from ridehail.config import RideHailConfig
from ridehail.simulation import (RideHailSimulation)
from ridehail.atom import (Direction, PlotArray, History)
import copy
import numpy as np

sim = None


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

    def enqueue(self, new_data: np.array) -> None:
        # move tail pointer forward then insert at the tail of the queue
        # to enforce max length of recording
        self.queue_tail = (self.queue_tail + 1) % self.max_length
        self.rec_queue[self.queue_tail] = new_data

    def get_head(self) -> int:
        queue_head = (self.queue_tail + 1) % self.max_length
        return self.rec_queue[queue_head]

    def get_tail(self) -> int:
        return self.rec_queue[self.queue_tail]

    def push(self, new_data: np.array) -> float:
        head = self.get_head()
        self.enqueue(new_data)
        tail = self.get_tail()
        return (tail - head)

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
    config.time_blocks.value = 2000
    config.animate.value = False
    config.equilibrate.value = False
    config.run_sequence.value = False
    sim = RideHailSimulation(config)
    results = sim.simulate()
    # print(f"worker.py says P3={results.end_state['vehicle_fraction_idle']}")
    return results.end_state


def init_map_simulation(city_size, vehicle_count, base_demand):
    # results = RideHailSimulationResults()
    global sim
    sim = MapSimulation(int(city_size), int(vehicle_count), float(base_demand))


def init_stats_simulation(city_size, vehicle_count, base_demand):
    global sim
    print(f"wo: cs={city_size}, bd={base_demand}")
    sim = StatsSimulation(int(city_size), int(vehicle_count),
                          float(base_demand))


class MapSimulation():
    def __init__(self, city_size, vehicle_count, base_demand=1):
        self.city_size = int(city_size)
        self.vehicle_count = int(vehicle_count)
        self.frame_index = 0
        self.old_results = None
        self.base_demand = float(base_demand)
        config = RideHailConfig()
        config.city_size.value = self.city_size
        config.vehicle_count.value = self.vehicle_count
        config.base_demand.value = self.base_demand
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
    def __init__(self,
                 city_size,
                 vehicle_count,
                 base_demand=1,
                 smoothing_window=20):
        self.city_size = city_size
        self.vehicle_count = vehicle_count
        self.base_demand = base_demand
        self.frame_index = 0
        self.smoothing_window = smoothing_window
        config = RideHailConfig()
        config.city_size.value = self.city_size
        config.vehicle_count.value = self.vehicle_count
        config.base_demand.value = self.base_demand
        config.time_blocks.value = 2000
        config.animate.value = False
        config.equilibrate.value = False
        config.run_sequence.value = False
        config.interpolate.value = 0
        config.smoothing_window.value = self.smoothing_window
        self.sim = RideHailSimulation(config)
        self.plot_buffers = {}
        self.results = {}
        for plot_property in list(PlotArray):
            self.plot_buffers[plot_property] = CircularBuffer(smoothing_window)
            self.results[plot_property] = 0

    # results = RideHailSimulationResults()

    def next_frame(self):
        # Get the latest History items in a dictionary
        frame_results = self.sim.next_block(output_file_handle=None,
                                            return_values="stats")
        # Get the total vehicle time over the smoothing window
        # print(f"frame_results={frame_results}")
        self.results[PlotArray.VEHICLE_TIME] += self.plot_buffers[
            PlotArray.VEHICLE_TIME].push(frame_results[History.VEHICLE_TIME])
        window_vehicle_time = float(self.results[PlotArray.VEHICLE_TIME])
        self.results[PlotArray.TRIP_RIDING_TIME] += self.plot_buffers[
            PlotArray.TRIP_RIDING_TIME].push(
                frame_results[History.TRIP_RIDING_TIME])
        window_riding_time = float(self.results[PlotArray.TRIP_RIDING_TIME])

        if window_vehicle_time > 0:
            # PlotArray.VEHICLE_IDLE_FRACTION
            self.results[PlotArray.VEHICLE_IDLE_FRACTION] += self.plot_buffers[
                PlotArray.VEHICLE_IDLE_FRACTION].push(
                    float(frame_results[History.VEHICLE_P1_TIME]) /
                    window_vehicle_time)
            # PlotArray.VEHICLE_DISPATCH_FRACTION
            self.results[PlotArray.VEHICLE_DISPATCH_FRACTION] += (
                self.plot_buffers[PlotArray.VEHICLE_DISPATCH_FRACTION].push(
                    float(frame_results[History.VEHICLE_P2_TIME]) /
                    window_vehicle_time))
            # PlotArray.VEHICLE_PAID_FRACTION
            self.results[PlotArray.VEHICLE_PAID_FRACTION] += (
                self.plot_buffers[PlotArray.VEHICLE_PAID_FRACTION].push(
                    float(frame_results[History.VEHICLE_P3_TIME]) /
                    window_vehicle_time))
            # PlotArray.VEHICLE_PAID_FRACTION
            # PlotArray.VEHICLE_COUNT
            # PlotArray.VEHICLE_UTILITY
        if window_riding_time > 0:
            # PlotArray.TRIP_MEAN_WAIT_TIME
            # PlotArray.TRIP_MEAN_DISTANCE
            # PlotArray.TRIP_WAIT_FRACTION_TOTAL
            # PlotArray.TRIP_WAIT_FRACTION
            self.results[PlotArray.TRIP_WAIT_FRACTION] += (
                self.plot_buffers[PlotArray.TRIP_WAIT_FRACTION].push(
                    float(frame_results[History.VEHICLE_P3_TIME]) /
                    window_riding_time))
            # PlotArray.TRIP_DISTANCE_FRACTION
            # PlotArray.TRIP_COUNT
            # PlotArray.TRIP_COMPLETED_FRACTION
            # PlotArray.TRIP_REQUEST_RATE
            # PlotArray.PLATFORM_INCOME
            # print(f"worker: {results}")
        # for plot_property in self.plot_buffers:
        # self.update_in_place(plot_property, frame_results)
        self.frame_index += 1
        return [
            self.results[PlotArray.VEHICLE_IDLE_FRACTION],
            self.results[PlotArray.VEHICLE_DISPATCH_FRACTION],
            self.results[PlotArray.VEHICLE_PAID_FRACTION],
            self.results[PlotArray.TRIP_WAIT_FRACTION],
        ]

    def update_in_place(self, plot_property, frame_results):
        self.results[plot_property] -= self.plot_buffers[
            plot_property].get_tail()
        self.plot_buffers[plot_property].enqueue(frame_results[plot_property])
        self.results[plot_property] += self.plot_buffers[
            plot_property].get_head()
