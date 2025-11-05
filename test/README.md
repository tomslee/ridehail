# Ridehail Simulation Regression Tests

This directory contains regression tests that verify simulation results remain consistent across code changes.

## Overview

The regression test system compares simulation results against expected values stored in the `[RESULTS]` section of configuration files. This ensures that changes to the simulation code don't inadvertently alter behavior.

## Quick Start

### Running Tests

```bash
# Run all regression tests
pytest test/test_regression.py

# Run with verbose output
pytest test/test_regression.py -v

# Run specific config test
pytest test/test_regression.py -k city
```

### Adding New Tests

1. Create a `.config` file in the `test/` directory
2. Ensure it has `random_number_seed` set for reproducibility
3. Run the simulation once to generate the `[RESULTS]` section:
   ```bash
   python -m ridehail test/your_test.config -a none -ad 0
   ```
4. Commit the config file - it will automatically be picked up by the test suite

### Updating Expected Results

When you intentionally change simulation logic and need to update expected results:

```bash
# Update all tests
pytest test/test_regression.py --update-expected

# Update specific test
pytest test/test_regression.py --update-expected -k city
```

## How It Works

### Test Process

1. **Extract expected results** from the `[RESULTS]` section of the original config file
2. **Copy config to temp location** to preserve the original
3. **Run simulation** with `-a none -ad 0` for maximum speed
4. **Extract actual results** from the temporary config file
5. **Compare results** with appropriate tolerances
6. **Clean up** temporary files

### Comparison Strategy

The test system uses intelligent comparison based on metric type:

**Excluded** (not compared):
- `SIM_TIMESTAMP` - Always different
- `SIM_DURATION_SECONDS` - Varies with system load

**Exact match** (integer comparison):
- `SIM_BLOCKS_SIMULATED`
- `SIM_BLOCKS_ANALYZED`

**Tolerance-based** (floating-point comparison):
- All vehicle metrics (`VEHICLE_FRACTION_P1`, etc.)
- All trip metrics (`TRIP_MEAN_WAIT_FRACTION_TOTAL`, etc.)
- All validation metrics (`SIM_CHECK_*`, etc.)
- Default tolerances: 0.1% relative, 0.001 absolute

**Version warning** (warns but doesn't fail):
- `SIM_RIDEHAIL_VERSION` - Useful to know if versions differ

### Example Test Failure Output

```
============================================================
REGRESSION TEST FAILURE: city.config
============================================================
vehicle_fraction_p1:
  Expected: 0.327
  Actual:   0.329
  Diff:     +0.002 (+0.61%)

trip_mean_wait_fraction_total:
  Expected: 0.196
  Actual:   0.198
  Diff:     +0.002 (+1.02%)
============================================================
To update expected results, run:
  pytest test/test_regression.py --update-expected -k city
============================================================
```

## Test Configuration Best Practices

### Reproducibility

- **Always set `random_number_seed`** to ensure deterministic results
- Use reasonable `time_blocks` values (avoid very long simulations)
- Document the purpose of each test config in the `title` field

### Test Coverage

Consider creating configs that test:
- Different city sizes
- Various vehicle counts and demand levels
- Equilibration scenarios
- Advanced dispatch algorithms
- Edge cases (e.g., very high demand, very low supply)

### Performance

- Keep `time_blocks` moderate (250-1000 for large cities, more for small ones)
- Tests run with `-a none -ad 0` for speed
- Entire test suite should complete in reasonable time (<5 minutes)

## Files

- `conftest.py` - Pytest configuration for `--update-expected` option
- `test_regression.py` - Main regression test implementation
- `*.config` - Test configuration files with `[RESULTS]` sections
- `README.md` - This file

## Integration with CI/CD

These tests are ideal for continuous integration:

```yaml
# Example GitHub Actions workflow
- name: Run regression tests
  run: pytest test/test_regression.py -v
```

The tests will fail if simulation results deviate beyond acceptable tolerances, catching unintended behavior changes.
