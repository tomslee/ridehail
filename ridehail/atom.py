#!/usr/bin/python3
"""
A ridehail simulation is composed of drivers and trips. These atoms
are defined here.
"""
from enum import Enum
import random
import logging

logger = logging.getLogger(__name__)


class Direction(Enum):
    NORTH = [0, 1]
    EAST = [1, 0]
    SOUTH = [0, -1]
    WEST = [-1, 0]


class TripPhase(Enum):
    INACTIVE = 0
    UNASSIGNED = 1
    WAITING = 2
    RIDING = 3
    FINISHED = 4


class DriverPhase(Enum):
    """
    Insurance commonly uses these phases
    Phase 0: App is off. Your personal policy covers you.
    Phase 1: App is on, you're waiting for ride request. ...
    Phase 2: Request accepted, and you're en route to pick up a passenger. ...
    Phase 3: You have passengers in the car.
    """
    AVAILABLE = 0
    PICKING_UP = 1
    WITH_RIDER = 2


class Atom():
    """
    Properties and methods that are common to trips and drivers
    """
    pass


class Trip(Atom):
    """
    A rider places a request and is taken to a destination
    """
    def __init__(self, i, city, location=[0, 0]):
        self.index = i
        self.city = city
        self.origin = self.city.set_random_location()
        self.destination = self.city.set_random_location()
        self.distance = 0
        for coord in [0, 1]:
            dist = abs(self.origin[coord] - self.destination[coord])
            dist = min(dist, self.city.city_size - dist)
            self.distance += dist
        # Don't allow the origin and destination to be the same
        while self.destination == self.origin:
            self.destination = self.city.set_random_location()
        self.phase = TripPhase.INACTIVE
        self.phase_time = {}
        for phase in list(TripPhase):
            self.phase_time[phase] = 0

    def phase_change(self, to_phase=None):
        """
        A trip changes phase from one phase to the next.
        On calling this function, the trip is in phase
        self.phase. It will change to the next phase.
        For now, the "to_phase" argument is not used as
        the sequence is fixed.
        """
        from_phase = self.phase
        if not to_phase:
            to_phase = TripPhase((self.phase.value + 1) % len(list(TripPhase)))
        logger.debug(
            (f"Trip {self.index}: {self.phase.name} -> {to_phase.name}"))
        self.phase = to_phase
        logger.debug(
            (f"Trip changes phase: {from_phase.name} -> {self.phase.name}"))


