"""
The four bot drivers: each takes offers by a simple rule, and the debrief
compares the player with them.
"""

from dataclasses import dataclass

from ridehail.game.params import MINUTES_PER_HOUR

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
