"""
Convergence tracking for ridehail simulations using Gelman-Rubin R-hat statistic.

The Gelman-Rubin diagnostic compares variance within simulation segments (chains)
to variance between segments. R-hat values near 1.0 indicate convergence to
steady state.
"""

import numpy as np
from ridehail.atom import History


class ConvergenceTracker:
    """
    Track convergence to steady state using Gelman-Rubin R-hat statistic.

    Splits simulation history into multiple chains and compares variance
    within chains to variance between chains. R-hat near 1.0 indicates
    convergence to steady state.
    """

    def __init__(self, n_chains=4, chain_length=50, convergence_threshold=1.1):
        """
        Args:
            n_chains: Number of chains to split history into (default 4)
            chain_length: Length of each chain in blocks (default 50)
            convergence_threshold: R-hat threshold for convergence (default 1.1)
        """
        self.n_chains = n_chains
        self.chain_length = chain_length
        self.convergence_threshold = convergence_threshold
        self.total_length = n_chains * chain_length

        # Track most recent R-hat values
        self.current_rhat_values = {}
        self.max_rhat = None
        self.worst_metric = None
        self.is_converged = False

    def compute_rhat(self, history_buffer):
        """
        Compute Gelman-Rubin R-hat statistic for a single metric.

        Args:
            history_buffer: CircularBuffer containing metric history

        Returns:
            R-hat value (float), or None if insufficient data
        """
        # Extract data from circular buffer
        data = history_buffer._rec_queue
        buffer_length = len(data)

        # Need at least total_length observations
        if buffer_length < self.total_length:
            return None

        # Extract the most recent total_length observations
        # Handle circular buffer properly
        tail = history_buffer._queue_tail

        # Extract in order from oldest to newest
        indices = [(tail + 1 + i) % buffer_length for i in range(self.total_length)]
        recent_data = data[indices]

        # Split into chains
        chains = recent_data.reshape(self.n_chains, self.chain_length)

        # Compute chain means and overall mean
        chain_means = np.mean(chains, axis=1)  # Mean of each chain
        overall_mean = np.mean(chain_means)  # Mean of chain means

        # Between-chain variance (B)
        B = self.chain_length * np.var(chain_means, ddof=1)

        # Within-chain variance (W)
        chain_variances = np.var(chains, axis=1, ddof=1)
        W = np.mean(chain_variances)

        # Estimated variance of parameter
        var_plus = ((self.chain_length - 1) / self.chain_length) * W + (
            1 / self.chain_length
        ) * B

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

        return rhat

    def compute_multivariate_rhat(self, history_buffers, metrics_to_track):
        """
        Compute R-hat for multiple metrics.

        Args:
            history_buffers: Dict of History -> CircularBuffer
            metrics_to_track: List of History enum values to track

        Returns:
            Dict of {metric_name: rhat_value}
        """
        rhat_values = {}
        for metric in metrics_to_track:
            if metric in history_buffers:
                rhat = self.compute_rhat(history_buffers[metric])
                if rhat is not None:
                    rhat_values[metric.name] = rhat

        # Update internal state
        self.current_rhat_values = rhat_values
        if rhat_values:
            self.max_rhat = max(rhat_values.values())
            self.worst_metric = max(rhat_values, key=rhat_values.get)
            self.is_converged = self.max_rhat < self.convergence_threshold
        else:
            self.max_rhat = None
            self.worst_metric = None
            self.is_converged = False

        return rhat_values

    def check_convergence(self):
        """
        Check if all tracked metrics have converged based on most recent computation.

        Returns:
            Tuple of (converged: bool, max_rhat: float, worst_metric: str)
        """
        return self.is_converged, self.max_rhat, self.worst_metric

    def get_convergence_summary(self):
        """
        Get a summary dict of current convergence state.

        Returns:
            Dict with convergence status and R-hat values
        """
        return {
            "converged": self.is_converged,
            "max_rhat": round(self.max_rhat, 4) if self.max_rhat is not None else None,
            "worst_metric": self.worst_metric,
            "rhat_values": {
                k: round(v, 4) for k, v in self.current_rhat_values.items()
            },
        }


# Default metrics to track for convergence
DEFAULT_CONVERGENCE_METRICS = [
    History.VEHICLE_TIME_P1,
    History.VEHICLE_TIME_P2,
    History.VEHICLE_TIME_P3,
    History.TRIP_WAIT_TIME,
    History.TRIP_DISTANCE,
]
