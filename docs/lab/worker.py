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
from ridehail.results import RideHailSimulationResults
from ridehail.atom import Direction, Measure, Equilibration
import copy

# Global simulation instance (initialized by init_simulation)
sim = None

# Above this city size, next_frame_map() never generates the interpolated
# mid-block frame - every call advances a real simulation block instead.
# At large city sizes the map shows snapped (non-eased) movement anyway (see
# SNAP_MOVEMENT_CITY_SIZE_THRESHOLD in docs/lab/modules/map.js), so the
# interpolated frame was pure overhead: computed, marshalled to JS, and
# round-tripped through the backpressure ack, only to be displayed as a
# visibly distinct "mid-block" state that flickered against the snapped
# real-block state instead of reading as motion.
# Must match INTERPOLATE_MAX_CITY_SIZE in docs/lab/js/constants.js - Python
# can't import a JS module, so this is a deliberate, commented duplicate.
INTERPOLATE_MAX_CITY_SIZE = 32


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
        # See INTERPOLATE_MAX_CITY_SIZE above.
        self.interpolate_frames = (
            int(web_config["citySize"]) <= INTERPOLATE_MAX_CITY_SIZE
        )

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
                - vehicles (list): Vehicle data as arrays [phase, location, direction, pickup_countdown]
                - trips (list): Active trip markers (origins and destinations)
                - [various simulation parameters and measurements]

        Note:
            Called from webworker.js when chartType == "map"
            Vehicle positions are interpolated +0.5 in movement direction on odd frames
            Pickup countdown logic prevents midpoint movement during passenger pickup
            When self.interpolate_frames is False (city_size above
            INTERPOLATE_MAX_CITY_SIZE), every call takes this branch - the
            odd-frame interpolation below is never reached, and webworker.js
            sizes its frame-count pacing accordingly (1 frame per block
            instead of 2).
        """
        results = {}
        if not self.interpolate_frames or self.frame_index % 2 == 0:
            # It's a real block: do the simulation
            results = self._get_block_results(return_values="map")
            self.block_index += 1
            # print(f"wo: trips={block_results['trips']}")
            # Results come back as a dictionary:
            # {"block": integer,
            #  "vehicles": [[phase.name, location, direction],...],
            #  "trips": [[phase.name, origin, destination, distance],...],
            # }
            # Only the vehicles are mutated during interpolation (odd frames):
            # the inner location lists are *live references* to sim vehicle state
            # (see simulation.py state_dict["vehicles"]), so they must be deep
            # copied or interpolation would corrupt the running simulation. The
            # rest of the dict is immutable scalars plus trips (passed through but
            # never mutated), so a shallow copy of those is safe and avoids
            # deep-copying every per-block measure each block.
            self.old_results = dict(results)
            self.old_results["vehicles"] = copy.deepcopy(results["vehicles"])
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
        # Vehicles stay in array form [phase, location, direction, pickup_countdown].
        # webworker.js converts the whole result with
        # toJs({dict_converter: Object.fromEntries}) and map.js consumes the vehicle
        # arrays directly, so no per-frame objectification is needed here.
        self.frame_index += 1
        return results

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
            - platform_commission: Platform's commission percentage
            - inhomogeneity: Spatial demand variation
            - idle_vehicles_moving: Whether idle vehicles drive randomly
            - demand_elasticity: Price sensitivity of demand
            - price: Per-block fare (non-city-scale mode; see note below)
            - reservation_wage: Driver reservation wage (non-city-scale mode)
            - equilibration: Equilibration mode (none/price/supply)

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
        self.sim.target_state["price"] = float(options["price"])
        self.sim.target_state["reservation_wage"] = float(options["reservationWage"])
        # Equilibration is a string from the UI ("none"/"price"/"supply"); convert
        # to the enum as __init__ does. Note: when use_city_scale is on, the core
        # recomputes price and reservation_wage from the cost-per-unit inputs each
        # block (after target_state is applied), so those two live updates have no
        # effect in that mode; they apply in the default non-city-scale mode.
        equilibration_str = options.get("equilibration")
        if equilibration_str:
            try:
                self.sim.target_state["equilibration"] = Equilibration[
                    equilibration_str.upper()
                ]
            except KeyError:
                self.sim.target_state["equilibration"] = Equilibration.NONE

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
