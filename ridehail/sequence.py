"""
Control a sequence of simulations
"""

import copy
import itertools
import logging
import math
from ridehail.simulation import RideHailSimulation
from ridehail.atom import Animation, DispatchMethod


def value_range(start, stop, step, decimals=3):
    """
    start, start + step, start + 2 * step, ... up to and including stop,
    rounded to `decimals` places (so 0.1 steps don't drift to 0.30000000004).
    """
    count = math.floor((stop - start) / step + 1e-9) + 1
    return [round(start + i * step, decimals) for i in range(max(count, 0))]


def sequence_values(config):
    """
    The values each swept parameter takes in a sequence: (vehicle_counts,
    request_rates, inhomogeneities, commissions). A parameter is swept from
    its config value to its max in steps of its increment, if both are set;
    otherwise it keeps its config value. Shared by RideHailSimulationSequence
    and the terminal sequence animation.
    """
    vehicle_counts = [config.vehicle_count.value]
    request_rates = [config.base_demand.value]
    inhomogeneities = [config.inhomogeneity.value]
    commissions = [config.platform_commission.value]
    if config.vehicle_count_increment.value and config.vehicle_count_max.value:
        vehicle_counts = list(
            range(
                config.vehicle_count.value,
                config.vehicle_count_max.value + 1,
                config.vehicle_count_increment.value,
            )
        )
    if config.request_rate_increment.value and config.request_rate_max.value:
        request_rates = value_range(
            config.base_demand.value,
            config.request_rate_max.value,
            config.request_rate_increment.value,
        )
    if config.inhomogeneity_increment.value and config.inhomogeneity_max.value:
        inhomogeneities = value_range(
            config.inhomogeneity.value,
            config.inhomogeneity_max.value,
            config.inhomogeneity_increment.value,
        )
    if config.commission_increment.value and config.commission_max.value:
        commissions = value_range(
            config.platform_commission.value,
            config.commission_max.value,
            config.commission_increment.value,
        )
    return vehicle_counts, request_rates, inhomogeneities, commissions


def sequence_parameters(vehicle_counts, request_rates, inhomogeneities, commissions):
    """
    Each simulation's (request_rate, vehicle_count, inhomogeneity,
    commission), in sequence order: the request rate varies slowest.
    """
    return itertools.product(
        request_rates, vehicle_counts, inhomogeneities, commissions
    )


