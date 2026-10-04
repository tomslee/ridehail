"""
Tests for advanced dispatch (use_advanced_dispatch, dispatch_method,
forward_dispatch_bias) and the forward_dispatch method in particular.

Spec and test plan: claude/forward-dispatch-spec.md. Test names carry the
spec item they check (G = gating, F = forward behaviour, I = invariants,
D = defect regression).
"""

import random

import pytest

from ridehail.atom import (
    Direction,
    DispatchMethod,
    Equilibration,
    History,
    Trip,
    TripPhase,
    VehiclePhase,
)
from ridehail.config import RideHailConfig
from ridehail.dispatch import Dispatch
from ridehail.simulation import RideHailSimulation


def make_sim(
    method=DispatchMethod.FORWARD_DISPATCH,
    use_advanced_dispatch=True,
    city_size=8,
    vehicle_count=1,
    base_demand=0.0,
    bias=0,
    seed=11,
    **extra,
):
    config = RideHailConfig(use_config_file=False)
    config.animation.value = "none"
    config.time_blocks.value = 1000
    config.random_number_seed.value = seed
    config.city_size.value = city_size
    config.vehicle_count.value = vehicle_count
    config.base_demand.value = base_demand
    config.mean_trip_distance.value = city_size // 2
    config.use_advanced_dispatch.value = use_advanced_dispatch
    config.dispatch_method.value = method
    config.forward_dispatch_bias.value = bias
    for key, value in extra.items():
        getattr(config, key).value = value
    return RideHailSimulation(config)


def place(vehicle, location, phase=VehiclePhase.P1, dropoff=None, trip_index=None):
    vehicle.location = list(location)
    vehicle.direction = Direction.NORTH
    vehicle.phase = phase
    vehicle.trip_index = trip_index
    vehicle.dropoff_location = list(dropoff) if dropoff else []
    vehicle.pickup_location = []
    vehicle.forward_dispatch_trip_index = None


def request(sim, index, origin, destination):
    trip = Trip(index, sim.city)
    trip.origin = list(origin)
    trip.destination = list(destination)
    trip.update_phase(TripPhase.UNASSIGNED)
    sim.trips[index] = trip
    return trip


def dispatch(sim, trips, bias=None):
    dispatcher = Dispatch(
        DispatchMethod.FORWARD_DISPATCH,
        sim.forward_dispatch_bias if bias is None else bias,
    )
    dispatcher.dispatch_vehicles(trips, sim.city, sim.vehicles)


# ---------------------------------------------------------------------------
# Gating (G1-G3)
# ---------------------------------------------------------------------------

CONFIG_TEXT = """[DEFAULT]
city_size = 8
vehicle_count = 4
base_demand = 1.0
time_blocks = 10
animation = none
use_advanced_dispatch = {uad}

[ADVANCED_DISPATCH]
dispatch_method = forward_dispatch
forward_dispatch_bias = {bias}
"""


def config_from_file(tmp_path, monkeypatch, uad=True, bias=2, cli=()):
    path = tmp_path / "fd.config"
    path.write_text(CONFIG_TEXT.format(uad=uad, bias=bias))
    monkeypatch.setattr("sys.argv", ["ridehail", str(path), *cli])
    return RideHailConfig()


def test_G1_config_file_section_read_when_enabled(tmp_path, monkeypatch):
    config = config_from_file(tmp_path, monkeypatch, uad=True)
    assert config.dispatch_method.value == DispatchMethod.FORWARD_DISPATCH
    assert config.forward_dispatch_bias.value == 2
    sim = RideHailSimulation(config)
    assert sim.dispatch_method == DispatchMethod.FORWARD_DISPATCH


def test_G1_config_file_section_ignored_when_disabled(tmp_path, monkeypatch):
    config = config_from_file(tmp_path, monkeypatch, uad=False)
    assert RideHailSimulation(config).dispatch_method == DispatchMethod.DEFAULT


