# Configuration Examples

Common configuration patterns for different simulation scenarios.

## Quick Test Configuration

For rapid testing and development:

```ini
[DEFAULT]
city_size = 6
vehicle_count = 20
base_demand = 1.0
time_blocks = 100
animation = terminal_map
animation_delay = 0.05
```

**Characteristics:**

- Small city for fast execution
- Low vehicle count and demand
- Short simulation duration
- Fast animation

**Use case:** Quick verification, debugging, development

## Balanced Urban Scenario

Realistic mid-sized city with balanced supply/demand:

```ini
[DEFAULT]
title = Balanced Urban Simulation
city_size = 12
vehicle_count = 80
base_demand = 3.0
time_blocks = 400
idle_vehicles_moving = True
dispatch_method = IMMEDIATE_BATCH_NEAREST
animation = terminal_stats
animation_delay = 0.1
results_window = 60

[CITY_SCALE]
block_length = 0.5
mean_vehicle_speed = 30.0

[EQUILIBRATION]
platform_commission = 0.25
reservation_wage = 15.0
```

**Characteristics:**

- Moderate city size
- Reasonable vehicle/demand ratio (~1:1.8)
- Standard economic parameters
- Statistical visualization

**Use case:** General experimentation, baseline comparisons

## High Demand / Congested

Undersupplied market with high passenger demand:

```ini
[DEFAULT]
title = High Demand Scenario
city_size = 10
vehicle_count = 30
base_demand = 6.0
time_blocks = 500
dispatch_method = IMMEDIATE_BATCH_NEAREST
animation = terminal_map
animation_delay = 0.1

[EQUILIBRATION]
platform_commission = 0.20
reservation_wage = 18.0
simple_fare = 6.0
use_simple_fare = True
```

**Characteristics:**

- High demand relative to supply (2:1 ratio)
- Expect long wait times
- High fare due to scarcity
- Many P2/P3 vehicles, few idle

**Use case:** Surge pricing studies, congestion analysis

## Oversupplied Market

Excess vehicles competing for passengers:

```ini
[DEFAULT]
title = Oversupply Scenario
city_size = 10
vehicle_count = 150
base_demand = 2.0
time_blocks = 500
idle_vehicles_moving = True
dispatch_method = IMMEDIATE_BATCH_NEAREST
animation = terminal_console
animation_delay = 0.05

[EQUILIBRATION]
platform_commission = 0.30
reservation_wage = 12.0
driver_rate = 10.0
```

**Characteristics:**

- Low demand relative to supply (13:1 ratio)
- Short wait times
- Many idle (P1) vehicles
- Low driver utilization

**Use case:** Driver earnings analysis, market saturation studies

## Economic Equilibration

Market with dynamic driver entry/exit:

```ini
[DEFAULT]
title = Economic Equilibration Study
city_size = 12
vehicle_count = 60
base_demand = 3.5
time_blocks = 1000
dispatch_method = IMMEDIATE_BATCH_NEAREST
animation = terminal_stats
animation_delay = 0.1
results_window = 100

[EQUILIBRATION]
equilibrate = True
equilibration_interval = 10
platform_commission = 0.25
reservation_wage = 15.0
driver_rate = 12.0
min_vehicles = 20
max_vehicles = 200
simple_fare = 4.5
use_simple_fare = True
```

**Characteristics:**

- Equilibration enabled
- Vehicle count adjusts every 10 blocks
- Longer simulation to observe dynamics
- Economic parameters calibrated for adjustment

**Use case:** Market dynamics, platform commission optimization

## Dispatch Algorithm Comparison

Three configs to compare dispatch strategies:

### Immediate Batch (Optimal)

```ini
[DEFAULT]
title = Batch Dispatch
city_size = 10
vehicle_count = 50
base_demand = 3.0
time_blocks = 400
dispatch_method = IMMEDIATE_BATCH_NEAREST
animation = terminal_stats
```

### Immediate Nearest

