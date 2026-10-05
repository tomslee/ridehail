"""
Game mode: "Just One More Shift…".

The player drives one car in a fixed-fleet simulation. When the dispatcher
picks the player's car for a trip, the trip becomes an *offer* at an upfront
price, and the player accepts or declines it. At the end of the shift the
player's net earnings per hour are compared with four rule-following bot
drivers and with the rest of the fleet (who accept everything).

This module holds all the game logic, so that it can be tested and calibrated
headless; the web lab (docs/lab/worker.py) only renders it and forwards the
player's decisions. See claude/game-mode.md for the design.

Scale: one block is one minute and KM_PER_BLOCK = 0.37 km (22 km/h), so trip
time and distance are proportional. 22 km/h is a typical speed for Toronto
trips under 12 km (claude/game-mode.md, 5.8); a 32-block city is 11.8 km
across. Money is computed here, not by the
simulation's Costs & Incomes mode, which stays off.

Offer prices come from a model fitted to the offer study (Uber offer cards
shown to Toronto drivers), weighted to Toronto's mix of trip lengths; see
ridehail/game_offer_model.py and claude/game-mode.md, Part 3:

    offer = F(trip_km, pickup_km) * luck

F falls per km as trips get longer and rises with long pickups. The luck is
drawn once per trip from the offer study's spread, so every driver offered a
trip shares it, but each driver's offer depends on their own pickup
distance. Each trip also has a rate card (base + per km + per minute, for the
trip only), which is a reference for the debrief and the rate-card bot, not
the source of the offer.

Rider fares: what the rider probably paid for each trip (claude/game-mode.md,
Part 4). The typical fare for the trip's length comes from the City of
Toronto's 2026 trip data (base + per km, including City fees and HST, excluding
tips). The trip's luck scales it as it scales the driver's offer, normalised
so the average fare is unchanged: the platform's take on real trips varies far
less than offers do, so a trip that pays the driver well also cost the rider
more. The debrief compares it with what the driver was paid.

Earnings accrue while the rider is on board, offer / trip_blocks per block,
with any rounding remainder credited at drop-off. Accruing per block treats
trips that straddle the start or end of the shift the same way for everyone.
"""

import bisect
import math
import random
from dataclasses import dataclass, field

from ridehail.atom import (
    DispatchMethod,
    Equilibration,
    TripDistribution,
    TripPhase,
    VehiclePhase,
)
from ridehail import game_offer_model as offer_model
from ridehail.config import RideHailConfig
from ridehail.dispatch import Dispatch, OfferDecision
from ridehail.simulation import RideHailSimulation

MINUTES_PER_HOUR = 60.0
# One block: one minute, and this many km (22 km/h)
KM_PER_BLOCK = 0.37
# Fleet cars that were on shift for less than this are left out of the
# comparison group (too short a window to compare with a whole shift)
MIN_FLEET_MINUTES = 60
# Ontario HST, included in the City's fares
HST_RATE = 0.13
# Mean of e^luck in each luck band, so that scaling a typical rider fare by
# e^luck / this leaves the average fare unchanged
MEAN_EXP_LUCK = [
    sum(math.exp(q) for q in band) / len(band) for band in offer_model.LUCK_QUANTILES
]


@dataclass
class GameParams:
    """Calibratable constants (see claude/game-mode.md, sections 1.4 and 1.9)."""

    km_per_block: float = KM_PER_BLOCK
    minutes_per_block: float = 1.0
    # Driver rate card, for the trip only: a reference for comparing offers
    # (offers themselves come from ridehail.game_offer_model)
    rate_base: float = 2.50
    rate_per_km: float = 0.75
    rate_per_min: float = 0.18
    price_step: float = 0.05
    # Running cost per km actually driven (idle cruising and pickups included).
    # The median vehicle expense per km driven, fixed and variable costs
    # together, from a 2024 report to the City of Toronto (background file
    # 251343, p. 26): https://www.toronto.ca/legdocs/mmis/2024/ex/bgrd/backgroundfile-251343.pdf
    ops_cost_per_km: float = 0.56
    shift_blocks: int = 180
    warmup_blocks: int = 60
    # Riders still unassigned after this many minutes give up (keeps the
    # backlog bounded in an undersupplied market)
    max_wait_minutes: int = 10
    # Seconds the player has to decide (used by the UI)
    offer_seconds: int = 8
    # Dormant (no offer screen turns it on): fewer than min_accepts of the
    # last `window` offers accepted puts the player in a timeout (no offers)
    # for timeout_blocks, e.g. {"min_accepts": 4, "window": 10,
    # "timeout_blocks": 10}.
    acceptance_rule: dict | None = None


