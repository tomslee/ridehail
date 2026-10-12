"""
A shift: every driver's ledger over a stretch of a simulation, and the
offers that seated cars (the game's player and bots, or the one car of
use_strategy) see. ShiftBase holds what the game (controller.GameController)
and the configured strategy (strategy.StrategyController) share.

Earnings accrue while the rider is on board, offer / trip_blocks per block,
with any rounding remainder credited at drop-off. Accruing per block treats
trips that straddle the start or end of the shift the same way for everyone.
"""

from dataclasses import dataclass, field

from ridehail.atom import TripPhase, VehiclePhase
from ridehail.dispatch import OfferDecision
from ridehail.game.params import HST_RATE, MINUTES_PER_HOUR


@dataclass
class Ledger:
    """One driver's shift so far."""

    earnings: float = 0.0
    km: float = 0.0
    minutes: dict = field(default_factory=lambda: {"P1": 0.0, "P2": 0.0, "P3": 0.0})
    offers: int = 0
    accepts: int = 0
    trips_completed: int = 0
    # What riders probably paid for this driver's trips (City fees and HST
    # included), accrued alongside earnings
    rider_fares: float = 0.0

    def summary(self, params):
        shift_minutes = sum(self.minutes.values())
        costs = self.km * params.ops_cost_per_km
        net = self.earnings - costs
        engaged = self.minutes["P2"] + self.minutes["P3"]
        hours = shift_minutes / MINUTES_PER_HOUR if shift_minutes else 0.0
        return {
            "earnings": round(self.earnings, 2),
            "costs": round(costs, 2),
            "net": round(net, 2),
            "km": round(self.km, 1),
            "minutes": dict(self.minutes),
            "net_per_hour": round(net / hours, 2) if hours else 0.0,
            "gross_per_engaged_hour": (
                round(self.earnings / (engaged / MINUTES_PER_HOUR), 2)
                if engaged
                else 0.0
            ),
            "offers": self.offers,
            "accepts": self.accepts,
            "acceptance_rate": (
                round(self.accepts / self.offers, 3) if self.offers else None
            ),
            "trips_completed": self.trips_completed,
            "rider_fares": round(self.rider_fares, 2),
            "rider_hst": round(self.rider_fares * HST_RATE / (1 + HST_RATE), 2),
            # The driver's share of what riders paid before HST
            "driver_share": (
                round(self.earnings / (self.rider_fares / (1 + HST_RATE)), 3)
                if self.rider_fares > 0
                else None
            ),
        }


