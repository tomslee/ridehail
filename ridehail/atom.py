#!/usr/bin/python3
"""
A ridehail simulation is composed of vehicles and trips. These atoms
are defined here.

Also, some basic types like CircularBuffer
"""

import random
import enum
import numpy as np


class Animation(enum.Enum):
    ALL = "all"
    BAR = "bar"  # plot histograms of phase distributions
    CONSOLE = "console"
    MAP = "map"
    NONE = "none"
    SEQUENCE = "sequence"
    STATS = "stats"
    STATS_BAR = "stats_bar"
    TERMINAL_MAP = "terminal_map"
    TERMINAL_SEQUENCE = "terminal_sequence"
    TERMINAL_STATS = "terminal_stats"
    TEXT = "text"
    WEB_MAP = "web_map"
    WEB_STATS = "web_stats"


class DispatchMethod(enum.Enum):
    DEFAULT = "default"
    P1_LEGACY = "p1_legacy"
    FORWARD_DISPATCH = "forward_dispatch"
    RANDOM = "random"


class Direction(enum.Enum):
    NORTH = [0, 1]
    EAST = [1, 0]
    SOUTH = [0, -1]
    WEST = [-1, 0]


class Equilibration(enum.Enum):
    SUPPLY = "supply"
    PRICE = "price"
    NONE = "none"
    WAIT_FRACTION = "wait_fraction"


class TripDistribution(enum.Enum):
    "No longer used: always UNIFORM"

    UNIFORM = 0


class TripPhase(enum.Enum):
    INACTIVE = 0
    UNASSIGNED = 1
    WAITING = 2
    RIDING = 3
    COMPLETED = 4
    CANCELLED = 5


class VehiclePhase(enum.Enum):
    """
    Insurance commonly uses these phases
    Phase -1: Not used now: would represent a vehicle not in the system
    Phase  0: App is off. Your personal policy covers you.
    Phase  1: App is on, you're waiting for ride request. ...
    Phase  2: Request accepted, and you're en route to pick up a passenger. ...
    Phase  3: You have passengers in the car.
    """

    # INACTIVE = -1
    P1 = 0
    P2 = 1
    P3 = 2


class CityScaleUnit(enum.Enum):
    KM = "km"
    MINUTE = "min"
    HOUR = "hour"
    BLOCK = "block"
    PER_KM = "per_km"
    PER_MINUTE = "per_min"
    PER_HOUR = "per_hour"
    PER_BLOCK = "per_block"


class History(str, enum.Enum):
    """
    A history records the value of some quantity, implemented as a CircularBuffer
    over a defined window. Some (e.g. VEHICLE_COUNT) record the value of a quantity
    (number of vehicles) in every move. Others (eg VEHICLE_TIME_P1) are cumulative.

    Several history buffers are created for each item in this list,
    when a Simulation is initialized.
    - A history_buffer (over smoothing_window) for smoothing plots,
    - A history_results (over results_window) to compute the final results,
    - A history_equilibration (over equilibration_interval) to drive
      equilibration processes.

    Each buffer is updated after each move.
    """

    VEHICLE_COUNT = "Vehicle count"
    VEHICLE_TIME = "Vehicle time"
    VEHICLE_TIME_P1 = "Vehicle P1 time"
    VEHICLE_TIME_P2 = "Vehicle P2 time"
    VEHICLE_TIME_P3 = "Vehicle P3 time"
    TRIP_COUNT = "Trips"
    TRIP_REQUEST_RATE = "Trip request rate"
    TRIP_WAIT_TIME = "Trip wait time"
    TRIP_RIDING_TIME = "Trip riding time"
    TRIP_DISTANCE = "Trip total distance"
    TRIP_PRICE = "Trip price"
    TRIP_COMPLETED_COUNT = "Trips completed (as oppposed to cancelled)"
    TRIP_UNASSIGNED_TIME = "Trip unassigned time"
    TRIP_AWAITING_TIME = "Trip awaiting time"
    TRIP_FORWARD_DISPATCH_COUNT = "Trip requests satisfied by forward dispatch"
    SIM_CONVERGENCE_MAX_RMS_RESIDUAL = "Convergence measure"


