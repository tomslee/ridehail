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

    def test_set_random_location(self):
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
            loc = city.set_random_location(is_destination=False)
            x += loc[0]
            y += loc[1]
        mean_x = x / repeat_count
        mean_y = y / repeat_count
        print(f"mean position = ({mean_x}, {mean_y})")
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
        print(f"mean distance = {mean_distance}")
        self.assertAlmostEqual(mean_distance, expected_mean_distance, places=1)


if __name__ == '__main__':
    unittest.main()