class ShiftBase:
    """
    Every driver's ledger for one shift of a RideHailSimulation. Subclasses
    install an offer filter on the dispatcher, call start_shift() when the
    shift begins and after_block() after each block. The pricing object
    gives offer_price(trip, dispatch_distance) and rider_fare(trip).
    """

    def __init__(self, sim, params, pricing, shift_blocks):
        self.sim = sim
        self.params = params
        self.pricing = pricing
        self.shift_blocks = shift_blocks
        # Every driver is measured from their first idle moment in the shift,
        # so that everyone is compared on the same footing as a seated car,
        # which logs on idle. A fleet car on a trip when the shift starts
        # joins when that trip ends (the trip itself does not count). See
        # after_block().
        self.on_shift = set()
        self._pre_shift_trip = {}
        # vehicle index -> Ledger
        self.ledgers = {v.index: Ledger() for v in sim.vehicles}
        # (vehicle index, trip id) -> the offer that driver took the trip at
        self.agreed = {}
        # (vehicle index, trip id) -> earnings accrued so far on that trip
        self.accrued = {}
        # (vehicle index, trip id) -> rider fare accrued so far, likewise
        self.accrued_fare = {}
        # trip id -> Trip, for trips with accrued earnings. The simulation's
        # garbage collection can drop a trip from sim.trips in the very block
        # it completes, so the ledger keeps its own reference.
        self._accruing_trips = {}
        # trip id -> indexes of the seated cars who declined it
        self.declined_by = {}
        self.active = False
        self.shift_block = 0
        self.shift_over = False
        # vehicle index -> location after the previous block, for the km count
        self._prev_locations = None
        self._city_core = sim.city.core_bounds()

    def zone(self, location):
        low, high = self._city_core
        if all(low <= c < high for c in location):
            return "core"
        return "outskirts"

    def start_shift(self):
        """Start the shift: from now on, ledgers count."""
        self._pre_shift_trip = {
            v.index: v.trip_index for v in self.sim.vehicles if v.trip_index is not None
        }
        self.on_shift = {
            v.index for v in self.sim.vehicles if v.index not in self._pre_shift_trip
        }
        self.active = True
        self._prev_locations = {v.index: list(v.location) for v in self.sim.vehicles}

    def _fleet_accepts(self, trip, index, dispatch_distance):
        """An ordinary fleet car takes every trip, at its offer price."""
        self.agreed[(index, trip.index)] = self.pricing.offer_price(
            trip, dispatch_distance
        )
        return OfferDecision.ACCEPT

    def _decline(self, trip, index):
        self.declined_by.setdefault(trip.index, set()).add(index)

    def after_block(self):
        """Update every driver's ledger for the block just simulated."""
        if not self.active or self.shift_over:
            return
        p = self.params
        trips = self.sim.trips
        prev = self._prev_locations
        for vehicle in self.sim.vehicles:
            index = vehicle.index
            if index not in self.on_shift:
                if vehicle.trip_index == self._pre_shift_trip.get(index):
                    continue
                # Its pre-shift trip has ended: this car's shift starts now
                self.on_shift.add(index)
            ledger = self.ledgers[index]
            ledger.minutes[vehicle.phase.name] += p.minutes_per_block
            if prev is not None and prev[index] != vehicle.location:
                ledger.km += p.km_per_block
            if vehicle.phase == VehiclePhase.P3:
                trip = trips.get(vehicle.trip_index)
                if trip is not None:
                    key = (index, trip.index)
                    increment = self._agreed_offer(key, trip) / trip.distance
                    self.accrued[key] = self.accrued.get(key, 0.0) + increment
                    self._accruing_trips[trip.index] = trip
                    ledger.earnings += increment
                    fare = self.pricing.rider_fare(trip) / trip.distance
                    self.accrued_fare[key] = self.accrued_fare.get(key, 0.0) + fare
                    ledger.rider_fares += fare
        # Trips completed this block: credit any remainder of the offer
        for key in list(self.accrued):
            index, trip_id = key
            trip = self._accruing_trips[trip_id]
            if trip.phase in (TripPhase.WAITING, TripPhase.RIDING):
                continue
            if trip.phase == TripPhase.COMPLETED:
                offer = self._agreed_offer(key, trip)
                self.ledgers[index].earnings += offer - self.accrued[key]
                self.ledgers[index].rider_fares += (
                    self.pricing.rider_fare(trip) - self.accrued_fare[key]
                )
                self.ledgers[index].trips_completed += 1
            del self.accrued[key]
            self.accrued_fare.pop(key, None)
            self.agreed.pop(key, None)
            self._accruing_trips.pop(trip_id, None)
        self._prev_locations = {v.index: list(v.location) for v in self.sim.vehicles}
        self.shift_block += 1
        if self.shift_block >= self.shift_blocks:
            self.shift_over = True

    def _agreed_offer(self, key, trip):
        """
        The offer a driver took a trip at. Every dispatch goes through the
        offer filter, so it is recorded; the fallback (a zero-length pickup)
        is only a guard.
        """
        if key not in self.agreed:
            self.agreed[key] = self.pricing.offer_price(trip, 0)
        return self.agreed[key]

    def shift_minutes(self):
        return self.shift_block * self.params.minutes_per_block