class Measure(enum.Enum):
    """
    Measures are numeric values built from history_buffer rolling
    averages and used for animations or writtern output.
    Some involve converting to fractions and others are just
    counts, but each is computed after every move and held as a single
    number in a dict called "measures".
    """

    VEHICLE_MEAN_COUNT = "Vehicles"
    VEHICLE_SUM_TIME = "Vehicle time"
    VEHICLE_FRACTION_P1 = "P1 (available)"
    VEHICLE_FRACTION_P2 = "P2 (en route)"
    VEHICLE_FRACTION_P3 = "P3 (busy)"
    VEHICLE_GROSS_INCOME = "Gross income"
    VEHICLE_NET_INCOME = "Net income"
    VEHICLE_MEAN_SURPLUS = "Surplus income"
    TRIP_SUM_COUNT = "Trips completed"
    TRIP_FORWARD_DISPATCH_FRACTION = "Forward dispatch fraction"
    TRIP_MEAN_REQUEST_RATE = "Request rate (R/Rmax)"
    TRIP_MEAN_WAIT_TIME = "Trip wait time"
    TRIP_MEAN_RIDE_TIME = "Trip distance"
    TRIP_MEAN_WAIT_FRACTION = "Waiting (w/L)"
    TRIP_MEAN_WAIT_FRACTION_TOTAL = "Waiting (w/(w+L))"
    TRIP_DISTANCE_FRACTION = "Trip distance (L/C)"
    TRIP_COMPLETED_FRACTION = "Trips completed (fraction)"
    TRIP_MEAN_PRICE = "Price"
    PLATFORM_MEAN_INCOME = "Platform income"
    SIM_BLOCKS_SIMULATED = "Blocks Simulated"
    SIM_BLOCKS_ANALYZED = "Blocks Analyzed"
    SIM_CONVERGENCE_MAX_RMS_RESIDUAL = "Convergence measure"
    SIM_CONVERGENCE_METRIC = "Convergence metric"
    SIM_IS_CONVERGED = "Convergence criteria satisfied"
    SIM_CHECK_NP3_OVER_RL = "Validation check: NP3/RL"
    SIM_CHECK_NP2_OVER_RW = "Validation check: NP2/RW"
    SIM_CHECK_P1_P2_P3 = "Validation check: P1 + P2 + P3"


class Colours(enum.Enum):
    # SNS theme indexes for the various colours
    # used in graphs and maps
    COLOUR_P1 = "red"
    COLOUR_P2 = "amber"
    COLOUR_P3 = "green"
    COLOUR_WAIT = "blue"
    COLOUR_TRIP_LENGTH = "violet"
    COLOUR_TRIP_START = "blue"
    COLOUR_TRIP_END = "violet"


class Atom:
    """
    Properties and methods that are common to trips and vehicles
    """

    pass


class Trip(Atom):
    """
    A rider places a request and is taken to a destination
    """

    __all__ = [
        "Trip",
    ]

    def __init__(
        self,
        i,
        city,
        min_trip_distance=0,
        max_trip_distance=None,
        per_km_price=None,
        per_min_price=None,
    ):
        self.index = i
        self.city = city
        if max_trip_distance is None or max_trip_distance > city.city_size:
            max_trip_distance = city.city_size
        self.origin = self.set_origin()
        self.destination = self.set_destination(
            self.origin, min_trip_distance, max_trip_distance
        )
        self.distance = self.city.distance(self.origin, self.destination)
        self.phase = TripPhase.INACTIVE
        self.per_km_price = per_km_price
        self.per_min_price = per_min_price
        self.phase_time = {}
        for phase in list(TripPhase):
            self.phase_time[phase] = 0
        self.forward_dispatch = False

    def set_origin(self):
        return self.city.set_location(is_destination=False)

    def set_destination(self, origin, min_trip_distance=0, max_trip_distance=None):
        # Choose a trip_distance:
        while True:
            if max_trip_distance is None or max_trip_distance >= self.city.city_size:
                destination = self.city.set_location(is_destination=True)
            else:
                # Impose a minimum and maximum trip distance
                delta_x = random.randint(min_trip_distance, max_trip_distance)
                delta_y = random.randint(min_trip_distance, max_trip_distance)
                destination = [
                    int(
                        (origin[0] - max_trip_distance / 2 + delta_x)
                        % self.city.city_size
                    ),
                    int(
                        (origin[1] - max_trip_distance / 2 + delta_y)
                        % self.city.city_size
                    ),
                ]
            if destination != origin:
                break
        return destination

    def set_forward_dispatch(self, state=True):
        self.forward_dispatch = state

    def update_phase(self, to_phase=None):
        """
        A trip changes phase from one phase to the next.
        On calling this function, the trip is in phase
        self.phase. It will change to the next phase.
        For now, the "to_phase" argument is used only when trips
        are abandoned, as otherwise the sequence is fixed.
        """
        if not to_phase:
            to_phase = TripPhase((self.phase.value + 1) % len(list(TripPhase)))
        self.phase = to_phase