class Driver(Atom):
    """
    A driver and its state

    """
    def __init__(self,
                 i,
                 city,
                 available_drivers_moving=False,
                 location=[0, 0]):
        """
        Create a driver at a random location.
        Grid has edge self.city.city_size, in blocks spaced 1 apart
        """
        self.index = i
        self.city = city
        self.available_drivers_moving = available_drivers_moving
        self.location = self.city.set_random_location()
        self.direction = random.choice(list(Direction))
        self.phase = DriverPhase.AVAILABLE
        self.trip_index = None
        self.pickup = []
        self.dropoff = []

    def phase_change(self, to_phase=None, trip=None):
        """
        Driver phase change
        In the routine, self.phase is the *from* phase
        """
        if not to_phase:
            # The usual case: move to the next phase in sequence
            to_phase = DriverPhase(
                (self.phase.value + 1) % len(list(DriverPhase)))
        # logger.info(f"Phase: {self.phase.name} -> {to_phase.name}")
        if self.phase == DriverPhase.AVAILABLE:
            # Driver is assigned to a new trip
            self.trip_index = trip.index
            self.pickup = trip.origin
            self.dropoff = trip.destination
        elif self.phase == DriverPhase.PICKING_UP:
            pass
        elif self.phase == DriverPhase.WITH_RIDER:
            # Driver has arrived at the destination and the trip
            # is finishing.
            # Clear out information about the now-finished trip
            # from the driver's state
            self.trip_index = None
            self.pickup = []
            self.dropoff = []
        logger.debug((f"Driver changes phase: "
                      f"{self.phase.name} "
                      f"-> {to_phase.name}"))
        self.phase = to_phase

    def update_direction(self):
        """
        Decide which way to turn, and change phase if needed
        """
        original_direction = self.direction
        if self.phase == DriverPhase.PICKING_UP:
            # For a driver on the way to pick up a trip, turn towards the
            # pickup point
            new_direction = self._navigate_towards(self.city, self.location,
                                                   self.pickup)
        elif self.phase == DriverPhase.WITH_RIDER:
            new_direction = self._navigate_towards(self.city, self.location,
                                                   self.dropoff)
        elif self.phase == DriverPhase.AVAILABLE:
            if self.available_drivers_moving:
                new_direction = random.choice(list(Direction))
            else:
                new_direction = self.direction
            # No u turns: is_opposite is -1 for opposite,
            # in which case keep on going
            is_opposite = 0
            for i in [0, 1]:
                is_opposite += (new_direction.value[i] *
                                self.direction.value[i])
            if is_opposite == -1:
                new_direction = original_direction
        if not new_direction:
            # arrived at destination (pickup or dropoff)
            new_direction = original_direction
        self.direction = new_direction
        logger.debug((f"Driver {self.phase.name} turns: "
                      f"{original_direction.name} "
                      f"-> {new_direction.name}"))

    def update_location(self):
        """
        Update the driver's location
        """
        location = self.location
        old_location = self.location.copy()
        if (self.phase == DriverPhase.AVAILABLE
                and not self.available_drivers_moving):
            # this driver does not move
            logger.debug((f"Driver {self.phase.name} "
                          f"not moving: {self.location}"))
        elif (self.phase == DriverPhase.PICKING_UP
              and self.location == self.pickup):
            # the driver is at the pickup location:
            # do not move. Usually this is handled
            # at the end of the previous period: this code
            # should be called only when the driver
            # is at the pickup location when called
            pass
            logger.debug((f"Driver {self.phase.name} "
                          f"at pickup: {self.location}"))
        else:
            for i, _ in enumerate(self.location):
                # Handle going off the edge
                location[i] = ((location[i] + self.direction.value[i]) %
                               self.city.city_size)
            logger.debug((f"Driver {self.index} from "
                          f"({self.location}) "
                          f"to ({location})"))
            self.location = location
            logger.debug((f"Driver {self.phase.name} "
                          f"moves: {old_location} -> {self.location}"))

    def _navigate_towards(self, city, location, destination):
        """
        At an intersection turn towards a destination
        (perhaps a pickup, perhaps a dropoff).
        The direction is chosen based on the quadrant
        relative to destination
        Values of zero are on the borders
        """
        delta = [location[i] - destination[i] for i in (0, 1)]
        quadrant_length = city.city_size / 2
        candidate_direction = []
        # go east or west?
        if (delta[0] > 0 and delta[0] < quadrant_length):
            candidate_direction.append(Direction.WEST)
        elif (delta[0] < 0 and delta[0] <= -quadrant_length):
            candidate_direction.append(Direction.WEST)
        elif delta[0] == 0:
            pass
        else:
            candidate_direction.append(Direction.EAST)
        # go north or south?
        if (delta[1] > 0 and delta[1] < quadrant_length) or (
                delta[1] < 0 and delta[1] <= -quadrant_length):
            candidate_direction.append(Direction.SOUTH)
        elif delta[1] == 0:
            pass
        else:
            candidate_direction.append(Direction.NORTH)
        if len(candidate_direction) > 0:
            direction = random.choice(candidate_direction)
        else:
            direction = None
        logger.debug((f"Driver location = ({location[0]}, {location[1]}), "
                      f"destination = ({destination[0]}, {destination[1]}), "
                      f"direction = {direction}"))
        return direction


class City():
    """
    Location-specific stuff
    """
    def __init__(self, city_size, display_fringe=0.25):
        self.city_size = city_size
        self.display_fringe = display_fringe

    def set_random_location(self):
        location = [None, None]
        for i in [0, 1]:
            location[i] = random.randint(0, self.city_size - 1)
        return location