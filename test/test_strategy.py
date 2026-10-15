"""
Tests for the individual strategy from the configuration: use_strategy and
the [STRATEGY] section (ridehail/strategy_spec.py, ridehail/game/strategy.py;
claude/strategy-config-spec.md), the game presets, and the [SEQUENCE]
additions (request_rate_values, sequence_repeats).
"""

import configparser
import csv
import logging
import math
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from ridehail.atom import IdleRule, Measure, OfferRule, VehiclePhase
from ridehail.config import ConfigValidationError, FloatList, RideHailConfig
from ridehail.game import make_game_config
from ridehail.game.strategy import format_summary
from ridehail.presets import GAME_PRESET_NAMES, get_preset
from ridehail.results import RideHailSimulationResults
from ridehail.sequence import RideHailSimulationSequence, sequence_values
from ridehail.simulation import RideHailSimulation
from ridehail.strategy_spec import make_strategy, parse_idle, parse_offer

logging.disable(logging.CRITICAL)


def make_config(preset=None, **values):
    """A validated config from an optional preset plus overrides."""
    config = RideHailConfig(use_config_file=False)
    config.animation.value = "none"
    for name, value in {**(get_preset(preset) if preset else {}), **values}.items():
        item = getattr(config, name)
        item.value = value
        item.explicitly_set = True
    config._convert_config_values_to_enum()
    config._set_parameter_defaults()
    config._validate_all_config_parameters()
    return config


def play(config):
    """Run a simulation for time_blocks blocks."""
    sim = RideHailSimulation(config)
    for _ in range(sim.time_blocks):
        sim.next_block()
    return sim


# ---------------------------------------------------------------------------
# Strategy specs
# ---------------------------------------------------------------------------


def test_rule_parsing():
    strategy = make_strategy("R:22.0", "p")
    assert (strategy.offer, strategy.idle) == ("rate:22", "park")
    assert strategy.offer_rule == OfferRule.RATE
    assert strategy.threshold == 22
    assert strategy.idle_rule == IdleRule.PARK
    assert make_strategy("cen", "mov : 0.5").idle == "moving:0.5"
    assert make_strategy().label == "all"
    assert make_strategy("rate:30", "park").label == "rate:30, park"


@pytest.mark.parametrize(
    "offer",
    [
        "sometimes",
        "",
        "rate",
        "rate:",
        "rate:x",
        "rate:-3",
        "all:3",
        "park",
        "all/park",
    ],
)
def test_bad_offer_rules(offer):
    with pytest.raises(ValueError):
        parse_offer(offer)


@pytest.mark.parametrize(
    "idle", ["", "moving", "moving:2", "park:1", "cruise:", "all", "park/all"]
)
def test_bad_idle_rules(idle):
    with pytest.raises(ValueError):
        parse_idle(idle)


def test_rules():
    rate = make_strategy("rate:30")
    centre = make_strategy("centre")
    assert rate.accepts({"rate": 30.0, "dropoff_zone": "outskirts"})
    assert not rate.accepts({"rate": 29.9, "dropoff_zone": "core"})
    assert centre.accepts({"rate": 0.0, "dropoff_zone": "core"})
    assert not centre.accepts({"rate": 99.0, "dropoff_zone": "outskirts"})
    vehicle = SimpleNamespace(idle_vehicles_moving=0.5)
    make_strategy(idle="park").apply_idle(vehicle)
    assert vehicle.idle_vehicles_moving == 0.0
    make_strategy(idle="moving:0.8").apply_idle(vehicle)
    assert vehicle.idle_vehicles_moving == 0.8
    make_strategy(idle="cruise").apply_idle(vehicle)
    assert vehicle.idle_vehicles_moving == 0.8


def test_float_list_writes_as_text():
    assert str(FloatList("100, 130,160.5")) == "100, 130, 160.5"


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def test_defaults():
    config = make_config(use_strategy=True, time_blocks=100)
    assert config.strategy_offer.value == "all"
    assert config.strategy_idle.value == "cruise"


def test_strategy_is_canonical():
    config = make_config(
        use_strategy=True,
        time_blocks=100,
        strategy_offer="R:1.50",
        strategy_idle="mov:1",
    )
    assert config.strategy_offer.value == "rate:1.5"
    assert config.strategy_idle.value == "moving:1"


@pytest.mark.parametrize(
    "values",
    [
        {"equilibration": "price"},
        {"time_blocks": 0},
        {"time_blocks": 50, "results_window": 50},
        {"vehicle_count": 1},
        {"impulse_list": [{"block": 10, "vehicle_count": 20}]},
        {"strategy_offer": "sometimes"},
        {"strategy_idle": "rate:3"},
    ],
)
def test_validation(values):
    with pytest.raises(ConfigValidationError):
        make_config(**{"use_strategy": True, "time_blocks": 100, **values})


