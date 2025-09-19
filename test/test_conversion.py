#!/bin/usr/python
import unittest
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from ridehail.atom import CityScaleUnit
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation


class TestConversions(unittest.TestCase):
    def setUp(self):
        """
        Set up a configuration for each test
        """
        print("\nTest = ", self.id().split("."))  # [-1]
        self.config = RideHailConfig(use_config_file=False)
        self.config.use_city_scale.value = True
        self.config.minutes_per_block.value = 2
        self.config.mean_vehicle_speed.value = 30  # km/h
        self.config.per_km_price.value = 1.2
        self.config.per_minute_price.value = 0.2
        self.config.per_hour_opportunity_cost.value = 5.0
        self.config.per_km_ops_cost.value = 0.40
        self.config.smoothing_window.value = 20

        self.sim = RideHailSimulation(self.config)

    def tearDown(self):
        pass

    def test_conversion(self):
        self.assertEqual(
            self.sim.convert_units(3.0, CityScaleUnit.MINUTE, CityScaleUnit.BLOCK), 1.5
        )
        print("At 2 minutes_per_block, a vehicle travels 1.5 blocks in 3.0 minutes")

        self.assertEqual(
            self.sim.convert_units(2.0, CityScaleUnit.HOUR, CityScaleUnit.BLOCK), 60
        )
        print("At 2 minutes_per_block, a vehicle travels 60 blocks in 2.0 hours")

        self.assertEqual(
            self.sim.convert_units(2.0, CityScaleUnit.KM, CityScaleUnit.BLOCK), 2
        )
        print(
            "At 2 minutes_per_block and 30 km/h, 2.0 km is the equivalent of 2 blocks"
        )

        self.assertEqual(
            self.sim.convert_units(3.0, CityScaleUnit.HOUR, CityScaleUnit.MINUTE), 180
        )
        print("3 hours is 180 minutes")

        self.assertEqual(
            self.sim.convert_units(3.0, CityScaleUnit.KM, CityScaleUnit.MINUTE), 6
        )
        print("At 30 km/h, it takes 6 minutes to travel 3.0 km")

        self.assertEqual(
            self.sim.convert_units(10, CityScaleUnit.BLOCK, CityScaleUnit.MINUTE), 20
        )
        print("At 2 minutes_per_block, it takes 20 minutes to travel 10 blocks")

        self.assertEqual(
            self.sim.convert_units(10, CityScaleUnit.BLOCK, CityScaleUnit.HOUR),
            (1.0 / 3.0),
        )
        print("At 2 minutes_per_block, it takes 1/3 hour to travel 10 blocks")

        self.assertEqual(
            self.sim.convert_units(3.0, CityScaleUnit.PER_KM, CityScaleUnit.PER_BLOCK),
            3.0,
        )
        print("At 30 km/h and 2 minutes_per_block, a cost of $3/km is also $3/block")

        self.assertEqual(
            self.sim.convert_units(
                15.0, CityScaleUnit.PER_HOUR, CityScaleUnit.PER_BLOCK
            ),
            0.5,
        )
        print("At 30 km/h and 2 minutes_per_block, a $15/hr wage is $0.50/block")

        self.assertEqual(
            self.sim.convert_units(
                0.5, CityScaleUnit.PER_BLOCK, CityScaleUnit.PER_HOUR
            ),
            15.0,
        )
        print("At 30 km/h and 2 minutes_per_block, $0.50/block is the same as $15/hr")
