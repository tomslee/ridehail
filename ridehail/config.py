#!/usr/bin/python3

import argparse
import configparser
import logging
import os
from datetime import datetime
from ridehail import animation
from ridehail import atom

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

    # Some attributes have defaults
    city_size = 20
    driver_count = 1
    base_demand = 0.2
    trip_distribution = atom.TripDistribution.UNIFORM
    min_trip_distance = 0.0
    time_blocks = 201
    verbose = False
    quiet = False
    trailing_window = min(int(1.0 / base_demand), 1)
    results_window = int(time_blocks * 0.25)
    available_drivers_moving = True

    animate = True
    equilibrate = atom.Equilibration.NONE
    sequence = False

    def __init__(self, use_config_file=True):
        """
        Read the configuration file  to set up the parameters
        """
        if use_config_file:
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
            self._print_config()

    def _print_config(self):
        for attr in dir(self):
            attr_name = attr.__str__()
            if not attr_name.startswith("_"):
                print(f"config.{attr_name} = {getattr(self, attr)}")

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
        if (self.animate and config.has_section("ANIMATION")):
            self._set_animation_section_options(config)
        if (self.equilibrate != atom.Equilibration.NONE
                and config.has_section("EQUILIBRATION")):
            self._set_equilibration_section_options(config)
        if hasattr(self, "sequence") and config.has_section("SEQUENCE"):
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
            self.time_blocks = default.getint("time_blocks")
        if config.has_option("DEFAULT", "log_file"):
            self.log_file = default["log_file"]
        if config.has_option("DEFAULT", "verbose"):
            self.verbose = default.getboolean("verbose", fallback=False)
        if config.has_option("DEFAULT", "quiet"):
            self.quiet = default.getboolean("quiet", fallback=False)
        if config.has_option("DEFAULT", "animate"):
            self.animate = default.getboolean("animate", fallback=False)
        if config.has_option("DEFAULT", "equilibrate"):
            self.equilibrate = default["equilibrate"]
        if config.has_option("DEFAULT", "sequence"):
            self.sequence = default["sequence"]
            if (self.sequence.lower().startswith("f")
                    or self.sequence.startswith("0") or self.sequence == ""):
                self.sequence = False
            else:
                self.sequence = True
        if config.has_option("DEFAULT", "trailing_window"):
            self.trailing_window = default.getint("trailing_window")
        if config.has_option("DEFAULT", "results_window"):
            self.results_window = default.getint("results_window")
        if config.has_option("DEFAULT", "imagemagick_dir"):
            self.imagemagick_dir = default["imagemagick_dir"]
        if config.has_option("DEFAULT", "available_drivers_moving"):
            self.available_drivers_moving = default.getboolean(
                "available_drivers_moving")

    def _set_animation_section_options(self, config):
        """
        """
        animate = config["ANIMATION"]
        if config.has_option("ANIMATION", "animate"):
            self.animate = animate["animate"]
        if config.has_option("ANIMATION", "animate_update_period"):
            self.animate_update_period = (
                animate.getint("animate_update_period"))
        if config.has_option("ANIMATION", "interpolate"):
            self.interpolate = animate.getint("interpolate")
        if config.has_option("ANIMATION", "output"):
            self.output = animate.get("output")

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
        for option in list(atom.Equilibration):
            if self.equilibrate.lower()[0] == option.name.lower()[0]:
                self.equilibrate = option
                logger.debug(
                    f"Equilibration method is {option.name.capitalize()}")
                break
        if self.equilibrate not in list(atom.Equilibration):
            logger.error(f"equilibrate must start with s, d, f, or n")
        for animate_option in list(animation.Animate):
            if self.animate == animate_option.value:
                self.animate = animate_option
                break
        if self.animate not in (animation.Animate.MAP, animation.Animate.ALL):
            # Interpolation is relevant only if the map is displayed
            self.interpolate = 1
        if self.trip_distribution.lower().startswith("b"):
            if self.trip_distribution == "beta_short":
                self.trip_distribution = atom.TripDistribution.BETA_SHORT
            else:
                self.trip_distribution = atom.TripDistribution.BETA_LONG
        else:
            self.trip_distribution = atom.TripDistribution.UNIFORM

    def _parser(self):
        """
        Define, read and parse command-line arguments.
        Defaults should all be None to avoid overwriting config file
        entries
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
            default=None,
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
        parser.add_argument("-au",
                            "--animate_update_period",
                            metavar="animate_update_period",
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
        parser.add_argument(
            "-eq",
            "--equilibrate",
            metavar="equilibrate",
            type=str,
            default=None,
            action="store",
            help="""Adjust driver count and ride requests to equilibrate""")
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
        parser.add_argument("-a",
                            "--animate",
                            metavar="animate",
                            action="store",
                            type=str,
                            default=None,
                            help="""animate 'all', 'none', 'driver', 'wait',
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