def test_strategy_settings_ignored_without_use_strategy():
    config = make_config(strategy_offer="centre", strategy_idle="park")
    assert RideHailSimulation(config).strategy_controller is None


# ---------------------------------------------------------------------------
# The game presets
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", GAME_PRESET_NAMES)
def test_game_presets_match_the_game(name):
    """The presets come from ridehail/game/market.py: same city, same market."""
    game = make_game_config(
        "normal", 1, 180, 60, "big" if name == "game-big" else "standard"
    )
    config = make_config(name)
    same = [
        "city_size",
        "vehicle_count",
        "base_demand",
        "mean_trip_distance",
        "inhomogeneity",
        "inhomogeneous_destinations",
        "trip_distance_distribution",
        "idle_vehicles_moving",
        "idle_vehicles_returning",
        "pickup_time",
        "max_wait_time",
        "equilibration",
        "minutes_per_block",
        "mean_vehicle_speed",
        "time_blocks",
        "dispatch_method",
    ]
    for key in same:
        assert getattr(config, key).value == getattr(game, key).value, key
    assert config.results_window.value == 180
    assert config.use_city_scale.value and config.use_strategy.value
    # The fare is the game's driver rate card, with no commission
    assert config.base_fare.value == 2.50 and config.per_km_price.value == 0.75
    assert config.platform_commission.value == 0.0
    # Upfront offers vary as Toronto offers do
    assert config.offer_variability.value == 0.31


def test_city_scale_leaves_the_game_city_unchanged():
    """
    The game presets use City-scale mode for km and minutes. With one minute
    per block and no demand elasticity, the city plays out exactly as in the
    game's Simple mode (claude/strategy-config-spec.md 5.3).
    """
    runs = []
    for use_city_scale in (False, True):
        config = make_game_config("normal", 12345, 60, 30)
        config.use_city_scale.value = use_city_scale
        sim = RideHailSimulation(config)
        history = []
        for _ in range(90):
            sim.next_block()
            history.append(
                (
                    tuple((tuple(v.location), v.phase) for v in sim.vehicles),
                    sim.next_trip_id,
                )
            )
        runs.append(history)
    assert runs[0] == runs[1]


# ---------------------------------------------------------------------------
# Playing a shift
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def game_shift():
    # No offer variability, so the car's income is the core's formula
    return play(
        make_config(
            "game",
            random_number_seed=11,
            strategy_offer="rate:30",
            offer_variability=0.0,
        )
    )


def test_shift(game_shift):
    controller = game_shift.strategy_controller
    assert controller.shift_start == 60
    assert controller.shift_block == 180 and controller.shift_over
    assert sum(controller.blocks.values()) == 180
    assert controller.offers > controller.accepts > 0


def test_summary_uses_the_core_formulas(game_shift):
    sim = game_shift
    summary = sim.strategy_controller.summary()
    # (p3 and fraction_parked are rounded to 3 places, so the recomputed
    # incomes match only to a few cents an hour)
    assert 0 < summary["accepts"] < summary["offers"]
    assert summary["p1"] + summary["p2"] + summary["p3"] == pytest.approx(1.0, abs=2e-3)
    per_hour = 60 / sim.minutes_per_block
    gross = sim.price * (1 - sim.platform_commission) * summary["p3"] * per_hour
    assert summary["gross_income"] == pytest.approx(gross, abs=0.05)
    running = sim.ops_cost * (1 - summary["fraction_parked"]) * per_hour
    assert summary["net_income"] == pytest.approx(gross - running, abs=0.05)
    assert summary["surplus"] == pytest.approx(
        summary["net_income"] - sim.reservation_wage * per_hour, abs=0.05
    )
    for removed in ("net_rate", "earnings", "costs", "fleet_net_rate"):
        assert removed not in summary
    text = format_summary(sim.strategy_controller)
    assert "Takes $30/hr or more" in text and "Fleet (215 cars)" in text


def test_take_every_offer_matches_the_fleet():
    """A car that takes every offer and cruises is measured like the fleet."""
    nets = []
    for seed in range(1, 6):
        sim = play(make_config("game", random_number_seed=seed, offer_variability=0.0))
        nets.append(sim.strategy_controller.summary()["net_income"])
        measures = RideHailSimulationResults(sim).get_result_measures()
    fleet = measures[Measure.VEHICLE_NET_INCOME.name]
    assert sum(nets) / len(nets) == pytest.approx(fleet, rel=0.25)


def test_end_state_carries_the_strategy(game_shift):
    end_state = RideHailSimulationResults(game_shift).get_end_state()
    assert end_state["strategy"]["net_income"] is not None
    assert "fraction_parked" in end_state["strategy"]


