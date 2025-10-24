#!/usr/bin/env python3
"""
Analyze profiling output to identify performance bottlenecks
"""
import pstats
from pstats import SortKey

# Load the profiling data
stats = pstats.Stats('profile_output.prof')

# Print summary statistics
print("=" * 80)
print("TOP 30 FUNCTIONS BY CUMULATIVE TIME")
print("=" * 80)
stats.sort_stats(SortKey.CUMULATIVE)
stats.print_stats(30)

print("\n" + "=" * 80)
print("TOP 30 FUNCTIONS BY TOTAL TIME (excluding subcalls)")
print("=" * 80)
stats.sort_stats(SortKey.TIME)
stats.print_stats(30)

print("\n" + "=" * 80)
print("CALLERS OF TOP TIME-CONSUMING FUNCTIONS")
print("=" * 80)
stats.sort_stats(SortKey.TIME)
stats.print_callers(10)

print("\n" + "=" * 80)
print("DETAILED BREAKDOWN FOR RIDEHAIL PACKAGE")
print("=" * 80)
stats.sort_stats(SortKey.TIME)
stats.print_stats('ridehail', 50)
