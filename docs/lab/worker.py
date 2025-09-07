from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.dispatch import Dispatch
from ridehail.atom import Direction, Measure, Equilibration
import copy

sim = None


def init_simulation(message_from_ui):
    # results = RideHailSimulationResults()
    global sim
    sim = Simulation(message_from_ui)


class Simulation:
    def __init__(self, message_from_ui):
        web_config = message_from_ui.to_py()
        config = RideHailConfig()
        config.city_size.value = int(web_config["citySize"])
        # TODO Set max trip distance to be citySize, unless
        # it is overriden later
        # config.max_trip_distance.value = int(web_config["citySize"])
        config.inhomogeneity.value = float(web_config["inhomogeneity"])
        config.max_trip_distance.value = web_config["maxTripDistance"]
        config.vehicle_count.value = int(web_config["vehicleCount"])
        config.base_demand.value = float(web_config["requestRate"])
        config.smoothing_window.value = int(web_config["smoothingWindow"])
        config.inhomogeneity.value = float(web_config["inhomogeneity"])
        config.inhomogeneous_destinations.value = bool(
            web_config["inhomogeneousDestinations"]
        )
        config.random_number_seed.value = int(web_config["randomNumberSeed"])
        config.verbosity.value = int(web_config["verbosity"])
        config.animate.value = False
        config.run_sequence.value = False
        config.animation_style.value = "none"
        config.interpolate.value = 0
        config.equilibrate.value = bool(web_config["equilibrate"])
        config.equilibration.value = Equilibration.PRICE
        config.equilibration_interval.value = int(web_config["equilibrationInterval"])
        config.demand_elasticity.value = float(web_config["demandElasticity"])
        config.use_city_scale.value = bool(web_config["useCityScale"])
        config.mean_vehicle_speed.value = float(web_config["meanVehicleSpeed"])
        config.minutes_per_block.value = float(web_config["minutesPerBlock"])
        config.price.value = float(web_config["price"])
        config.per_km_price.value = float(web_config["perKmPrice"])
        config.per_minute_price.value = float(web_config["perMinutePrice"])
        config.reservation_wage.value = float(web_config["reservationWage"])
        config.platform_commission.value = float(web_config["platformCommission"])
        config.per_km_ops_cost.value = float(web_config["perKmOpsCost"])
        config.per_hour_opportunity_cost.value = float(
            web_config["perHourOpportunityCost"]
        )
        config.time_blocks.value = int(web_config["timeBlocks"])

        # else:
        # config.price.value = 0.20 + (0.5 * 0.80) + 0.30
        # .20 per min, .8 / km, .3 starting
        # config.platform_commission.value = 0.25
        # config.reservation_wage.value = 0.25
        # $0.55 / km, but in Simple mode a block is 0.5km
        # Scaled for slower driving while in P1
        # config.per_km_ops_cost.value = 0.50 * 0.5
        # for attr in dir(config):
        # assign default values
        # option = getattr(config, attr)
        # if isinstance(option, ConfigItem):
        # print(f"{option.name}={option.value}")
        self.sim = RideHailSimulation(config)
        self.plot_buffers = {}
        self.results = {}
        self.smoothing_window = config.smoothing_window.value
        for plot_property in list(Measure):
            self.results[plot_property.value] = 0
        self.old_results = {}
        self.frame_index = 0

    def _get_frame_results(self, return_values):
        frame_results = self.sim.next_block(
            jsonl_file_handle=None,
            csv_file_handle=None,
            return_values=return_values,
            dispatch=Dispatch(),
        )
        # Some need converting before passing to JavaScript. For example,
        # any enum values must be replaced with their name or value
        results = {}
        results["block"] = frame_results["block"]
        results["city_size"] = frame_results["city_size"]
        results["vehicle_count"] = frame_results["vehicle_count"]
        results["base_demand"] = frame_results["base_demand"]
        results["inhomogeneity"] = frame_results["inhomogeneity"]
        results["min_trip_distance"] = frame_results["min_trip_distance"]
        results["max_trip_distance"] = frame_results["max_trip_distance"]
        results["idle_vehicles_moving"] = frame_results["idle_vehicles_moving"]
        results["time_blocks"] = frame_results["time_blocks"]
        results["equilibrate"] = frame_results["equilibrate"]
        results["price"] = frame_results["price"]
        results["platform_commission"] = frame_results["platform_commission"]
        results["reservation_wage"] = frame_results["reservation_wage"]
        results["demand_elasticity"] = frame_results["demand_elasticity"]
        results["use_city_scale"] = frame_results["use_city_scale"]
        results["mean_vehicle_speed"] = frame_results["mean_vehicle_speed"]
        results["minutes_per_block"] = frame_results["minutes_per_block"]
        results["per_hour_opportunity_cost"] = frame_results[
            "per_hour_opportunity_cost"
        ]
        results["per_km_ops_cost"] = frame_results["per_km_ops_cost"]
        results["per_km_price"] = frame_results["per_km_price"]
        results["per_minute_price"] = frame_results["per_minute_price"]
        if return_values == "map":
            results["vehicles"] = frame_results["vehicles"]
            results["trips"] = frame_results["trips"]
        for item in list(Measure):
            results[item.name] = frame_results[item.name]
        return results

    def next_frame_map(self):
        """
        This method is called from webworker.js for cases where the
        map is displayed.
        - results is the dictionary that gets returned to webworker.js.
        """
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
            results["vehicles"] = [vehicle for vehicle in self.old_results["vehicles"]]
            # TODO: Fix this block/frame disconnect
            # For now, return the frame index, not the block index
            results["trips"] = self.old_results["trips"]
        results["block"] = self.frame_index
        js_results = self._prepare_results_for_js(results)
        self.frame_index += 1
        return js_results

    def _prepare_results_for_js(self, results):
        """Convert Python objects to JavaScript-friendly format"""
        js_results = {}
        # Copy scalar values directly
        for key, value in results.items():
            if key != "vehicles":
                js_results[key] = value
        # Handle vehicles specially
        if "vehicles" in results:
            js_vehicles = []
            for vehicle_data in results["vehicles"]:
                # Assuming vehicle_data is [phase_name, location, direction_name]
                if len(vehicle_data) >= 3:
                    js_vehicle = {
                        "phase": vehicle_data[0],  # phase.name string
                        "location": list(vehicle_data[1])
                        if hasattr(vehicle_data[1], "__iter__")
                        else vehicle_data[1],  # ensure it's a list
                        "direction": vehicle_data[2],  # direction.name string
                    }
                    js_vehicles.append(js_vehicle)
            js_results["vehicles"] = js_vehicles
        return js_results

    def next_frame_stats(self):
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
            options["platformCommission"]
        )
        self.sim.target_state["inhomogeneity"] = float(options["inhomogeneity"])
        self.sim.target_state["idle_vehicles_moving"] = bool(
            options["idleVehiclesMoving"]
        )
        self.sim.target_state["demand_elasticity"] = float(options["demandElasticity"])
