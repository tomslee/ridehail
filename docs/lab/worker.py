from ridehail.config import (RideHailConfig, ConfigItem)
from ridehail.simulation import (RideHailSimulation)
from ridehail.atom import (Direction, Measure, History, Equilibration)
import copy
import numpy as np

sim = None


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
        # config.max_trip_distance.value = int(web_config["citySize"])
        config.max_trip_distance.value = None
        config.vehicle_count.value = int(web_config["vehicleCount"])
        config.base_demand.value = float(web_config["requestRate"])
        config.smoothing_window.value = int(web_config["smoothingWindow"])
        config.random_number_seed.value = int(web_config["randomNumberSeed"])
        config.trip_inhomogeneity.value = float(
            web_config["tripInhomogeneity"])
        config.time_blocks.value = 2000
        config.animate.value = False
        config.animation_style.value = "none"
        config.equilibrate.value = bool(web_config["equilibrate"])
        config.equilibration.value = Equilibration.PRICE
        config.run_sequence.value = False
        config.interpolate.value = 0
        config.use_city_scale.value = bool(web_config["useCityScale"])
        config.city_scale_unit.value = str(web_config["cityScaleUnit"])
        config.units_per_block.value = float(web_config["unitsPerBlock"])
        config.mean_vehicle_speed.value = float(web_config["meanVehicleSpeed"])
        config.per_km_price.value = float(web_config["perKmPrice"])
        config.per_min_price.value = float(web_config["perMinPrice"])
        config.demand_elasticity.value = 1.0
        config.price.value = float(web_config["price"])
        config.reserved_wage.value = float(web_config["reservedWage"])
        config.platform_commission.value = float(
            web_config["platformCommission"])
        config.per_km_ops_cost.value = float(web_config["perKmOpsCost"])
        config.per_unit_opp_cost.value = float(web_config["perUnitOppCost"])
        # else:
        # config.price.value = 0.20 + (0.5 * 0.80) + 0.30
        # .20 per min, .8 / km, .3 starting
        # config.platform_commission.value = 0.25
        # config.reserved_wage.value = 0.25
        # $0.55 / km, but in Simple mode a block is 0.5km
        # Scaled for slower driving while in P1
        # config.per_km_ops_cost.value = 0.50 * 0.5

        # config.validate_options()
        self.sim = RideHailSimulation(config)
        self.plot_buffers = {}
        self.results = {}
        self.smoothing_window = config.smoothing_window.value
        for plot_property in list(RollingAverage):
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
            results = self.old_results
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
        # TODO: Fix this haxk: it can't be sent as it's an Enum
        results["city_scale_unit"] = "min"
        self.frame_index += 1
        return results

    def next_frame_stats(self, message_from_ui):
        # web_config = config.to_py()
        # Get the latest History items in a dictionary
        frame_results = self.sim.next_block(output_file_handle=None,
                                            return_values="stats")
        # print(f"wo: frame_results={frame_results}")
        # Some need converting before passing to JavaScript. For example,
        # any enum values must be replaced with their name or value
        self.results["block"] = frame_results["block"]
        self.results["city_size"] = frame_results["city_size"]
        self.results["vehicle_count"] = frame_results["vehicle_count"]
        self.results["base_demand"] = frame_results["base_demand"]
        self.results["trip_inhomogeneity"] = frame_results[
            "trip_inhomogeneity"]
        self.results["min_trip_distance"] = frame_results["min_trip_distance"]
        self.results["max_trip_distance"] = frame_results["max_trip_distance"]
        self.results["idle_vehicles_moving"] = frame_results[
            "idle_vehicles_moving"]
        self.results["equilibrate"] = frame_results["equilibrate"]
        self.results["price"] = frame_results["price"]
        self.results["platform_commission"] = frame_results[
            "platform_commission"]
        self.results["reserved_wage"] = frame_results["reserved_wage"]
        self.results["demand_elasticity"] = frame_results["demand_elasticity"]
        self.results["city_scale_unit"] = frame_results["city_scale_unit"].name
        self.results["mean_vehicle_speed"] = frame_results[
            "mean_vehicle_speed"]
        self.results["units_per_block"] = frame_results["units_per_block"]
        self.results["per_unit_opp_cost"] = frame_results["per_unit_opp_cost"]
        self.results["per_km_ops_cost"] = frame_results["per_km_ops_cost"]
        self.results["per_km_price"] = frame_results["per_km_price"]
        self.results["per_min_price"] = frame_results["per_min_price"]
        # self.results["values"] = frame_results["values"]
        for item in list(Measure):
            self.results[item.value] = frame_results[item]
        return self.results
        # return {
            # "block": self.results["block"],
            # "values": self.results["values"],
            # "city_size": self.results["city_size"],
            # "vehicle_count": self.results["vehicle_count"],
            # "base_demand": self.results["base_demand"],
            # "trip_inhomogeneity": self.results["trip_inhomogeneity"],
            # "min_trip_distance": self.results["min_trip_distance"],
            # "max_trip_distance": self.results["max_trip_distance"],
            # "idle_vehicles_moving": self.results["idle_vehicles_moving"],
            # "equilibrate": self.results["equilibrate"],
            # "price": self.results["price"],
            # "platform_commission": self.results["platform_commission"],
            # "reserved_wage": self.results["reserved_wage"],
            # "demand_elasticity": self.results["demand_elasticity"],
            # "city_scale_unit": self.results["city_scale_unit"],
            # "mean_vehicle_speed": self.results["mean_vehicle_speed"],
            # "units_per_block": self.results["units_per_block"],
            # "per_unit_opp_cost": self.results["per_unit_opp_cost"],
            # "per_km_ops_cost": self.results["per_km_ops_cost"],
            # "per_km_price": self.results["per_km_price"],
            # "per_min_price": self.results["per_min_price"],
        # }

    def update_options(self, message_from_ui):
        options = message_from_ui.to_py()
        self.sim.target_state["vehicle_count"] = int(options["vehicleCount"])
        self.sim.target_state["base_demand"] = float(options["requestRate"])
        self.sim.target_state["equilibrate"] = bool(options["equilibrate"])
        self.sim.target_state["platform_commission"] = float(
            options["platformCommission"])
        self.sim.target_state["trip_inhomogeneity"] = float(
            options["tripInhomogeneity"])
        self.sim.target_state["idle_vehicles_moving"] = bool(
            options["idleVehiclesMoving"])
