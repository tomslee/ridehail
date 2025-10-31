"""
Performance profiling script for ridehail simulation.
Tracks per-block timing to identify slowdown causes.
"""

import cProfile
import pstats
import io
import time
import sys
from ridehail.config import RideHailConfig
from ridehail.simulation import RideHailSimulation, GARBAGE_COLLECTION_INTERVAL


def profile_simulation_blocks(config_file, num_blocks, profile_every=10):
    """
    Run simulation and profile specific blocks to identify slowdown pattern.

    Args:
        config_file: Path to .config file
        num_blocks: Total blocks to simulate
        profile_every: Profile detailed stats every N blocks
    """
    # Load config
    sys.argv = ["performance_profiler.py", config_file, "-b", str(num_blocks), "-as", "none"]
    config = RideHailConfig()
    sim = RideHailSimulation(config)

    # Track timing per block
    block_times = []
    trips_dict_sizes = []

    print(f"Profiling {num_blocks} blocks...")
    print(f"Config: city_size={sim.city_size}, vehicles={sim.vehicle_count}, demand={sim.base_demand}")
    print(f"Garbage collection interval: {GARBAGE_COLLECTION_INTERVAL}")
    print("\nBlock    Time(ms)  Trips  Cumulative(s)")
    print("-" * 50)

    cumulative_time = 0.0

    for block in range(num_blocks):
        start = time.perf_counter()
        sim.next_block()
        elapsed = time.perf_counter() - start

        block_times.append(elapsed)
        trips_dict_sizes.append(len(sim.trips))
        cumulative_time += elapsed

        # Print progress every 10 blocks
        if block % 10 == 0 or block == num_blocks - 1:
            print(f"{block:5d}    {elapsed*1000:7.2f}  {len(sim.trips):6d}  {cumulative_time:13.2f}")

    # Analysis
    print("\n" + "=" * 50)
    print("PERFORMANCE ANALYSIS")
    print("=" * 50)

    # Timing progression
    early_avg = sum(block_times[:10]) / 10 * 1000
    mid_avg = sum(block_times[num_blocks//2:num_blocks//2+10]) / 10 * 1000 if num_blocks > 20 else 0
    late_avg = sum(block_times[-10:]) / 10 * 1000

    print(f"\nAverage block time:")
    print(f"  First 10 blocks:  {early_avg:.2f} ms")
    if mid_avg > 0:
        print(f"  Middle 10 blocks: {mid_avg:.2f} ms ({(mid_avg/early_avg-1)*100:+.1f}%)")
    print(f"  Last 10 blocks:   {late_avg:.2f} ms ({(late_avg/early_avg-1)*100:+.1f}%)")

    # Trip dictionary growth
    print(f"\nTrip dictionary size:")
    print(f"  Start:  {trips_dict_sizes[0]}")
    print(f"  Peak:   {max(trips_dict_sizes)} (block {trips_dict_sizes.index(max(trips_dict_sizes))})")
    print(f"  End:    {trips_dict_sizes[-1]}")

    # Slowdown correlation
    print(f"\nSlowdown pattern:")
    for i, block_idx in enumerate([0, num_blocks//4, num_blocks//2, 3*num_blocks//4, num_blocks-1]):
        if block_idx < len(block_times):
            print(f"  Block {block_idx:4d}: {block_times[block_idx]*1000:6.2f} ms, {trips_dict_sizes[block_idx]:6d} trips")

    return block_times, trips_dict_sizes


def deep_profile_single_block(config_file, target_block=100):
    """
    Run cProfile on a specific block to identify bottleneck functions.
    """
    sys.argv = ["performance_profiler.py", config_file, "-b", str(target_block + 10), "-as", "none"]
    config = RideHailConfig()
    sim = RideHailSimulation(config)

    # Warm up to target block
    print(f"Warming up to block {target_block}...")
    for block in range(target_block):
        sim.next_block()

    # Profile the target block
    print(f"\nProfiling block {target_block} in detail...")
    profiler = cProfile.Profile()
    profiler.enable()

    sim.next_block()

    profiler.disable()

    # Print results
    s = io.StringIO()
    ps = pstats.Stats(profiler, stream=s).sort_stats('cumulative')
    ps.print_stats(30)  # Top 30 functions

    print(s.getvalue())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python performance_profiler.py <config_file> [num_blocks]")
        print("Example: python performance_profiler.py feb_6_48.config 400")
        sys.exit(1)

    config_file = sys.argv[1]
    num_blocks = int(sys.argv[2]) if len(sys.argv) > 2 else 100

    print("=" * 50)
    print("RIDEHAIL PERFORMANCE PROFILER")
    print("=" * 50)

    # Block-by-block timing analysis
    block_times, trips_sizes = profile_simulation_blocks(config_file, num_blocks)

    # Detailed profiling at different points
    print("\n" + "=" * 50)
    print("DETAILED PROFILING: BLOCK 10 (Early)")
    print("=" * 50)
    deep_profile_single_block(config_file, target_block=10)

    print("\n" + "=" * 50)
    print(f"DETAILED PROFILING: BLOCK {num_blocks-10} (Late)")
    print("=" * 50)
    deep_profile_single_block(config_file, target_block=num_blocks-10)
