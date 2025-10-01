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
from .atom import Animation
from .animation import create_animation
from .config import RideHailConfig, ConfigItem
from .simulation import RideHailSimulation
from .sequence import RideHailSimulationSequence

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
            else:
                # Use the animation factory (Textual is now default for terminal animations)
                anim = create_animation(
                    ridehail_config.animation_style.value,
                    sim,
                )
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
        stats = pstats.Stats(profiler).sort_stats("tottime")
        stats.print_stats()
    else:
        sys.exit(main())
