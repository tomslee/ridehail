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
]


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
        convergence_threshold=1.1,
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
        self.total_length = self.n_chains * chain_length
        self.measures = {}
        for metric in self.metrics_to_track:
            self.measures[metric.name] = CircularBuffer(self.chain_length)

        # Track most recent R-hat values
        self.current_rhat_values = {}
        self.rhat = None
        self.is_converged = False

    def push_measures(self, measure):
        for metric in self.metrics_to_track:
            self.measures[metric.name].push(measure[metric.name])

    def compute_residual_rms(self):
        """
        Track convergence by comparing variance for each measure over the
        last self.chain_length blocks, and reporting the largest.
        The measures are expressed as fractions (of the sum) so that
        they fit on the same scale.
        """
        chains_list = []
        for metric in self.metrics_to_track:
            chains_list.append(self.measures[metric.name]._rec_queue)
        chains = np.array(chains_list)
        for index, metric in enumerate(self.metrics_to_track):
            chains[index] = (
                self.chain_length * chains[index] / self.measures[metric.name].sum
            )
        chain_rmse = np.sqrt(np.var(chains, axis=1, ddof=1))
        # logging.debug(
        # f"chain_rmse={chain_rmse}, chain_means={chain_means}, "
        # f"chains={chains}"
        # )
        rms_residual_max = np.max(chain_rmse)
        rms_residual_max_metric = DEFAULT_CONVERGENCE_METRICS[np.argmax(chain_rmse)]
        logging.debug(
            f"rms_residual_max={rms_residual_max}, metric={rms_residual_max_metric}"
        )
        return (rms_residual_max, rms_residual_max_metric)

    def compute_rhat(self):
        """
        Compute R-hat for multiple metrics.

        Args:
            history_buffers: Dict of History -> CircularBuffer
            metrics_to_track: List of History enum values to track

        Returns:
            Dict of {metric_name: rhat_value}
        """

        chains_list = []
        for metric in self.metrics_to_track:
            chains_list.append(self.measures[metric.name]._rec_queue)
            # rhat = self.compute_chain_rhat(history_buffers[metric])
            # if rhat is not None:
            # rhat_values[metric.name] = rhat
        chains = np.array(chains_list)
        chain_means = np.mean(chains, axis=1)  # Mean of each chain
        overall_mean = np.mean(chain_means)
        # logging.debug(f"chain_means={chain_means}")
        logging.debug(f"chain_means={chain_means}, overall_mean={overall_mean}")
        # Between-chain variance (B)
        L = self.chain_length
        B = L * np.var(chain_means, ddof=1)
        # Within-chain variances
        chain_variances = np.var(chains, axis=1, ddof=1)
        W = np.mean(chain_variances)

        # Estimated variance of parameter
        var_plus = ((L - 1) / L) * W + (1 / L) * B

        # Gelman-Rubin statistic
        if W > 0:
            rhat = np.sqrt(var_plus / W)
        else:
            # If within-chain variance is zero, all chains are constant
            # Check if they're the same constant
            if B == 0:
                rhat = 1.0  # Perfect convergence to same value
            else:
                rhat = None  # Degenerate case
        # Update internal state
        logging.debug(f"rhat={rhat}, L={L}, B={B}, W={W}, chain_means={chain_means}")
        return rhat

    def check_convergence(self):
        """
        Check if all tracked metrics have converged based on most recent computation.

        Returns:
            Tuple of (converged: bool, max_rhat: float)
        """
        return self.is_converged, self.rhat
