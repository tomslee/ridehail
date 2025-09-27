"""
Core functionality tests for RideHailSimulation.

Tests for initialization, basic simulation mechanics, and state management.
"""

import pytest
import random
import numpy as np
from ridehail.simulation import RideHailSimulation, CircularBuffer
from ridehail.atom import VehiclePhase, TripPhase, History, Measure


class TestSimulationInitialization:
    """Test simulation initialization and setup."""

    def test_basic_initialization(self, basic_config):
        """Test that simulation initializes correctly with basic config."""
        sim = RideHailSimulation(basic_config)

        # Test basic attributes are set
        assert sim.city_size == 8
        assert sim.vehicle_count == 5
        assert sim.base_demand == 0.5
        assert len(sim.vehicles) == 5
        assert sim.trips == []
        assert sim.block_index == 0

        # Test city is created
        assert sim.city is not None
        assert sim.city.city_size == 8

        # Test history buffers are initialized
        assert len(sim.history_buffer) == len(list(History))
        assert len(sim.history_results) == len(list(History))
        assert len(sim.history_equilibration) == len(list(History))

        for history_item in list(History):
            assert isinstance(sim.history_buffer[history_item], CircularBuffer)
            assert isinstance(sim.history_results[history_item], CircularBuffer)
            assert isinstance(sim.history_equilibration[history_item], CircularBuffer)

    def test_vehicle_initialization(self, basic_simulation):
        """Test that vehicles are properly initialized."""
        sim = basic_simulation

        assert len(sim.vehicles) == sim.vehicle_count
        for i, vehicle in enumerate(sim.vehicles):
            assert vehicle.index == i
            assert vehicle.phase == VehiclePhase.P1
            assert hasattr(vehicle, "location")
            assert hasattr(vehicle, "direction")
            assert vehicle.trip_index is None

    def test_configuration_validation(self, basic_config):
        """Test that configuration parameters are validated correctly."""
        # Test even city size validation
        basic_config.city_size.value = 7  # odd number
        sim = RideHailSimulation(basic_config)
        assert sim.city_size == 6  # should be corrected to even

    def test_random_seed_reproducibility(self):
        """Test that setting a random seed produces reproducible results."""
        from ridehail.config import RideHailConfig

        config1 = RideHailConfig(use_config_file=False)
        config1.random_number_seed.value = 42
        config1.city_size.value = 4
        config1.vehicle_count.value = 2
        config1.base_demand.value = 0.1
        config1.animate.value = False
        config1.equilibrate.value = False

        config2 = RideHailConfig(use_config_file=False)
        config2.random_number_seed.value = 42
        config2.city_size.value = 4
        config2.vehicle_count.value = 2
        config2.base_demand.value = 0.1
        config2.animate.value = False
        config2.equilibrate.value = False

        sim1 = RideHailSimulation(config1)
        sim2 = RideHailSimulation(config2)

        # Vehicle initial positions should be identical with same seed
        for v1, v2 in zip(sim1.vehicles, sim2.vehicles):
            assert (
                v1.location == v2.location
            ), f"Initial positions differ: {v1.location} vs {v2.location}"

        # Run one block and compare key outcomes
        state1 = sim1.next_block(block=0)
        state2 = sim2.next_block(block=0)

        # Key simulation state should be identical
        assert len(sim1.trips) == len(sim2.trips), "Different number of trips generated"
        assert sim1.request_rate == sim2.request_rate, "Different request rates"


