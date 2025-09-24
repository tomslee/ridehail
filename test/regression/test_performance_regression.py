"""
Performance and regression protection tests for RideHailSimulation.

Tests for performance baselines, memory usage, and regression detection.
"""

import pytest
import time
import gc
import psutil
import os
from ridehail.simulation import RideHailSimulation
from ridehail.atom import DispatchMethod


class TestPerformanceBaselines:
    """Test performance baselines for critical operations."""

    def test_simulation_initialization_time(self, basic_config):
        """Test that simulation initialization completes within reasonable time."""
        start_time = time.time()
        sim = RideHailSimulation(basic_config)
        end_time = time.time()

        initialization_time = end_time - start_time

        # Initialization should complete within 1 second
        assert initialization_time < 1.0

    def test_single_block_performance(self, basic_config):
        """Test that a single block execution completes within reasonable time."""
        sim = RideHailSimulation(basic_config)

        # Warm up
        sim.next_block(block=0)

        # Time a single block
        start_time = time.time()
        sim.next_block(block=1)
        end_time = time.time()

        block_time = end_time - start_time

        # Single block should complete within 0.1 seconds
        assert block_time < 0.1

    @pytest.mark.parametrize("city_size,vehicle_count", [
        (8, 10),
        (12, 25),
        (16, 50),
        (20, 100),
    ])
    def test_scaling_performance(self, city_size, vehicle_count):
        """Test performance scaling with city size and vehicle count."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = city_size
        config.vehicle_count.value = vehicle_count
        config.base_demand.value = min(2.0, vehicle_count * 0.1)
        config.time_blocks.value = 50
        config.animate.value = False
        config.equilibrate.value = False
        config.random_number_seed.value = 42

        start_time = time.time()
        sim = RideHailSimulation(config)
        results = sim.simulate()
        end_time = time.time()

        total_time = end_time - start_time

        # Time should scale reasonably with problem size
        # Rough estimate: should complete within 10 seconds for largest case
        assert total_time < 10.0

        # Verify simulation completed successfully
        assert results is not None

    def test_dispatch_algorithm_performance(self):
        """Compare performance of different dispatch algorithms."""
        from ridehail.config import RideHailConfig

        base_config_params = {
            "city_size": 12,
            "vehicle_count": 20,
            "base_demand": 1.5,
            "time_blocks": 100,
            "animate": False,
            "equilibrate": False,
            "random_number_seed": 42,
        }

        performance_results = {}

        for method in [DispatchMethod.DEFAULT, DispatchMethod.RANDOM, DispatchMethod.FORWARD_DISPATCH]:
            config = RideHailConfig(use_config_file=False)
            for key, value in base_config_params.items():
                getattr(config, key).value = value
            config.dispatch_method.value = method

            start_time = time.time()
            sim = RideHailSimulation(config)
            results = sim.simulate()
            end_time = time.time()

            performance_results[method] = {
                "time": end_time - start_time,
                "results": results
            }

        # All methods should complete within reasonable time
        for method, perf_data in performance_results.items():
            assert perf_data["time"] < 5.0
            assert perf_data["results"] is not None

        # No dispatch method should be dramatically slower than others
        times = [perf_data["time"] for perf_data in performance_results.values()]
        max_time = max(times)
        min_time = min(times)

        # Slowest should not be more than 3x slower than fastest
        if min_time > 0:
            assert max_time / min_time < 3.0


class TestMemoryUsage:
    """Test memory usage patterns and detect leaks."""

    def get_memory_usage(self):
        """Get current memory usage in MB."""
        process = psutil.Process(os.getpid())
        return process.memory_info().rss / 1024 / 1024  # Convert to MB

    def test_memory_stability_long_simulation(self):
        """Test that memory usage remains stable during long simulation."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 10
        config.vehicle_count.value = 15
        config.base_demand.value = 1.0
        config.time_blocks.value = 1000  # Long simulation
        config.animate.value = False
        config.equilibrate.value = False
        config.random_number_seed.value = 42

        # Force garbage collection before starting
        gc.collect()
        initial_memory = self.get_memory_usage()

        sim = RideHailSimulation(config)
        results = sim.simulate()

        # Force garbage collection after simulation
        gc.collect()
        final_memory = self.get_memory_usage()

        memory_growth = final_memory - initial_memory

        # Memory growth should be reasonable (less than 100MB for this test)
        assert memory_growth < 100

        # Verify simulation completed successfully
        assert results is not None

    def test_repeated_simulation_memory(self):
        """Test memory usage when running multiple simulations."""
        from ridehail.config import RideHailConfig

        # Force initial garbage collection
        gc.collect()
        initial_memory = self.get_memory_usage()

        # Run multiple simulations
        for i in range(10):
            config = RideHailConfig(use_config_file=False)
            config.city_size.value = 8
            config.vehicle_count.value = 8
            config.base_demand.value = 0.8
            config.time_blocks.value = 50
            config.animate.value = False
            config.equilibrate.value = False
            config.random_number_seed.value = i

            sim = RideHailSimulation(config)
            results = sim.simulate()
            assert results is not None

            # Clear reference to simulation
            del sim
            del results

        # Force garbage collection
        gc.collect()
        final_memory = self.get_memory_usage()

        memory_growth = final_memory - initial_memory

        # Memory growth should be minimal (less than 50MB)
        assert memory_growth < 50

    def test_large_simulation_memory_bounds(self):
        """Test memory usage bounds for large simulations."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 20
        config.vehicle_count.value = 100
        config.base_demand.value = 3.0
        config.time_blocks.value = 200
        config.animate.value = False
        config.equilibrate.value = False
        config.random_number_seed.value = 42

        gc.collect()
        initial_memory = self.get_memory_usage()

        sim = RideHailSimulation(config)

        # Check memory during simulation initialization
        init_memory = self.get_memory_usage()
        init_growth = init_memory - initial_memory

        # Initialization should not use excessive memory
        assert init_growth < 200  # Less than 200MB

        results = sim.simulate()

        gc.collect()
        final_memory = self.get_memory_usage()
        total_growth = final_memory - initial_memory

        # Total memory growth should be reasonable
        assert total_growth < 500  # Less than 500MB

        assert results is not None


class TestRegressionProtection:
    """Test for regression detection using golden master approach."""

    def test_deterministic_output_consistency(self):
        """Test that identical configurations produce identical results."""
        from ridehail.config import RideHailConfig

        # Create two identical configurations
        def create_config():
            config = RideHailConfig(use_config_file=False)
            config.city_size.value = 8
            config.vehicle_count.value = 10
            config.base_demand.value = 1.0
            config.time_blocks.value = 100
            config.animate.value = False
            config.equilibrate.value = False
            config.random_number_seed.value = 12345  # Fixed seed
            return config

        config1 = create_config()
        config2 = create_config()

        sim1 = RideHailSimulation(config1)
        results1 = sim1.simulate()

        sim2 = RideHailSimulation(config2)
        results2 = sim2.simulate()

        # Key results should be identical
        end_state1 = results1.end_state
        end_state2 = results2.end_state

        # Compare key metrics
        key_metrics = [
            "mean_vehicle_count", "mean_request_rate",
            "vehicle_fraction_p1", "vehicle_fraction_p2", "vehicle_fraction_p3",
            "mean_trip_wait_time", "mean_trip_distance"
        ]

        for metric in key_metrics:
            if metric in end_state1 and metric in end_state2:
                assert abs(end_state1[metric] - end_state2[metric]) < 1e-10, \
                    f"Metric {metric} differs: {end_state1[metric]} vs {end_state2[metric]}"

    def test_known_good_baseline_small(self):
        """Test against a known good baseline for small simulation."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 6
        config.vehicle_count.value = 5
        config.base_demand.value = 0.8
        config.time_blocks.value = 200
        config.results_window.value = 50
        config.animate.value = False
        config.equilibrate.value = False
        config.random_number_seed.value = 999

        sim = RideHailSimulation(config)
        results = sim.simulate()

        end_state = results.end_state

        # These values represent a known good baseline
        # Update if simulation logic changes intentionally
        expected_ranges = {
            "mean_vehicle_count": (5.0, 5.0),  # Exact
            "vehicle_fraction_p1": (0.0, 1.0),  # Should be in valid range
            "vehicle_fraction_p2": (0.0, 1.0),
            "vehicle_fraction_p3": (0.0, 1.0),
        }

        for metric, (min_val, max_val) in expected_ranges.items():
            if metric in end_state:
                value = end_state[metric]
                assert min_val <= value <= max_val, \
                    f"Metric {metric} = {value} outside expected range [{min_val}, {max_val}]"

        # Phase fractions should sum to 1
        phase_sum = (end_state["vehicle_fraction_p1"] +
                    end_state["vehicle_fraction_p2"] +
                    end_state["vehicle_fraction_p3"])
        assert abs(phase_sum - 1.0) < 0.01

    def test_configuration_parameter_sensitivity(self):
        """Test that small parameter changes produce expected result changes."""
        from ridehail.config import RideHailConfig

        base_params = {
            "city_size": 8,
            "vehicle_count": 8,
            "base_demand": 1.0,
            "time_blocks": 150,
            "animate": False,
            "equilibrate": False,
            "random_number_seed": 42
        }

        def run_simulation(params):
            config = RideHailConfig(use_config_file=False)
            for key, value in params.items():
                getattr(config, key).value = value

            sim = RideHailSimulation(config)
            return sim.simulate()

        # Baseline
        baseline_results = run_simulation(base_params)

        # Test demand sensitivity
        high_demand_params = base_params.copy()
        high_demand_params["base_demand"] = 2.0
        high_demand_results = run_simulation(high_demand_params)

        # Higher demand should generally lead to higher utilization
        baseline_p3 = baseline_results.end_state["vehicle_fraction_p3"]
        high_demand_p3 = high_demand_results.end_state["vehicle_fraction_p3"]

        # With higher demand, should have higher utilization (or at least not lower)
        assert high_demand_p3 >= baseline_p3 - 0.1

        # Test vehicle count sensitivity
        more_vehicles_params = base_params.copy()
        more_vehicles_params["vehicle_count"] = 16
        more_vehicles_results = run_simulation(more_vehicles_params)

        # More vehicles should lead to lower utilization per vehicle
        more_vehicles_p3 = more_vehicles_results.end_state["vehicle_fraction_p3"]
        assert more_vehicles_p3 <= baseline_p3 + 0.1  # Should not be much higher