def test_G2_cli_switch_off_wins_over_config_file(tmp_path, monkeypatch):
    # D1: the section is read before the CLI turns the switch off
    config = config_from_file(
        tmp_path, monkeypatch, uad=True, cli=["--no-use_advanced_dispatch"]
    )
    assert RideHailSimulation(config).dispatch_method == DispatchMethod.DEFAULT


def test_G2_cli_method_without_switch_is_ignored(tmp_path, monkeypatch):
    config = config_from_file(
        tmp_path, monkeypatch, uad=False, cli=["-dm", "forward_dispatch"]
    )
    assert RideHailSimulation(config).dispatch_method == DispatchMethod.DEFAULT


def test_G2_programmatic_method_without_switch_is_ignored():
    sim = make_sim(use_advanced_dispatch=False)
    assert sim.dispatch_method == DispatchMethod.DEFAULT
    assert sim._dispatcher.dispatch_method == DispatchMethod.DEFAULT


def test_G3_negative_bias_rejected(tmp_path, monkeypatch):
    # Like other invalid config-file values: warn and use the default
    config = config_from_file(tmp_path, monkeypatch, bias=-1)
    assert config.forward_dispatch_bias.value == 0
    is_valid, _, _ = config.forward_dispatch_bias.validate_value(-1)
    assert not is_valid


# ---------------------------------------------------------------------------
# Choice of vehicle (F1-F6)
# ---------------------------------------------------------------------------


def test_F2_nearer_p1_beats_p3():
    sim = make_sim(vehicle_count=2)
    p1, p3 = sim.vehicles
    place(p1, (0, 2))  # 2 from origin
    place(p3, (0, 5), VehiclePhase.P3, dropoff=(0, 6), trip_index=99)  # 1 + 6
    trip = request(sim, 1, (0, 0), (4, 4))
    dispatch(sim, [trip])
    assert p1.phase == VehiclePhase.P2 and p1.trip_index == 1
    assert p3.forward_dispatch_trip_index is None
    assert trip.phase == TripPhase.WAITING and not trip.forward_dispatch


def test_F6_nearer_p3_is_forward_dispatched():
    sim = make_sim(vehicle_count=2)
    p1, p3 = sim.vehicles
    place(p1, (4, 4))  # 8 from origin
    place(p3, (0, 2), VehiclePhase.P3, dropoff=(0, 1), trip_index=99)  # 1 + 1
    trip = request(sim, 1, (0, 0), (4, 4))
    dispatch(sim, [trip])
    assert p1.phase == VehiclePhase.P1
    assert p3.phase == VehiclePhase.P3
    assert p3.trip_index == 99
    assert p3.forward_dispatch_trip_index == 1
    assert p3.forward_dispatch_pickup_location == [0, 0]
    assert p3.forward_dispatch_dropoff_location == [4, 4]
    assert p3.forward_dispatches == 1
    assert trip.phase == TripPhase.WAITING and trip.forward_dispatch


@pytest.mark.parametrize("bias, expect_p3", [(0, False), (1, False), (2, True)])
def test_F2_bias_tips_choice_to_p3(bias, expect_p3):
    # P1 at distance 2; P3 effective distance 3 (2 to dropoff, 1 on)
    sim = make_sim(vehicle_count=2)
    p1, p3 = sim.vehicles
    place(p1, (0, 2))
    place(p3, (2, 1), VehiclePhase.P3, dropoff=(0, 1), trip_index=99)
    trip = request(sim, 1, (0, 0), (4, 4))
    random.seed(0)
    dispatch(sim, [trip], bias=bias)
    if bias == 1:
        # Tie at 3: either vehicle, chosen at random
        assert (p1.trip_index == 1) != (p3.forward_dispatch_trip_index == 1)
    else:
        assert (p3.forward_dispatch_trip_index == 1) == expect_p3
        assert (p1.trip_index == 1) == (not expect_p3)


