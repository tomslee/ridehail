"""
An individual strategy from the configuration (use_strategy and the
[STRATEGY] section; claude/strategy-config-spec.md).

One car is seated with the strategy (strategy_offer and strategy_idle;
ridehail/strategy_spec.py). It takes or declines the offers dispatch makes
it by its offer rule, playing by the game's rules: one offer a block, and a
declined trip waits for the next block. Every other car takes every offer.

The shift is the last results_window blocks of the run, the blocks the core
results are averaged over. The car is drawn at random from the fleet when
the shift starts, wherever it is and whatever it is doing, as the game
seats its player and bots: a car kept out of service until then would
drift undispatched and start ahead of the fleet
(claude/game-environment-scan.md, "Follow-up"). A trip under way then is
paid for the blocks of it in the shift. Over the shift the car's time is
counted the way the core counts the fleet's (each block's phase, and whether it stayed parked
while idle), and its income is the core's formulas applied to that time
(ridehail/measures.py): gross is price (less commission) per block with a
rider, net is gross less running costs (ops_cost) on blocks driven, surplus
is net less the reservation wage. So the car compares directly with the
fleet's income_and_costs. With use_city_scale incomes are per hour,
otherwise per block.

An offer is the core's fare for the trip, price per block of the trip less
the commission (the pickup is unpaid), times the trip's upfront-pricing
factor: lognormal with mean 1 and log spread offer_variability, 1 when that
is 0 (claude/upfront-pricing-spec.md). The car earns its trip's fare times
the factor in each block it has a rider, so with no variability its income
is exactly the core's formula.

RideHailSimulation builds a StrategyController when use_strategy is set,
and calls before_block() and after_block() from next_block().
"""

import math
import random

from ridehail.atom import CityScaleUnit, Measure, VehiclePhase
from ridehail.dispatch import OfferDecision
from ridehail.strategy_spec import make_strategy


class StrategyController:
    def __init__(self, sim):
        self.sim = sim
        # The seat is drawn from its own generator, so the simulation's
        # random stream is not touched here
        seed = sim.random_number_seed
        self.rng = random.Random(seed) if seed else random.Random()
        self.strategy = make_strategy(sim.strategy_offer, sim.strategy_idle)
        # Each trip's upfront-pricing factor is a function of this seed and
        # the trip's index (offer_factor)
        self.price_seed = seed if seed else self.rng.getrandbits(32)
        # The seated car and its vehicle.index, from the start of the shift
        self.vehicle = None
        self.seat = None
        self.shift_start = max(0, sim.time_blocks - sim.results_window)
        self.shift_blocks = sim.results_window
        self.active = False
        self.shift_block = 0
        # Blocks of the shift in each phase, and those parked while idle
        self.blocks = {phase: 0 for phase in VehiclePhase}
        self.parked_blocks = 0
        # What the car has earned in its blocks with a rider (per block,
        # before running costs)
        self.earnings = 0.0
        self.offers = 0
        self.accepts = 0
        # Trips the seated car has declined: it is not offered them again
        self.declined = set()
        sim.dispatcher.offer_filter = self._offer_filter
        sim.protected_vehicles = set()

    @property
    def per_hour(self):
        return bool(self.sim.use_city_scale)

    @property
    def rate_unit(self):
        return "hour" if self.per_hour else "block"

    @property
    def shift_over(self):
        return self.shift_block >= self.shift_blocks

    def before_block(self):
        """At the start of the shift, seat the car."""
        if not self.active and self.sim.block_index >= self.shift_start:
            self.active = True
            vehicles = self.sim.vehicles
            self.vehicle = vehicles[self.rng.randrange(len(vehicles))]
            self.seat = self.vehicle.index
            # Changes to the fleet must not remove the seated car
            self.sim.protected_vehicles = {self.seat}
            self.strategy.apply_idle(self.vehicle)

    def after_block(self):
        """Count the seated car's block, as the core's history counts the fleet's."""
        if not self.active or self.shift_over:
            return
        self.blocks[self.vehicle.phase] += 1
        if self.vehicle.phase == VehiclePhase.P3:
            self.earnings += self._fare_per_block() * self.offer_factor(
                self.vehicle.trip_index
            )
        if self.vehicle.parked:
            self.parked_blocks += 1
        self.shift_block += 1

    def offer_factor(self, trip_index):
        """
        The trip's upfront-pricing factor m: lognormal with mean 1 and log
        spread offer_variability, drawn from a generator seeded with the
        run's price seed and the trip's index, so a trip always has the same
        factor, whoever is offered it and in whatever order.
        """
        sigma = self.sim.offer_variability
        if not sigma:
            return 1.0
        rng = random.Random(f"{self.price_seed}:{trip_index}")
        return math.exp(rng.gauss(-0.5 * sigma * sigma, sigma))

    def _fare_per_block(self):
        """The driver's share of the fare for a block of a trip: the rate card."""
        return self.sim.price * (1.0 - self.sim.platform_commission)

    def _per_rate_unit(self, per_block):
        """A per-block amount in the rate unit: per hour with use_city_scale."""
        if self.per_hour:
            return self.sim.convert_units(
                per_block, CityScaleUnit.PER_BLOCK, CityScaleUnit.PER_HOUR
            )
        return per_block

    def describe_offer(self, trip, dispatch_distance):
        """What the strategy decides on: the offer and its rate, pickup included."""
        offer = self._fare_per_block() * trip.distance * self.offer_factor(trip.index)
        rate = self._per_rate_unit(offer / max(dispatch_distance + trip.distance, 1))
        return {
            "offer": offer,
            "rate": rate,
            "dropoff_zone": self.sim.city.zone(trip.destination),
        }

    def _offer_filter(self, trip, vehicle, dispatch_distance):
        """Dispatch.offer_filter: the fast path is any ordinary fleet car."""
        if vehicle.index != self.seat:
            return OfferDecision.ACCEPT
        if not self.active or self.shift_over or trip.index in self.declined:
            return OfferDecision.DECLINE
        self.offers += 1
        if self.strategy.accepts(self.describe_offer(trip, dispatch_distance)):
            self.accepts += 1
            return OfferDecision.ACCEPT
        # One offer a block: DEFER takes the car out of the pool for the rest
        # of the block, and the trip waits for the next (claude/game-mode.md
        # 10.5)
        self.declined.add(trip.index)
        return OfferDecision.DEFER

    # ------------------------------------------------------------------
    # Results
    # ------------------------------------------------------------------

    def summary(self):
        """
        The shift so far, as a flat dict (an end_state section): the seated
        car's time shares and income, measured as the core measures the
        fleet's (the end state's vehicles and income_and_costs sections).
        Incomes are per hour with use_city_scale, otherwise per block, and
        idle_per_accept is in minutes or blocks. Measures with nothing to
        measure are None; numbers are rounded to 3 places.
        """
        sim = self.sim
        time = self.shift_block
        summary = {}
        for phase in VehiclePhase:
            summary[phase.name.lower()] = self.blocks[phase] / time if time else None
        summary["fraction_parked"] = self.parked_blocks / time if time else None
        if time:
            # With no offer variability, gross is the core's
            # price * (1 - commission) * p3
            gross = self.earnings / time
            net = gross - sim.ops_cost * (1.0 - summary["fraction_parked"])
            summary["gross_income"] = self._per_rate_unit(gross)
            summary["net_income"] = self._per_rate_unit(net)
            summary["surplus"] = self._per_rate_unit(net - sim.reservation_wage)
        else:
            summary["gross_income"] = summary["net_income"] = None
            summary["surplus"] = None
        summary["offers"] = self.offers
        summary["accepts"] = self.accepts
        idle = self.blocks[VehiclePhase.P1]
        if self.per_hour:
            idle *= sim.minutes_per_block
        summary["idle_per_accept"] = idle / self.accepts if self.accepts else None
        # Rounded like the rest of the end state
        return {
            key: round(value, 3) if isinstance(value, float) else value
            for key, value in summary.items()
        }


