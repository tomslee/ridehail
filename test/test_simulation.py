#!/bin/usr/python
import sys
import glob
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))
import unittest
import random

# from ridehail import animation, atom, config, simulation, sequence
from ridehail.atom import City, Trip, TripDistribution
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.sequence import RideHailSimulationSequence


class TestSimulation(unittest.TestCase):
    def setUp(self):
        """
        Set up a configuration for each test
        """
        FIXED_VC = 1
        TARGET_P3 = 0.28
        print("\nTest = ", self.id().split("."))  # [-1]
        config = RideHailConfig(use_config_file=False)
        config.title.value = "Test of ridehailing identities"
        config.city_size.value = 8
        config.vehicle_count.value = FIXED_VC
        # config.base_demand.value = 1
        config.base_demand.value = (
            config.vehicle_count.value * TARGET_P3 * 2.0 / config.city_size.value
        )
        # config.vehicle_count.value = int(
        # config.city_size.value * config.base_demand.value / (2.0 * TARGET_P3)
        # )
        print(f"Using {config.vehicle_count.value} vehicles")
        config.min_trip_distance.value = 0.0
        config.animate.value = False
        config.equilibrate.value = False
        config.run_sequence.value = False
        config.use_city_scale.value = False
        config.random_number_seed.value = random.randint(0, 1000)
        config.inhomogeneity.value = 0.0
        config.time_blocks.value = 2000
        config.results_window.value = 1000
        config.config_file.value = "test_simulation.config"
        sim = RideHailSimulation(config)
        self.results = sim.simulate()

    def tearDown(self):
        files = glob.glob("./output/test_simulation*")
        for f in files:
            os.remove(f)

    def test_identity_vehicle_fraction_sum(self):
        """
        A vehicle is always in state p1, p2, or p3.
        The sum of these states must equal 1
        """
        p1 = self.results.end_state["vehicle_fraction_p1"]
        p2 = self.results.end_state["vehicle_fraction_p2"]
        p3 = self.results.end_state["vehicle_fraction_p3"]
        self.assertAlmostEqual(p1 + p2 + p3, 1, places=2)

    def test_identity_p3(self):
        """
        The time spent with a passenger is the time a passenger
        spends in a vehicle.
        n * p3 = r * l
        """
        n = self.results.end_state["mean_vehicle_count"]
        p3 = self.results.end_state["vehicle_fraction_p3"]
        r = self.results.end_state["mean_request_rate"]
        l = self.results.end_state["mean_trip_distance"]
        print(f"n={n}, p3={p3}, r={r}, l={l}, n.p3 = {n * p3}, r.l = {r * l}")
        self.assertAlmostEqual(n * p3, r * l, places=1)

    def test_identity_p2(self):
        """
        The time spent waiting for a trip is the time
        a vehicle spends en route to pick up.
        n * p2 = r * w
        """
        n = self.results.end_state["mean_vehicle_count"]
        p2 = self.results.end_state["vehicle_fraction_p2"]
        r = self.results.end_state["mean_request_rate"]
        w = self.results.end_state["mean_trip_wait_time"]
        print(f"n={n}, p2={p2}, r={r}, w={w}, n.p2 = {n * p2}, r.w = {r * w}")
        self.assertAlmostEqual(n * p2, r * w, places=1)


if __name__ == "__main__":
    unittest.main()
