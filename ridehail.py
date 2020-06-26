#!/usr/bin/python3
"""
Ridehail animations: for amusement only
"""

# -------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------
import argparse
import configparser
import logging
import random
import os
import copy
import matplotlib as mpl
from enum import Enum
# from matplotlib.widgets import Slider
import seaborn as sns
from pandas.plotting import register_matplotlib_converters
from atoms import Driver, DriverPhase, Trip, TripPhase, City, Direction
from simulation import RideHailSimulation, Equilibration
from sequence import RideHailSimulationSequence
from plot import Draw

register_matplotlib_converters()

logger = logging.getLogger(__name__)

# -------------------------------------------------------------------------------
# Parameters
# -------------------------------------------------------------------------------

GARBAGE_COLLECTION_INTERVAL = 10
SUPPLY_DEMAND_RANGE = [0.8, 1.2]
DEFAULT_TIME_PERIODS = 1001
DEFAULT_REQUEST_RATE = 0.2
DEFAULT_INTERPOLATION_POINTS = 4
DEFAULT_CITY_SIZE = 10
DEFAULT_DRIVER_COUNT = 1
MAX_REQUESTS_PER_PERIOD = 10

# TODO: IMAGEMAGICK_EXE is hardcoded here. Put it in a config file.
IMAGEMAGICK_DIR = "/Program Files/ImageMagick-7.0.9-Q16"
# IMAGEMAGICK_DIR = "/Program Files/ImageMagick-7.0.10-Q16"
# For ImageMagick configuration, see
# https://stackoverflow.com/questions/23417487/saving-a-matplotlib-animation-with-imagemagick-and-without-ffmpeg-or-mencoder/42565258#42565258

# -------------------------------------------------------------------------------
# Set up graphicself.color_palette['figure.figsize'] = [7.0, 4.0]
mpl.rcParams['figure.dpi'] = 90
mpl.rcParams['savefig.dpi'] = 100
mpl.rcParams['animation.convert_path'] = IMAGEMAGICK_DIR + "/magick.exe"
mpl.rcParams['animation.ffmpeg_path'] = IMAGEMAGICK_DIR + "/ffmpeg.exe"

# mpl.rcParams['font.size'] = 12
# mpl.rcParams['legend.fontsize'] = 'large'
# mpl.rcParams['figure.titlesize'] = 'medium'
sns.set()
sns.set_palette("muted")

# ------------------------------------------------------------------------------
# Enumerations
# ------------------------------------------------------------------------------


class RequestModel(Enum):
    THRESHOLD_GLOBAL = 0
    THRESHOLD_PER_DRIVER = 1


