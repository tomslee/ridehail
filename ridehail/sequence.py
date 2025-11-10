"""
Control a sequence of simulations
"""

import logging
import copy
from ridehail.simulation import RideHailSimulation
from ridehail.atom import Animation, DispatchMethod


class RideHailSimulationSequence:
    """
    A sequence of simulations
    """

    def __init__(self, config):
        """
        Initialize sequence properties
        """
        self.vehicle_counts = [config.vehicle_count.value]
        self.request_rates = [config.base_demand.value]
        self.inhomogeneities = [config.inhomogeneity.value]
        self.reservation_wage = [config.reservation_wage.value]
        self.commissions = [config.platform_commission.value]
        self.prices = [config.price.value]
        if config.vehicle_count_increment.value and config.vehicle_count_max.value:
            self.vehicle_counts = [
                x
                for x in range(
                    config.vehicle_count.value,
                    config.vehicle_count_max.value + 1,
                    config.vehicle_count_increment.value,
                )
            ]
        if config.request_rate_increment.value and config.request_rate_max.value:
            # request rates managed to two decimal places
            self.request_rates = [
                x * 0.01
                for x in range(
                    int(100 * config.base_demand.value),
                    int(100 * (config.request_rate_max.value + 1)),
                    int(100 * config.request_rate_increment.value),
                )
            ]
        if config.inhomogeneity_increment.value and config.inhomogeneity_max.value:
            # inhomogeneities managed to two decimal places
            self.inhomogeneities = [
                x * 0.01
                for x in range(
                    int(100 * config.inhomogeneity.value),
                    int(100 * (config.inhomogeneity_max.value) + 1),
                    int(100 * config.inhomogeneity_increment.value),
                )
            ]
        if config.commission_increment.value and config.commission_max.value:
            # commissions managed to two decimal places
            self.commissions = [
                x * 0.01
                for x in range(
                    int(100 * config.platform_commission.value),
                    int(100 * (config.commission_max.value + 0.01)),
                    int(100 * config.commission_increment.value),
                )
            ]
        # Check if this is a valid sequence
        # Horribly inelegant at the moment
        # test_sequence = (
        # len(self.request_rates),
        # len(self.vehicle_counts),
        # len(self.inhomogeneities),
        # )
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
        self.plot_count = 1

    def run_sequence(self, config):
        """
        Loop through the sequence of simulations.
        """
        # output_file_handle = open(f"{config.jsonl_file}", 'a')
        # output_file_handle.write(
        # json.dumps(rh_config.WritableConfig(config).__dict__) + "\n")
        # output_file_handle.close()
        if config.animation.value == Animation.NONE:
            # Iterate over models
            for request_rate in self.request_rates:
                for vehicle_count in self.vehicle_counts:
                    for inhomogeneity in self.inhomogeneities:
                        for commission in self.commissions:
                            self._next_sim(
                                request_rate=request_rate,
                                vehicle_count=vehicle_count,
                                inhomogeneity=inhomogeneity,
                                commission=commission,
                                config=config,
                            )
        elif config.animation.value == Animation.TEXT:
            # Iterate over models with text output (one line per simulation)
            from ridehail.atom import Measure

            for request_rate in self.request_rates:
                for vehicle_count in self.vehicle_counts:
                    for inhomogeneity in self.inhomogeneities:
                        for commission in self.commissions:
                            # Create config for this simulation
                            runconfig = copy.deepcopy(config)
                            runconfig.base_demand.value = request_rate
                            runconfig.vehicle_count.value = vehicle_count
                            runconfig.inhomogeneity.value = inhomogeneity
                            runconfig.platform_commission.value = commission
                            # Individual simulations in sequence should not have run_sequence set
                            runconfig.run_sequence.value = False
                            # Prevent config file writing for individual simulations in sequence
                            runconfig.config_file.value = None

                            # Create and run simulation without keyboard handling
                            sim = RideHailSimulation(runconfig)

                            # Run simulation blocks with text output
                            for block in range(sim.time_blocks):
                                state_dict = sim.next_block(block=block)

                                # Print current state (overwrite with \r during simulation)
                                s = (
                                    f"block {block:5d}: "
                                    f"cs={sim.city_size:3d}, "
                                    f"vc={vehicle_count:3d}, "
                                    f"N={state_dict[Measure.VEHICLE_MEAN_COUNT.name]:.2f}, "
                                    f"R={state_dict[Measure.TRIP_MEAN_REQUEST_RATE.name]:.2f}, "
                                    f"P1={state_dict[Measure.VEHICLE_FRACTION_P1.name]:.2f}, "
                                    f"P2={state_dict[Measure.VEHICLE_FRACTION_P2.name]:.2f}, "
                                    f"P3={state_dict[Measure.VEHICLE_FRACTION_P3.name]:.2f}, "
                                    f"W={state_dict[Measure.TRIP_MEAN_WAIT_FRACTION.name]:.2f}, "
                                    f"rmsr={state_dict[Measure.SIM_CONVERGENCE_MAX_RMS_RESIDUAL.name]:.3f}"
                                )
                                print(f"{s}", end="\r", flush=True)

                            # Print newline to finalize this simulation's output
                            print()

                            # Get results and collect for sequence tracking
                            from ridehail.simulation_results import RideHailSimulationResults

                            results = RideHailSimulationResults(sim)
                            self._collect_sim_results(results)
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

            # config_file_root = path.splitext(path.split(config.config_file.value)[1])[0]
            # fig.savefig(f"./img/{config_file_root}" f"-{config.start_time}.png")
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
            # print(f"index={index}, len={len(self.commissions)}")
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
        s = (
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