# The offer screens (claude/game-mode.md, "Rate helper"). They differ only in
# what the UI shows: "helper" adds the offer's $/km and $/hr, pickup
# included, as a third-party driver app overlays them on the platform's card;
# "platform" is the platform's card alone. Each has its own leaderboard.
CARDS = ("helper", "platform")

# Markets differ only in demand: the fleet is the same in every market, and
# Busy and Slow have more and fewer trip requests than Normal (claude/game-mode.md
# 1.9 and Part 8). Demand varies through the day and the week; the number of
# drivers responds to it, not the other way round, and with markets that
# differed in fleet size a Slow Tuesday had more cars on the road than a Busy
# Friday. At 0.37 km per block, a 32-block city with a mean trip draw of 16
# blocks reproduces Toronto's trip lengths up to 12 km (10/25/50/75/90%: 1.5
# / 2.6 / 4.4 / 7.0 / 9.2 km against 1.7 / 2.6 / 4.3 / 6.9 / 9.5). Normal's
# demand is scaled with the area from the earlier 24-block city (5 -> 9 per
# minute), and Busy and Slow demand were searched (Part 8) for the earlier
# markets' time split (5.8): Busy undersupplied (P1 ~ 0, about 15% of riders
# give up), Normal P1 ~ 0.2, Slow P1 ~ 0.47. When idle cars started waiting
# where they are half the time (IDLE_VEHICLES_MOVING, Part 13), declining an
# offer got cheaper, and Slow's demand was lowered (6.5 -> 5) until taking
# every offer again did about as well as any price threshold when Slow.
# Idle drivers head towards a place requests come from (mostly the City
# Centre) with this probability at each intersection, rather than always
# cruising at random (claude/idle-vehicles-returning.md; claude/game-mode.md
# Part 11, and 16.11 for the change to a sampled request origin).
IDLE_VEHICLES_RETURNING = 0.25
# An idle car moves (and pays running costs) in only this fraction of
# minutes: in the others it waits where it is, as real drivers often park
# rather than cruise (claude/game-mode.md Part 13).
IDLE_VEHICLES_MOVING = 0.5
MARKET_SHARED = {
    "city_size": 32,
    "vehicle_count": 215,
    "mean_trip_distance": 16,
    "inhomogeneity": 0.5,
}
MARKETS = {
    "busy": {"label": "Busy Friday", "base_demand": 11.0},
    "normal": {"label": "Normal", "base_demand": 9.0},
    "slow": {"label": "Slow Tuesday", "base_demand": 5.0},
}
# The big city (hidden in the web lab: "+" on the setup screen) is 48 blocks
# (17.8 km) across, so the city-size cap on trip lengths no longer cuts off
# Toronto's long trips (the 32-block city loses about a tenth of its trip
# draws to the cap). The mean trip draw is unchanged. The fleet is 6000
# cars, roughly Toronto's; Normal's demand and the other markets' demand were
# searched for the same time split as the 32-block markets (P1 / P2 / P3,
# riders giving up): Busy 0 / 0.31 / 0.69, ~15%; Normal 0.19 / 0.22 / 0.59;
# Slow 0.46 / 0.12 / 0.42. Pickups are a little shorter than in the 32-block
# city. With IDLE_VEHICLES_MOVING, Slow was cut by the same fraction as the
# 32-block city's (170 -> 130), keeping its P1 a little above that city's
# (0.65 against 0.63).
CITIES = ("standard", "big")
BIG_CITY_SHARED = {
    "city_size": 48,
    "vehicle_count": 6000,
    "mean_trip_distance": 16,
    "inhomogeneity": 0.5,
}
BIG_CITY_DEMAND = {"busy": 330.0, "normal": 240.0, "slow": 130.0}


