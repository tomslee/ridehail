#!/usr/bin/python3
"""
Ridehail animations: for amusement only
"""

# -------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------
import sys
from ridehail import simulation, animation, sequence, config


def main():
    """
    Entry point.
    """
    # ridehail_config = read_config(args)
    ridehail_config = config.RideHailConfig()
    if ridehail_config is False:
        return (-1)
    else:
        if hasattr(ridehail_config, "sequence") and ridehail_config.sequence:
            seq = sequence.RideHailSimulationSequence(ridehail_config)
            seq.run_sequence()
        else:
            sim = simulation.RideHailSimulation(ridehail_config)
            if ridehail_config.animate in (animation.Animation.NONE,
                                           animation.Animation.SUMMARY):
                sim.simulate()
                # results.write_json(ridehail_config.jsonl_file)
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
