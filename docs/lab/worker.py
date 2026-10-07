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

    # Follow one car on the map ("i" key): see Simulation.follow_vehicle
    sim.follow_vehicle("random")

    # Game mode (the Game tab): see GameSimulation below
    init_game(settings)
    sim.resolve_offer(accept, timed_out)
    sim.game_results()
"""

from ridehail import __version__
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.results import RideHailSimulationResults
from ridehail.atom import Measure, Equilibration, TripDistribution, VehiclePhase
import copy
import random

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
# can't import a JS module, so this is a deliberate duplicate, checked by
# test/test_web_lab_constants.py.
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
    "base_fare": "baseFare",
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


def get_presets():
    """Return the Village/Town/City preset starting values, keyed by JS name.

    This is the authoritative source of the web lab's presets: the values live
    in ridehail/presets.py (shared by the desktop --preset CLI option), and the
    browser overlays them onto its slider ranges instead of hard-coding a second
    copy in docs/lab/js/config.js. Each preset is the full merged parameter set
    (geometry + Toronto-calibrated economics) with parameter names mapped from
    Python snake_case to the JS camelCase the UI uses. Preset parameters that
    have no matching web control (i.e. not in PARAM_NAME_MAP) are omitted.

    Returns a dict of the form::

        {"village": {"citySize": 8, "vehicleCount": 6, ...}, "town": {...}, ...}

    Called once from webworker.js immediately after Pyodide finishes loading,
    piggybacked on the "Pyodide loaded" postMessage, alongside get_slider_help()
    and get_slider_config().
    """
    from ridehail.presets import PRESET_NAMES, get_preset

    result = {}
    for name in PRESET_NAMES:
        js_values = {}
        for py_name, value in get_preset(name).items():
            js_name = PARAM_NAME_MAP.get(py_name)
            if js_name:
                js_values[js_name] = value
        result[name] = js_values
    return result


def _int_or_none(value):
    """int(value), or None for a JS null (JsNull in Pyodide, not None) or blank."""
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


# How the web lab's settings (js/sim-settings.js) set the simulation config:
# config item -> (web setting, conversion). See Simulation.__init__.
WEB_SETTINGS = {
    "city_size": ("citySize", int),
    "vehicle_count": ("vehicleCount", int),
    "base_demand": ("requestRate", float),
    # null means "use the default" (city_size // 2, set by the config)
    "mean_trip_distance": ("meanTripDistance", _int_or_none),
    "inhomogeneity": ("inhomogeneity", float),
    "inhomogeneous_destinations": ("inhomogeneousDestinations", bool),
    # null means non-deterministic random numbers
    "random_number_seed": ("randomNumberSeed", _int_or_none),
    "verbosity": ("verbosity", int),
    "equilibration_interval": ("equilibrationInterval", int),
    "demand_elasticity": ("demandElasticity", float),
    "use_city_scale": ("useCostsAndIncomes", bool),
    "mean_vehicle_speed": ("meanVehicleSpeed", float),
    "minutes_per_block": ("minutesPerBlock", float),
    "reservation_wage": ("reservationWage", float),
    "platform_commission": ("platformCommission", float),
    "price": ("price", float),
    "per_km_price": ("perKmPrice", float),
    "per_minute_price": ("perMinutePrice", float),
    "per_km_ops_cost": ("perKmOpsCost", float),
    "per_hour_opportunity_cost": ("perHourOpportunityCost", float),
    "time_blocks": ("timeBlocks", int),
    "smoothing_window": ("smoothingWindow", int),
    # results_window should match smoothing_window for consistent calculations
    # (desktop typically uses a larger results_window)
    "results_window": ("smoothingWindow", int),
    # milliseconds in the web lab, seconds in the config
    "animation_delay": ("animationDelay", lambda ms: float(ms) / 1000.0),
}
# Settings that older saved sessions don't have:
# config item -> (web setting, conversion, default)
OPTIONAL_WEB_SETTINGS = {
    "min_trip_distance": ("minTripDistance", lambda value: value, 0),
    "idle_vehicles_moving": ("idleVehiclesMoving", float, 1.0),
    "pickup_time": ("pickupTime", int, 1),
    "base_fare": ("baseFare", lambda value: float(value or 0.0), 0.0),
}

# The block's settings that each frame carries, besides every Measure (and
# the title, if there is one). The simulation's state dict has a few more,
# which the browser doesn't use.
FRAME_SETTINGS = (
    "city_size",
    "vehicle_count",
    "base_demand",
    "inhomogeneity",
    "min_trip_distance",
    "mean_trip_distance",
    "idle_vehicles_moving",
    "time_blocks",
    "price",
    "platform_commission",
    "reservation_wage",
    "demand_elasticity",
    "use_city_scale",
    "mean_vehicle_speed",
    "minutes_per_block",
    "per_hour_opportunity_cost",
    "per_km_ops_cost",
    "per_km_price",
    "per_minute_price",
)


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
        for item, (name, convert) in WEB_SETTINGS.items():
            getattr(config, item).value = convert(web_config[name])
        for item, (name, convert, default) in OPTIONAL_WEB_SETTINGS.items():
            getattr(config, item).value = convert(web_config.get(name, default))
        config.run_sequence.value = False
        config.animation.value = "none"
        config.interpolate.value = 0
        config.equilibration.value = self._equilibration(web_config)
        # Trip distance distribution — not exposed in web UI but honoured when
        # a .config file containing the setting is uploaded
        config.trip_distance_distribution.value = TripDistribution.UNIFORM
        tdd_str = web_config.get("tripDistanceDistribution")
        if tdd_str and tdd_str.upper() in TripDistribution.__members__:
            config.trip_distance_distribution.value = TripDistribution[tdd_str.upper()]
        # User-editable scenario title (blank/missing means no title, matching
        # the desktop config's default)
        config.title.value = web_config.get("title") or None

        self.sim = RideHailSimulation(config)
        self._init_frame_state(int(web_config["citySize"]))

    @staticmethod
    def _equilibration(web_config):
        """
        The equilibration method: the "equilibration" string (none, price,
        ...) if there is one, else the legacy "equilibrate" boolean (price or
        none). An unknown string means none.
        """
        equilibration_str = web_config.get("equilibration")
        if equilibration_str:
            return Equilibration.__members__.get(
                equilibration_str.upper(), Equilibration.NONE
            )
        if bool(web_config.get("equilibrate", False)):
            return Equilibration.PRICE
        return Equilibration.NONE

    def _init_frame_state(self, city_size):
        """Wrapper state for frame generation, shared with GameSimulation."""
        self.old_results = {}
        self.prev_positions = {}
        self.prev_directions = {}
        self.pending_results = None
        self.frame_index = 0
        # Store version for inclusion in results
        self.version = __version__
        # See INTERPOLATE_MAX_CITY_SIZE above.
        self.interpolate_frames = city_size <= INTERPOLATE_MAX_CITY_SIZE
        # The previous block's vehicle indexes, in sim.vehicles order, to spot
        # a fleet change that shifts cars along the list (see "reindexed" in
        # _get_block_results)
        self.block_vehicle_indexes = []
        # The car followed on the map, by vehicle index (stable for the whole
        # run, unlike its position in sim.vehicles), or None; and its trip as
        # shown on the last frame sent (see follow_vehicle)
        self.followed_index = None
        self.shown_followed = None
        # Picks the car to follow. Not the global random module, which the
        # simulation seeds and draws from: following a car must not change
        # the run.
        self.follow_rng = random.Random()

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
            The state dict holds no enums: the simulation already gives
            their names (e.g. Direction.NORTH as "NORTH").
        """
        block_results = self.sim.next_block(
            jsonl_file_handle=None,
            csv_file_handle=None,
            return_values=return_values,
        )
        results = {"block": block_results["block"]}
        if "title" in block_results:
            results["title"] = block_results["title"]
        for key in FRAME_SETTINGS:
            results[key] = block_results[key]
        if return_values == "map":
            results["vehicles"] = block_results["vehicles"]
            results["trips"] = block_results["trips"]
            # The map matches each car to its previous frame's point by
            # position in the vehicle list. Removing vehicles shifts the cars
            # after them along the list, so on this block's first frame those
            # would glide from a neighbour's place: map.js snaps instead.
            # (Added vehicles go on the end and shift nobody.)
            indexes = [v.index for v in self.sim.vehicles]
            results["reindexed"] = any(
                a != b for a, b in zip(self.block_vehicle_indexes, indexes)
            )
            self.block_vehicle_indexes = indexes
            results["followed"] = self._followed_trip()
        for item in Measure:
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

            if self.frame_index % 2 == 1:
                # Odd frame: save the real block for the upcoming even frame, then
                # build midpoint positions from *actual* prev→new vehicle movement.
                # This eliminates false midpoints for stationary vehicles and the
                # phantom edge-wrap flicker they cause.
                self.pending_results = dict(results)
                self.pending_results["vehicles"] = copy.deepcopy(results["vehicles"])
                # Same vehicle list as this (midpoint) frame
                self.pending_results["reindexed"] = False

                interp_vehicles = copy.deepcopy(results["vehicles"])
                # results["vehicles"] lists the vehicles in sim.vehicles order.
                # Match each one with its previous position by vehicle index,
                # not by position in the list: removing vehicles shifts the
                # ones after them.
                vehicle_ids = [v.index for v in self.sim.vehicles]
                for idx, vehicle in zip(vehicle_ids, interp_vehicles):
                    prev_pos = self.prev_positions.get(idx)
                    if prev_pos is None:
                        continue
                    new_pos = vehicle[1]
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
                # And the followed car's trip as of the previous block, like
                # its colour (map.js changes colours on real-block frames)
                results["followed"] = self.shown_followed

            # Update state for the next midpoint computation.
            # Use the actual (non-midpoint) block positions.
            block_vehicles = (
                self.pending_results["vehicles"]
                if self.pending_results is not None
                else results["vehicles"]
            )
            # Keyed by vehicle index (see the midpoint loop above)
            vehicle_ids = [v.index for v in self.sim.vehicles]
            self.prev_positions = {
                idx: list(v[1]) for idx, v in zip(vehicle_ids, block_vehicles)
            }
            self.prev_directions = {
                idx: v[2] for idx, v in zip(vehicle_ids, block_vehicles)
            }
            block_trips = (
                self.pending_results if self.pending_results is not None else results
            ).get("trips", [])
            self.old_results = {"trips": block_trips}

        if "followed" in results:
            if not (self.interpolate_frames and self.frame_index % 2 == 1):
                self.shown_followed = results["followed"]
            results["followed"] = self._followed_payload(results["followed"])
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

    def follow_vehicle(self, choice):
        """
        Follow a car on the map (the "i" key), or stop following it.

        The car is held by its vehicle index, which stays the same for the
        whole run; its position in sim.vehicles (which is how frames list
        cars) shifts when vehicles are removed, so each frame looks it up
        again (_followed_payload). Map frames then carry results["followed"]:
        None when no car is followed, else the payload of _followed_payload.

        Args:
            choice: "random" to follow a randomly chosen car, preferring an
                idle one so that its next trip is seen from the start (a
                different car if one is already followed); a vehicle index
                to follow that car; anything else (None) to stop

        Returns:
            dict | None: the followed payload for the frame now on screen,
            so that the map can show it at once (e.g. while paused)
        """
        previous = self.followed_index
        self.followed_index = None
        if choice == "random":
            others = [v for v in self.sim.vehicles if v.index != previous]
            idle = [v for v in others if v.phase == VehiclePhase.P1]
            pool = idle or others
            if pool:
                self.followed_index = self.follow_rng.choice(pool).index
        elif isinstance(choice, (int, float)):
            self.followed_index = int(choice)
        # The frame on screen, and the real-block frame that may be waiting
        # to follow it, now show this car (or none)
        self.shown_followed = self._followed_trip()
        if self.pending_results is not None:
            self.pending_results["followed"] = self.shown_followed
        return self._followed_payload(self.shown_followed)

    def _followed_trip(self):
        """The followed car's trip as of now, without its list position."""
        if self.followed_index is None:
            return None
        vehicle = next(
            (v for v in self.sim.vehicles if v.index == self.followed_index), None
        )
        if vehicle is None:
            return {"index": self.followed_index, "left": True}
        next_pickup = vehicle.forward_dispatch_pickup_location
        return {
            "index": vehicle.index,
            "phase": vehicle.phase.name,
            "pickup": list(vehicle.pickup_location) or None,
            "dropoff": list(vehicle.dropoff_location) or None,
            # A forward-dispatched car's next pickup, while still in P3
            "next_pickup": list(next_pickup) if next_pickup else None,
        }

    def _followed_payload(self, trip):
        """
        A frame's results["followed"]: the trip (from _followed_trip) plus
        the car's position in the frame's vehicle list, which is
        sim.vehicles as it is now (both frames of an interpolated pair show
        the same list). None if no car is followed, or the trip is for a
        car no longer followed. If the car has left the fleet (only idle
        cars are removed), {"index", "left": True}, once, and the car is no
        longer followed.
        """
        if trip is None or trip["index"] != self.followed_index:
            return None
        position = next(
            (
                i
                for i, v in enumerate(self.sim.vehicles)
                if v.index == self.followed_index
            ),
            None,
        )
        if trip.get("left") or position is None:
            self.followed_index = None
            self.shown_followed = None
            if self.pending_results is not None:
                self.pending_results["followed"] = None
            return {"index": trip["index"], "left": True}
        return dict(trip, position=position)

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
        # The slider is in user-facing units (trips/min in city-scale mode)
        self.sim.target_state["base_demand"] = self.sim.demand_from_display(
            float(options["requestRate"])
        )
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


