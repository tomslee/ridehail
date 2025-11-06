# Configuration Overview

Ridehail simulations are controlled through configuration files that define all aspects of the simulation: city layout, vehicle fleet, demand patterns, economic parameters, and visualization settings.

## Configuration File Format

Configuration files use the INI format with sections for different parameter categories:

```ini
[DEFAULT]
# Core simulation parameters
city_size = 10
vehicle_count = 50
base_demand = 3.0

[CITY_SCALE]
# Scale factors for different city sizes
block_length = 0.5
trip_distance_km = 3.0

[EQUILIBRATION]
# Economic equilibration parameters
equilibrate = False
platform_commission = 0.25

[ANIMATION]
# Visualization settings
animation = terminal_map
animation_delay = 0.1
```

## Creating Configuration Files

### Generate Default Configuration

```bash
python -m ridehail -wc my_config.config
```

This creates a config file with documented default values.

### Generate with Custom Parameters

```bash
python -m ridehail -wc my_config.config -cs 12 -vc 60 -bd 4.0
```

Command-line flags:

- `-wc` / `--write-config` - Write configuration file
- `-cs` / `--city-size` - City size (blocks)
- `-vc` / `--vehicle-count` - Initial vehicle count
- `-bd` / `--base-demand` - Base demand rate

### Copy Existing Configuration

```bash
cp test.config my_custom.config
```

Then edit `my_custom.config` in a text editor.

## Configuration Sections

### DEFAULT Section

Core simulation parameters:

- **City geometry**: `city_size`, `time_blocks`
- **Vehicle fleet**: `vehicle_count`, `idle_vehicles_moving`
- **Demand**: `base_demand`, `demand_elasticity`
- **Dispatch**: `dispatch_method`

See [Parameters Reference](parameters.md) for complete list.

### CITY_SCALE Section

Physical scale parameters:

- `block_length` - Distance between intersections (km)
- `trip_distance_km` - Average trip distance
- `mean_vehicle_speed` - Average vehicle speed (km/h)

These affect time and distance calculations but not core simulation dynamics.

### EQUILIBRATION Section

Economic model parameters:

- `equilibrate` - Enable driver entry/exit
- `platform_commission` - Platform's share of fares (0-1)
- `reservation_wage` - Minimum acceptable driver earnings ($/hour)
- `driver_rate` - Operating cost ($/hour)

When `equilibrate = True`, the vehicle count adjusts based on economic viability.

### ANIMATION Section

Visualization settings:

- `animation` - Animation mode (terminal_map, console, map, stats, none)
- `animation_delay` - Delay between frames (seconds)
- `results_window` - Rolling average window size

## Command-Line Overrides

Configuration file values can be overridden via command-line arguments:

```bash
# Override animation mode
python -m ridehail my_config.config -a terminal_stats

# Override multiple parameters
python -m ridehail my_config.config -cs 16 -vc 100 -bd 5.0

# Disable animation entirely
python -m ridehail my_config.config -a none
```

Not all parameters have command-line flags. Use config files for advanced parameters.

## Parameter Validation

The configuration system validates parameters:

- **Type checking**: Ensures correct types (int, float, bool, enum)
- **Range validation**: Checks min/max bounds where applicable
- **Dependency validation**: Ensures required parameters are present
- **Even number constraints**: Some parameters must be even

Invalid configurations raise `ConfigValidationError` with descriptive messages.

## Example Configurations

### Small Village

```ini
[DEFAULT]
city_size = 6
vehicle_count = 20
base_demand = 1.0
time_blocks = 200
animation = terminal_map
```

Low demand, small fleet, manageable for quick tests.

### Medium Town

```ini
[DEFAULT]
city_size = 12
vehicle_count = 80
base_demand = 3.5
time_blocks = 400
animation = terminal_stats
```

Moderate complexity, suitable for parameter exploration.

### Large City

```ini
[DEFAULT]
city_size = 20
vehicle_count = 200
base_demand = 8.0
time_blocks = 800
animation = none
results_window = 100
```

High complexity, typically run without animation for performance.

### Equilibration Study

```ini
[DEFAULT]
city_size = 10
vehicle_count = 50
base_demand = 3.0
time_blocks = 1000

[EQUILIBRATION]
equilibrate = True
platform_commission = 0.25
reservation_wage = 15.0
driver_rate = 12.0
equilibration_interval = 10
```

Models driver entry/exit based on earnings.

## Configuration Tips

### Performance

- **Large simulations**: Use `animation = none` for speed
- **Long runs**: Increase `results_window` for smoother statistics
- **Quick tests**: Use small `city_size` and `time_blocks`

### Realistic Scenarios

- **Undersupply**: Low `vehicle_count`, high `base_demand`
- **Oversupply**: High `vehicle_count`, low `base_demand`
- **Balanced**: `vehicle_count ≈ city_size² × base_demand / 3`

### Economic Analysis

- Enable `equilibrate` to study market dynamics
- Adjust `platform_commission` to model platform strategies
- Vary `reservation_wage` to represent driver opportunity costs

## Sequence Configurations

For parameter sweeps, use sequence configuration files:

```ini
[DEFAULT]
city_size = 10
base_demand = 3.0
time_blocks = 400

[SEQUENCE]
sequence_variable = vehicle_count
sequence_start = 20
sequence_end = 100
sequence_step = 10
```

This runs simulations with vehicle counts from 20 to 100 in steps of 10.

Run with:

```bash
python -m ridehail my_sequence.config -a terminal_sequence
```

## Next Steps

- **[Parameters Reference](parameters.md)** - Complete parameter documentation
- **[Configuration Examples](examples.md)** - More example configurations
- **[Quick Start](../quickstart.md)** - Get started with simulations
