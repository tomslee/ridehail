import argparse
import configparser
import logging
import os
import sys
from enum import Enum
from configupdater import ConfigUpdater
from datetime import datetime
from ridehail import animation as rh_animation, atom

# Initial logging config, which may be overriden by config file or
# command-line setting later
logging.basicConfig(level=logging.INFO,
                    force=True,
                    format=("[%(filename)12s %(lineno)4s: %(funcName)20s()] "
                            "%(levelname) - 8s%(message)s"))


class ConfigItem():
    """
    Represents a single configuration parameter, which may be specified through
    a config file, a command-line argument (some) or as a default
    """
    def __init__(self,
                 name=None,
                 type=None,
                 default=None,
                 action=None,
                 description=[],
                 help=None,
                 short_form=None,
                 metavar=None,
                 config_section=None,
                 weight=999):
        self.name = name
        self.type = type
        self.default = default
        self.action = action
        self.value = None
        self.description = description
        self.help = help
        self.short_form = short_form
        self.metavar = metavar
        self.config_section = config_section
        self.weight = weight

        def __lt__(self, other):
            # Use the "weight" attribute to decide the order
            # in which the items appear in each section of
            # the config file
            return self.weight < other.weight


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
    config_file = ConfigItem(name="config_file",
                             type=str,
                             default=None,
                             action="store",
                             config_section=None)
    config_file.help = ("configuration file")
    config_file.description = (
        f"configuration file ({config_file.type.__name__}, "
        f"default {config_file.default})", )
    # [DEFAULT]
    title = ConfigItem(name="title",
                       type=str,
                       default=None,
                       action="store",
                       short_form="t",
                       metavar="string",
                       config_section="DEFAULT",
                       weight=0)
    title.help = "the display title for plots and animations"
    title.description = (
        f"plot title ({title.type.__name__}, default {title.default})",
        "The title is recorded in the output json file",
        "and is used as the plot title.",
    )
    city_size = ConfigItem(name="city_size",
                           type=int,
                           default=8,
                           action='store',
                           short_form="cs",
                           metavar="even-integer",
                           config_section="DEFAULT",
                           weight=10)
    city_size.help = """the number of blocks on each side of the city"""
    city_size.description = (
        f"city size, in blocks "
        f"(even {city_size.type.__name__}, default {city_size.default})",
        "The grid is a square, with this number of blocks on each side.",
        "A block is often a minute, or a kilometer.",
    )
    vehicle_count = ConfigItem(name="vehicle_count",
                               type=int,
                               default=0,
                               action='store',
                               short_form="vc",
                               metavar="N",
                               config_section="DEFAULT",
                               weight=20)
    vehicle_count.help = (
        "the number of vehicles at the start of the simulation "
        "(it's more complex when equilibrate is set)")
    vehicle_count.description = (
        f"vehicle count ({vehicle_count.type.__name__}, "
        f"default {vehicle_count.default})",
        "The number of vehicles in the simulation. For simulations with ",
        "equilibration or sequences, this is the number of vehicles at ",
        " the beginning of the simulation.",
    )
    base_demand = ConfigItem(name="base_demand",
                             type=float,
                             default=0.0,
                             action='store',
                             short_form="bd",
                             metavar="float",
                             config_section="DEFAULT",
                             weight=40)
    base_demand.help = ("the request rate at the start of the simulation "
                        "(it's more complex when equilibrate is set)")
    base_demand.description = (
        f"base demand ({base_demand.type.__name__}, "
        f"default {base_demand.default})",
        "For simulations without equilibration, the demand for trips.",
        "Alternatively, the request rate (requests per block of time).",
        "For simulations with equilibration, the request rate is given by ",
        "", "      demand = base_demand * price ** (-elasticity)")
    trip_distribution = ConfigItem(name="trip_distribution",
                                   type=float,
                                   default=None,
                                   action='store',
                                   short_form="td",
                                   config_section="DEFAULT",
                                   weight=500)
    trip_distribution.description = (
        "DEPRECATION NOTICE: The trip_distribution option is deprecated",
        "This option is now ignored.",
        "To configure trip distribution, use the trip_inhomogeneity option.",
    )
    trip_inhomogeneity = ConfigItem(name="trip_inhomogeneity",
                                    type=float,
                                    default=0.0,
                                    action='store',
                                    short_form="ti",
                                    metavar="float",
                                    config_section="DEFAULT",
                                    weight=50)
    trip_inhomogeneity.help = ("float, in [0.0], [1.0]")
    trip_inhomogeneity.description = (
        f"trip inhomogeneity ({trip_inhomogeneity.type.__name__} "
        f"in the range [0.0, 1.0], default {trip_inhomogeneity.default})",
        "Trips originate in one of two zones: central zone or outer zone.",
        "The inner zone has sides C/2, and is centred on (C/2, C/2); ",
        "the outer zone is the remaining 3/4 of the area.",
        "At 0: the distribution of trip origins is homogenous.",
        "At 1: all trip origins are inside the central zone.",
    )
    trip_inhomogeneous_destinations = ConfigItem(
        name="trip_inhomogeneous_destinations",
        action='store_true',
        short_form="tid",
        config_section="DEFAULT",
        weight=55)
    trip_inhomogeneous_destinations.help = (
        "if set, both origins and destinations are affected by inhomogeneity")
    trip_inhomogeneous_destinations.description = (
        "trip inhomogeneous destinations"
        "If not set, only trip origins are affected by trip_inohomgeneity.",
        "If set, both origins and destinations are affected.",
        "If set, mean trip length is also affected.")
    min_trip_distance = ConfigItem(name="min_trip_distance",
                                   type=int,
                                   default=0,
                                   action='store',
                                   short_form="tmin",
                                   metavar="N",
                                   config_section="DEFAULT",
                                   weight=60)
    min_trip_distance.help = ("min trip distance, in blocks")
    min_trip_distance.description = (
        f"minimum trip distance ({min_trip_distance.type.__name__}, "
        f"default {min_trip_distance.default})",
        "A trip must be at least this long.")
    max_trip_distance = ConfigItem(name="max_trip_distance",
                                   type=int,
                                   default=city_size.default,
                                   action='store',
                                   short_form="tmax",
                                   metavar="N",
                                   config_section="DEFAULT",
                                   weight=70)
    max_trip_distance.help = ("max trip distance, in blocks")
    max_trip_distance.description = (
        f"maximum trip distance ({max_trip_distance.type.__name__}, "
        f"default city_size)", "A trip must be at most this long.")
    time_blocks = ConfigItem(name="time_blocks",
                             type=int,
                             default=201,
                             action='store',
                             short_form="b",
                             metavar="N",
                             config_section="DEFAULT",
                             weight=80)
    time_blocks.help = ("duration of the simulation, in blocks")
    time_blocks.description = (
        f"time blocks ({time_blocks.type.__name__}, "
        f"default {time_blocks.default})",
        "The number of time periods (blocks) to run the simulation.",
        "Each period corresponds to a vehicle travelling one block.",
    )
    random_number_seed = ConfigItem(name="random_number_seed",
                                    type=int,
                                    default=None,
                                    action='store',
                                    short_form="rns",
                                    metavar="N",
                                    config_section="DEFAULT",
                                    weight=87)
    random_number_seed.help = ("set a seed for random number generation")
    random_number_seed.description = (
        f"random number seed ({random_number_seed.type.__name__}, "
        f"default {random_number_seed.default})",
        "Random numbers are used throughout the simulation. ",
        "Set the seed to an integer for reproducible simulations.",
        "If None, then each simulation will be different.")
    idle_vehicles_moving = ConfigItem(name="idle_vehicles_moving",
                                      type=bool,
                                      default=True,
                                      action='store',
                                      short_form="ivm",
                                      config_section="DEFAULT",
                                      weight=85)
    idle_vehicles_moving.help = ("by default, idle vehicles move; "
                                 "set this to keep them stationary")
    idle_vehicles_moving.description = (
        f"idle vehicles moving ({idle_vehicles_moving.type.__name__}, "
        f"default True)",
        "If True, vehicles in the 'available' state move around",
        "If False, they stay where they are.",
    )
    results_window = ConfigItem(name="results_window",
                                type=int,
                                default=50,
                                action='store',
                                short_form="rw",
                                metavar="N",
                                config_section="DEFAULT",
                                weight=90)
    results_window.help = ("number of blocks over which to average results "
                           "computed at the end of the simulation")
    results_window.description = (
        f"results window ({results_window.type.__name__}, "
        f"default {results_window.default})",
        "At the end of the run, compute the final results by averaging over",
        "results_window blocks. Typically bigger than smoothing_window.",
    )
    log_file = ConfigItem(name="log_file",
                          type=str,
                          default=None,
                          action='store',
                          short_form="l",
                          metavar="filename",
                          config_section="DEFAULT",
                          weight=100)
    log_file.help = "file name for logging messages"
    log_file.description = (
        f"log file ({log_file.type.__name__}, default {log_file.default})",
        "The file name for logging messages.",
        "By default, log messages are written to standard output only.",
    )
    verbosity = ConfigItem(name="verbosity",
                           type=int,
                           default=0,
                           action='store',
                           short_form="v",
                           metavar="N",
                           config_section="DEFAULT",
                           weight=110)
    verbosity.help = ("[0] (print warnings only), 1 (+info), 2 (+debug)")
    verbosity.description = (
        f"verbosity ({verbosity.type.__name__}, default {verbosity.default})",
        "If 0, log warning, and error messages",
        "If 1, log info, warning, and error messages",
        "If 2, log debug, information, warning, and error messages.",
    )
    animate = ConfigItem(name="animate",
                         action='store_true',
                         short_form="a",
                         config_section="DEFAULT",
                         weight=120)
    animate.help = "display an animation of the simulation"
    animate.description = (
        "animate the simulation",
        "If set, configure the animation in the [ANIMATION] section.",
    )
    equilibrate = ConfigItem(name="equilibrate",
                             action='store_true',
                             short_form="e",
                             config_section="DEFAULT",
                             weight=130)
    equilibrate.help = (
        "equilibrate the supply of vehicles and demand for trips")
    equilibrate.description = (
        "equilibrate the supply of vehicles and demand for trips",
        "If set, configure the equilibration in the [EQUILIBRATION] section.",
    )
    run_sequence = ConfigItem(name="run_sequence",
                              action='store_true',
                              short_form="s",
                              config_section="DEFAULT",
                              weight=140)
    run_sequence.help = (
        "run a sequence of simulations with different vehicle "
        "counts or request rates")
    run_sequence.description = (
        "run a sequence of simulations with different vehicle "
        "counts or request rates",
        "If set, configure the sequence in the [SEQUENCE] section.",
    )
    fix_config_file = ConfigItem(name="fix_config_file",
                                 action='store_true',
                                 short_form="fc",
                                 config_section="DEFAULT",
                                 weight=150)
    fix_config_file.help = (
        "backup the configuration file, update in place, and exit")
    fix_config_file.description = (
        "fix the configuration file and exit"
        "If set, update the configuration file with the current descriptions",
        "A backup copy of the configuration file is made",
    )

    # [ANIMATION]
    animation_style = ConfigItem(name="animation_style",
                                 type=str,
                                 default=None,
                                 action='store',
                                 short_form="as",
                                 config_section="ANIMATION",
                                 weight=0)
    animation_style.help = (
        "the charts to display. none, map, stats, all, bar, sequence")
    animation_style.description = (
        f"animation style ({animation_style.type.__name__}, "
        f"default {animation_style.default})",
        "Select which charts and / or maps to display.",
        "Possible values include...",
        "- none (no charts)",
        "- map",
        "- stats",
        "- all (displays map + stats)",
        "- bar",
        "- sequence.",
    )
    animate_update_period = ConfigItem(name="animate_update_period",
                                       type=int,
                                       default=1,
                                       action='store',
                                       short_form="ap",
                                       metavar="N",
                                       config_section="ANIMATION",
                                       weight=10)
    animate_update_period.help = "update charts every N blocks"
    animate_update_period.description = (
        f"animate update period ({animate_update_period.type.__name__}, "
        f"default {animate_update_period.default})",
        "Update charts every N blocks.",
    )
    annotation = ConfigItem(name="annotation",
                            type=str,
                            default=None,
                            action='store',
                            short_form="an",
                            metavar="string",
                            config_section="ANIMATION",
                            weight=20)
    annotation.help = ("an annotation added to map and statistics plots")
    annotation.description = (f"annotation ({annotation.type.__name__}, "
                              f"default {annotation.default})",
                              "An annotation added to map and stats plots")
    interpolate = ConfigItem(name="interpolate",
                             type=int,
                             default=1,
                             action='store',
                             short_form="ai",
                             metavar="N",
                             config_section="ANIMATION",
                             weight=30)
    interpolate.help = (
        "for map animations, number of interpolated points per block")
    interpolate.description = (
        f"interpolate ({interpolate.type.__name__}, "
        f"default {interpolate.default})",
        "For the map display (only) add this many interpolated points between",
        "time periods so the car movements are smoother.",
    )
    animation_output_file = ConfigItem(name="animation_output_file",
                                       type=str,
                                       default=None,
                                       action='store',
                                       short_form="aof",
                                       metavar="filename",
                                       config_section="ANIMATION",
                                       weight=40)
    animation_output_file.help = ("write animation to a file (.mp4 or .gif) "
                                  "instead of displaying on screen")
    animation_output_file.description = (
        f"animation output file ({animation_output_file.type.__name__}, "
        f"default {animation_output_file.default})",
        "Supply a file name in which to save the animations",
        "If none is supplied, display animations on the screen only.",
    )
    imagemagick_dir = ConfigItem(name="imagemagick_dir",
                                 type=str,
                                 default=None,
                                 action='store',
                                 short_form="aid",
                                 config_section="ANIMATION",
                                 weight=50)
    imagemagick_dir.help = ("ImageMagick directory. "
                            "Not needed if it is in the path")
    imagemagick_dir.description = (
        f"ImageMagick directory ({imagemagick_dir.type.__name__}, "
        f"default {imagemagick_dir.default})",
        "If you choose an MP4 or GIF output (output parameter) then you need ",
        "ImageMagick. This is the directory in which it is installed,",
        "for example:",
        "",
        "  imagemagick_dir = /Program Files/ImageMagick-7.0.9-Q16 ",
    )
    smoothing_window = ConfigItem(name="smoothing_window",
                                  type=int,
                                  default=None,
                                  action='store',
                                  short_form="asw",
                                  metavar="N",
                                  config_section="ANIMATION",
                                  weight=60)
    smoothing_window.help = (
        "for graphs, display rolling averages over this many blocks")
    smoothing_window.description = (
        f"smoothing window ({smoothing_window.type.__name__}, "
        f"default {smoothing_window.default})",
        "Rolling window in which to compute trailing averages ",
        "(wait times, busy fraction etc) used in graphs and in calculations.",
    )

    # [EQUILIBRATION]
    equilibration = ConfigItem(name="equilibration",
                               type=str,
                               default=atom.Equilibration.NONE,
                               action='store',
                               short_form="eq",
                               config_section="EQUILIBRATION",
                               weight=0)
    equilibration.help = ("the equilibration method: none or price")
    equilibration.description = (
        f"equilibration method ({equilibration.type.__name__} "
        f"converted to enum, default {equilibration.default})",
        "Valid values are 'None' or 'Price (case insensitive)'.",
    )
    price = ConfigItem(name="price",
                       type=float,
                       default=1.0,
                       action='store',
                       short_form="eqp",
                       metavar="float",
                       config_section="EQUILIBRATION",
                       weight=10)
    price.help = ("price per block, used when equilibrating")
    price.description = (
        f"price ({price.type.__name__}, default {price.default})",
        "Price paid by passengers, input to the equilibration process.",
    )
    platform_commission = ConfigItem(name="platform_commission",
                                     type=float,
                                     default=0.0,
                                     action='store',
                                     short_form="eqc",
                                     metavar="float",
                                     config_section="EQUILIBRATION",
                                     weight=20)
    platform_commission.help = ("fraction of fare taken by the platform, "
                                "used when equilibrating")
    platform_commission.description = (
        f"platform commission F ({platform_commission.type.__name__}, "
        f"default {platform_commission.default})",
        "The vehicle utility per block is U = P.B.(1 - F) - C_d, ",
        "where F = platform commission.",
        "F > 0 amounts to the platform taking a commission, ",
        "F < 0 is the platform subsidizing vehicles.",
    )
    demand_elasticity = ConfigItem(name="demand_elasticity",
                                   type=float,
                                   default=0.0,
                                   action='store',
                                   short_form="eqe",
                                   metavar="k",
                                   config_section="EQUILIBRATION",
                                   weight=30)
    demand_elasticity.help = (
        "demand elasticity (float, default 0), used when equilibrating")
    demand_elasticity.description = (
        f"demand elasticity ({demand_elasticity.type.__name__}, "
        f"default {demand_elasticity.default})",
        "The demand (request rate) = k * p ^ (-r), ",
        "where r is the demand elasticity and k is the base demand",
        "If left at the default, the demand does not depend on price.",
    )
    equilibration_interval = ConfigItem(name="equilibration_interval",
                                        type=int,
                                        default=1,
                                        action='store',
                                        short_form="eqi",
                                        metavar="N",
                                        config_section="EQUILIBRATION",
                                        weight=40)
    equilibration_interval.help = (
        "adjust supply and demand every N blocks, when equilibrating")
    equilibration_interval.description = (
        f"equilibration interval ({equilibration_interval.type.__name__}, "
        f"default {equilibration_interval.default})",
        "The number of blocks at which equilibration steps are chosen.",
    )
    reserved_wage = ConfigItem(name="reserved_wage",
                               type=float,
                               default=0.5,
                               action='store',
                               short_form="eqw",
                               metavar="float",
                               config_section="EQUILIBRATION",
                               weight=5)
    reserved_wage.help = (
        "vehicles must earn this to be available, used when equilibrating")
    reserved_wage.description = (
        f"reserved wage ({reserved_wage.type.__name__}, "
        f"default {reserved_wage.default})",
        "Vehicle utility per block is U = P.B(1 - F) - C_d, ",
        "where C_d = reserved wage.",
    )

    # [SEQUENCE]
    request_rate_increment = ConfigItem(name="request_rate_increment",
                                        type=float,
                                        default=None,
                                        action='store',
                                        short_form="sri",
                                        metavar="float",
                                        config_section="SEQUENCE",
                                        weight=10)
    request_rate_increment.help = (
        "determines the demand for trips in each simulation of a sequence")
    request_rate_increment.description = (
        f"request rate increment ({request_rate_increment.type.__name__}, "
        f"default {request_rate_increment.default})",
        "The increment in a sequence of request rates",
        "The starting value is 'base_demand' in the DEFAULT section.",
    )
    request_rate_max = ConfigItem(name="request_rate_max",
                                  type=float,
                                  default=None,
                                  action='store',
                                  short_form="srm",
                                  metavar="float",
                                  config_section="SEQUENCE",
                                  weight=20)
    request_rate_max.help = ("max request rate for a sequence")
    request_rate_max.description = (
        f"request rate max ({request_rate_max.type.__name__}, "
        f"default {request_rate_max.default})",
        "The maximum value in a sequence of request rates",
        "The starting value is 'base_demand' in the DEFAULT section.",
    )
    vehicle_count_increment = ConfigItem(name="vehicle_count_increment",
                                         type=int,
                                         default=None,
                                         action='store',
                                         short_form="svi",
                                         config_section="SEQUENCE",
                                         weight=30)
    vehicle_count_increment.help = ("increment vehicle count for a sequence")
    vehicle_count_increment.description = (
        f"vehicle count increment ({vehicle_count_increment.type.__name__}, "
        f"default {vehicle_count_increment.default})",
        "The increment in a sequence of vehicle counts.",
    )
    vehicle_count_max = ConfigItem(name="vehicle_count_max",
                                   type=int,
                                   default=None,
                                   action='store',
                                   short_form="svm",
                                   config_section="SEQUENCE",
                                   weight=40)
    vehicle_count_max.help = ("max vehicle count for a sequence")
    vehicle_count_max.description = (
        f"vehicle Count Max ({vehicle_count_max.type.__name__}, "
        f"default {vehicle_count_max.default})",
        "The maximum value in a sequence of vehicle counts.")

    # [IMPULSES]
    impulse_list = ConfigItem(name="impulse_list",
                              default=None,
                              action='store',
                              type=dict,
                              short_form="il",
                              config_section="IMPULSES")
    impulse_list.help = ("a json document describing sudden "
                         "changes during the simulation")
    impulse_list.description = (
        f"impulse list ({impulse_list.type.__name__}, "
        f"default {impulse_list.default})",
        "Sudden changes during the simulation",
        "Write as a list of dictionaries. For example...",
        "impulse_list = [{'block': 480, 'base_demand': 20.0},",
        "   {'block': 960, 'base_demand': 18.0},",
        "   {'block': 1080, 'base_demand': 7},", "   ]")

    def __init__(self, use_config_file=True):
        """
        Read the configuration file  to set up the parameters
        """
        for attr in dir(self):
            # assign default values
            option = getattr(self, attr)
            if isinstance(option, ConfigItem):
                option.value = option.default

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
        if self.verbosity.value == 0:
            loglevel = 30  # logging.WARNING
        elif self.verbosity.value == 1:
            loglevel = 20  # logging.INFO
        elif self.verbosity.value == 2:
            loglevel = 10  # logging.DEBUG
        else:
            loglevel = logging.INFO
        if sys.version_info[0] >= 3 and sys.version_info[1] >= 8:
            # Python 3.8+required for "force" reconfigure of logging
            if self.log_file.value:
                logging.basicConfig(
                    filename=self.log_file.value,
                    filemode="w",
                    level=loglevel,
                    force=True,
                    format=("[%(filename)12s %(lineno)4s: %(funcName)20s()] "
                            "%(levelname) - 8s%(message)s"))
            else:
                logging.basicConfig(
                    level=loglevel,
                    force=True,
                    format=("[%(filename)12s %(lineno)4s: %(funcName)20s()] "
                            "%(levelname) - 8s%(message)s"))
        self._log_config_settings()
        if self.fix_config_file.value:
            self._write_config_file()
            sys.exit(0)

    def _log_config_settings(self):
        for attr in dir(self):
            attr_name = attr.__str__()
            option = getattr(self, attr)
            if isinstance(option, ConfigItem):
                logging.info(
                    f"config.{attr_name} = {getattr(self, attr).value}")

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
            # exit(False)
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
        if self.run_sequence.value and config.has_section("SEQUENCE"):
            self._set_sequence_section_options(config)
        if config.has_section("IMPULSES"):
            self._set_impulses_section_options(config)

    def _set_default_section_options(self, config):
        default = config["DEFAULT"]
        if config.has_option("DEFAULT", "title"):
            self.title.value = default.get("title")
        if config.has_option("DEFAULT", "city_size"):
            self.city_size.value = default.getint("city_size")
        if config.has_option("DEFAULT", "vehicle_count"):
            self.vehicle_count.value = default.getint("vehicle_count")
        if config.has_option("DEFAULT", "base_demand"):
            self.base_demand.value = default.getfloat("base_demand")
        if config.has_option("DEFAULT", "trip_distribution"):
            # Deprecated
            pass
        if config.has_option("DEFAULT", "trip_inhomogeneity"):
            self.trip_inhomogeneity.value = default.getfloat(
                "trip_inhomogeneity")
        if config.has_option("DEFAULT", "trip_inhomogeneous_destinations"):
            self.trip_inhomogeneous_destinations.value = default.getboolean(
                "trip_inhomogeneous_destinations", fallback=False)
        if config.has_option("DEFAULT", "min_trip_distance"):
            self.min_trip_distance.value = default.getint("min_trip_distance")
            # min_trip_distance must be even for now
            self.min_trip_distance.value = 2 * int(
                self.min_trip_distance.value / 2)
        if config.has_option("DEFAULT", "max_trip_distance"):
            try:
                self.max_trip_distance.value = default.getint(
                    "max_trip_distance")
                # max_trip_distance must be even
                self.max_trip_distance.value = 2 * int(
                    self.max_trip_distance.value / 2)
            except ValueError:
                self.max_trip_distance.value = self.city_size.value
        else:
            self.max_trip_distance.value = self.city_size.value
        if config.has_option("DEFAULT", "time_blocks"):
            self.time_blocks.value = default.getint("time_blocks")
        if config.has_option("DEFAULT", "results_window"):
            self.results_window.value = default.getint("results_window")
        if config.has_option("DEFAULT", "idle_vehicles_moving"):
            self.idle_vehicles_moving.value = default.getboolean(
                "idle_vehicles_moving")
        if config.has_option("DEFAULT", "random_number_seed"):
            try:
                self.random_number_seed.value = default.getint(
                    "random_number_seed")
            except ValueError:
                # leave as the default
                pass
        if config.has_option("DEFAULT", "log_file"):
            self.log_file.value = default["log_file"]
        if config.has_option("DEFAULT", "verbosity"):
            self.verbosity.value = default.getint("verbosity", fallback=0)
        if config.has_option("DEFAULT", "animate"):
            self.animate.value = default.getboolean("animate", fallback=False)
        if config.has_option("DEFAULT", "equilibrate"):
            self.equilibrate.value = default.getboolean("equilibrate",
                                                        fallback=False)
        if config.has_option("DEFAULT", "run_sequence"):
            self.run_sequence.value = default.getboolean("run_sequence",
                                                         fallback=False)

    def _set_animation_section_options(self, config):
        """
        """
        animation = config["ANIMATION"]
        if config.has_option("ANIMATION", "animation_style"):
            try:
                self.animation_style.value = animation.get("animation_style")
            except ValueError:
                pass
        if config.has_option("ANIMATION", "animate_update_period"):
            try:
                self.animate_update_period.value = (
                    animation.getint("animate_update_period"))
            except ValueError:
                pass
        if config.has_option("ANIMATION", "interpolate"):
            try:
                self.interpolate.value = animation.getint("interpolate")
            except ValueError:
                pass
        if config.has_option("ANIMATION", "animation_output_file"):
            try:
                self.animation_output_file.value = animation.get(
                    "animation_output_file")
            except ValueError:
                pass
        if config.has_option("ANIMATION", "annotation"):
            try:
                self.annotation.value = animation.get("annotation")
            except ValueError:
                pass
        if config.has_option("ANIMATION", "imagemagick_dir"):
            try:
                self.imagemagick_dir.value = animation.get("imagemagick_dir")
            except ValueError:
                pass
        if config.has_option("ANIMATION", "smoothing_window"):
            try:
                self.smoothing_window.value = animation.getint(
                    "smoothing_window")
            except ValueError:
                pass

    def _set_equilibration_section_options(self, config):
        equilibration = config["EQUILIBRATION"]
        if config.has_option("EQUILIBRATION", "equilibration"):
            self.equilibration.value = equilibration.get("equilibration")
        if config.has_option("EQUILIBRATION", "price"):
            self.price.value = equilibration.getfloat("price", fallback=1.0)
        if config.has_option("EQUILIBRATION", "platform_commission"):
            self.platform_commission.value = (equilibration.getfloat(
                "platform_commission", fallback=0))
        if config.has_option("EQUILIBRATION", "reserved_wage"):
            self.reserved_wage.value = equilibration.getfloat("reserved_wage",
                                                              fallback=0.0)
        if config.has_option("EQUILIBRATION", "demand_elasticity"):
            self.demand_elasticity.value = equilibration.getfloat(
                "demand_elasticity", fallback=0.0)
        if config.has_option("EQUILIBRATION", "equilibration_interval"):
            self.equilibration_interval.value = equilibration.getint(
                "equilibration_interval", fallback=5)

    def _set_sequence_section_options(self, config):
        sequence = config["SEQUENCE"]
        if config.has_option("SEQUENCE", "request_rate_increment"):
            try:
                self.request_rate_increment.value = sequence.getfloat(
                    "request_rate_increment", fallback=None)
            except ValueError:
                # leave as the default
                pass
        if config.has_option("SEQUENCE", "request_rate_max"):
            try:
                self.request_rate_max.value = sequence.getfloat(
                    "request_rate_max", fallback=None)
            except ValueError:
                # leave as the default
                pass
        if config.has_option("SEQUENCE", "vehicle_count_increment"):
            try:
                self.vehicle_count_increment.value = sequence.getint(
                    "vehicle_count_increment", fallback=None)
            except ValueError:
                # leave as the default
                pass
        if config.has_option("SEQUENCE", "vehicle_count_max"):
            try:
                self.vehicle_count_max.value = sequence.getint(
                    "vehicle_count_max", fallback=None)
            except ValueError:
                # leave as the default
                pass

    def _set_impulses_section_options(self, config):
        impulses = config["IMPULSES"]
        if config.has_option("IMPULSES", "impulse_list"):
            self.impulse_list.value = impulses.get("impulse_list")
            if self.impulse_list.value:
                self.impulse_list.value = eval(self.impulse_list.value)

    def _override_options_from_command_line(self, args):
        """
        Override configuration options with command line settings
        """
        args_dict = vars(args)
        for key, val in args_dict.items():
            option = getattr(self, key)
            if (isinstance(option, ConfigItem)
                    and option.action != "store_true" and val is not None):
                # better to do this by selecting on action=store_true
                option.value = val
            elif (isinstance(option, ConfigItem)
                  and option.action == "store_true" and val is True):
                option.value = val

    def _validate_options(self):
        """
        For options that have validation constraints, impose them
        For options that are supposed to be enum values, fix them
        """
        if not isinstance(self.equilibration.value, atom.Equilibration):
            for eq_option in list(atom.Equilibration):
                if self.equilibration.value.lower()[0] == eq_option.name.lower(
                )[0]:
                    self.equilibration.value = eq_option
                    break
            if self.equilibration.value not in list(atom.Equilibration):
                logging.error(
                    "equilibration must start with n[one] or p[rice]")
        if self.animation_style.value:
            for animation_style in list(rh_animation.Animation):
                if self.animation_style.value.lower(
                )[0:2] == animation_style.value.lower()[0:2]:
                    self.animation_style.value = animation_style
                    break
            if self.animation_style.value not in list(rh_animation.Animation):
                logging.error(
                    "animation_style must start with m, s, a, or n"
                    " and the first two letters must match the allowed values."
                )
            if (self.animation_style.value
                    not in (rh_animation.Animation.MAP,
                            rh_animation.Animation.ALL)):
                # Interpolation is relevant only if the map is displayed
                self.interpolate.value = 0
            if self.animation_output_file.value:
                if not (self.animation_output_file.value.endswith("mp4")
                        or self.animation_output_file.value.endswith(".gif")):
                    self.animation_output_file.value = None
        else:
            self.animation_style.value = rh_animation.Animation.NONE
        if self.trip_inhomogeneity.value:
            # Default 0, must be between 0 and 1
            if (self.trip_inhomogeneity.value < 0.0
                    or self.trip_inhomogeneity.value > 1.0):
                self.trip_inhomogeneity.value = max(
                    min(self.trip_inhomogeneity.value, 1.0), 0.0)
                logging.warn("trip_inhomogeneity must be between 0.0 and 1.0: "
                             f"reset to {self.trip_inhomogeneity.value}")
        city_size = 2 * int(self.city_size.value / 2)
        if city_size != self.city_size.value:
            logging.warning(f"City size must be an even integer"
                            f": reset to {city_size}")
            self.city_size.value = city_size

    def _write_config_file(self):
        """
        Write out a configuration file, with name ...
        """
        # Back up existing config file
        i = 0
        while True:
            config_file_backup = (f"./{self.config_file_dir}/"
                                  f"{self.config_file_root}_{i}.config_backup")
            if not os.path.isfile(config_file_backup):
                break
            else:
                i += 1
        if os.path.isfile(self.config_file):
            os.rename(self.config_file, config_file_backup)

        # Write out a new one
        updater = ConfigUpdater(allow_no_value=True)
        updater.read_string("[DEFAULT]\n")
        updater["DEFAULT"].add_after.space().section("ANIMATION").space()
        updater["ANIMATION"].add_after.space().section("EQUILIBRATION").space()
        updater["EQUILIBRATION"].add_after.space().section("SEQUENCE").space()
        updater["SEQUENCE"].add_after.space().section("IMPULSES").space()
        comment_line = "# " + "-" * 76 + "\n"
        config_item_list = [
            getattr(self, attr) for attr in dir(self)
            if isinstance(getattr(self, attr), ConfigItem)
        ]
        config_item_list.sort(key=lambda x: x.weight)
        for config_item in config_item_list:
            if config_item.name == "fix_config_file":
                # don't write out the fc option
                continue
            # Rename legacy names
            if (config_item.name == "animation"
                    and config_item.config_section == "DEFAULT"):
                config_item.name = "animate"
            if (config_item.name == "equilibration"
                    and config_item.config_section == "DEFAULT"):
                config_item.name = "equilibrate"
            if (config_item.name == "sequence"
                    and config_item.config_section == "DEFAULT"):
                config_item.name = "run_sequence"
            if (config_item.name == "animate"
                    and config_item.config_section == "ANIMATION"):
                config_item.name = "animation_style"
            if (config_item.name == "equilibrate"
                    and config_item.config_section == "EQUILIBRATION"):
                config_item.name = "equilibration"
            if isinstance(config_item.value, Enum):
                config_item.value = config_item.value.value
            if config_item.value is None:
                if config_item.action == "store_true":
                    config_item.value = "False"
                elif config_item.type == str:
                    config_item.value = ""
                    pass
                else:
                    config_item.value = ""
            description = comment_line
            for line in config_item.description:
                description += "# " + line + "\n"
            description += comment_line
            if config_item.config_section in updater:
                if config_item.name in updater[config_item.config_section]:
                    updater[config_item.config_section][
                        config_item.name] = config_item.value
                    updater[config_item.config_section][
                        config_item.name].add_before.space().comment(
                            description).space()
                else:
                    updater[config_item.config_section][
                        config_item.name] = config_item.value
                    updater[config_item.config_section][
                        config_item.name].add_before.comment(
                            description).space()
                    updater[config_item.config_section][
                        config_item.name].add_after.space()
        updater.write(open(self.config_file, 'w'))

    def _parser(self):
        """
        Define, read and parse command-line arguments.
        """
        # Usage text
        parser = argparse.ArgumentParser(
            description="Simulate ride-hail vehicles and trips.",
            usage="%(prog)s config-file [options]",
            fromfile_prefix_chars='@')
        # Config file (no flag hyphen)

        # [DEFAULT]
        for attr in dir(self):
            config_item = getattr(self, attr)
            if isinstance(config_item, ConfigItem):
                if config_item.help is not None:
                    help_text = config_item.help
                else:
                    # help_text = ' '.join(config_item.description)
                    help_text = "HELP"
                if config_item.metavar is not None:
                    metavar = config_item.metavar
                else:
                    metavar = config_item.name

                # For all except the config file, do not specify a default.
                # The default is already set in the ConfigItem and if set here,
                # it overrides the value from the config file.
                if config_item.name == "config_file":
                    parser.add_argument(config_item.name,
                                        metavar=metavar,
                                        nargs="?",
                                        action=config_item.action,
                                        type=config_item.type,
                                        default=config_item.default,
                                        help=help_text)
                elif config_item.action == "store":
                    parser.add_argument(f"-{config_item.short_form}",
                                        f"--{config_item.name}",
                                        metavar=metavar,
                                        action=config_item.action,
                                        type=config_item.type,
                                        help=help_text)
                elif config_item.action == "store_true":
                    # Does not need a metavar
                    parser.add_argument(f"-{config_item.short_form}",
                                        f"--{config_item.name}",
                                        action=config_item.action,
                                        help=help_text)

        return parser


class WritableConfig():
    def __init__(self, config):
        self.title = config.title.value
        self.start_time = config.start_time
        self.city_size = config.city_size.value
        self.base_demand = config.base_demand.value
        self.vehicle_count = config.vehicle_count.value
        self.trip_inhomogeneity = config.trip_inhomogeneity.value
        self.trip_inhomogeneous_destinations = (
            config.trip_inhomogeneous_destinations.value)
        self.min_trip_distance = config.min_trip_distance.value
        self.max_trip_distance = config.max_trip_distance.value
        self.time_blocks = config.time_blocks.value
        self.results_window = config.results_window.value
        self.random_number_seed = config.random_number_seed.value
        self.idle_vehicles_moving = config.idle_vehicles_moving.value
        if config.equilibration.value:
            equilibration = {}
            equilibration["equilibration"] = config.equilibration.value.name
            equilibration["price"] = config.price.value
            equilibration[
                "platform_commission"] = config.platform_commission.value
            equilibration["reserved_wage"] = config.reserved_wage.value
            equilibration["demand_elasticity"] = config.demand_elasticity.value
            equilibration[
                "equilibration_interval"] = config.equilibration_interval.value
            self.equilibration = equilibration
