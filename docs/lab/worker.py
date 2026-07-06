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
from ridehail.atom import Measure, Equilibration, TripDistribution
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

# Maps Python (snake_case) config parameter names to the JS (camelCase) names
# the web UI uses. Shared by get_slider_help() and get_slider_config().
PARAM_NAME_MAP = {
    "city_size": "citySize",
    "vehicle_count": "vehicleCount",
    "base_demand": "requestRate",
    "inhomogeneity": "inhomogeneity",
    "idle_vehicles_moving": "idleVehiclesMoving",
    "mean_trip_distance": "meanTripDistance",
    "mean_vehicle_speed": "meanVehicleSpeed",
    "pickup_time": "pickupTime",
    "demand_elasticity": "demandElasticity",
    "price": "price",
    "per_km_price": "perKmPrice",
    "per_minute_price": "perMinutePrice",
    "platform_commission": "platformCommission",
    "reservation_wage": "reservationWage",
    "per_hour_opportunity_cost": "perHourOpportunityCost",
    "per_km_ops_cost": "perKmOpsCost",
    "smoothing_window": "smoothingWindow",
    "animation_delay": "animationDelay",
}


def get_slider_help():
    """Return extended descriptions for web UI slider help popovers.

    Reads ConfigItem.description tuples from RideHailConfig and returns a dict
    mapping JS camelCase parameter names to a list of description sentences.
    Element 0 of each tuple is a type/default signature (not useful in the UI),
    so only elements from index 1 onward are included.  Parameters with fewer
    than two description elements are omitted.

    Called once from webworker.js immediately after Pyodide finishes loading,
    piggybacked on the "Pyodide loaded" postMessage.
    """
    # Static metadata only: no config file or command-line parsing needed.
    config = RideHailConfig(use_config_file=False)
    result = {}
    for py_name, js_name in PARAM_NAME_MAP.items():
        item = getattr(config, py_name, None)
        if item is None:
            continue
        desc = getattr(item, "description", None)
        if isinstance(desc, (tuple, list)) and len(desc) > 1:
            result[js_name] = list(desc[1:])
    return result


