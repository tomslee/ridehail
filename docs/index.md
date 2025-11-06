# Ridehail Simulation

Ridehail is a python package for modelling and simulating the dynamics of ridehailing services (like Uber and Lyft) across different urban environments.

It models an urban environment as a square grid of streets which we call a "city". Vehicles that drive out of the grid on one side appear on the other (it is a torus). Different city environments can be simulated by changing parameters associated with the basic grid.

The best way to get a sense of what the model does is to go to https://tomslee.github.io/ridehail/lab and run a simulation there.

Ridehail provides tools to:

- **Analyze vehicle utilization** across fleet sizes, city sizes, and demand patterns
- **Study pricing effects** on driver behavior and system equilibrium
- **Visualize results** in terminal, desktop, or browser environments
- **Compare dispatch algorithms** for optimal vehicle-passenger matching

## Key Features

### Flexible Simulation Engine

The ridehail simulation engine lets you configure city size, vehicle counts, trip rates, dispatch strategies, and many other parameters to model realistic or hypothetical scenarios.

### Multiple Visualization Modes

For exploration and experiment, Ridehail provides several visualization options.

- **Terminal animations**: Real-time console, map, and statistical visualizations
- **Desktop visualizations**: Matplotlib-based charts and maps
- **Browser interface**: Interactive lab running entirely in-browser via Pyodide
- **Text output:** Minimal text output for batch operation.

### Advanced Analysis

- **Parameter sweeps**: Run sequences of simulations to explore parameter spaces
- **Equilibration**: Model driver entry/exit based on economic incentives
- **Real-time metrics**: Track vehicle phases, wait times, ride times, and pricing

## Quick Links

<div class="grid cards" markdown>

- :material-download:{ .lg .middle } **Installation**

  ***

  Get started with pip or uv installation

  [:octicons-arrow-right-24: Installation Guide](installation.md)

- :material-play-circle:{ .lg .middle } **Quick Start**

  ***

  Run your first simulation in 60 seconds

  [:octicons-arrow-right-24: Quick Start](quickstart.md)

- :material-cog:{ .lg .middle } **Configuration**

  ***

  Learn about configuration parameters

  [:octicons-arrow-right-24: Configuration](configuration/overview.md)

- :material-palette:{ .lg .middle } **Animations**

  ***

  Explore visualization options

  [:octicons-arrow-right-24: Animations](animations/overview.md)

- :material-flask:{ .lg .middle } **Live Demo**

  ***

  Try it in your browser, no installation

  [:octicons-arrow-right-24: Ridehail Lab](lab/index.html)

- :fontawesome-brands-github:{ .lg .middle } **GitHub**

  ***

  Source code, issues, and contributions

  [:octicons-arrow-right-24: Repository](https://github.com/tomslee/ridehail)

</div>

## Example Usage

### Basic Simulation

```bash
# Install with terminal animation support
pip install ridehail[terminal]

# Get help on the parameters
python -m ridehail --help

# Create a configuration file
python -m ridehail -wc my_simulation.config -cs 10 -vc 50

# Run simulation with terminal map visualization
python -m ridehail my_simulation.config -a terminal_map
```

### Parameter Sweep

```bash
# Create a sequence configuration
python -m ridehail test_sequence.config -a terminal_sequence
```

### Browser-based interactive lab

Visit the [Ridehail Lab](lab/index.html) to experiment with simulations interactively in your browser.

## What Can You Learn?

This simulation helps answer questions like:

- How does vehicle fleet size affect passenger wait times?
- How does passenger demand affect system efficiency?
- How do dispatch algorithms affect efficiency (in progress)?
- How do pricing and costs affect driver participation?

## Background

The simulation models a simplified city grid where:

- **Vehicles** move between intersections in discrete time steps
- **Trips** are requested at random locations with configurable demand rates
- **Dispatch algorithms** match available vehicles to waiting passengers
- **Equilibration** models driver entry/exit based on economic viability

For more details, see the [Background](background.md) documentation.

## Getting Help

- **Documentation**: This is the package documentation. Use the navigation to explore topics
- **Issues**: Report bugs or request features on [GitHub Issues](https://github.com/tomslee/ridehail/issues)
- **PyPI**: Package details at [pypi.org/project/ridehail](https://pypi.org/project/ridehail/)

## License

This project is licensed under the MIT License - see the LICENSE file for details.