def market_settings(market, city="standard"):
    """City size, demand, trip length, inhomogeneity and fleet for a market."""
    if market not in MARKETS:
        raise ValueError(f"Unknown market '{market}'. Choose from {list(MARKETS)}")
    if city == "standard":
        return {**MARKET_SHARED, **MARKETS[market]}
    if city == "big":
        return {
            **BIG_CITY_SHARED,
            **MARKETS[market],
            "base_demand": BIG_CITY_DEMAND[market],
        }
    raise ValueError(f"Unknown city '{city}'. Choose from {list(CITIES)}")


# The price bots' thresholds in $/hr, pickup included, like the $/hr the rate
# helper shows on the offer card. A car covers one block a minute, pickup or
# trip, so $/km and $/hr rank offers the same way, and one scale is enough: a
# weak and a strong threshold either side of the best one (about $27-30/hr in
# every market; claude/game-mode.md Part 10). The strong one wins when Busy
# and loses when Slow.
BOT_HOURLY_LOW = 22
BOT_HOURLY_HIGH = 33


@dataclass
class Bot:
    key: str
    name: str

    def accepts(self, offer):
        if self.key == "yes":
            return True
        if self.key == "hourly_low":
            return offer["per_min"] * MINUTES_PER_HOUR >= BOT_HOURLY_LOW
        if self.key == "hourly_high":
            return offer["per_min"] * MINUTES_PER_HOUR >= BOT_HOURLY_HIGH
        if self.key == "centre":
            # Destination-driven: requests come mostly from the City Centre
            # (inhomogeneity), so ending a trip there means a quick next
            # offer, while idle cars collect in the outskirts
            # (claude/game-mode.md 5.7, Part 9 and 10.6)
            return offer["dropoff_zone"] == "core"
        raise ValueError(f"Unknown bot {self.key}")


# Each bot is named for its rule, so the debrief needs no other explanation
BOTS = [
    Bot("yes", "Takes every offer"),
    Bot("hourly_low", f"Takes ${BOT_HOURLY_LOW}/hr or more"),
    Bot("hourly_high", f"Takes ${BOT_HOURLY_HIGH}/hr or more"),
    Bot("centre", "Takes trips to the City Centre"),
]


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


def make_game_config(
    market="normal",
    seed=1,
    shift_blocks=180,
    warmup_blocks=60,
    city="standard",
    max_wait_time=GameParams.max_wait_minutes,
):
    """A RideHailConfig for a game market: Simple mode, fixed fleet and demand.
    Riders give up after max_wait_time blocks (minutes) without a car."""
    settings = market_settings(market, city)
    config = RideHailConfig(use_config_file=False)
    config.animation.value = "none"
    config.run_sequence.value = False
    config.interpolate.value = 0
    config.city_size.value = settings["city_size"]
    config.vehicle_count.value = settings["vehicle_count"]
    config.base_demand.value = settings["base_demand"]
    config.mean_trip_distance.value = settings["mean_trip_distance"]
    config.inhomogeneity.value = settings["inhomogeneity"]
    config.inhomogeneous_destinations.value = False
    config.trip_distance_distribution.value = TripDistribution.GAMMA
    config.idle_vehicles_moving.value = IDLE_VEHICLES_MOVING
    config.idle_vehicles_returning.value = IDLE_VEHICLES_RETURNING
    config.pickup_time.value = 1
    config.max_wait_time.value = max_wait_time
    config.equilibration.value = Equilibration.NONE
    config.dispatch_method.value = DispatchMethod.DEFAULT
    config.use_city_scale.value = False
    config.minutes_per_block.value = 1.0
    config.mean_vehicle_speed.value = KM_PER_BLOCK * MINUTES_PER_HOUR
    config.time_blocks.value = shift_blocks + warmup_blocks
    # The simulation seeds the global RNG only for a truthy seed
    config.random_number_seed.value = int(seed) or 1
    return config


