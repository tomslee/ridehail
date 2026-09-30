"""
Tests for ridehail/game.py (game mode: "One Shift").
"""

import logging
import math
import random

import pytest

from ridehail.atom import Trip, TripPhase, VehiclePhase
from ridehail import game_offer_model as offer_model
from ridehail.game import (
    BOTS,
    GameController,
    GameParams,
    create_game,
    shift_seed,
)

logging.disable(logging.CRITICAL)


@pytest.fixture(scope="module")
def played_shift():
    """One Normal-market shift, player accepting every offer."""
    sim, game = create_game("normal", "pytest")
    entries = []
    while not game.shift_over:
        entry = game.step(lambda offer: True)
        if entry:
            entries.append(entry)
    return sim, game, entries


# ---------------------------------------------------------------------------
# Prices
# ---------------------------------------------------------------------------


def test_rate_card():
    game = GameController.__new__(GameController)
    game.params = GameParams()
    # 14 blocks = 7 km, 14 min: 2.50 + 0.75 * 7 + 0.18 * 14
    assert game.rate_card(14) == pytest.approx(2.50 + 5.25 + 2.52)


def _trip(index, blocks):
    trip = Trip.__new__(Trip)
    trip.index = index
    trip.distance = blocks
    return trip


def test_offer_luck_matches_the_model(played_shift):
    """log(offer / F) reproduces the stored quantiles of the trip's band."""
    _, game, _ = played_shift
    game.rng = random.Random(3)
    game.prices = {}
    blocks, pickup = 10, 4  # a 5 km trip, 2 km pickup: luck band 1
    typical = game.typical_offer(5.0, 2.0)
    logs = sorted(
        math.log(game.offer_price(_trip(-1 - i, blocks), pickup) / typical)
        for i in range(20000)
    )
    table = dict(zip(offer_model.LUCK_PROBS, offer_model.LUCK_QUANTILES[1]))
    for prob in (0.1, 0.5, 0.9):
        assert logs[int(prob * len(logs))] == pytest.approx(table[prob], abs=0.03)
    assert math.exp(logs[0]) * typical >= offer_model.MIN_OFFER - 0.01


def test_offer_shape():
    """Pay per km falls with trip length; long pickups raise the offer."""
    per_km = [GameController.typical_offer(km, 1.0) / km for km in (1, 2, 4, 8, 12)]
    assert per_km == sorted(per_km, reverse=True)
    by_pickup = [GameController.typical_offer(5.0, pu) for pu in (0, 1, 3, 5, 8)]
    assert by_pickup == sorted(by_pickup)
    assert by_pickup[-1] / by_pickup[0] > 1.1


def test_luck_is_shared_by_the_drivers_offered_a_trip(played_shift):
    _, game, _ = played_shift
    trip = _trip(-50000, 12)
    near, far = game.offer_price(trip, 1), game.offer_price(trip, 16)
    expected = game.typical_offer(6.0, 8.0) / game.typical_offer(6.0, 0.5)
    assert far / near == pytest.approx(expected, rel=0.03)


def test_price_is_fixed_per_trip(played_shift):
    sim, game, _ = played_shift
    trip = Trip.__new__(Trip)
    trip.index = -99999
    trip.distance = 10
    assert game.price(trip) == game.price(trip)


def test_prices_round_to_five_cents(played_shift):
    _, game, entries = played_shift
    offers = [e["offer"] for e in entries] + list(game.agreed.values())
    assert offers
    for offer in offers:
        assert round(offer * 100) % 5 == 0


# ---------------------------------------------------------------------------
# Bots
# ---------------------------------------------------------------------------


def _offer(offer, rate_card, pickup_km=1.0, trip_km=5.0):
    pickup_min, trip_min = pickup_km * 2, trip_km * 2
    return {
        "offer": offer,
        "rate_card": rate_card,
        "pickup_km": pickup_km,
        "trip_km": trip_km,
        "per_min": offer / (pickup_min + trip_min),
        "per_km": offer / (pickup_km + trip_km),
    }


def test_bot_rules():
    bots = {bot.key: bot for bot in BOTS}
    assert bots["yes"].accepts(_offer(1.0, 10.0))
    assert bots["loyalist"].accepts(_offer(10.0, 10.0))
    assert not bots["loyalist"].accepts(_offer(9.95, 10.0))
    assert bots["per_km"].accepts(_offer(6.0, 20.0))  # $6 / 6 km
    assert not bots["per_km"].accepts(_offer(5.95, 20.0))
    assert bots["hourly"].accepts(_offer(6.7, 20.0))  # $6.70 / 12 min
    assert not bots["hourly"].accepts(_offer(6.5, 20.0))


# ---------------------------------------------------------------------------
# A whole shift
# ---------------------------------------------------------------------------


