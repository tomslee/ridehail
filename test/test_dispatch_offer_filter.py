"""
Tests for the dispatch offer hook (Dispatch.offer_filter), used by game mode.

Part 1 - regression: with no offer_filter installed, dispatch must behave
exactly as it did before the hook (and the find/commit refactor that supports
it) was introduced. Each scenario runs a seeded simulation and hashes the full
vehicle state (phase, location, direction, trip) after every block. The
expected digests were recorded from the pre-refactor code; if a deliberate
change to dispatch or the simulation alters them, re-record by running this
file directly (python test/test_dispatch_offer_filter.py) and review why.

Part 2 - the hook itself: ACCEPT / DECLINE / DEFER semantics.
"""

import hashlib
import random

import pytest

from ridehail.atom import TripDistribution, TripPhase, VehiclePhase
from ridehail.config import RideHailConfig
from ridehail.dispatch import Dispatch, OfferDecision
from ridehail.simulation import RideHailSimulation

# name: (city_size, vehicle_count, base_demand, inhomogeneity, distribution)
# "town" is the game's geometry (dense search); "dense" keeps P1 >> city_size;
# "sparse" is undersupplied with a growing unassigned backlog (sparse search;
# its digest was re-recorded 2026-10-03 for the per-trip dense->sparse switch,
# which first fires in block 2, when the pool drains from 24 to 20; "town"
# was re-recorded 2026-10-09 when GAMMA distances changed from int() to
# round()).
SCENARIOS = {
    "town": (24, 120, 5.0, 0.5, TripDistribution.GAMMA),
    "dense": (16, 100, 2.0, 0.0, TripDistribution.UNIFORM),
    "sparse": (20, 30, 6.0, 0.0, TripDistribution.UNIFORM),
}
BLOCKS = 150
SEED = 20260929

EXPECTED_DIGESTS = {
    "town": "6d6161cae5528199ed70b61072919b587b3300e1899bc0cd0f98070c6f892f59",
    "dense": "a6f5c185e39e8a7e3e7e892a3ee634a64770c0de7c17c5cda3cf5ce372d0fc9c",
    "sparse": "7c3f6e6e3fdc5980a8d99ab95365d6c5fc20d82ce20ead7538156f0445406407",
}


def make_sim(city_size, vehicle_count, base_demand, inhomogeneity, distribution):
    config = RideHailConfig(use_config_file=False)
    config.animation.value = "none"
    config.time_blocks.value = BLOCKS
    config.random_number_seed.value = SEED
    config.city_size.value = city_size
    config.vehicle_count.value = vehicle_count
    config.base_demand.value = base_demand
    config.inhomogeneity.value = inhomogeneity
    config.mean_trip_distance.value = city_size // 2
    config.trip_distance_distribution.value = distribution
    return RideHailSimulation(config)


def run_digest(name):
    sim = make_sim(*SCENARIOS[name])
    digest = hashlib.sha256()
    for block in range(BLOCKS):
        sim.next_block(block=block)
        for v in sim.vehicles:
            digest.update(
                f"{v.phase.name}{v.location}{v.direction.name}{v.trip_index};".encode()
            )
    return digest.hexdigest()


@pytest.mark.parametrize("name", list(SCENARIOS))
def test_no_filter_matches_recorded_dispatch(name):
    assert run_digest(name) == EXPECTED_DIGESTS[name]


# ---------------------------------------------------------------------------
# Part 2: the hook
# ---------------------------------------------------------------------------


def _sim_with_single_request(vehicle_count=6, city_size=10):
    """A quiet simulation (no demand), ready for one hand-made request."""
    sim = make_sim(city_size, vehicle_count, 0.0, 0.0, TripDistribution.UNIFORM)
    sim.next_block(block=0)
    return sim


def _request(sim, origin, destination):
    from ridehail.atom import Trip

    trip = Trip(sim.next_trip_id, sim.city)
    trip.origin = list(origin)
    trip.destination = list(destination)
    trip.distance = sim.city.distance(trip.origin, trip.destination)
    trip.update_phase(TripPhase.UNASSIGNED)
    sim.trips[sim.next_trip_id] = trip
    sim.next_trip_id += 1
    return trip


def _dispatch(sim, trip):
    sim.dispatcher.dispatch_vehicles([trip], sim.city, sim.vehicles)


