"""
Pytest configuration and fixtures for regression tests.
"""

import pytest
import sys
from pathlib import Path

from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.atom import Equilibration

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture
def basic_config():
    """Create a basic configuration for testing."""
    config = RideHailConfig(use_config_file=False)
    config.title.value = "Test simulation"
    config.city_size.value = 8
    config.vehicle_count.value = 5
    config.base_demand.value = 0.5
    config.min_trip_distance.value = 0
    config.max_trip_distance.value = 8
    config.time_blocks.value = 100
    config.results_window.value = 20
    config.smoothing_window.value = 10
    config.animate.value = False
    config.equilibrate.value = False
    config.run_sequence.value = False
    config.use_city_scale.value = False
    config.random_number_seed.value = 42  # Fixed seed for reproducibility
    config.inhomogeneity.value = 0.0
    config.idle_vehicles_moving.value = True
    return config


@pytest.fixture
def minimal_config():
    """Create a minimal configuration for fast tests."""
    config = RideHailConfig(use_config_file=False)
    config.city_size.value = 4
    config.vehicle_count.value = 2
    config.base_demand.value = 0.2
    config.time_blocks.value = 20
    config.results_window.value = 5
    config.smoothing_window.value = 5
    config.animate.value = False
    config.equilibrate.value = False
    config.run_sequence.value = False
    config.random_number_seed.value = 123
    return config


@pytest.fixture
def large_config():
    """Create a larger configuration for stress testing."""
    config = RideHailConfig(use_config_file=False)
    config.city_size.value = 20
    config.vehicle_count.value = 50
    config.base_demand.value = 2.0
    config.time_blocks.value = 500
    config.results_window.value = 100
    config.smoothing_window.value = 50
    config.animate.value = False
    config.equilibrate.value = False
    config.run_sequence.value = False
    config.random_number_seed.value = 456
    return config


@pytest.fixture
def equilibration_config():
    """Create configuration with equilibration enabled."""
    config = RideHailConfig(use_config_file=False)
    config.city_size.value = 10
    config.vehicle_count.value = 10
    config.base_demand.value = 1.0
    config.time_blocks.value = 200
    config.results_window.value = 50
    config.smoothing_window.value = 20
    config.animate.value = False
    config.equilibrate.value = True
    config.equilibration.value = Equilibration.PRICE
    config.run_sequence.value = False
    config.random_number_seed.value = 789
    config.price.value = 1.0
    config.platform_commission.value = 0.2
    config.reservation_wage.value = 0.5
    config.demand_elasticity.value = 0.5
    config.equilibration_interval.value = 10
    return config


@pytest.fixture
def basic_simulation(basic_config):
    """Create a basic simulation instance."""
    return RideHailSimulation(basic_config)


@pytest.fixture
def minimal_simulation(minimal_config):
    """Create a minimal simulation instance."""
    return RideHailSimulation(minimal_config)


@pytest.fixture
def completed_simulation(basic_config):
    """Create and run a complete simulation for result analysis."""
    sim = RideHailSimulation(basic_config)
    results = sim.simulate()
    return sim, results


class SimulationAsserter:
    """Helper class for making simulation-specific assertions."""

    @staticmethod
    def assert_vehicle_phases_sum_to_one(end_state, tolerance=0.01):
        """Assert that vehicle phase fractions sum to 1."""
        p1 = end_state.get("vehicle_fraction_p1", 0)
        p2 = end_state.get("vehicle_fraction_p2", 0)
        p3 = end_state.get("vehicle_fraction_p3", 0)
        phase_sum = p1 + p2 + p3
        assert abs(phase_sum - 1.0) < tolerance, (
            f"Vehicle phases sum to {phase_sum}, expected ~1.0"
        )

    @staticmethod
    def assert_identity_p3(end_state, tolerance=0.1):
        """Assert the fundamental identity n*p3 = r*l."""
        n = end_state["mean_vehicle_count"]
        p3 = end_state["vehicle_fraction_p3"]
        r = end_state["mean_request_rate"]
        l = end_state["mean_trip_distance"]

        left_side = n * p3
        right_side = r * l
        diff = abs(left_side - right_side)

        assert diff < tolerance, (
            f"Identity n*p3 = r*l violated: {left_side:.3f} != {right_side:.3f} (diff: {diff:.3f})"
        )

    @staticmethod
    def assert_identity_p2(end_state, tolerance=0.1):
        """Assert the fundamental identity n*p2 = r*w."""
        n = end_state["mean_vehicle_count"]
        p2 = end_state["vehicle_fraction_p2"]
        r = end_state["mean_request_rate"]
        w = end_state["mean_trip_wait_time"]

        left_side = n * p2
        right_side = r * w
        diff = abs(left_side - right_side)

        assert diff < tolerance, (
            f"Identity n*p2 = r*w violated: {left_side:.3f} != {right_side:.3f} (diff: {diff:.3f})"
        )

    @staticmethod
    def assert_valid_fractions(end_state):
        """Assert all fraction values are between 0 and 1."""
        fraction_keys = [
            "vehicle_fraction_p1",
            "vehicle_fraction_p2",
            "vehicle_fraction_p3",
            "mean_trip_wait_fraction",
            "forward_dispatch_fraction",
        ]

        for key in fraction_keys:
            if key in end_state:
                value = end_state[key]
                assert 0.0 <= value <= 1.0, (
                    f"{key} = {value} is not a valid fraction [0,1]"
                )

    @staticmethod
    def assert_positive_values(end_state):
        """Assert that values that should be positive are positive."""
        positive_keys = [
            "mean_vehicle_count",
            "mean_request_rate",
            "mean_trip_distance",
            "mean_trip_wait_time",
            "trip_distance",
        ]

        for key in positive_keys:
            if key in end_state and end_state[key] is not None:
                value = end_state[key]
                assert value >= 0, f"{key} = {value} should be non-negative"


@pytest.fixture
def asserter():
    """Provide the simulation asserter helper."""
    return SimulationAsserter()


# Test data generators
def generate_config_variations():
    """Generate various configuration combinations for parametrized tests."""
    variations = []

    # City sizes
    city_sizes = [4, 8, 12, 16]

    # Vehicle counts (relative to city size)
    vehicle_ratios = [0.1, 0.5, 1.0, 2.0]

    # Demand levels
    demand_levels = [0.1, 0.5, 1.0, 2.0]

    for city_size in city_sizes:
        for ratio in vehicle_ratios:
            for demand in demand_levels:
                vehicle_count = max(1, int(city_size * ratio))
                variations.append((city_size, vehicle_count, demand))

    return variations


@pytest.fixture(scope="session")
def config_variations():
    """Provide configuration variations for parametrized tests."""
    return generate_config_variations()