class Vehicle(Atom):
    """
    A vehicle and its state.
    - A vehicle has a location and direction
    - A vehicle is always in phase P1, P2, or P3.
    - If a vehicle is engaged in a trip, it keeps the trip_index, pickup location
      and dropoff location.
    - If a vehicle is forward-dispatched to another trip while on a current trip,
      then the index of that trip is stored until the current trip is finished.
    - During garbage collection, trip indexes may change even though the trip itself
      is the same.
    """

    __all__ = [
        "Vehicle",
    ]

    def __init__(self, i, city, idle_vehicles_moving=False, location=[0, 0]):
        """
        Create a vehicle at a random location.
        Grid has edge self.city.city_size, in blocks spaced 1 apart
        The location is always expressed in blocks
        """
        self.index = i
        self.city = city
        self.idle_vehicles_moving = idle_vehicles_moving
        self.location = self.city.set_location()
        self.direction = random.choice(list(Direction))
        self.phase = VehiclePhase.P1
        self.trip_index = None
        self.pickup_location = []
        self.dropoff_location = []
        self.forward_dispatch_trip_index = None
        self.forward_dispatch_pickup_location = None
        self.forward_dispatch_dropoff_location = None
        self.utilization = {}
        self.utilization[VehiclePhase.P1] = 0
        self.utilization[VehiclePhase.P2] = 0
        self.utilization[VehiclePhase.P3] = 0
        self.utilization["total"] = 0
        self.forward_dispatches = 0
        self.pickup_countdown = None

    def assign_forward_dispatch_trip(self, forward_dispatch_trip):
        # Vehicle has been forward-dispatched to a trip, meaning it is still
        # on a current trip but will take the new one after that is done.
        # Don't change the phase from P3, but do update the forward_dispatch trip info
        self.forward_dispatch_trip_index = forward_dispatch_trip.index
        self.forward_dispatch_pickup_location = forward_dispatch_trip.origin
        self.forward_dispatch_dropoff_location = forward_dispatch_trip.destination
        self.forward_dispatches += 1

    def update_phase(self, to_phase=None, trip=None, forward_dispatch_trip=None):
        """
        Vehicle phase change
        In the routine, self.phase is the *from* phase
        Currently overloaded as it is called to add forward dispatch trip information,
        even though that is not a phase update.
        """
        if not to_phase:
            # The usual case: move to the next phase in sequence
            to_phase = VehiclePhase((self.phase.value + 1) % len(list(VehiclePhase)))
        if self.phase == VehiclePhase.P1:
            # Vehicle is dispatched to a new trip
            self.trip_index = trip.index
            self.pickup_location = trip.origin
            self.dropoff_location = trip.destination
        elif self.phase == VehiclePhase.P2:
            pass
        elif self.phase == VehiclePhase.P3:
            if not self.forward_dispatch_trip_index:
                # Vehicle has arrived at the destination and the trip is completed.
                # Clear out information about the now-completed trip
                # from the vehicle's state
                to_phase = VehiclePhase.P1
                self.trip_index = None
                self.pickup_location = []
                self.dropoff_location = []
                self.pickup_countdown = None
            elif self.forward_dispatch_trip_index:
                # TODO
                # Vehicle has arrived at the destination and the trip is completed.
                # But the vehicle has a forward_dispatch trip. Set the phase to P2
                # and update the current trip information
                to_phase = VehiclePhase.P2
                self.trip_index = self.forward_dispatch_trip_index
                self.pickup_location = self.forward_dispatch_pickup_location
                self.dropoff_location = self.forward_dispatch_dropoff_location
                self.forward_dispatch_trip_index = None
                self.forward_dispatch_pickup_location = None
                self.forward_dispatch_dropoff_location = None
                self.pickup_countdown = None
        self.phase = to_phase

    def update_direction(self):
        """
        Decide which way to turn, and change phase if needed
        """
        original_direction = self.direction
        if self.phase == VehiclePhase.P2:
            # For a vehicle on the way to pick up a trip, turn towards the
            # pickup point
            new_direction = self._navigate_towards(self.location, self.pickup_location)
        elif self.phase == VehiclePhase.P3:
            new_direction = self._navigate_towards(self.location, self.dropoff_location)
        elif self.phase == VehiclePhase.P1:
            if self.idle_vehicles_moving:
                new_direction = random.choice(list(Direction))
            else:
                new_direction = self.direction
            # No u turns: is_opposite is -1 for opposite,
            # in which case keep on going
            is_opposite = 0
            if new_direction is None:
                is_opposite = -1
            else:
                for i in [0, 1]:
                    is_opposite += new_direction.value[i] * self.direction.value[i]
            if is_opposite == -1:
                new_direction = random.choice(list(Direction))
        if not new_direction:
            # arrived at destination (pickup or dropoff)
            new_direction = original_direction
        self.direction = new_direction

    def update_location(self):
        """
        Update the vehicle's location. Continue driving in the same direction
        """
        old_location = self.location.copy()
        if self.phase == VehiclePhase.P1 and not self.idle_vehicles_moving:
            # this vehicle does not move
            pass
        elif self.phase == VehiclePhase.P2 and self.location == self.pickup_location:
            # the vehicle is at the pickup location:
            # do not move. Usually picking up is handled
            # at the end of the previous block: this
            # code should run only when the vehicle
            # is at the pickup location when called
            pass
        else:
            for i, _ in enumerate(self.location):
                # Handle going off the edge
                self.location[i] = (
                    old_location[i] + self.direction.value[i]
                ) % self.city.city_size

    def _navigate_towards(self, current_location, destination):
        """
        At an intersection turn towards a destination
        (perhaps a pickup, perhaps a dropoff).
        The direction is chosen based on the quadrant
        relative to destination
        Values of zero are on the borders
        """
        delta = [current_location[i] - destination[i] for i in (0, 1)]
        quadrant_length = self.city.city_size / 2
        candidate_direction = []
        # go east or west?
        if (delta[0] > 0 and delta[0] < quadrant_length) or (
            delta[0] < 0 and delta[0] <= -quadrant_length
        ):
            candidate_direction.append(Direction.WEST)
        elif delta[0] == 0:
            pass
        else:
            candidate_direction.append(Direction.EAST)
        # go north or south?
        if (delta[1] > 0 and delta[1] < quadrant_length) or (
            delta[1] < 0 and delta[1] <= -quadrant_length
        ):
            candidate_direction.append(Direction.SOUTH)
        elif delta[1] == 0:
            pass
        else:
            candidate_direction.append(Direction.NORTH)
        if len(candidate_direction) > 0:
            direction = random.choice(candidate_direction)
        else:
            direction = None
        return direction


