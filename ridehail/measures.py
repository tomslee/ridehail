"""
Shared Measure computation for a given History-keyed window of CircularBuffers.

Used by both RideHailSimulation._update_measures() (live, per-block stats,
windowed over smoothing_window) and RideHailSimulationResults.get_result_measures()
(end-of-run results, windowed over results_window). The two call sites differ
only in which buffer dict and window size they pass in, and in what they do
with the returned dict afterward (live convergence tracking vs. end-of-run
validation checks and bookkeeping fields).
"""

import statistics

from ridehail.atom import CityScaleUnit, DispatchMethod, History, Measure


def compute_measures(sim, history, window):
    """
    Compute the dict of Measure values (keyed by Measure.name) for the given
    History buffer dict and window size.

    Args:
        sim: a RideHailSimulation instance. Only read: price,
            platform_commission, dispatch_method, use_city_scale, city_size,
            per_km_ops_cost, trip_completion_history, vehicle_utility(),
            convert_units().
        history: dict[History, CircularBuffer] -- either sim.history_buffer
            (smoothing_window-sized, live stats) or sim.history_results
            (results_window-sized, end-of-run results).
        window: int, the number of blocks the buffers above represent.

    Does not set SIM_CONVERGENCE_MAX_RMS_RESIDUAL, SIM_CONVERGENCE_METRIC,
    SIM_IS_CONVERGED, SIM_CHECK_*, or any SIM_* bookkeeping fields (timestamp,
    duration, blocks_simulated/analyzed) -- these are computed differently by
    each caller and are added to the returned dict afterward.
    """
    measures = {}
    for item in list(Measure):
        measures[item.name] = 0

    measures[Measure.TRIP_SUM_COUNT.name] = float(history[History.TRIP_COUNT].sum)
    measures[Measure.VEHICLE_MEAN_COUNT.name] = (
        float(history[History.VEHICLE_COUNT].sum) / window
    )
    measures[Measure.TRIP_MEAN_REQUEST_RATE.name] = (
        float(history[History.TRIP_REQUEST_RATE].sum) / window
    )
    measures[Measure.TRIP_MEAN_PRICE.name] = (
        float(history[History.TRIP_PRICE].sum) / window
    )
    measures[Measure.VEHICLE_SUM_TIME.name] = float(history[History.VEHICLE_TIME].sum)
    if measures[Measure.VEHICLE_SUM_TIME.name] > 0:
        measures[Measure.VEHICLE_FRACTION_P1.name] = (
            float(history[History.VEHICLE_TIME_P1].sum)
            / measures[Measure.VEHICLE_SUM_TIME.name]
        )
        measures[Measure.VEHICLE_FRACTION_P2.name] = (
            float(history[History.VEHICLE_TIME_P2].sum)
            / measures[Measure.VEHICLE_SUM_TIME.name]
        )
        measures[Measure.VEHICLE_FRACTION_P3.name] = (
            float(history[History.VEHICLE_TIME_P3].sum)
            / measures[Measure.VEHICLE_SUM_TIME.name]
        )
        vehicle_median_time = history[History.VEHICLE_TIME].median()
        if vehicle_median_time > 0:
            measures[Measure.VEHICLE_MEDIAN_P1.name] = (
                history[History.VEHICLE_TIME_P1].median() / vehicle_median_time
            )
            measures[Measure.VEHICLE_MEDIAN_P2.name] = (
                history[History.VEHICLE_TIME_P2].median() / vehicle_median_time
            )
            measures[Measure.VEHICLE_MEDIAN_P3.name] = (
                history[History.VEHICLE_TIME_P3].median() / vehicle_median_time
            )
        measures[Measure.VEHICLE_GROSS_INCOME.name] = (
            sim.price
            * (1.0 - sim.platform_commission)
            * measures[Measure.VEHICLE_FRACTION_P3.name]
        )
        # if use_city_scale is false, net income is same as gross
        measures[Measure.VEHICLE_NET_INCOME.name] = (
            sim.price
            * (1.0 - sim.platform_commission)
            * measures[Measure.VEHICLE_FRACTION_P3.name]
        )
        measures[Measure.VEHICLE_MEAN_SURPLUS.name] = sim.vehicle_utility(
            measures[Measure.VEHICLE_FRACTION_P3.name]
        )
    if measures[Measure.TRIP_SUM_COUNT.name] > 0:
        measures[Measure.TRIP_MEAN_WAIT_TIME.name] = (
            float(history[History.TRIP_WAIT_TIME].sum)
            / measures[Measure.TRIP_SUM_COUNT.name]
        )
        measures[Measure.TRIP_MEAN_RIDE_TIME.name] = (
            float(history[History.TRIP_DISTANCE].sum)
            / measures[Measure.TRIP_SUM_COUNT.name]
        )
        measures[Measure.TRIP_MEAN_WAIT_FRACTION.name] = (
            measures[Measure.TRIP_MEAN_WAIT_TIME.name]
            / measures[Measure.TRIP_MEAN_RIDE_TIME.name]
        )
        measures[Measure.TRIP_MEAN_WAIT_FRACTION_TOTAL.name] = measures[
            Measure.TRIP_MEAN_WAIT_TIME.name
        ] / (
            measures[Measure.TRIP_MEAN_RIDE_TIME.name]
            + measures[Measure.TRIP_MEAN_WAIT_TIME.name]
        )
        if sim.trip_completion_history:
            wait_times = [w for (_, w, _) in sim.trip_completion_history]
            distances = [d for (_, _, d) in sim.trip_completion_history]
            measures[Measure.TRIP_MEDIAN_WAIT_TIME.name] = statistics.median(
                wait_times
            )
            median_ride_time = statistics.median(distances)
            if median_ride_time > 0:
                measures[Measure.TRIP_MEDIAN_WAIT_FRACTION.name] = (
                    measures[Measure.TRIP_MEDIAN_WAIT_TIME.name] / median_ride_time
                )
                measures[Measure.TRIP_MEDIAN_WAIT_FRACTION_TOTAL.name] = measures[
                    Measure.TRIP_MEDIAN_WAIT_TIME.name
                ] / (median_ride_time + measures[Measure.TRIP_MEDIAN_WAIT_TIME.name])
        measures[Measure.TRIP_DISTANCE_FRACTION.name] = measures[
            Measure.TRIP_MEAN_RIDE_TIME.name
        ] / float(sim.city_size)
        measures[Measure.PLATFORM_MEAN_INCOME.name] = (
            sim.price
            * sim.platform_commission
            * measures[Measure.TRIP_SUM_COUNT.name]
            * measures[Measure.TRIP_MEAN_RIDE_TIME.name]
            / window
        )
        if sim.dispatch_method == DispatchMethod.FORWARD_DISPATCH:
            measures[Measure.TRIP_FORWARD_DISPATCH_FRACTION.name] = (
                float(history[History.TRIP_FORWARD_DISPATCH_COUNT].sum)
                / measures[Measure.TRIP_SUM_COUNT.name]
            )
    if sim.use_city_scale:
        measures[Measure.TRIP_MEAN_PRICE.name] = sim.convert_units(
            measures[Measure.TRIP_MEAN_PRICE.name],
            CityScaleUnit.PER_BLOCK,
            CityScaleUnit.PER_MINUTE,
        )
        measures[Measure.TRIP_MEAN_WAIT_TIME.name] = sim.convert_units(
            measures[Measure.TRIP_MEAN_WAIT_TIME.name],
            CityScaleUnit.PER_BLOCK,
            CityScaleUnit.PER_MINUTE,
        )
        measures[Measure.TRIP_MEAN_RIDE_TIME.name] = sim.convert_units(
            measures[Measure.TRIP_MEAN_RIDE_TIME.name],
            CityScaleUnit.PER_BLOCK,
            CityScaleUnit.PER_MINUTE,
        )
        measures[Measure.VEHICLE_GROSS_INCOME.name] = sim.convert_units(
            measures[Measure.VEHICLE_GROSS_INCOME.name],
            CityScaleUnit.PER_BLOCK,
            CityScaleUnit.PER_HOUR,
        )
        measures[Measure.VEHICLE_NET_INCOME.name] = measures[
            Measure.VEHICLE_GROSS_INCOME.name
        ] - sim.convert_units(
            sim.per_km_ops_cost, CityScaleUnit.PER_KM, CityScaleUnit.PER_HOUR
        )
        measures[Measure.PLATFORM_MEAN_INCOME.name] = sim.convert_units(
            measures[Measure.PLATFORM_MEAN_INCOME.name],
            CityScaleUnit.PER_BLOCK,
            CityScaleUnit.PER_HOUR,
        )
        measures[Measure.VEHICLE_MEAN_SURPLUS.name] = sim.convert_units(
            measures[Measure.VEHICLE_MEAN_SURPLUS.name],
            CityScaleUnit.PER_BLOCK,
            CityScaleUnit.PER_HOUR,
        )
        # Note: TRIP_MEAN_PRICE was previously converted a second time here,
        # re-applying PER_BLOCK->PER_MINUTE to an already-converted value.
        # That double conversion is a no-op only when minutes_per_block == 1
        # (the default); for any other value it silently produced a wrong
        # result. Removed as part of de-duplicating this function.
    return measures
