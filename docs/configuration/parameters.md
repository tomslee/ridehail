# Configuration Parameters Reference

Complete reference for all ridehail simulation configuration parameters.

## Core Simulation Parameters

### city_size

- **Type**: Integer (must be even)
- **Default**: 32
- **Range**: 2-200
- **CLI**: `-cs`, `--city-size`
- **Section**: `[DEFAULT]`

The number of blocks on each side of the square city grid. Vehicles and trips exist at intersections on this grid.

**Example**: `city_size = 10` creates a 10×10 grid with 100 intersections.

### vehicle_count

- **Type**: Integer
- **Default**: 64
- **Range**: 1-100000
- **CLI**: `-vc`, `--vehicle-count`
- **Section**: `[DEFAULT]`

The initial number of vehicles in the simulation. With equilibration enabled, this number can change as drivers enter/exit based on earnings.

### base_demand

- **Type**: Float
- **Default**: Calculated from request_rate if not specified
- **Range**: 0.0+
- **CLI**: `-bd`, `--base-demand`
- **Section**: `[DEFAULT]`

Base demand rate: the average number of trip requests per block per time step. Higher values create more passenger demand.

**Example**: `base_demand = 3.0` with `city_size = 10` generates ~300 requests per time step.

### time_blocks

- **Type**: Integer
- **Default**: 600
- **Range**: 1+
- **CLI**: `-tb`, `--time-blocks`
- **Section**: `[DEFAULT]`

The total number of simulation time steps to run. Each time step represents vehicle movement between adjacent intersections.

### idle_vehicles_moving

- **Type**: Boolean
- **Default**: True
- **CLI**: `-ivm`, `--idle-vehicles-moving`
- **Section**: `[DEFAULT]`

Whether idle (P1 phase) vehicles move randomly or remain stationary while waiting for dispatch.

## Dispatch Parameters

### dispatch_method

- **Type**: Enum
- **Default**: `IMMEDIATE_BATCH_NEAREST`
- **Choices**: `IMMEDIATE_BATCH_NEAREST`, `IMMEDIATE_NEAREST`, `QUEUE_NEAREST`
- **CLI**: `-dm`, `--dispatch-method`
- **Section**: `[DEFAULT]`

Algorithm for matching vehicles to trip requests:

- **IMMEDIATE_BATCH_NEAREST**: Batch matching every time step, minimize total distance
- **IMMEDIATE_NEAREST**: Match each request to nearest available vehicle immediately
- **QUEUE_NEAREST**: Queue requests, match with nearest vehicle when one becomes available

## Economic Parameters

### platform_commission

- **Type**: Float
- **Default**: 0.25
- **Range**: 0.0-1.0
- **Section**: `[EQUILIBRATION]`

The fraction of fares taken by the platform. Drivers receive `1 - platform_commission` of each fare.

**Example**: `platform_commission = 0.25` means platform keeps 25%, driver gets 75%.

### reservation_wage

- **Type**: Float
- **Default**: 15.0
- **Range**: 0.0+
- **Section**: `[EQUILIBRATION]`

The minimum hourly earnings drivers require to participate. Used with `equilibrate = True` to model driver entry/exit.

### driver_rate

- **Type**: Float
- **Default**: 12.0
- **Range**: 0.0+
- **Section**: `[EQUILIBRATION]`

The operating cost per hour for drivers (fuel, wear, etc.). Affects economic equilibration.

### simple_fare

- **Type**: Float
- **Default**: 4.0
- **Range**: 0.0+
- **Section**: `[DEFAULT]`

Fixed fare per trip (used when `use_simple_fare = True`).

### use_simple_fare

- **Type**: Boolean
- **Default**: True
- **Section**: `[DEFAULT]`

Whether to use simple fixed fares (`simple_fare`) or distance/time-based pricing.

## Equilibration Parameters

### equilibrate

- **Type**: Boolean
- **Default**: False
- **CLI**: `--equilibrate`
- **Section**: `[EQUILIBRATION]`

Enable economic equilibration where drivers enter/exit the market based on earnings vs. reservation wage.

### equilibration_interval

- **Type**: Integer
- **Default**: 10
- **Range**: 1+
- **Section**: `[EQUILIBRATION]`

Number of time blocks between equilibration adjustments.

### min_vehicles

