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


def get_preset(name):
    """
    Return the full parameter dict for a named preset.

    Merges the shared economics with the per-preset geometry. Keys are
    ridehail config parameter names (snake_case), ready to be applied to
    RideHailConfig ConfigItems.

    Args:
        name: One of PRESET_NAMES ("village", "town", "city").

    Returns:
        A new dict mapping config parameter name -> value.

    Raises:
        ValueError: if name is not a known preset.
    """
    if name not in PRESETS:
        raise ValueError(
            f"Unknown preset '{name}'. Choose from: {', '.join(PRESET_NAMES)}"
        )
    return {**PRESET_SHARED, **PRESETS[name]}
