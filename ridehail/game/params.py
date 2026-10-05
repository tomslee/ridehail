"""
Units and calibratable constants for game mode, shared by the other modules.
"""

from dataclasses import dataclass

MINUTES_PER_HOUR = 60.0
# One block: one minute, and this many km (22 km/h)
KM_PER_BLOCK = 0.37
# Fleet cars that were on shift for less than this are left out of the
# comparison group (too short a window to compare with a whole shift)
MIN_FLEET_MINUTES = 60
# Ontario HST, included in the City's fares
HST_RATE = 0.13


@dataclass
class GameParams:
    """Calibratable constants (see claude/game-mode.md, sections 1.4 and 1.9)."""

    km_per_block: float = KM_PER_BLOCK
    minutes_per_block: float = 1.0
    # Driver rate card, for the trip only: a reference for comparing offers
    # (offers themselves come from ridehail.game.offer_model)
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