def shift_seed(code, market, city="standard"):
    """
    A stable, non-zero 31-bit seed from a shift code and market (FNV-1a).
    The standard city's seeds are unchanged from before the big city.
    """
    key = f"{code}|{market}" if city == "standard" else f"{code}|{market}|{city}"
    h = 0x811C9DC5
    for byte in key.encode():
        h = ((h ^ byte) * 0x01000193) & 0xFFFFFFFF
    return (h & 0x7FFFFFFF) | 1


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
        vehicle_count = len(sim.vehicles)
        seats = self.rng.sample(range(vehicle_count), 1 + len(BOTS))
        self.player = seats[0]
        self.bots = {index: bot for index, bot in zip(seats[1:], BOTS)}
        # Every driver is measured from their first idle moment in the shift,
        # so that everyone is compared on the same footing as the player, who
        # logs on idle. A fleet car on a trip when the shift starts joins when
        # that trip ends (the trip itself does not count). See after_block().
        self.on_shift = set()
        self._pre_shift_trip = {}
        self.ledgers = [Ledger() for _ in range(vehicle_count)]
        # trip id -> (rate_card, luck): drawn once per trip
        self.prices = {}
        # (vehicle index, trip id) -> the offer that driver took the trip at
        self.agreed = {}
        # Set to a list to collect every offer priced (for validation)
        self.record_offers = None
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
        self.pending = None
        self.active = False
        self.shift_block = 0
        self.shift_over = False
        self.timeout_until = None
        self._recent_decisions = []
        # Vehicle locations after the previous block, for the km count
        self._prev_locations = None
        # ((phase name, trip id), leg length in blocks) for the player's
        # current pickup or trip, for the HUD's progress bar
        self._leg = None
        self._city_core = self._core_range()
        sim._dispatcher.offer_filter = self._offer_filter

    # ------------------------------------------------------------------
    # Setup
    # ------------------------------------------------------------------

    def _core_range(self):
        return self.sim.city.core_bounds()

    def warm_up(self):
        """
        Run the market to a steady state before the shift starts. The player
        and the bots are logged off (out of the dispatch pool), so each of
        them logs on idle.
        """
        dispatcher = self.sim._dispatcher
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
        self._prev_locations = [list(v.location) for v in self.sim.vehicles]

    # ------------------------------------------------------------------
    # Prices and offers
    # ------------------------------------------------------------------

    def rate_card(self, trip_blocks):
        p = self.params
        return (
            p.rate_base
            + p.rate_per_km * trip_blocks * p.km_per_block
            + p.rate_per_min * trip_blocks * p.minutes_per_block
        )

    def _round_price(self, value):
        step = self.params.price_step
        return round(round(value / step) * step, 2)

    def price(self, trip):
        """(rate_card, luck) for a trip, drawn the first time it is needed."""
        if trip.index not in self.prices:
            km = trip.distance * self.params.km_per_block
            band = bisect.bisect_right(offer_model.LUCK_BAND_EDGES, km)
            self.prices[trip.index] = (
                round(self.rate_card(trip.distance), 2),
                self._draw_luck(band),
            )
        return self.prices[trip.index]

    def _draw_luck(self, band):
        """log(offer / F), by inverse CDF from the stored quantiles."""
        probs = offer_model.LUCK_PROBS
        quantiles = offer_model.LUCK_QUANTILES[band]
        u = min(max(self.rng.random(), probs[0]), probs[-1])
        i = min(bisect.bisect_right(probs, u), len(probs) - 1)
        p0, p1 = probs[i - 1], probs[i]
        q0, q1 = quantiles[i - 1], quantiles[i]
        return q0 + (q1 - q0) * (u - p0) / (p1 - p0)

    @staticmethod
    def typical_offer(trip_km, pickup_km):
        """F: the typical offer for a trip and pickup (before the trip's luck)."""
        c = offer_model.COEF
        log_km = math.log(max(trip_km, 0.1))
        log_f = c[0] + c[1] * log_km + c[2] * log_km * log_km
        if offer_model.FORM == "log1p":
            log_f += c[3] * math.log1p(pickup_km)
        else:
            log_f += c[3] * pickup_km + c[4] * max(0.0, pickup_km - offer_model.KNEE_KM)
        return math.exp(log_f)

    def offer_price(self, trip, dispatch_distance):
        """The offer to a driver dispatch_distance blocks from the pickup."""
        p = self.params
        trip_km = trip.distance * p.km_per_block
        pickup_km = dispatch_distance * p.km_per_block
        luck = self.price(trip)[1]
        value = max(
            offer_model.MIN_OFFER,
            self.typical_offer(trip_km, pickup_km) * math.exp(luck),
        )
        offer = self._round_price(value)
        if self.record_offers is not None:
            self.record_offers.append(
                {"offer": offer, "trip_km": trip_km, "pickup_km": pickup_km}
            )
        return offer

    @staticmethod
    def typical_rider_fare(trip_km):
        """The City's typical fare for a trip this long (City fees and HST in)."""
        return offer_model.RIDER_FARE_BASE + offer_model.RIDER_FARE_PER_KM * trip_km

    def rider_fare(self, trip):
        """
        What the rider probably paid for a trip: the typical fare, scaled by
        the trip's luck as the driver's offer is, with the average unchanged.
        """
        trip_km = trip.distance * self.params.km_per_block
        band = bisect.bisect_right(offer_model.LUCK_BAND_EDGES, trip_km)
        luck = self.price(trip)[1]
        return round(
            self.typical_rider_fare(trip_km) * math.exp(luck) / MEAN_EXP_LUCK[band], 2
        )

    def zone(self, location):
        low, high = self._city_core
        if all(low <= c < high for c in location):
            return "core"
        return "outskirts"

    def describe_offer(self, trip, vehicle, dispatch_distance):
        p = self.params
        rate_card = self.price(trip)[0]
        offer = self.offer_price(trip, dispatch_distance)
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
            "rider_fare": self.rider_fare(trip),
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
            self.agreed[(index, trip.index)] = self.offer_price(trip, dispatch_distance)
            return OfferDecision.ACCEPT
        declined_by = getattr(trip, "declined_by", None)
        if not self.active or self.shift_over:
            # Before and after the shift, the player and bots are logged off
            return OfferDecision.DECLINE
        if declined_by and index in declined_by:
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
        if getattr(trip, "declined_by", None) is None:
            trip.declined_by = set()
        trip.declined_by.add(index)

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
        vehicle = self.sim.vehicles[self.player]
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
        for index, vehicle in enumerate(self.sim.vehicles):
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
                    fare = self.rider_fare(trip) / trip.distance
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
                    self.rider_fare(trip) - self.accrued_fare[key]
                )
                self.ledgers[index].trips_completed += 1
            del self.accrued[key]
            self.accrued_fare.pop(key, None)
            self.agreed.pop(key, None)
            self._accruing_trips.pop(trip_id, None)
        self._prev_locations = [list(v.location) for v in self.sim.vehicles]
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
            self.agreed[key] = self.offer_price(trip, 0)
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
        vehicle = self.sim.vehicles[self.player]
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
        player = self.sim.vehicles[self.player]
        summary = self.ledgers[self.player].summary(p)
        timeout_left = 0
        if self.timeout_until is not None:
            timeout_left = max(0, self.timeout_until - self.shift_block)
        return {
            "shift_block": self.shift_block,
            "shift_blocks": p.shift_blocks,
            "player": self.player,
            "bots": {str(i): bot.name for i, bot in self.bots.items()},
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
        """Everything the end-of-shift debrief needs."""
        p = self.params
        minutes = self.shift_minutes()
        player = self.ledgers[self.player].summary(p)
        bots = []
        for index, bot in self.bots.items():
            row = self.ledgers[index].summary(p)
            row.update({"key": bot.key, "name": bot.name})
            bots.append(row)
        # Every other driver, each over their own time on shift (see
        # on_shift), leaving out any who joined too late to be comparable.
        others = [
            self.ledgers[i]
            for i in sorted(self.on_shift)
            if i != self.player
            and sum(self.ledgers[i].minutes.values()) >= MIN_FLEET_MINUTES
        ]
        fleet = [ledger.summary(p)["net_per_hour"] for ledger in others]
        # Their pooled share of what riders paid before HST
        fleet_fares = sum(ledger.rider_fares for ledger in others) / (1 + HST_RATE)
        fleet_share = (
            round(sum(ledger.earnings for ledger in others) / fleet_fares, 3)
            if fleet_fares > 0
            else None
        )
        beaten = sum(1 for value in fleet if value < player["net_per_hour"])
        log = self.offer_log
        accepted = [e for e in log if e["decision"] == "accept"]
        declined = [e for e in log if e["decision"] != "accept"]
        return {
            "player": player,
            "bots": bots,
            "fleet_net_per_hour": sorted(fleet),
            "fleet_mean_net_per_hour": round(sum(fleet) / len(fleet), 2)
            if fleet
            else 0.0,
            "fleet_percentile": round(beaten / len(fleet), 3) if fleet else None,
            "fleet_driver_share": fleet_share,
            # Those drivers' pooled time in each phase, for the debrief's
            # "Where your time went" comparison
            "fleet_minutes": {
                phase: round(sum(ledger.minutes[phase] for ledger in others), 1)
                for phase in ("P1", "P2", "P3")
            },
            "offer_log": log,
            "insights": {
                "declined_above_rate_card": sum(
                    1 for e in declined if e["offer"] >= e["rate_card"]
                ),
                "accepted_below_rate_card": sum(
                    1 for e in accepted if e["offer"] < e["rate_card"]
                ),
                "unpaid_share": (
                    round(
                        (player["minutes"]["P1"] + player["minutes"]["P2"]) / minutes,
                        3,
                    )
                    if minutes
                    else None
                ),
                "pickup_share": (
                    round(player["minutes"]["P2"] / minutes, 3) if minutes else None
                ),
                "best_per_min": max((e["per_min"] for e in accepted), default=None),
                "worst_per_min": min((e["per_min"] for e in accepted), default=None),
                "idle_minutes_per_offer": (
                    round(player["minutes"]["P1"] / len(log), 2) if log else None
                ),
                "rider_extra_wait": sum(e.get("rider_extra_wait", 0) for e in declined),
                "declined_never_taken": sum(
                    1 for e in declined if "taken_after_minutes" not in e
                ),
            },
            "params": {
                "shift_blocks": p.shift_blocks,
                "rate_base": p.rate_base,
                "rate_per_km": p.rate_per_km,
                "rate_per_min": p.rate_per_min,
                "ops_cost_per_km": p.ops_cost_per_km,
                "offer_study_offers": offer_model.N_OFFERS,
                "rider_fare_base": offer_model.RIDER_FARE_BASE,
                "rider_fare_per_km": offer_model.RIDER_FARE_PER_KM,
                "rider_fare_months": offer_model.RIDER_FARE_MONTHS,
                "hst_rate": HST_RATE,
                "city_km": round(self.sim.city.city_size * p.km_per_block, 1),
            },
        }


def create_game(
    market="normal", code="practice", card="helper", params=None, city="standard"
):
    """
    Build a (sim, controller) pair for one shift, warmed up and ready for
    block 0 of the shift.
    """
    params = params or GameParams()
    if card not in CARDS:
        raise ValueError(f"Unknown offer screen '{card}'")
    seed = shift_seed(code, market, city)
    config = make_game_config(
        market,
        seed,
        params.shift_blocks,
        params.warmup_blocks,
        city,
        params.max_wait_minutes,
    )
    sim = RideHailSimulation(config)
    controller = GameController(sim, params, seed=seed)
    controller.warm_up()
    return sim, controller