```ini
[DEFAULT]
title = Greedy Dispatch
city_size = 10
vehicle_count = 50
base_demand = 3.0
time_blocks = 400
dispatch_method = IMMEDIATE_NEAREST
animation = terminal_stats
```

### Queue Nearest

```ini
[DEFAULT]
title = Queue Dispatch
city_size = 10
vehicle_count = 50
base_demand = 3.0
time_blocks = 400
dispatch_method = QUEUE_NEAREST
animation = terminal_stats
```

**Use case:** Compare efficiency of different matching algorithms

## Parameter Sweep Sequence

Vary vehicle count to find optimal supply level:

```ini
[DEFAULT]
city_size = 10
base_demand = 3.0
time_blocks = 400
animation = terminal_sequence

[SEQUENCE]
sequence_variable = vehicle_count
sequence_start = 20
sequence_end = 120
sequence_step = 10

[EQUILIBRATION]
platform_commission = 0.25
reservation_wage = 15.0
```

**Characteristics:**

- Runs 11 simulations (vehicle_count: 20, 30, ..., 120)
- Displays results as scatter plots
- Identifies optimal vehicle count

**Use case:** Optimization studies, sensitivity analysis

## Large-Scale Performance Test

No visualization for maximum speed:

```ini
[DEFAULT]
city_size = 30
vehicle_count = 500
base_demand = 12.0
time_blocks = 2000
animation = none
results_window = 200
log_level = WARNING

[EQUILIBRATION]
platform_commission = 0.25
```

**Characteristics:**

- Large city and fleet
- No animation overhead
- Reduced logging
- Long simulation

**Use case:** Performance testing, statistical validation

## Distance-Based Fare Model

Use distance+time pricing instead of simple fares:

```ini
[DEFAULT]
city_size = 12
vehicle_count = 80
base_demand = 3.5
time_blocks = 500
use_simple_fare = False
animation = terminal_stats

[CITY_SCALE]
block_length = 0.5
mean_vehicle_speed = 30.0
trip_distance_km = 4.0

[EQUILIBRATION]
fare_per_km = 1.50
fare_per_minute = 0.25
base_fare = 2.50
platform_commission = 0.25
```

**Characteristics:**

- Realistic fare structure
- Distance-sensitive pricing
- Physical scale calibration

**Use case:** Fare structure analysis, realistic modeling

## Platform Commission Study

Sequence over commission rates:

```ini
[DEFAULT]
city_size = 12
vehicle_count = 80
base_demand = 3.5
time_blocks = 800
animation = terminal_sequence

[SEQUENCE]
sequence_variable = platform_commission
sequence_start = 0.10
sequence_end = 0.40
sequence_step = 0.05

[EQUILIBRATION]
equilibrate = True
equilibration_interval = 10
reservation_wage = 15.0
driver_rate = 12.0
simple_fare = 5.0
use_simple_fare = True
```

**Characteristics:**

- Studies commission rates from 10% to 40%
- Equilibration shows driver response
- Observes market viability

**Use case:** Platform economics, commission optimization

## Creating Your Own

Start with a template:

```bash
# Generate default config
python -m ridehail -wc my_config.config

# Or start from example
cp test.config my_config.config
```

Then modify parameters for your scenario. Use the [parameters reference](parameters.md) for complete documentation.

## Tips

### Finding Balance

Good vehicle/demand ratio: `vehicle_count ≈ city_size² × base_demand / 3`

### Performance vs. Detail

- Use `animation = none` for long simulations
- Reduce `city_size` for faster iterations
- Increase `results_window` for smoother statistics

### Economic Realism

- `reservation_wage` > `driver_rate` (drivers need positive net earnings)
- `platform_commission` typically 20-30%
- `simple_fare` should cover ~30-45 minutes of `reservation_wage`

## Next Steps

- **[Parameters Reference](parameters.md)** - Complete parameter documentation
- **[Configuration Overview](overview.md)** - Configuration system guide
- **[Quick Start](../quickstart.md)** - Run your first simulation
