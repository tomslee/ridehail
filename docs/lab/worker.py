"""
Pyodide Web Worker Bridge for Ridehail Simulation

This module runs in Pyodide (Python in WebAssembly) within a web worker and provides
a JavaScript-friendly API for the ridehail simulation package. It handles:

- Configuration mapping from web UI settings to Python simulation config
- Frame-by-frame simulation execution for smooth animation
- Bidirectional interpolation for edge-of-map transitions (torus topology)
- Real-time parameter updates during simulation
- Type conversion between Python and JavaScript objects

Architecture:
    JavaScript UI (app.js)
        ↓ postMessage(settings)
    Web Worker (webworker.js)
        ↓ pyimport("worker")
    This Module (worker.py)
        ↓ RideHailSimulation
    Core Simulation (ridehail package)

Usage:
    # Initialization (called from webworker.js)
    init_simulation(settings)  # Creates global Simulation instance

    # Frame generation for map visualization
    results = sim.next_frame_map()  # Returns dict with vehicles, trips, stats

    # Frame generation for statistics charts
    results = sim.next_frame_stats()  # Returns dict with aggregated measures

    # Runtime parameter updates
    sim.update_options(new_settings)  # Updates simulation mid-run
"""

from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.dispatch import Dispatch
from ridehail.atom import Direction, Measure, Equilibration
import copy

# Global simulation instance (initialized by init_simulation)
sim = None


def init_simulation(settings):
    """
    Initialize a new simulation with settings from the web UI.

    Creates a global Simulation instance that maps web UI parameters to the
    ridehail package configuration format.

    Args:
        settings: Pyodide proxy object from JavaScript with simulation parameters.
                  Converted to Python dict via settings.to_py()

    Returns:
        Simulation: The initialized simulation instance (also stored in global `sim`)

    Side Effects:
        Sets the global `sim` variable

    Note:
        This function is called from webworker.js when starting a new simulation
        or resetting to frame 0.
    """
    global sim
    sim = Simulation(settings)
    return sim


