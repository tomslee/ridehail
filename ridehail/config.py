import argparse
import configparser
import logging
from os import path, rename
import sys
from enum import Enum
from datetime import datetime
from ridehail import __version__
from ridehail.atom import Animation, Equilibration, Measure, DispatchMethod

# Initial logging config, which may be overriden by config file or
# command-line setting later
logging.basicConfig(
    level=logging.INFO,
    force=True,
    format="[%(filename)s:%(lineno)d] %(levelname)s - %(message)s",
)


class ConfigValidationError(Exception):
    """Exception raised when configuration validation fails"""

    def __init__(self, parameter_name, message):
        self.parameter_name = parameter_name
        self.message = message
        super().__init__(f"Config validation error for '{parameter_name}': {message}")


class ConfigItem:
    """
    Represents a single configuration parameter, which may be specified through
    a config file, a command-line argument (some) or as a default
    """

    def __init__(
        self,
        name=None,
        type=None,
        default=None,
        action=None,
        description=[],
        help=None,
        short_form=None,
        metavar=None,
        config_section=None,
        active=True,
        weight=999,
        min_value=None,
        max_value=None,
        choices=None,
        validator=None,
        must_be_even=False,
        required_if=None,
    ):
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
        self.active = active
        self.weight = weight

        # Validation parameters
        self.min_value = min_value
        self.max_value = max_value
        self.choices = choices
        self.validator = validator  # Custom validation function
        self.must_be_even = must_be_even
        self.required_if = (
            required_if  # Function that returns True if this param is required
        )

    def __lt__(self, other):
        # Use the "weight" attribute to decide the order
        # in which the items appear in each section of
        # the config file
        return self.weight < other.weight

    def validate_value(self, value, config_context=None):
        """
        Validate a value for this configuration parameter

        Args:
            value: The value to validate
            config_context: The full config object for dependency validation

        Returns:
            tuple: (is_valid, validated_value, error_message)
        """
        if value is None:
            if self.required_if and config_context and self.required_if(config_context):
                return False, None, f"Parameter '{self.name}' is required"
            return True, None, None

        # Type validation
        if self.type and not isinstance(value, self.type):
            try:
                if self.type is bool and isinstance(value, str):
                    # Handle string boolean conversion
                    value = value.lower() in ("true", "1", "yes", "on")
                else:
                    value = self.type(value)
            except (ValueError, TypeError):
                return False, None, f"Cannot convert '{value}' to {self.type.__name__}"

        # Range validation for numeric types
        if (
            self.min_value is not None
            and hasattr(value, "__lt__")
            and value < self.min_value
        ):
            return False, None, f"Value {value} is less than minimum {self.min_value}"

        if (
            self.max_value is not None
            and hasattr(value, "__gt__")
            and value > self.max_value
        ):
            return (
                False,
                None,
                f"Value {value} is greater than maximum {self.max_value}",
            )

        # Choice validation
        if self.choices is not None and value not in self.choices:
            return (
                False,
                None,
                f"Value '{value}' not in allowed choices: {self.choices}",
            )

        # Even number validation
        if self.must_be_even and isinstance(value, int) and value % 2 != 0:
            # Auto-correct to nearest even number (current behavior)
            value = 2 * int(value / 2)
            logging.warning(
                f"Parameter '{self.name}' must be even, adjusted to {value}"
            )

        # Custom validator
        if self.validator:
            try:
                valid, message = self.validator(value, config_context)
                if not valid:
                    return False, None, message
            except Exception as e:
                return False, None, f"Validation function failed: {str(e)}"

        return True, value, None

    def set_value(self, value, config_context=None, strict=False):
        """
        Set and validate the value for this parameter

        Args:
            value: The value to set
            config_context: The full config object for dependency validation
            strict: If True, raise exception on validation failure

        Returns:
            bool: True if validation passed, False otherwise
        """
        is_valid, validated_value, error_message = self.validate_value(
            value, config_context
        )

        if is_valid:
            self.value = validated_value
            return True
        else:
            if strict:
                raise ConfigValidationError(self.name, error_message)
            else:
                logging.warning(
                    f"Config validation failed for '{self.name}': {error_message}, using default"
                )
                self.value = self.default
                return False


