import enum
import logging
import random
import sys
from ridehail.atom import DispatchMethod, VehiclePhase, TripPhase


class OfferDecision(enum.Enum):
    """
    A driver's answer when the dispatcher offers them a trip (see
    Dispatch.offer_filter).
    """

    ACCEPT = "accept"
    # The dispatcher moves on to the next-nearest vehicle for this trip.
    DECLINE = "decline"
    # The decision is pending (a human player): the trip stays UNASSIGNED and
    # the vehicle leaves the pool for the rest of this dispatch call. The
    # caller resolves the offer later, e.g. with Dispatch.commit_dispatch.
    DEFER = "defer"


class Dispatch:
    """
    Handle all dispatch-related tasks.
    Uses a factory pattern to call the appropriate dispatch function
    """

    def __init__(
        self, dispatch_method=DispatchMethod.DEFAULT, forward_dispatch_bias=0.0
    ):
        self.dispatch_method = dispatch_method
        self.forward_dispatch_bias = forward_dispatch_bias
        # Optional hook, used by game mode: a callable
        # offer_filter(trip, vehicle, dispatch_distance) -> OfferDecision,
        # consulted before each assignment is committed. None (the default)
        # commits every assignment, exactly as before the hook existed.
        # Supported by the DEFAULT dispatch method only.
        self.offer_filter = None
        # Vehicle indexes that are logged off (game mode, before the shift):
        # left out of the dispatch pool, so they are never offered a trip.
        # Declining every offer would leave them in the pool, and once the
        # rest of the pool is used up within a block, each remaining trip
        # would search the whole city for them. DEFAULT dispatch method only.
        self.offline = frozenset()

    def dispatch_vehicles(self, unassigned_trips, city, vehicles):
        """
        All trips without an assigned vehicle make a request.
        Dispatch a vehicle to each trip.
        """
        dispatcher = self._get_dispatch_function()
        return dispatcher(unassigned_trips, city, vehicles)

    def _get_dispatch_function(self):
        """
        All trips without an assigned vehicle make a request.
        Dispatch a vehicle to each trip.
        """
        if (
            self.offer_filter is not None
            and self.dispatch_method != DispatchMethod.DEFAULT
        ):
            raise ValueError(
                f"offer_filter is not supported by dispatch method "
                f"{self.dispatch_method.name}"
            )
        if self.dispatch_method == DispatchMethod.DEFAULT:
            dispatcher = self._dispatch_vehicles_default
        elif self.dispatch_method == DispatchMethod.FORWARD_DISPATCH:
            dispatcher = self._dispatch_vehicles_forward_dispatch
        elif self.dispatch_method == DispatchMethod.P1_LEGACY:
            dispatcher = self._dispatch_vehicles_p1_legacy
        elif self.dispatch_method == DispatchMethod.RANDOM:
            dispatcher = self._dispatch_vehicles_random
        else:
            logging.error(f"Unrecognized dispatch method {self.dispatch_method}")
            sys.exit(-1)
        return dispatcher

    # The sparse search is used once the idle pool has at most
    # SPARSE_SEARCH_FACTOR * city_size vehicles. Measured optimum is flat over
    # 1.0-1.5 (claude/dispatch-changeover-criterion.md); a class attribute so
    # benchmarks/bench_dispatch.py can sweep it.
    SPARSE_SEARCH_FACTOR = 1.0

    @classmethod
    def _use_sparse_search(cls, vehicle_count, city_size):
        """
        ADAPTIVE DISPATCH: choose the search for the next trip from the number
        of idle vehicles still in the pool. Returns True for the sparse
        (vehicle-loop) search, False for the dense (location-ring) search.

        Per trip, with m idle vehicles left:
        - sparse scans the pool list: cost ~ m
        - dense ring-searches outward to the nearest vehicle: ~ city_size^2 / m
          cells (plus an O(P1) grid build, once per block)
        so they cross at m ~ city_size, times a measured constant.

        The decision is made per trip, not per block. Every dispatch removes a
        vehicle, so when the backlog is at least the idle pool the pool drains
        to zero within the block. A once-per-block dense choice then pays for
        whole-city scans to find the last few vehicles (~ city_size^2 * ln P1
        in all). Switching to sparse as the pool falls below the threshold
        avoids that tail. The pool only shrinks, so a block switches from
        dense to sparse at most once and never back.

        Regression-tested in test/test_dispatch_performance.py; benchmarked by
        benchmarks/bench_dispatch.py.
        """
        return vehicle_count <= cls.SPARSE_SEARCH_FACTOR * city_size

    @staticmethod
    def commit_dispatch(trip, vehicle):
        """
        Assign an idle (P1) vehicle to an unassigned trip: the trip starts
        WAITING and the vehicle moves to P2, heading for the pickup.
        """
        trip.update_phase(to_phase=TripPhase.WAITING)
        vehicle.update_phase(trip=trip)

    def _offer(self, trip, vehicle, dispatch_distance):
        """The offer_filter's decision, or ACCEPT when there is no filter."""
        if self.offer_filter is None:
            return OfferDecision.ACCEPT
        return self.offer_filter(trip, vehicle, dispatch_distance)

    def _dispatch_vehicles_default(self, unassigned_trips, city, vehicles):
        dispatchable_vehicles_list = [
            vehicle for vehicle in vehicles if vehicle.phase == VehiclePhase.P1
        ]
        random.shuffle(dispatchable_vehicles_list)
        if self.offline:
            # After the shuffle, which then draws the same random numbers
            dispatchable_vehicles_list = [
                vehicle
                for vehicle in dispatchable_vehicles_list
                if vehicle.index not in self.offline
            ]

        # Dense (location-ring) search while the idle pool is large, then
        # sparse (vehicle-loop) search once it has drained below the threshold
        # (see _use_sparse_search). Trips left once the pool is empty can't be
        # dispatched, so stop there.
        trip_count = len(unassigned_trips)
        i = 0
        if not self._use_sparse_search(len(dispatchable_vehicles_list), city.city_size):
            # Set for O(1) membership testing and removal
            dispatchable_vehicles_set = set(dispatchable_vehicles_list)
            vehicles_at_location = self._build_location_grid(dispatchable_vehicles_list)
            while (
                i < trip_count
                and dispatchable_vehicles_set
                and not self._use_sparse_search(
                    len(dispatchable_vehicles_set), city.city_size
                )
            ):
                self._dispatch_vehicle_dense(
                    unassigned_trips[i],
                    city,
                    vehicles_at_location,
                    dispatchable_vehicles_set,
                    vehicles,
                )
                i += 1
            if i < trip_count:
                # Keep the shuffled order: the sparse search breaks ties by it
                dispatchable_vehicles_list = [
                    vehicle
                    for vehicle in dispatchable_vehicles_list
                    if vehicle in dispatchable_vehicles_set
                ]
        while i < trip_count and dispatchable_vehicles_list:
            self._dispatch_vehicle_sparse(
                unassigned_trips[i], city, dispatchable_vehicles_list, vehicles
            )
            i += 1

    def _dispatch_vehicles_forward_dispatch(self, unassigned_trips, city, vehicles):
        dispatchable_vehicles = [
            vehicle
            for vehicle in vehicles
            if (
                vehicle.phase == VehiclePhase.P1
                or (
                    vehicle.phase == VehiclePhase.P3
                    and vehicle.forward_dispatch_trip_index is None
                )
            )
        ]
        random.shuffle(dispatchable_vehicles)
        vehicles_at_location = self._build_location_grid(dispatchable_vehicles)
        # Set for O(1) membership testing and removal
        dispatchable_vehicles_set = set(dispatchable_vehicles)
        for trip in unassigned_trips:
            if not dispatchable_vehicles_set:
                break
            self._dispatch_vehicle_forward_dispatch(
                trip, city, vehicles_at_location, dispatchable_vehicles_set
            )

    @staticmethod
    def _build_location_grid(dispatchable_vehicles):
        """
        Map each occupied intersection (x, y) to the list of vehicles at that
        point.

        The grid holds the vehicle objects, not their indexes: vehicle.index is
        not a position in the vehicles list once _remove_vehicles has compacted
        it (fleet changes, equilibration), so looking vehicles up by index
        picked the wrong ones.

        Uses a dict keyed by occupied locations only, so building the grid is
        O(number of dispatchable vehicles). The previous implementation
        allocated a full city_size x city_size grid of empty lists every block,
        an O(city_size^2) cost paid regardless of how few vehicles were present.
        """
        grid = {}
        for vehicle in dispatchable_vehicles:
            grid.setdefault((vehicle.location[0], vehicle.location[1]), []).append(
                vehicle
            )
        return grid

    def _dispatch_vehicles_p1_legacy(self, unassigned_trips, city, vehicles):
        dispatchable_vehicles = [
            vehicle for vehicle in vehicles if vehicle.phase == VehiclePhase.P1
        ]
        random.shuffle(dispatchable_vehicles)
        for trip in unassigned_trips:
            self._dispatch_vehicle_p1_legacy(
                trip, city, dispatchable_vehicles, vehicles
            )

    def _dispatch_vehicles_random(self, unassigned_trips, city, vehicles):
        dispatchable_vehicles = [
            vehicle for vehicle in vehicles if vehicle.phase == VehiclePhase.P1
        ]
        random.shuffle(dispatchable_vehicles)
        for trip in unassigned_trips:
            self._dispatch_vehicle_random(dispatchable_vehicles, vehicles)

    def _dispatch_vehicle_sparse(
        self, trip, city, dispatchable_vehicles_list, vehicles
    ):
        """
        Dispatch vehicles by looping over the list of available vehicles.
        Efficient when vehicles are sparse (few vehicles, many intersections).

        This is similar to _dispatch_vehicle_p1_legacy but operates on a list
        that's passed in and modified, allowing multiple trips to be dispatched
        from the same vehicle pool.

        Each candidate is offered the trip (see offer_filter): a declining
        vehicle is skipped and the next-nearest is offered it, a deferring one
        leaves the pool and the trip stays unassigned.
        """
        declined = set()
        while True:
            found = self._find_vehicle_sparse(
                trip, city, dispatchable_vehicles_list, declined
            )
            if found is None:
                return None
            dispatch_vehicle, dispatch_distance = found
            decision = self._offer(trip, dispatch_vehicle, dispatch_distance)
            if decision == OfferDecision.DECLINE:
                declined.add(dispatch_vehicle)
                continue
            dispatchable_vehicles_list.remove(dispatch_vehicle)
            if decision == OfferDecision.DEFER:
                return None
            self.commit_dispatch(trip, dispatch_vehicle)
            return dispatch_vehicle

    @staticmethod
    def _find_vehicle_sparse(trip, city, dispatchable_vehicles_list, declined):
        """
        The nearest vehicle in dispatchable_vehicles_list (excluding those in
        declined) and its dispatch distance, or None. Changes nothing.
        """
        current_minimum = city.city_size * 100  # Very big
        dispatch_vehicle = None

        for vehicle in dispatchable_vehicles_list:
            if vehicle in declined:
                continue
            dispatch_distance = city.dispatch_distance(
                location_from=vehicle.location,
                current_direction=vehicle.direction,
                location_to=trip.origin,
                vehicle_phase=vehicle.phase,
                threshold=current_minimum,
            )
            if 0 < dispatch_distance < current_minimum:
                current_minimum = dispatch_distance
                dispatch_vehicle = vehicle
            # Early termination: can't get closer than distance 1
            if dispatch_distance == 1:
                break

        if dispatch_vehicle is None:
            return None
        return dispatch_vehicle, current_minimum

    # @profile
    def _dispatch_vehicle_dense(
        self, trip, city, vehicles_at_location, dispatchable_vehicles_set, vehicles
    ):
        """
        Dispatch vehicles by looping over increasingly distant locations
        until we find one or more candidate vehicles.
        Efficient when vehicles are dense (many vehicles spread across city).

        Performance optimizations:
        - vehicles_at_location is a dict keyed by occupied (x, y) only
        - dispatchable_vehicles_set is a set for O(1) membership testing
        - Removed redundant phase checks (vehicles already filtered to P1)

        Offers work as in _dispatch_vehicle_sparse.
        """
        declined = set()
        while True:
            found = self._find_vehicle_dense(
                trip,
                city,
                vehicles_at_location,
                dispatchable_vehicles_set,
                vehicles,
                declined,
            )
            if found is None:
                return None
            dispatch_vehicle, dispatch_distance = found
            decision = self._offer(trip, dispatch_vehicle, dispatch_distance)
            if decision == OfferDecision.DECLINE:
                declined.add(dispatch_vehicle)
                continue
            # O(1) set removal instead of O(n) list removal
            dispatchable_vehicles_set.discard(dispatch_vehicle)
            cell = vehicles_at_location.get(
                (dispatch_vehicle.location[0], dispatch_vehicle.location[1])
            )
            if cell:
                cell.remove(dispatch_vehicle)
            if decision == OfferDecision.DEFER:
                return None
            # The trip now changes to WAITING, and the vehicle from P1 to P2
            self.commit_dispatch(trip, dispatch_vehicle)
            return dispatch_vehicle

    @staticmethod
    def _find_vehicle_dense(
        trip, city, vehicles_at_location, dispatchable_vehicles_set, vehicles, declined
    ):
        """
        The nearest dispatchable vehicle (excluding those in declined), chosen
        at random among equally near candidates, and its dispatch distance, or
        None. Changes nothing (other than consuming a random number).
        """
        if len(dispatchable_vehicles_set) == 0:
            return None
        current_minimum = city.city_size * 100  # Very big
        # Assemble a list of candidate vehicles who have
        # the same minimal dispatch_distance
        current_candidates = []
        # Find candidates from the list of dispatchable vehicles. The largest
        # torus distance is city_size (the antipode), so search up to it.
        for distance in range(0, city.city_size + 1):
            for x_offset in range(-distance, distance + 1):
                y_offset = distance - abs(x_offset)
                x = (trip.origin[0] + x_offset) % city.city_size
                y_lower = (trip.origin[1] - y_offset) % city.city_size
                y_upper = (trip.origin[1] + y_offset) % city.city_size
                # set() both deduplicates (y_lower == y_upper when y_offset == 0,
                # or when 2*y_offset == city_size and they wrap together) and
                # fixes the visit order, so dispatch results stay identical to
                # the pre-dict-grid implementation.
                for y in set([y_lower, y_upper]):
                    cell = vehicles_at_location.get((x, y))
                    if not cell:
                        continue
                    for vehicle in cell:
                        # O(1) set membership check instead of O(n) list search
                        if (
                            vehicle not in dispatchable_vehicles_set
                            or vehicle in declined
                        ):
                            continue

                        dispatch_distance = city.dispatch_distance(
                            location_from=vehicle.location,
                            current_direction=vehicle.direction,
                            location_to=trip.origin,
                            vehicle_phase=vehicle.phase,
                        )
                        if 0 < dispatch_distance < current_minimum:
                            current_minimum = dispatch_distance
                            current_candidates = []
                        if 0 < dispatch_distance <= current_minimum:
                            current_candidates.append(vehicle)
            if current_minimum <= distance and len(current_candidates) > 0:
                # We have at least one vehicle as close as "distance"
                break
        if len(current_candidates) == 0:
            return None
        # Select a vehicle at random from the candidate list
        dispatch_vehicle = random.choice(current_candidates)
        return dispatch_vehicle, current_minimum

    def _dispatch_vehicle_forward_dispatch(
        self, trip, city, vehicles_at_location, dispatchable_vehicles_set
    ):
        """
        Dispatch the vehicle with the smallest effective distance to the trip
        origin, searching outwards from the origin ring by ring. Candidates
        are P1 vehicles, whose distance is increased by forward_dispatch_bias,
        and P3 vehicles without a forward trip, whose distance runs via their
        current dropoff (see claude/forward-dispatch-spec.md, F1-F6).

        A vehicle's effective distance is never less than its ring distance
        (for P3, by the triangle inequality), so once the best effective
        distance is no more than the ring distance, no further ring can beat
        it.
        """
        current_minimum = city.city_size * 100  # Very big
        current_candidates = []
        # Rings beyond city_size / 2 wrap round the torus and revisit cells, so
        # score each vehicle once: a duplicate would bias the random tie-break
        scored = set()
        for distance in range(0, city.city_size + 1):
            for x_offset in range(-distance, distance + 1):
                y_offset = distance - abs(x_offset)
                x = (trip.origin[0] + x_offset) % city.city_size
                y_lower = (trip.origin[1] - y_offset) % city.city_size
                y_upper = (trip.origin[1] + y_offset) % city.city_size
                for y in set([y_lower, y_upper]):
                    cell = vehicles_at_location.get((x, y))
                    if not cell:
                        continue
                    for vehicle in cell:
                        if vehicle not in dispatchable_vehicles_set or (
                            vehicle in scored
                        ):
                            continue
                        scored.add(vehicle)
                        dispatch_distance = city.dispatch_distance(
                            location_from=vehicle.location,
                            current_direction=vehicle.direction,
                            location_to=trip.origin,
                            vehicle_phase=vehicle.phase,
                            vehicle_current_trip_destination=vehicle.dropoff_location,
                        )
                        if dispatch_distance <= 0:
                            # A P1 vehicle at the origin (minimum distance 1)
                            continue
                        if vehicle.phase == VehiclePhase.P1:
                            dispatch_distance += self.forward_dispatch_bias
                        if dispatch_distance < current_minimum:
                            current_minimum = dispatch_distance
                            current_candidates = []
                        if dispatch_distance <= current_minimum:
                            current_candidates.append(vehicle)
            if current_minimum <= distance and len(current_candidates) > 0:
                # No vehicle in a further ring can be nearer
                break
        if len(current_candidates) == 0:
            return None
        # Select a vehicle at random from the candidate list
        dispatch_vehicle = random.choice(current_candidates)
        # As a vehicle has been dispatched, the trip phase now changes to WAITING
        trip.update_phase(to_phase=TripPhase.WAITING)
        if dispatch_vehicle.phase == VehiclePhase.P1:
            # The dispatched vehicle changes phase from P1 to P2
            dispatch_vehicle.update_phase(trip=trip)
        else:
            # A P3 vehicle stays P3, and takes the trip after its dropoff
            dispatch_vehicle.assign_forward_dispatch_trip(trip)
            trip.set_forward_dispatch()
        dispatchable_vehicles_set.discard(dispatch_vehicle)
        vehicles_at_location[
            (dispatch_vehicle.location[0], dispatch_vehicle.location[1])
        ].remove(dispatch_vehicle)
        return dispatch_vehicle

    def _dispatch_vehicle_p1_legacy(self, trip, city, dispatchable_vehicles, vehicles):
        """
        Dispatch a vehicle to a trip, using the algorithm self.dispatch_method
        Returns a dispatch vehicle or None.
        The default dispatch_method is:
        - Find the nearest P1 vehicle to a ridehail call at x, y
        - Set that vehicle's phase to P2
        - The list of idle vehicles is already randomized
        The forward_dispatch dispatch_method is:
        - Assign a vehicle from p1_vehicles
        - Check p3_vehicles to see if there are any closer
        The minimum distance checked is 1, not zero, because it takes
        a period to do the assignment. Also, this makes scaling
        more realistic as small city sizes are equivalent to "batching"
        requests across a longer time interval (see notebook, 2021-12-06).
        """
        current_minimum = city.city_size * 100  # Very big
        dispatch_vehicle = None
        if len(dispatchable_vehicles) > 0:
            for vehicle in dispatchable_vehicles:
                dispatch_distance = city.dispatch_distance(
                    vehicle.location,
                    vehicle.direction,
                    trip.origin,
                    vehicle.phase,
                    threshold=current_minimum,
                )
                if 0 < dispatch_distance < current_minimum:
                    current_minimum = dispatch_distance
                    dispatch_vehicle = vehicle
                if dispatch_distance == 1:
                    break
        if dispatch_vehicle:
            # As a vehicle has been dispatched, the trip phase now changes to WAITING
            trip.update_phase(to_phase=TripPhase.WAITING)
            # The dispatched vehicle changes phase from P1 to P2
            dispatch_vehicle.update_phase(trip=trip)
            dispatchable_vehicles.remove(dispatch_vehicle)
        return dispatch_vehicle

    def _dispatch_vehicle_random(self, trip, dispatchable_vehicles, vehicles):
        """
        Dispatch a vehicle by choosing one at random from the list of p1 vehicles.
        """
        if len(dispatchable_vehicles) > 0:
            dispatch_vehicle = random.choice(dispatchable_vehicles)
        else:
            dispatch_vehicle = None
        if dispatch_vehicle:
            # As a vehicle has been dispatched, the trip phase now changes to WAITING
            trip.update_phase(to_phase=TripPhase.WAITING)
            dispatch_vehicle.update_phase(trip=trip)
            dispatchable_vehicles.remove(dispatch_vehicle)
        return dispatch_vehicle

    def _get_dispatchable_vehicles(self, vehicles, dispatch_method):
        dispatchable_vehicles = [
            vehicle
            for vehicle in vehicles
            if (
                vehicle.phase == VehiclePhase.P1
                or (
                    vehicle.phase == VehiclePhase.P3
                    and vehicle.forward_dispatch_trip_index is None
                )
            )
        ]
        return dispatchable_vehicles
