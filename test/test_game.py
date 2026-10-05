"""
Tests for ridehail/game/ (game mode: "One Shift").
"""

import json
import logging
import math
import random
import re
from pathlib import Path

import pytest

from ridehail.atom import Trip, TripPhase, VehiclePhase
from ridehail.game import (
    BOTS,
    CARDS,
    CITIES,
    MARKETS,
    GameParams,
    OfferPricing,
    create_game,
    market_settings,
    offer_model,
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


def _pricing(seed=1):
    return OfferPricing(GameParams(), random.Random(seed))


def test_rate_card():
    pricing = _pricing()
    # 14 blocks = 14 min and 14 * km_per_block km
    km = 14 * pricing.params.km_per_block
    assert pricing.rate_card(14) == pytest.approx(2.50 + 0.75 * km + 0.18 * 14)


def _trip(index, blocks):
    trip = Trip.__new__(Trip)
    trip.index = index
    trip.distance = blocks
    return trip


def test_offer_luck_matches_the_model():
    """log(offer / F) reproduces the stored quantiles of the trip's band."""
    pricing = _pricing(3)
    km = pricing.params.km_per_block
    blocks, pickup = 13, 5  # a 4.8 km trip, 1.9 km pickup: luck band 1
    typical = pricing.typical_offer(blocks * km, pickup * km)
    logs = sorted(
        math.log(pricing.offer_price(_trip(-1 - i, blocks), pickup) / typical)
        for i in range(20000)
    )
    table = dict(zip(offer_model.LUCK_PROBS, offer_model.LUCK_QUANTILES[1]))
    for prob in (0.1, 0.5, 0.9):
        assert logs[int(prob * len(logs))] == pytest.approx(table[prob], abs=0.03)
    assert math.exp(logs[0]) * typical >= offer_model.MIN_OFFER - 0.01


def test_offer_shape():
    """Pay per km falls with trip length; long pickups raise the offer."""
    per_km = [OfferPricing.typical_offer(km, 1.0) / km for km in (1, 2, 4, 8, 12)]
    assert per_km == sorted(per_km, reverse=True)
    by_pickup = [OfferPricing.typical_offer(5.0, pu) for pu in (0, 1, 3, 5, 8)]
    assert by_pickup == sorted(by_pickup)
    assert by_pickup[-1] / by_pickup[0] > 1.1


def test_luck_is_shared_by_the_drivers_offered_a_trip():
    pricing = _pricing()
    km = pricing.params.km_per_block
    trip = _trip(-50000, 16)
    near, far = pricing.offer_price(trip, 1), pricing.offer_price(trip, 22)
    expected = pricing.typical_offer(16 * km, 22 * km) / pricing.typical_offer(
        16 * km, km
    )
    assert far / near == pytest.approx(expected, rel=0.03)


def test_price_is_fixed_per_trip():
    pricing = _pricing()
    trip = _trip(-99999, 10)
    assert pricing.price(trip) == pricing.price(trip)


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
    assert bots["hourly_low"].accepts(_offer(4.5, 20.0))  # $4.50 / 12 min
    assert not bots["hourly_low"].accepts(_offer(4.3, 20.0))
    assert bots["hourly_high"].accepts(_offer(6.7, 20.0))  # $6.70 / 12 min
    assert not bots["hourly_high"].accepts(_offer(6.5, 20.0))
    assert bots["centre"].accepts({**_offer(1.0, 10.0), "dropoff_zone": "core"})
    assert not bots["centre"].accepts(
        {**_offer(50.0, 10.0), "dropoff_zone": "outskirts"}
    )


# ---------------------------------------------------------------------------
# A whole shift
# ---------------------------------------------------------------------------


def test_shift_bookkeeping(played_shift):
    sim, game, entries = played_shift
    p = game.params
    assert game.shift_block == p.shift_blocks
    for index, ledger in game.ledgers.items():
        if index == game.player or index in game.bots:
            assert sum(ledger.minutes.values()) == p.shift_blocks
        else:
            assert sum(ledger.minutes.values()) <= p.shift_blocks
        assert 0 <= ledger.km <= p.shift_blocks * p.km_per_block
    results = game.results()
    assert results["player"]["offers"] == len(entries) == len(results["offer_log"])
    assert results["player"]["acceptance_rate"] == 1.0
    assert len(results["bots"]) == len(BOTS)
    # Most of the fleet is on shift for most of it
    assert len(results["fleet_net_per_hour"]) > 0.8 * (len(sim.vehicles) - 1)
    assert 0.0 <= results["fleet_percentile"] <= 1.0
    # The fleet's pooled phase minutes: each counted driver was on shift for
    # at most the whole shift
    fleet_minutes = sum(results["fleet_minutes"].values())
    assert 0 < fleet_minutes <= len(results["fleet_net_per_hour"]) * p.shift_blocks + 1


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


def test_rider_fares_match_completed_trips(played_shift):
    """Rider fares accrue like earnings: completed trips plus the part in progress."""
    sim, game, entries = played_shift
    ledger = game.ledgers[game.player]
    completed = [
        e["rider_fare"]
        for e in entries
        if e["decision"] == "accept"
        and (
            sim.trips.get(e["trip_id"]) is None
            or sim.trips[e["trip_id"]].phase
            in (TripPhase.COMPLETED, TripPhase.INACTIVE)
        )
    ]
    in_progress = sum(v for (i, _), v in game.accrued_fare.items() if i == game.player)
    assert ledger.rider_fares == pytest.approx(sum(completed) + in_progress)
    summary = ledger.summary(game.params)
    assert 0.3 < summary["driver_share"] < 1.0
    assert summary["rider_hst"] == pytest.approx(
        summary["rider_fares"] * 0.13 / 1.13, abs=0.01
    )


def test_rider_fares_share_the_trip_luck():
    """Typical fare is linear in km; each trip's fare moves with its luck."""
    pricing = _pricing(5)
    typical = OfferPricing.typical_rider_fare
    assert typical(6.0) - typical(2.0) == pytest.approx(
        offer_model.RIDER_FARE_PER_KM * 4
    )
    trips = [_trip(-70000 - i, 10) for i in range(4000)]
    fares = [pricing.rider_fare(t) for t in trips]
    # The average over many trips is the typical fare
    assert sum(fares) / len(fares) == pytest.approx(
        typical(10 * pricing.params.km_per_block), rel=0.03
    )
    # The driver's share barely varies from trip to trip: fare and offer
    # share the luck (up to the offer's rounding and minimum)
    shares = [pricing.offer_price(t, 4) / f for t, f in zip(trips, fares)]
    shares.sort()
    assert shares[int(0.9 * len(shares))] / shares[int(0.1 * len(shares))] < 1.05


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
    player = game.player_vehicle
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
            player = game.player_vehicle
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
    assert game.player in game.declined_by[trip_id]


def test_acceptance_timeout():
    # Dormant: no offer screen turns the rule on, but GameParams still can
    params = GameParams(
        acceptance_rule={"min_accepts": 4, "window": 10, "timeout_blocks": 10}
    )
    _, game = create_game("busy", "pro", params=params)
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


def test_offer_screens():
    for card in CARDS:
        create_game("normal", "cards", card=card)
    with pytest.raises(ValueError):
        create_game("normal", "cards", card="rookie")


LAB = Path(__file__).resolve().parent.parent / "docs" / "lab"


def test_web_lab_setup_matches_the_game():
    """
    The web lab's game choices (docs/lab/modules/game-setup.js, and the setup
    screen in components/game-tab.html) agree with ridehail.game.
    """
    source = (LAB / "modules" / "game-setup.js").read_text()
    setup = json.loads(re.search(r"const SETUP = (\{.*?\n\});", source, re.S)[1])
    assert setup["shiftBlocks"] == GameParams().shift_blocks
    assert setup["citySizes"] == {
        city: market_settings("normal", city)["city_size"] for city in CITIES
    }
    assert setup["markets"] == {key: m["label"] for key, m in MARKETS.items()}
    assert list(setup["cards"]) == list(CARDS)
    # The setup screen: each radio button's value and title
    html = (LAB / "components" / "game-tab.html").read_text()
    for name, labels in (("market", setup["markets"]), ("card", setup["cards"])):
        options = re.findall(
            rf'name="game-{name}" value="(\w+)".*?game-option-title">([^<]+)<',
            html,
            re.S,
        )
        assert dict(options) == labels, name
