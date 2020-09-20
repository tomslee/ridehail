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
from ridehail import simulation
from ridehail import animation
from ridehail import sequence
from ridehail import config


def main():
    """
    Entry point.
    """
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    stream_handler = logging.StreamHandler()
    logger.addHandler(stream_handler)
    ridehail_config = config.RideHailConfig()
    if os.path.isfile(ridehail_config.jsonl):
        os.remove(ridehail_config.jsonl)
    if ridehail_config.log_file:
        file_handler = logging.FileHandler(ridehail_config.log_file)
        logger.addHandler(file_handler)
        # logging.basicConfig(filename=args.log_file,
        # filemode='w',
        # level=getattr(logging, loglevel.upper()),
        # format='%(asctime)-15s %(levelname)-8s%(message)s')
        logger.info(f"Logging to {ridehail_config.log_file}")
    logger.debug("Logging debug messages...")
    # ridehail_config = read_config(args)
    if ridehail_config is False:
        return (False)
    else:
        if hasattr(ridehail_config,
                   "run_sequence") and ridehail_config.run_sequence:
            seq = sequence.RideHailSimulationSequence(ridehail_config)
            seq.run_sequence()
        else:
            sim = simulation.RideHailSimulation(ridehail_config)
            if ridehail_config.animate in (animation.Animate.NONE,
                                           animation.Animate.SUMMARY):
                results = sim.simulate()
                results.write_json(ridehail_config.jsonl)
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
