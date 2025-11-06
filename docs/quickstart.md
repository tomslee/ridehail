# Quick Start

Get up and running with your first ridehail simulation in under 60 seconds.

## Installation

If you haven't installed ridehail yet:

```bash
pip install ridehail[terminal]
```

## Your First Simulation

### Step 1: Create a Configuration File

Generate a default configuration file:

```bash
python -m ridehail -wc my_first_sim.config
```

This creates `my_first_sim.config` with sensible defaults:

- **City size**: 8×8 blocks
- **Vehicle count**: 30 vehicles
- **Base demand**: 2.0 requests per block per time step

### Step 2: Run the Simulation

Launch with terminal map visualization:

```bash
python -m ridehail my_first_sim.config -a terminal_map
```

You'll see a real-time map showing:

- **Blue vehicles** (P1): Idle, waiting for passengers
- **Orange vehicles** (P2): Dispatched to pick up passengers
- **Green vehicles** (P3): Carrying passengers
- **Markers**: Trip origins and destinations

### Step 3: Interact with the Simulation

**Keyboard controls:**

- `Space` - Pause/resume
- `+` / `-` - Adjust animation speed
- `v` - Increase vehicle count
- `V` - Decrease vehicle count
- `d` - Increase demand
- `D` - Decrease demand
- `r` - Reset simulation
- `q` - Quit

## Understanding the Display

### Vehicle States (Phases)

| Symbol | Color  | Phase | Description                           |
| ------ | ------ | ----- | ------------------------------------- |
| `◆`    | Blue   | P1    | Idle vehicle, driving randomly        |
| `◆`    | Orange | P2    | Dispatched, en route to pickup        |
| `◆`    | Green  | P3    | Occupied, carrying passenger          |

### Trip Markers

- `○` - Trip origin (passenger waiting)
- `●` - Trip destination

### Statistics Panel

The sidebar shows:

- **Phase fractions**: % of vehicles in each state
- **Wait time**: Average passenger wait time
- **Ride time**: Average trip duration
- **Trip rate**: Completed trips per time unit

## Try Different Animations

### Console View

Simple text-based statistics:

```bash
python -m ridehail my_first_sim.config -a console
```

Shows progress bars for vehicle phases and key metrics.

### Terminal Stats

Real-time line charts in the terminal:

```bash
python -m ridehail my_first_sim.config -a terminal_stats
```

Displays rolling graphs of:

- Vehicle phase fractions over time
- Wait times and ride times

### Desktop Map (Matplotlib)

If you have matplotlib installed:

```bash
pip install ridehail[desktop]
python -m ridehail my_first_sim.config -a map
```

Opens a desktop window with matplotlib visualization.

## Customizing Your Simulation

### Command-Line Overrides

Override config file settings directly:

```bash
# Run with larger city and more vehicles
python -m ridehail my_first_sim.config -cs 16 -vc 100 -a terminal_map

# Disable graphics for faster simulation
python -m ridehail my_first_sim.config -a none
```

### Creating Custom Configurations

Generate a config file with specific parameters:

```bash
# Small village simulation
python -m ridehail -wc village.config -cs 6 -vc 20 -bd 1.0

# Large city simulation
python -m ridehail -wc city.config -cs 20 -vc 200 -bd 8.0
```

### Editing Configuration Files

Open your config file in a text editor to see all available parameters:

```ini
[DEFAULT]
# City parameters
city_size = 8
vehicle_count = 30
base_demand = 2.0

# Economic parameters
platform_commission = 0.25
reservation_wage = 15.0

# Simulation control
time_blocks = 200
animation = terminal_map
animation_delay = 0.1
```

Each parameter includes documentation comments. See [Configuration Guide](configuration/overview.md) for details.

## Common Scenarios

### High Demand, Few Vehicles

```bash
python -m ridehail -wc congested.config -cs 10 -vc 20 -bd 5.0
python -m ridehail congested.config -a terminal_map
```

**Observe:** Long wait times, mostly P2/P3 vehicles (few idle).

### Low Demand, Many Vehicles

```bash
python -m ridehail -wc oversupply.config -cs 10 -vc 100 -bd 1.0
python -m ridehail oversupply.config -a terminal_map
```

**Observe:** Short wait times, mostly P1 vehicles (many idle).

### Equilibration (Driver Entry/Exit)

Enable economic equilibration where drivers join/leave based on earnings:

```bash
python -m ridehail -wc equilibrate.config -cs 10 -vc 50 -bd 2.0
python -m ridehail equilibrate.config --equilibrate -a terminal_stats
```

**Observe:** Vehicle count adjusts over time to market conditions.

## Parameter Sweeps

Run a sequence of simulations to explore parameter space:

```bash
# Create a sequence config
python -m ridehail test_sequence.config -a terminal_sequence
```

This runs multiple simulations with varying parameters and displays results as scatter plots.

## Next Steps

- **[Configuration Guide](configuration/overview.md)** - Learn about all available parameters
- **[Animation Modes](animations/overview.md)** - Explore visualization options
- **[Background](background.md)** - Understand the simulation model
- **[Browser Lab](lab/index.html)** - Try the interactive web interface

## Getting Help

```bash
# View all command-line options
python -m ridehail --help

# Check version
python -m ridehail --version
```

For issues or questions, visit the [GitHub Issues](https://github.com/tomslee/ridehail/issues) page.
