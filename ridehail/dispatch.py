import logging
import numpy as np
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

    def _dispatch_vehicles_default(self, unassigned_trips, city, vehicles):
        dispatchable_vehicles_list = [
            vehicle for vehicle in vehicles if vehicle.phase == VehiclePhase.P1
        ]
        random.shuffle(dispatchable_vehicles_list)

        # ADAPTIVE DISPATCH: Choose algorithm based on vehicle count
        # Heuristic: Use vehicle-loop when vehicles are sparse, location-loop when dense
        #
        # Rationale: Dense algorithm loops over O(city_size²) intersection checks in worst case.
        # Sparse algorithm loops over O(num_vehicles) distance calculations.
        # Crossover point is approximately when checking all vehicles is cheaper than
        # checking intersection grids. Use threshold of city_size * 0.5 as practical cutoff.
        vehicle_count = len(dispatchable_vehicles_list)
        vehicle_density = vehicle_count / (city.city_size**2)
        threshold = 0.9

        if vehicle_density < threshold:  # Sparse: fewer vehicles than threshold
            # Use vehicle-loop algorithm (like p1_legacy but with early termination)
            for trip in unassigned_trips:
                self._dispatch_vehicle_sparse(
                    trip, city, dispatchable_vehicles_list, vehicles
                )
        else:
            # Use location-loop algorithm (original implementation)
            # Convert to set for O(1) membership testing and removal
            dispatchable_vehicles_set = set(dispatchable_vehicles_list)

            vehicles_at_location = np.array(
                np.empty(shape=(city.city_size, city.city_size), dtype=object)
            )
            for i in range(city.city_size):
                for j in range(city.city_size):
                    vehicles_at_location[i][j] = []
            # At each intersection, assign a list of vehicle indexes for the vehicles
            # at that point.
            for vehicle in dispatchable_vehicles_list:
                # No need for phase check - already filtered to P1 only
                vehicles_at_location[vehicle.location[0]][vehicle.location[1]].append(
                    vehicle.index
                )
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
        vehicles_at_location = np.array(
            np.empty(shape=(city.city_size, city.city_size), dtype=object)
        )
        for i in range(city.city_size):
            for j in range(city.city_size):
                vehicles_at_location[i][j] = []
        # At each intersection, assign a list of vehicle indexes for the vehicles
        # at that point.
        for vehicle in dispatchable_vehicles:
            vehicles_at_location[vehicle.location[0]][vehicle.location[1]].append(
                vehicle.index
            )
        for trip in unassigned_trips:
            self._dispatch_vehicle_forward_dispatch(
                trip, city, vehicles_at_location, dispatchable_vehicles, vehicles
            )

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
                for y in set([y_lower, y_upper]):
                    for vehicle_index in vehicles_at_location[x][y]:
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
            vehicles_at_location[dispatch_vehicle.location[0]][
                dispatch_vehicle.location[1]
            ].remove(dispatch_vehicle.index)
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
                for y in set([y_lower, y_upper]):
                    for vehicle_index in vehicles_at_location[x][y]:
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
                vehicles_at_location[dispatch_vehicle.location[0]][
                    dispatch_vehicle.location[1]
                ].remove(dispatch_vehicle.index)
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