# ------------------------------------------------------------------------------
# Functions
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Classes
# ------------------------------------------------------------------------------
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
        config = configparser.ConfigParser()
        if self.config_file is None:
            # The default config file is username.config
            # look for username.config on both Windows (USERNAME)
            # and Linux (USER)
            if os.name == "nt":
                username = os.environ['USERNAME']
            else:
                username = os.environ['USER']
            self.config_file = username + ".config"
            logger.info(f"Reading configuration file {self.config_file}")
            if not os.path.isfile(self.config_file):
                logger.error(
                    f"Configuration file {self.config_file} not found.")
        config.read(self.config_file)

        # Fill in individual configuration values
        # City size
        self.city_size = int(args.city_size if args.
                             city_size else config["DEFAULT"]["city_size"])
        logger.info(f"City size = {self.city_size}")
        # Driver count
        driver_counts = (args.driver_count if args.driver_count else
                         config["DEFAULT"]["driver_count"])
        self.driver_count = [int(x) for x in driver_counts.split(",")]
        logger.info(f"Driver counts = {self.driver_count}")
        # Request rate
        request_rates = (args.request_rate if args.request_rate else
                         config["DEFAULT"]["request_rate"])
        self.request_rate = [float(x) for x in request_rates.split(",")]
        logger.info(f"Request rate = {self.request_rate}")
        # Time periods
        self.time_periods = int(args.time_periods if args.time_periods else
                                config["DEFAULT"]["time_periods"])
        logger.info(f"Time periods = {self.time_periods}")
        # Log file TODO not sure if this works
        self.log_file = str(
            args.log_file if args.log_file else config["DEFAULT"]["log_file"])
        logger.info(f"Log file = {self.log_file}")
        # Verbose output
        self.verbose = bool(
            args.verbose if args.verbose else config["DEFAULT"]["verbose"])
        logger.info(f"Verbose = {self.verbose}")
        # Quiet output
        self.quiet = bool(
            args.quiet if args.quiet else config["DEFAULT"]["quiet"])
        logger.info(f"Quiet = {self.quiet}")
        # Draw maps or charts
        self.draw = str(args.draw if args.draw else config["DEFAULT"]["draw"])
        for draw_option in list(Draw):
            if self.draw == draw_option.value:
                self.draw = draw_option
                break
        logger.info(f"Draw = {self.draw}")
        # Draw update period
        self.draw_update_period = int(
            args.draw_update_period if args.
            draw_update_period else config["DEFAULT"]["draw_update_period"])
        logger.info(f"Draw update period = {self.draw_update_period}")
        # Interpolation points
        self.interpolate = int(args.interpolate if args.interpolate else
                               config["DEFAULT"]["interpolate"])
        logger.info(f"Interpolation points = {self.interpolate}")
        # Equilibrate
        self.equilibrate = str(args.equilibrate if args.equilibrate else
                               config["DEFAULT"]["equilibrate"])
        logger.info(f"Equilibration = {self.equilibrate}")
        # Rolling window
        self.rolling_window = int(args.rolling_window if args.rolling_window
                                  else config["DEFAULT"]["rolling_window"])
        logger.info(f"Rolling window = {self.rolling_window}")
        # Output file for charts
        self.output = str(
            args.output if args.output else config["DEFAULT"]["output"])
        logger.info(f"Output file for charts = {self.output}")
        # ImageMagick directory
        self.imagemagick_dir = str(args.imagemagick_dir if args.imagemagick_dir
                                   else config["DEFAULT"]["imagemagick_dir"])
        logger.info(f"ImageMagick_Dir = {self.imagemagick_dir}")
        # Available drivers moving
        self.available_drivers_moving = bool(
            args.available_drivers_moving if args.available_drivers_moving else
            config["DEFAULT"]["available_drivers_moving"])
        logger.info(
            f"Available drivers moving = {self.available_drivers_moving}")
        if self.equilibrate:
            for option in list(Equilibration):
                if self.equilibrate.lower()[0] == option.name.lower()[0]:
                    self.equilibrate = option
                    logger.info(f"Equilibration method is {option.name}")
                    break
            if self.equilibrate not in list(Equilibration):
                logger.error(f"equilibrate must start with s, d, or f")
            # Price
            self.price = float(
                args.price if args.price else config["EQUILIBRATION"]["price"])
            logger.info(f"Price = {self.price}")
            # Driver cost
            self.driver_cost = float(args.driver_cost if args.driver_cost else
                                     config["EQUILIBRATION"]["driver_cost"])
            logger.info(f"Driver cost = {self.driver_cost}")
            # Ride utility
            self.ride_utility = float(
                args.ride_utility if args.
                ride_utility else config["EQUILIBRATION"]["ride_utility"])
            logger.info(f"Ride utility = {self.ride_utility}")
            # Wait cost
            self.wait_cost = float(args.wait_cost if args.wait_cost else
                                   config["EQUILIBRATION"]["wait_cost"])
            logger.info(f"Wait cost = {self.wait_cost}")
            # Equilibration interval
            self.equilibration_interval = int(
                args.equilibration_interval if args.equilibration_interval else
                config["EQUILIBRATION"]["equilibration_interval"])
            logger.info(
                f"Equilibration interval = {self.equilibration_interval}")


