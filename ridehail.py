#!/usr/bin/python3
"""
Ridehail animations: for amusement only
"""

# -------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------
import argparse
import logging
import os
# from matplotlib.widgets import Slider
from pandas.plotting import register_matplotlib_converters
from ridehail.simulation import RideHailSimulation
from ridehail.sequence import RideHailSimulationSequence
from ridehail.config import Config
from datetime import datetime

register_matplotlib_converters()

# -------------------------------------------------------------------------------
# Parameters
# -------------------------------------------------------------------------------

GARBAGE_COLLECTION_INTERVAL = 10
SUPPLY_DEMAND_RANGE = [0.8, 1.2]
DEFAULT_TIME_PERIODS = 1001
DEFAULT_REQUEST_RATE = 0.2
DEFAULT_INTERPOLATION_POINTS = 4
DEFAULT_DRIVER_COUNT = 1
MAX_REQUESTS_PER_PERIOD = 10
# ------------------------------------------------------------------------------
# Enumerations
# ------------------------------------------------------------------------------


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
        help=
        """filename: graphics output to the display or as a file; gif or mp4"""
    )
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
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler()
    logger.addHandler(stream_handler)
    args = parse_args()
    config = Config(args)
    if args.verbose:
        loglevel = "DEBUG"
    elif args.quiet:
        loglevel = "WARN"
    else:
        loglevel = "INFO"
    logger.setLevel(loglevel)
    config.jsonl = ((f"{config.config_file_root}"
                     f"-{datetime.now().strftime('%Y-%m-%d-%H-%M')}"
                     ".jsonl"))
    if os.path.isfile(config.jsonl):
        os.remove(config.jsonl)
    if config.log_file:
        file_handler = logging.FileHandler(config.log_file)
        logger.addHandler(file_handler)
        # logging.basicConfig(filename=args.log_file,
        # filemode='w',
        # level=getattr(logging, loglevel.upper()),
        # format='%(asctime)-15s %(levelname)-8s%(message)s')
        logger.info(f"Logging to {config.log_file}")
    logger.debug("Logging debug messages...")
    # config = read_config(args)
    if config is False:
        exit(False)
    else:
        if hasattr(config, "run_sequence") and config.run_sequence:
            sequence = RideHailSimulationSequence(config)
            sequence.run_sequence()
        else:
            simulation = RideHailSimulation(config)
            results = simulation.simulate()
            # results.write_csv()
            results.write_json(config.jsonl)


if __name__ == '__main__':
    main()