def test_F3_tie_break_is_uniform():
    # P1 at 2 + bias 1 ties with P3 at 3: each should win about half the time
    wins = 0
    for seed in range(400):
        sim = make_sim(vehicle_count=2)
        p1, p3 = sim.vehicles
        place(p1, (0, 2))
        place(p3, (2, 1), VehiclePhase.P3, dropoff=(0, 1), trip_index=99)
        trip = request(sim, 1, (0, 0), (4, 4))
        random.seed(seed)
        dispatch(sim, [trip], bias=1)
        wins += p3.forward_dispatch_trip_index == 1
    assert 140 < wins < 260


def test_F1_p2_and_engaged_p3_never_chosen():
    sim = make_sim(vehicle_count=3)
    p2, p3_busy, p1 = sim.vehicles
    place(p2, (0, 1), VehiclePhase.P2, trip_index=98)
    p2.pickup_location = [3, 3]
    place(p3_busy, (0, 2), VehiclePhase.P3, dropoff=(0, 1), trip_index=99)
    p3_busy.forward_dispatch_trip_index = 97
    place(p1, (4, 4))
    trip = request(sim, 1, (0, 0), (4, 4))
    dispatch(sim, [trip])
    assert p2.trip_index == 98
    assert p3_busy.forward_dispatch_trip_index == 97
    assert p1.trip_index == 1


def test_F1_one_forward_trip_per_vehicle():
    sim = make_sim(vehicle_count=1)
    (p3,) = sim.vehicles
    place(p3, (0, 2), VehiclePhase.P3, dropoff=(0, 1), trip_index=99)
    first = request(sim, 1, (0, 0), (4, 4))
    second = request(sim, 2, (0, 0), (3, 3))
    dispatch(sim, [first, second])
    assert p3.forward_dispatch_trip_index == 1
    assert second.phase == TripPhase.UNASSIGNED


def test_F2_p3_standing_on_origin_is_a_candidate():
    # D3: dispatch_distance used to return 0 (not a candidate) for location == origin
    sim = make_sim(vehicle_count=1)
    (p3,) = sim.vehicles
    place(p3, (2, 2), VehiclePhase.P3, dropoff=(2, 3), trip_index=99)
    trip = request(sim, 1, (2, 2), (5, 5))
    dispatch(sim, [trip])
    assert p3.forward_dispatch_trip_index == 1


def test_F2_p1_standing_on_origin_is_not_a_candidate():
    sim = make_sim(vehicle_count=1)
    (p1,) = sim.vehicles
    place(p1, (2, 2))
    trip = request(sim, 1, (2, 2), (5, 5))
    dispatch(sim, [trip])
    assert p1.phase == VehiclePhase.P1 and trip.phase == TripPhase.UNASSIGNED


@pytest.mark.parametrize(
    "method", [DispatchMethod.FORWARD_DISPATCH, DispatchMethod.DEFAULT]
)
def test_F4_antipodal_vehicle_is_found(method):
    # D4: the ring search stopped at city_size - 1. Two vehicles at the
    # antipode keep the default method on its dense (ring) search.
    sim = make_sim(method=method, city_size=2, vehicle_count=3)
    for vehicle in sim.vehicles:
        place(vehicle, (1, 1))
    trip = request(sim, 1, (0, 0), (1, 0))
    Dispatch(method).dispatch_vehicles([trip], sim.city, sim.vehicles)
    assert trip.phase == TripPhase.WAITING


# ---------------------------------------------------------------------------
# Handover at dropoff (F7)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("forward_index", [0, 1, 42])
def test_F7_handover_to_p2_at_dropoff(forward_index):
    # D2: trip index 0 was treated as "no forward trip"
    sim = make_sim(vehicle_count=1)
    (vehicle,) = sim.vehicles
    place(vehicle, (0, 2), VehiclePhase.P3, dropoff=(0, 1), trip_index=99)
    trip = request(sim, forward_index, (0, 0), (4, 4))
    dispatch(sim, [trip])
    vehicle.location = [0, 1]
    vehicle.update_phase(to_phase=VehiclePhase.P1)
    assert vehicle.phase == VehiclePhase.P2
    assert vehicle.trip_index == forward_index
    assert vehicle.pickup_location == [0, 0]
    assert vehicle.dropoff_location == [4, 4]
    assert vehicle.forward_dispatch_trip_index is None


