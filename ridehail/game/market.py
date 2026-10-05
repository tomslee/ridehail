"""
The markets and cities a shift can be played in, and the simulation config
and random seed for a shift.
"""

from ridehail.atom import DispatchMethod, Equilibration, TripDistribution
from ridehail.config import RideHailConfig
from ridehail.game.params import KM_PER_BLOCK, MINUTES_PER_HOUR, GameParams

# Markets differ only in demand: the fleet is the same in every market, and
# Busy and Slow have more and fewer trip requests than Normal (claude/game-mode.md
# 1.9 and Part 8). Demand varies through the day and the week; the number of
# drivers responds to it, not the other way round, and with markets that
# differed in fleet size a Slow Tuesday had more cars on the road than a Busy
# Friday. At 0.37 km per block, a 32-block city with a mean trip draw of 16
# blocks reproduces Toronto's trip lengths up to 12 km (10/25/50/75/90%: 1.5
# / 2.6 / 4.4 / 7.0 / 9.2 km against 1.7 / 2.6 / 4.3 / 6.9 / 9.5). Normal's
# demand is scaled with the area from the earlier 24-block city (5 -> 9 per
# minute), and Busy and Slow demand were searched (Part 8) for the earlier
# markets' time split (5.8): Busy undersupplied (P1 ~ 0, about 15% of riders
# give up), Normal P1 ~ 0.2, Slow P1 ~ 0.47. When idle cars started waiting
# where they are half the time (IDLE_VEHICLES_MOVING, Part 13), declining an
# offer got cheaper, and Slow's demand was lowered (6.5 -> 5) until taking
# every offer again did about as well as any price threshold when Slow.
# Idle drivers head towards a place requests come from (mostly the City
# Centre) with this probability at each intersection, rather than always
# cruising at random (claude/idle-vehicles-returning.md; claude/game-mode.md
# Part 11, and 16.11 for the change to a sampled request origin).
IDLE_VEHICLES_RETURNING = 0.25
# An idle car moves (and pays running costs) in only this fraction of
# minutes: in the others it waits where it is, as real drivers often park
# rather than cruise (claude/game-mode.md Part 13).
IDLE_VEHICLES_MOVING = 0.5
MARKET_SHARED = {
    "city_size": 32,
    "vehicle_count": 215,
    "mean_trip_distance": 16,
    "inhomogeneity": 0.5,
}
MARKETS = {
    "busy": {"label": "Busy Friday", "base_demand": 11.0},
    "normal": {"label": "Normal", "base_demand": 9.0},
    "slow": {"label": "Slow Tuesday", "base_demand": 5.0},
}
# The big city (hidden in the web lab: "+" on the setup screen) is 48 blocks
# (17.8 km) across, so the city-size cap on trip lengths no longer cuts off
# Toronto's long trips (the 32-block city loses about a tenth of its trip
# draws to the cap). The mean trip draw is unchanged. The fleet is 6000
# cars, roughly Toronto's; Normal's demand and the other markets' demand were
# searched for the same time split as the 32-block markets (P1 / P2 / P3,
# riders giving up): Busy 0 / 0.31 / 0.69, ~15%; Normal 0.19 / 0.22 / 0.59;
# Slow 0.46 / 0.12 / 0.42. Pickups are a little shorter than in the 32-block
# city. With IDLE_VEHICLES_MOVING, Slow was cut by the same fraction as the
# 32-block city's (170 -> 130), keeping its P1 a little above that city's
# (0.65 against 0.63).
CITIES = ("standard", "big")
BIG_CITY_SHARED = {
    "city_size": 48,
    "vehicle_count": 6000,
    "mean_trip_distance": 16,
    "inhomogeneity": 0.5,
}
BIG_CITY_DEMAND = {"busy": 330.0, "normal": 240.0, "slow": 130.0}


def market_settings(market, city="standard"):
    """City size, demand, trip length, inhomogeneity and fleet for a market."""
    if market not in MARKETS:
        raise ValueError(f"Unknown market '{market}'. Choose from {list(MARKETS)}")
    if city == "standard":
        return {**MARKET_SHARED, **MARKETS[market]}
    if city == "big":
        return {
            **BIG_CITY_SHARED,
            **MARKETS[market],
            "base_demand": BIG_CITY_DEMAND[market],
        }
    raise ValueError(f"Unknown city '{city}'. Choose from {list(CITIES)}")


def make_game_config(
    market="normal",
    seed=1,
    shift_blocks=180,
    warmup_blocks=60,
    city="standard",
    max_wait_time=GameParams.max_wait_minutes,
):
    """A RideHailConfig for a game market: Simple mode, fixed fleet and demand.
    Riders give up after max_wait_time blocks (minutes) without a car."""
    settings = market_settings(market, city)
    config = RideHailConfig(use_config_file=False)
    config.animation.value = "none"
    config.run_sequence.value = False
    config.interpolate.value = 0
    config.city_size.value = settings["city_size"]
    config.vehicle_count.value = settings["vehicle_count"]
    config.base_demand.value = settings["base_demand"]
    config.mean_trip_distance.value = settings["mean_trip_distance"]
    config.inhomogeneity.value = settings["inhomogeneity"]
    config.inhomogeneous_destinations.value = False
    config.trip_distance_distribution.value = TripDistribution.GAMMA
    config.idle_vehicles_moving.value = IDLE_VEHICLES_MOVING
    config.idle_vehicles_returning.value = IDLE_VEHICLES_RETURNING
    config.pickup_time.value = 1
    config.max_wait_time.value = max_wait_time
    config.equilibration.value = Equilibration.NONE
    config.dispatch_method.value = DispatchMethod.DEFAULT
    config.use_city_scale.value = False
    config.minutes_per_block.value = 1.0
    config.mean_vehicle_speed.value = KM_PER_BLOCK * MINUTES_PER_HOUR
    config.time_blocks.value = shift_blocks + warmup_blocks
    # The simulation seeds the global RNG only for a truthy seed
    config.random_number_seed.value = int(seed) or 1
    return config


def shift_seed(code, market, city="standard"):
    """
    A stable, non-zero 31-bit seed from a shift code and market (FNV-1a).
    The standard city's seeds are unchanged from before the big city.
    """
    key = f"{code}|{market}" if city == "standard" else f"{code}|{market}|{city}"
    h = 0x811C9DC5
    for byte in key.encode():
        h = ((h ^ byte) * 0x01000193) & 0xFFFFFFFF
    return (h & 0x7FFFFFFF) | 1
