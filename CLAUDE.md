# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a ridehail simulation project that models the dynamics of ride-hailing services. The simulation supports multiple visualization modes, can run sequences of simulations, and includes both desktop and browser-based interfaces.

## Core Architecture

### Main Components

- **`run.py`**: Entry point that orchestrates simulations based on configuration files
- **`ridehail/`**: Core simulation package containing:
  - `config.py`: Configuration system with validation and parameter management
  - `simulation.py`: Core simulation engine
  - `animation.py`: Visualization components (console, matplotlib)
  - `dispatch.py`: Vehicle dispatch logic
  - `sequence.py`: Multi-simulation sequence runner
  - `atom.py`: Core data structures and enums

### Configuration System

The project uses a robust configuration system centered around `.config` files:
- Configuration files define simulation parameters (see examples: `test.config`, `metro.config`, `city.config`)
- Command-line arguments can override config file settings
- The `ConfigItem` class manages parameter validation, types, and defaults

## Development Commands

### Running Simulations

```bash
# Basic simulation run
python run.py <config_file>.config
# OR with uv
uv run run.py <config_file>.config

# Create new config file
python run.py -wc my_simulation.config

# Run with command line overrides (example: disable graphics)
python run.py <config_file>.config -dr None

# Get help on command line options
python run.py --help

# Run with profiling
python run.py --profile <config_file>.config
```

### Package Management

```bash
# Install dependencies
pip install -r requirements.txt
# OR with uv
uv pip install -r requirements.txt

# Build package
python -m build
# OR with uv
uv build --wheel --package ridehail

# Install built package
pip install dist/ridehail-0.1.0-py3-none-any.whl --force-reinstall
# OR with uv
uv pip install dist/ridehail-0.1.0-py3-none-any.whl --force-reinstall
```

### Testing

```bash
# Run tests (basic test files exist)
python -m pytest test/
python test_config_loading.py
python test_config_validation.py
```

### Linting and Code Quality

```bash
# Run ruff (configured in dependencies)
ruff check .
ruff format .
```

### Web Interface (Browser Lab)

```bash
# Build and serve the browser version
cp dist/ridehail-0.0.1-py3-non-any.whl docs/lab/dist/
cd docs/lab
python -m http.server
# Then navigate to http://localhost:8000
```

## Key Configuration Parameters

The simulation supports various configuration options including:
- City boundaries and map settings
- Vehicle fleet size and dispatch algorithms
- Animation styles (none, console, matplotlib)
- Sequence running for parameter sweeps
- Profiling and performance analysis

## File Structure Conventions

- Configuration files use `.config` extension and are stored in project root
- Test files follow `test_*.py` naming convention
- Documentation is in `docs/` directory
- Plotting utilities are in `plot/` directory
- Browser lab interface files are in `docs/lab/`

## Important Notes

- The project supports both traditional Python virtual environments and modern tools like `uv`
- Configuration validation is strict - invalid parameters will raise `ConfigValidationError`
- The browser interface uses Pyodide to run Python code client-side
- Profiling can be enabled with the `--profile` flag for performance analysis