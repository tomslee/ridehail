#!/bin/usr/python
import sys
import os
import unittest
import random

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

# from ridehail import animation, atom, config, simulation, sequence
from ridehail.atom import City, Trip, Vehicle, TripDistribution
from ridehail.config import RideHailConfig


class TestCity(unittest.TestCase):
    def setUp(self):
        """
        Set up a configuration for each test
        """
        print("\nTest = ", self.id().split("."))  # [-1]
        self.config = RideHailConfig(use_config_file=False)
        self.config.city_size = 20
        self.config.trip_distribution = TripDistribution.UNIFORM
        self.config.min_trip_distance = 0.0

    def tearDown(self):
        pass

    def test_set_location(self):
        """
        Each coordinate is chosen randomly in the range [0, city_size-1]
        so the mean should be (city_size - 0.5) for each coordinate.
        """
        random.seed(0)
        city = City(city_size=self.config.city_size)
        expected_magnitude = city.city_size - 1
        repeat_count = 100000
        (x, y) = (0, 0)
        for i in range(repeat_count):
            loc = city.set_location(is_destination=False)
            x += loc[0]
            y += loc[1]
        mean_x = x / repeat_count
        mean_y = y / repeat_count
        print(f"\nmean position = ({mean_x}, {mean_y})")
        self.assertAlmostEqual(mean_x + mean_y, expected_magnitude, places=1)

    def test_travel_distance(self):
        """
        set the beginning, and the end, and check
        """
        random.seed(0)
        city = City(city_size=self.config.city_size)
        for i in range(10):
            vehicle = Vehicle(i, city)
            trip = Trip(i, city)
            trip_origin = trip.set_origin()
            distance = city.distance(vehicle.location, trip_origin)
            travel_distance = city.travel_distance(
                vehicle.location, vehicle.direction, trip_origin
            )
            print(
                (
                    f"distance = {distance}"
                    f", travel distance={travel_distance}"
                    f", from={vehicle.location}, to={trip_origin}"
                    f", with direction{vehicle.direction.value}"
                )
            )
            try:
                self.assertTrue(abs(distance - travel_distance) < 2.1)
            except:
                print(f"failure on i={i}")

    def test_trip_distance_distribution(self):
        """
        set the beginning, and the end, and check the distribution
        """
        random.seed(0)
        city = City(city_size=self.config.city_size)
        repeat_count = 10000
        repeat_count = 0
        expected_mean_distance = city.city_size / 2.0
        distance = 0
        for i in range(repeat_count):
            trip = Trip(i, city)
            origin = trip.set_origin()
            destination = trip.set_destination(origin)
            distance += city.distance(origin, destination)
        mean_distance = distance / repeat_count
        print(
            (
                f"\nmean distance = {mean_distance}, "
                f"expected mean distance={expected_mean_distance}"
            )
        )
        self.assertAlmostEqual(mean_distance, expected_mean_distance, places=1)

    def test_nearest_distance(self):
        """
        Place a number of vehicles at random in a city, then see what the
        distance is to another randome point
        """
        idle_vehicle_count = 3
        request_count = 1000
        vehicle_locations = []
        request_locations = []
        city = City(city_size=self.config.city_size)
        city.city_size = 50
        for vehicle in range(idle_vehicle_count):
            vehicle_locations.append(city.set_location(is_destination=False))

        for request in range(request_count):
            request_locations.append(city.set_location(is_destination=False))

        nearest_distances = []
        for request_location in request_locations:
            nearest_distance = city.city_size * 2  # big
            for vehicle_location in vehicle_locations:
                # distance = (abs(vehicle_location[0] - request_location[0]) +
                # abs(vehicle_location[1] - request_location[1]))
                distance = city.distance(request_location, vehicle_location)
                nearest_distance = min(distance, nearest_distance)
            nearest_distances.append(nearest_distance)

        mean_nearest_distance = sum(nearest_distances) / request_count
        print(
            f"\n'Vehicles': {idle_vehicle_count}"
            f", 'City size': {city.city_size}"
            f", 'requests': {request_count}"
            f", 'mean nearest_distance': {mean_nearest_distance}"
        )
        self.assertLess(nearest_distance, city.city_size, "too far")


if __name__ == "__main__":
    unittest.main()