class Simulation:
    """
    Web-optimized wrapper for RideHailSimulation.

    Handles the interface between JavaScript settings and the Python simulation engine,
    including frame-by-frame execution, interpolation for smooth animation, and
    type conversion for efficient data transfer via postMessage.

    Attributes:
        sim (RideHailSimulation): The core simulation engine
        plot_buffers (dict): Unused in web version (legacy from desktop)
        results (dict): Current frame measurement results
        smoothing_window (int): Window size for statistics smoothing
        old_results (dict): Previous frame results for interpolation
        frame_index (int): Current animation frame (2 frames per simulation block)

    Frame Indexing:
        Even frames (0, 2, 4...): Run simulation, cache results
        Odd frames (1, 3, 5...): Interpolate from cached results for smooth animation
    """

    def __init__(self, settings):
        """
        Initialize simulation from web UI settings.

        Maps JavaScript camelCase settings to Python snake_case configuration,
        performs type conversions, and initializes the simulation engine.

        Args:
            settings: Pyodide proxy object containing simulation parameters from web UI

        Note:
            - animationDelay is converted from milliseconds (web) to seconds (Python)
            - Animation is disabled (handled by JavaScript instead)
            - Interpolation handled by this wrapper, not core simulation
        """
        web_config = settings.to_py()
        config = RideHailConfig()
        config.city_size.value = int(web_config["citySize"])
        config.vehicle_count.value = int(web_config["vehicleCount"])
        config.base_demand.value = float(web_config["requestRate"])
        config.max_trip_distance.value = web_config["maxTripDistance"]
        # TODO Set max trip distance to be citySize, unless
        # it is overriden later
        # config.max_trip_distance.value = int(web_config["citySize"])
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
        config.use_city_scale.value = bool(web_config["useCostsAndIncomes"])
        config.mean_vehicle_speed.value = float(web_config["meanVehicleSpeed"])
        config.minutes_per_block.value = float(web_config["minutesPerBlock"])
        config.reservation_wage.value = float(web_config["reservationWage"])
        config.platform_commission.value = float(web_config["platformCommission"])
        config.price.value = float(web_config["price"])
        config.per_km_price.value = float(web_config["perKmPrice"])
        config.per_minute_price.value = float(web_config["perMinutePrice"])
        config.per_km_ops_cost.value = float(web_config["perKmOpsCost"])
        config.per_hour_opportunity_cost.value = float(
            web_config["perHourOpportunityCost"]
        )
        config.time_blocks.value = int(web_config["timeBlocks"])
        config.smoothing_window.value = int(web_config["smoothingWindow"])
        # Convert animationDelay from milliseconds (web) to seconds (Python config)
        config.animation_delay.value = float(web_config["animationDelay"]) / 1000.0
        # Pickup time configuration (default 1 if not present for backward compatibility)
        config.pickup_time.value = int(web_config.get("pickupTime", 1))

        self.sim = RideHailSimulation(config)
        self.plot_buffers = {}
        self.results = {}
        self.smoothing_window = config.smoothing_window.value
        for plot_property in list(Measure):
            self.results[plot_property.value] = 0
        self.old_results = {}
        self.frame_index = 0

    def _get_frame_results(self, return_values):
        """
        Execute one simulation block and extract results.

        Runs the simulation forward by one block (time step) and collects
        results in a format suitable for JavaScript consumption.

        Args:
            return_values (str): Type of data to return - "map" for vehicle/trip data,
                               "stats" for aggregate statistics only

        Returns:
            dict: Simulation results with scalar values, measurements, and optionally
                 vehicle/trip data depending on return_values parameter

        Note:
            Enum values are converted to strings (e.g., Direction.NORTH → "NORTH")
            for JavaScript compatibility.
        """
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
        Generate next animation frame for map visualization.

        Implements a two-frame-per-block animation system for smooth vehicle movement:
        - Even frames (0, 2, 4...): Execute simulation block, cache results
        - Odd frames (1, 3, 5...): Interpolate vehicle positions for midpoint animation

        The midpoint interpolation strategy matches the Chart.js browser implementation
        and enables:
        - Smooth vehicle transitions between intersections
        - Proper direction changes at intersection centers
        - Phase color updates at logical moments
        - Torus edge wrapping without visual streaking

        Returns:
            dict: Frame results containing:
                - block (int): Current frame index (NOT simulation block number)
                - vehicles (list): Vehicle data as objects with phase, location, direction
                - trips (list): Active trip markers (origins and destinations)
                - [various simulation parameters and measurements]

        Note:
            Called from webworker.js when chartType == "map"
            Vehicle positions are interpolated +0.5 in movement direction on odd frames
            Pickup countdown logic prevents midpoint movement during passenger pickup
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
            for idx, vehicle in enumerate(self.old_results["vehicles"]):
                # vehicle = [phase.name, vehicle.location, vehicle.direction, vehicle.pickup_countdown]
                direction = vehicle[2]
                pickup_countdown = vehicle[3] if len(vehicle) > 3 else None

                # Skip midpoint movement if vehicle is waiting for pickup
                if pickup_countdown is not None and pickup_countdown > 0:
                    # Vehicle is at pickup location, don't move to midpoint
                    continue

                # If pickup just completed (countdown == 0), update phase and direction
                # from live simulation state to show correct P3 phase and dropoff direction
                if pickup_countdown is not None and pickup_countdown == 0:
                    # Get updated state from live simulation
                    if idx < len(self.sim.vehicles):
                        live_vehicle = self.sim.vehicles[idx]
                        vehicle[0] = live_vehicle.phase.name  # Update to P3
                        vehicle[2] = live_vehicle.direction.name  # Update to dropoff direction
                        direction = vehicle[2]  # Use updated direction for midpoint offset

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
        """
        Convert Python vehicle data to JavaScript-friendly object format.

        Transforms vehicle list data from Python array format to JavaScript objects
        for easier consumption in the map rendering code.

        Args:
            results (dict): Simulation results with vehicles as nested arrays

        Returns:
            dict: Same results but with vehicles converted to list of objects:
                  [{phase: str, location: [x, y], direction: str}, ...]

        Note:
            This conversion makes JavaScript code cleaner:
            vehicle.phase vs vehicle[0], vehicle.location vs vehicle[1], etc.
        """
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
        """
        Generate next frame for statistics chart visualization.

        Executes simulation block and returns aggregate statistics without
        vehicle/trip position data (more efficient than next_frame_map).

        Returns:
            dict: Frame results containing simulation measurements and parameters
                 but excluding vehicles and trips arrays

        Note:
            Called from webworker.js when chartType == "stats" or "what_if"
            No interpolation needed for statistics - every call advances simulation
        """
        results = self._get_frame_results(return_values="stats")
        return results

    def update_options(self, message_from_ui):
        """
        Update simulation parameters during runtime.

        Allows real-time adjustment of simulation settings without stopping/restarting.
        Updates the simulation's target_state which is applied gradually.

        Args:
            message_from_ui: Pyodide proxy object with new parameter values from UI

        Side Effects:
            Modifies self.sim.target_state with new parameter values

        Supported runtime updates:
            - vehicle_count: Number of active vehicles
            - base_demand: Trip request rate
            - equilibrate: Enable/disable price equilibration
            - platform_commission: Platform's commission percentage
            - inhomogeneity: Spatial demand variation
            - idle_vehicles_moving: Whether idle vehicles drive randomly
            - demand_elasticity: Price sensitivity of demand

        Note:
            Called from webworker.js when action == "Update"
        """
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