class City:
    """
    Location-specific stuff
    """

    __all__ = [
        "City",
    ]
    TWO_ZONE_LENGTH = 0.5
    MINUTES_PER_HOUR = 60.0
    HOURS_PER_MINUTE = 1.0 / 60.0

    def __init__(self, city_size, inhomogeneity=0.0, inhomogeneous_destinations=False):
        self.city_size = city_size
        self.inhomogeneity = inhomogeneity
        self.inhomogeneous_destinations = inhomogeneous_destinations
        self.two_zone_size = int(self.city_size * self.TWO_ZONE_LENGTH)

    def set_location(self, is_destination=False):
        """
        Set a location in the city for the beginning or end of a trip
        """
        location = [None, None]
        for i in [0, 1]:
            location[i] = random.randint(0, self.city_size - 1)
        if self.inhomogeneity > 0.0:
            two_zone_selector = random.random()
            if two_zone_selector < self.inhomogeneity:
                if not is_destination or self.inhomogeneous_destinations:
                    # Set some trip locations inside the city core.
                    for i in [0, 1]:
                        location[i] = random.randrange(
                            int((self.city_size - self.two_zone_size) / 2.0),
                            int((self.city_size + self.two_zone_size) / 2.0),
                        )
        return location

    def distance(self, position_0, position_1, threshold=1000):
        """
        Return the distance from position_0 to position_1
        where position_i = (x,y)
        A return of None if there is no distance
        If the distance is bigger than threshold, just return threshold.
        """
        if position_0 is None or position_1 is None:
            return None
        distance = 0
        for i in (0, 1):
            component = abs(position_0[i] - position_1[i])
            component = min(component, self.city_size - component)
            distance += component
            if distance > threshold:
                return threshold
        return distance

    def dispatch_distance(
        self,
        location_from,
        current_direction,
        location_to,
        vehicle_phase=VehiclePhase.P1,
        vehicle_current_trip_destination=None,
        threshold=1000,
    ):
        """
        Return the number of blocks a vehicle at position "location_from" traveling
        in direction "direction" must travel to reach "location_to".
        !!! TODO 2024-07-03: the following paragraph is incorrect: direction changes
        happen right after vehicle dispatch. But I remember introducing this
        method to fix a problem where N.P3 != R.L
        The vehicle is committed to moving in the same direction for
        one move because, in simulation.next_block, update_location
        is called before update_direction.
        If the distance is bigger than threshold, just return threshold.
        """
        dispatch_distance = threshold
        if location_from == location_to:
            return 0
        if vehicle_phase == VehiclePhase.P1:
            dispatch_distance = self.distance(location_from, location_to, threshold)
        elif vehicle_phase == VehiclePhase.P3:
            dispatch_distance = self.distance(
                location_from, vehicle_current_trip_destination, threshold
            ) + self.distance(vehicle_current_trip_destination, location_to, threshold)
            # one_step_position = [
            #     (location_from[i] + direction.value[i]) % self.city_size for i in [0, 1]
            # ]
            # dispatch_distance = 1 + self.distance(
            # one_step_position, location_to, threshold
            # )
        else:
            print(
                (
                    f"Warning: dispatch_distance being evaluated for "
                    f"vehicle in phase {vehicle_phase}"
                )
            )

        return dispatch_distance


