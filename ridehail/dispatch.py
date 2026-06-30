import logging
import random
import sys
from ridehail.atom import DispatchMethod, VehiclePhase, TripPhase


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

    @staticmethod
    def _use_sparse_search(trip_count, vehicle_count, city_size):
        """
        ADAPTIVE DISPATCH: choose the search strategy by comparing the two
        strategies' dominant cost estimates. Returns True for the sparse
        (vehicle-loop) search, False for the dense (location-ring) search.

        Sparse (vehicle-loop): each trip scans the P1 list, so the cost is
        O(trips * P1).
        Dense (location-ring): O(P1) to build the occupancy grid, then each
        trip ring-searches outward to the nearest vehicle, costing roughly
        city_size^2 / P1 cells -> O(P1 + trips * city_size^2 / P1).

        The dense per-trip term (trips * city_size^2 / P1) is what the old rule
        (trips*P1 vs 0.5*city_size^2) omitted. When P1 is small but the
        unassigned-trip backlog is large -- a deeply undersupplied run -- that
        rule flipped to dense and ring-searched a near-empty grid thousands of
        times per block, which was the source of the reported slowdown.
        Including the term reduces the choice to roughly "sparse when
        P1 < city_size", which tracks the measured crossover.

        This crossover is regression-tested directly in
        test/test_dispatch_performance.py; keep it a pure function of the three
        scalars so it stays testable. See also utils/benchmark_dispatch.py.
        """
        if vehicle_count <= 0:
            return True  # nothing to dispatch; avoid grid build and /0
        sparse_cost_estimate = trip_count * vehicle_count
        dense_cost_estimate = (
            vehicle_count + trip_count * city_size**2 / vehicle_count
        )
        return sparse_cost_estimate <= dense_cost_estimate

    def _dispatch_vehicles_default(self, unassigned_trips, city, vehicles):
        dispatchable_vehicles_list = [
            vehicle for vehicle in vehicles if vehicle.phase == VehiclePhase.P1
        ]
        random.shuffle(dispatchable_vehicles_list)

        if self._use_sparse_search(
            len(unassigned_trips), len(dispatchable_vehicles_list), city.city_size
        ):
            # Use vehicle-loop algorithm (like p1_legacy but with early termination)
            for trip in unassigned_trips:
                self._dispatch_vehicle_sparse(
                    trip, city, dispatchable_vehicles_list, vehicles
                )
        else:
            # Use location-ring algorithm.
            # Convert to set for O(1) membership testing and removal
            dispatchable_vehicles_set = set(dispatchable_vehicles_list)
            vehicles_at_location = self._build_location_grid(dispatchable_vehicles_list)
            for trip in unassigned_trips:
                self._dispatch_vehicle_dense(
                    trip,
                    city,
                    vehicles_at_location,
                    dispatchable_vehicles_set,
                    vehicles,
                )

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
        for trip in unassigned_trips:
            self._dispatch_vehicle_forward_dispatch(
                trip, city, vehicles_at_location, dispatchable_vehicles, vehicles
            )

    @staticmethod
    def _build_location_grid(dispatchable_vehicles):
        """
        Map each occupied intersection (x, y) to the list of vehicle indexes at
        that point.

        Uses a dict keyed by occupied locations only, so building the grid is
        O(number of dispatchable vehicles). The previous implementation
        allocated a full city_size x city_size grid of empty lists every block,
        an O(city_size^2) cost paid regardless of how few vehicles were present.
        """
        grid = {}
        for vehicle in dispatchable_vehicles:
            grid.setdefault(
                (vehicle.location[0], vehicle.location[1]), []
            ).append(vehicle.index)
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
        """
        if len(dispatchable_vehicles_list) == 0:
            return None

        current_minimum = city.city_size * 100  # Very big
        dispatch_vehicle = None

        for vehicle in dispatchable_vehicles_list:
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

        if dispatch_vehicle:
            # Update trip and vehicle phases
            trip.update_phase(to_phase=TripPhase.WAITING)
            dispatch_vehicle.update_phase(trip=trip)
            dispatchable_vehicles_list.remove(dispatch_vehicle)

        return dispatch_vehicle

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
        """
        if len(dispatchable_vehicles_set) == 0:
            return None
        current_minimum = city.city_size * 100  # Very big
        dispatch_vehicle = None
        # Assemble a list of candidate vehicle indexes who have
        # the same minimal dispatch_distance
        current_candidate_vehicle_indexes = []
        # Find candidates from the list of dispatchable vehicles
        for distance in range(0, city.city_size):
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
                    for vehicle_index in cell:
                        try:
                            vehicle = vehicles[vehicle_index]
                        except IndexError:
                            continue
                        # O(1) set membership check instead of O(n) list search
                        if vehicle not in dispatchable_vehicles_set:
                            continue

                        dispatch_distance = city.dispatch_distance(
                            location_from=vehicle.location,
                            current_direction=vehicle.direction,
                            location_to=trip.origin,
                            vehicle_phase=vehicle.phase,
                        )
                        if 0 < dispatch_distance < current_minimum:
                            current_minimum = dispatch_distance
                            current_candidate_vehicle_indexes = []
                        if 0 < dispatch_distance <= current_minimum:
                            current_candidate_vehicle_indexes.append(vehicle_index)
            if (
                current_minimum <= distance
                and len(current_candidate_vehicle_indexes) > 0
            ):
                # We have at least one vehicle as close as "distance"
                # print(f"Dispatch distance={current_minimum}")
                break
        # Select a vehicle at random from the candidate list and return it
        if len(current_candidate_vehicle_indexes) > 0:
            dispatch_vehicle = vehicles[
                random.choice(current_candidate_vehicle_indexes)
            ]
            # As a vehicle has been dispatched, the trip phase now changes to WAITING
            trip.update_phase(to_phase=TripPhase.WAITING)
            # The dispatched vehicle changes phase from P1 to P2
            dispatch_vehicle.update_phase(trip=trip)
            # O(1) set removal instead of O(n) list removal
            dispatchable_vehicles_set.discard(dispatch_vehicle)
            cell = vehicles_at_location.get(
                (dispatch_vehicle.location[0], dispatch_vehicle.location[1])
            )
            if cell:
                cell.remove(dispatch_vehicle.index)
        return dispatch_vehicle

    def _dispatch_vehicle_forward_dispatch(
        self, trip, city, vehicles_at_location, dispatchable_vehicles, vehicles
    ):
        """
        Dispatch vehicles by looping over increasingly distance locations
        until we find one or more candidate vehicles.
        """
        if len(dispatchable_vehicles) == 0:
            return None
        current_minimum = city.city_size * 100  # Very big
        dispatch_vehicle = None
        # Assemble a list of candidate vehicle indexes who have
        # the same minimal dispatch_distance
        current_candidate_vehicle_indexes = []
        # Find candidates from the list of dispatchable vehicles
        for distance in range(0, city.city_size):
            for x_offset in range(-distance, distance + 1):
                y_offset = distance - abs(x_offset)
                x = (trip.origin[0] + x_offset) % city.city_size
                y_lower = (trip.origin[1] - y_offset) % city.city_size
                y_upper = (trip.origin[1] + y_offset) % city.city_size
                # set() deduplicates and fixes visit order so dispatch results
                # stay identical to the pre-dict-grid implementation.
                for y in set([y_lower, y_upper]):
                    cell = vehicles_at_location.get((x, y))
                    if not cell:
                        continue
                    for vehicle_index in cell:
                        try:
                            vehicle = vehicles[vehicle_index]
                        except IndexError:
                            continue
                        dispatch_distance = city.dispatch_distance(
                            location_from=vehicle.location,
                            current_direction=vehicle.direction,
                            location_to=trip.origin,
                            vehicle_phase=vehicle.phase,
                            vehicle_current_trip_destination=vehicle.dropoff_location,
                        )
                        if vehicle.phase == VehiclePhase.P1:
                            dispatch_distance += self.forward_dispatch_bias
                        if (
                            0 < dispatch_distance < current_minimum
                        ) and vehicle in dispatchable_vehicles:
                            current_minimum = dispatch_distance
                            current_candidate_vehicle_indexes = []
                        if 0 < dispatch_distance <= current_minimum:
                            current_candidate_vehicle_indexes.append(vehicle_index)
            if (
                current_minimum <= distance
                and len(current_candidate_vehicle_indexes) > 0
            ):
                # We have at least one vehicle as close as "distance"
                break
        # Select a vehicle at random from the candidate list and return it
        if len(current_candidate_vehicle_indexes) > 0:
            dispatch_vehicle = vehicles[
                random.choice(current_candidate_vehicle_indexes)
            ]
            # As a vehicle has been dispatched, the trip phase now changes to WAITING
            trip.update_phase(to_phase=TripPhase.WAITING)
            # The dispatched vehicle changes phase from P1 to P2
            if dispatch_vehicle.phase == VehiclePhase.P1:
                dispatch_vehicle.update_phase(trip=trip)
            elif dispatch_vehicle.phase == VehiclePhase.P3:
                dispatch_vehicle.assign_forward_dispatch_trip(trip)
                trip.set_forward_dispatch()
            try:
                dispatchable_vehicles.remove(dispatch_vehicle)
                cell = vehicles_at_location.get(
                    (dispatch_vehicle.location[0], dispatch_vehicle.location[1])
                )
                if cell:
                    cell.remove(dispatch_vehicle.index)
            except ValueError:
                logging.warn("dispatched vehicle not in list(s)")
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
