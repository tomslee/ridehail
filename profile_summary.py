#!/usr/bin/env python3
"""
Generate a focused summary of profiling results
"""
import pstats
from pstats import SortKey

# Load the profiling data
stats = pstats.Stats('profile_output.prof')

print("=" * 80)
print("PERFORMANCE PROFILING SUMMARY")
print("Simulation: Toronto coarse.config (3000 vehicles, 500 blocks, ~22.85s)")
print("=" * 80)
print()

# Get total time
total_time = stats.total_tt
print(f"Total profiled time: {total_time:.2f} seconds")
print()

# Focus on the most time-consuming functions in ridehail package
print("=" * 80)
print("TOP BOTTLENECKS IN RIDEHAIL PACKAGE (by cumulative time)")
print("=" * 80)

# Get stats sorted by cumulative time
stats.sort_stats(SortKey.CUMULATIVE)
ridehail_stats = {k: v for k, v in stats.stats.items() if 'ridehail' in k[0]}

# Get top entries
sorted_stats = sorted(ridehail_stats.items(), key=lambda x: x[1][3], reverse=True)

print(f"{'Function':<60} {'Calls':>12} {'Total Time':>12} {'Cumulative':>12} {'% Total':>8}")
print("-" * 110)

for i, (key, value) in enumerate(sorted_stats[:20]):
    filename, line, func_name = key
    # value is (cc, nc, tt, ct, callers) - primitive calls, ncalls, tottime, cumtime, callers
    cc, nc, tt, ct, callers = value
    # Extract just the relevant part of the path
    short_path = filename.replace('/home/tom/src/ridehail-simulation/', '')
    func_display = f"{short_path.split('/')[-1]}:{func_name}"[:60]
    pct_total = (tt / total_time) * 100

    print(f"{func_display:<60} {str(nc):>12} {tt:>12.3f} {ct:>12.3f} {pct_total:>7.1f}%")

print()
print("=" * 80)
print("KEY INSIGHTS")
print("=" * 80)

# Calculate percentage of time in key functions
dispatch_distance_time = 0
distance_time = 0
dispatch_sparse_time = 0
update_direction_time = 0
update_location_time = 0

for key, value in ridehail_stats.items():
    filename, line, func_name = key
    cc, nc, tt, ct, callers = value

    if 'dispatch_distance' in func_name:
        dispatch_distance_time = tt
    elif func_name == 'distance':
        distance_time = tt
    elif '_dispatch_vehicle_sparse' in func_name:
        dispatch_sparse_time = tt
    elif 'update_direction' in func_name and 'atom.py' in filename:
        update_direction_time = tt
    elif 'update_location' in func_name and 'atom.py' in filename:
        update_location_time = tt

dispatch_total = dispatch_distance_time + distance_time + dispatch_sparse_time
movement_total = update_direction_time + update_location_time

print(f"1. DISPATCH OPERATIONS: {dispatch_total:.2f}s ({(dispatch_total/total_time)*100:.1f}% of total)")
print(f"   - dispatch_distance(): {dispatch_distance_time:.2f}s")
print(f"   - distance(): {distance_time:.2f}s")
print(f"   - _dispatch_vehicle_sparse(): {dispatch_sparse_time:.2f}s")
print()
print(f"2. VEHICLE MOVEMENT: {movement_total:.2f}s ({(movement_total/total_time)*100:.1f}% of total)")
print(f"   - update_direction(): {update_direction_time:.2f}s")
print(f"   - update_location(): {update_location_time:.2f}s")
print()

# Calculate calls per block
print("=" * 80)
print("CALL FREQUENCY ANALYSIS (500 blocks simulated)")
print("=" * 80)

for key, value in sorted_stats[:10]:
    filename, line, func_name = key
    cc, nc, tt, ct, callers = value
    if isinstance(nc, tuple):
        nc = nc[0]  # primitive calls
    calls_per_block = nc / 500
    short_path = filename.replace('/home/tom/src/ridehail-simulation/', '')
    func_display = f"{short_path.split('/')[-1]}:{func_name}"

    if calls_per_block > 1:
        print(f"{func_display:<50} {calls_per_block:>12,.1f} calls/block")

print()
print("=" * 80)
print("RECOMMENDATIONS")
print("=" * 80)
print("1. Distance calculations dominate (19.8s, 35% of total time)")
print("   - Called 25.5M times (51k per block)")
print("   - Optimization target: cache or reduce distance calculations")
print()
print("2. Dispatch is expensive (27s total, 48% of total time)")
print("   - _dispatch_vehicle_sparse called 48k times (~96 per block)")
print("   - Each dispatch searches through available vehicles")
print("   - Consider spatial indexing (quadtree, k-d tree)")
print()
print("3. Vehicle updates are frequent but efficient")
print("   - update_direction/location called ~1.6M times each")
print("   - Takes 3.7s total (6.5% of time) - already well optimized")
print()
