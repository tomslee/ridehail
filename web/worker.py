from ridehail.config import (RideHailConfig, ConfigItem)
from ridehail.simulation import (RideHailSimulation)
from ridehail.atom import (Direction, PlotArray, History)
import copy
import numpy as np

sim = None


# Class to hold arrays to do smoothing averages
# From
# https://stackoverflow.com/questions/42771110/fastest-way-to-left-cycle-a-numpy-array-like-pop-push-for-a-queue
class CircularBuffer:
    """
    Oddly enough, this class pushes new values on to the tail, and drops them
    from the head. Think of it like appending to the tail of a file.
    """
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


def init_simulation(message_from_ui):
    # results = RideHailSimulationResults()
    global sim
    sim = Simulation(message_from_ui)


class Simulation():
    def __init__(self, message_from_ui):
        web_config = message_from_ui.to_py()
        config = RideHailConfig()
        config.city_size.value = int(web_config["citySize"])
        # TODO Set max trip distance to be citySize, unless
        # it is overriden later
        config.max_trip_distance.value = int(web_config["citySize"])
        config.vehicle_count.value = int(web_config["vehicleCount"])
        config.base_demand.value = float(web_config["requestRate"])
        config.smoothing_window.value = int(web_config["smoothingWindow"])
        config.random_number_seed.value = int(web_config["randomNumberSeed"])
        config.time_blocks.value = 2000
        config.animate.value = False
        config.equilibrate.value = False
        config.run_sequence.value = False
        config.interpolate.value = 0
        self.sim = RideHailSimulation(config)
        self.plot_buffers = {}
        self.results = {}
        for plot_property in list(PlotArray):
            self.plot_buffers[plot_property] = CircularBuffer(
                config.smoothing_window.value)
            self.results[plot_property] = 0
        self.old_results = {}
        self.frame_index = 0

    def next_frame_map(self, message_from_ui=None):
        # web_config = message_from_ui.to_py()
        results = {}
        if self.frame_index % 2 == 0:
            # It's a real block: do the simulation
            frame_results = self.sim.next_block(output_file_handle=None,
                                                return_values="map")
            # print(f"wo: trips={frame_results['trips']}")
            # Results come back as a dictionary:
            # {"block": integer,
            #  "vehicles": [[phase.name, location, direction],...],
            #  "trips": [[phase.name, origin, destination, distance],...],
            # }
            self.old_results = copy.deepcopy(frame_results)
            results = frame_results
        else:
            # interpolating a frame, to animate edge-of-map transitions
            for vehicle in self.old_results["vehicles"]:
                # vehicle = [phase.name, vehicle.location, vehicle.direction]
                direction = vehicle[2]
                if direction == Direction.NORTH.name:
                    vehicle[1][1] += 0.5
                elif direction == Direction.EAST.name:
                    vehicle[1][0] += 0.5
                elif direction == Direction.SOUTH.name:
                    vehicle[1][1] -= 0.5
                elif direction == Direction.WEST.name:
                    vehicle[1][0] -= 0.5
            results["vehicles"] = [
                vehicle for vehicle in self.old_results["vehicles"]
            ]
            # TODO: Fix this block/frame disconnect
            # For now, return the frame inde, not the block index
            results["trips"] = self.old_results["trips"]
        results["block"] = self.frame_index
        self.frame_index += 1
        return results

    def next_frame_stats(self, message_from_ui):
        # web_config = config.to_py()
        # Get the latest History items in a dictionary
        frame_results = self.sim.next_block(output_file_handle=None,
                                            return_values="stats")
        # print(f"wo: frame_results={frame_results}")
        self.results["block"] = frame_results["block"]
        self.results["city_size"] = frame_results["city_size"]
        self.results["vehicle_count"] = frame_results["vehicle_count"]
        self.results["base_demand"] = frame_results["base_demand"]
        # Get the total vehicle time over the smoothing window
        self.results[PlotArray.VEHICLE_TIME] += self.plot_buffers[
            PlotArray.VEHICLE_TIME].push(frame_results[History.VEHICLE_TIME])
        window_vehicle_time = float(self.results[PlotArray.VEHICLE_TIME])
        self.results[PlotArray.TRIP_RIDING_TIME] += self.plot_buffers[
            PlotArray.TRIP_RIDING_TIME].push(
                frame_results[History.TRIP_RIDING_TIME])
        window_riding_time = float(self.results[PlotArray.TRIP_RIDING_TIME])
        self.results[PlotArray.TRIP_COUNT] += self.plot_buffers[
            PlotArray.TRIP_COUNT].push(frame_results[History.COMPLETED_TRIPS])
        window_completed_trip_count = int(self.results[PlotArray.TRIP_COUNT])

        if window_vehicle_time > 0:
            # PlotArray.VEHICLE_IDLE_FRACTION - divide by vehicle time late
            self.results[PlotArray.VEHICLE_IDLE_FRACTION] += self.plot_buffers[
                PlotArray.VEHICLE_IDLE_FRACTION].push(
                    frame_results[History.VEHICLE_P1_TIME])
            # PlotArray.VEHICLE_DISPATCH_FRACTION - divide by vehicle time late
            self.results[
                PlotArray.VEHICLE_DISPATCH_FRACTION] += self.plot_buffers[
                    PlotArray.VEHICLE_DISPATCH_FRACTION].push(
                        frame_results[History.VEHICLE_P2_TIME])
            # PlotArray.VEHICLE_PAID_FRACTION - divide by vehicle time late
            self.results[PlotArray.VEHICLE_PAID_FRACTION] += self.plot_buffers[
                PlotArray.VEHICLE_PAID_FRACTION].push(
                    frame_results[History.VEHICLE_P3_TIME])
            # PlotArray.VEHICLE_PAID_FRACTION
            # PlotArray.VEHICLE_COUNT
            # PlotArray.VEHICLE_UTILITY
        if window_riding_time > 0 and window_completed_trip_count > 0:
            # PlotArray.TRIP_MEAN_WAIT_TIME
            self.results[PlotArray.TRIP_MEAN_WAIT_TIME] += (
                self.plot_buffers[PlotArray.TRIP_MEAN_WAIT_TIME].push(
                    float(frame_results[History.WAIT_TIME]) /
                    window_completed_trip_count))
            # PlotArray.TRIP_MEAN_DISTANCE
            # PlotArray.TRIP_WAIT_FRACTION_TOTAL
            # PlotArray.TRIP_WAIT_FRACTION
            self.results[PlotArray.TRIP_WAIT_FRACTION] += (
                self.plot_buffers[PlotArray.TRIP_WAIT_FRACTION].push(
                    float(frame_results[History.TRIP_WAIT_FRACTION]) /
                    window_riding_time))
            # PlotArray.TRIP_DISTANCE_FRACTION
            # PlotArray.TRIP_COUNT
            # PlotArray.TRIP_COMPLETED_FRACTION
            # PlotArray.TRIP_REQUEST_RATE
            # PlotArray.PLATFORM_INCOME
            # print(f"worker: {results}")
        # for plot_property in self.plot_buffers:
        values = [
            float(self.results[x] / window_vehicle_time) for x in [
                PlotArray.VEHICLE_IDLE_FRACTION, PlotArray.
                VEHICLE_DISPATCH_FRACTION, PlotArray.VEHICLE_PAID_FRACTION
            ]
        ]
        values.append(self.results[PlotArray.TRIP_MEAN_WAIT_TIME])
        values.append(self.results[PlotArray.TRIP_WAIT_FRACTION])
        return {
            "block": self.results["block"],
            "values": values,
            "city_size": self.results["city_size"],
            "vehicle_count": self.results["vehicle_count"],
            "base_demand": self.results["base_demand"]
        }

    def update_options(self, message_from_ui):
        options = message_from_ui.to_py()
        self.sim.target_state["vehicle_count"] = int(options["vehicleCount"])
        self.sim.target_state["base_demand"] = float(options["requestRate"])
