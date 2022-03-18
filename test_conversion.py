#!/bin/usr/python
from ridehail.atom import CityScaleUnit
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation

config = RideHailConfig()
config.use_city_scale.value = True
config.minutes_per_block.value = 2
config.mean_vehicle_speed.value = 30  # km/h
config.per_km_price.value = 1.2
config.per_minute_price.value = 0.2
config.per_minute_opp_cost.value = 1.2
config.per_km_ops_cost.value = 0.40
config.smoothing_window.value = 20

sim = RideHailSimulation(config)

assert sim.convert_units(3.0, CityScaleUnit.MINUTE, CityScaleUnit.BLOCK) == 1.5
print("At 2 minutes_per_block, a vehicle travels 1.5 blocks in 3.0 minutes")

assert sim.convert_units(2.0, CityScaleUnit.HOUR, CityScaleUnit.BLOCK) == 60
print("At 2 minutes_per_block, a vehicle travels 60 blocks in 2.0 hours")

assert sim.convert_units(2.0, CityScaleUnit.KM, CityScaleUnit.BLOCK) == 2
print(
    "At 2 minutes_per_block and 30 km/h, 2.0 km is the equivalent of 2 blocks")

assert sim.convert_units(3.0, CityScaleUnit.HOUR, CityScaleUnit.MINUTE) == 180
print("3 hours is 180 minutes")

assert sim.convert_units(3.0, CityScaleUnit.KM, CityScaleUnit.MINUTE) == 6
print("At 30 km/h, it takes 6 minutes to travel 3.0 km")

assert sim.convert_units(10, CityScaleUnit.BLOCK, CityScaleUnit.MINUTE) == 20
print("At 2 minutes_per_block, it takes 20 minutes to travel 10 blocks")

assert sim.convert_units(10, CityScaleUnit.BLOCK,
                         CityScaleUnit.HOUR) == (1.0 / 3.0)
print("At 2 minutes_per_block, it takes 1/3 hour to travel 10 blocks")

assert sim.convert_units(3.0, CityScaleUnit.PER_KM,
                         CityScaleUnit.PER_BLOCK) == 3.0
print("At 30 km/h and 2 minutes_per_block, a cost of $3/km is also $3/block")

assert sim.convert_units(15.0, CityScaleUnit.PER_HOUR,
                         CityScaleUnit.PER_BLOCK) == 0.5
print("At 30 km/h and 2 minutes_per_block, a $15/hr wage is $0.50/block")

assert sim.convert_units(0.5, CityScaleUnit.PER_BLOCK,
                         CityScaleUnit.PER_HOUR) == 15.0
print("At 30 km/h and 2 minutes_per_block, $0.50/block is the same as $15/hr")