def _cell(value, form):
    return "-" if value is None else format(value, form)


def format_summary(controller):
    """
    A plain-text comparison of the seated car with the whole fleet, whose
    figures are the end state's (and include the seated car).
    """
    from ridehail.results import RideHailSimulationResults

    summary = controller.summary()
    measures = RideHailSimulationResults(controller.sim).get_result_measures()
    unit = controller.rate_unit
    time_unit = "min" if unit == "hour" else "blocks"
    strategy = controller.strategy
    name = strategy.name(per_hour=unit == "hour")
    fleet_name = f"Fleet ({len(controller.sim.vehicles)} cars)"
    acceptance = summary["accepts"] / summary["offers"] if summary["offers"] else None
    width = max(len(name), len(fleet_name))
    rows = [
        (
            name,
            summary["gross_income"],
            summary["net_income"],
            summary["surplus"],
            acceptance,
            summary["idle_per_accept"],
        )
        + tuple(summary[p] for p in ("p1", "p2", "p3")),
        (
            fleet_name,
            measures[Measure.VEHICLE_GROSS_INCOME.name],
            measures[Measure.VEHICLE_NET_INCOME.name],
            measures[Measure.VEHICLE_MEAN_SURPLUS.name],
            None,
            None,
        )
        + tuple(measures[f"VEHICLE_FRACTION_{p}"] for p in ("P1", "P2", "P3")),
    ]
    lines = [
        f"Strategy {strategy.label}: {controller.shift_block}-block shift, "
        f"incomes per {unit}",
        f"{'':<{width}}  {'gross':>7}  {'net':>7}  {'surplus':>7}  {'accepts':>7}  "
        f"{'idle ' + time_unit + '/trip':>16}  {'P1 / P2 / P3':>18}",
    ]
    for label, gross, net, surplus, acceptance, idle, p1, p2, p3 in rows:
        split = " / ".join(_cell(p, ".2f") for p in (p1, p2, p3))
        lines.append(
            f"{label:<{width}}  {_cell(gross, '.2f'):>7}  {_cell(net, '.2f'):>7}  "
            f"{_cell(surplus, '.2f'):>7}  {_cell(acceptance, '.0%'):>7}  "
            f"{_cell(idle, '.1f'):>16}  {split:>18}"
        )
    return "\n".join(lines)