def parse_args():
    """
    Define, read and parse command-line arguments.
    """
    parser = argparse.ArgumentParser(
        description="Simulate ride-hail drivers and trips.",
        usage="%(prog)s [options]",
        fromfile_prefix_chars='@')
    parser.add_argument("-@",
                        "--config_file",
                        metavar="config_file",
                        action="store",
                        type=str,
                        default=None,
                        help="""Configuration file""")
    parser.add_argument("-adm",
                        "--available_drivers_moving",
                        metavar="available_drivers_moving",
                        action="store",
                        type=bool,
                        default=False,
                        help="""True if drivers should drive around looking for
                        a ride; False otherwise.""")
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
                        default=1,
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
                        help="""Change driver count  or request rate, or both,
                        to equilibrate""")
    parser.add_argument("-dc",
                        "--driver_cost",
                        metavar="driver_cost",
                        action="store",
                        type=float,
                        default=None,
                        help="""Driver cost per unit time""")
    parser.add_argument("-i",
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
        help="""filename: output to the display or as a file; gif or mp4""")
    parser.add_argument("-p",
                        "--price",
                        action="store",
                        type=float,
                        default=None,
                        help="Fixed price")
    parser.add_argument("-q",
                        "--quiet",
                        action="store_true",
                        default=False,
                        help="log only warnings and errors")
    parser.add_argument(
        "-ur",
        "--ride_utility",
        metavar="ride_utility",
        action="store",
        type=float,
        default=None,
        help="utility of a trip, per period, for the passenger")
    parser.add_argument("-r",
                        "--request_rate",
                        metavar="request_rate",
                        action="store",
                        type=float,
                        default=None,
                        help="requests per period")
    parser.add_argument("-dr",
                        "--draw",
                        metavar="draw",
                        action="store",
                        type=str,
                        default=None,
                        help="""draw 'all', 'none', 'driver', 'wait',
                        'stats', 'equilibration', ['map']""")
    parser.add_argument("-t",
                        "--time_periods",
                        metavar="time_periods",
                        action="store",
                        type=int,
                        default=None,
                        help="numberof time time periods")
    parser.add_argument("-v",
                        "--verbose",
                        action="store_true",
                        default=False,
                        help="log all messages, including debug")
    parser.add_argument("-rw",
                        "--rolling_window",
                        metavar="rolling_window",
                        action="store",
                        type=int,
                        default=None,
                        help="""rolling window for computing averages""")
    parser.add_argument("-wc",
                        "--wait_cost",
                        metavar="wait_cost",
                        action="store",
                        type=float,
                        default=None,
                        help="""Passenger cost per unit wait fraction""")
    args = parser.parse_args()
    return args


def main():
    """
    Entry point.
    """
    args = parse_args()
    if args.verbose:
        loglevel = "DEBUG"
    elif args.quiet:
        loglevel = "WARN"
    else:
        loglevel = "INFO"
    if args.log_file:
        logging.basicConfig(filename=args.log_file,
                            filemode='w',
                            level=getattr(logging, loglevel.upper()),
                            format='%(asctime)-15s %(levelname)-8s%(message)s')
    else:
        logging.basicConfig(level=getattr(logging, loglevel.upper()),
                            format='%(levelname)-8s%(message)s')
    logger.debug("Logging debug messages...")
    # config = read_config(args)
    config = Config(args)
    if config is False:
        exit(False)
    else:
        if config.draw == Draw.SUMMARY:
            sequence = RideHailSimulationSequence(config)
            sequence.run_sequence()
        else:
            runconfig = copy.deepcopy(config)
            for request_rate in config.request_rate:
                logger.info((f"config.request_rate = {config.request_rate}, "
                             f"config.driver_count = {config.driver_count}"))
                runconfig.request_rate = request_rate
                for driver_count in config.driver_count:
                    runconfig.driver_count = driver_count
                    simulation = RideHailSimulation(runconfig)
                    results = simulation.simulate()
                    results.write()


if __name__ == '__main__':
    main()
