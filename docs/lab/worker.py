"""
Pyodide Web Worker Bridge for Ridehail Simulation

This module runs in Pyodide (Python in WebAssembly) within a web worker and provides
a JavaScript-friendly API for the ridehail simulation package. It handles:

- Configuration mapping from web UI settings to Python simulation config
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
    results = sim.next_block_stats()  # Returns dict with aggregated measures

    # Runtime parameter updates
    sim.update_options(new_settings)  # Updates simulation mid-run
"""

from ridehail import __version__
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.simulation_results import RideHailSimulationResults
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
        or resetting to block 0.
    """
    global sim
    sim = Simulation(settings)
    return sim


class Simulation:
    """
    Web-optimized wrapper for RideHailSimulation.

    Handles the interface between JavaScript settings and the Python simulation engine,
    including block-by-block execution, interpolation for smooth animation, and
    type conversion for efficient data transfer via postMessage.

    Attributes:
        sim (RideHailSimulation): The core simulation engine
        plot_buffers (dict): Unused in web version (legacy from desktop)
        results (dict): Current block measurement results
        smoothing_window (int): Window size for statistics smoothing
        old_results (dict): Previous block results for interpolation
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
        # Handle null/None values for optional parameters
        # JavaScript null becomes JsNull in Pyodide, not Python None, so use try-except
        try:
            config.max_trip_distance.value = int(web_config["maxTripDistance"])
        except (TypeError, ValueError):
            config.max_trip_distance.value = None
        config.min_trip_distance.value = web_config.get("minTripDistance", 0)
        # TODO Set max trip distance to be citySize, unless
        # it is overriden later
        # config.max_trip_distance.value = int(web_config["citySize"])
        config.inhomogeneity.value = float(web_config["inhomogeneity"])
        config.inhomogeneous_destinations.value = bool(
            web_config["inhomogeneousDestinations"]
        )
        config.idle_vehicles_moving.value = bool(
            web_config.get("idleVehiclesMoving", True)
        )
        # Handle null/None for random_number_seed (None means non-deterministic random)
        # JavaScript null becomes JsNull in Pyodide, not Python None, so use try-except
        try:
            config.random_number_seed.value = int(web_config["randomNumberSeed"])
        except (TypeError, ValueError):
            config.random_number_seed.value = None
        config.verbosity.value = int(web_config["verbosity"])
        config.run_sequence.value = False
        config.animation.value = "none"
        config.interpolate.value = 0
        # Handle equilibration: web config provides both "equilibrate" boolean (legacy)
        # and "equilibration" string. Priority: equilibration string > equilibrate boolean
        equilibration_str = web_config.get("equilibration")
        if equilibration_str:
            # Use explicit equilibration method if provided
            # Convert to uppercase to match enum member names (NONE, PRICE, SUPPLY, etc.)
            try:
                config.equilibration.value = Equilibration[equilibration_str.upper()]
            except KeyError:
                # Invalid equilibration value - default to NONE for safety
                config.equilibration.value = Equilibration.NONE
        else:
            # Fall back to equilibrate boolean for backward compatibility
            if bool(web_config.get("equilibrate", False)):
                config.equilibration.value = Equilibration.PRICE
            else:
                config.equilibration.value = Equilibration.NONE
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
        # results_window should match smoothing_window for consistent calculations
        # (desktop typically uses larger results_window, but for web we use smoothing_window)
        config.results_window.value = int(web_config["smoothingWindow"])
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
        self.block_index = 0
        # Store version for inclusion in results
        self.version = __version__

    def _get_block_results(self, return_values):
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
        block_results = self.sim.next_block(
            jsonl_file_handle=None,
            csv_file_handle=None,
            return_values=return_values,
        )
        # Some need converting before passing to JavaScript. For example,
        # any enum values must be replaced with their name or value
        results = {}
        results["block"] = block_results["block"]
        if "title" in block_results:
            results["title"] = block_results["title"]
        results["city_size"] = block_results["city_size"]
        results["vehicle_count"] = block_results["vehicle_count"]
        results["base_demand"] = block_results["base_demand"]
        results["inhomogeneity"] = block_results["inhomogeneity"]
        results["min_trip_distance"] = block_results["min_trip_distance"]
        results["max_trip_distance"] = block_results["max_trip_distance"]
        results["idle_vehicles_moving"] = block_results["idle_vehicles_moving"]
        results["time_blocks"] = block_results["time_blocks"]
        results["price"] = block_results["price"]
        results["platform_commission"] = block_results["platform_commission"]
        results["reservation_wage"] = block_results["reservation_wage"]
        results["demand_elasticity"] = block_results["demand_elasticity"]
        results["use_city_scale"] = block_results["use_city_scale"]
        results["mean_vehicle_speed"] = block_results["mean_vehicle_speed"]
        results["minutes_per_block"] = block_results["minutes_per_block"]
        results["per_hour_opportunity_cost"] = block_results[
            "per_hour_opportunity_cost"
        ]
        results["per_km_ops_cost"] = block_results["per_km_ops_cost"]
        results["per_km_price"] = block_results["per_km_price"]
        results["per_minute_price"] = block_results["per_minute_price"]
        if return_values == "map":
            results["vehicles"] = block_results["vehicles"]
            results["trips"] = block_results["trips"]
        for item in list(Measure):
            results[item.name] = block_results[item.name]
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
            results = self._get_block_results(return_values="map")
            self.block_index += 1
            # print(f"wo: trips={block_results['trips']}")
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
                        vehicle[2] = (
                            live_vehicle.direction.name
                        )  # Update to dropoff direction
                        direction = vehicle[
                            2
                        ]  # Use updated direction for midpoint offset

                if direction == Direction.NORTH.name:
                    vehicle[1][1] += 0.5
                elif direction == Direction.EAST.name:
                    vehicle[1][0] += 0.5
                elif direction == Direction.SOUTH.name:
                    vehicle[1][1] -= 0.5
                elif direction == Direction.WEST.name:
                    vehicle[1][0] -= 0.5
            results["vehicles"] = [vehicle for vehicle in self.old_results["vehicles"]]
            results["trips"] = self.old_results["trips"]
        # TODO: Fix this block/frame disconnect
        # For now, return the frame index, not the block index
        # results["block"] = self.frame_index
        results["frame"] = self.frame_index
        results["version"] = self.version
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
                # vehicle_data is [phase_name, location, direction_name, pickup_countdown]
                if len(vehicle_data) >= 3:
                    js_vehicle = {
                        "phase": vehicle_data[0],  # phase.name string
                        "location": list(vehicle_data[1])
                        if hasattr(vehicle_data[1], "__iter__")
                        else vehicle_data[1],  # ensure it's a list
                        "direction": vehicle_data[2],  # direction.name string
                    }
                    # Add pickup_countdown if available (4th element)
                    if len(vehicle_data) >= 4:
                        js_vehicle["pickup_countdown"] = vehicle_data[3]
                    js_vehicles.append(js_vehicle)
            js_results["vehicles"] = js_vehicles
        return js_results

    def next_block_stats(self):
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
        results = self._get_block_results(return_values="stats")
        results["version"] = self.version  # Add version to stats results
        results["frame"] = self.frame_index
        self.frame_index += 1
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
        self.sim.target_state["platform_commission"] = float(
            options["platformCommission"]
        )
        self.sim.target_state["inhomogeneity"] = float(options["inhomogeneity"])
        self.sim.target_state["idle_vehicles_moving"] = bool(
            options["idleVehiclesMoving"]
        )
        self.sim.target_state["demand_elasticity"] = float(options["demandElasticity"])

    def get_simulation_results(self):
        """
        Get simulation results for inclusion in configuration file downloads.

        Retrieves the final simulation results using get_result_measures() from a
        RideHailSimulationResults object. These results are used by the web interface to
        append a [RESULTS] section to downloaded configuration files.

        Returns:
            dict: Results dictionary with simulation metrics including:
                - Simulation metadata (timestamp, version, duration)
                - Vehicle metrics (mean count, phase fractions)
                - Trip metrics (request rate, wait times, distances)
                - Validation metrics (convergence checks)
                Returns empty dict if simulation hasn't run for at least results_window blocks.

        Note:
            Called from webworker.js when user downloads configuration with results.
            Results format matches the desktop application's write_results_section().
        """
        # Check if simulation has run for at least results_window blocks
        # This prevents division by zero errors in get_result_measures()
        if self.sim.block_index < self.sim.results_window:
            # Not enough blocks simulated to compute meaningful results
            return {}

        # Create a RideHailSimulationResults object from the current simulation
        simulation_results = RideHailSimulationResults(self.sim)
        return simulation_results.get_result_measures()
