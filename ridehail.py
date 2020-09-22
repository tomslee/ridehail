#!/usr/bin/python3
"""
Ridehail animations: for amusement only
"""

# -------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------
import logging
import os
import sys
from ridehail import simulation, animation, sequence, config


def main():
    """
    Entry point.
    """
    ridehail_config = config.RideHailConfig()
    if ridehail_config.verbosity == 0:
        loglevel = "WARNING"
    elif ridehail_config.verbosity == 1:
        loglevel = "INFO"
    elif ridehail_config.verbosity == 2:
        loglevel = "DEBUG"
    else:
        loglevel = "WARNING"
    if ridehail_config.log_file:
        logging.basicConfig(filename=ridehail_config.log_file,
                            filemode='w',
                            level=getattr(logging, loglevel.upper()),
                            format='%(asctime)-15s %(levelname)-8s%(message)s')
        logging.info(f"Logging to {ridehail_config.log_file}")
    else:
        logging.basicConfig(level=getattr(logging, loglevel.upper()),
                            format='%(asctime)-15s %(levelname)-8s%(message)s')
    logging.debug("Logging debug messages...")
    # ridehail_config = read_config(args)
    if ridehail_config is False:
        return (False)
    else:
        if hasattr(ridehail_config, "sequence") and ridehail_config.sequence:
            seq = sequence.RideHailSimulationSequence(ridehail_config)
            seq.run_sequence()
        else:
            sim = simulation.RideHailSimulation(ridehail_config)
            if ridehail_config.animate in (animation.Animation.NONE,
                                           animation.Animation.SUMMARY):
                results = sim.simulate()
                results.write_json(ridehail_config.jsonl_file)
            else:
                anim = animation.RideHailAnimation(sim)
                anim.animate()
    return (0)


if __name__ == '__main__':
    sys.exit(main())
    # import cProfile
    # import pstats
    # profiler = cProfile.Profile()
    # profiler.enable()
    # main()
    # profiler.disable()
    # stats = pstats.Stats(profiler).sort_stats('tottime')
    # stats.print_stats()