def test_F7_F9_forward_trip_lifecycle_in_running_sim():
    """Run the real block loop through dropoff, pickup and completion."""
    sim = make_sim(vehicle_count=1, base_demand=0.0)
    (vehicle,) = sim.vehicles
    current = request(sim, 0, (0, 0), (0, 3))
    current.update_phase(TripPhase.RIDING)
    place(vehicle, (0, 1), VehiclePhase.P3, dropoff=(0, 3), trip_index=0)
    forward = request(sim, 1, (2, 3), (2, 6))
    block = 0
    sim.next_block(block=block)  # dispatch: forward trip to the P3 vehicle
    assert vehicle.forward_dispatch_trip_index == 1
    phases = []
    while forward.phase not in (TripPhase.COMPLETED, TripPhase.INACTIVE):
        block += 1
        sim.next_block(block=block)
        phases.append(vehicle.phase)
        assert block < 30
    # P3 (current ride), then straight to P2 with no P1 block, then P3 again
    assert VehiclePhase.P1 not in phases[: phases.index(VehiclePhase.P2) + 1]
    assert current.phase in (TripPhase.COMPLETED, TripPhase.INACTIVE)
    assert forward.forward_dispatch
    assert sim.history_buffer[History.TRIP_FORWARD_DISPATCH_COUNT].sum == 1


# ---------------------------------------------------------------------------
# Invariants over seeded runs (I1-I4, D5, D6)
# ---------------------------------------------------------------------------


def check_invariants(sim):
    held = {}
    for vehicle in sim.vehicles:
        for index in (vehicle.trip_index, vehicle.forward_dispatch_trip_index):
            if index is not None:
                assert index not in held, f"I1: trip {index} held twice"
                held[index] = vehicle
        if vehicle.forward_dispatch_trip_index is not None:
            assert vehicle.phase == VehiclePhase.P3, "I3"
        if vehicle.phase == VehiclePhase.P1:
            assert vehicle.trip_index is None, "I4"
        else:
            assert vehicle.trip_index is not None, "I4"
    for index, trip in sim.trips.items():
        if trip.phase in (TripPhase.WAITING, TripPhase.RIDING):
            assert index in held, f"I2: {trip.phase.name} trip {index} unheld"


RUNS = {
    # name: (city_size, vehicle_count, base_demand, bias, extra)
    "oversupplied": (16, 120, 2.0, 0, {}),
    "oversupplied_bias": (16, 120, 2.0, 4, {}),
    "undersupplied": (12, 20, 4.0, 0, {}),
    "pickup_time": (16, 60, 2.0, 2, {"pickup_time": 2}),
    "inhomogeneous": (16, 80, 3.0, 2, {"inhomogeneity": 0.5}),
}


@pytest.mark.parametrize("name", list(RUNS))
def test_invariants_hold(name):
    city_size, vehicle_count, base_demand, bias, extra = RUNS[name]
    sim = make_sim(
        city_size=city_size,
        vehicle_count=vehicle_count,
        base_demand=base_demand,
        bias=bias,
        **extra,
    )
    for block in range(300):
        sim.next_block(block=block)
        check_invariants(sim)
    assert sum(v.forward_dispatches for v in sim.vehicles) > 0


@pytest.mark.parametrize(
    "method", [DispatchMethod.FORWARD_DISPATCH, DispatchMethod.DEFAULT]
)
def test_D5_invariants_survive_fleet_resizing(method):
    sim = make_sim(method=method, city_size=16, vehicle_count=80, base_demand=3.0)
    for block in range(300):
        if block == 100:
            sim.target_state["vehicle_count"] = 40
        if block == 150:
            sim.target_state["vehicle_count"] = 70
        sim.next_block(block=block)
        check_invariants(sim)