def test_parked_car_saves_running_costs():
    sim = play(make_config("game", random_number_seed=4, strategy_idle="park"))
    summary = sim.strategy_controller.summary()
    assert sim.vehicles[sim.strategy_controller.seat].idle_vehicles_moving == 0.0
    # Every idle block of the shift is parked (a car is idle when it arrives
    # at a drop-off, but moves only when it has a trip)
    assert summary["fraction_parked"] > 0
    assert summary["fraction_parked"] <= summary["p1"] + 0.01
    assert summary["gross_income"] - summary["net_income"] < (
        sim.ops_cost * 60 / sim.minutes_per_block
    )


def test_simple_mode_fares():
    """Simple mode: offers are price per trip block, less commission."""
    config = make_config(
        use_strategy=True,
        city_size=16,
        vehicle_count=40,
        base_demand=3.0,
        price=2.0,
        platform_commission=0.25,
        per_block_ops_cost=0.1,
        time_blocks=200,
        results_window=150,
        random_number_seed=3,
    )
    sim = play(config)
    controller = sim.strategy_controller
    assert controller.rate_unit == "block"
    # A trip pays price per block, less the commission; pickups are unpaid
    trip = SimpleNamespace(index=1, distance=4, destination=[0, 0])
    offer = controller.describe_offer(trip, 4)
    assert offer["offer"] == pytest.approx(2.0 * 4 * 0.75)
    assert offer["rate"] == pytest.approx(6.0 / 8)
    summary = controller.summary()
    assert summary["gross_income"] == pytest.approx(1.5 * summary["p3"], abs=1e-3)
    assert summary["net_income"] == pytest.approx(
        summary["gross_income"] - 0.1 * (1 - summary["fraction_parked"]), abs=1e-3
    )


# ---------------------------------------------------------------------------
# Upfront pricing (claude/upfront-pricing-spec.md)
# ---------------------------------------------------------------------------


def _controller(**values):
    """A seated car in a small Simple-mode city, not yet run."""
    config = make_config(
        **{
            "use_strategy": True,
            "city_size": 16,
            "vehicle_count": 40,
            "base_demand": 3.0,
            "price": 2.0,
            "platform_commission": 0.25,
            "time_blocks": 200,
            "results_window": 150,
            "random_number_seed": 3,
            **values,
        }
    )
    return RideHailSimulation(config).strategy_controller


def test_offer_factor_has_mean_one_and_the_given_spread():
    controller = _controller(offer_variability=0.31)
    logs = [math.log(controller.offer_factor(i)) for i in range(20000)]
    factors = [math.exp(x) for x in logs]
    assert statistics.fmean(factors) == pytest.approx(1.0, abs=0.01)
    assert statistics.pstdev(logs) == pytest.approx(0.31, abs=0.01)
    # Right-skewed: the median factor is below the mean
    assert statistics.median(factors) < 0.97


def test_offer_factor_is_fixed_per_trip_and_seed():
    a = _controller(offer_variability=0.31)
    b = _controller(offer_variability=0.31)
    order = [5, 1, 9, 1, 5]
    assert [a.offer_factor(i) for i in order] == [
        b.offer_factor(i) for i in reversed(order)
    ][::-1]
    assert a.offer_factor(1) == a.offer_factor(1)
    assert a.offer_factor(1) != a.offer_factor(2)
    other_seed = _controller(offer_variability=0.31, random_number_seed=4)
    assert other_seed.offer_factor(1) != a.offer_factor(1)
    # No variability: the flat fare
    assert _controller().offer_factor(1) == 1.0


def test_offers_carry_the_trip_factor():
    controller = _controller(offer_variability=0.5)
    trip = SimpleNamespace(index=7, distance=4, destination=[0, 0])
    offer = controller.describe_offer(trip, 4)
    m = controller.offer_factor(7)
    assert offer["offer"] == pytest.approx(2.0 * 0.75 * 4 * m)
    assert offer["rate"] == pytest.approx(2.0 * 0.75 * 4 * m / 8)


def test_variability_leaves_the_city_unchanged():
    """The factors have their own generator: the simulation runs the same."""
    runs = []
    for sigma in (0.0, 0.31):
        sim = play(
            make_config(
                "game",
                random_number_seed=6,
                time_blocks=100,
                results_window=60,
                offer_variability=sigma,
            )
        )
        runs.append([(tuple(v.location), v.phase) for v in sim.vehicles])
    assert runs[0] == runs[1]


