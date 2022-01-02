import argparse
import configparser
import logging
import os
import sys
from datetime import datetime
from ridehail import animation as rh_animation, atom


class RideHailConfig():
    """
    Hold the configuration parameters for the simulation, which come from three
    places:
    - default values, unless overridden by
    - a configuration file, unless overridden by
    - command line arguments
    The configuration parameters are stored in sections:
    - DEFAULT
    - ANIMATION
    - EQUILIBRATION
    - SEQUENCE
    - IMPULSES
    However, the config option does not use these sections:
    it just has a lot of attributes,
    """

    # Default values here

    # Arguments
    config_file = None

    # [DEFAULT]
    title = None
    city_size = 8
    vehicle_count = 10
    base_demand = 0.5
    trip_distribution = None  # obsolete
    trip_inhomogeneity = 0.0
    min_trip_distance = 0.0
    max_trip_distance = city_size
    time_blocks = 201
    log_file = None
    verbosity = 0
    results_window = int(time_blocks * 0.25)
    animation = False
    equilibration = False
    sequence = False
    idle_vehicles_moving = True
    fix_config_file = False

    # [ANIMATION]
    animate = "none"
    animate_update_period = 1
    interpolate = 4
    animation_output_file = None
    imagemagick_dir = None
    smoothing_window = 20

    # [EQUILIBRATION]
    equilibrate = "none"
    price = 1.0
    platform_commission = 0
    demand_elasticity = 0.0
    equilibration_interval = 5
    reserved_wage = 0.0
    reserved_wage_increment = None
    reserved_wage_max = None
    wait_cost = 0.0
    wait_cost_increment = None

    # [SEQUENCE]
    sequence = None
    price_repeat = 1
    price_increment = 0.1
    price_max = None
    request_rate_increment = None
    request_rate_max = None
    vehicle_count_increment = None
    vehicle_count_max = None
    vehicle_cost_max = None
    vehicle_cost_increment = None

    # [IMPULSES]
    impulses = None
    impulse_list = None

    def __init__(self, use_config_file=True):
        """
        Read the configuration file  to set up the parameters
        """
        # logging.info("Initializing configuration")
        if use_config_file:
            parser = self._parser()
            args, extra = parser.parse_known_args()
            self.config_file = self._set_config_file(args)
            self.config_file_dir = os.path.dirname(self.config_file)
            self.config_file_root = (os.path.splitext(
                os.path.split(self.config_file)[1])[0])
            self.start_time = f"{datetime.now().strftime('%Y-%m-%d-%H-%M')}"
            self.jsonl_file = ((f"./output/{self.config_file_root}"
                                f"-{self.start_time}.jsonl"))
            self._set_options_from_config_file(self.config_file)
            self._override_options_from_command_line(args)
            self._validate_options()
        if self.verbosity == 0:
            loglevel = 30  # logging.WARNING  # 30
        elif self.verbosity == 1:
            loglevel = 20  # logging.INFO  # 20
        elif self.verbosity == 2:
            loglevel = 10  # logging.DEBUG  # 10
        else:
            loglevel = 20  # logging.INFO  # 20
        if sys.version_info[0] >= 3 and sys.version_info[1] >= 8:
            # Python 3.8+required for "force" reconfigure of logging
            if self.log_file:
                logging.basicConfig(
                    filename=self.log_file,
                    filemode="w",
                    level=loglevel,
                    force=True,
                    format="%(asctime)-15s %(levelname)-8s%(message)s")
            else:
                logging.basicConfig(
                    level=loglevel,
                    force=True,
                    format="%(asctime)-15s %(levelname)-8s%(message)s")
        self._log_config_settings()
        # if self.fix_config_file:
        #    self._write_config_file()

    def _log_config_settings(self):
        for attr in dir(self):
            attr_name = attr.__str__()
            if not attr_name.startswith("_"):
                logging.info(f"config.{attr_name} = {getattr(self, attr)}")

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
            print(f"Configuration file {config_file} not found.")
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
            if (config.has_section("ANIMATION")
                    and "include_file" in config["ANIMATION"].keys()):
                # only one level of inclusion
                include_config_file = config['ANIMATION']['include_file']
                include_config_file = os.path.join(self.config_file_dir,
                                                   include_config_file)
                self._set_options_from_config_file(include_config_file,
                                                   included=True)
        if config:
            self._set_default_section_options(config)
        if config.has_section("ANIMATION"):
            self._set_animation_section_options(config)
        if config.has_section("EQUILIBRATION"):
            self._set_equilibration_section_options(config)
        if config.has_section("SEQUENCE"):
            self._set_sequence_section_options(config)
        if config.has_section("IMPULSES"):
            self._set_impulses_section_options(config)

    def _set_default_section_options(self, config):
        default = config["DEFAULT"]
        if config.has_option("DEFAULT", "title"):
            self.title = default.get("title")
        if config.has_option("DEFAULT", "city_size"):
            self.city_size = default.getint("city_size")
        if config.has_option("DEFAULT", "vehicle_count"):
            self.vehicle_count = default.getint("vehicle_count")
        if config.has_option("DEFAULT", "base_demand"):
            self.base_demand = default.getfloat("base_demand")
        if config.has_option("DEFAULT", "trip_distribution"):
            # Deprecated
            self.trip_distribution = default.get("trip_distribution")
        if config.has_option("DEFAULT", "trip_inhomogeneity"):
            self.trip_inhomogeneity = default.getfloat("trip_inhomogeneity")
        if config.has_option("DEFAULT", "min_trip_distance"):
            self.min_trip_distance = default.getint("min_trip_distance")
            # min_trip_distance must be even for now
            self.min_trip_distance = 2 * int(self.min_trip_distance / 2)
        if config.has_option("DEFAULT", "max_trip_distance"):
            self.max_trip_distance = default.getint("max_trip_distance")
            # max_trip_distance must be even
            self.max_trip_distance = 2 * int(self.max_trip_distance / 2)
        else:
            self.max_trip_distance = self.city_size
        if config.has_option("DEFAULT", "time_blocks"):
            self.time_blocks = default.getint("time_blocks")
        if config.has_option("DEFAULT", "results_window"):
            self.results_window = default.getint("results_window")
        if config.has_option("DEFAULT", "log_file"):
            self.log_file = default["log_file"]
        if config.has_option("DEFAULT", "verbosity"):
            self.verbosity = default.getint("verbosity", fallback=0)
        if config.has_option("DEFAULT", "animation"):
            self.animation = default.getboolean("animation", fallback=False)
        if config.has_option("DEFAULT", "equilibration"):
            self.equilibration = default.getboolean("equilibration",
                                                    fallback=False)
        if config.has_option("DEFAULT", "sequence"):
            self.sequence = default.getboolean("sequence", fallback=False)
        if config.has_option("DEFAULT", "idle_vehicles_moving"):
            self.idle_vehicles_moving = default.getboolean(
                "idle_vehicles_moving")

    def _set_animation_section_options(self, config):
        """
        """
        animation = config["ANIMATION"]
        if config.has_option("ANIMATION", "animate"):
            self.animate = animation.get("animate")
        if config.has_option("ANIMATION", "animate_update_period"):
            self.animate_update_period = (
                animation.getint("animate_update_period"))
        if config.has_option("ANIMATION", "interpolate"):
            self.interpolate = animation.getint("interpolate")
        if config.has_option("ANIMATION", "animation_output_file"):
            self.animation_output_file = animation.get("animation_output_file")
            if not (self.animation_output_file.endswith("mp4")
                    or self.animation_output_file.endswith(".gif")):
                self.animation_output_file = None
        if config.has_option("ANIMATION", "imagemagick_dir"):
            self.imagemagick_dir = animation.get("imagemagick_dir")
        if config.has_option("ANIMATION", "smoothing_window"):
            self.smoothing_window = animation.getint("smoothing_window")

    def _set_equilibration_section_options(self, config):
        equilibration = config["EQUILIBRATION"]
        if config.has_option("EQUILIBRATION", "equilibrate"):
            self.equilibrate = equilibration.get("equilibrate")
        if config.has_option("EQUILIBRATION", "price"):
            self.price = equilibration.getfloat("price", fallback=1.0)
        if config.has_option("EQUILIBRATION", "platform_commission"):
            self.platform_commission = (equilibration.getfloat(
                "platform_commission", fallback=0))
        if config.has_option("EQUILIBRATION", "reserved_wage"):
            self.reserved_wage = equilibration.getfloat("reserved_wage",
                                                        fallback=0.0)
        if config.has_option("EQUILIBRATION", "demand_elasticity"):
            self.demand_elasticity = equilibration.getfloat(
                "demand_elasticity", fallback=0.0)
        if config.has_option("EQUILIBRATION", "equilibration_interval"):
            self.equilibration_interval = equilibration.getint(
                "equilibration_interval", fallback=5)

    def _set_sequence_section_options(self, config):
        sequence = config["SEQUENCE"]
        if config.has_option("SEQUENCE", "price_repeat"):
            self.price_repeat = sequence.getint("price_repeat", fallback=1)
        if config.has_option("SEQUENCE", "price_increment"):
            self.price_increment = sequence.getfloat("price_increment",
                                                     fallback=0.1)
        if config.has_option("SEQUENCE", "price_max"):
            self.price_max = sequence.getfloat("price_max", fallback=2)
        if config.has_option("SEQUENCE", "request_rate_increment"):
            self.request_rate_increment = sequence.getfloat(
                "request_rate_increment", fallback=None)
        if config.has_option("SEQUENCE", "request_rate_max"):
            self.request_rate_max = sequence.getfloat("request_rate_max",
                                                      fallback=None)
        if config.has_option("SEQUENCE", "vehicle_count_increment"):
            self.vehicle_count_increment = sequence.getint(
                "vehicle_count_increment", fallback=None)
        if config.has_option("SEQUENCE", "vehicle_count_max"):
            self.vehicle_count_max = sequence.getint("vehicle_count_max",
                                                     fallback=None)
        if config.has_option("SEQUENCE", "vehicle_cost_max"):
            self.vehicle_cost_max = sequence.getfloat("vehicle_cost_max",
                                                      fallback=None)
        if config.has_option("SEQUENCE", "vehicle_cost_increment"):
            self.vehicle_cost_increment = sequence.getfloat(
                "vehicle_cost_increment", fallback=None)

    def _set_impulses_section_options(self, config):
        impulses = config["IMPULSES"]
        if config.has_option("IMPULSES", "impulse_list"):
            self.impulse_list = impulses.get("impulse_list")
            self.impulse_list = eval(self.impulse_list)

    def _override_options_from_command_line(self, args):
        """
        Override configuration options with command line settings
        """
        args_dict = vars(args)
        for key, val in args_dict.items():
            if hasattr(self, key) and key != "config_file" and val is not None:
                setattr(self, key, val)

    def _validate_options(self):
        """
        For options that have validation constraints, impose them
        For options that are supposed to be enum values, fix them
        """
        if self.equilibration:
            for eq_option in list(atom.Equilibration):
                if self.equilibrate.lower()[0] == eq_option.name.lower()[0]:
                    self.equilibrate = eq_option
                    break
            if self.equilibrate not in list(atom.Equilibration):
                logging.error("equilibration must start with s, d, f, or n")
        else:
            self.equilibrate = atom.Equilibration.NONE
        if self.animation:
            for animate_option in list(rh_animation.Animation):
                if self.animate.lower()[0:2] == animate_option.value.lower(
                )[0:2]:
                    self.animate = animate_option
                    break
            if self.animate not in list(rh_animation.Animation):
                logging.error(
                    "animate must start with m, s, a, or n"
                    " and the first two letters must match the allowed values."
                )
            if (self.animate not in (rh_animation.Animation.MAP,
                                     rh_animation.Animation.ALL)):
                # Interpolation is relevant only if the map is displayed
                self.interpolate = 1
            if self.animation_output_file:
                if not (self.animation_output_file.endswith("mp4")
                        or self.animation_output_file.endswith(".gif")):
                    self.animation_output_file = None
        else:
            self.animate = rh_animation.Animation.NONE
        if self.trip_inhomogeneity:
            # Default 0, must be between 0 and 1
            if self.trip_inhomogeneity < 0.0 or self.trip_inhomogeneity > 1.0:
                self.trip_inhomogeneity = max(
                    min(self.trip_inhomogeneity, 1.0), 0.0)
                logging.warn("trip_inhomogeneity must be between 0.0 and 1.0: "
                             f"reset to {self.trip_inhomogeneity}")
        if self.trip_distribution is not None:
            self.trip_distribution = atom.TripDistribution.UNIFORM
            logging.warn("trip_distribution is now always set to UNIFORM."
                         " See instead self.trip_inhomogeneity")
        city_size = 2 * int(self.city_size / 2)
        if city_size != self.city_size:
            logging.warning(f"City size must be an even integer"
                            f": reset to {city_size}")
            self.city_size = city_size

    def _write_config_file(self):
        """
        Write out a configuration file, with name self.
        """
        logging.info(f"write out config file {self.config_file}")
        with open(self.config_file, 'a+') as f:
            logging.info(f"write out config file {self.config_file}")
            f.write('Hey hey')
        exit(0)

    def _parser(self):
        """
        Define, read and parse command-line arguments.
        Defaults should all be None to avoid overwriting config file
        entries
        """
        # Usage text
        parser = argparse.ArgumentParser(
            description="Simulate ride-hail vehicles and trips.",
            usage="%(prog)s [options]",
            fromfile_prefix_chars='@')
        # Config file (no flag hyphen)
        parser.add_argument("config_file",
                            metavar="config_file",
                            nargs="?",
                            action="store",
                            type=str,
                            default=None,
                            help="""Configuration file""")
        # [DEFAULT]
        parser.add_argument("-cs",
                            "--city_size",
                            metavar="city_size",
                            action="store",
                            type=int,
                            default=None,
                            help="""Length of the city grid, in blocks.""")
        parser.add_argument("-vc",
                            "--vehicle_count",
                            metavar="vehicle_count",
                            action="store",
                            type=int,
                            default=None,
                            help="number of vehicles")
        parser.add_argument(
            "-bd",
            "--base_demand",
            metavar="base_demand",
            action="store",
            type=float,
            default=None,
            help="Base demand (request rate) before price takes effect")
        parser.add_argument(
            "-ivm",
            "--idle_vehicles_moving",
            metavar="idle_vehicles_moving",
            action="store",
            type=bool,
            default=None,
            help="""True if vehicles should drive around looking for
                        a ride; False otherwise.""")
        parser.add_argument("-ti",
                            "--trip_inhomogeneity",
                            metavar="trip_inhomogeneity",
                            action="store",
                            type=float,
                            default=None,
                            help="Trip inhomogeneity (0 to 1)")
        # parser.add_argument(
        #    "-fc",
        #    "--fix_config_file",
        #    dest="fix_config_file",
        #    action="store_true",
        #    help="""Fix the supplied configuration file and quit.
        #    If the named config file does not exist, write one out."""
        #    )
        parser.add_argument("-l",
                            "--log_file",
                            metavar="log_file",
                            action="store",
                            type=str,
                            default=None,
                            help=("Logfile name. By default, log messages "
                                  "are written to the screen only"))
        parser.add_argument("-t",
                            "--time_blocks",
                            metavar="time_blocks",
                            action="store",
                            type=int,
                            default=None,
                            help="number of time blocks")
        parser.add_argument(
            "-v",
            "--verbosity",
            action="store",
            metavar="verbosity",
            type=int,
            help="""log verbosity level: 0=WARNING, 1=INFO, 2=DEBUG""")

        # [ANIMATION]
        parser.add_argument(
            "-a",
            "--animate",
            metavar="animate",
            action="store",
            type=str,
            default=None,
            help="""animate 'all', 'stats', 'bar', 'map', 'none',
                        ['map']""")
        parser.add_argument(
            "-ai",
            "--interpolate",
            metavar="interpolate",
            action="store",
            type=int,
            default=None,
            help="""Number of interpolation points when updating
                        the map display""")
        parser.add_argument("-au",
                            "--animate_update_period",
                            metavar="animate_update_period",
                            action="store",
                            type=int,
                            default=None,
                            help="How often to update charts")
        parser.add_argument("-aimg",
                            "--imagemagick_dir",
                            metavar="imagemagick_dir",
                            action="store",
                            type=str,
                            default=None,
                            help="""ImageMagick Directory""")
        parser.add_argument(
            "-aof",
            "--animation_output_file",
            metavar="animation_output_file",
            action="store",
            type=str,
            default=None,
            help="""filename: graphics output as a file; gif or mp4""")
        parser.add_argument("-sw",
                            "--smoothing_window",
                            metavar="smoothing_window",
                            action="store",
                            type=int,
                            default=None,
                            help="""Smoothing window for computing averages""")

        # [EQUILIBRATION]
        parser.add_argument("-ei",
                            "--equilibration_interval",
                            metavar="equilibration_interval",
                            type=int,
                            action="store",
                            help="""Interval at which to adjust supply and/or
                        demand""")
        parser.add_argument("-rw",
                            "--reserved_wage",
                            metavar="reserved_wage",
                            action="store",
                            type=float,
                            help="""Vehicle cost per unit time""")
        parser.add_argument("-p",
                            "--price",
                            action="store",
                            type=float,
                            help="Fixed price")
        return parser


class WritableConfig():
    def __init__(self, config):
        self.title = config.title
        self.start_time = config.start_time
        self.city_size = config.city_size
        self.base_demand = config.base_demand
        self.vehicle_count = config.vehicle_count
        self.trip_inhomogeneity = config.trip_inhomogeneity
        self.min_trip_distance = config.min_trip_distance
        self.max_trip_distance = config.max_trip_distance
        self.time_blocks = config.time_blocks
        self.results_window = config.results_window
        self.idle_vehicles_moving = config.idle_vehicles_moving
        if config.equilibration:
            equilibration = {}
            equilibration["equilibrate"] = config.equilibrate.name
            equilibration["price"] = config.price
            equilibration["platform_commission"] = config.platform_commission
            equilibration["reserved_wage"] = config.reserved_wage
            equilibration["demand_elasticity"] = config.demand_elasticity
            equilibration["equilibration_interval"] = config.equilibration_interval
            self.equilibration = equilibration