@pytest.mark.parametrize("sparse", [True, False])
def test_accept_all_filter_matches_no_filter(sparse, monkeypatch):
    """An always-ACCEPT filter chooses the same vehicle as no filter."""
    monkeypatch.setattr(Dispatch, "_use_sparse_search", staticmethod(lambda *a: sparse))
    chosen = []
    for use_filter in (False, True):
        random.seed(7)
        sim = _sim_with_single_request()
        if use_filter:
            sim.dispatcher.offer_filter = lambda t, v, d: OfferDecision.ACCEPT
        trip = _request(sim, (3, 3), (7, 7))
        random.seed(11)
        _dispatch(sim, trip)
        chosen.append(sim.trips[trip.index].phase)
        chosen.append([v.index for v in sim.vehicles if v.trip_index == trip.index])
    assert chosen[0] == chosen[2] == TripPhase.WAITING
    assert chosen[1] == chosen[3]


@pytest.mark.parametrize("sparse", [True, False])
def test_decline_goes_to_next_nearest(sparse, monkeypatch):
    monkeypatch.setattr(Dispatch, "_use_sparse_search", staticmethod(lambda *a: sparse))
    sim = _sim_with_single_request()
    offered = []

    def decline_first(trip, vehicle, distance):
        offered.append((vehicle.index, distance))
        return OfferDecision.DECLINE if len(offered) == 1 else OfferDecision.ACCEPT

    sim.dispatcher.offer_filter = decline_first
    trip = _request(sim, (3, 3), (7, 7))
    _dispatch(sim, trip)
    assert len(offered) == 2
    first, second = offered
    assert first[0] != second[0]
    assert second[1] >= first[1]  # next-nearest is no nearer
    assert trip.phase == TripPhase.WAITING
    assert sim.vehicles[second[0]].trip_index == trip.index
    assert sim.vehicles[first[0]].phase == VehiclePhase.P1


@pytest.mark.parametrize("sparse", [True, False])
def test_decline_all_leaves_trip_unassigned(sparse, monkeypatch):
    monkeypatch.setattr(Dispatch, "_use_sparse_search", staticmethod(lambda *a: sparse))
    sim = _sim_with_single_request(vehicle_count=5)
    offered = []

    def decline(trip, vehicle, distance):
        offered.append(vehicle.index)
        return OfferDecision.DECLINE

    sim.dispatcher.offer_filter = decline
    trip = _request(sim, (3, 3), (7, 7))
    _dispatch(sim, trip)
    assert trip.phase == TripPhase.UNASSIGNED
    # every idle vehicle offered at most once (a vehicle already at the origin
    # has dispatch distance 0 and is never a candidate)
    assert len(offered) == len(set(offered))
    assert all(v.phase == VehiclePhase.P1 for v in sim.vehicles)


@pytest.mark.parametrize("sparse", [True, False])
def test_defer_holds_trip_and_vehicle(sparse, monkeypatch):
    monkeypatch.setattr(Dispatch, "_use_sparse_search", staticmethod(lambda *a: sparse))
    sim = _sim_with_single_request()
    deferred = []

    def defer_first(trip, vehicle, distance):
        if not deferred:
            deferred.append(vehicle.index)
            return OfferDecision.DEFER
        return OfferDecision.ACCEPT

    sim.dispatcher.offer_filter = defer_first
    trip = _request(sim, (3, 3), (7, 7))
    other = _request(sim, (3, 4), (8, 8))
    _dispatch(sim, trip)
    sim.dispatcher.dispatch_vehicles([other], sim.city, sim.vehicles)
    assert trip.phase == TripPhase.UNASSIGNED
    assert sim.vehicles[deferred[0]].phase == VehiclePhase.P1
    # The deferring vehicle is out of the pool for the rest of that call only;
    # a later call can still use it (for `other`, if it is nearest).
    assert other.phase == TripPhase.WAITING


def test_commit_dispatch():
    sim = _sim_with_single_request()
    trip = _request(sim, (3, 3), (7, 7))
    vehicle = sim.vehicles[0]
    Dispatch.commit_dispatch(trip, vehicle)
    assert trip.phase == TripPhase.WAITING
    assert vehicle.phase == VehiclePhase.P2
    assert vehicle.pickup_location == [3, 3]


if __name__ == "__main__":
    for scenario in SCENARIOS:
        print(f'    "{scenario}": "{run_digest(scenario)}",')