def test_choosy_car_earns_more_per_rider_block():
    """
    With varying offers, a car that declines poor ones earns more than the
    rate card in its blocks with a rider; taking every offer averages out.
    """
    per_rider_block = {}
    for offer_rule in ("all", "rate:1.2"):
        totals = []
        for seed in range(1, 4):
            sim = play(
                make_config(
                    use_strategy=True,
                    city_size=16,
                    vehicle_count=30,
                    base_demand=3.0,
                    price=2.0,
                    platform_commission=0.25,
                    time_blocks=500,
                    results_window=400,
                    random_number_seed=seed,
                    offer_variability=0.31,
                    strategy_offer=offer_rule,
                )
            )
            controller = sim.strategy_controller
            totals.append(controller.earnings / controller.blocks[VehiclePhase.P3])
        per_rider_block[offer_rule] = statistics.fmean(totals)
    rate_card = 2.0 * 0.75
    assert per_rider_block["all"] == pytest.approx(rate_card, rel=0.1)
    assert per_rider_block["rate:1.2"] > 1.1 * rate_card


def test_restart_reseats():
    config = make_config(
        "game", random_number_seed=5, time_blocks=80, results_window=40
    )
    sim = RideHailSimulation(config)
    for _ in range(70):
        sim.next_block()
    first = sim.strategy_controller
    sim._restart_simulation()
    assert sim.strategy_controller is not first
    assert not sim.strategy_controller.active
    assert sim.strategy_controller.shift_block == 0
    assert sim.dispatcher.offline == frozenset([sim.strategy_controller.seat])


def test_seated_car_is_idle_when_the_shift_starts():
    config = make_config(
        "game", random_number_seed=8, time_blocks=80, results_window=20
    )
    sim = RideHailSimulation(config)
    controller = sim.strategy_controller
    for _ in range(controller.shift_start):
        sim.next_block()
    assert controller.vehicle.phase == VehiclePhase.P1


# ---------------------------------------------------------------------------
# Sequences and the command line
# ---------------------------------------------------------------------------


def test_request_rate_values_and_repeats():
    config = make_config(
        run_sequence=True,
        request_rate_values=FloatList("100, 130, 160"),
        request_rate_increment=10.0,
        request_rate_max=500.0,
        sequence_repeats=3,
        random_number_seed=40,
        time_blocks=100,
    )
    assert sequence_values(config)[1] == [100.0, 130.0, 160.0]
    runs = list(RideHailSimulationSequence(config).runs(config))
    assert len(runs) == 9
    # Repeats outermost
    assert [seed for seed, _ in runs] == [40] * 3 + [41] * 3 + [42] * 3
    assert [params[0] for _, params in runs[:3]] == [100.0, 130.0, 160.0]


def _run_cli(args, cwd):
    return subprocess.run(
        [sys.executable, "-m", "ridehail", *args],
        cwd=str(cwd),
        capture_output=True,
        text=True,
        timeout=300,
    )


def test_command_line_sequence():
    """A preset sequence with -o: the strategy is in the sequence CSV."""
    tmp = Path(tempfile.mkdtemp(prefix="strategy_seq_"))
    result = _run_cli(
        [
            "--preset",
            "game",
            "-a",
            "none",
            "-s",
            "-srv",
            "5,11",
            "-sr",
            "2",
            "-rns",
            "9",
            "-b",
            "100",
            "-rw",
            "60",
            "-so",
            "rate:30",
            "-o",
        ],
        tmp,
    )
    assert result.returncode == 0, result.stderr
    assert "== demand 5" in result.stdout and "== demand 11" in result.stdout
    assert "rate:30" in result.stdout
    files = list((tmp / "out").glob("game-*.csv"))
    assert len(files) == 1
    with open(files[0]) as f:
        rows = list(csv.reader(f, skipinitialspace=True))
    header = [name.strip('"') for name in rows[0] if name.strip()]
    assert "strategy_net_income" in header and "strategy_fraction_parked" in header
    # 2 demands x 2 repeats
    assert len([row for row in rows[1:] if any(row)]) == 4


def test_command_line_single_run_results_section():
    tmp = Path(tempfile.mkdtemp(prefix="strategy_run_"))
    cfg = tmp / "g.config"
    write = _run_cli(
        [
            "--preset",
            "game",
            "-a",
            "none",
            "-so",
            "centre",
            "-si",
            "park",
            "-wc",
            str(cfg),
        ],
        tmp,
    )
    assert write.returncode == 0, write.stderr
    parsed = configparser.RawConfigParser()
    parsed.read(cfg)
    assert parsed["STRATEGY"]["strategy_offer"] == "centre"
    assert parsed["STRATEGY"]["strategy_idle"] == "park"
    run = _run_cli([str(cfg), "-rns", "4"], tmp)
    assert run.returncode == 0, run.stderr
    assert "Takes trips to the City Centre, parks when idle" in run.stdout
    parsed = configparser.RawConfigParser()
    parsed.read(cfg)
    results = parsed["RESULTS"]
    assert "strategy_offer_rule" not in results
    assert "strategy_net_income" in results and "strategy_surplus" in results
