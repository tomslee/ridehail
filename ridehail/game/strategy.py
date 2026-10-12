"""
An individual strategy from the configuration (use_strategy and the
[STRATEGY] section; claude/strategy-config-spec.md).

One car is seated with the strategy (strategy_offer and strategy_idle;
ridehail/strategy_spec.py). It takes or declines the offers dispatch makes
it by its offer rule, playing by the game's
rules: one offer a block, and a declined trip waits for the next block.
Every other car takes every offer. The shift is the last results_window
blocks of the run: before it, the seated car is logged off, so it starts
the shift idle; fleet cars join the shift at their first idle moment
(shift.ShiftBase).

Money follows the simulation's mode. With use_city_scale, a block has a
length in km and a duration in minutes, running costs are per_km_ops_cost
and earnings are reported per hour; in Simple mode everything is per block
and running costs are strategy_ops_cost per block driven. Offers are priced
by strategy_pricing: the simulation's own fare (FarePricing), or the game's
offer model (pricing.OfferPricing, use_city_scale only).

RideHailSimulation builds a StrategyController when use_strategy is set,
and calls before_block() and after_block() from next_block().
"""

import random
import statistics

from ridehail.atom import StrategyPricing, VehiclePhase
from ridehail.dispatch import OfferDecision
from ridehail.game.params import MINUTES_PER_HOUR, GameParams
from ridehail.game.pricing import OfferPricing
from ridehail.game.shift import ShiftBase
from ridehail.strategy_spec import make_strategy

# The rest of the fleet is compared over cars on shift for at least this
# share of it (the game: 60 of 180 minutes, MIN_FLEET_MINUTES)
MIN_FLEET_SHARE = 1 / 3


def strategy_params(sim):
    """
    GameParams carrying the mode's units: km and minutes per block with
    use_city_scale; otherwise one "km" and one "minute" is a block, so
    distance and time are counted in blocks.
    """
    if sim.use_city_scale:
        return GameParams(
            km_per_block=sim.mean_vehicle_speed
            * sim.minutes_per_block
            / MINUTES_PER_HOUR,
            minutes_per_block=sim.minutes_per_block,
            ops_cost_per_km=sim.per_km_ops_cost,
        )
    return GameParams(
        km_per_block=1.0, minutes_per_block=1.0, ops_cost_per_km=sim.strategy_ops_cost
    )


class FarePricing:
    """
    The simulation's own fare: price per block in Simple mode; base fare,
    per km and per minute with use_city_scale. The driver is offered the
    fare less the platform commission; the pickup is unpaid.
    """

    def __init__(self, sim, params):
        self.sim = sim
        self.params = params

    def rider_fare(self, trip):
        sim = self.sim
        if sim.use_city_scale:
            p = self.params
            return (
                sim.base_fare
                + sim.per_km_price * trip.distance * p.km_per_block
                + sim.per_minute_price * trip.distance * p.minutes_per_block
            )
        return sim.price * trip.distance

    def offer_price(self, trip, dispatch_distance):
        return self.rider_fare(trip) * (1.0 - self.sim.platform_commission)