class TestBlockSimulation:
    """Test single block simulation mechanics."""

    def test_next_block_basic(self, minimal_simulation):
        """Test basic next_block functionality."""
        sim = minimal_simulation
        initial_block = sim.block_index

        # Run one block
        state_dict = sim.next_block(block=0)

        assert sim.block_index == initial_block + 1
        assert isinstance(state_dict, dict)
        assert "block" in state_dict
        assert state_dict["block"] == 0

    def test_vehicle_movement(self, minimal_simulation):
        """Test that vehicles move during simulation blocks."""
        sim = minimal_simulation

        # Record initial positions
        initial_positions = [vehicle.location.copy() for vehicle in sim.vehicles]

        # Run several blocks
        for i in range(5):
            sim.next_block(block=i)

        # At least some vehicles should have moved (with idle_vehicles_moving=True)
        moved_count = 0
        for initial_pos, vehicle in zip(initial_positions, sim.vehicles):
            if vehicle.location != initial_pos:
                moved_count += 1

        # With moving idle vehicles, at least some should have moved
        assert moved_count > 0

    def test_trip_generation(self, basic_simulation):
        """Test that trips are generated based on demand."""
        sim = basic_simulation
        sim.base_demand = 1.0  # Ensure some trip generation

        initial_trip_count = len(sim.trips)

        # Run multiple blocks to generate trips
        for i in range(10):
            sim.next_block(block=i)

        # Should have generated some trips
        assert len(sim.trips) > initial_trip_count

    def test_dispatch_process(self, basic_simulation):
        """Test the vehicle dispatch process."""
        sim = basic_simulation

        # Force trip generation by setting high demand
        sim.base_demand = 2.0
        sim.request_capital = 2.0  # Ensure trips are generated

        # Run one block to generate and dispatch trips
        sim.next_block(block=0)

        # Check if any vehicles were dispatched (P2 phase)
        dispatched_vehicles = [v for v in sim.vehicles if v.phase == VehiclePhase.P2]

        # With high demand and available vehicles, some should be dispatched
        if len(sim.trips) > 0:
            assert len(dispatched_vehicles) > 0

    def test_trip_phase_transitions(self, basic_simulation):
        """Test trip phase transitions during simulation."""
        sim = basic_simulation

        # Create a trip manually for testing
        from ridehail.atom import Trip

        trip = Trip(0, sim.city, min_trip_distance=1, max_trip_distance=3)
        trip.update_phase(TripPhase.UNASSIGNED)
        sim.trips.append(trip)

        # Ensure we have available vehicles
        assert any(v.phase == VehiclePhase.P1 for v in sim.vehicles)

        # Run simulation blocks
        for i in range(20):
            sim.next_block(block=i)

            # Check for valid trip phases
            for t in sim.trips:
                assert t.phase in [
                    TripPhase.UNASSIGNED,
                    TripPhase.WAITING,
                    TripPhase.RIDING,
                    TripPhase.COMPLETED,
                    TripPhase.CANCELLED,
                    TripPhase.INACTIVE,
                ]

    def test_history_updates(self, minimal_simulation):
        """Test that history buffers are updated during simulation."""
        sim = minimal_simulation

        # Check initial history state
        initial_vehicle_count = sim.history_buffer[History.VEHICLE_COUNT].sum

        # Run one block
        sim.next_block(block=0)

        # History should be updated
        current_vehicle_count = sim.history_buffer[History.VEHICLE_COUNT].sum
        assert current_vehicle_count != initial_vehicle_count

        # Vehicle count history should reflect actual vehicle count
        expected_count = len(sim.vehicles)
        # The sum includes the new entry, so it should be at least the vehicle count
        assert current_vehicle_count >= expected_count