def test_D5_invariants_survive_equilibration():
    sim = make_sim(
        city_size=16,
        vehicle_count=60,
        base_demand=3.0,
        bias=2,
        equilibration=Equilibration.PRICE,
        equilibration_interval=5,
    )
    counts = set()
    for block in range(300):
        sim.next_block(block=block)
        check_invariants(sim)
        counts.add(len(sim.vehicles))
    assert len(counts) > 1  # the fleet really did change size


def test_D5_dense_default_picks_nearest_after_fleet_shrink(monkeypatch):
    """After _remove_vehicles, list positions no longer match vehicle.index."""
    misses = []
    original = Dispatch._dispatch_vehicle_dense

    def checked(self, trip, city, grid, pool, vehicles):
        nearest = min(
            (
                d
                for d in (
                    city.dispatch_distance(v.location, v.direction, trip.origin)
                    for v in pool
                )
                if d > 0
            ),
            default=None,
        )
        positions = {id(v): v.location[:] for v in pool}
        chosen = original(self, trip, city, grid, pool, vehicles)
        if chosen is not None:
            chosen_distance = city.distance(positions[id(chosen)], trip.origin)
            misses.append(chosen_distance != nearest)
        return chosen

    monkeypatch.setattr(Dispatch, "_dispatch_vehicle_dense", checked)
    sim = make_sim(
        method=DispatchMethod.DEFAULT,
        city_size=24,
        vehicle_count=300,
        base_demand=8.0,
    )
    for block in range(200):
        if block == 50:
            sim.target_state["vehicle_count"] = 200
        sim.next_block(block=block)
    assert misses and not any(misses)


# ---------------------------------------------------------------------------
# Measures and live changes (F9-F11)
# ---------------------------------------------------------------------------


def forward_fraction(sim, blocks=300):
    for block in range(blocks):
        sim.next_block(block=block)
    completed = sim.history_buffer[History.TRIP_COMPLETED_COUNT].sum
    return sim.history_buffer[History.TRIP_FORWARD_DISPATCH_COUNT].sum / completed


def test_F10_forward_fraction_rises_with_bias():
    fractions = [
        forward_fraction(
            make_sim(city_size=16, vehicle_count=120, base_demand=2.0, bias=bias)
        )
        for bias in (0, 3, 10)
    ]
    assert fractions[0] < fractions[1] < fractions[2]
    assert fractions[2] > 0.8


def test_F9_default_method_counts_no_forward_dispatches():
    sim = make_sim(
        method=DispatchMethod.DEFAULT, city_size=16, vehicle_count=60, base_demand=2.0
    )
    assert forward_fraction(sim) == 0


def test_F11_live_change_of_dispatch_method():
    # D8: the dispatcher was built once, so target_state changes were ignored
    sim = make_sim(
        method=DispatchMethod.DEFAULT,
        city_size=16,
        vehicle_count=120,
        base_demand=2.0,
        bias=10,
    )
    for block in range(100):
        sim.next_block(block=block)
    assert sum(v.forward_dispatches for v in sim.vehicles) == 0
    sim.target_state["dispatch_method"] = DispatchMethod.FORWARD_DISPATCH
    for block in range(100, 200):
        sim.next_block(block=block)
        check_invariants(sim)
    assert sim._dispatcher.dispatch_method == DispatchMethod.FORWARD_DISPATCH
    assert sum(v.forward_dispatches for v in sim.vehicles) > 0
    # And back again: vehicles holding forward trips finish them
    sim.target_state["dispatch_method"] = DispatchMethod.DEFAULT
    for block in range(200, 260):
        sim.next_block(block=block)
        check_invariants(sim)
    assert all(v.forward_dispatch_trip_index is None for v in sim.vehicles)
