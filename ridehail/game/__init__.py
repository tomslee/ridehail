"""
Game mode: "Just One More Shift…".

The player drives one car in a fixed-fleet simulation. When the dispatcher
picks the player's car for a trip, the trip becomes an *offer* at an upfront
price, and the player accepts or declines it. At the end of the shift the
player's net earnings per hour are compared with four rule-following bot
drivers and with the rest of the fleet (who accept everything).

This package holds all the game logic, so that it can be tested and
calibrated headless; the web lab (docs/lab/worker.py) only renders it and
forwards the player's decisions. See claude/game-design.md for the design
as it is now, and claude/game-mode.md (the dated log) for its history.

- params: units and calibratable constants (GameParams)
- market: markets, cities, the simulation config and seed for a shift
- bots: the bot drivers
- offer_model: the fitted offer-price model (generated; do not edit)
- pricing: offer prices and rider fares (OfferPricing)
- controller: the shift itself (GameController, Ledger)
- report: the end-of-shift debrief

Scale: one block is one minute and KM_PER_BLOCK = 0.37 km (22 km/h), so trip
time and distance are proportional. 22 km/h is a typical speed for Toronto
trips under 12 km (claude/game-mode.md, 5.8); a 32-block city is 11.8 km
across. Money is computed here, not by the simulation's Costs & Incomes mode,
which stays off.
"""

from ridehail.game.bots import BOT_HOURLY_HIGH, BOT_HOURLY_LOW, BOTS, Bot
from ridehail.game.controller import GameController, Ledger
from ridehail.game.market import (
    CITIES,
    IDLE_VEHICLES_MOVING,
    IDLE_VEHICLES_RETURNING,
    MARKETS,
    make_game_config,
    market_settings,
    shift_seed,
)
from ridehail.game.params import (
    CARDS,
    HST_RATE,
    KM_PER_BLOCK,
    MIN_FLEET_MINUTES,
    MINUTES_PER_HOUR,
    GameParams,
)
from ridehail.game.pricing import OfferPricing
from ridehail.simulation import RideHailSimulation

__all__ = [
    "BOT_HOURLY_HIGH",
    "BOT_HOURLY_LOW",
    "BOTS",
    "Bot",
    "CARDS",
    "CITIES",
    "GameController",
    "GameParams",
    "HST_RATE",
    "IDLE_VEHICLES_MOVING",
    "IDLE_VEHICLES_RETURNING",
    "KM_PER_BLOCK",
    "Ledger",
    "MARKETS",
    "MIN_FLEET_MINUTES",
    "MINUTES_PER_HOUR",
    "OfferPricing",
    "create_game",
    "make_game_config",
    "market_settings",
    "shift_seed",
]


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
