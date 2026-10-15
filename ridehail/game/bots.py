"""
The four bot drivers: each takes offers by a simple rule, and the debrief
compares the player with them. The rules are individual strategies
(ridehail/strategy_spec.py), the ones use_strategy plays, and each bot is
named for its rule, so the debrief needs no other explanation.
"""

from dataclasses import dataclass, field

from ridehail.strategy_spec import Strategy, make_strategy

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
    # The bot's key, used by the debrief and the scripts in utils/
    key: str
    # Its rule, as a strategy_offer value
    offer_rule: str
    strategy: Strategy = field(init=False)

    def __post_init__(self):
        self.strategy = make_strategy(self.offer_rule)

    @property
    def name(self):
        return self.strategy.name(per_hour=True)

    def accepts(self, offer):
        """
        offer: the game's offer dict (GameController.describe_offer), whose
        "rate" is $/hr, pickup included, and "dropoff_zone" is core or
        outskirts. The City Centre rule is destination-driven: requests come
        mostly from the City Centre (inhomogeneity), so ending a trip there
        means a quick next offer, while idle cars collect in the outskirts
        (claude/game-mode.md 5.7, Part 9 and 10.6).
        """
        return self.strategy.accepts(offer)


BOTS = [
    Bot("yes", "all"),
    Bot("hourly_low", f"rate:{BOT_HOURLY_LOW}"),
    Bot("hourly_high", f"rate:{BOT_HOURLY_HIGH}"),
    Bot("centre", "centre"),
]
