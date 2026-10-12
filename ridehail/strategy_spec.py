"""
The strategy of the [STRATEGY] configuration section (use_strategy): the
rules one seated car plays by. strategy_offer says which offers it takes,
strategy_idle what it does while idle:

    strategy_offer
    all              take every offer
    rate:N           take offers paying at least N per hour (use_city_scale)
                     or per block, pickup included
    centre           take offers whose drop-off is in the City Centre

    strategy_idle
    cruise           the fleet's idle behaviour (the default)
    park             never move while idle
    moving:P         move in a fraction P of idle blocks

Rule names take a unique prefix ("r:22", "p"). The rule names and their
descriptions are OfferRule and IdleRule in ridehail/atom.py. This module
depends only on atom.py, so config.py can parse the rules; the controller
that plays them is ridehail/game/strategy.py. See
claude/strategy-config-spec.md.
"""

import math
from dataclasses import dataclass

from ridehail.atom import IdleRule, OfferRule


def _number(value):
    """A number as it appears in a spec: 22, not 22.0."""
    return f"{value:g}"


def _match(text, enum_class, part):
    """The member of enum_class named by text or a unique prefix of it."""
    key = text.strip().lower()
    names = [member.value for member in enum_class]
    if key in names:
        return enum_class(key)
    matches = [name for name in names if key and name.startswith(key)]
    if len(matches) == 1:
        return enum_class(matches[0])
    raise ValueError(f"unknown {part} rule '{text}' (choose from {', '.join(names)})")


@dataclass(frozen=True)
class Strategy:
    """One strategy: an offer rule (with its threshold) and an idle rule."""

    offer_rule: OfferRule = OfferRule.ALL
    threshold: float = None
    idle_rule: IdleRule = IdleRule.CRUISE
    moving: float = None

    @property
    def offer(self):
        """The offer rule in canonical form, as configured and reported."""
        if self.offer_rule == OfferRule.RATE:
            return f"rate:{_number(self.threshold)}"
        return self.offer_rule.value

    @property
    def idle(self):
        """The idle rule in canonical form, as configured and reported."""
        if self.idle_rule == IdleRule.MOVING:
            return f"moving:{_number(self.moving)}"
        return self.idle_rule.value

    @property
    def label(self):
        """A short label: the offer rule, then any idle rule but cruise."""
        if self.idle_rule == IdleRule.CRUISE:
            return self.offer
        return f"{self.offer}, {self.idle}"

    def name(self, per_hour=True):
        """A name that explains the rule, like the game's bot names."""
        if self.offer_rule == OfferRule.ALL:
            name = "Takes every offer"
        elif self.offer_rule == OfferRule.CENTRE:
            name = "Takes trips to the City Centre"
        elif per_hour:
            name = f"Takes ${_number(self.threshold)}/hr or more"
        else:
            name = f"Takes {_number(self.threshold)}/block or more"
        if self.idle_rule == IdleRule.PARK:
            name += ", parks when idle"
        elif self.idle_rule == IdleRule.MOVING:
            name += f", moves in {_number(self.moving)} of idle blocks"
        return name

    def accepts(self, offer):
        """offer: a dict with "rate" (pickup included) and "dropoff_zone"."""
        if self.offer_rule == OfferRule.ALL:
            return True
        if self.offer_rule == OfferRule.RATE:
            return offer["rate"] >= self.threshold
        return offer["dropoff_zone"] == "core"

    def apply_idle(self, vehicle):
        """Set the vehicle's own idle behaviour for the shift."""
        if self.idle_rule == IdleRule.PARK:
            vehicle.idle_vehicles_moving = 0.0
        elif self.idle_rule == IdleRule.MOVING:
            vehicle.idle_vehicles_moving = self.moving


def _parse_float(text, what):
    try:
        value = float(text)
    except ValueError:
        raise ValueError(f"{what} '{text}' is not a number") from None
    if not math.isfinite(value) or value < 0:
        raise ValueError(f"{what} '{text}' must be zero or more")
    return value


def _split(text, enum_class, part):
    """A rule and its ':' argument (None if it has none)."""
    name, colon, argument = text.replace(" ", "").partition(":")
    rule = _match(name, enum_class, part)
    return rule, (argument if colon else None)


def parse_offer(text):
    """(OfferRule, threshold) from a strategy_offer value; ValueError if bad."""
    rule, argument = _split(text, OfferRule, "offer")
    if rule == OfferRule.RATE:
        if not argument:
            raise ValueError(f"'{text}': rate needs a threshold, as in rate:22")
        return rule, _parse_float(argument, "rate")
    if argument is not None:
        raise ValueError(f"'{text}': {rule.value} takes no ':' value")
    return rule, None


def parse_idle(text):
    """(IdleRule, moving) from a strategy_idle value; ValueError if bad."""
    rule, argument = _split(text, IdleRule, "idle")
    if rule == IdleRule.MOVING:
        if not argument:
            raise ValueError(f"'{text}': moving needs a fraction, as in moving:1")
        moving = _parse_float(argument, "moving")
        if moving > 1:
            raise ValueError(f"'{text}': moving must be between 0 and 1")
        return rule, moving
    if argument is not None:
        raise ValueError(f"'{text}': {rule.value} takes no ':' value")
    return rule, None


def make_strategy(offer="all", idle="cruise"):
    """A Strategy from strategy_offer and strategy_idle values."""
    return Strategy(*parse_offer(offer), *parse_idle(idle))