class StrategyController(ShiftBase):
    def __init__(self, sim):
        params = strategy_params(sim)
        # The seat and the offer model's per-trip spread use their own
        # generator, so the simulation's random stream is not touched here
        seed = sim.random_number_seed
        self.rng = random.Random(seed) if seed else random.Random()
        if sim.strategy_pricing == StrategyPricing.OFFER_MODEL:
            pricing = OfferPricing(params, self.rng)
        else:
            pricing = FarePricing(sim, params)
        super().__init__(sim, params, pricing, sim.results_window)
        self.per_hour = bool(sim.use_city_scale)
        self.strategy = make_strategy(sim.strategy_offer, sim.strategy_idle)
        self.vehicle = sim.vehicles[self.rng.randrange(len(sim.vehicles))]
        self.seat = self.vehicle.index
        self.shift_start = max(0, sim.time_blocks - sim.results_window)
        sim.dispatcher.offer_filter = self._offer_filter
        # Logged off until the shift starts
        sim.dispatcher.offline = frozenset([self.seat])

    @property
    def rate_unit(self):
        return "hour" if self.per_hour else "block"

    def before_block(self):
        """At the start of the shift, log the seated car on."""
        if not self.active and self.sim.block_index >= self.shift_start:
            self.sim.dispatcher.offline = frozenset()
            self.start_shift()
            self.strategy.apply_idle(self.vehicle)

    def describe_offer(self, trip, dispatch_distance):
        """What the strategy decides on: the offer and its rate, pickup included."""
        offer = self.pricing.offer_price(trip, dispatch_distance)
        rate = offer / max(dispatch_distance + trip.distance, 1)
        if self.per_hour:
            rate *= MINUTES_PER_HOUR / self.params.minutes_per_block
        return {
            "offer": offer,
            "rate": rate,
            "dropoff_zone": self.zone(trip.destination),
        }

    def _offer_filter(self, trip, vehicle, dispatch_distance):
        """Dispatch.offer_filter: the fast path is any ordinary fleet car."""
        index = vehicle.index
        if index != self.seat:
            return self._fleet_accepts(trip, index, dispatch_distance)
        if not self.active or self.shift_over:
            return OfferDecision.DECLINE
        if index in self.declined_by.get(trip.index, ()):
            return OfferDecision.DECLINE
        offer = self.describe_offer(trip, dispatch_distance)
        ledger = self.ledgers[index]
        ledger.offers += 1
        if self.strategy.accepts(offer):
            ledger.accepts += 1
            self.agreed[(index, trip.index)] = offer["offer"]
            return OfferDecision.ACCEPT
        # One offer a block: DEFER takes the car out of the pool for the rest
        # of the block, and the trip waits for the next (claude/game-mode.md
        # 10.5)
        self._decline(trip, index)
        return OfferDecision.DEFER

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def net_rate(self, ledger):
        """Net earnings per hour (use_city_scale) or per block."""
        time = sum(ledger.minutes.values())
        if not time:
            return 0.0
        net = ledger.earnings - ledger.km * self.params.ops_cost_per_km
        return net / (time / MINUTES_PER_HOUR if self.per_hour else time)

    def fleet_ledgers(self):
        """Every other car on shift for at least MIN_FLEET_SHARE of it."""
        minimum = MIN_FLEET_SHARE * self.shift_minutes()
        return [
            self.ledgers[index]
            for index in sorted(self.on_shift)
            if index != self.seat
            and sum(self.ledgers[index].minutes.values()) >= minimum
        ]

    def summary(self):
        """
        The shift so far, as a flat dict (an end_state section): the seated
        car's measures, then the fleet's mean net rate (the fleet's time
        split is the end state's vehicles fraction_p1..3). Net
        rates are per hour with use_city_scale, otherwise per block; time is
        in minutes or blocks. Settings (the rules,
        the shift's length) are left out, like the rest of the end state.
        Measures with nothing to measure are None; numbers are rounded to 3
        places.
        """
        ledger = self.ledgers[self.seat]
        time = sum(ledger.minutes.values())
        summary = {
            "net_rate": self.net_rate(ledger),
            "earnings": ledger.earnings,
            "costs": ledger.km * self.params.ops_cost_per_km,
        }
        for phase in VehiclePhase:
            share = ledger.minutes[phase.name] / time if time else None
            summary[phase.name.lower()] = share
        summary.update(
            {
                "offers": ledger.offers,
                "accepts": ledger.accepts,
                "idle_per_accept": (
                    ledger.minutes["P1"] / ledger.accepts if ledger.accepts else None
                ),
                "trips_completed": ledger.trips_completed,
            }
        )
        fleet = self.fleet_ledgers()
        summary["fleet_net_rate"] = (
            statistics.fmean(self.net_rate(other) for other in fleet) if fleet else None
        )
        # Rounded like the rest of the end state
        return {
            key: round(value, 3) if isinstance(value, float) else value
            for key, value in summary.items()
        }


def _cell(value, form):
    return "-" if value is None else format(value, form)


def format_summary(controller):
    """
    A plain-text comparison of the seated car with the fleet. The fleet's
    time split is the whole fleet's, as in the end state.
    """
    from ridehail.results import RideHailSimulationResults

    summary = controller.summary()
    measures = RideHailSimulationResults(controller.sim).get_result_measures()
    unit = controller.rate_unit
    time_unit = "min" if unit == "hour" else "blocks"
    strategy = controller.strategy
    name = strategy.name(per_hour=unit == "hour")
    fleet_name = f"Fleet mean ({len(controller.fleet_ledgers())} cars)"
    acceptance = summary["accepts"] / summary["offers"] if summary["offers"] else None
    width = max(len(name), len(fleet_name))
    rows = [
        (name, summary["net_rate"], acceptance, summary["idle_per_accept"])
        + tuple(summary[p] for p in ("p1", "p2", "p3")),
        (fleet_name, summary["fleet_net_rate"], None, None)
        + tuple(measures[f"VEHICLE_FRACTION_{p}"] for p in ("P1", "P2", "P3")),
    ]
    lines = [
        f"Strategy {strategy.label}: {controller.shift_block}-block shift",
        f"{'':<{width}}  {'net/' + unit:>9}  {'accepts':>7}  "
        f"{'idle ' + time_unit + '/trip':>16}  {'P1 / P2 / P3':>18}",
    ]
    for label, net, acceptance, idle, p1, p2, p3 in rows:
        split = " / ".join(_cell(p, ".2f") for p in (p1, p2, p3))
        lines.append(
            f"{label:<{width}}  {_cell(net, '.2f'):>9}  {_cell(acceptance, '.0%'):>7}  "
            f"{_cell(idle, '.1f'):>16}  {split:>18}"
        )
    return "\n".join(lines)
