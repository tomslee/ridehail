"""
The shift itself: GameController runs one shift of a RideHailSimulation,
making offers to the player and the bots through the dispatcher's offer
filter and keeping every driver's ledger.

Earnings accrue while the rider is on board, offer / trip_blocks per block,
with any rounding remainder credited at drop-off. Accruing per block treats
trips that straddle the start or end of the shift the same way for everyone.
"""

import random
from dataclasses import dataclass, field

from ridehail.atom import TripPhase, VehiclePhase
from ridehail.dispatch import Dispatch, OfferDecision
from ridehail.game.bots import BOTS
from ridehail.game.params import HST_RATE, MINUTES_PER_HOUR, GameParams
from ridehail.game.pricing import OfferPricing
from ridehail.game.report import shift_results


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


class GameController:
    """
    Wraps a RideHailSimulation for one shift. Call warm_up() once, then for
    each block: before_block(); sim.next_block(); after_block(). When
    after_block() leaves a pending offer, call resolve_offer() before the next
    block (an unresolved offer is treated as a timeout). step() does all of
    this for headless play with a callable decider.
    """

    def __init__(self, sim, params=None, seed=1):
        self.sim = sim
        self.params = params or GameParams()
        self.rng = random.Random(seed)
        # Drivers are identified by vehicle.index, which is fixed for the
        # life of a vehicle, not by position in sim.vehicles, which changes if
        # the fleet does (Simulation._remove_vehicles). See position().
        vehicles = sim.vehicles
        seats = self.rng.sample(range(len(vehicles)), 1 + len(BOTS))
        self.player_vehicle = vehicles[seats[0]]
        self.player = self.player_vehicle.index
        self.bot_vehicles = [vehicles[seat] for seat in seats[1:]]
        self.bots = {v.index: bot for v, bot in zip(self.bot_vehicles, BOTS)}
        # Every driver is measured from their first idle moment in the shift,
        # so that everyone is compared on the same footing as the player, who
        # logs on idle. A fleet car on a trip when the shift starts joins when
        # that trip ends (the trip itself does not count). See after_block().
        self.on_shift = set()
        self._pre_shift_trip = {}
        # vehicle index -> Ledger
        self.ledgers = {v.index: Ledger() for v in vehicles}
        self.pricing = OfferPricing(self.params, self.rng)
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
        self.offer_log = []
        # trip id -> player's log entry, for trips the player declined
        self._declined_log = {}
        # trip id -> indexes of the player and bots who declined it
        self.declined_by = {}
        self.pending = None
        self.active = False
        self.shift_block = 0
        self.shift_over = False
        self.timeout_until = None
        self._recent_decisions = []
        # vehicle index -> location after the previous block, for the km count
        self._prev_locations = None
        # ((phase name, trip id), leg length in blocks) for the player's
        # current pickup or trip, for the HUD's progress bar
        self._leg = None
        self._city_core = self._core_range()
        sim.dispatcher.offer_filter = self._offer_filter

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _core_range(self):
        return self.sim.city.core_bounds()

    def position(self, vehicle):
        """
        A vehicle's position in sim.vehicles, which is how the web lab's
        frames list vehicles. The game's fleet is fixed, so this is the
        vehicle's index; the search is only a guard.
        """
        vehicles = self.sim.vehicles
        if vehicle.index < len(vehicles) and vehicles[vehicle.index] is vehicle:
            return vehicle.index
        return vehicles.index(vehicle)

    def warm_up(self):
        """
        Run the market to a steady state before the shift starts. The player
        and the bots are logged off (out of the dispatch pool), so each of
        them logs on idle.
        """
        dispatcher = self.sim.dispatcher
        dispatcher.offline = frozenset([self.player, *self.bots])
        for _ in range(self.params.warmup_blocks):
            self.sim.next_block()
        dispatcher.offline = frozenset()
        self._pre_shift_trip = {
            v.index: v.trip_index for v in self.sim.vehicles if v.trip_index is not None
        }
        self.on_shift = {
            v.index for v in self.sim.vehicles if v.index not in self._pre_shift_trip
        }
        self.active = True
        self._prev_locations = {v.index: list(v.location) for v in self.sim.vehicles}

    # ------------------------------------------------------------------
    # Offers
    # ------------------------------------------------------------------

    def zone(self, location):
        low, high = self._city_core
        if all(low <= c < high for c in location):
            return "core"
        return "outskirts"

    def describe_offer(self, trip, vehicle, dispatch_distance):
        p = self.params
        rate_card = self.pricing.price(trip)[0]
        offer = self.pricing.offer_price(trip, dispatch_distance)
        pickup_minutes = dispatch_distance * p.minutes_per_block
        trip_minutes = trip.distance * p.minutes_per_block
        pickup_km = dispatch_distance * p.km_per_block
        trip_km = trip.distance * p.km_per_block
        return {
            "trip_id": trip.index,
            "block": self.shift_block,
            "offer": offer,
            "rate_card": rate_card,
            "vs_rate_card": round(offer / rate_card - 1.0, 3),
            "rider_fare": self.pricing.rider_fare(trip),
            "pickup_minutes": pickup_minutes,
            "pickup_km": pickup_km,
            "trip_minutes": trip_minutes,
            "trip_km": trip_km,
            "per_min": round(offer / (pickup_minutes + trip_minutes), 3),
            "per_km": round(offer / (pickup_km + trip_km), 3),
            "vehicle_location": list(vehicle.location),
            "pickup": list(trip.origin),
            "dropoff": list(trip.destination),
            "dropoff_zone": self.zone(trip.destination),
        }

    def _offer_filter(self, trip, vehicle, dispatch_distance):
        """Dispatch.offer_filter: the fast path is any ordinary fleet car."""
        index = vehicle.index
        is_player = index == self.player
        if not is_player and index not in self.bots:
            if trip.index in self._declined_log:
                self._note_taken(trip, dispatch_distance)
            self.agreed[(index, trip.index)] = self.pricing.offer_price(
                trip, dispatch_distance
            )
            return OfferDecision.ACCEPT
        if not self.active or self.shift_over:
            # Before and after the shift, the player and bots are logged off
            return OfferDecision.DECLINE
        if index in self.declined_by.get(trip.index, ()):
            return OfferDecision.DECLINE
        if is_player:
            max_wait = self.sim.max_wait_time
            if max_wait and trip.phase_time[TripPhase.UNASSIGNED] >= max_wait:
                # This rider cancels at the end of the block: don't offer
                return OfferDecision.DECLINE
            if self.timeout_until is not None and self.shift_block < self.timeout_until:
                return OfferDecision.DECLINE
            self.pending = self.describe_offer(trip, vehicle, dispatch_distance)
            return OfferDecision.DEFER
        offer = self.describe_offer(trip, vehicle, dispatch_distance)
        ledger = self.ledgers[index]
        ledger.offers += 1
        if self.bots[index].accepts(offer):
            ledger.accepts += 1
            self.agreed[(index, trip.index)] = offer["offer"]
            self._note_taken(trip, dispatch_distance)
            return OfferDecision.ACCEPT
        # A bot plays by the player's rules: one offer a block, and a declined
        # trip waits for the next block. DEFER takes the bot out of the pool
        # for the rest of the block and leaves the trip unassigned, as the
        # player's deferred offer does. (With DECLINE, a bot in a backlog
        # could browse dozens of offers in one block; claude/game-mode.md
        # 10.5.)
        self._decline(trip, index)
        return OfferDecision.DEFER

    def _decline(self, trip, index):
        self.declined_by.setdefault(trip.index, set()).add(index)

    def _note_taken(self, trip, dispatch_distance):
        """Record who took a trip the player declined, for the offer log."""
        entry = self._declined_log.pop(trip.index, None)
        if entry is not None:
            entry["taken_after_minutes"] = self.shift_block - entry["block"]
            entry["taken_pickup_minutes"] = (
                dispatch_distance * self.params.minutes_per_block
            )
            entry["rider_extra_wait"] = (
                entry["taken_after_minutes"]
                + entry["taken_pickup_minutes"]
                - entry["pickup_minutes"]
            )

    def resolve_offer(self, accept, timed_out=False):
        """
        Apply the player's decision on the pending offer, between blocks.
        Returns the logged offer entry (or None if nothing was pending).
        """
        entry = self.pending
        if entry is None:
            return None
        self.pending = None
        trip = self.sim.trips.get(entry["trip_id"])
        vehicle = self.player_vehicle
        ledger = self.ledgers[self.player]
        ledger.offers += 1
        valid = (
            trip is not None
            and trip.phase == TripPhase.UNASSIGNED
            and vehicle.phase == VehiclePhase.P1
        )
        if accept and valid:
            ledger.accepts += 1
            entry["decision"] = "accept"
            self.agreed[(self.player, trip.index)] = entry["offer"]
            Dispatch.commit_dispatch(trip, vehicle)
            # The car chose its next direction at the end of the block, while
            # still idle: point it at the pickup instead.
            vehicle.update_direction()
        else:
            entry["decision"] = "timeout" if timed_out else "decline"
            if trip is not None:
                self._decline(trip, self.player)
                self._declined_log[trip.index] = entry
        self.offer_log.append(entry)
        self._apply_acceptance_rule(entry["decision"] == "accept")
        return entry

    def _apply_acceptance_rule(self, accepted):
        rule = self.params.acceptance_rule
        if not rule:
            return
        self._recent_decisions.append(accepted)
        window = self._recent_decisions[-rule["window"] :]
        if len(window) >= rule["window"] and sum(window) < rule["min_accepts"]:
            self.timeout_until = self.shift_block + rule["timeout_blocks"]
            self._recent_decisions = []

    # ------------------------------------------------------------------
    # The block loop
    # ------------------------------------------------------------------

    def before_block(self):
        if self.pending is not None:
            self.resolve_offer(False, timed_out=True)

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
        if self.shift_block >= p.shift_blocks:
            self.shift_over = True
            self.pending = None

    def _agreed_offer(self, key, trip):
        """
        The offer a driver took a trip at. Every dispatch goes through
        _offer_filter, so it is recorded; the fallback (a zero-length pickup)
        is only a guard.
        """
        if key not in self.agreed:
            self.agreed[key] = self.pricing.offer_price(trip, 0)
        return self.agreed[key]

    def step(self, decider=None):
        """
        Headless play: one block, with decider(offer_dict) -> bool answering
        any offer to the player immediately. Returns the resolved offer entry,
        if there was one.
        """
        self.before_block()
        self.sim.next_block()
        self.after_block()
        if self.pending is not None:
            accept = decider(self.pending) if decider else True
            return self.resolve_offer(bool(accept))
        return None

    # ------------------------------------------------------------------
    # Reporting
    # ------------------------------------------------------------------

    def shift_minutes(self):
        return self.shift_block * self.params.minutes_per_block

    def leg_progress(self):
        """
        How far through the current pickup (P2) or trip (P3) the player is,
        from 0 to 1, or None while idle. A pickup's length is the distance
        when it is first seen (the car is where it was dispatched); a trip's
        is the trip's own distance.
        """
        vehicle = self.player_vehicle
        if vehicle.phase == VehiclePhase.P2:
            target = vehicle.pickup_location
        elif vehicle.phase == VehiclePhase.P3:
            target = vehicle.dropoff_location
        else:
            self._leg = None
            return None
        remaining = self.sim.city.distance(vehicle.location, target)
        if remaining is None:
            return None
        key = (vehicle.phase.name, vehicle.trip_index)
        if self._leg is None or self._leg[0] != key:
            total = remaining
            if vehicle.phase == VehiclePhase.P3:
                trip = self.sim.trips.get(vehicle.trip_index)
                if trip is not None:
                    total = max(trip.distance, remaining)
            self._leg = (key, max(total, 1))
        return round(min(1.0, max(0.0, 1.0 - remaining / self._leg[1])), 3)

    def frame_payload(self):
        """Small per-frame dict for the HUD, the map overlay and the offer card."""
        p = self.params
        player = self.player_vehicle
        summary = self.ledgers[self.player].summary(p)
        timeout_left = 0
        if self.timeout_until is not None:
            timeout_left = max(0, self.timeout_until - self.shift_block)
        return {
            "shift_block": self.shift_block,
            "shift_blocks": p.shift_blocks,
            # Positions in the frame's vehicle list (see position())
            "player": self.position(player),
            "bots": {
                str(self.position(v)): self.bots[v.index].name
                for v in self.bot_vehicles
            },
            "player_phase": player.phase.name,
            "leg_progress": self.leg_progress(),
            "player_pickup": list(player.pickup_location) or None,
            "player_dropoff": list(player.dropoff_location) or None,
            "earnings": summary["earnings"],
            "costs": summary["costs"],
            "net": summary["net"],
            "net_per_hour": summary["net_per_hour"],
            "offers": summary["offers"],
            "accepts": summary["accepts"],
            "acceptance_rate": summary["acceptance_rate"],
            "timeout_blocks_left": timeout_left,
            "offer_seconds": p.offer_seconds,
            "offer": self.pending,
            "shift_over": self.shift_over,
        }

    def results(self):
        """Everything the end-of-shift debrief needs (see report.py)."""
        return shift_results(self)
