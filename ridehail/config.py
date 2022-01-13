import argparse
import configparser
import logging
import os
import sys
from configupdater import ConfigUpdater
from datetime import datetime
from ridehail import animation as rh_animation, atom


class ConfigItem():
    """
    Represents a single configuration parameter, which may be specified through
    a config file, a command-line argument (some) or as a default
    """
    name = None
    description = []
    default = None
    value = None
    arg_name = None
    short_form = None
    config_section = None

    def __init__(self,
                 name=None,
                 description=None,
                 default=None,
                 arg_name=None,
                 short_form=None,
                 config_section=None):
        self.name = name
        self.description = description
        self.default = default
        self.arg_name = arg_name
        self.value = default
        self.short_form = short_form
        self.config_section = config_section


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
    title = ConfigItem(name="title",
                       default=None,
                       arg_name="title",
                       short_form="t",
                       config_section="DEFAULT")
    title.description = (
        "Title (string, default None",
        "The title is recorded in the output json file and displayed",
        "at the top of charts in any animations.")
    city_size = ConfigItem(name="city_size",
                           default=8,
                           arg_name="city_size",
                           short_form="cs",
                           config_section="DEFAULT")
    city_size.description = (
        "City Size (even integer, default 8)",
        "The grid is a square, with this number of blocks on each side.",
        "A block is often a minute, or a kilometer.",
    )
    vehicle_count = ConfigItem(name="vehicle_count",
                               default=0,
                               arg_name="vehicle_count",
                               short_form="vc",
                               config_section="DEFAULT")
    vehicle_count.description = (
        "Vehicle Count (integer, default 0).",
        "The number of vehicles in the simulation. For simulations with ",
        "equilibration or sequences, this is the number of vehicles at ",
        " the beginning of the simulation.",
    )
    base_demand = ConfigItem(name="base_demand",
                             default=0,
                             arg_name="base_demand",
                             short_form="bd",
                             config_section="DEFAULT")
    base_demand.description = (
        "Base Demand (float, default 0.0).",
        "For simulations without equilibration, the demand for trips.",
        "Alternatively, the request rate (requests per block of time).",
        "For simulations with equilibration, the request rate is given by ",
        "", "      demand = base_demand * price ** (-elasticity)")
    trip_distribution = ConfigItem(name="trip_distribution",
                                   default=None,
                                   arg_name="trip_distribution",
                                   short_form="td",
                                   config_section="DEFAULT")
    trip_distribution.description = (
        "DEPRECATION NOTICE: The trip_distribution option is deprecated",
        "This option is now ignored.",
        "To configure trip distribution, use the trip_inhomogeneity option.",
    )
    trip_distribution.value = None
    trip_inhomogeneity = ConfigItem(name="trip_inhomogeneity",
                                    default=0.0,
                                    arg_name="trip_inhomogeneity",
                                    short_form="ti",
                                    config_section="DEFAULT")
    trip_inhomogeneity.description = (
        "Trip Inhomogeneity (float in the range [0.0, 1.0], default 0.0).",
        "Trips originate in one of two zones: central zone or outer zone.",
        "The inner zone has sides C/2, and is centred on (C/2, C/2); ",
        "the outer zone is the remaining 3/4 of the area.",
        "At 0: the distribution of trip origins is homogenous.",
        "At 1: all trip origins are inside the central zone.",
    )
    min_trip_distance = ConfigItem(name="min_trip_distance",
                                   default=0,
                                   arg_name="min_trip_distance",
                                   short_form="tmin",
                                   config_section="DEFAULT")
    min_trip_distance.description = (
        "Minimum trip distance (integer, default 0).",
        "A trip must be at least this long.")
    max_trip_distance = ConfigItem(name="max_trip_distance",
                                   default=city_size.default,
                                   arg_name="max_trip_distance",
                                   short_form="tmax",
                                   config_section="DEFAULT")
    max_trip_distance.description = (
        "Maximum trip distance (integer, default <city_size>).",
        "A trip must be at most this long.")
    time_blocks = ConfigItem(name="time_blocks",
                             default=201,
                             arg_name="time_blocks",
                             short_form="b",
                             config_section="DEFAULT")
    time_blocks.value = time_blocks.default
    time_blocks.description = (
        "Time blocks (integer, default 201)",
        "The number of time periods (blocks) to run the simulation.",
        "Each period corresponds to a vehicle travelling one block",
    )
    results_window = ConfigItem(name="results_window",
                                default=int(time_blocks.value * 0.25),
                                arg_name="results_window",
                                short_form="rw",
                                config_section="DEFAULT")
    results_window.value = results_window.default
    results_window.description = (
        "Results Window (integer, default = 0.25 * time_blocks)",
        "At the end of the run, compute the final results by averaging over",
        "results_window blocks. Typically bigger than trailing_window",
    )
    log_file = ConfigItem(name="log_file",
                          default=None,
                          arg_name="log_file",
                          short_form="l",
                          config_section="DEFAULT")
    log_file.value = log_file.default
    log_file.description = (
        "Log file (string, default None)",
        "The file name for logging messages.",
        "By default, log messages are written to standard output only.",
    )
    verbosity = ConfigItem(name="verbosity",
                           default=0,
                           arg_name="verbosity",
                           short_form="v",
                           config_section="DEFAULT")
    verbosity.value = verbosity.default
    verbosity.description = (
        "Verbosity (integer, default 0)",
        "If 0, log warning, and error messages",
        "If 1, log info, warning, and error messages",
        "If 2, log debug, information, warning, and error messages",
    )
    animate = ConfigItem(name="animate",
                         default=False,
                         arg_name="animate",
                         short_form="a",
                         config_section="DEFAULT")
    animate.value = animate.default
    animate.description = (
        "Animate (binary, default False)",
        "If True, display or save animation.",
        "Animation configuration is in the [ANIMATION] section.",
    )
    equilibrate = ConfigItem(name="equilibrate",
                             default=False,
                             arg_name="equilibrate",
                             short_form="eq",
                             config_section="DEFAULT")
    equilibrate.value = equilibrate.default
    equilibrate.description = (
        "Equilibrate (binary, default False)",
        "If True, equilibrate the supply of vehicles and demand for trips.",
        "Configure equilibration in the [EQUILIBRATION] section.",
    )
    run_sequence = ConfigItem(name="run_sequence",
                              default=False,
                              arg_name="run_sequence",
                              short_form="seq",
                              config_section="DEFAULT")
    run_sequence.value = run_sequence.default
    run_sequence.description = (
        "Run sequence (boolean, default False)",
        "Set to True to run a sequence of simulations with different vehicle ",
        "counts or request rates.",
        "If True, configure the sequence in the [SEQUENCE] section.",
    )
    idle_vehicles_moving = ConfigItem(name="idle_vehicles_moving",
                                      default=True,
                                      arg_name="idle_vehicles_moving",
                                      short_form="ivm",
                                      config_section="DEFAULT")
    idle_vehicles_moving.value = idle_vehicles_moving.default
    idle_vehicles_moving.description = (
        "Available vehicles moving (boolean, default True)",
        "If True, vehicles in the 'available' state move around",
        "If False, they stay where they are.",
    )
    fix_config_file = ConfigItem(name="fix_config_file",
                                 default=False,
                                 arg_name="fix_config_file",
                                 short_form="fc",
                                 config_section="DEFAULT")
    fix_config_file.value = fix_config_file.default
    fix_config_file.description = (
        "Fix the configuration file (boolean, default False)",
        "If True, write a copy of the configuration file ",
        "with updated descriptions to the console.",
        "Pipe it to another file if you want to use it.",
    )

    # [ANIMATION]
    animation_style = ConfigItem(name="animation_style",
                                 default='none',
                                 arg_name="animation_style",
                                 short_form="as",
                                 config_section="ANIMATION")
    animation_style.value = animation_style.default
    animation_style.description = (
        "Animation Style (string, default 'none'",
        "Select which charts and / or maps to display.",
        "Possible values include...",
        "- none (no charts)",
        "- map",
        "- stats",
        "- all (displays map + stats)",
        "- bar",
        "- sequence",
    )
    animate_update_period = ConfigItem(name="animate_update_period",
                                       default=1,
                                       arg_name="animate_update_period",
                                       short_form="ap",
                                       config_section="ANIMATION")
    animate_update_period.value = animate_update_period.default
    animate_update_period.description = (
        "Animate update period (integer, default 1)",
        "Update charts every N periods",
    )
    interpolate = ConfigItem(name="interpolate",
                             default=1,
                             arg_name="interpolate",
                             short_form="ai",
                             config_section="ANIMATION")
    interpolate.value = interpolate.default
    interpolate.description = (
        "Interpolate (integer, default 1)",
        "For the map display (only) add this many interpolated points between",
        "time periods so the car movements are smoother.",
    )
    animation_output_file = ConfigItem(name="animation_output_file",
                                       default=None,
                                       arg_name="animation_output_file",
                                       short_form="aof",
                                       config_section="ANIMATION")
    animation_output_file.value = animation_output_file.default
    animation_output_file.description = (
        "Animation output (string, default None)",
        "Supply a file name in which to save the animations. ",
        "If none is supplied, display animations on the screen only.",
    )
    imagemagick_dir = ConfigItem(name="imagemagick_dir",
                                 default=None,
                                 arg_name="imagemagick_dir",
                                 short_form="aid",
                                 config_section="ANIMATION")
    imagemagick_dir.value = imagemagick_dir.default
    imagemagick_dir.description = (
        "ImageMagick_Dir (string)",
        "If you choose an MP4 or GIF output (output parameter) then you need ",
        "ImageMagick. This is the directory in which it is installed,",
        "for example:",
        "",
        "  imagemagick_dir = /Program Files/ImageMagick-7.0.9-Q16 ",
    )
    smoothing_window = ConfigItem(name="smoothing_window",
                                  default=None,
                                  arg_name="smoothing_window",
                                  short_form="asw",
                                  config_section="ANIMATION")
    smoothing_window.value = smoothing_window.default
    smoothing_window.description = (
        "Smoothing Window (integer, default = 20)",
        "Rolling window in which to compute trailing averages ",
        "(wait times, busy fraction etc) used in graphs and in calculations.",
    )

    # [EQUILIBRATION]
    equilibration = ConfigItem(name="equilibration",
                               default=atom.Equilibration.NONE,
                               arg_name="equilibration",
                               short_form="eq",
                               config_section="EQUILIBRATION")
    equilibration.value = equilibration.default
    equilibration.description = (
        "Equilibration method (String, converted to enumeration).",
        "Valid values are 'None' or 'Price'",
    )
    price = ConfigItem(name="price",
                       default=1.0,
                       arg_name="price",
                       short_form="ep",
                       config_section="EQUILIBRATION")
    price.value = price.default
    price.description = (
        "Price (float, default 1.0)",
        "Price is a part of the equilibration path",
    )
    platform_commission = ConfigItem(name="platform_commission",
                                     default=0.0,
                                     arg_name="platform_commission",
                                     short_form="pc",
                                     config_section="EQUILIBRATION")
    platform_commission.value = platform_commission.default
    platform_commission.description = (
        "Platform commission F (float, default 0.0)",
        "The vehicle utility per block is U = P.B.(1 - F) - C_d, ",
        "where F = platform commission.",
        "F > 0 amounts to the platform taking a commission, ",
        "F < 0 is the platform subsidizing vehicles.",
    )
    demand_elasticity = ConfigItem(name="demand_elasticity",
                                   default=0.0,
                                   arg_name="demand_elasticity",
                                   short_form="de",
                                   config_section="EQUILIBRATION")
    demand_elasticity.value = demand_elasticity.default
    demand_elasticity.description = (
        "Demand elasticity (float, default 1.0)",
        "The demand (request rate) = k * p ^ (-r) ",
        "where r is the demand elasticity and k is the base demand",
    )
    equilibration_interval = ConfigItem(name="equilibration_interval",
                                        default=1,
                                        arg_name="equilibration_interval",
                                        short_form="eqi",
                                        config_section="EQUILIBRATION")
    equilibration_interval.value = equilibration_interval.default
    equilibration_interval.description = (
        "Equilibration interval (integer, default 1)",
        "The number of blocks at which equilibration steps are chosen",
    )
    reserved_wage = ConfigItem(name="reserved_wage",
                               default=0.5,
                               arg_name="reserved_wage",
                               short_form="rw",
                               config_section="EQUILIBRATION")
    reserved_wage.value = reserved_wage.default
    reserved_wage.description = (
        "Reserved wage (float, default 0.5)",
        "Vehicle utility per block is U = P.B(1 - F) - C_d, ",
        "where C_d = reserved wage",
    )
    reserved_wage_increment = ConfigItem(name="reserved_wage_increment",
                                         default=None,
                                         arg_name="reserved_wage_increment",
                                         short_form="rwi",
                                         config_section="EQUILIBRATION")
    reserved_wage_increment.value = reserved_wage_increment.default
    reserved_wage_increment.description = ("NOT IN USE", )
    reserved_wage_max = ConfigItem(name="reserved_wage_max",
                                   default=None,
                                   arg_name="reserved_wage_max",
                                   short_form="rwm",
                                   config_section="EQUILIBRATION")
    reserved_wage_max.value = reserved_wage_max.default
    reserved_wage_max.description = ("NOT IN USE", )
    wait_cost = ConfigItem(name="wait_cost",
                           default=None,
                           arg_name="wait_cost",
                           short_form="wc",
                           config_section="EQUILIBRATION")
    wait_cost.value = wait_cost.default
    wait_cost.description = ("NOT IN USE", )
    wait_cost_increment = ConfigItem(name="wait_cost_increment",
                                     default=None,
                                     arg_name="wait_cost_increment",
                                     short_form="wci",
                                     config_section="EQUILIBRATION")
    wait_cost_increment.value = wait_cost_increment.default
    wait_cost_increment.description = ("NOT IN USE", )
    wait_cost_max = ConfigItem(name="wait_cost_max",
                               default=None,
                               arg_name="wait_cost_max",
                               short_form="wcm",
                               config_section="EQUILIBRATION")
    wait_cost_max.value = wait_cost_max.default
    wait_cost_max.description = ("NOT IN USE", )

    # [SEQUENCE]
    price_repeat = ConfigItem(name="price_repeat",
                              default=None,
                              arg_name="price_repeat",
                              short_form="pr",
                              config_section="SEQUENCE")
    price_repeat.value = price_repeat.default
    price_repeat.description = ("NOT IN USE", )
    price_increment = ConfigItem(name="price_increment",
                                 default=None,
                                 arg_name="price_increment",
                                 short_form="pi",
                                 config_section="SEQUENCE")
    price_increment.value = price_increment.default
    price_increment.description = ("NOT IN USE", )
    price_max = ConfigItem(name="price_max",
                           default=None,
                           arg_name="price_max",
                           short_form="pm",
                           config_section="SEQUENCE")
    price_max.value = price_max.default
    price_max.description = ("NOT IN USE", )
    request_rate_increment = ConfigItem(name="request_rate_increment",
                                        default=None,
                                        arg_name="request_rate_increment",
                                        short_form="rri",
                                        config_section="SEQUENCE")
    request_rate_increment.value = request_rate_increment.default
    request_rate_increment.description = (
        "Request rate increment (integer, default None)",
        "The increment in a sequence of request rates",
        "The starting value is 'base_demand' in the DEFAULT section",
    )
    request_rate_max = ConfigItem(name="request_rate_max",
                                  default=None,
                                  arg_name="request_rate_max",
                                  short_form="rrm",
                                  config_section="SEQUENCE")
    request_rate_max.value = request_rate_max.default
    request_rate_max.description = (
        "Request rate max (integer, default None)",
        "The maximum value in a sequence of request rates",
        "The starting value is 'base_demand' in the DEFAULT section",
    )
    vehicle_count_increment = ConfigItem(name="vehicle_count_increment",
                                         default=None,
                                         arg_name="vehicle_count_increment",
                                         short_form="vci",
                                         config_section="SEQUENCE")
    vehicle_count_increment.value = vehicle_count_increment.default
    vehicle_count_increment.description = (
        "Vehicle count increment (integer, default None)",
        "The increment in a sequence of vehicle counts",
    )
    vehicle_count_max = ConfigItem(name="vehicle_count_max",
                                   default=None,
                                   arg_name="vehicle_count_max",
                                   short_form="vcm",
                                   config_section="SEQUENCE")
    vehicle_count_max.value = vehicle_count_max.default
    vehicle_count_max.description = (
        "Vehicle Count Max (integer, default None)",
        "The maximum value in a sequence of vehicle counts")
    vehicle_cost_increment = ConfigItem(name="vehicle_cost_increment",
                                        default=None,
                                        arg_name="vehicle_cost_increment",
                                        short_form="vcti",
                                        config_section="SEQUENCE")
    vehicle_cost_increment.value = vehicle_cost_increment.default
    vehicle_cost_increment.description = ("NOT IN USE", )
    vehicle_cost_max = ConfigItem(name="vehicle_cost_max",
                                  default=None,
                                  arg_name="vehicle_cost_max",
                                  short_form="vctm",
                                  config_section="SEQUENCE")
    vehicle_cost_max.value = vehicle_cost_max.default
    vehicle_cost_max.description = ("NOT IN USE", )

    # [IMPULSES]
    impulses = ConfigItem(name="impulses",
                          default=None,
                          arg_name="impulses",
                          short_form="i",
                          config_section="IMPULSES")
    impulses.value = impulses.default
    impulses.description = ("NOT IN USE", )
    impulse_list = ConfigItem(name="impulse_list",
                              default=None,
                              arg_name="impulse_list",
                              short_form="il",
                              config_section="IMPULSES")
    impulse_list.value = impulse_list.default
    impulse_list.description = (
        "Sudden changes during the simulation",
        "Write as a list of dictionaries. For example...",
        "impulse_list = [{'block': 480, 'base_demand': 20.0},",
        "   {'block': 960, 'base_demand': 18.0},",
        "   {'block': 1080, 'base_demand': 7},",
        "   ]",
    )

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
        if self.verbosity.value == 0:
            loglevel = 30  # logging.WARNING  # 30
        elif self.verbosity.value == 1:
            loglevel = 20  # logging.INFO  # 20
        elif self.verbosity.value == 2:
            loglevel = 10  # logging.DEBUG  # 10
        else:
            loglevel = 20  # logging.INFO  # 20
        if sys.version_info[0] >= 3 and sys.version_info[1] >= 8:
            # Python 3.8+required for "force" reconfigure of logging
            if self.log_file.value:
                logging.basicConfig(
                    filename=self.log_file.value,
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
        if self.fix_config_file.value:
            print("Writing config file")
            self._write_config_file()

    def _log_config_settings(self):
        for attr in dir(self):
            attr_name = attr.__str__()
            if not attr_name.startswith("_"):
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
        if self.animate.value and config.has_section("ANIMATION"):
            self._set_animation_section_options(config)
        if self.equilibrate.value and config.has_section("EQUILIBRATION"):
            self._set_equilibration_section_options(config)
        if self.run_sequence.value and config.has_section("SEQUENCE"):
            logging.info("Setting the SEQUENCE section")
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
        if config.has_option("DEFAULT", "min_trip_distance"):
            self.min_trip_distance.value = default.getint("min_trip_distance")
            # min_trip_distance must be even for now
            self.min_trip_distance.value = 2 * int(
                self.min_trip_distance.value / 2)
        if config.has_option("DEFAULT", "max_trip_distance"):
            self.max_trip_distance.value = default.getint("max_trip_distance")
            # max_trip_distance must be even
            self.max_trip_distance.value = 2 * int(
                self.max_trip_distance.value / 2)
        else:
            self.max_trip_distance.value = self.city_size.value
        if config.has_option("DEFAULT", "time_blocks"):
            self.time_blocks.value = default.getint("time_blocks")
        if config.has_option("DEFAULT", "results_window"):
            self.results_window.value = default.getint("results_window")
        if config.has_option("DEFAULT", "idle_vehicles_moving"):
            self.idle_vehicles_moving.value = default.getboolean(
                "idle_vehicles_moving")
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
            self.animation_style.value = animation.get("animation_style")
        if config.has_option("ANIMATION", "animate_update_period"):
            self.animate_update_period.value = (
                animation.getint("animate_update_period"))
        if config.has_option("ANIMATION", "interpolate"):
            self.interpolate.value = animation.getint("interpolate")
        if config.has_option("ANIMATION", "animation_output_file"):
            self.animation_output_file.value = animation.get(
                "animation_output_file")
            if not (self.animation_output_file.value.endswith("mp4")
                    or self.animation_output_file.value.endswith(".gif")):
                self.animation_output_file.value = None
        if config.has_option("ANIMATION", "imagemagick_dir"):
            self.imagemagick_dir.value = animation.get("imagemagick_dir")
        if config.has_option("ANIMATION", "smoothing_window"):
            self.smoothing_window.value = animation.getint("smoothing_window")

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
        if config.has_option("SEQUENCE", "price_repeat"):
            self.price_repeat.value = sequence.getint("price_repeat",
                                                      fallback=1)
        if config.has_option("SEQUENCE", "price_increment"):
            self.price_increment.value = sequence.getfloat("price_increment",
                                                           fallback=0.1)
        if config.has_option("SEQUENCE", "price_max"):
            self.price_max.value = sequence.getfloat("price_max", fallback=2)
        if config.has_option("SEQUENCE", "request_rate_increment"):
            self.request_rate_increment.value = sequence.getfloat(
                "request_rate_increment", fallback=None)
        if config.has_option("SEQUENCE", "request_rate_max"):
            self.request_rate_max.value = sequence.getfloat("request_rate_max",
                                                            fallback=None)
        if config.has_option("SEQUENCE", "vehicle_count_increment"):
            self.vehicle_count_increment.value = sequence.getint(
                "vehicle_count_increment", fallback=None)
        if config.has_option("SEQUENCE", "vehicle_count_max"):
            self.vehicle_count_max.value = sequence.getint("vehicle_count_max",
                                                           fallback=None)
        if config.has_option("SEQUENCE", "vehicle_cost_max"):
            self.vehicle_cost_max.value = sequence.getfloat("vehicle_cost_max",
                                                            fallback=None)
        if config.has_option("SEQUENCE", "vehicle_cost_increment"):
            self.vehicle_cost_increment.value = sequence.getfloat(
                "vehicle_cost_increment", fallback=None)

    def _set_impulses_section_options(self, config):
        impulses = config["IMPULSES"]
        if config.has_option("IMPULSES", "impulse_list"):
            self.impulse_list.value = impulses.get("impulse_list")
            self.impulse_list.value = eval(self.impulse_list.value)

    def _override_options_from_command_line(self, args):
        """
        Override configuration options with command line settings
        """
        args_dict = vars(args)
        for key, val in args_dict.items():
            if hasattr(self, key) and key != "config_file" and val is not None:
                option = getattr(self, key)
                if isinstance(option, ConfigItem):
                    option.value = val
                else:
                    print(f"Option {key} is of type {type(option)}")

    def _validate_options(self):
        """
        For options that have validation constraints, impose them
        For options that are supposed to be enum values, fix them
        """
        if self.equilibration.value:
            for eq_option in list(atom.Equilibration):
                if self.equilibration.value.name.lower(
                )[0] == eq_option.name.lower()[0]:
                    self.equilibration.value = eq_option
                    break
            if self.equilibration.value not in list(atom.Equilibration):
                logging.error("equilibration must start with s, d, f, or n")
        else:
            self.equilibration.value = atom.Equilibration.NONE
        if self.animation_style.value:
            for animate_option in list(rh_animation.Animation):
                if self.animation_style.value.lower(
                )[0:2] == animate_option.value.lower()[0:2]:
                    self.animation_style.value = animate_option
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
        config_file_out = "testfix.config"
        logging.info(f"write out config file {config_file_out}")
        updater = ConfigUpdater(allow_no_value=True)
        # skeleton = """[DEFAULT]
        # [ANIMATION]
        # [EQUILIBRATION]
        # [SEQUENCE]
        # [IMPULSES]
        # """
        # updater.read_string(skeleton)
        updater.read(self.config_file)
        if "animate" in updater["ANIMATION"]:
            updater["ANIMATION"]["animate"].key = "animation_style"
        if "animation" in updater["DEFAULT"]:
            updater["DEFAULT"]["animation"].key = "animate"
        if "equilibration" in updater["DEFAULT"]:
            updater["DEFAULT"]["equilibration"].key = "equilibrate"
        if "sequence" in updater["DEFAULT"]:
            updater["DEFAULT"]["sequence"].key = "run_sequence"
        comment_line = "# " + "=" * 76 + "\n"
        for attr in dir(self):
            attr_name = attr.__str__()
            if not (attr_name.startswith("_")
                    or attr_name == "fix_config_file"):
                config_item = getattr(self, attr)
                if isinstance(config_item, ConfigItem):
                    if config_item.config_section in updater:
                        if config_item.name in updater[
                                config_item.config_section]:
                            updater[config_item.config_section][
                                config_item.name] = config_item.value
                            description = comment_line
                            for line in config_item.description:
                                description += "# " + line + "\n"
                            description += comment_line
                            updater[config_item.config_section][
                                config_item.name].add_before.space().comment(
                                    description).space()
        # updater.write(open(config_file_out, 'w'))
        print(updater)
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
                            help="number of vehicles")
        parser.add_argument(
            "-bd",
            "--base_demand",
            metavar="base_demand",
            action="store",
            type=float,
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
        parser.add_argument(
            "-fc",
            "--fix_config_file",
            dest="fix_config_file",
            action="store_true",
            help="""Fix the supplied configuration file and quit.
            If the named config file does not exist, write one out.""")
        parser.add_argument("-l",
                            "--log_file",
                            metavar="log_file",
                            action="store",
                            type=str,
                            default=None,
                            help=("Logfile name. By default, log messages "
                                  "are written to the screen only"))
        parser.add_argument("-b",
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
            "-as",
            "--animation_style",
            metavar="animation_style",
            action="store",
            type=str,
            default=None,
            help="""animation_style 'all', 'stats', 'bar', 'map', 'none',
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
        self.title = config.title.value
        self.start_time = config.start_time
        self.city_size = config.city_size.value
        self.base_demand = config.base_demand.value
        self.vehicle_count = config.vehicle_count.value
        self.trip_inhomogeneity = config.trip_inhomogeneity.value
        self.min_trip_distance = config.min_trip_distance.value
        self.max_trip_distance = config.max_trip_distance.value
        self.time_blocks = config.time_blocks.value
        self.results_window = config.results_window.value
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
