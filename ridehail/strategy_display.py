"""
Display helpers for the individual strategy (use_strategy), with no
terminal or Textual dependency so they can be tested on their own: the data
that the terminal_strategy display (claude/terminal-strategy-spec.md) draws.

- performance_lines(): the relative-performance panel's text, the car and
  the fleet over the same blocks;
- series_points(): the cumulative net income chart's points;
- offer_histogram() bins the seated car's offers
  (StrategyController.offer_log) by their rate, accepted and declined, and
  rate_threshold() is the threshold to mark on it, and count_ticks() its
  whole-number y-axis ticks;
- strategy_line(): a one-line summary, for the strip under terminal_map.
"""

import math

from ridehail.atom import OfferRule

# The most lines performance_lines() returns: the display gives the panel a
# fixed height, so that updating it needs no layout pass
PANEL_LINES = 7
# Steps for a histogram's bin width, times a power of ten
NICE_STEPS = (1.0, 2.0, 2.5, 5.0)


def nice_width(rough):
    """The smallest 1, 2, 2.5 or 5 times a power of ten at least rough."""
    if rough <= 0:
        return 1.0
    power = 10.0 ** math.floor(math.log10(rough))
    for step in NICE_STEPS:
        if step * power >= rough * (1 - 1e-9):
            return step * power
    return 10.0 * power


def offer_histogram(offer_log, threshold=None, max_bins=12):
    """
    Bin offers by rate (each a dict with "rate" and "accepted", as in
    StrategyController.offer_log) into at most about max_bins bins of a round
    width. With a threshold (a rate:N strategy's N), a bin edge falls on it,
    so no bin holds both offers below it and offers at or above it.

    Returns a dict: "edges" (bin edges, one more than the bins), "accepted"
    and "declined" (counts per bin), and "threshold". With no offers, the
    lists are empty.
    """
    result = {"edges": [], "accepted": [], "declined": [], "threshold": threshold}
    if not offer_log:
        return result
    rates = [offer["rate"] for offer in offer_log]
    low, high = min(rates), max(rates)
    if threshold is not None:
        low, high = min(low, threshold), max(high, threshold)
    width = nice_width((high - low) / max_bins if high > low else 1.0)
    # The edges are multiples of the width from the threshold (or from zero)
    anchor = threshold if threshold is not None else 0.0
    first = anchor + math.floor((low - anchor) / width + 1e-9) * width
    bins = max(1, math.ceil((high - first) / width + 1e-9))
    if first + bins * width <= high:
        bins += 1
    edges = [first + i * width for i in range(bins + 1)]
    accepted = [0] * bins
    declined = [0] * bins
    for offer in offer_log:
        index = min(int((offer["rate"] - first) / width + 1e-9), bins - 1)
        if offer["accepted"]:
            accepted[index] += 1
        else:
            declined[index] += 1
    result.update({"edges": edges, "accepted": accepted, "declined": declined})
    return result


