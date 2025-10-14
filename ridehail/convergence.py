"""
Convergence tracking for ridehail simulations using Gelman-Rubin R-hat statistic.

The Gelman-Rubin diagnostic compares variance within simulation segments (chains)
to variance between segments. R-hat values near 1.0 indicate convergence to
steady state.
"""

import logging
import numpy as np
from ridehail.atom import Measure, CircularBuffer


# Default metrics to track for convergence
DEFAULT_CONVERGENCE_METRICS = [
    Measure.VEHICLE_MEAN_COUNT,
    Measure.VEHICLE_FRACTION_P1,
    Measure.VEHICLE_FRACTION_P2,
    Measure.VEHICLE_FRACTION_P3,
    Measure.TRIP_MEAN_WAIT_FRACTION,
]
DEFAULT_CONVERGENCE_THRESHOLD = 0.02
DEFAULT_CONVERGENCE_WINDOWS = 3


class ConvergenceTracker:
    """
    Track convergence to steady state using Gelman-Rubin R-hat statistic.

    Splits simulation history into multiple chains and compares variance
    within chains to variance between chains. R-hat near 1.0 indicates
    convergence to steady state.
    """

    def __init__(
        self,
        metrics_to_track=DEFAULT_CONVERGENCE_METRICS,
        chain_length=50,
        convergence_threshold=DEFAULT_CONVERGENCE_THRESHOLD,
        convergence_windows=DEFAULT_CONVERGENCE_WINDOWS,
    ):
        """
        Args:
            n_chains: Number of chains to split history into (default 4)
            chain_length: Length of each chain in blocks (default 50)
            convergence_threshold: R-hat threshold for convergence (default 1.1)
        """
        self.metrics_to_track = metrics_to_track
        self.n_chains = len(metrics_to_track)
        self.chain_length = chain_length
        self.convergence_threshold = convergence_threshold
        self.convergence_windows = convergence_windows
        self.total_length = self.n_chains * chain_length
        self.measures = {}
        for metric in self.metrics_to_track:
            self.measures[metric.name] = CircularBuffer(self.chain_length)
        self.rms_residual_max = 0.0
        self.rms_residual_max_metric = DEFAULT_CONVERGENCE_METRICS[0]
        # Track most recent R-hat values
        self.sequential_windows_below_threshold = 0
        self.is_converged = False

    def push_measures(self, measure):
        for metric in self.metrics_to_track:
            self.measures[metric.name].push(measure[metric.name])

    def max_rms_residual(self, block):
        """
        Track convergence by comparing variance for each measure over the
        last self.chain_length blocks, and reporting the largest.
        The measures are expressed as fractions (of the sum) so that
        they fit on the same scale.

        Only recompute every chain_length
        """
        if block % self.chain_length == 0 and block > self.chain_length:
            chains_list = []
            for metric in self.metrics_to_track:
                chains_list.append(self.measures[metric.name]._rec_queue)
            chains = np.array(chains_list)
            for index, metric in enumerate(self.metrics_to_track):
                chains[index] = (
                    self.chain_length * chains[index] / self.measures[metric.name].sum
                )
            chain_rmse = np.sqrt(np.var(chains, axis=1, ddof=1))
            self.rms_residual_max = np.max(chain_rmse)
            self.rms_residual_max_metric = DEFAULT_CONVERGENCE_METRICS[
                np.argmax(chain_rmse)
            ]
            self.check_convergence()
        return (self.rms_residual_max, self.rms_residual_max_metric, self.is_converged)

    def check_convergence(self):
        """
        Check if all tracked metrics have converged based on most recent computation.

        Returns:
            Tuple of (converged: bool, max_rhat: float)
        """
        if self.rms_residual_max < self.convergence_threshold:
            self.sequential_windows_below_threshold += 1
        else:
            # reset
            self.sequential_windows_below_threshold = 0
        if self.sequential_windows_below_threshold >= self.convergence_windows:
            self.is_converged = True
        else:
            self.is_converged = False
