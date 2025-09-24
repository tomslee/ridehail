"""
Integration and scenario tests for RideHailSimulation.

Tests for multi-block simulations, dispatch algorithms, and complex scenarios.
"""

import pytest
import math
from ridehail.simulation import RideHailSimulation
from ridehail.atom import DispatchMethod, VehiclePhase, TripPhase, Equilibration


class TestMultiBlockSimulation:
    """Test long-running simulation scenarios."""

    def test_long_simulation_stability(self, basic_config):
        """Test that simulation remains stable over many blocks."""
        basic_config.time_blocks.value = 1000
        basic_config.base_demand.value = 1.0

        sim = RideHailSimulation(basic_config)
        results = sim.simulate()

        # Should complete without crashing
        assert results is not None
        assert sim.block_index == basic_config.time_blocks.value

        # End state should be reasonable
        end_state = results.end_state
        assert 0 <= end_state["vehicle_fraction_p1"] <= 1
        assert 0 <= end_state["vehicle_fraction_p2"] <= 1
        assert 0 <= end_state["vehicle_fraction_p3"] <= 1

    def test_demand_variation_scenario(self):
        """Test simulation with varying demand using impulses."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 8
        config.vehicle_count.value = 10
        config.base_demand.value = 0.5
        config.time_blocks.value = 300
        config.animate.value = False
        config.equilibrate.value = False

        # Add impulses to change demand mid-simulation
        config.impulse_list.value = [
            {'block': 100, 'base_demand': 2.0},  # Increase demand
            {'block': 200, 'base_demand': 0.1},  # Decrease demand
        ]

        sim = RideHailSimulation(config)
        results = sim.simulate()

        assert results is not None

        # Simulation should adapt to demand changes without crashing
        end_state = results.end_state
        assert end_state["mean_vehicle_count"] == 10

    def test_vehicle_count_variation_scenario(self):
        """Test simulation with varying vehicle count using impulses."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 8
        config.vehicle_count.value = 5
        config.base_demand.value = 1.0
        config.time_blocks.value = 300
        config.animate.value = False
        config.equilibrate.value = False

        # Add impulses to change vehicle count mid-simulation
        config.impulse_list.value = [
            {'block': 100, 'vehicle_count': 15},  # Increase vehicles
            {'block': 200, 'vehicle_count': 3},   # Decrease vehicles
        ]

        sim = RideHailSimulation(config)
        results = sim.simulate()

        assert results is not None

        # Final vehicle count should reflect last impulse
        assert len(sim.vehicles) == 3

    def test_city_size_change_scenario(self):
        """Test simulation adaptation to city size changes."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 6
        config.vehicle_count.value = 5
        config.base_demand.value = 0.8
        config.time_blocks.value = 200
        config.animate.value = False
        config.equilibrate.value = False

        # Change city size mid-simulation
        config.impulse_list.value = [
            {'block': 100, 'city_size': 10},
        ]

        sim = RideHailSimulation(config)
        results = sim.simulate()

        assert results is not None
        assert sim.city_size == 10

        # Vehicles should be repositioned within new city bounds
        for vehicle in sim.vehicles:
            assert 0 <= vehicle.location[0] < 10
            assert 0 <= vehicle.location[1] < 10


class TestDispatchAlgorithms:
    """Test different dispatch algorithms."""

    @pytest.mark.parametrize("dispatch_method", [
        DispatchMethod.DEFAULT,
        DispatchMethod.RANDOM,
        DispatchMethod.P1_LEGACY,
        DispatchMethod.FORWARD_DISPATCH,
    ])
    def test_dispatch_methods(self, dispatch_method):
        """Test that all dispatch methods work correctly."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 8
        config.vehicle_count.value = 10
        config.base_demand.value = 1.0
        config.time_blocks.value = 200
        config.dispatch_method.value = dispatch_method
        config.animate.value = False
        config.equilibrate.value = False
        config.random_number_seed.value = 42

        sim = RideHailSimulation(config)
        results = sim.simulate()

        assert results is not None

        # All dispatch methods should complete trips
        end_state = results.end_state
        assert end_state.get("trip_distance", 0) > 0

        # Should have some utilization
        assert end_state["vehicle_fraction_p3"] > 0

    def test_forward_dispatch_effectiveness(self):
        """Test that forward dispatch actually uses forward dispatching."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 12
        config.vehicle_count.value = 20
        config.base_demand.value = 2.0
        config.time_blocks.value = 300
        config.dispatch_method.value = DispatchMethod.FORWARD_DISPATCH
        config.forward_dispatch_bias.value = 0.5
        config.animate.value = False
        config.equilibrate.value = False
        config.random_number_seed.value = 42

        sim = RideHailSimulation(config)
        results = sim.simulate()

        end_state = results.end_state

        # Should have some forward dispatch usage
        if "forward_dispatch_fraction" in end_state:
            forward_fraction = end_state["forward_dispatch_fraction"]
            assert forward_fraction > 0

    def test_dispatch_comparison(self):
        """Compare different dispatch methods on same scenario."""
        from ridehail.config import RideHailConfig

        base_config_params = {
            "city_size": 10,
            "vehicle_count": 15,
            "base_demand": 1.5,
            "time_blocks": 200,
            "animate": False,
            "equilibrate": False,
            "random_number_seed": 123,
        }

        results = {}

        for method in [DispatchMethod.DEFAULT, DispatchMethod.RANDOM]:
            config = RideHailConfig(use_config_file=False)
            for key, value in base_config_params.items():
                getattr(config, key).value = value
            config.dispatch_method.value = method

            sim = RideHailSimulation(config)
            result = sim.simulate()
            results[method] = result.end_state

        # Both methods should achieve reasonable performance
        for method, end_state in results.items():
            assert end_state["vehicle_fraction_p3"] > 0.1  # Some utilization
            assert end_state.get("trip_distance", 0) > 0   # Some completed trips


class TestEquilibrationScenarios:
    """Test equilibration in various scenarios."""

    def test_price_equilibration_convergence(self):
        """Test that price equilibration converges to reasonable values."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 10
        config.vehicle_count.value = 10
        config.base_demand.value = 2.0
        config.time_blocks.value = 500
        config.equilibrate.value = True
        config.equilibration.value = Equilibration.PRICE
        config.equilibration_interval.value = 20
        config.price.value = 1.0
        config.platform_commission.value = 0.2
        config.reservation_wage.value = 0.5
        config.demand_elasticity.value = 0.3
        config.animate.value = False
        config.random_number_seed.value = 42

        sim = RideHailSimulation(config)
        results = sim.simulate()

        assert results is not None

        # Should achieve some equilibrium
        end_state = results.end_state
        assert end_state["mean_vehicle_count"] > 0
        assert end_state["vehicle_fraction_p3"] > 0

    def test_wait_fraction_equilibration(self):
        """Test wait fraction equilibration."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 8
        config.vehicle_count.value = 8
        config.base_demand.value = 1.0
        config.time_blocks.value = 400
        config.equilibrate.value = True
        config.equilibration.value = Equilibration.WAIT_FRACTION
        config.wait_fraction.value = 0.3  # Target 30% wait time
        config.equilibration_interval.value = 20
        config.animate.value = False
        config.random_number_seed.value = 42

        sim = RideHailSimulation(config)
        results = sim.simulate()

        assert results is not None

        # Should approach target wait fraction
        end_state = results.end_state
        if "mean_trip_wait_fraction" in end_state:
            actual_wait_fraction = end_state["mean_trip_wait_fraction"]
            target_wait_fraction = 0.3
            # Should be reasonably close to target (within 50% tolerance)
            assert abs(actual_wait_fraction - target_wait_fraction) < target_wait_fraction * 0.5


class TestComplexScenarios:
    """Test complex real-world-like scenarios."""

    def test_rush_hour_simulation(self):
        """Test simulation of rush hour demand patterns."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 16
        config.vehicle_count.value = 25
        config.base_demand.value = 0.5  # Start low
        config.time_blocks.value = 400
        config.animate.value = False
        config.equilibrate.value = False

        # Simulate rush hour with impulses
        config.impulse_list.value = [
            {'block': 100, 'base_demand': 3.0},  # Morning rush
            {'block': 200, 'base_demand': 1.0},  # Midday
            {'block': 300, 'base_demand': 3.5},  # Evening rush
        ]

        sim = RideHailSimulation(config)
        results = sim.simulate()

        assert results is not None

        # Should handle demand spikes without crashing
        end_state = results.end_state
        assert end_state["mean_vehicle_count"] == 25
        assert end_state.get("trip_distance", 0) > 0

    def test_inhomogeneous_city_scenario(self):
        """Test simulation with inhomogeneous trip distribution."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 12
        config.vehicle_count.value = 15
        config.base_demand.value = 1.2
        config.time_blocks.value = 300
        config.inhomogeneity.value = 0.7  # High concentration in center
        config.animate.value = False
        config.equilibrate.value = False
        config.random_number_seed.value = 42

        sim = RideHailSimulation(config)
        results = sim.simulate()

        assert results is not None

        # Should complete simulation successfully
        end_state = results.end_state
        assert end_state.get("trip_distance", 0) > 0

    def test_high_demand_scenario(self):
        """Test simulation under very high demand conditions."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 8
        config.vehicle_count.value = 5
        config.base_demand.value = 5.0  # Very high demand
        config.time_blocks.value = 200
        config.animate.value = False
        config.equilibrate.value = False
        config.random_number_seed.value = 42

        sim = RideHailSimulation(config)
        results = sim.simulate()

        assert results is not None

        # Should handle high demand gracefully
        end_state = results.end_state

        # Vehicles should be highly utilized
        assert end_state["vehicle_fraction_p3"] > 0.3

        # Should have high wait times due to insufficient supply
        if "mean_trip_wait_time" in end_state:
            assert end_state["mean_trip_wait_time"] > 0

    def test_large_city_scenario(self, large_config):
        """Test simulation in a large city configuration."""
        sim = RideHailSimulation(large_config)
        results = sim.simulate()

        assert results is not None

        # Should handle large scale without issues
        end_state = results.end_state
        assert end_state["mean_vehicle_count"] == 50
        assert end_state.get("trip_distance", 0) > 0

    def test_minimal_resources_scenario(self):
        """Test simulation with very limited resources."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 6
        config.vehicle_count.value = 1  # Single vehicle
        config.base_demand.value = 2.0  # High demand
        config.time_blocks.value = 150
        config.animate.value = False
        config.equilibrate.value = False
        config.random_number_seed.value = 42

        sim = RideHailSimulation(config)
        results = sim.simulate()

        assert results is not None

        # Should handle resource constraint gracefully
        end_state = results.end_state
        assert end_state["mean_vehicle_count"] == 1

        # Single vehicle should be highly utilized
        assert end_state["vehicle_fraction_p1"] < 0.8  # Not idle all the time