#!/usr/bin/python3
"""
Ridehail animations: for amusement only
"""

# -------------------------------------------------------------------------------
# Imports
# -------------------------------------------------------------------------------
import logging
import logging.config
import sys
from ridehail.atom import Animation
from ridehail.animation import ConsoleAnimation, MatplotlibAnimation, TerminalMapAnimation
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation
from ridehail.sequence import RideHailSimulationSequence

logging.config.dictConfig(
    {
        "version": 1,
        "disable_existing_loggers": True,
    }
)


def main():
    """
    Entry point.
    """
    # ridehail_config = read_config(args)
    ridehail_config = RideHailConfig()
    # for attr in dir(ridehail_config):
    # attr_name = attr.__str__()
    # config_item = getattr(ridehail_config, attr)
    # if isinstance(config_item, ConfigItem):
    # print(f"ridehail_config.{attr_name} "
    # f"= {getattr(ridehail_config, attr).value}")
    if ridehail_config:
        if (
            hasattr(ridehail_config, "run_sequence")
            and ridehail_config.run_sequence.value
        ):
            seq = RideHailSimulationSequence(ridehail_config)
            seq.run_sequence(ridehail_config)
        else:
            sim = RideHailSimulation(ridehail_config)
            if (
                ridehail_config.animate.value is False
                or ridehail_config.animation_style.value
                in (Animation.NONE, Animation.TEXT, "none", "text")
            ):
                sim.simulate()
                # results.write_json(ridehail_config.jsonl_file)
            elif ridehail_config.animation_style.value == Animation.CONSOLE:
                anim = ConsoleAnimation(sim)
                anim.animate()
            elif ridehail_config.animation_style.value == Animation.TERMINAL_MAP:
                anim = TerminalMapAnimation(sim)
                anim.animate()
            else:
                anim = MatplotlibAnimation(sim)
                anim.animate()
        return 0
    else:
        logging.error("Configuration error: exiting")
        return -1


if __name__ == "__main__":
    if "--profile" in sys.argv:
        import cProfile
        import pstats
        profiler = cProfile.Profile()
        profiler.enable()
        main()
        profiler.disable()
        stats = pstats.Stats(profiler).sort_stats('tottime')
        stats.print_stats()
    else:
        sys.exit(main())
