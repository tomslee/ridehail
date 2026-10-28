"""
Named starting-point configurations ("presets") for the ridehail simulation.

A preset is a complete set of geometry and economic parameters that make a good
starting point for experimentation at a given scale: a small Village, a mid-size
Town, or a large City. Selecting a preset on the command line (``--preset town``)
is an alternative to supplying a config file; it fills in the parameters below and
leaves everything else at its default.

Like the web lab, a preset only sets *starting values*. The mode
(``use_city_scale``, i.e. Costs & Incomes) and equilibration (``equilibration``,
i.e. Free Entry & Exit) remain independent flags, so the four operating regimes
are reached by combining a preset with those flags, e.g.::

    python -m ridehail --preset village              # Simple, no equilibration
    python -m ridehail --preset village -ucs         # Costs & Incomes
    python -m ridehail --preset village -e price      # Free Entry & Exit
    python -m ridehail --preset town -ucs -e price    # both

IMPORTANT: these values are the source-of-truth mirror of the web lab presets in
``docs/lab/js/config.js`` (``PRESET_VALUES`` plus the shared economic parts of
``SLIDER_CONFIG``). Keep the two in sync until Phase 2 has the web app read these
values from Python via ``worker.py``. See the preset-calibration notes.
"""

# Toronto-calibrated economics shared by all presets. These mirror the shared
# (non-per-preset) values in docs/lab/js/config.js SLIDER_CONFIG. They differ
# from the bare config.py defaults, which is why a preset must set them
# explicitly rather than relying on defaults.
PRESET_SHARED = {
    "price": 1.2,
    "platform_commission": 0.25,
    "reservation_wage": 0.35,
    "per_km_price": 0.80,
    "per_minute_price": 0.18,
    "base_fare": 3.0,
    "per_km_ops_cost": 0.3,
    "mean_vehicle_speed": 30.0,
    "minutes_per_block": 1.0,
}

# Per-preset geometry and entry/exit economics. These mirror PRESET_VALUES in
# docs/lab/js/config.js. Geometry satisfies the phase relation
# P3 = base_demand * mean_trip_distance / vehicle_count (mean_trip_distance =
# city_size / 2). per_hour_opportunity_cost decreases with city size to offset
# the fixed base fare, which is a larger share of short (Village) fares.
#
# The Village is deliberately a sparse case: 6 vehicles in an 8x8 grid, which
# settles near P1 ~= 0.34, P3 ~= 0.34 with a high but bounded wait fraction and
# stays stable (P1 > 0) across all four mode/equilibration combinations.
PRESETS = {
    "village": {
        "city_size": 8,
        "vehicle_count": 6,
        "base_demand": 0.5,
        "mean_trip_distance": 4,
        "inhomogeneity": 0.0,
        "per_hour_opportunity_cost": 13.0,
    },
    "town": {
        "city_size": 24,
        "vehicle_count": 120,
        "base_demand": 5.0,
        "mean_trip_distance": 12,
        "inhomogeneity": 0.5,
        "per_hour_opportunity_cost": 6.0,
    },
    "city": {
        "city_size": 48,
        "vehicle_count": 1200,
        "base_demand": 24.0,
        "mean_trip_distance": 24,
        "inhomogeneity": 0.5,
        "per_hour_opportunity_cost": 4.0,
    },
}

# Ordered list of preset names, for command-line choices and help text.
PRESET_NAMES = list(PRESETS)

# The "Just One More Shift…" game's cities (command line only; the web lab's
# presets are PRESET_NAMES). The values come from ridehail/game/market.py,
# so the game and these presets can't drift apart: see game_preset().
GAME_PRESET_DESCRIPTIONS = {
    "game": "the game's city (Normal demand), one car seated (use_strategy)",
    "game-big": "the game's big city (Normal demand), one car seated (use_strategy)",
}
GAME_PRESET_NAMES = list(GAME_PRESET_DESCRIPTIONS)

