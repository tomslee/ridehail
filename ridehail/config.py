#!/usr/bin/python3

import argparse
import configparser
import logging
from datetime import datetime
import os
from ridehail.animation import Draw
from ridehail.atom import TripDistribution, Equilibration

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------------
# Parameters
# -------------------------------------------------------------------------------

GARBAGE_COLLECTION_INTERVAL = 10
SUPPLY_DEMAND_RANGE = [0.8, 1.2]
MAX_REQUESTS_PER_PERIOD = 10
DEFAULT_TIME_PERIODS = 1001
DEFAULT_REQUEST_RATE = 0.2
DEFAULT_INTERPOLATION_POINTS = 4
DEFAULT_DRIVER_COUNT = 1
DEFAULT_TRAILING_WINDOW = 20
DEFAULT_RESULTS_WINDOW = 100


class RideHailConfig():
    """
    Hold the configuration parameters for the simulation, which come from three
    places:
    - default values, unless overridden by
    - a configuration file, unless overridden by
    - command line arguments
    """
    def __init__(self):
        """
        Read the configuration file  to set up the parameters
        """
        parser = self._parser()
        args, extra = parser.parse_known_args()
        config_file = self._set_config_file(args)
        self.config_file_dir = os.path.dirname(config_file)
        self.config_file_root = (os.path.splitext(
            os.path.split(config_file)[1])[0])
        self.jsonl = ((f"{self.config_file_root}"
                       f"-{datetime.now().strftime('%Y-%m-%d-%H-%M')}"
                       ".jsonl"))
        self._set_options_from_config_file(config_file)
        self._override_options_from_command_line(args)
        self._fix_option_enums()
        for attr in dir(self):
            attr_name = attr.__str__()
            if not attr_name.startswith("_"):
                logger.debug(f"config.{attr_name} =  {getattr(self, attr)}")

    def _set_config_file(self, args):
        """
        Set self.config_file
        """
        if args.config_file is not None:
            config_file = args.config_file
        else:
            # The default config file is username.config
            # look for username.config on both Windows (USERNAME)
            # and Linux (USER)
            if os.name == "nt":
                username = os.environ['USERNAME']
            else:
                username = os.environ['USER']
            config_file = username + ".config"
        if not os.path.isfile(config_file):
            logger.error(f"Configuration file {config_file} not found.")
            exit(False)
        return config_file

    def _set_options_from_config_file(self, config_file, included=False):
        """
        Read a configuration file
        """
        config = configparser.ConfigParser(allow_no_value=True)
        config.read(config_file)
        if included is False:
            if "include_file" in config["DEFAULT"].keys():
                # only one level of inclusion
                include_config_file = config['DEFAULT']['include_file']
                include_config_file = os.path.join(self.config_file_dir,
                                                   include_config_file)
                self._set_options_from_config_file(include_config_file,
                                                   included=True)
        self._set_default_section_options(config)
        if (self.equilibrate != Equilibration.NONE
                and config.has_section("EQUILIBRATION")):
            self._set_equilibration_section_options(config)
        if hasattr(self, "run_sequence") and config.has_section("SEQUENCE"):
            self._set_sequence_section_options(config)

    def _set_default_section_options(self, config):
        default = config["DEFAULT"]
        if config.has_option("DEFAULT", "city_size"):
            self.city_size = default.getint("city_size")
        if config.has_option("DEFAULT", "driver_count"):
            self.driver_count = default.getint("driver_count")
        if config.has_option("DEFAULT", "base_demand"):
            self.base_demand = default.getfloat("base_demand")
        if config.has_option("DEFAULT", "trip_distribution"):
            self.trip_distribution = default.get("trip_distribution")
        if config.has_option("DEFAULT", "min_trip_distance"):
            self.min_trip_distance = default.getint("min_trip_distance")
        if config.has_option("DEFAULT", "time_blocks"):
            self.time_blocks = default["time_blocks"]
            self.time_blocks = self.time_blocks.split(",")
            self.time_blocks = [int(i) for i in self.time_blocks]
        if config.has_option("DEFAULT", "log_file"):
            self.log_file = default["log_file"]
        if config.has_option("DEFAULT", "verbose"):
            self.verbose = default.getboolean("verbose", fallback=False)
        if config.has_option("DEFAULT", "quiet"):
            self.quiet = default.getboolean("quiet", fallback=False)
        if config.has_option("DEFAULT", "draw"):
            self.draw = default["draw"]
        if config.has_option("DEFAULT", "draw_update_period"):
            self.draw_update_period = default.getint("draw_update_period")
        if config.has_option("DEFAULT", "interpolate"):
            self.interpolate = default.getint("interpolate")
        if config.has_option("DEFAULT", "equilibrate"):
            self.equilibrate = default["equilibrate"]
        if config.has_option("DEFAULT", "run_sequence"):
            self.run_sequence = default["run_sequence"]
            if (self.run_sequence.lower().startswith("f")
                    or self.run_sequence.startswith("0")
                    or self.run_sequence == ""):
                self.run_sequence = False
            else:
                self.run_sequence = True
        if config.has_option("DEFAULT", "trailing_window"):
            self.trailing_window = default.getint("trailing_window")
        if config.has_option("DEFAULT", "results_window"):
            self.results_window = default.getint("results_window")
        if config.has_option("DEFAULT", "output"):
            self.output = default["output"]
        if config.has_option("DEFAULT", "imagemagick_dir"):
            self.imagemagick_dir = default["imagemagick_dir"]
        if config.has_option("DEFAULT", "available_drivers_moving"):
            self.available_drivers_moving = default.getboolean(
                "available_drivers_moving")

    def _set_equilibration_section_options(self, config):
        equilibration = config["EQUILIBRATION"]
        self.price = equilibration.getfloat("price", fallback=1.0)
        self.reserved_wage = equilibration.getfloat("reserved_wage",
                                                    fallback=0.5)
        self.driver_price_factor = equilibration.getfloat(
            "driver_price_factor", fallback=1.0)
        self.demand_elasticity = equilibration.getfloat("demand_elasticity",
                                                        fallback=0.5)
        self.equilibration_interval = equilibration.getint(
            "equilibration_interval", fallback=5)

    def _set_sequence_section_options(self, config):
        sequence = config["SEQUENCE"]
        self.price_repeat = sequence.getint("price_repeat", fallback=1)
        self.price_increment = sequence.getfloat("price_increment",
                                                 fallback=0.1)
        self.price_max = sequence.getfloat("price_max", fallback=2)
        self.driver_count_increment = sequence.getint("driver_count_increment",
                                                      fallback=1)
        self.driver_count_max = sequence.getint("driver_count_max",
                                                fallback=10)
        self.driver_cost_max = sequence.getfloat("driver_cost_max",
                                                 fallback=0.8)
        self.driver_cost_increment = sequence.getfloat("driver_cost_increment",
                                                       fallback=0.1)

    def _override_options_from_command_line(self, args):
        """
        Override configuration options with command line settings
        """
        args_dict = vars(args)
        for key, val in args_dict.items():
            if hasattr(self, key) and key != "config_file" and val is not None:
                setattr(self, key, val)

    def _fix_option_enums(self):
        """
        For options that are supposed to be enum values, fix them
        """
        for option in list(Equilibration):
            if self.equilibrate.lower()[0] == option.name.lower()[0]:
                self.equilibrate = option
                logger.debug(
                    f"Equilibration method is {option.name.capitalize()}")
                break
        if self.equilibrate not in list(Equilibration):
            logger.error(f"equilibrate must start with s, d, f, or n")
        for draw_option in list(Draw):
            if self.draw == draw_option.value:
                self.draw = draw_option
                break
        if self.trip_distribution.lower().startswith("b"):
            if self.trip_distribution == "beta_short":
                self.trip_distribution = TripDistribution.BETA_SHORT
            else:
                self.trip_distribution = TripDistribution.BETA_LONG
        else:
            self.trip_distribution = TripDistribution.UNIFORM

    def _parser(self):
        """
        Define, read and parse command-line arguments.
        """
        parser = argparse.ArgumentParser(
            description="Simulate ride-hail drivers and trips.",
            usage="%(prog)s [options]",
            fromfile_prefix_chars='@')
        parser.add_argument("-c",
                            "--config_file",
                            metavar="config_file",
                            action="store",
                            type=str,
                            default=None,
                            help="""Configuration file""")
        parser.add_argument(
            "-adm",
            "--available_drivers_moving",
            metavar="available_drivers_moving",
            action="store",
            type=bool,
            default=False,
            help="""True if drivers should drive around looking for
                        a ride; False otherwise.""")
        parser.add_argument(
            "-bd",
            "--base_demand",
            metavar="base_demand",
            action="store",
            type=float,
            default=None,
            help="Base demand (request rate) before price takes effect")
        parser.add_argument("-cs",
                            "--city_size",
                            metavar="city_size",
                            action="store",
                            type=int,
                            default=None,
                            help="""Length of the city grid, in blocks.""")
        parser.add_argument("-d",
                            "--driver_count",
                            metavar="driver_count",
                            action="store",
                            type=int,
                            default=None,
                            help="number of drivers")
        parser.add_argument("-du",
                            "--draw_update_period",
                            metavar="draw_update_period",
                            action="store",
                            type=int,
                            default=None,
                            help="How often to update charts")
        parser.add_argument("-ei",
                            "--equilibration_interval",
                            metavar="equilibration_interval",
                            type=int,
                            default=None,
                            action="store",
                            help="""Interval at which to adjust supply and/or
                        demand""")
        parser.add_argument("-eq",
                            "--equilibrate",
                            metavar="equilibrate",
                            type=str,
                            default=None,
                            action="store",
                            help="""Adjust driver count to equilibrate""")
        parser.add_argument("-rw",
                            "--reserved_wage",
                            metavar="reserved_wage",
                            action="store",
                            type=float,
                            default=None,
                            help="""Driver cost per unit time""")
        parser.add_argument(
            "-i",
            "--interpolate",
            metavar="interpolate",
            action="store",
            type=int,
            default=None,
            help="""Number of interpolation points when updating
                        the map display""")
        parser.add_argument("-img",
                            "--imagemagick_dir",
                            metavar="imagemagick_dir",
                            action="store",
                            type=str,
                            default=None,
                            help="""ImageMagick Directory""")
        parser.add_argument("-l",
                            "--log_file",
                            metavar="log_file",
                            action="store",
                            type=str,
                            default=None,
                            help=("Logfile name. By default, log messages "
                                  "are written to the screen only"))
        parser.add_argument(
            "-o",
            "--output",
            metavar="output",
            action="store",
            type=str,
            default=None,
            help="""filename: graphics output as a file; gif or mp4""")
        parser.add_argument("-p",
                            "--price",
                            action="store",
                            type=float,
                            default=None,
                            help="Fixed price")
        parser.add_argument("-q",
                            "--quiet",
                            action="store_true",
                            default=None,
                            help="log only warnings and errors")
        parser.add_argument("-dr",
                            "--draw",
                            metavar="draw",
                            action="store",
                            type=str,
                            default=None,
                            help="""draw 'all', 'none', 'driver', 'wait',
                        'stats', 'equilibration', ['map']""")
        parser.add_argument("-t",
                            "--time_blocks",
                            metavar="time_blocks",
                            action="store",
                            type=int,
                            default=None,
                            help="number of time blocks")
        parser.add_argument("-v",
                            "--verbose",
                            action="store_true",
                            default=None,
                            help="log all messages, including debug")
        parser.add_argument("-tw",
                            "--trailing_window",
                            metavar="trailing_window",
                            action="store",
                            type=int,
                            default=None,
                            help="""trailing window for computing averages""")
        return parser
