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
        config.reservation_wage.value = float(web_config["reservationWage"])
        config.platform_commission.value = float(
            web_config["platformCommission"])
        config.per_km_ops_cost.value = float(web_config["perKmOpsCost"])
        config.per_unit_opp_cost.value = float(web_config["perUnitOppCost"])
        # else:
        # config.price.value = 0.20 + (0.5 * 0.80) + 0.30
        # .20 per min, .8 / km, .3 starting
        # config.platform_commission.value = 0.25
        # config.reservation_wage.value = 0.25
        # $0.55 / km, but in Simple mode a block is 0.5km
        # Scaled for slower driving while in P1
        # config.per_km_ops_cost.value = 0.50 * 0.5

        # config.validate_options()
        self.sim = RideHailSimulation(config)
        self.plot_buffers = {}
        self.results = {}
        self.smoothing_window = config.smoothing_window.value
        for plot_property in list(Measure):
            self.results[plot_property.value] = 0
        self.old_results = {}
        self.frame_index = 0

    def _get_frame_results(self, return_values):
        frame_results = self.sim.next_block(output_file_handle=None,
                                            return_values=return_values)
        # Some need converting before passing to JavaScript. For example,
        # any enum values must be replaced with their name or value
        results = {}
        results["block"] = frame_results["block"]
        results["city_size"] = frame_results["city_size"]
        results["vehicle_count"] = frame_results["vehicle_count"]
        results["base_demand"] = frame_results["base_demand"]
        results["trip_inhomogeneity"] = frame_results["trip_inhomogeneity"]
        results["min_trip_distance"] = frame_results["min_trip_distance"]
        results["max_trip_distance"] = frame_results["max_trip_distance"]
        results["idle_vehicles_moving"] = frame_results["idle_vehicles_moving"]
        results["equilibrate"] = frame_results["equilibrate"]
        results["price"] = frame_results["price"]
        results["platform_commission"] = frame_results["platform_commission"]
        results["reservation_wage"] = frame_results["reservation_wage"]
        results["demand_elasticity"] = frame_results["demand_elasticity"]
        results["city_scale_unit"] = frame_results["city_scale_unit"].name
        results["mean_vehicle_speed"] = frame_results["mean_vehicle_speed"]
        results["units_per_block"] = frame_results["units_per_block"]
        results["per_unit_opp_cost"] = frame_results["per_unit_opp_cost"]
        results["per_km_ops_cost"] = frame_results["per_km_ops_cost"]
        results["per_km_price"] = frame_results["per_km_price"]
        results["per_min_price"] = frame_results["per_min_price"]
        if return_values == "map":
            results["vehicles"] = frame_results["vehicles"]
            results["trips"] = frame_results["trips"]
        for item in list(Measure):
            results[item.name] = frame_results[item]
        print(f"wo: results={results}")
        return results

    def next_frame_map(self, message_from_ui=None):
        # web_config = message_from_ui.to_py()
        results = {}
        if self.frame_index % 2 == 0:
            # It's a real block: do the simulation
            results = self._get_frame_results(return_values="map")
            # print(f"wo: trips={frame_results['trips']}")
            # Results come back as a dictionary:
            # {"block": integer,
            #  "vehicles": [[phase.name, location, direction],...],
            #  "trips": [[phase.name, origin, destination, distance],...],
            # }
            self.old_results = copy.deepcopy(results)
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
        self.frame_index += 1
        return results

    def next_frame_stats(self, message_from_ui):
        # web_config = config.to_py()
        # Get the latest History items in a dictionary
        results = self._get_frame_results(return_values="stats")
        return results

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