class RideHailConfig:
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
    - CITY_SCALE
    - ADVANCED_DISPATCH
    However, the config option does not use these sections:
    it just has a lot of attributes,
    """

    # Default values here

    # Arguments
    config_file = ConfigItem(
        name="config_file", type=str, default=None, action="store", config_section=None
    )
    config_file.help = "configuration file"
    config_file.description = (
        f"configuration file ({config_file.type.__name__}, "
        f"default {config_file.default})",
    )

    # [DEFAULT]
    version = ConfigItem(
        name="version",
        type=str,
        default=__version__,
        action="store",
        config_section="DEFAULT",
        weight=-10,
        active=False,  # Not user-configurable
    )
    version.help = "ridehail package version"
    version.description = (
        f"package version ({version.type.__name__}, default {version.default})",
        "The version of the ridehail package used for this simulation.",
        "This is automatically set and not user-configurable.",
    )

    title = ConfigItem(
        name="title",
        type=str,
        default=None,
        action="store",
        short_form="t",
        metavar="string",
        config_section="DEFAULT",
        weight=0,
    )
    title.help = "the display title for plots and animations"
    title.description = (
        f"plot title ({title.type.__name__}, default {title.default})",
        "The title is recorded in the output json file",
        "and is used as the plot title.",
    )
    city_size = ConfigItem(
        name="city_size",
        type=int,
        default=8,
        action="store",
        short_form="cs",
        metavar="even-integer",
        config_section="DEFAULT",
        weight=10,
        min_value=2,
        max_value=200,
        must_be_even=True,
    )
    city_size.help = """the number of blocks on each side of the city"""
    city_size.description = (
        f"city size, in blocks "
        f"(even {city_size.type.__name__}, default {city_size.default})",
        "The grid is a square, with this number of blocks on each side.",
        "A block is often a minute, or a kilometer.",
        "If use_city_scale is set to True, then this value is divded by ",
        "minutes_per_block and rounded to an even number",
    )
    vehicle_count = ConfigItem(
        name="vehicle_count",
        type=int,
        default=4,
        action="store",
        short_form="vc",
        metavar="N",
        config_section="DEFAULT",
        weight=20,
        min_value=1,
        max_value=100000,
    )
    vehicle_count.help = (
        "the number of vehicles at the start of the simulation "
        "(it's more complex when equilibrate is set)"
    )
    vehicle_count.description = (
        f"vehicle count ({vehicle_count.type.__name__}, "
        f"default {vehicle_count.default})",
        "The number of vehicles in the simulation. For simulations with ",
        "equilibration or sequences, this is the number of vehicles at ",
        " the beginning of the simulation.",
    )
    base_demand = ConfigItem(
        name="base_demand",
        type=float,
        default=0.2,
        action="store",
        short_form="bd",
        metavar="float",
        config_section="DEFAULT",
        weight=40,
        min_value=0.0,
        max_value=10000.0,
    )
    base_demand.help = (
        "the request rate at the start of the simulation "
        "(when equilibrate or use_city_scale are set the request"
        "rate becomes the base_demand * price ^ - (elasticity)"
    )
    base_demand.description = (
        f"base demand ({base_demand.type.__name__}, default {base_demand.default})",
        "For simulations without equilibration, the demand for trips.",
        "Alternatively, the request rate (requests per block of time).",
        "For simulations with equilibration, the request rate is given by ",
        "",
        "      demand = base_demand * price ** (-elasticity)",
    )
    inhomogeneity = ConfigItem(
        name="inhomogeneity",
        type=float,
        default=0.0,
        action="store",
        short_form="ti",
        metavar="float",
        config_section="DEFAULT",
        weight=50,
        min_value=0.0,
        max_value=1.0,
    )
    inhomogeneity.help = "float, in [0.0], [1.0]"
    inhomogeneity.description = (
        f"inhomogeneity ({inhomogeneity.type.__name__} "
        f"in the range [0.0, 1.0], default {inhomogeneity.default})",
        "Trips originate in one of two zones: central zone or outer zone.",
        "The inner zone has sides C/2, and is centred on (C/2, C/2); ",
        "the outer zone is the remaining 3/4 of the area.",
        "At 0: the distribution of trip origins is homogenous.",
        "At 1: all trip origins are inside the central zone.",
    )
    inhomogeneous_destinations = ConfigItem(
        name="inhomogeneous_destinations",
        type=bool,
        default=False,
        action="store_true",
        short_form="tid",
        config_section="DEFAULT",
        weight=55,
    )
    inhomogeneous_destinations.help = (
        "if set, both origins and destinations are affected by inhomogeneity"
    )
    inhomogeneous_destinations.description = (
        "inhomogeneous destinations"
        "If not set, only trip origins are affected by trip_inohomgeneity.",
        "If set, both origins and destinations are affected.",
        "If set, mean trip length is also affected.",
    )
    min_trip_distance = ConfigItem(
        name="min_trip_distance",
        type=int,
        default=0,
        action="store",
        short_form="tmin",
        metavar="N",
        config_section="DEFAULT",
        weight=60,
        min_value=0,
        max_value=100,
        must_be_even=True,
    )
    min_trip_distance.help = "min trip distance, in blocks"
    min_trip_distance.description = (
        f"minimum trip distance ({min_trip_distance.type.__name__}, "
        f"default {min_trip_distance.default})",
        "A trip must be at least this long.",
    )

    @staticmethod
    def _validate_max_trip_distance(value, config_context):
        """Ensure max_trip_distance is greater than min_trip_distance"""
        if value is None:
            return True, None
        if config_context and hasattr(config_context, "min_trip_distance"):
            min_dist = getattr(config_context.min_trip_distance, "value", 0)
            if min_dist and value <= min_dist:
                return (
                    False,
                    f"max_trip_distance ({value}) must be greater than min_trip_distance ({min_dist})",
                )
        if config_context and hasattr(config_context, "city_size"):
            max_dist = 0.5 * getattr(config_context.city_size, "value", 1000)
            if max_dist and value > max_dist:
                return (
                    False,
                    f"max_trip_distance ({value}) must be no greater than city_size/2 ({max_dist})",
                )
        return True, None

    max_trip_distance = ConfigItem(
        name="max_trip_distance",
        type=int,
        default=None,
        action="store",
        short_form="tmax",
        metavar="N",
        config_section="DEFAULT",
        weight=70,
        min_value=1,
        max_value=200,
        must_be_even=True,
        validator=_validate_max_trip_distance,
    )
    max_trip_distance.help = "max trip distance, in blocks"
    max_trip_distance.description = (
        f"maximum trip distance ({max_trip_distance.type.__name__}, "
        f"default {max_trip_distance.default})",
        "A trip must be at most this long.",
    )

    pickup_time = ConfigItem(
        name="pickup_time",
        type=int,
        default=1,
        action="store",
        short_form="pt",
        metavar="T",
        config_section="DEFAULT",
        weight=75,
        min_value=0,
        max_value=10,
    )
    pickup_time.help = "pickup dwell time, in blocks"
    pickup_time.description = (
        f"pickup time ({pickup_time.type.__name__}, default {pickup_time.default})",
        "Number of blocks a vehicle dwells at trip origin during passenger boarding.",
        "0 = instant pickup (original behavior)",
        "1 = one block dwell time (recommended default)",
        ">1 = extended boarding time (accessibility scenarios, etc.)",
    )

    time_blocks = ConfigItem(
        name="time_blocks",
        type=int,
        default=201,
        action="store",
        short_form="b",
        metavar="B",
        config_section="DEFAULT",
        weight=80,
        min_value=0,
        max_value=100000,
    )
    time_blocks.help = "duration of the simulation, in blocks"
    time_blocks.description = (
        f"time blocks ({time_blocks.type.__name__}, default {time_blocks.default})",
        "The number of time periods (blocks) to run the simulation.",
        "Each period corresponds to a vehicle travelling one block.",
    )
    random_number_seed = ConfigItem(
        name="random_number_seed",
        type=int,
        default=None,
        action="store",
        short_form="rns",
        metavar="N",
        config_section="DEFAULT",
        weight=87,
    )
    random_number_seed.help = "set a seed for random number generation"
    random_number_seed.description = (
        f"random number seed ({random_number_seed.type.__name__}, "
        f"default {random_number_seed.default})",
        "Random numbers are used throughout the simulation. ",
        "Set the seed to an integer for reproducible simulations.",
        "If None, then each simulation will be different.",
    )
    idle_vehicles_moving = ConfigItem(
        name="idle_vehicles_moving",
        type=bool,
        default=True,
        action="store",
        short_form="ivm",
        config_section="DEFAULT",
        weight=85,
    )
    idle_vehicles_moving.help = (
        "by default, idle vehicles move; set this to keep them stationary"
    )
    idle_vehicles_moving.description = (
        f"idle vehicles moving ({idle_vehicles_moving.type.__name__}, default True)",
        "If True, vehicles in the 'available' state move around",
        "If False, they stay where they are.",
    )
    results_window = ConfigItem(
        name="results_window",
        type=int,
        default=50,
        action="store",
        short_form="rw",
        metavar="N",
        config_section="DEFAULT",
        weight=90,
        min_value=1,
        max_value=1000,
    )
    results_window.help = (
        "number of blocks over which to average results "
        "computed at the end of the simulation"
    )
    results_window.description = (
        f"results window ({results_window.type.__name__}, "
        f"default {results_window.default})",
        "At the end of the run, compute the final results by averaging over",
        "results_window blocks. Typically bigger than smoothing_window.",
    )
    log_file = ConfigItem(
        name="log_file",
        type=str,
        default=None,
        action="store",
        short_form="l",
        metavar="filename",
        config_section="DEFAULT",
        weight=100,
    )
    log_file.help = "file name for logging messages"
    log_file.description = (
        f"log file ({log_file.type.__name__}, default {log_file.default})",
        "The file name for logging messages.",
        "By default, log messages are written to standard output only.",
    )
    verbosity = ConfigItem(
        name="verbosity",
        type=int,
        default=0,
        action="store",
        short_form="v",
        metavar="N",
        config_section="DEFAULT",
        weight=110,
        choices=[0, 1, 2],
    )
    verbosity.help = "[0] (print warnings only), 1 (+info), 2 (+debug)"
    verbosity.description = (
        f"verbosity ({verbosity.type.__name__}, default {verbosity.default})",
        "If 0, log warning, and error messages",
        "If 1, log info, warning, and error messages",
        "If 2, log debug, information, warning, and error messages.",
    )
    animate = ConfigItem(
        name="animate",
        type=bool,
        default=False,
        action="store_true",
        short_form="a",
        config_section="DEFAULT",
        weight=120,
    )
    animate.help = "display an animation of the simulation"
    animate.description = (
        "animate the simulation",
        "If set, configure the animation in the [ANIMATION] section.",
    )
    equilibrate = ConfigItem(
        name="equilibrate",
        type=bool,
        default=False,
        action="store_true",
        short_form="e",
        config_section="DEFAULT",
        weight=130,
    )
    equilibrate.help = "equilibrate the supply of vehicles and demand for trips"
    equilibrate.description = (
        "equilibrate the supply of vehicles and demand for trips",
        "If set, configure the equilibration in the [EQUILIBRATION] section.",
    )
    run_sequence = ConfigItem(
        name="run_sequence",
        type=bool,
        default=False,
        action="store_true",
        short_form="s",
        config_section="DEFAULT",
        weight=140,
    )
    run_sequence.help = (
        "run a sequence of simulations with different vehicle counts or request rates"
    )
    run_sequence.description = (
        "run a sequence of simulations with different vehicle counts or request rates",
        "If set, configure the sequence in the [SEQUENCE] section.",
    )
    use_city_scale = ConfigItem(
        name="use_city_scale",
        type=bool,
        default=False,
        action="store_true",
        short_form="ucs",
        config_section="DEFAULT",
        weight=145,
    )
    use_city_scale.help = (
        "Override city_size and other parameters using options in CITY_SCALE"
    )
    use_city_scale.description = (
        "The city size, and driver earnings, are calculated using options",
        "in the CITY_SCALE section. city_size and max_trip_distance are ",
        "replaced with a calculated number of blocks",
    )
    use_advanced_dispatch = ConfigItem(
        name="use_advanced_dispatch",
        type=bool,
        default=False,
        action="store_true",
        short_form="uad",
        config_section="DEFAULT",
        weight=155,
    )
    use_advanced_dispatch.help = "when dispatching vehicles to handle requests, use a method other than the default"
    use_advanced_dispatch.description = (
        "The default dispatch algorithm is to assign the closest vehicle, ",
        "or if there are multiple closest vehicles, to assign a random ",
        "vehicle from those closest.",
    )
    fix_config_file = ConfigItem(
        name="fix_config_file",
        action="store_true",
        short_form="fc",
        config_section=None,
        weight=150,
    )
    fix_config_file.help = "backup the configuration file, update in place, and exit"
    fix_config_file.description = (
        "fix the configuration file and exit"
        "If set, update the configuration file with the current descriptions",
        "A backup copy of the configuration file is made",
    )
    write_config_file = ConfigItem(
        name="write_config_file",
        type=str,
        default=None,
        action="store",
        metavar="filename",
        short_form="wc",
        config_section=None,
        weight=20,
    )
    write_config_file.help = "write a configuration file and exit"
    write_config_file.description = "write out a configuration file and exit"

    # [ANIMATION]
    animation_style = ConfigItem(
        name="animation_style",
        type=Animation,
        default=Animation.TEXT,
        action="store",
        short_form="as",
        config_section="ANIMATION",
        weight=0,
    )
    animation_style.help = "the charts to display. none, map, stats, all, bar, sequence, console, terminal_map, terminal_stats, terminal_sequence"
    animation_style.description = (
        f"animation style ({animation_style.type.__name__}, "
        f"default {animation_style.default})",
        "Select which charts and / or maps to display.",
        "Possible values include...",
        "- none (no display)",
        "- map (desktop map of vehicles and trips)",
        "- stats (desktop driver phases and wait times)",
        "- stats_bar (desktop driver phases and wait times as a bar chart)",
        "- console (a rich text-based console)",
        "- terminal_map (terminal-based map with Unicode characters and statistics)",
        "- terminal_stats (terminal-based real-time line charts using plotext)",
        "- terminal_sequence (terminal-based parameter sweep visualization using plotext)",
        "- all (displays map + stats)",
        "- bar (trip distance and wait time histogram)",
        "- text (plain text output)",
        "- sequence (desktop display of a sequence of simulations)",
    )
    animate_update_period = ConfigItem(
        name="animate_update_period",
        type=int,
        default=1,
        action="store",
        short_form="ap",
        metavar="N",
        config_section="ANIMATION",
        weight=10,
    )
    animate_update_period.help = "update charts every N blocks"
    animate_update_period.description = (
        f"animate update period ({animate_update_period.type.__name__}, "
        f"default {animate_update_period.default})",
        "Update charts every N blocks.",
    )
    annotation = ConfigItem(
        name="annotation",
        type=str,
        default=None,
        action="store",
        short_form="an",
        metavar="string",
        config_section="ANIMATION",
        weight=20,
    )
    annotation.help = "an annotation added to map and statistics plots"
    annotation.description = (
        f"annotation ({annotation.type.__name__}, default {annotation.default})",
        "An annotation added to map and stats plots",
    )
    # use_textual parameter removed - Textual is now the default for terminal animations

    # Animation delay configuration for animations
    animation_delay = ConfigItem(
        name="animation_delay",
        type=float,
        default=0.0,
        action="store",
        short_form="ad",
        config_section="ANIMATION",
        weight=26,
        min_value=0.0,
        max_value=10.0,
    )
    animation_delay.help = "Delay in seconds between animation updates"
    animation_delay.description = (
        f"animation delay ({animation_delay.type.__name__}, default {animation_delay.default}s)",
        "Controls the delay between animation updates.",
        "Higher values slow down animation, useful for small cities with few vehicles.",
        "Range: 0.1-10.0 seconds",
    )
    interpolate = ConfigItem(
        name="interpolate",
        type=int,
        default=1,
        action="store",
        short_form="ai",
        metavar="N",
        config_section="ANIMATION",
        weight=30,
    )
    interpolate.help = "for map animations, number of interpolated points per block"
    interpolate.description = (
        f"interpolate ({interpolate.type.__name__}, default {interpolate.default})",
        "For the map display (only) add this many interpolated points between",
        "time periods so the car movements are smoother.",
    )
    animation_output_file = ConfigItem(
        name="animation_output_file",
        type=str,
        default=None,
        action="store",
        short_form="aof",
        metavar="filename",
        config_section="ANIMATION",
        weight=40,
    )
    animation_output_file.help = (
        "write animation to a file (.mp4 or .gif) instead of displaying on screen"
    )
    animation_output_file.description = (
        f"animation output file ({animation_output_file.type.__name__}, "
        f"default {animation_output_file.default})",
        "Supply a file name in which to save the animations",
        "If none is supplied, display animations on the screen only.",
    )
    imagemagick_dir = ConfigItem(
        name="imagemagick_dir",
        type=str,
        default=None,
        action="store",
        short_form="aid",
        config_section="ANIMATION",
        weight=50,
    )
    imagemagick_dir.help = "ImageMagick directory. Not needed if it is in the path"
    imagemagick_dir.description = (
        f"ImageMagick directory ({imagemagick_dir.type.__name__}, "
        f"default {imagemagick_dir.default})",
        "If you choose an MP4 or GIF output (output parameter) then you need ",
        "ImageMagick. This is the directory in which it is installed,",
        "for example:",
        "",
        "  imagemagick_dir = /Program Files/ImageMagick-7.0.9-Q16 ",
    )
    smoothing_window = ConfigItem(
        name="smoothing_window",
        type=int,
        default=20,
        action="store",
        short_form="asw",
        metavar="N",
        config_section="ANIMATION",
        weight=60,
        min_value=1,
        max_value=128,
    )
    smoothing_window.help = "for graphs, display rolling averages over this many blocks"
    smoothing_window.description = (
        f"smoothing window ({smoothing_window.type.__name__}, "
        f"default {smoothing_window.default})",
        "Rolling window in which to compute trailing averages ",
        "(wait times, busy fraction etc) used in graphs and in calculations.",
    )

    # [EQUILIBRATION]
    equilibration = ConfigItem(
        name="equilibration",
        type=Equilibration,
        default=Equilibration.NONE,
        action="store",
        short_form="eq",
        config_section="EQUILIBRATION",
        weight=0,
    )
    equilibration.help = (
        "the equilibration method: none, price, or wait_fraction (no quotes)"
    )
    equilibration.description = (
        f"equilibration method ({equilibration.type.__name__} "
        f"converted to enum, default {equilibration.default})",
        "Valid values are 'none', 'price', or 'wait_fraction' (case insensitive,",
        " without the quotes).",
    )
    wait_fraction = ConfigItem(
        name="wait_fraction",
        type=float,
        default=0.3,
        action="store",
        short_form="eqw",
        metavar="float",
        config_section="EQUILIBRATION",
        weight=9,
        min_value=0.0,
        max_value=1.0,
    )
    wait_fraction.help = "wait time, as a fraction of average trip length L"
    wait_fraction.description = (
        f"wait_fraction ({wait_fraction.type.__name__}, "
        f"default {wait_fraction.default})",
        "If equilibration is set to wait_fraction, this is the wait time, as a fraction ",
        "of the average trip length L, that the system approaches.",
    )
    price = ConfigItem(
        name="price",
        type=float,
        default=1.0,
        action="store",
        short_form="eqp",
        metavar="float",
        config_section="EQUILIBRATION",
        weight=10,
        min_value=0.0,
        max_value=4.0,
    )
    price.help = "price per block, used when equilibrating by price"
    price.description = (
        f"price ({price.type.__name__}, default {price.default})",
        "Price paid by passengers, input to the equilibration process.",
    )
    platform_commission = ConfigItem(
        name="platform_commission",
        type=float,
        default=0.0,
        action="store",
        short_form="eqc",
        metavar="float",
        config_section="EQUILIBRATION",
        weight=20,
        min_value=0.0,
        max_value=0.5,
    )
    platform_commission.help = (
        "fraction of fare taken by the platform, used when equilibrating"
    )
    platform_commission.description = (
        f"platform commission F ({platform_commission.type.__name__}, "
        f"default {platform_commission.default})",
        "The vehicle utility per block is U = P.B.(1 - F) - C_d, ",
        "where F = platform commission.",
        "F > 0 amounts to the platform taking a commission, ",
        "F < 0 is the platform subsidizing vehicles.",
    )
    demand_elasticity = ConfigItem(
        name="demand_elasticity",
        type=float,
        default=0.0,
        action="store",
        short_form="eqe",
        metavar="k",
        config_section="EQUILIBRATION",
        weight=30,
        min_value=0.0,
        max_value=2.0,
    )
    demand_elasticity.help = (
        "demand elasticity (float, default 0), used when equilibrating"
    )
    demand_elasticity.description = (
        f"demand elasticity ({demand_elasticity.type.__name__}, "
        f"default {demand_elasticity.default})",
        "Applicable only when at least one of equilibrate or use_city_scale",
        "is set.",
        "The demand (request rate) = R_0 * p ^ (-e), ",
        "where e is the demand elasticity and R_0 is the base demand",
        "If left at the default, the demand does not depend on price.",
    )
    equilibration_interval = ConfigItem(
        name="equilibration_interval",
        type=int,
        default=5,
        action="store",
        short_form="eqi",
        metavar="N",
        config_section="EQUILIBRATION",
        weight=40,
        min_value=1,
        max_value=100,
    )
    equilibration_interval.help = (
        "adjust supply and demand every N blocks, when equilibrating"
    )
    equilibration_interval.description = (
        f"equilibration interval ({equilibration_interval.type.__name__}, "
        f"default {equilibration_interval.default})",
        "The number of blocks at which equilibration steps are chosen.",
    )
    reservation_wage = ConfigItem(
        name="reservation_wage",
        type=float,
        default=0.5,
        action="store",
        short_form="eqrw",
        metavar="float",
        config_section="EQUILIBRATION",
        weight=5,
        min_value=0.0,
        max_value=1.0,
    )
    reservation_wage.help = (
        "vehicles must earn this to be available, used when equilibrating"
    )
    reservation_wage.description = (
        f"reservation wage ({reservation_wage.type.__name__}, "
        f"default {reservation_wage.default})",
        "Vehicle utility per block is U = P.B(1 - F) - C_d, ",
        "where C_d = reservation wage.",
    )

    # [SEQUENCE]
    request_rate_increment = ConfigItem(
        name="request_rate_increment",
        type=float,
        default=None,
        action="store",
        short_form="sri",
        metavar="float",
        config_section="SEQUENCE",
        weight=10,
    )
    request_rate_increment.help = (
        "determines the demand for trips in each simulation of a sequence"
    )
    request_rate_increment.description = (
        f"request rate increment ({request_rate_increment.type.__name__}, "
        f"default {request_rate_increment.default})",
        "The increment in a sequence of request rates",
        "The starting value is 'base_demand' in the DEFAULT section.",
    )
    request_rate_max = ConfigItem(
        name="request_rate_max",
        type=float,
        default=None,
        action="store",
        short_form="srm",
        metavar="float",
        config_section="SEQUENCE",
        weight=20,
    )
    request_rate_max.help = "max request rate for a sequence"
    request_rate_max.description = (
        f"request rate max ({request_rate_max.type.__name__}, "
        f"default {request_rate_max.default})",
        "The maximum value in a sequence of request rates",
        "The starting value is 'base_demand' in the DEFAULT section.",
    )

    vehicle_count_increment = ConfigItem(
        name="vehicle_count_increment",
        type=int,
        default=None,
        action="store",
        short_form="svi",
        config_section="SEQUENCE",
        weight=30,
    )
    vehicle_count_increment.help = "increment vehicle count for a sequence"
    vehicle_count_increment.description = (
        f"vehicle count increment ({vehicle_count_increment.type.__name__}, "
        f"default {vehicle_count_increment.default})",
        "The increment in a sequence of vehicle counts.",
    )
    vehicle_count_max = ConfigItem(
        name="vehicle_count_max",
        type=int,
        default=None,
        action="store",
        short_form="svm",
        config_section="SEQUENCE",
        weight=40,
    )
    vehicle_count_max.help = "max vehicle count for a sequence"
    vehicle_count_max.description = (
        f"Vehicle Count Max ({vehicle_count_max.type.__name__}, "
        f"default {vehicle_count_max.default})",
        "The maximum value in a sequence of vehicle counts.",
    )
    inhomogeneity_increment = ConfigItem(
        name="inhomogeneity_increment",
        type=float,
        default=None,
        action="store",
        short_form="sii",
        metavar="float",
        config_section="SEQUENCE",
        weight=80,
    )
    inhomogeneity_increment.help = (
        "determines the city inhomogeneity in each simulation of a sequence"
    )
    inhomogeneity_increment.description = (
        f"inhomogeneity increment ({inhomogeneity_increment.type.__name__}, "
        f"default {inhomogeneity_increment.default})",
        "The increment in a sequence of inhomogeneity values",
        "The starting value is 'inhomogeneity' in the DEFAULT section.",
    )
    inhomogeneity_max = ConfigItem(
        name="inhomogeneity_max",
        type=float,
        default=None,
        action="store",
        short_form="sim",
        metavar="float",
        config_section="SEQUENCE",
        weight=90,
    )
    inhomogeneity_max.help = "max inhomogeneity for a sequence"
    inhomogeneity_max.description = (
        f"inhomogeneity max ({inhomogeneity_max.type.__name__}, "
        f"default {inhomogeneity_max.default})",
        "The maximum value in a sequence of inhomogeneity values",
        "The starting value is 'inhomgeneity' in the DEFAULT section.",
    )

    commission_increment = ConfigItem(
        name="commission_increment",
        type=float,
        default=None,
        action="store",
        short_form="pci",
        metavar="float",
        config_section="SEQUENCE",
        weight=100,
    )
    commission_increment.help = (
        "sets the commission taken by the platform in each simulation of a sequence"
    )
    commission_increment.description = (
        f"commission increment ({commission_increment.type.__name__}, "
        f"default {commission_increment.default})",
        "The increment in a sequence of platform commissions (usually between 0 and 1)",
        "The starting value is 'platform_commission' in the EQUILIBRATION section.",
    )
    commission_max = ConfigItem(
        name="commission_max",
        type=float,
        default=None,
        action="store",
        short_form="pcm",
        metavar="float",
        config_section="SEQUENCE",
        weight=120,
    )
    commission_max.help = "max commission for a sequence"
    commission_max.description = (
        f"commission max ({commission_max.type.__name__}, "
        f"default {commission_max.default})",
        "The maximum value in a sequence of platform commissions",
        "The starting value is 'platform_commission' in the EQUILIBRATION section.",
    )

    # [IMPULSES]
    impulse_list = ConfigItem(
        name="impulse_list",
        default=None,
        action="store",
        type=dict,
        short_form="il",
        config_section="IMPULSES",
    )
    impulse_list.help = (
        "a json document describing sudden changes during the simulation"
    )
    impulse_list.description = (
        f"impulse list ({impulse_list.type.__name__}, default {impulse_list.default})",
        "Sudden changes during the simulation",
        "Write as a list of dictionaries. For example...",
        "impulse_list = [{'block': 480, 'base_demand': 20.0},",
        "   {'block': 960, 'base_demand': 18.0},",
        "   {'block': 1080, 'base_demand': 7},",
        "   ]",
    )

    # [CITY_SCALE]
    @staticmethod
    def _require_if_city_scale(config_context):
        """Check if use_city_scale is enabled"""
        if config_context and hasattr(config_context, "use_city_scale"):
            return getattr(config_context.use_city_scale, "value", False)
        return False

    mean_vehicle_speed = ConfigItem(
        name="mean_vehicle_speed",
        default=30,
        action="store",
        type=float,
        short_form="ms",
        config_section="CITY_SCALE",
        weight=30,
        min_value=1.0,
        max_value=200.0,
        required_if=_require_if_city_scale,
    )
    mean_vehicle_speed.help = "mean vehicle speed in km/h"
    mean_vehicle_speed.description = (
        f"mean vehicle speed in km/h, default {mean_vehicle_speed.default}.",
        "Must be specified if use_city_scale is True",
    )
    minutes_per_block = ConfigItem(
        name="minutes_per_block",
        default=1,
        action="store",
        type=float,
        short_form="mpb",
        config_section="CITY_SCALE",
        weight=50,
        min_value=0.1,
        max_value=60.0,
        required_if=_require_if_city_scale,
    )
    minutes_per_block.help = "minutes for each block"
    minutes_per_block.description = (
        "minutes per block. Must be specified if use_city_scale is True",
    )
    per_km_ops_cost = ConfigItem(
        name="per_km_ops_cost",
        default=0,
        action="store",
        type=float,
        short_form="pkops",
        config_section="CITY_SCALE",
        weight=60,
    )
    per_km_ops_cost.help = "vehicle operations cost, per km"
    per_km_ops_cost.description = (
        "vehicle operations cost, per km",
        "Operations cost + opportunity cost = total cost",
        "Total cost overrides reservation_wage, if use_city_scale is True",
    )
    per_hour_opportunity_cost = ConfigItem(
        name="per_hour_opportunity_cost",
        default=0.0,
        action="store",
        type=float,
        short_form="phopp",
        config_section="CITY_SCALE",
        weight=70,
    )
    per_hour_opportunity_cost.help = "vehicle opportunity cost, per hour"
    per_hour_opportunity_cost.description = (
        "vehicle opportunity cost, per hour",
        "If the vehicle does not earn this much, after operating expenses,",
        "the driver will not take part in ridehailing.",
        "Operations cost + opportunity cost = total cost",
        "Total cost overrides reservation_wage, if use_city_scale is True",
    )
    per_km_price = ConfigItem(
        name="per_km_price",
        default=0,
        action="store",
        type=float,
        short_form="pkp",
        config_section="CITY_SCALE",
        weight=80,
        min_value=0.0,
        max_value=1.2,
    )
    per_km_price.help = "price charged, per km"
    per_km_price.description = (
        "price  per km",
        "Per km price + per minute price yields total price per block",
        "using the mean_vehicle_speed and city_scale to convert",
        "Total price overrides the 'price' in the EQUILIBRATION section, ",
        "if equilibrating",
    )
    per_minute_price = ConfigItem(
        name="per_minute_price",
        default=0,
        action="store",
        type=float,
        short_form="pmp",
        config_section="CITY_SCALE",
        weight=90,
        min_value=0.0,
        max_value=0.4,
    )
    per_minute_price.help = "price charged, per min"
    per_minute_price.description = (
        "price  per min",
        "Per min price + per km price yields total price per block",
        "using the mean_vehicle_speed and city_scale to convert",
        "Total price overrides the 'price' in the EQUILIBRATION section, ",
        "if equilibrating",
    )

    #
    # [ADVANCED_DISPATCH]
    #
    dispatch_method = ConfigItem(
        name="dispatch_method",
        type=DispatchMethod,
        default=DispatchMethod.DEFAULT,
        action="store",
        short_form="dm",
        config_section="ADVANCED_DISPATCH",
        weight=0,
    )
    dispatch_method.help = "the algorithm that matches vehicles to trip requests"
    dispatch_method.description = (
        f"dispatch method ({dispatch_method.type.__name__}, "
        f"default {dispatch_method.default})",
        "Select the algorithm that dispatches vehicles to trip requests",
        "Possible values include...",
        "- default (closest available p1 vehicle)",
        "- forward_dispatch (closest vehicle including p3 vehicles)",
        "- p1_legacy (closest available p1 vehicle, using older method)",
    )

    forward_dispatch_bias = ConfigItem(
        name="forward_dispatch_bias",
        type=int,
        default=0,
        action="store",
        short_form="fdb",
        config_section="ADVANCED_DISPATCH",
        weight=10,
    )
    forward_dispatch_bias.help = (
        "A higher weight gives more preference to already-engaged vehicles"
    )
    forward_dispatch_bias.description = (
        f"forward_dispatch_bias ({forward_dispatch_bias.type.__name__}, "
        f"default {forward_dispatch_bias.default})",
        "Applies only if dispatch_method = forward_dispatch.",
        "Dispatch an already-engaged vehicle if it is closer to the trip origin",
        "than (nearest P1 driver distance + forward_dispatch_bias) blocks.",
        "Must be an integer 0, 1, 2...",
    )

    def __init__(self, use_config_file=True):
        """
        Read the configuration file  to set up the parameters
        """
        self.start_time = f"{datetime.now().strftime('%Y-%m-%d-%H-%M')}"
        for attr in dir(self):
            # assign default values
            option = getattr(self, attr)
            if isinstance(option, ConfigItem):
                option.value = option.default

        if use_config_file:
            # Get the config file from the command line
            parser = self._parser()
            args, extra = parser.parse_known_args()
            self.config_file.value = args.config_file
        if use_config_file:
            self._set_options_from_config_file(self.config_file.value)
            self._override_options_from_command_line(args)
            if self.fix_config_file.value:
                self._write_config_file()
                sys.exit(0)
        self._convert_config_values_to_enum()
        self._validate_all_config_parameters()
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
                    format="[%(filename)s:%(lineno)d] %(levelname)s - %(message)s",
                )
            else:
                logging.basicConfig(
                    level=loglevel,
                    force=True,
                    format="[%(filename)s:%(lineno)d] %(levelname)s - %(message)s",
                )
        # self._log_config_settings()
        if self.write_config_file.value:
            self._write_config_file(self.write_config_file.value)
            sys.exit(0)

    def _safe_config_set(self, config_section, param_name, config_item):
        """
        Safely set a config value from config file, falling back to default if empty or invalid

        Args:
            config_section: The config section object
            param_name: The parameter name
            config_item: The ConfigItem object
        """
        try:
            raw_value = config_section.get(param_name)
            if raw_value.strip() == "":
                # Empty value, use default
                config_item.value = config_item.default
                return

            # Try to parse according to type and set
            if config_item.type is int:
                config_item.set_value(config_section.getint(param_name), self)
            elif config_item.type is float:
                config_item.set_value(config_section.getfloat(param_name), self)
            elif config_item.type is bool:
                config_item.set_value(config_section.getboolean(param_name), self)
            else:
                config_item.set_value(raw_value, self)
        except (ValueError, TypeError):
            # Invalid value, use default
            config_item.value = config_item.default

    def _validate_all_config_parameters(self):
        """
        Perform comprehensive validation of all configuration parameters
        """
        validation_errors = []

        for attr in dir(self):
            option = getattr(self, attr)
            if isinstance(option, ConfigItem):
                # Re-validate with full config context for dependency checking
                is_valid, validated_value, error_message = option.validate_value(
                    option.value, self
                )
                if not is_valid:
                    validation_errors.append(f"{option.name}: {error_message}")
                else:
                    # Update with validated value (might have been corrected)
                    option.value = validated_value

        if validation_errors:
            error_msg = "Configuration validation failed:\n" + "\n".join(
                f"  - {error}" for error in validation_errors
            )
            logging.error(error_msg)
            raise ConfigValidationError(
                "overall_config",
                f"Multiple validation failures: {len(validation_errors)} errors found",
            )

    def _log_config_settings(self):
        for attr in dir(self):
            attr_name = attr.__str__()
            option = getattr(self, attr)
            if isinstance(option, ConfigItem):
                logging.info(f"config.{attr_name} = {getattr(self, attr).value}")

    def _set_options_from_config_file(self, config_file, included=False):
        """
        Read a configuration file. This function may also be called
        with the -wc option, when there is no config file to read.
        """
        config = configparser.ConfigParser(allow_no_value=True)
        if config_file and path.exists(config_file):
            config.read(config_file)
        if included is False:
            if "include_file" in config["DEFAULT"].keys():
                # only one level of inclusion
                include_config_file = config["DEFAULT"]["include_file"]
                include_config_file = path.join(
                    self.config_file_dir, include_config_file
                )
                self._set_options_from_config_file(include_config_file, included=True)
            if (
                config.has_section("ANIMATION")
                and "include_file" in config["ANIMATION"].keys()
            ):
                # only one level of inclusion
                include_config_file = config["ANIMATION"]["include_file"]
                include_config_file = path.join(
                    self.config_file_dir, include_config_file
                )
                self._set_options_from_config_file(include_config_file, included=True)
        # Check for and ignore [RESULTS] section if present
        if config.has_section("RESULTS"):
            # Ignore [RESULTS] section in config file
            # (auto-generated from previous run)")
            pass
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
        if config.has_section("CITY_SCALE"):
            self._set_city_scale_section_options(config)
        if self.use_advanced_dispatch.value and config.has_section("ADVANCED_DISPATCH"):
            self._set_advanced_dispatch_section_options(config)

    def _set_default_section_options(self, config):
        default = config["DEFAULT"]
        if config.has_option("DEFAULT", "title"):
            self._safe_config_set(default, "title", self.title)
        if config.has_option("DEFAULT", "city_size"):
            self._safe_config_set(default, "city_size", self.city_size)
        if config.has_option("DEFAULT", "vehicle_count"):
            self._safe_config_set(default, "vehicle_count", self.vehicle_count)
        if config.has_option("DEFAULT", "base_demand"):
            self._safe_config_set(default, "base_demand", self.base_demand)
        if config.has_option("DEFAULT", "inhomogeneity"):
            self._safe_config_set(default, "inhomogeneity", self.inhomogeneity)
        if config.has_option("DEFAULT", "inhomogeneous_destinations"):
            self._safe_config_set(
                default, "inhomogeneous_destinations", self.inhomogeneous_destinations
            )
        if config.has_option("DEFAULT", "min_trip_distance"):
            self._safe_config_set(default, "min_trip_distance", self.min_trip_distance)
        if config.has_option("DEFAULT", "max_trip_distance"):
            self._safe_config_set(default, "max_trip_distance", self.max_trip_distance)
        if config.has_option("DEFAULT", "time_blocks"):
            self._safe_config_set(default, "time_blocks", self.time_blocks)
        if config.has_option("DEFAULT", "results_window"):
            self._safe_config_set(default, "results_window", self.results_window)
        if config.has_option("DEFAULT", "idle_vehicles_moving"):
            self._safe_config_set(
                default, "idle_vehicles_moving", self.idle_vehicles_moving
            )
        if config.has_option("DEFAULT", "random_number_seed"):
            self._safe_config_set(
                default, "random_number_seed", self.random_number_seed
            )
        if config.has_option("DEFAULT", "log_file"):
            self._safe_config_set(default, "log_file", self.log_file)
        if config.has_option("DEFAULT", "verbosity"):
            self._safe_config_set(default, "verbosity", self.verbosity)
        if config.has_option("DEFAULT", "animate"):
            self._safe_config_set(default, "animate", self.animate)
        if config.has_option("DEFAULT", "equilibrate"):
            self._safe_config_set(default, "equilibrate", self.equilibrate)
        if config.has_option("DEFAULT", "run_sequence"):
            self._safe_config_set(default, "run_sequence", self.run_sequence)
        if config.has_option("DEFAULT", "use_city_scale"):
            self._safe_config_set(default, "use_city_scale", self.use_city_scale)
        if config.has_option("DEFAULT", "use_advanced_dispatch"):
            self._safe_config_set(
                default, "use_advanced_dispatch", self.use_advanced_dispatch
            )

    def _set_animation_section_options(self, config):
        """ """
        animation = config["ANIMATION"]
        if config.has_option("ANIMATION", "animation_style"):
            try:
                self.animation_style.value = animation.get("animation_style")
            except ValueError:
                pass
        if config.has_option("ANIMATION", "animate_update_period"):
            try:
                self.animate_update_period.value = animation.getint(
                    "animate_update_period"
                )
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
                    "animation_output_file"
                )
            except ValueError:
                pass
        if config.has_option("ANIMATION", "annotation"):
            try:
                self.annotation.value = animation.get("annotation")
            except ValueError:
                pass
        # use_textual configuration removed - Textual is now the default
        if config.has_option("ANIMATION", "animation_delay"):
            try:
                self.animation_delay.value = animation.getfloat("animation_delay")
            except ValueError:
                pass
        if config.has_option("ANIMATION", "imagemagick_dir"):
            try:
                self.imagemagick_dir.value = animation.get("imagemagick_dir")
            except ValueError:
                pass
        if config.has_option("ANIMATION", "smoothing_window"):
            try:
                self.smoothing_window.value = animation.getint("smoothing_window")
            except ValueError:
                pass

    def _set_equilibration_section_options(self, config):
        equilibration = config["EQUILIBRATION"]
        if config.has_option("EQUILIBRATION", "equilibration"):
            self.equilibration.value = equilibration.get("equilibration")
        if config.has_option("EQUILIBRATION", "price"):
            self.price.value = equilibration.getfloat("price", fallback=1.0)
        if config.has_option("EQUILIBRATION", "wait_fraction"):
            self.wait_fraction.value = equilibration.getfloat(
                "wait_fraction", fallback=0.3
            )
        if config.has_option("EQUILIBRATION", "platform_commission"):
            self.platform_commission.value = equilibration.getfloat(
                "platform_commission", fallback=0
            )
        if config.has_option("EQUILIBRATION", "reservation_wage"):
            self.reservation_wage.value = equilibration.getfloat(
                "reservation_wage", fallback=0.0
            )
        if config.has_option("EQUILIBRATION", "demand_elasticity"):
            self.demand_elasticity.value = equilibration.getfloat(
                "demand_elasticity", fallback=0.0
            )
        if config.has_option("EQUILIBRATION", "equilibration_interval"):
            self.equilibration_interval.value = equilibration.getint(
                "equilibration_interval", fallback=5
            )

    def _set_sequence_section_options(self, config):
        sequence = config["SEQUENCE"]
        if config.has_option("SEQUENCE", "request_rate_increment"):
            try:
                self.request_rate_increment.value = sequence.getfloat(
                    "request_rate_increment", fallback=None
                )
            except ValueError:
                # leave as the default
                pass
        if config.has_option("SEQUENCE", "request_rate_max"):
            try:
                self.request_rate_max.value = sequence.getfloat(
                    "request_rate_max", fallback=None
                )
            except ValueError:
                # leave as the default
                pass
        if config.has_option("SEQUENCE", "vehicle_count_increment"):
            try:
                self.vehicle_count_increment.value = sequence.getint(
                    "vehicle_count_increment", fallback=None
                )
            except ValueError:
                # leave as the default
                pass
        if config.has_option("SEQUENCE", "vehicle_count_max"):
            try:
                self.vehicle_count_max.value = sequence.getint(
                    "vehicle_count_max", fallback=None
                )
            except ValueError:
                # leave as the default
                pass
        if config.has_option("SEQUENCE", "inhomogeneity_increment"):
            try:
                self.inhomogeneity_increment.value = sequence.getfloat(
                    "inhomogeneity_increment", fallback=None
                )
            except ValueError:
                # leave as the default
                pass
        if config.has_option("SEQUENCE", "inhomogeneity_max"):
            try:
                self.inhomogeneity_max.value = sequence.getfloat(
                    "inhomogeneity_max", fallback=None
                )
            except ValueError:
                # leave as the default
                pass
        if config.has_option("SEQUENCE", "commission_increment"):
            try:
                self.commission_increment.value = sequence.getfloat(
                    "commission_increment", fallback=None
                )
            except ValueError:
                # leave as the default
                pass
        if config.has_option("SEQUENCE", "commission_max"):
            try:
                self.commission_max.value = sequence.getfloat(
                    "commission_max", fallback=None
                )
            except ValueError:
                # leave as the default
                pass

    def _set_impulses_section_options(self, config):
        impulses = config["IMPULSES"]
        if config.has_option("IMPULSES", "impulse_list"):
            self.impulse_list.value = impulses.get("impulse_list")
            if self.impulse_list.value:
                self.impulse_list.value = eval(self.impulse_list.value)

    def _set_city_scale_section_options(self, config):
        city_scale = config["CITY_SCALE"]
        if config.has_option("CITY_SCALE", "mean_vehicle_speed"):
            self.mean_vehicle_speed.value = city_scale.getfloat("mean_vehicle_speed")
        if config.has_option("CITY_SCALE", "minutes_per_block"):
            self.minutes_per_block.value = city_scale.getfloat("minutes_per_block")
        if config.has_option("CITY_SCALE", "per_km_ops_cost"):
            self.per_km_ops_cost.value = city_scale.getfloat("per_km_ops_cost")
        if config.has_option("CITY_SCALE", "per_hour_opportunity_cost"):
            self.per_hour_opportunity_cost.value = city_scale.getfloat(
                "per_hour_opportunity_cost"
            )
        if config.has_option("CITY_SCALE", "per_km_price"):
            self.per_km_price.value = city_scale.getfloat("per_km_price")
        if config.has_option("CITY_SCALE", "per_minute_price"):
            self.per_minute_price.value = city_scale.getfloat("per_minute_price")

    def _set_advanced_dispatch_section_options(self, config):
        """ """
        advanced_dispatch = config["ADVANCED_DISPATCH"]
        if config.has_option("ADVANCED_DISPATCH", "dispatch_method"):
            try:
                self.dispatch_method.value = advanced_dispatch.get("dispatch_method")
            except ValueError:
                pass
        if config.has_option("ADVANCED_DISPATCH", "forward_dispatch_bias"):
            self.forward_dispatch_bias.value = advanced_dispatch.getint(
                "forward_dispatch_bias"
            )

    def _override_options_from_command_line(self, args):
        """
        Override configuration options with command line settings
        """
        args_dict = vars(args)
        for key, val in args_dict.items():
            option = getattr(self, key)
            if (
                isinstance(option, ConfigItem)
                and option.action != "store_true"
                and val is not None
            ):
                # better to do this by selecting on action=store_true
                option.value = val
            elif (
                isinstance(option, ConfigItem)
                and option.action == "store_true"
                and val is True
            ):
                option.value = val

    def _convert_config_values_to_enum(self):
        """
        For options that are supposed to be enum values, make them so.
        """
        # Set the equilibration value to an enum
        if not isinstance(self.equilibration.value, Equilibration):
            for eq_option in list(Equilibration):
                if self.equilibration.value.lower()[0:2] == eq_option.name.lower()[0:2]:
                    self.equilibration.value = eq_option
                    break
            if self.equilibration.value not in list(Equilibration):
                logging.error(
                    "equilibration must start with n[one], p[rice], or w[ait_fraction]"
                )

        # set animation style to an enum
        if not isinstance(self.animation_style.value, Animation):
            for animation_style in list(Animation):
                if (
                    self.animation_style.value.lower().strip()
                    == animation_style.value.lower().strip()
                ):
                    self.animation_style.value = animation_style
                    break
            if self.animation_style.value not in list(Animation):
                self.animation_style.value = Animation.NONE

        # set dispatch method to an enum
        if not isinstance(self.dispatch_method.value, DispatchMethod):
            for dispatch_method in list(DispatchMethod):
                if (
                    self.dispatch_method.value.lower()[0:2]
                    == dispatch_method.value.lower()[0:2]
                ):
                    self.dispatch_method.value = dispatch_method
                    break
            if self.dispatch_method.value not in list(DispatchMethod):
                self.dispatch_method.value = DispatchMethod.DEFAULT

    def _write_config_file(self, config_file=None):
        # Write out a configuration file, with name ...
        # The config_file parameter is supplied to create a new config file
        # but not supplied when writing out a fixed config file.
        # In that case, it comes in from self.config_file
        if config_file:
            this_config_file = config_file
        else:
            this_config_file = self.config_file.value
        this_config_file_dir = path.dirname(this_config_file)
        this_config_file_root = path.splitext(path.split(this_config_file)[1])[0]
        if not config_file:
            # Fixing an existing config file (self.config_file)
            # Back up existing config file
            i = 0
            while True:
                config_file_backup = (
                    f"./{this_config_file_dir}/"
                    f"{this_config_file_root}_{i}.config_backup"
                )
                if not path.isfile(config_file_backup):
                    break
                else:
                    i += 1
            if path.isfile(this_config_file):
                rename(this_config_file, config_file_backup)

        # Write out a new one
        comment_line = "# " + "-" * 76 + "\n"
        config_item_list = [
            getattr(self, attr)
            for attr in dir(self)
            if isinstance(getattr(self, attr), ConfigItem)
        ]
        config_item_list.sort(key=lambda x: x.weight)
        config_file_sections = [
            "DEFAULT",
            "ANIMATION",
            "EQUILIBRATION",
            "SEQUENCE",
            "IMPULSES",
            "CITY_SCALE",
            "ADVANCED_DISPATCH",
        ]
        with open(this_config_file, "w") as f:
            for section in config_file_sections:
                f.write("\n")
                f.write(f"[{section}]")
                f.write("\n")
                for config_item in config_item_list:
                    # Only write out active items with config sections
                    if config_item.config_section is None or not config_item.active:
                        continue
                    if isinstance(config_item.value, Enum):
                        config_item.value = config_item.value.value
                    if config_item.value is None:
                        if config_item.action == "store_true":
                            config_item.value = "False"
                        elif config_item.type is str:
                            config_item.value = ""
                            pass
                        else:
                            config_item.value = ""
                    description = comment_line
                    for line in config_item.description:
                        description += "# " + line + "\n"
                    description += comment_line
                    if config_item.config_section == section:
                        f.write("\n")
                        f.write(description)
                        f.write("\n")
                        if config_item.value is None:
                            f.write(f"# {config_item.name} = \n")
                        else:
                            f.write(f"{config_item.name} = {config_item.value}\n")
            f.write("\n")
        f.close()

    def write_results_section(self, config_file_path, results_dict):
        """
        Write or replace [RESULTS] section in config file with simulation results.

        This method appends a [RESULTS] section to the config file after a simulation
        completes. If a [RESULTS] section already exists, it is removed first to
        ensure only the most recent results are stored.

        Args:
            config_file_path: Path to the configuration file
            results_dict: Dictionary of standardized results (from get_standardized_results())

        Returns:
            bool: True if successful, False if file not writable or other error

        Side effects:
            - Modifies config file in place (atomic operation using temp file)
            - Logs warnings if file issues occur
        """
        import os
        import tempfile

        # Check if file exists
        if not os.path.exists(config_file_path):
            logging.warning(
                f"Config file {config_file_path} not found, skipping results write"
            )
            return False

        # Check if file is writable
        if not os.access(config_file_path, os.W_OK):
            logging.warning(
                f"Config file {config_file_path} not writable, skipping results write"
            )
            return False

        try:
            # Read existing content
            with open(config_file_path, "r") as f:
                lines = f.readlines()

            # Remove any existing [RESULTS] section
            filtered_lines = self._remove_results_section(lines)

            # Format new results section
            results_section = self._format_results_section(results_dict)

            # Write atomically using temp file in same directory
            config_dir = os.path.dirname(config_file_path) or "."
            fd, temp_path = tempfile.mkstemp(
                dir=config_dir, prefix=".config_", suffix=".tmp"
            )

            try:
                with os.fdopen(fd, "w") as temp_file:
                    temp_file.writelines(filtered_lines)
                    temp_file.write(results_section)

                # Atomic rename (replaces original file)
                os.replace(temp_path, config_file_path)
                return True

            except Exception as e:
                # Clean up temp file if something went wrong
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                raise e

        except Exception as e:
            logging.error(f"Failed to write results to config file: {e}")
            return False

    def _remove_results_section(self, lines):
        """
        Remove any existing [RESULTS] section from config file lines.

        Args:
            lines: List of lines from config file

        Returns:
            List of lines with [RESULTS] section removed
        """
        filtered_lines = []
        in_results_section = False

        for line in lines:
            stripped = line.strip()

            # Check if we're entering results section
            if stripped == "[RESULTS]":
                in_results_section = True
                continue

            # Check if we're entering a different section (end of RESULTS)
            if (
                in_results_section
                and stripped.startswith("[")
                and stripped.endswith("]")
            ):
                in_results_section = False
                # Include this line (start of new section)
                filtered_lines.append(line)
                continue

            # Skip lines while in results section
            if in_results_section:
                continue

            # Keep all other lines
            filtered_lines.append(line)
        if filtered_lines[-1].strip() != "":
            filtered_lines.append("\n")

        return filtered_lines

    def _format_results_section(self, results_dict):
        """
        Format results dictionary as a [RESULTS] config section.

        Args:
            results_dict: Dictionary of result key-value pairs

        Returns:
            String formatted as config file section
        """
        comment_line = "# " + "-" * 76 + "\n"
        section_lines = []

        # Section header
        section_lines.append("[RESULTS]\n\n")

        # Header comment
        section_lines.append(comment_line)
        section_lines.append("# Simulation Results\n")
        if "SIM_TIMESTAMP" in results_dict:
            section_lines.append(f"# Generated: {results_dict['SIM_TIMESTAMP']}\n")
        section_lines.append(
            "# This section is automatically generated and will be overwritten on each run\n"
        )
        section_lines.append("# Do not manually edit this section\n")
        section_lines.append("#\n")
        section_lines.append(
            "# If configuration parameters in this file were overwritten by command-line\n"
        )
        section_lines.append(
            "# options or interactively, the results will not be reproducible.\n"
        )
        section_lines.append(comment_line)
        section_lines.append("\n")

        # Group results by category for better readability
        vehicle_keys = [
            Measure.VEHICLE_MEAN_COUNT.name,
            Measure.VEHICLE_FRACTION_P1.name,
            Measure.VEHICLE_FRACTION_P2.name,
            Measure.VEHICLE_FRACTION_P3.name,
        ]
        trip_keys = [
            Measure.TRIP_MEAN_REQUEST_RATE.name,
            Measure.TRIP_MEAN_RIDE_TIME.name,
            Measure.TRIP_MEAN_WAIT_FRACTION_TOTAL.name,
            Measure.TRIP_FORWARD_DISPATCH_FRACTION.name,
        ]
        validation_keys = [
            Measure.SIM_CHECK_NP2_OVER_RW.name,
            Measure.SIM_CHECK_NP3_OVER_RL.name,
            Measure.SIM_CHECK_P1_P2_P3.name,
            Measure.SIM_CONVERGENCE_MAX_RMS_RESIDUAL.name,
        ]
        simulation_keys = [
            "SIM_TIMESTAMP",
            "SIM_RIDEHAIL_VERSION",
            "SIM_DURATION_SECONDS",
            "SIM_BLOCKS_SIMULATED",
            "SIM_BLOCKS_ANALYZED",
        ]

        # Write metadata

        # Write simulation metrics
        section_lines.append("# Simulation metrics\n")
        for key in simulation_keys:
            if key in results_dict:
                section_lines.append(f"{key} = {results_dict[key]}\n")
        section_lines.append("\n")

        # Write vehicle metrics
        section_lines.append("# Vehicle metrics (averaged over results window)\n")
        for key in vehicle_keys:
            if key in results_dict:
                section_lines.append(f"{key} = {results_dict[key]:.3f}\n")
        section_lines.append("\n")

        # Write trip metrics
        section_lines.append("# Trip metrics (averaged over results window)\n")
        for key in trip_keys:
            if key in results_dict:
                section_lines.append(f"{key} = {results_dict[key]:.3f}\n")
        section_lines.append("\n")

        # Write validation metrics
        section_lines.append(
            "# Validation metrics (to measure simulation correctness)\n"
        )
        for key in validation_keys:
            if key in results_dict:
                section_lines.append(f"{key} = {results_dict[key]:.3f}\n")
        section_lines.append("\n")

        return "".join(section_lines)

    def _parser(self):
        """
        Define, read and parse command-line arguments.
        """
        # Usage text
        parser = argparse.ArgumentParser(
            description="Simulate ride-hail vehicles and trips.",
            usage="%(prog)s config-file [options]",
            fromfile_prefix_chars="@",
        )
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
                    parser.add_argument(
                        config_item.name,
                        metavar=metavar,
                        nargs="?",
                        action=config_item.action,
                        type=config_item.type,
                        default=config_item.default,
                        help=help_text,
                    )
                elif config_item.action == "store":
                    parser.add_argument(
                        f"-{config_item.short_form}",
                        f"--{config_item.name}",
                        metavar=metavar,
                        action=config_item.action,
                        type=config_item.type,
                        help=help_text,
                    )
                elif config_item.action == "store_true":
                    # Does not need a metavar
                    parser.add_argument(
                        f"-{config_item.short_form}",
                        f"--{config_item.name}",
                        action=config_item.action,
                        help=help_text,
                    )

        return parser


class WritableConfig:
    def __init__(self, config):
        """
        Return the configuration information relevant to simulations,
        to be written to output files.

        This is a bit different to the methods in RideHailSimulationResult, whic
        return the configuration as it is at the end of the run. Here, it's the
        configuration fed in which is supplyed and which might be a big different.
        Still, it seems like duplication....

        This does not include all the animation choices etc.
        """
        self.title = config.title.value
        self.start_time = config.start_time
        self.city_size = config.city_size.value
        self.base_demand = config.base_demand.value
        self.vehicle_count = config.vehicle_count.value
        self.inhomogeneity = config.inhomogeneity.value
        self.inhomogeneous_destinations = config.inhomogeneous_destinations.value
        self.min_trip_distance = config.min_trip_distance.value
        self.max_trip_distance = config.max_trip_distance.value
        self.time_blocks = config.time_blocks.value
        self.results_window = config.results_window.value
        self.random_number_seed = config.random_number_seed.value
        self.idle_vehicles_moving = config.idle_vehicles_moving.value
        # Handle dispatch_method which may be enum or string
        if isinstance(config.dispatch_method.value, DispatchMethod):
            self.dispatch_method = config.dispatch_method.value.value
        else:
            self.dispatch_method = config.dispatch_method.value
        self.forward_dispatch_bias = config.forward_dispatch_bias.value
        if config.equilibration.value:
            equilibration = {}
            # Handle equilibration which may be enum or string
            if isinstance(config.equilibration.value, Equilibration):
                equilibration["equilibration"] = config.equilibration.value.value
            else:
                equilibration["equilibration"] = config.equilibration.value
            equilibration["price"] = config.price.value
            equilibration["platform_commission"] = config.platform_commission.value
            equilibration["reservation_wage"] = config.reservation_wage.value
            equilibration["demand_elasticity"] = config.demand_elasticity.value
            equilibration["equilibration_interval"] = (
                config.equilibration_interval.value
            )
            self.equilibration = equilibration