class TestStressTests:
    """Stress tests for edge cases and extreme conditions."""

    def test_zero_time_blocks(self):
        """Test simulation with zero time blocks."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 4
        config.vehicle_count.value = 2
        config.base_demand.value = 0.5
        config.time_blocks.value = 0  # Run indefinitely
        config.animate.value = False
        config.equilibrate.value = False

        sim = RideHailSimulation(config)

        # Should be able to create simulation without crashing
        assert sim is not None
        assert sim.time_blocks == 0

        # Don't actually run the infinite simulation, just test setup

    def test_extreme_parameter_values(self):
        """Test with extreme but valid parameter values."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 2  # Minimum practical city
        config.vehicle_count.value = 1  # Single vehicle
        config.base_demand.value = 0.01  # Very low demand
        config.time_blocks.value = 10  # Very short simulation
        config.animate.value = False
        config.equilibrate.value = False
        config.random_number_seed.value = 1

        sim = RideHailSimulation(config)
        results = sim.simulate()

        # Should complete without crashing
        assert results is not None

    @pytest.mark.slow
    def test_very_long_simulation(self):
        """Test very long simulation (marked as slow test)."""
        from ridehail.config import RideHailConfig

        config = RideHailConfig(use_config_file=False)
        config.city_size.value = 8
        config.vehicle_count.value = 8
        config.base_demand.value = 0.8
        config.time_blocks.value = 5000  # Very long
        config.animate.value = False
        config.equilibrate.value = False
        config.random_number_seed.value = 42

        start_time = time.time()
        sim = RideHailSimulation(config)
        results = sim.simulate()
        end_time = time.time()

        # Should complete successfully
        assert results is not None
        assert sim.block_index == 5000

        # Performance should still be reasonable
        total_time = end_time - start_time
        assert total_time < 60  # Less than 1 minute