def test_shift_bookkeeping(played_shift):
    sim, game, entries = played_shift
    p = game.params
    assert game.shift_block == p.shift_blocks
    for index, ledger in enumerate(game.ledgers):
        if index == game.player or index in game.bots:
            assert sum(ledger.minutes.values()) == p.shift_blocks
        else:
            assert sum(ledger.minutes.values()) <= p.shift_blocks
        assert 0 <= ledger.km <= p.shift_blocks * p.km_per_block
    results = game.results()
    assert results["player"]["offers"] == len(entries) == len(results["offer_log"])
    assert results["player"]["acceptance_rate"] == 1.0
    assert len(results["bots"]) == 4
    # Most of the fleet is on shift for most of it
    assert len(results["fleet_net_per_hour"]) > 0.8 * (len(sim.vehicles) - 1)
    assert 0.0 <= results["fleet_percentile"] <= 1.0


def test_player_earnings_match_completed_trips(played_shift):
    """Earnings = completed offers + the accrued part of any trip in progress."""
    sim, game, entries = played_shift
    ledger = game.ledgers[game.player]
    completed = [
        e["offer"]
        for e in entries
        if sim.trips.get(e["trip_id"]) is None
        or sim.trips[e["trip_id"]].phase in (TripPhase.COMPLETED, TripPhase.INACTIVE)
    ]
    in_progress = sum(v for (i, _), v in game.accrued.items() if i == game.player)
    assert ledger.trips_completed == len(completed)
    assert ledger.earnings == pytest.approx(sum(completed) + in_progress)


def test_player_offered_only_when_idle_and_logged_on(played_shift):
    _, game, entries = played_shift
    assert entries, "a Normal shift should produce offers"
    for e in entries:
        assert 0 <= e["block"] < game.params.shift_blocks
        assert e["pickup_minutes"] > 0
        assert e["dropoff_zone"] in ("core", "outskirts")


def test_same_code_same_shift():
    runs = []
    for _ in range(2):
        _, game = create_game("busy", "same-code")
        offers = []
        for _ in range(60):
            entry = game.step(lambda o: o["offer"] >= o["rate_card"])
            if entry:
                offers.append((entry["block"], entry["offer"], entry["decision"]))
        runs.append(offers)
    assert runs[0] == runs[1]
    assert shift_seed("a", "busy") != shift_seed("a", "slow")
    assert shift_seed("", "busy") % 2 == 1  # never zero


def test_decline_is_redispatched_and_never_reoffered():
    _, game = create_game("busy", "decline")
    declined = []
    for _ in range(90):
        entry = game.step(lambda o: False)
        if entry:
            declined.append(entry)
    assert declined
    trip_ids = [e["trip_id"] for e in declined]
    assert len(trip_ids) == len(set(trip_ids))
    player = game.sim.vehicles[game.player]
    assert player.phase == VehiclePhase.P1
    assert game.ledgers[game.player].earnings == 0.0
    # In a busy market declined trips are soon taken by another car
    assert any("taken_after_minutes" in e for e in declined)


def test_accept_points_player_at_pickup():
    _, game = create_game("normal", "accept-direction")
    for _ in range(game.params.shift_blocks):
        game.before_block()
        game.sim.next_block()
        game.after_block()
        if game.pending:
            pickup = game.pending["pickup"]
            game.resolve_offer(True)
            player = game.sim.vehicles[game.player]
            assert player.phase == VehiclePhase.P2
            assert player.pickup_location == pickup
            # One step in the new direction brings the car closer
            city = game.sim.city
            before = city.distance(player.location, pickup)
            step = [
                (player.location[i] + player.direction.value[i]) % city.city_size
                for i in (0, 1)
            ]
            assert city.distance(step, pickup) == before - 1
            return
    pytest.fail("no offer in a whole shift")


def test_leg_progress():
    """The HUD's progress: None while idle, rising from 0 on each leg."""
    _, game = create_game("normal", "leg-progress")
    trace = []
    while not game.shift_over:
        game.before_block()
        game.sim.next_block()
        game.after_block()
        if game.pending:
            game.resolve_offer(True)
        payload = game.frame_payload()
        trace.append((payload["player_phase"], payload["leg_progress"]))
    assert any(phase == "P3" for phase, _ in trace)
    previous = (None, None)
    for phase, progress in trace:
        if phase == "P1":
            assert progress is None
        else:
            assert 0.0 <= progress <= 1.0
            if phase == previous[0]:
                assert progress >= previous[1]
            else:
                assert progress <= 0.5
        previous = (phase, progress)


def test_unresolved_offer_times_out():
    _, game = create_game("busy", "timeout")
    while game.pending is None:
        game.before_block()
        game.sim.next_block()
        game.after_block()
    trip_id = game.pending["trip_id"]
    game.before_block()
    assert game.pending is None
    assert game.offer_log[-1]["decision"] == "timeout"
    assert game.player in game.sim.trips[trip_id].declined_by


def test_pro_acceptance_timeout():
    _, game = create_game("busy", "pro", difficulty="pro")
    rule = game.params.acceptance_rule
    decisions = 0
    while decisions < rule["window"] and not game.shift_over:
        if game.step(lambda o: False):
            decisions += 1
    assert game.timeout_until is not None
    start = game.shift_block
    while game.shift_block < game.timeout_until:
        assert game.step(lambda o: False) is None
    assert game.shift_block - start <= rule["timeout_blocks"]
