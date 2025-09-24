# Ridehail Simulation Regression Tests

Comprehensive regression test suite for the core ridehail simulation functionality.

## Overview

This test suite provides extensive coverage of the `RideHailSimulation` class and related components, focusing on:

- **Core functionality**: Initialization, block simulation, state management
- **Mathematical invariants**: Fundamental identities and conservation laws
- **Integration scenarios**: Multi-block simulations, dispatch algorithms, complex scenarios
- **Performance baselines**: Timing benchmarks and memory usage monitoring
- **Regression protection**: Deterministic output validation and known-good baselines

## Test Structure

```
test/regression/
├── conftest.py                      # Fixtures and test configuration
├── test_simulation_core.py          # Core functionality tests
├── test_mathematical_invariants.py  # Mathematical identity tests
├── test_integration_scenarios.py    # Integration and scenario tests
├── test_performance_regression.py   # Performance and regression tests
├── pytest.ini                      # Pytest configuration
└── README.md                       # This file
```

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install -r requirements-test.txt
```

### Basic Test Execution

Run all regression tests:
```bash
pytest test/regression/
```

Run with coverage reporting:
```bash
pytest test/regression/ --cov=ridehail --cov-report=html --cov-report=term
```

### Selective Test Execution

Run only fast tests (exclude slow tests):
```bash
pytest test/regression/ -m "not slow"
```

Run only core functionality tests:
```bash
pytest test/regression/test_simulation_core.py
```

Run only mathematical invariant tests:
```bash
pytest test/regression/test_mathematical_invariants.py
```

Run with parallel execution:
```bash
pytest test/regression/ -n auto
```

### Performance Tests

Run performance baseline tests:
```bash
pytest test/regression/test_performance_regression.py -m performance
```

## Test Categories

### Core Functionality Tests (`test_simulation_core.py`)

- **Initialization**: Configuration validation, vehicle setup, history buffer initialization
- **Block Simulation**: Single-block mechanics, vehicle movement, trip generation
- **State Management**: Phase consistency, trip-vehicle consistency, garbage collection
- **CircularBuffer**: Helper class functionality

### Mathematical Invariant Tests (`test_mathematical_invariants.py`)

- **Fundamental Identities**:
  - P1 + P2 + P3 = 1.0 (vehicle phase fractions sum to one)
  - n * P3 = r * l (vehicle busy time equals passenger ride time)
  - n * P2 = r * w (vehicle dispatch time equals passenger wait time)
- **Conservation Laws**: Vehicle count preservation, trip completion consistency
- **Statistical Properties**: Fraction bounds, positive values, utilization consistency
- **Edge Cases**: No demand, no vehicles, single vehicle scenarios

### Integration Scenarios (`test_integration_scenarios.py`)

- **Multi-block Simulations**: Long-running stability, demand variation, parameter changes
- **Dispatch Algorithms**: All dispatch methods (DEFAULT, RANDOM, P1_LEGACY, FORWARD_DISPATCH)
- **Equilibration**: Price and wait-fraction equilibration convergence
- **Complex Scenarios**: Rush hour patterns, inhomogeneous cities, high demand, large scale

### Performance & Regression (`test_performance_regression.py`)

- **Performance Baselines**: Initialization time, block execution time, scaling behavior
- **Memory Usage**: Long simulation stability, repeated simulation memory, large simulation bounds
- **Regression Protection**: Deterministic output consistency, known-good baselines
- **Stress Tests**: Extreme parameters, very long simulations

## Key Fixtures

### Configuration Fixtures
- `basic_config`: Standard 8x8 city with 5 vehicles
- `minimal_config`: Small 4x4 city with 2 vehicles for fast tests
- `large_config`: Large 20x20 city with 50 vehicles for stress testing
- `equilibration_config`: Configuration with price equilibration enabled

### Simulation Fixtures
- `basic_simulation`: Pre-initialized simulation instance
- `completed_simulation`: Fully executed simulation with results

### Helper Classes
- `SimulationAsserter`: Specialized assertions for simulation-specific validations

## Mathematical Identities Tested

The test suite validates these fundamental relationships:

1. **Phase Conservation**: `P1 + P2 + P3 = 1`
   - All vehicles are always in exactly one phase

2. **Busy Time Identity**: `n * P3 = r * l`
   - Total vehicle time with passengers equals total passenger ride time

3. **Wait Time Identity**: `n * P2 = r * w`
   - Total vehicle time dispatching equals total passenger wait time

4. **Utilization Bounds**: All fractions ∈ [0,1], positive values ≥ 0

## Performance Expectations

- **Initialization**: < 1 second
- **Single Block**: < 0.1 seconds
- **Full Simulation** (100 blocks): < 10 seconds
- **Memory Growth**: < 100MB for long simulations
- **Scaling**: Reasonable performance up to 20x20 cities with 100 vehicles

## Regression Protection

- **Deterministic Testing**: Fixed random seeds ensure reproducible results
- **Golden Master**: Known-good baselines for regression detection
- **Parameter Sensitivity**: Validates expected behavior under parameter changes
- **Cross-Algorithm Consistency**: Dispatch algorithms produce reasonable results

## Adding New Tests

When adding new tests:

1. Use appropriate fixtures from `conftest.py`
2. Follow the existing naming conventions
3. Add docstrings explaining the test purpose
4. Use the `SimulationAsserter` for simulation-specific validations
5. Mark slow tests with `@pytest.mark.slow`
6. Update this README if adding new categories

## Troubleshooting

### Common Issues

- **Import Errors**: Ensure project root is in Python path
- **Random Failures**: Use fixed random seeds for reproducible tests
- **Slow Performance**: Use minimal configurations or skip slow tests
- **Memory Issues**: Monitor system resources for large-scale tests

### Test Debugging

Run with verbose output:
```bash
pytest test/regression/ -v -s
```

Run specific test with full traceback:
```bash
pytest test/regression/test_simulation_core.py::TestSimulationInitialization::test_basic_initialization -v --tb=long
```

## Coverage Goals

Target coverage metrics:
- **Overall**: 95%+ of `ridehail/simulation.py`
- **Core Methods**: 100% of critical simulation methods
- **Edge Cases**: Comprehensive boundary condition testing
- **Integration**: All dispatch methods and equilibration scenarios