#!/bin/usr/python
import sys

sys.path.append("/home/tom/src/ridehail")
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
        print("\nTest = ", self.id().split("."))  # [-1]
        self.config = RideHailConfig(use_config_file=False)
        self.config.title.value = "Test of ridehailing identities"
        self.config.city_size.value = 16
        self.config.min_trip_distance.value = 0.0
        self.config.animate.value = False
        self.config.equilibrate.value = False
        self.config.run_sequence.value = False
        self.config.use_city_scale.value = False
        self.config.random_number_seed.value = random.randint(0, 1000)
        self.config.base_demand.value = 1
        self.config.vehicle_count.value = 24
        self.config.trip_distribution.value = TripDistribution.UNIFORM
        self.config.trip_inhomogeneity.value = 0.0
        self.config.time_blocks.value = 2000
        self.config.results_window.value = 500
        self.config.config_file.value = "test_simulation.config"

    def tearDown(self):
        pass

    def test_identity_1(self):
        """
        """
        sim = RideHailSimulation(self.config)
        results = sim.simulate()
        n = results.end_state["mean_vehicle_count"]
        p3 = results.end_state["vehicle_fraction_with_rider"]
        r = results.end_state["mean_request_rate"]
        l = results.end_state["mean_trip_distance"]
        print(f"n={n}, p3={p3}, r={r}, l={l}, n.p3 = {n * p3}, r.l = {r * l}")
        self.assertAlmostEqual(n * p3, r * l, places=1)

    def test_identity_2(self):
        sim = RideHailSimulation(self.config)
        results = sim.simulate()
        n = results.end_state["mean_vehicle_count"]
        p2 = results.end_state["vehicle_fraction_picking_up"]
        r = results.end_state["mean_request_rate"]
        w = results.end_state["mean_trip_wait_time"]
        print(f"n={n}, p2={p2}, r={r}, w={w}, n.p2 = {n * p2}, r.w = {r * w}")

        self.assertAlmostEqual(n * p2, r * w, places=1)


if __name__ == "__main__":
    unittest.main()
