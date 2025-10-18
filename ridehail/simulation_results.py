from ridehail.atom import (
    Animation,
    Equilibration,
    Measure,
    History,
    CityScaleUnit,
    DispatchMethod,
)
from datetime import datetime
import logging


class RideHailSimulationResults:
    """
    Hold the results of a RideHailSimulation.
    Usually it just writes it out, but now we can do things like
    plot sequences of simulations
    """

    def __init__(self, sim):
        self.sim = sim
        self.results = {}
        self.results["config"] = self.get_current_config()
        # Add version at top level

    def get_current_config(self):
        """
        Configuration parameters may change during the course of a simulation,
        for example by keyboard shortcuts. So we take the current config
        from the simulation object properties rather than the configuration
        object fed into the simulation.
        """
        config = {}
        # Special values from context
        config["timestamp"] = self.sim.start_time
        config["version"] = self.sim.version
        # Config DEFAULT section
        config["title"] = self.sim.title
        config["city_size"] = self.sim.city_size
        config["vehicle_count"] = len(self.sim.vehicles)
        config["inhomogeneity"] = self.sim.city.inhomogeneity
        config["base_demand"] = self.sim.base_demand
        config["min_trip_distance"] = self.sim.min_trip_distance
        config["max_trip_distance"] = self.sim.max_trip_distance
        config["results_window"] = self.sim.results_window
        config["idle_vehicles_moving"] = self.sim.idle_vehicles_moving
        config["time_blocks"] = self.sim.time_blocks
        config["animate"] = self.sim.animate
        config["equilibrate"] = self.sim.equilibrate
        config["use_city_scale"] = self.sim.use_city_scale
        config["use_advanced_dispatch"] = self.sim.use_advanced_dispatch
        config["run_sequence"] = self.sim.run_sequence
        # Config ANIMATION section
        if self.sim.animate and self.sim.animation_style != Animation.NONE:
            animation = {}
            animation["animation_style"] = self.sim.animation_style
            animation["animation_output_file"] = self.sim.animation_output_file
            animation["interpolate"] = self.sim.interpolate
            animation["smoothing_window"] = self.sim.smoothing_window
            animation["annotation"] = self.sim.annotation
            config["animation"] = animation
        # Config EQUILIBRATION section
        if self.sim.equilibrate and self.sim.equilibration != Equilibration.NONE:
            equilibration = {}
            equilibration["equilibration"] = self.sim.equilibration.name
            equilibration["price"] = self.sim.price
            equilibration["platform_commission"] = self.sim.platform_commission
            equilibration["equilibration_interval"] = self.sim.equilibration_interval
            if self.sim.equilibrate == Equilibration.PRICE:
                equilibration["base_demand"] = self.sim.base_demand
                equilibration["demand_elasticity"] = self.sim.demand_elasticity
            if self.sim.equilibrate in (Equilibration.PRICE, Equilibration.SUPPLY):
                equilibration["reservation_wage"] = self.sim.reservation_wage
            config["equilibration"] = equilibration
        # Cnfig CITY_SCALE section
        if self.sim.use_city_scale:
            city_scale = {}
            city_scale["mean_vehicle_speed"] = self.sim.mean_vehicle_speed
            city_scale["minutes_per_block"] = self.sim.minutes_per_block
            city_scale["per_km_ops_cost"] = self.sim.per_km_ops_cost
            city_scale["per_hour_opportunity_cost"] = self.sim.per_hour_opportunity_cost
            city_scale["per_km_price"] = self.sim.per_km_price
            city_scale["per_minute_price"] = self.sim.per_minute_price
            config["city_scale"] = city_scale
        # Config ADVANCED_DISPATCH section
        if self.sim.use_advanced_dispatch:
            advanced_dispatch = {}
            advanced_dispatch["dispatch_method"] = self.sim.dispatch_method
            advanced_dispatch["forward_dispatch_bias"] = self.sim.forward_dispatch_bias
            config["advanced_dispatch"] = advanced_dispatch
        config["request_rate"] = self.sim.request_rate
        return config

    def _get_result_measures(self):
        """
        Collect final state measures, averaged over the final
        sim.results_window blocks of the simulation.

        Use strings for keys instead of enums as this needs to be callable from
        outside environments.

        This method parallels RideHailSimulation._update_measures() and ideally
        they should be combined.

        Phase 1 enhancement: Returns hierarchical structure with summary,
        vehicles, trips, and validation sections.
        """
        # check for case where results_window is bigger than time_blocks
        block = self.sim.time_blocks
        block_lower_bound = max((self.sim.time_blocks - self.sim.results_window), 0)
        window = block - block_lower_bound
        measures = {}
        for item in list(Measure):
            measures[item.name] = 0

        measures[Measure.TRIP_SUM_COUNT.name] = float(
            self.sim.history_results[History.TRIP_COUNT].sum
        )
        measures[Measure.VEHICLE_MEAN_COUNT.name] = (
            float(self.sim.history_results[History.VEHICLE_COUNT].sum) / window
        )
        measures[Measure.TRIP_MEAN_REQUEST_RATE.name] = (
            float(self.sim.history_results[History.TRIP_REQUEST_RATE].sum) / window
        )
        measures[Measure.TRIP_MEAN_PRICE.name] = (
            float(self.sim.history_results[History.TRIP_PRICE].sum) / window
        )
        measures[Measure.VEHICLE_SUM_TIME.name] = float(
            self.sim.history_results[History.VEHICLE_TIME].sum
        )
        if measures[Measure.VEHICLE_SUM_TIME.name] > 0:
            measures[Measure.VEHICLE_FRACTION_P1.name] = (
                float(self.sim.history_results[History.VEHICLE_TIME_P1].sum)
                / measures[Measure.VEHICLE_SUM_TIME.name]
            )
            measures[Measure.VEHICLE_FRACTION_P2.name] = (
                float(self.sim.history_results[History.VEHICLE_TIME_P2].sum)
                / measures[Measure.VEHICLE_SUM_TIME.name]
            )
            measures[Measure.VEHICLE_FRACTION_P3.name] = (
                float(self.sim.history_results[History.VEHICLE_TIME_P3].sum)
                / measures[Measure.VEHICLE_SUM_TIME.name]
            )
            measures[Measure.VEHICLE_GROSS_INCOME.name] = (
                self.sim.price
                * (1.0 - self.sim.platform_commission)
                * measures[Measure.VEHICLE_FRACTION_P3.name]
            )
            # if use_city_scale is false, net income is same as gross
            measures[Measure.VEHICLE_NET_INCOME.name] = (
                self.sim.price
                * (1.0 - self.sim.platform_commission)
                * measures[Measure.VEHICLE_FRACTION_P3.name]
            )
            measures[Measure.VEHICLE_MEAN_SURPLUS.name] = self.sim.vehicle_utility(
                measures[Measure.VEHICLE_FRACTION_P3.name]
            )
        if measures[Measure.TRIP_SUM_COUNT.name] > 0:
            measures[Measure.TRIP_MEAN_WAIT_TIME.name] = (
                float(self.sim.history_results[History.TRIP_WAIT_TIME].sum)
                / measures[Measure.TRIP_SUM_COUNT.name]
            )
            measures[Measure.TRIP_MEAN_RIDE_TIME.name] = (
                # float(self.sim.history_results[History.TRIP_RIDING_TIME].sum) /
                float(self.sim.history_results[History.TRIP_DISTANCE].sum)
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
            measures[Measure.TRIP_DISTANCE_FRACTION.name] = measures[
                Measure.TRIP_MEAN_RIDE_TIME.name
            ] / float(self.sim.city_size)
            measures[Measure.PLATFORM_MEAN_INCOME.name] = (
                self.sim.price
                * self.sim.platform_commission
                * measures[Measure.TRIP_SUM_COUNT.name]
                * measures[Measure.TRIP_MEAN_RIDE_TIME.name]
                / window
            )
            if self.sim.dispatch_method == DispatchMethod.FORWARD_DISPATCH:
                measures[Measure.TRIP_FORWARD_DISPATCH_FRACTION.name] = (
                    float(
                        self.sim.history_results[
                            History.TRIP_FORWARD_DISPATCH_COUNT
                        ].sum
                    )
                    / measures[Measure.TRIP_SUM_COUNT.name]
                )
        if self.sim.use_city_scale:
            measures[Measure.TRIP_MEAN_PRICE.name] = self.sim.convert_units(
                measures[Measure.TRIP_MEAN_PRICE.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_MINUTE,
            )
            measures[Measure.TRIP_MEAN_WAIT_TIME.name] = self.sim.convert_units(
                measures[Measure.TRIP_MEAN_WAIT_TIME.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_MINUTE,
            )
            measures[Measure.TRIP_MEAN_RIDE_TIME.name] = self.sim.convert_units(
                measures[Measure.TRIP_MEAN_RIDE_TIME.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_MINUTE,
            )
            measures[Measure.VEHICLE_GROSS_INCOME.name] = self.sim.convert_units(
                measures[Measure.VEHICLE_GROSS_INCOME.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_HOUR,
            )
            measures[Measure.VEHICLE_NET_INCOME.name] = measures[
                Measure.VEHICLE_GROSS_INCOME.name
            ] - self.sim.convert_units(
                self.sim.per_km_ops_cost, CityScaleUnit.PER_KM, CityScaleUnit.PER_HOUR
            )
            measures[Measure.PLATFORM_MEAN_INCOME.name] = self.sim.convert_units(
                measures[Measure.PLATFORM_MEAN_INCOME.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_HOUR,
            )
            measures[Measure.VEHICLE_MEAN_SURPLUS.name] = self.sim.convert_units(
                measures[Measure.VEHICLE_MEAN_SURPLUS.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_HOUR,
            )
            measures[Measure.TRIP_MEAN_PRICE.name] = self.sim.convert_units(
                measures[Measure.TRIP_MEAN_PRICE.name],
                CityScaleUnit.PER_BLOCK,
                CityScaleUnit.PER_MINUTE,
            )
        # Simulation checks
        measures[Measure.SIM_CONVERGENCE_MAX_RMS_RESIDUAL.name] = (
            self.sim.history_results[History.SIM_CONVERGENCE_MAX_RMS_RESIDUAL].sum
            / window
        )
        # These simulation checks rely only on measures, not history values
        measures[Measure.SIM_CHECK_NP3_OVER_RL.name] = (
            measures[Measure.VEHICLE_MEAN_COUNT.name]
            * measures[Measure.VEHICLE_FRACTION_P3.name]
            / (
                measures[Measure.TRIP_MEAN_REQUEST_RATE.name]
                * measures[Measure.TRIP_MEAN_RIDE_TIME.name]
            )
        )
        measures[Measure.SIM_CHECK_NP2_OVER_RW.name] = (
            measures[Measure.VEHICLE_MEAN_COUNT.name]
            * measures[Measure.VEHICLE_FRACTION_P2.name]
            / (
                measures[Measure.TRIP_MEAN_REQUEST_RATE.name]
                * measures[Measure.TRIP_MEAN_WAIT_TIME.name]
            )
        )
        measures[Measure.SIM_CHECK_P1_P2_P3.name] = (
            measures[Measure.VEHICLE_FRACTION_P1.name]
            + measures[Measure.VEHICLE_FRACTION_P2.name]
            + measures[Measure.VEHICLE_FRACTION_P3.name]
        )
        self.sim.convergence_tracker.push_measures(measures)
        # Compute convergence metrics if we have sufficient history
        return (measures, window)

    def get_end_state(self):
        """
        The end_state dict is a more readable representation of the final
        results computed in _get_result_measures(). It is a bit more selective,
        groups the items into a hieratchy, and gives them lower case keys.

        The end_state dict is used in the "text" animation_style output, as
        well as in the output csv and json files.
        """
        # Validation checks
        (measures, window) = self._get_result_measures()
        # validation and convergence checks
        if (
            measures[Measure.TRIP_SUM_COUNT.name] > 0
            and measures[Measure.TRIP_MEAN_RIDE_TIME.name] > 0
            and measures[Measure.TRIP_MEAN_REQUEST_RATE.name] > 0
        ):
            # Create hierarchical structure (Phase 1 enhancement)
            end_state = {
                "simulation": {
                    "blocks_simulated": self.sim.time_blocks,
                    "blocks_analyzed": window,
                    "max_rms_residual": round(
                        measures[Measure.SIM_CONVERGENCE_MAX_RMS_RESIDUAL.name],
                        4,
                    ),
                },
                "vehicles": {
                    "mean_count": round(measures[Measure.VEHICLE_MEAN_COUNT.name], 3),
                    "fraction_p1": round(measures[Measure.VEHICLE_FRACTION_P1.name], 3),
                    "fraction_p2": round(measures[Measure.VEHICLE_FRACTION_P2.name], 3),
                    "fraction_p3": round(measures[Measure.VEHICLE_FRACTION_P3.name], 3),
                },
                "trips": {
                    "mean_request_rate": round(
                        measures[Measure.TRIP_MEAN_REQUEST_RATE.name], 3
                    ),
                    "mean_wait_fraction_total": round(
                        measures[Measure.TRIP_MEAN_WAIT_FRACTION_TOTAL.name], 3
                    ),
                    "mean_ride_time": round(
                        measures[Measure.TRIP_MEAN_RIDE_TIME.name], 3
                    ),
                    "forward_dispatch_fraction": round(
                        measures[Measure.TRIP_FORWARD_DISPATCH_FRACTION.name], 3
                    ),
                },
                "validation": {
                    "check_np3_over_rl": round(
                        measures[Measure.SIM_CHECK_NP3_OVER_RL.name], 3
                    ),
                    "check_np2_over_rw": round(
                        measures[Measure.SIM_CHECK_NP2_OVER_RW.name], 3
                    ),
                    "check_p1_p2_p3": round(
                        measures[Measure.SIM_CHECK_P1_P2_P3.name],
                        3,
                    ),
                },
            }

        # I hope I can avoid keeping end_state around, but need to confirm.
        return end_state

    def get_standardized_results(self, timestamp=None, duration_seconds=None):
        """
        Return standardized results using History enum names for config file export.

        This method creates a flat dictionary suitable for writing to a config file's
        [RESULTS] section. Keys use History enum names (e.g., History.VEHICLE_COUNT.name)
        for consistency with internal simulation structures.

        Args:
            timestamp: ISO format timestamp for when simulation completed (optional)
            duration_seconds: Total simulation execution time in seconds (optional)

        Returns:
            Dictionary with standardized result keys and values
        """
        (measures, window) = self._get_result_measures()

        # Start with metadata
        results = {}

        # Add timestamp (use provided or generate now)
        if timestamp:
            results["SIM_TIMESTAMP"] = timestamp
        else:
            results["SIM_TIMESTAMP"] = datetime.now().isoformat()

        # Add version
        results["SIM_RIDEHAIL_VERSION"] = self.sim.config.version.value
        results["SIM_BLOCKS_SIMULATED"] = self.sim.time_blocks
        results["SIM_BLOCKS_ANALYZED"] = window

        # Add duration if provided
        if duration_seconds is not None:
            logging.debug(f"duration_seconds={duration_seconds:.2f}")
            results["SIM_DURATION_SECONDS"] = round(duration_seconds, 2)

        # Union these results with all measures
        results = results | measures

        return results