- **Type**: Integer
- **Default**: 1
- **Range**: 1+
- **Section**: `[EQUILIBRATION]`

Minimum number of vehicles during equilibration (prevents complete market exit).

### max_vehicles

- **Type**: Integer
- **Default**: 10000
- **Range**: 1+
- **Section**: `[EQUILIBRATION]`

Maximum number of vehicles during equilibration.

## Physical Scale Parameters

### block_length

- **Type**: Float
- **Default**: 0.5 km
- **Section**: `[CITY_SCALE]`

Physical distance between adjacent intersections in kilometers.

### mean_vehicle_speed

- **Type**: Float
- **Default**: 30.0 km/h
- **Section**: `[CITY_SCALE]`

Average vehicle speed. Used to convert simulation time steps to real-world time.

### trip_distance_km

- **Type**: Float
- **Default**: Calculated from city geometry
- **Section**: `[CITY_SCALE]`

Average trip distance in kilometers. Used for fare calculations with distance-based pricing.

## Animation Parameters

### animation

- **Type**: Enum
- **Default**: `terminal_map`
- **Choices**: `none`, `console`, `terminal_map`, `terminal_stats`, `terminal_sequence`, `map`, `stats`
- **CLI**: `-a`, `--animation`
- **Section**: `[ANIMATION]`

Visualization mode:

- **none**: No visualization (fastest)
- **console**: Text-based console output
- **terminal_map**: Real-time terminal map with vehicles
- **terminal_stats**: Terminal-based statistical charts
- **terminal_sequence**: Terminal visualization for parameter sweeps
- **map**: Matplotlib desktop map
- **stats**: Matplotlib desktop statistics

### animation_delay

- **Type**: Float
- **Default**: 0.1 seconds
- **Range**: 0.0+
- **CLI**: `-ad`, `--animation-delay`
- **Section**: `[ANIMATION]`

Delay between animation frames in seconds. Lower values = faster animation.

### results_window

- **Type**: Integer
- **Default**: 60
- **Range**: 1+
- **Section**: `[ANIMATION]`

Size of rolling window for statistical smoothing in visualizations.

## Sequence Parameters

### sequence_variable

- **Type**: String
- **Default**: `vehicle_count`
- **Section**: `[SEQUENCE]`

The parameter to vary in sequence runs. Commonly `vehicle_count`, `base_demand`, or `platform_commission`.

### sequence_start

- **Type**: Float
- **Default**: Depends on variable
- **Section**: `[SEQUENCE]`

Starting value for sequence parameter sweeps.

### sequence_end

- **Type**: Float
- **Default**: Depends on variable
- **Section**: `[SEQUENCE]`

Ending value for sequence parameter sweeps.

### sequence_step

- **Type**: Float
- **Default**: Depends on variable
- **Section**: `[SEQUENCE]`

Increment between sequence runs.

## Advanced Parameters

### demand_elasticity

- **Type**: Float
- **Default**: 0.0
- **Range**: -1.0 to 1.0
- **Section**: `[DEFAULT]`

Price elasticity of demand. Negative values reduce demand as prices increase.

### p3_pickup_only

- **Type**: Boolean
- **Default**: False
- **Section**: `[DEFAULT]`

If True, occupied (P3) vehicles can pick up additional passengers at trip origins (ride pooling).

### log_level

- **Type**: String
- **Default**: `INFO`
- **Choices**: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`
- **CLI**: `-ll`, `--log-level`
- **Section**: `[DEFAULT]`

Python logging level for debug output.

### random_number_seed

- **Type**: Integer
- **Default**: None (random seed)
- **Section**: `[DEFAULT]`

Seed for random number generator. Set to a specific value for reproducible simulations.

## Viewing All Parameters

To see all available parameters with descriptions, generate a config file:

```bash
python -m ridehail -wc example.config
```

Open `example.config` in a text editor to see inline documentation for every parameter.

## Validation

Configuration validation checks:

- **Type correctness**: Parameters must match expected types
- **Range bounds**: Numeric parameters stay within min/max
- **Even number requirements**: `city_size` must be even
- **Dependency validation**: Related parameters are consistent

Invalid configurations raise descriptive error messages.

## Next Steps

- **[Configuration Examples](examples.md)** - Common configuration patterns
- **[Configuration Overview](overview.md)** - General configuration guide
- **[Quick Start](../quickstart.md)** - Get started with simulations
