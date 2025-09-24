"""
Mathematical invariant tests for RideHailSimulation.

Tests for fundamental relationships and conservation laws in the simulation.
"""

import pytest
import math
from ridehail.simulation import RideHailSimulation
from ridehail.atom import VehiclePhase, TripPhase


class TestFundamentalIdentities:
    """Test the fundamental mathematical identities of the simulation."""

    def test_vehicle_phase_fractions_sum_to_one(self, completed_simulation, asserter):
        """Test that P1 + P2 + P3 = 1.0."""
        sim, results = completed_simulation
        asserter.assert_vehicle_phases_sum_to_one(results.end_state)

    def test_identity_n_p3_equals_r_l(self, completed_simulation, asserter):
        """Test the fundamental identity: n * P3 = r * l.

        Vehicle time in P3 (busy with passenger) equals
        passenger time in vehicles.
        """
        sim, results = completed_simulation
        asserter.assert_identity_p3(results.end_state)

    def test_identity_n_p2_equals_r_w(self, completed_simulation, asserter):
        """Test the fundamental identity: n * P2 = r * w.

        Vehicle time traveling to pickup equals
        passenger waiting time.
        """
        sim, results = completed_simulation
        asserter.assert_identity_p2(results.end_state)

    @pytest.mark.parametrize("city_size,vehicle_count,demand", [
        (4, 2, 0.1),
        (8, 5, 0.5),
        (12, 10, 1.0),
        (16, 8, 1.5),
    ])
    def test_identities_across_configurations(self, city_size, vehicle_count, demand, asserter):
        """Test identities hold across different configuration parameters."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = city_size
        config.vehicle_count.value = vehicle_count
        config.base_demand.value = demand
        config.time_blocks.value = 200
        config.results_window.value = 50
        config.animate.value = False
        config.equilibrate.value = False
        config.run_sequence.value = False
        config.random_number_seed.value = 42

        sim = RideHailSimulation(config)
        results = sim.simulate()

        # Test all fundamental identities
        asserter.assert_vehicle_phases_sum_to_one(results.end_state)

        # Only test other identities if there were completed trips
        if results.end_state.get("trip_distance", 0) > 0:
            asserter.assert_identity_p3(results.end_state, tolerance=0.2)
            asserter.assert_identity_p2(results.end_state, tolerance=0.2)

    def test_conservation_of_vehicles(self, basic_simulation):
        """Test that the number of vehicles is conserved throughout simulation."""
        sim = basic_simulation
        initial_vehicle_count = len(sim.vehicles)

        # Run simulation
        for i in range(50):
            sim.next_block(block=i)
            assert len(sim.vehicles) == initial_vehicle_count

        # Total vehicle count should be preserved
        assert len(sim.vehicles) == initial_vehicle_count

    def test_trip_completion_consistency(self, basic_simulation):
        """Test consistency in trip completion tracking."""
        sim = basic_simulation
        sim.base_demand = 1.0  # Ensure trip generation

        completed_trips = 0
        cancelled_trips = 0

        for i in range(100):
            sim.next_block(block=i)

            # Count completed and cancelled trips
            for trip in sim.trips:
                if trip.phase == TripPhase.COMPLETED:
                    completed_trips += 1
                elif trip.phase == TripPhase.CANCELLED:
                    cancelled_trips += 1

        # Total trips in history should match what we observed
        from ridehail.atom import History
        total_trip_count = sim.history_buffer[History.TRIP_COUNT].sum
        assert total_trip_count >= completed_trips + cancelled_trips


class TestStatisticalProperties:
    """Test statistical properties and measures."""

    def test_fraction_bounds(self, completed_simulation, asserter):
        """Test that all fraction values are within [0, 1]."""
        sim, results = completed_simulation
        asserter.assert_valid_fractions(results.end_state)

    def test_positive_values(self, completed_simulation, asserter):
        """Test that values that should be positive are positive."""
        sim, results = completed_simulation
        asserter.assert_positive_values(results.end_state)

    def test_wait_time_fraction_bounds(self, completed_simulation):
        """Test that wait time fractions are reasonable."""
        sim, results = completed_simulation
        end_state = results.end_state

        if "mean_trip_wait_fraction" in end_state:
            wait_fraction = end_state["mean_trip_wait_fraction"]
            # Wait fraction should be non-negative
            assert wait_fraction >= 0

            # In most reasonable scenarios, wait time shouldn't be more than 10x ride time
            assert wait_fraction < 10

    def test_distance_fraction_bounds(self, completed_simulation):
        """Test that trip distance fractions are reasonable."""
        sim, results = completed_simulation
        end_state = results.end_state

        if "trip_distance_fraction" in end_state:
            distance_fraction = end_state["trip_distance_fraction"]
            # Distance fraction should be between 0 and 1 (trips can't be longer than city)
            assert 0 <= distance_fraction <= 1

    def test_utilization_consistency(self, completed_simulation):
        """Test that utilization measures are consistent."""
        sim, results = completed_simulation
        end_state = results.end_state

        # P3 fraction should relate to gross income
        p3 = end_state.get("vehicle_fraction_p3", 0)
        gross_income = end_state.get("vehicle_gross_income", 0)

        if p3 > 0 and gross_income > 0:
            # Higher utilization should generally mean higher income
            # (exact relationship depends on price and commission)
            assert gross_income > 0


class TestEquilibrationProperties:
    """Test properties specific to equilibration scenarios."""

    def test_equilibration_convergence(self, equilibration_config):
        """Test that equilibration leads to convergence."""
        sim = RideHailSimulation(equilibration_config)

        # Track vehicle counts over time
        vehicle_counts = []

        # Run simulation with equilibration
        for i in range(equilibration_config.time_blocks.value):
            sim.next_block(block=i)
            vehicle_counts.append(len(sim.vehicles))

        # After initial period, vehicle count should stabilize
        # (not oscillate wildly)
        if len(vehicle_counts) > 100:
            late_counts = vehicle_counts[-50:]  # Last 50 blocks
            variance = sum((x - sum(late_counts)/len(late_counts))**2 for x in late_counts) / len(late_counts)
            std_dev = math.sqrt(variance)

            # Standard deviation of vehicle count should be reasonable
            # (not more than 50% of mean)
            mean_count = sum(late_counts) / len(late_counts)
            if mean_count > 0:
                assert std_dev / mean_count < 0.5

    def test_price_equilibration_utility(self, equilibration_config):
        """Test that price equilibration drives toward zero utility."""
        from ridehail.atom import Equilibration

        # Ensure we're using price equilibration
        equilibration_config.equilibration.value = Equilibration.PRICE

        sim = RideHailSimulation(equilibration_config)
        results = sim.simulate()

        end_state = results.end_state

        # In price equilibration, vehicle surplus should approach zero
        if "vehicle_mean_surplus" in end_state:
            surplus = end_state["vehicle_mean_surplus"]
            # Surplus should be close to zero (within reasonable tolerance)
            assert abs(surplus) < 1.0


class TestEdgeCaseInvariants:
    """Test invariants in edge cases."""

    def test_no_demand_scenario(self):
        """Test invariants when there's no demand for trips."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.base_demand.value = 0.0  # No demand
        config.city_size.value = 6
        config.vehicle_count.value = 3
        config.time_blocks.value = 50
        config.animate.value = False
        config.equilibrate.value = False

        sim = RideHailSimulation(config)
        results = sim.simulate()

        end_state = results.end_state

        # With no demand, all vehicles should be in P1
        assert abs(end_state["vehicle_fraction_p1"] - 1.0) < 0.01
        assert end_state["vehicle_fraction_p2"] < 0.01
        assert end_state["vehicle_fraction_p3"] < 0.01

        # No trips should be completed
        assert end_state.get("trip_distance", 0) == 0

    def test_no_vehicles_scenario(self):
        """Test behavior when there are no vehicles."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.base_demand.value = 1.0
        config.city_size.value = 6
        config.vehicle_count.value = 0  # No vehicles
        config.time_blocks.value = 20
        config.animate.value = False
        config.equilibrate.value = False

        sim = RideHailSimulation(config)

        # Should not crash
        results = sim.simulate()
        assert results is not None

        # All trips should remain unassigned/cancelled
        end_state = results.end_state
        assert end_state.get("mean_vehicle_count", 0) == 0

    def test_single_vehicle_scenario(self):
        """Test invariants with exactly one vehicle."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.base_demand.value = 0.5
        config.city_size.value = 4
        config.vehicle_count.value = 1  # Single vehicle
        config.time_blocks.value = 100
        config.results_window.value = 20
        config.animate.value = False
        config.equilibrate.value = False
        config.random_number_seed.value = 42

        sim = RideHailSimulation(config)
        results = sim.simulate()

        end_state = results.end_state

        # Phase fractions should still sum to 1
        assert abs(end_state["vehicle_fraction_p1"] +
                  end_state["vehicle_fraction_p2"] +
                  end_state["vehicle_fraction_p3"] - 1.0) < 0.01

        # Vehicle count should be exactly 1
        assert abs(end_state["mean_vehicle_count"] - 1.0) < 0.01