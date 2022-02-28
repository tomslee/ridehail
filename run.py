#!/usr/bin/python3
"""
Ridehail animations: for amusement only
"""

# -------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------
import logging
import sys
from ridehail import sequence, animation, simulation, config


def main():
    """
    Entry point.
    """
    # ridehail_config = read_config(args)
    ridehail_config = config.RideHailConfig()
    for attr in dir(ridehail_config):
        attr_name = attr.__str__()
        config_item = getattr(ridehail_config, attr)
        if isinstance(config_item, config.ConfigItem):
            print(f"ridehail_config.{attr_name} "
                  f"= {getattr(ridehail_config, attr).value}")
    if ridehail_config:
        if (hasattr(ridehail_config, "run_sequence")
                and ridehail_config.run_sequence.value):
            seq = sequence.RideHailSimulationSequence(ridehail_config)
            seq.run_sequence(ridehail_config)
        else:
            sim = simulation.RideHailSimulation(ridehail_config)
            if ridehail_config.animate == animation.Animation.NONE:
                sim.simulate()
                # results.write_json(ridehail_config.jsonl_file)
            else:
                anim = animation.RideHailAnimation(sim)
                anim.animate()
        return (0)
    else:
        logging.error("Configuration error: exiting")
        return (-1)


if __name__ == '__main__':
    sys.exit(main())
    # import cProfile
    # import pstats
    # profiler = cProfile.Profile()
    # profiler.enable()
    # # For some reason, using sys.exit(main()) produces no output,
    # # so just call main()
    # main()
    # profiler.disable()
    # stats = pstats.Stats(profiler).sort_stats('tottime')
    # stats.print_stats()