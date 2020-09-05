#!/usr/bin/python3

import configparser
import logging
import os
from ridehail.animation import Draw
from ridehail.atom import TripDistribution, Equilibration

logger = logging.getLogger(__name__)

DEFAULT_TRAILING_WINDOW = 20
DEFAULT_RESULTS_WINDOW = 100


class Config():
    """
    Hold the configuration parameters for the simulation, which come from three
    places:
    - default values, unless overridden by
    - a configuration file, unless overridden by
    - command line arguments
    """
    def __init__(self, args=None):
        """
        Read the configuration file  to set up the parameters
        """
        self.config_file = None
        self.log_level = logging.INFO
        if args is not None:
            self.config_file = args.config_file
            try:
                if args.verbose:
                    self.log_level = logging.DEBUG
                else:
                    self.log_level = logging.INFO
            except Exception:
                self.log_level = logging.INFO
        config = configparser.ConfigParser(allow_no_value=True)
        if self.config_file is None:
            # The default config file is username.config
            # look for username.config on both Windows (USERNAME)
            # and Linux (USER)
            if os.name == "nt":
                username = os.environ['USERNAME']
            else:
                username = os.environ['USER']
            self.config_file = username + ".config"
            logger.debug(f"Reading configuration file {self.config_file}")
            if not os.path.isfile(self.config_file):
                logger.error(
                    f"Configuration file {self.config_file} not found.")
        config.read(self.config_file)
        self.config_file_root = (os.path.splitext(
            os.path.split(self.config_file)[1])[0])

        # Fill in individual configuration values
        default = config["DEFAULT"]
        # City size
        self.city_size = int(args.city_size if args.
                             city_size else config["DEFAULT"]["city_size"])
        logger.debug(f"City size = {self.city_size}")
        # Driver count
        self.driver_count = int(args.driver_count if args.driver_count else
                                config["DEFAULT"]["driver_count"])
        logger.debug(f"Driver counts = {self.driver_count}")
        # Request rate
        self.request_rate = (args.request_rate if args.request_rate else
                             config["DEFAULT"]["request_rate"])
        self.request_rate = self.request_rate.split(",")
        self.request_rate = [float(x) for x in self.request_rate]
        logger.debug(f"Request rate = {self.request_rate}")
        # Trip distribution
        if config.has_option("DEFAULT", "trip_distribution"):
            trip_distribution = default.get("trip_distribution",
                                            fallback="u").lower()
            if trip_distribution.startswith("b"):
                self.trip_distribution = TripDistribution.BETA
            else:
                self.trip_distribution = TripDistribution.UNIFORM
        else:
            self.trip_distribution = TripDistribution.UNIFORM
        logger.debug(f"Trip distribution = {self.trip_distribution.name}")
        # Minimum trip distance
        if config.has_option("DEFAULT", "min_trip_distance"):
            self.min_trip_distance = default.getint("min_trip_distance",
                                                    fallback=0)
        else:
            self.min_trip_distance = 0
        # Time blocks: may be a list
        self.time_blocks = (args.time_blocks if args.time_blocks else
                            config["DEFAULT"]["time_blocks"])
        self.time_blocks = self.time_blocks.split(",")
        self.time_blocks = [int(i) for i in self.time_blocks]
        logger.debug(f"Time blocks = {self.time_blocks}")
        # Log file TODO not sure if this works
        self.log_file = str(
            args.log_file if args.log_file else config["DEFAULT"]["log_file"])
        logger.debug(f"Log file = {self.log_file}")
        # Verbose output
        self.verbose = bool(
            args.verbose if args.verbose else config["DEFAULT"]["verbose"])
        logger.debug(f"Verbose = {self.verbose}")
        # Quiet output
        self.quiet = bool(
            args.quiet if args.quiet else config["DEFAULT"]["quiet"])
        logger.debug(f"Quiet = {self.quiet}")
        # Draw maps or charts
        self.draw = str(args.draw if args.draw else config["DEFAULT"]["draw"])
        for draw_option in list(Draw):
            if self.draw == draw_option.value:
                self.draw = draw_option
                break
        logger.debug(f"Draw = {self.draw}")
        # Draw update period
        self.draw_update_period = int(
            args.draw_update_period if args.
            draw_update_period else config["DEFAULT"]["draw_update_period"])
        logger.debug(f"Draw update period = {self.draw_update_period}")
        # Interpolation points
        self.interpolate = int(args.interpolate if args.interpolate else
                               config["DEFAULT"]["interpolate"])
        logger.debug(f"Interpolation points = {self.interpolate}")
        # Equilibrate
        if config.has_option("DEFAULT", "equilibrate"):
            self.equilibrate = str(args.equilibrate if args.equilibrate else
                                   config["DEFAULT"]["equilibrate"])
        else:
            self.equilibrate = Equilibration.NONE
        if self.equilibrate == "":
            self.equilibrate = Equilibration.NONE
        logger.debug(f"Equilibration = {self.equilibrate}")
        # Sequence
        if config.has_option("DEFAULT", "run_sequence"):
            self.run_sequence = str(config["DEFAULT"]["run_sequence"])
            if (self.run_sequence.lower().startswith("f")
                    or self.run_sequence.startswith("0")
                    or self.run_sequence == ""):
                self.run_sequence = False
            else:
                self.run_sequence = True
        else:
            self.run_sequence = False
        logger.debug(f"Run sequence = {self.run_sequence}")
        # Rolling window
        if config.has_option("DEFAULT", "trailing_window"):
            self.trailing_window = int(
                args.trailing_window if args.
                trailing_window else config["DEFAULT"]["trailing_window"])
        else:
            self.trailing_window = DEFAULT_TRAILING_WINDOW
        logger.debug(f"Rolling window = {self.trailing_window}")
        # Results window
        if config.has_option("DEFAULT", "results_window"):
            self.results_window = int(config["DEFAULT"]["results_window"])
        else:
            self.results_window = DEFAULT_RESULTS_WINDOW
        logger.debug(f"Results window = {self.results_window}")
        # Output file for charts
        self.output = str(
            args.output if args.output else config["DEFAULT"]["output"])
        logger.debug(f"Output file for charts = {self.output}")
        # ImageMagick directory
        self.imagemagick_dir = str(args.imagemagick_dir if args.imagemagick_dir
                                   else config["DEFAULT"]["imagemagick_dir"])
        logger.debug(f"ImageMagick_Dir = {self.imagemagick_dir}")
        # Available drivers moving
        self.available_drivers_moving = (
            args.available_drivers_moving if args.available_drivers_moving else
            config["DEFAULT"].getboolean("available_drivers_moving"))
        logger.debug(
            f"Available drivers moving = {self.available_drivers_moving}")
        if (self.equilibrate != Equilibration.NONE
                and config.has_section("EQUILIBRATION")):
            self._init_equilibration_section(config, args)
        if self.run_sequence and config.has_section("SEQUENCE"):
            self._init_sequence_section(config, args)

    def _init_equilibration_section(self, config, args):
        equilibration = config["EQUILIBRATION"]
        for option in list(Equilibration):
            if self.equilibrate.lower()[0] == option.name.lower()[0]:
                self.equilibrate = option
                logger.debug(f"Equilibration method is {option.name}")
                break
        if self.equilibrate not in list(Equilibration):
            logger.error(f"equilibrate must start with s, d, f, or n")
        # Price
        self.price = float(
            args.price if args.price else equilibration["price"])
        logger.debug(f"Price = {self.price}")
        # Driver cost
        self.driver_cost = float(args.driver_cost if args.
                                 driver_cost else equilibration["driver_cost"])
        logger.info(f"Driver cost = {self.driver_cost}")
        # Driver price factor
        if config.has_option("EQUILIBRATION", "driver_price_factor"):
            self.driver_price_factor = equilibration.getfloat(
                "driver_price_factor", fallback=1.0)
        else:
            self.driver_price_factor = 1.0
        logger.debug(f"Driver price factor = {self.driver_price_factor}")
        # Ride utility
        self.ride_utility = float(args.ride_utility if args.ride_utility else
                                  equilibration["ride_utility"])
        logger.debug(f"Ride utility = {self.ride_utility}")
        # Demand slope
        if config.has_option("EQUILIBRATION", "demand_slope"):
            self.demand_slope = equilibration.getfloat("demand_slope",
                                                       fallback=1.0)
        else:
            self.demand_slope = 1.0
        logger.debug(f"Demand slope = {self.demand_slope}")
        # Wait cost
        self.wait_cost = float(
            args.wait_cost if args.wait_cost else equilibration["wait_cost"])
        logger.debug(f"Wait cost = {self.wait_cost}")
        # Equilibration interval
        if config.has_option("EQUILIBRATION", "equilibration_interval"):
            self.equilibration_interval = int(
                args.equilibration_interval if args.equilibration_interval else
                equilibration["equilibration_interval"])
            logger.debug(
                f"Equilibration interval = {self.equilibration_interval}")

    def _init_sequence_section(self, config, args):
        sequence = config["SEQUENCE"]
        if (config.has_option("SEQUENCE", "request_rate_repeat")):
            self.request_rate_repeat = sequence.getint("request_rate_repeat",
                                                       fallback=1)
        else:
            self.request_rate_repeat = 1
        if (config.has_option("SEQUENCE", "request_rate_increment")):
            self.request_rate_increment = float(
                sequence["request_rate_increment"])
        else:
            self.request_rate_increment = 1.0
        if (config.has_option("SEQUENCE", "request_rate_max")):
            self.request_rate_max = float(sequence["request_rate_max"])
        else:
            self.request_rate_max = self.request_rate
        if (config.has_option("SEQUENCE", "driver_count_increment")):
            self.driver_count_increment = int(
                sequence["driver_count_increment"])
        else:
            self.driver_count_increment = 1
        if (config.has_option("SEQUENCE", "driver_count_max")):
            self.driver_count_max = int(sequence["driver_count_max"])
        else:
            self.driver_count_max = self.driver_count
        if (config.has_option("SEQUENCE", "driver_cost_max")):
            self.driver_cost_max = float(sequence["driver_cost_max"])
        elif hasattr(self, "driver_cost"):
            self.driver_cost_max = self.driver_cost
        else:
            self.driver_cost_max = None
        if (config.has_option("SEQUENCE", "driver_cost_increment")):
            self.driver_cost_increment = float(
                sequence["driver_cost_increment"])
        else:
            self.driver_cost_increment = None
        if (config.has_option("SEQUENCE", "wait_cost_max")):
            self.wait_cost_max = float(sequence["wait_cost_max"])
        elif hasattr(self, "wait_cost"):
            self.wait_cost_max = self.wait_cost
        else:
            self.wait_cost_max = None
        if (config.has_option("SEQUENCE", "wait_cost_increment")):
            self.wait_cost_increment = float(sequence["wait_cost_increment"])
        else:
            self.wait_cost_increment = None