class CircularBuffer:
    """
    Class to hold arrays to do smoothing averages
    From
    https://stackoverflow.com/questions/42771110/fastest-way-to-left-cycle-a-numpy-array-like-pop-push-for-a-queue

    Oddly enough, this class pushes new values on to the tail, and drops them
    from the head. Think of it like appending to the tail of a file.
    """

    def __init__(self, maxlen: int):
        # allocate the memory we need ahead of time
        self._max_length: int = maxlen
        self._queue_tail: int = maxlen - 1
        self._rec_queue = np.zeros(maxlen)
        self.sum = np.sum(self._rec_queue)

    def _enqueue(self, new_data: np.array) -> None:
        # move tail pointer forward then insert at the tail of the queue
        # to enforce max length of recording
        self._queue_tail = (self._queue_tail + 1) % self._max_length
        self._rec_queue[self._queue_tail] = new_data

    def _get_head(self) -> int:
        queue_head = (self._queue_tail + 1) % self._max_length
        return self._rec_queue[queue_head]

    def _get_tail(self) -> int:
        return self._rec_queue[self._queue_tail]

    def push(self, new_data: np.array) -> float:
        """
        Add an item to the buffer, and update the sum
        """
        head = self._get_head()
        self._enqueue(new_data)
        tail = self._get_tail()
        self.sum += tail - head

    def __repr__(self):
        return "tail: " + str(self._queue_tail) + "\narray: " + str(self._rec_queue)

    def __str__(self):
        return "tail: " + str(self._queue_tail) + "\narray: " + str(self._rec_queue)
        # return str(self.to_array())
