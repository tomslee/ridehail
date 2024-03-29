import unittest
import random
from ridehail import animation, atom, config, simulation, sequence


class TestCity(unittest.TestCase):
    def setUp(self):
        """
        Set up a configuration for each test
        """
        self.rh_config = config.RideHailConfig(use_config_file=False)
        self.rh_config.city_size = 20
        self.rh_config.trip_distribution = atom.TripDistribution.UNIFORM
        self.rh_config.min_trip_distance = 0.0

    def tearDown(self):
        pass

    def test_set_location(self):
        """
        Each coordinate is chosen randomly in the range [0, city_size-1]
        so the mean should be (city_size - 0.5) for each coordinate.
        """
        random.seed(0)
        city = atom.City()
        city.city_size = self.rh_config.city_size
        expected_magnitude = city.city_size - 1
        repeat_count = 100000
        (x, y) = (0, 0)
        for i in range(repeat_count):
            loc = city.set_trip_location(is_destination=False)
            x += loc[0]
            y += loc[1]
        mean_x = x / repeat_count
        mean_y = y / repeat_count
        print(f"\nmean position = ({mean_x}, {mean_y})")
        self.assertAlmostEqual(mean_x + mean_y, expected_magnitude, places=1)

    def test_trip_distance(self):
        """
        set the beginning, and the end, and check the distribution
        """
        random.seed(0)
        city = atom.City()
        repeat_count = 10000
        expected_mean_distance = city.city_size / 2.0
        distance = 0
        for i in range(repeat_count):
            trip = atom.Trip(i, city)
            origin = trip.set_origin()
            destination = trip.set_destination(origin)
            distance += city.distance(origin, destination)
        mean_distance = distance / repeat_count
        print(f"\nmean distance = {mean_distance}")
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
        city = atom.City()
        city.city_size = 50
        for vehicle in range(idle_vehicle_count):
            vehicle_locations.append(
                city.set_trip_location(is_destination=False))

        for request in range(request_count):
            request_locations.append(
                city.set_trip_location(is_destination=False))

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
        print(f"\n'Vehicles': {idle_vehicle_count}"
              f", 'City size': {city.city_size}"
              f", 'requests': {request_count}"
              f", 'mean nearest_distance': {mean_nearest_distance}")
        self.assertLess(nearest_distance, city.city_size, "too far")


if __name__ == '__main__':
    unittest.main()