def init_game(settings):
    """
    Start a game shift (the Game tab). Like init_simulation, sets the global
    `sim`, here to a GameSimulation.

    Args:
        settings: Pyodide proxy of the game settings from game-tab.js, with
                  "market" (busy/normal/slow), "code" (the shift code),
                  "card" (helper/platform: the offer screen) and "city"
                  (standard/big; see ridehail.game.CITIES)
    """
    global sim
    sim = GameSimulation(settings)
    return sim


class GameSimulation(Simulation):
    """
    A game shift: a RideHailSimulation driven by ridehail.game.GameController.

    All game logic (prices, bots, the player's ledger, offers) is in
    ridehail/game/; this class adds the controller's per-block hooks to the
    frame loop and attaches its payload to each frame as results["game"].

    Offer timing: a block runs on an odd (interpolated) frame, and its real
    positions are shown on the following even frame. A pending offer, and the
    shift-over flag, are therefore sent only with real-block frames; an
    interpolated frame repeats the payload of the previous real block. The
    offer card appears when the car visibly reaches the intersection where it
    was dispatched, and webworker.js holds the frame loop there until the
    player decides (resolve_offer).
    """

    def __init__(self, settings):
        from ridehail.game import create_game

        game_settings = settings.to_py()
        self.sim, self.game = create_game(
            market=game_settings.get("market", "normal"),
            code=str(game_settings.get("code", "practice")),
            card=game_settings.get("card", "helper"),
            city=game_settings.get("city", "standard"),
        )
        self._init_frame_state(self.sim.city_size)
        self._shown_payload = self.game.frame_payload()

    def _get_block_results(self, return_values):
        self.game.before_block()
        results = super()._get_block_results(return_values)
        self.game.after_block()
        results["game"] = self.game.frame_payload()
        return results

    def next_frame_map(self):
        results = super().next_frame_map()
        if self.interpolate_frames and results["frame"] % 2 == 1:
            # Interpolated midpoint frame: hold the offer and HUD back to the
            # real-block frame that follows (see the class docstring)
            results["game"] = self._shown_payload
        else:
            self._shown_payload = results["game"]
        return results

    def resolve_offer(self, accept, timed_out=False):
        """
        Apply the player's decision on the pending offer, before the next block.
        """
        entry = self.game.resolve_offer(bool(accept), bool(timed_out))
        if entry is not None and entry["decision"] == "accept":
            # Accepting turns the car toward the pickup. The next interpolated
            # frame draws each car facing its direction from the previous block
            # (prev_directions), so update the player's to the new heading.
            vehicle = self.game.player_vehicle
            self.prev_directions[vehicle.index] = vehicle.direction.name
        self._shown_payload = self.game.frame_payload()
        return entry

    def game_results(self):
        """Everything the end-of-shift debrief needs (ridehail.game results)."""
        return self.game.results()