class RideHailSimulationSequence:
    """
    A sequence of simulations
    """

    def __init__(self, config):
        """
        Initialize sequence properties
        """
        (
            self.vehicle_counts,
            self.request_rates,
            self.inhomogeneities,
            self.commissions,
        ) = sequence_values(config)
        # Create lists to hold the sequence plot data
        self.trip_wait_fraction = []
        self.vehicle_p1_fraction = []
        self.vehicle_p2_fraction = []
        self.vehicle_p3_fraction = []
        self.mean_vehicle_count = []
        self.forward_dispatch_fraction = []
        self.frame_count = (
            len(self.vehicle_counts)
            * len(self.request_rates)
            * len(self.inhomogeneities)
            * len(self.commissions)
        )
        # Set the dispatch_method to a string holding the method
        self.dispatch_method = config.dispatch_method.value.value

    def parameters(self):
        """Each simulation's parameters, in order (see sequence_parameters)."""
        return sequence_parameters(
            self.vehicle_counts,
            self.request_rates,
            self.inhomogeneities,
            self.commissions,
        )

    def run_sequence(self, config):
        """
        Loop through the sequence of simulations.

        With no animation, each simulation runs with run_sequence set, so with
        -o each one adds a row of end-state measures to the sequence's CSV
        file. The text animation prints each block, so its simulations run
        without run_sequence (next_block then returns the state) and without
        output files or [RESULTS].
        """
        if config.animation.value == Animation.NONE:
            for (
                request_rate,
                vehicle_count,
                inhomogeneity,
                commission,
            ) in self.parameters():
                self._next_sim(
                    request_rate=request_rate,
                    vehicle_count=vehicle_count,
                    inhomogeneity=inhomogeneity,
                    commission=commission,
                    config=config,
                )
        elif config.animation.value == Animation.TEXT:
            # Text output, one line per simulation
            from ridehail.animation.text import TextAnimation

            for (
                request_rate,
                vehicle_count,
                inhomogeneity,
                commission,
            ) in self.parameters():
                runconfig = copy.deepcopy(config)
                runconfig.base_demand.value = request_rate
                runconfig.vehicle_count.value = vehicle_count
                runconfig.inhomogeneity.value = inhomogeneity
                runconfig.platform_commission.value = commission
                runconfig.run_sequence.value = False
                runconfig.config_file.value = None
                sim = RideHailSimulation(runconfig)
                text_animation = TextAnimation(
                    sim, print_results_table=False, enable_keyboard=False
                )
                self._collect_sim_results(text_animation.animate())
        elif config.animation.value == Animation.SEQUENCE:
            # Use matplotlib sequence animation
            try:
                from ridehail.animation.sequence_animation import SequenceAnimation

                # Create simulation instance for the animation
                # (required by SequenceAnimation)
                # Use the base config but disable sequence mode to avoid infinite recursion
                sim_config = copy.deepcopy(config)
                sim_config.animation.value = Animation.NONE

                # Create a simulation instance (needed for SequenceAnimation interface)
                base_sim = RideHailSimulation(sim_config)

                # Create sequence animation instance
                sequence_animation = SequenceAnimation(base_sim, self)
                sequence_animation.animate()

            except ImportError:
                logging.error(
                    "Matplotlib sequence animation not available. "
                    "Please install matplotlib and scipy dependencies."
                )
        elif config.animation.value == Animation.TERMINAL_SEQUENCE:
            # Use textual-based sequence animation instead of matplotlib
            try:
                from ridehail.animation.terminal_sequence import (
                    TextualSequenceAnimation,
                )

                # Create a simulation instance for the animation
                # (required by TextualSequenceAnimation)
                # Use the base config but disable sequence mode to avoid infinite recursion
                sim_config = copy.deepcopy(config)
                sim_config.animation.value = Animation.NONE

                # Create a simulation instance (needed for TextualSequenceAnimation interface)
                base_sim = RideHailSimulation(sim_config)

                # Create and run the textual sequence animation
                textual_animation = TextualSequenceAnimation(base_sim)
                textual_animation.animate()

            except ImportError:
                logging.warning(
                    "Textual sequence animation not available, "
                    "falling back to matplotlib sequence"
                )
                # Fall back to matplotlib sequence animation
                config.animation.value = Animation.SEQUENCE
                self.run_sequence(config)  # Recursive call with matplotlib sequence
                return
        else:
            logging.error(
                f"\n\tThe 'animation' configuration parameter "
                f"in the [ANIMATION] section of"
                f"\n\tthe configuration file is set to "
                f"'{config.animation.value}'."
                f"\n\n\tTo run a sequence, set this to either "
                f"'{Animation.SEQUENCE.value}', "
                f"'{Animation.TERMINAL_SEQUENCE.value}', "
                f"'{Animation.TEXT.value}', "
                f"or '{Animation.NONE.value}'."
                f"\n\t(A setting of "
                f"'{Animation.STATS.value}' may be the "
                "result of a typo)."
            )

    def _collect_sim_results(self, results):
        """
        After a simulation, collect the results for plotting etc
        """
        end_state = results.get_end_state()
        self.vehicle_p1_fraction.append(end_state["vehicles"]["fraction_p1"])
        self.vehicle_p2_fraction.append(end_state["vehicles"]["fraction_p2"])
        self.vehicle_p3_fraction.append(end_state["vehicles"]["fraction_p3"])
        self.mean_vehicle_count.append(end_state["vehicles"]["mean_count"])
        self.trip_wait_fraction.append(end_state["trips"]["mean_wait_fraction_total"])
        if self.dispatch_method == DispatchMethod.FORWARD_DISPATCH.value:
            self.forward_dispatch_fraction.append(
                end_state["trips"]["forward_dispatch_fraction"]
            )

    def _next_sim(
        self,
        index=None,
        request_rate=None,
        vehicle_count=None,
        inhomogeneity=None,
        commission=None,
        config=None,
    ):
        """
        Run a single simulation
        """
        # If called from animation, we are looping over a single variable.
        # Compute the value of that variable from the index.
        if request_rate is None:
            request_rate_index = index % len(self.request_rates)
            request_rate = self.request_rates[request_rate_index]
        if vehicle_count is None:
            vehicle_count_index = index % len(self.vehicle_counts)
            vehicle_count = self.vehicle_counts[vehicle_count_index]
        if inhomogeneity is None:
            inhomogeneity_index = index % len(self.inhomogeneities)
            inhomogeneity = self.inhomogeneities[inhomogeneity_index]
        if commission is None:
            commission_index = index % len(self.commissions)
            commission = self.commissions[commission_index]
        # Set configuration parameters
        # For now, say we can't draw simulation-level plots
        # if we are running a sequence
        runconfig = copy.deepcopy(config)
        runconfig.animation.value = Animation.NONE
        runconfig.base_demand.value = request_rate
        runconfig.vehicle_count.value = vehicle_count
        runconfig.inhomogeneity.value = inhomogeneity
        runconfig.platform_commission.value = commission
        sim = RideHailSimulation(runconfig)
        results = sim.simulate()
        self._collect_sim_results(results)
        logging.info(
            "Simulation completed"
            f": Nv={vehicle_count:d}"
            f", R={request_rate:.02f}"
            f", I={inhomogeneity:.02f}"
            f", m={commission:.02f}"
            f", p1={self.vehicle_p1_fraction[-1]:.02f}"
            f", p2={self.vehicle_p2_fraction[-1]:.02f}"
            f", p3={self.vehicle_p3_fraction[-1]:.02f}"
            f", mvc={self.mean_vehicle_count[-1]:.02f}"
            f", w={self.trip_wait_fraction[-1]:.02f}"
        )
        return results