def count_ticks(max_count, tick_count=5, label_width=6):
    """
    Whole-number y-axis ticks for a chart of counts, from 0 to a little above
    max_count, in steps of 1, 2 or 5 times a power of ten (about tick_count
    ticks), and their labels, padded to label_width so the axis column keeps
    its width as the counts grow.
    """
    max_count = max(int(max_count), 1)
    rough = max_count / max(tick_count - 1, 1)
    power = 10 ** math.floor(math.log10(rough)) if rough >= 1 else 1
    step = next((s * power for s in (1, 2, 5) if s * power >= rough), 10 * power)
    step = max(1, int(step))
    top = step * (max_count // step + 1)
    ticks = list(range(0, top + 1, step))
    return ticks, [str(tick).rjust(label_width) for tick in ticks]


def rate_threshold(controller):
    """A rate:N strategy's N, to mark on the offers histogram; else None."""
    strategy = controller.strategy
    if strategy.offer_rule == OfferRule.RATE:
        return strategy.threshold
    return None


def _money(value):
    return "-" if value is None else f"{value:.2f}"


def _share(value):
    return "  -  " if value is None else f"{value:5.2f}"


def performance_lines(controller):
    """
    The relative-performance panel, as (text, style) pairs: style is None,
    or "lead" / "lag" for the line comparing the car's net income with the
    fleet's. Before the shift starts, a warm-up countdown.
    """
    unit = "hour" if controller.per_hour else "block"
    name = controller.strategy.name(per_hour=controller.per_hour)
    if not controller.active:
        start = controller.shift_start
        return [
            (f"Strategy: {name}", None),
            (f"Warm-up: block {controller.sim.block_index} of {start}.", None),
            (
                f"The car is seated at block {start}; "
                "the figures and charts start then.",
                None,
            ),
        ]
    if controller.shift_blocks is None:
        progress = f"block {controller.shift_block} of an open-ended shift"
    else:
        progress = f"block {controller.shift_block} of {controller.shift_blocks}"
    if controller.shift_start:
        progress += f" (seated at block {controller.shift_start})"
    car = controller.summary()
    fleet = controller.fleet_summary()
    cars = fleet["mean_vehicles"]
    fleet_label = f"Fleet ({cars:.0f})" if cars else "Fleet"
    width = max(len("Car"), len(fleet_label))
    lines = [
        (f"Strategy: {name}", None),
        (f"Shift: {progress}; incomes per {unit}", None),
        (
            f"{'':<{width}}  {'gross':>7} {'net':>7} {'surplus':>7}   "
            f"{'P1':>5} {'P2':>5} {'P3':>5} {'parked':>6}",
            None,
        ),
    ]
    for label, row in (("Car", car), (fleet_label, fleet)):
        lines.append(
            (
                f"{label:<{width}}  {_money(row['gross_income']):>7} "
                f"{_money(row['net_income']):>7} {_money(row['surplus']):>7}   "
                f"{_share(row['fraction_p1'])} {_share(row['fraction_p2'])} "
                f"{_share(row['fraction_p3'])} "
                f"{_share(row['fraction_parked']):>6}",
                None,
            )
        )
    car_net, fleet_net = car["net_income"], fleet["net_income"]
    if car_net is not None and fleet_net is not None:
        lead = car_net - fleet_net
        text = f"Car vs fleet, net: {lead:+.2f} per {unit}"
        if fleet_net > 0:
            text += f" ({lead / fleet_net:+.0%})"
        lines.append((text, "lead" if lead >= 0 else "lag"))
    offers = car["offers"]
    acceptance = f"{car['accepts'] / offers:.0%}" if offers else "-"
    idle = car["idle_per_accept"]
    idle_unit = "min" if controller.per_hour else "blocks"
    idle_text = "-" if idle is None else f"{idle:.1f} {idle_unit}"
    lines.append(
        (f"Offers {offers}, accepted {acceptance}, idle {idle_text} per trip", None)
    )
    return lines


def series_points(series, max_points=400):
    """
    (x, y) lists for a series of (block, value) pairs (blocks of the shift,
    counted from 1, as BlockSeries.points() gives them), leaving out blocks
    with no value, and keeping at most about max_points evenly spaced points
    (always the last).
    """
    points = [(x, v) for x, v in series if v is not None]
    if len(points) > max_points:
        step = math.ceil(len(points) / max_points)
        points = points[::step] + ([points[-1]] if (len(points) - 1) % step else [])
    return [x for x, _ in points], [y for _, y in points]


def strategy_line(controller):
    """
    A one-line summary of the seated car against the fleet, for the strip
    under terminal_map, as (text, style): style is "lead" or "lag" once
    there is a net income to compare, else None.
    """
    name = controller.strategy.name(per_hour=controller.per_hour)
    if not controller.active:
        return (
            f"Seated car ({name}): warm-up, block {controller.sim.block_index}; "
            f"seated at block {controller.shift_start}",
            None,
        )
    unit = "hr" if controller.per_hour else "block"
    car = controller.summary()
    fleet = controller.fleet_summary()
    offers = car["offers"]
    accepted = (
        f"accepted {car['accepts']} of {offers} offers" if offers else "no offers yet"
    )
    car_net, fleet_net = car["net_income"], fleet["net_income"]
    if car_net is None or fleet_net is None:
        return (f"Seated car (highlighted), {name}: {accepted}", None)
    lead = car_net - fleet_net
    relative = f" ({lead / fleet_net:+.0%})" if fleet_net > 0 else ""
    text = (
        f"Seated car (highlighted), {name}: net {car_net:.2f}/{unit}, "
        f"fleet {fleet_net:.2f}/{unit}{relative}; {accepted}"
    )
    return (text, "lead" if lead >= 0 else "lag")