# Real cities, calibrated outside this repository, named <city>-<calibration>
# (toronto-2026; later perhaps toronto-2026-8am, chicago-2025). Each entry:
#   title: the web lab's preset title ("<title> (Preset)")
#   map_view: the map view (docs/lab/maps/) the web lab switches on with the
#     preset, shared by every calibration of a city; None for none
#   description: for --preset help
#   source: where the calibration lives
#   settings: config parameters, over PRESET_SHARED
# Simple mode (no use_city_scale): the calibrations set no prices, and Simple
# mode gives the same dynamics. The shared economics (PRESET_SHARED) and the
# City's opportunity cost keep the income charts comparable with the City's.
CITY_PRESETS = {
    "toronto-2026": {
        "title": "Toronto 2026",
        "map_view": "toronto",
        "description": "Toronto, all day 2026 (calibrated): 48x48 city, 5757 vehicles",
        # The all-day 2026 calibration (Tier 1). Reproduces P1/P2/P3 =
        # 0.33/0.14/0.53 and a mean wait of 4.7 minutes (2026-10-28).
        # min_trip_distance matters: without it P3 rises to 0.55.
        "source": "ridehail-toronto simulation/toronto_2026.config",
        "settings": {
            "city_size": 48,
            "vehicle_count": 5757,
            "base_demand": 172.561,
            "inhomogeneity": 0.3938,
            "inhomogeneous_destinations": False,
            "min_trip_distance": 2,
            "mean_trip_distance": 18,
            "pickup_time": 1,
            "idle_vehicles_moving": 1.0,
            "per_hour_opportunity_cost": 4.0,
        },
    },
}
CITY_PRESET_DESCRIPTIONS = {
    name: preset["description"] for name, preset in CITY_PRESETS.items()
}
CITY_PRESET_NAMES = list(CITY_PRESETS)
ALL_PRESET_NAMES = PRESET_NAMES + CITY_PRESET_NAMES + GAME_PRESET_NAMES


def game_preset(name):
    """
    The game's city as config parameters: its market settings (Normal
    demand) in City-scale mode, with one car seated (use_strategy; its
    strategy is set with -so and -si). The fare is the game's driver rate
    card, and upfront offers vary around it as Toronto offers do
    (offer_variability). The shift is the last results_window blocks, after
    the game's warm-up.
    See claude/strategy-config-spec.md.
    """
    # Imported here: ridehail.game imports the simulation, which imports
    # the config, which imports this module
    from ridehail.game import market
    from ridehail.game.params import MINUTES_PER_HOUR, GameParams

    params = GameParams()
    settings = market.market_settings(
        "normal", "big" if name == "game-big" else "standard"
    )
    return {
        "city_size": settings["city_size"],
        "vehicle_count": settings["vehicle_count"],
        "base_demand": settings["base_demand"],
        "mean_trip_distance": settings["mean_trip_distance"],
        "inhomogeneity": settings["inhomogeneity"],
        "inhomogeneous_destinations": False,
        "trip_distance_distribution": "gamma",
        "idle_vehicles_moving": market.IDLE_VEHICLES_MOVING,
        "idle_vehicles_returning": market.IDLE_VEHICLES_RETURNING,
        "pickup_time": 1,
        "max_wait_time": params.max_wait_minutes,
        "equilibration": "none",
        "demand_elasticity": 0.0,
        "use_city_scale": True,
        "minutes_per_block": params.minutes_per_block,
        "mean_vehicle_speed": round(params.km_per_block * MINUTES_PER_HOUR, 6),
        "per_km_ops_cost": params.ops_cost_per_km,
        # The fare is the game's driver rate card, with no commission: the
        # driver is paid the rate card for the trip (the pickup is unpaid)
        "base_fare": params.rate_base,
        "per_km_price": params.rate_per_km,
        "per_minute_price": params.rate_per_min,
        "platform_commission": 0.0,
        "time_blocks": params.warmup_blocks + params.shift_blocks,
        "results_window": params.shift_blocks,
        "use_strategy": True,
        # Upfront offers vary around the rate card as offers to Toronto
        # drivers do (claude/upfront-pricing-spec.md)
        "offer_variability": 0.31,
    }


def get_preset(name):
    """
    Return the full parameter dict for a named preset.

    Merges the shared economics with the per-preset geometry. Keys are
    ridehail config parameter names (snake_case), ready to be applied to
    RideHailConfig ConfigItems.

    Args:
        name: One of ALL_PRESET_NAMES ("village", "town", "city",
            "toronto-2026", "game", "game-big").

    Returns:
        A new dict mapping config parameter name -> value.

    Raises:
        ValueError: if name is not a known preset.
    """
    if name in GAME_PRESET_NAMES:
        return game_preset(name)
    if name in CITY_PRESETS:
        return {**PRESET_SHARED, **CITY_PRESETS[name]["settings"]}
    if name not in PRESETS:
        raise ValueError(
            f"Unknown preset '{name}'. Choose from: {', '.join(ALL_PRESET_NAMES)}"
        )
    return {**PRESET_SHARED, **PRESETS[name]}
