"""
The shift itself: GameController runs one shift of a RideHailSimulation,
making offers to the player and the bots through the dispatcher's offer
filter and keeping every driver's ledger (shift.ShiftBase).
"""

import random

from ridehail.atom import TripPhase, VehiclePhase
from ridehail.dispatch import Dispatch, OfferDecision
from ridehail.game.bots import BOTS
from ridehail.game.params import MINUTES_PER_HOUR, GameParams
from ridehail.game.pricing import OfferPricing
from ridehail.game.report import shift_results
from ridehail.game.shift import Ledger, ShiftBase

__all__ = ["GameController", "Ledger"]


class GameController(ShiftBase):
    """
    Wraps a RideHailSimulation for one shift. Call warm_up() once, then for
    each block: before_block(); sim.next_block(); after_block(). When
    after_block() leaves a pending offer, call resolve_offer() before the next
    block (an unresolved offer is treated as a timeout). step() does all of
    this for headless play with a callable decider.
    """

    def __init__(self, sim, params=None, seed=1, cars_per_bot=1):
        params = params or GameParams()
        self.rng = random.Random(seed)
        super().__init__(
            sim, params, OfferPricing(params, self.rng), params.shift_blocks
        )
        # The player and the bots take their seats when the warm-up ends
        # (see warm_up()). cars_per_bot > 1 seats several cars per bot, for
        # headless studies (utils/game_environment_scan.py).
        self.cars_per_bot = cars_per_bot
        self.player_vehicle = None
        self.player = None
        self.bot_vehicles = []
        self.bots = {}
        self.offer_log = []
        # trip id -> player's log entry, for trips the player declined
        self._declined_log = {}
        self.pending = None
        self.timeout_until = None
        self._recent_decisions = []
        # ((phase name, trip id), leg length in blocks) for the player's
        # current pickup or trip, for the HUD's progress bar
        self._leg = None
        sim.dispatcher.offer_filter = self._offer_filter

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

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
        Run the market to a steady state before the shift starts, then seat
        the player and the bots in randomly chosen cars and start the shift.
        """
        for _ in range(self.params.warmup_blocks):
            self.sim.next_block()
        self._take_seats()
        self.start_shift()

    def _take_seats(self):
        """
        Seat the player and the bots in cars chosen at random from the whole
        fleet, so that they start the shift where fleet cars are. A seated
        car on a pickup or trip is on shift at once and is paid for the part
        of the trip still to drive, as every fleet car is
        (ShiftBase.start_shift).
        Seated cars that sat out the warm-up instead drifted towards the
        City Centre undispatched and started about $1/hr ahead of the fleet
        when Slow or Normal (claude/game-environment-scan.md, "Follow-up").
        Drivers are identified by vehicle.index, which is fixed for the life
        of a vehicle, not by position in sim.vehicles, which changes if the
        fleet does (Simulation._remove_vehicles). See position().
        """
        vehicles = self.sim.vehicles
        seats = self.rng.sample(range(len(vehicles)), 1 + self.cars_per_bot * len(BOTS))
        self.player_vehicle = vehicles[seats[0]]
        self.player = self.player_vehicle.index
        self.bot_vehicles = [vehicles[seat] for seat in seats[1:]]
        self.bots = {
            v.index: BOTS[i % len(BOTS)] for i, v in enumerate(self.bot_vehicles)
        }

    # ------------------------------------------------------------------
    # Offers
    # ------------------------------------------------------------------

    def describe_offer(self, trip, vehicle, dispatch_distance):
        p = self.params
        rate_card = self.pricing.price(trip)[0]
        offer = self.pricing.offer_price(trip, dispatch_distance)
        pickup_minutes = dispatch_distance * p.minutes_per_block
        trip_minutes = trip.distance * p.minutes_per_block
        pickup_km = dispatch_distance * p.km_per_block
        trip_km = trip.distance * p.km_per_block
        per_min = round(offer / (pickup_minutes + trip_minutes), 3)
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
            "per_min": per_min,
            # $/hr, pickup included: what the bots' rate rules test
            # (strategy_spec.Strategy.accepts)
            "rate": per_min * MINUTES_PER_HOUR,
            "per_km": round(offer / (pickup_km + trip_km), 3),
            "vehicle_location": list(vehicle.location),
            "pickup": list(trip.origin),
            "dropoff": list(trip.destination),
            "dropoff_zone": self.sim.city.zone(trip.destination),
        }

    def _offer_filter(self, trip, vehicle, dispatch_distance):
        """Dispatch.offer_filter: the fast path is any ordinary fleet car."""
        index = vehicle.index
        is_player = index == self.player
        if not is_player and index not in self.bots:
            if trip.index in self._declined_log:
                self._note_taken(trip, dispatch_distance)
            return self._fleet_accepts(trip, index, dispatch_distance)
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
        was_over = self.shift_over
        super().after_block()
        if self.shift_over and not was_over:
            self.pending = None

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