def get_slider_config():
    """Return per-slider constraint metadata for the web UI, keyed by JS name.

    Exposes the structural constraints the Python config enforces so the browser
    imposes the same rules instead of hard-coding (or omitting) them:

    - "integer": true      - value must be a whole number (ConfigItem.type is int)
    - "even": true         - value must be an even integer (must_be_even)
    - "maxRelativeTo"/"maxFraction" - declarative cross-parameter upper bound
                             (from ConfigItem.max_relation), e.g. mean_trip_distance
                             must be no greater than city_size / 2

    Only parameters that carry at least one constraint appear. Static per-slider
    ranges (min/max, log scale) remain a UI presentation concern and stay in the
    HTML; those web ranges are intentionally narrower than the Python validation
    bounds.

    Called once from webworker.js immediately after Pyodide finishes loading,
    piggybacked on the "Pyodide loaded" postMessage, alongside get_slider_help().
    """
    # Static metadata only: no config file or command-line parsing needed.
    config = RideHailConfig(use_config_file=False)
    result = {}
    for py_name, js_name in PARAM_NAME_MAP.items():
        item = getattr(config, py_name, None)
        if item is None:
            continue
        entry = {}
        if item.type is int:
            entry["integer"] = True
        if item.must_be_even:
            entry["even"] = True
        relation = getattr(item, "max_relation", None)
        if relation:
            base_js_name = PARAM_NAME_MAP.get(relation["param"])
            if base_js_name:
                entry["maxRelativeTo"] = base_js_name
                entry["maxFraction"] = relation["fraction"]
        if entry:
            result[js_name] = entry
    return result


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
        old_results (dict): Trips from the previous block, used for midpoint frames
        prev_positions (dict): Vehicle positions keyed by index, from the previous block
        prev_directions (dict): Vehicle direction strings keyed by index, from the previous
            block — used to give midpoint frames the correct facing direction (the direction
            the vehicle was traveling, not the new direction chosen on arrival)
        pending_results (dict | None): Pre-computed block results waiting to be returned
            on the next even frame (set by odd frames, cleared by even frames)
        frame_index (int): Current animation frame (2 frames per simulation block)

    Frame Indexing:
        Even frames (0, 2, 4...): Return pre-computed block results (set by odd frame).
            Exception: frame 0 runs the first block directly (no pending results yet).
        Odd frames (1, 3, 5...): Run the simulation block, compute midpoint positions
            from actual prev→new movement, save the real block for the next even frame.
        This ordering means midpoints are always based on the vehicle's *actual* next
        position, eliminating false midpoints for stationary vehicles and edge-wrap ghosts.
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
            config.mean_trip_distance.value = int(web_config["meanTripDistance"])
        except (TypeError, ValueError):
            config.mean_trip_distance.value = None
        config.min_trip_distance.value = web_config.get("minTripDistance", 0)
        config.inhomogeneity.value = float(web_config["inhomogeneity"])
        config.inhomogeneous_destinations.value = bool(
            web_config["inhomogeneousDestinations"]
        )
        config.idle_vehicles_moving.value = float(
            web_config.get("idleVehiclesMoving", 1.0)
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
        # Trip distance distribution — not exposed in web UI but honoured when
        # a .config file containing the setting is uploaded
        tdd_str = web_config.get("tripDistanceDistribution")
        if tdd_str:
            try:
                config.trip_distance_distribution.value = TripDistribution[
                    tdd_str.upper()
                ]
            except KeyError:
                config.trip_distance_distribution.value = TripDistribution.UNIFORM
        else:
            config.trip_distance_distribution.value = TripDistribution.UNIFORM
        # User-editable scenario title (blank/missing means no title, matching
        # the desktop config's default)
        config.title.value = web_config.get("title") or None

        self.sim = RideHailSimulation(config)
        self.plot_buffers = {}
        self.results = {}
        self.smoothing_window = config.smoothing_window.value
        for plot_property in list(Measure):
            self.results[plot_property.value] = 0
        self.old_results = {}
        self.prev_positions = {}
        self.prev_directions = {}
        self.pending_results = None
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
        results["mean_trip_distance"] = block_results["mean_trip_distance"]
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

        Implements a two-frame-per-block animation system for smooth vehicle movement.
        Frame ordering (when interpolate_frames is True):

        - Frame 0 (first ever, even, no pending_results): run block → show real positions.
        - Odd frames (1, 3, 5...): run the NEXT block → emit midpoint positions computed
          from actual prev→new movement; cache the real block as pending_results.
        - Even frames (2, 4, 6..., when pending_results exists): return cached real block.

        Running the block on odd frames ensures midpoint positions are derived from *actual*
        displacement rather than forward-projected direction, which eliminates:
        - False midpoints for stationary vehicles (idle_vehicles_moving < 1)
        - Phantom edge-wrap flicker when a stationary vehicle sits near a torus boundary

        Trip marker changes are held back to even (real-block) frames to stay in sync with
        the JS-side display timing.

        Returns:
            dict: Frame results containing:
                - frame (int): Current frame index (NOT simulation block number)
                - vehicles (list): Vehicle data as arrays [phase, location, direction, pickup_countdown]
                - trips (list): Active trip markers (origins and destinations)
                - [various simulation parameters and measurements]

        Note:
            Called from webworker.js when chartType == "map".
            When self.interpolate_frames is False (city_size above
            INTERPOLATE_MAX_CITY_SIZE), every call runs a block directly;
            webworker.js sizes its frame-count pacing accordingly (1 frame per block
            instead of 2).
        """
        results = {}
        if not self.interpolate_frames:
            # No interpolation: run the block and return directly every call.
            results = self._get_block_results(return_values="map")
            self.block_index += 1
        elif self.frame_index % 2 == 0 and self.pending_results is not None:
            # Even frame (not the first): return the block results pre-computed by
            # the previous odd frame.  Trips at even frames = new-block trips, so
            # the JS side sees trip changes at even frames (same as before).
            results = self.pending_results
            self.pending_results = None
        else:
            # First frame (frame_index == 0, pending_results is None) OR any odd frame:
            # run the simulation block now.
            #
            # Results come back as a dictionary:
            # {"block": integer,
            #  "vehicles": [[phase.name, location, direction, pickup_countdown],...],
            #  "trips": [[phase.name, origin, destination, distance],...],
            # }
            # The inner location lists are *live references* to sim vehicle state
            # (see simulation.py state_dict["vehicles"]), so they must be deep
            # copied before mutation; the rest of the dict is immutable scalars
            # plus trips which are never mutated, so a shallow copy suffices.
            results = self._get_block_results(return_values="map")
            self.block_index += 1

            if self.frame_index % 2 == 1:
                # Odd frame: save the real block for the upcoming even frame, then
                # build midpoint positions from *actual* prev→new vehicle movement.
                # This eliminates false midpoints for stationary vehicles and the
                # phantom edge-wrap flicker they cause.
                self.pending_results = dict(results)
                self.pending_results["vehicles"] = copy.deepcopy(results["vehicles"])

                interp_vehicles = copy.deepcopy(results["vehicles"])
                for idx, vehicle in enumerate(interp_vehicles):
                    prev_pos = self.prev_positions.get(idx)
                    if prev_pos is None:
                        continue
                    new_pos = results["vehicles"][idx][1]
                    dx = new_pos[0] - prev_pos[0]
                    dy = new_pos[1] - prev_pos[1]

                    if dx == 0 and dy == 0:
                        # Stationary: keep at previous position, no midpoint offset.
                        vehicle[1] = list(prev_pos)
                    elif abs(dx) > 1 or abs(dy) > 1:
                        # Edge-wrap: push 0.5 beyond the boundary from prev_pos so
                        # that map.js edge-wrap detection fires and teleports the
                        # vehicle to the opposite side.  Direction is inferred from
                        # the sign of the modular displacement (avoids relying on the
                        # vehicle's post-wrap direction field which may have changed).
                        vehicle[1] = list(prev_pos)
                        if abs(dx) > 1:
                            vehicle[1][0] += 0.5 if dx < 0 else -0.5
                        if abs(dy) > 1:
                            vehicle[1][1] += 0.5 if dy < 0 else -0.5
                    else:
                        # Normal single-block movement: place at midpoint.
                        vehicle[1][0] = prev_pos[0] + dx / 2
                        vehicle[1][1] = prev_pos[1] + dy / 2

                    # Restore the direction from the *previous* block so the vehicle
                    # faces the way it was traveling, not the new direction chosen at
                    # the end of the block it just completed.
                    prev_dir = self.prev_directions.get(idx)
                    if prev_dir is not None:
                        vehicle[2] = prev_dir

                results = dict(results)
                results["vehicles"] = interp_vehicles
                # Show previous block's trips at the midpoint frame so that trip
                # marker changes coincide with even (real-block) frames, consistent
                # with the existing JS-side update timing.
                results["trips"] = self.old_results.get("trips", [])

            # Update state for the next midpoint computation.
            # Use the actual (non-midpoint) block positions.
            block_vehicles = (
                self.pending_results["vehicles"]
                if self.pending_results is not None
                else results["vehicles"]
            )
            self.prev_positions = {
                idx: list(v[1]) for idx, v in enumerate(block_vehicles)
            }
            self.prev_directions = {idx: v[2] for idx, v in enumerate(block_vehicles)}
            block_trips = (
                self.pending_results if self.pending_results is not None else results
            ).get("trips", [])
            self.old_results = {"trips": block_trips}

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
        self.sim.target_state["idle_vehicles_moving"] = float(
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