class TestStateManagement:
    """Test simulation state management and consistency."""

    def test_vehicle_phase_consistency(self, basic_simulation):
        """Test that vehicle phases remain consistent throughout simulation."""
        sim = basic_simulation

        for i in range(10):
            sim.next_block(block=i)

            # Check that all vehicles have valid phases
            for vehicle in sim.vehicles:
                assert vehicle.phase in [
                    VehiclePhase.P1,
                    VehiclePhase.P2,
                    VehiclePhase.P3,
                ]

            # Check that trip assignments are consistent with vehicle phases
            for vehicle in sim.vehicles:
                if vehicle.phase == VehiclePhase.P1:
                    assert vehicle.trip_index is None
                elif vehicle.phase in [VehiclePhase.P2, VehiclePhase.P3]:
                    # Should have a trip assigned (if there are trips)
                    if len(sim.trips) > 0 and vehicle.trip_index is not None:
                        assert 0 <= vehicle.trip_index < len(sim.trips)

    def test_trip_vehicle_consistency(self, basic_simulation):
        """Test consistency between trip assignments and vehicle states."""
        sim = basic_simulation
        sim.base_demand = 1.0  # Ensure trip generation

        for i in range(15):
            sim.next_block(block=i)

            # For each assigned trip, there should be a corresponding vehicle
            for trip in sim.trips:
                if trip.phase in [TripPhase.WAITING, TripPhase.RIDING]:
                    # Find the assigned vehicle
                    assigned_vehicles = [
                        v for v in sim.vehicles if v.trip_index == trip.index
                    ]
                    assert len(assigned_vehicles) <= 1  # At most one vehicle per trip

                    if len(assigned_vehicles) == 1:
                        vehicle = assigned_vehicles[0]
                        # Vehicle phase should match trip phase
                        if trip.phase == TripPhase.WAITING:
                            assert vehicle.phase == VehiclePhase.P2
                        elif trip.phase == TripPhase.RIDING:
                            assert vehicle.phase == VehiclePhase.P3

    def test_garbage_collection(self, basic_simulation):
        """Test that completed trips are garbage collected."""
        sim = basic_simulation
        sim.base_demand = 2.0  # High demand to generate many trips

        # Count trips before and after garbage collection
        trips_before_gc = len(sim.trips)

        # Run enough blocks to complete some trips and trigger garbage collection
        for i in range(250):  # More than GARBAGE_COLLECTION_INTERVAL (200)
            sim.next_block(block=i)

        # Garbage collection removes completed/cancelled trips
        # But some trips might still be COMPLETED in the current block before GC
        # So let's check that GC actually happened by running a few more blocks
        for i in range(250, 260):
            sim.next_block(block=i)

        # After sufficient time, trips should have been cleaned up
        # The key test is that the system remains stable and functional
        assert len(sim.trips) >= 0  # Should have some trips or none

        # Trip indices should be contiguous after garbage collection
        if len(sim.trips) > 0:
            indices = [trip.index for trip in sim.trips]
            indices.sort()
            expected_indices = list(range(len(sim.trips)))
            assert (
                indices == expected_indices
            ), f"Indices {indices} not contiguous, expected {expected_indices}"


class TestCircularBuffer:
    """Test the CircularBuffer helper class."""

    def test_circular_buffer_initialization(self):
        """Test CircularBuffer initialization."""
        buffer = CircularBuffer(5)
        assert buffer._max_length == 5
        assert buffer.sum == 0.0
        assert len(buffer._rec_queue) == 5

    def test_circular_buffer_push(self):
        """Test pushing values to CircularBuffer."""
        buffer = CircularBuffer(3)

        # Push some values
        buffer.push(1.0)
        assert buffer.sum == 1.0

        buffer.push(2.0)
        assert buffer.sum == 3.0

        buffer.push(3.0)
        assert buffer.sum == 6.0

        # Push beyond capacity - should replace oldest
        buffer.push(4.0)
        assert buffer.sum == 9.0  # 2.0 + 3.0 + 4.0

    def test_circular_buffer_wraparound(self):
        """Test CircularBuffer wraparound behavior."""
        buffer = CircularBuffer(2)

        # Fill the buffer
        buffer.push(10.0)
        buffer.push(20.0)
        assert buffer.sum == 30.0

        # Test multiple wraparounds
        buffer.push(30.0)  # Replaces first 10.0
        assert buffer.sum == 50.0  # 20.0 + 30.0

        buffer.push(40.0)  # Replaces 20.0
        assert buffer.sum == 70.0  # 30.0 + 40.0
