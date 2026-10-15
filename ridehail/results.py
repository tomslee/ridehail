"""
The results of a simulation: the final state, averaged over the last
results_window blocks.

One layout (RESULTS_LAYOUT) says which results are reported, in which
section, in what order, rounded how, in what units, and when they are
relevant. Every presentation is built from it:

- the end state (get_end_state): the text animation's table, the JSONL
  end_state record and the sequence CSV row;
- the [RESULTS] section of the config file (format_results_section), which
  the web lab also uses for its downloads (worker.py).

A result is reported only where it is relevant, as the config sections make
it relevant: forward dispatch with use_advanced_dispatch, the strategy
section with use_strategy, and so on. Add new results to the layout only.
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Callable, Optional
import logging

from ridehail.atom import DispatchMethod, History, Measure
from ridehail.measures import compute_measures

# Units of each kind of result: (with use_city_scale, without)
UNITS = {
    "time": ("minutes", "blocks"),
    "rate": ("per minute", "per block"),
    "price": ("per minute", "per block"),
    "income": ("per hour", "per block"),
}


@dataclass(frozen=True)
class ResultRow:
    """
    One result. key names it in the end state; name names it in [RESULTS],
    and is the key of the section's values (a Measure name for the core's
    results). decimals None reports the value as it is.
    """

    key: str
    name: str
    decimals: Optional[int] = 3
    unit: Optional[str] = None
    relevant: Optional[Callable] = None


@dataclass(frozen=True)
class ResultSection:
    """
    A group of results. values(results) gives the section's values, keyed by
    row name; relevant(results) says whether to report the section at all.
    units names the rows of each unit kind, for the [RESULTS] comment.
    """

    key: str
    title: str
    rows: tuple
    values: Callable
    relevant: Optional[Callable] = None
    units: tuple = ()


def _can_park(results):
    """Whether any car can park while idle (idle_vehicles_moving below 1)."""
    sim = results.sim
    return sim.idle_vehicles_moving < 1 or any(
        vehicle.idle_vehicles_moving < 1 for vehicle in sim.vehicles
    )


def _cancels(results):
    """Whether trips can be cancelled (max_wait_time)."""
    return bool(results.sim.max_wait_time)


def _forward_dispatch(results):
    """The simulation forces the default method without use_advanced_dispatch."""
    return results.sim.dispatch_method == DispatchMethod.FORWARD_DISPATCH


def _measures(results):
    return results.measures


def _strategy(results):
    summary = results.sim.strategy_controller.summary()
    return {f"STRATEGY_{key.upper()}": value for key, value in summary.items()}


def _row(key, measure, **kwargs):
    return ResultRow(key, measure.name, **kwargs)


RESULTS_LAYOUT = (
    ResultSection(
        "simulation",
        "Simulation",
        (
            _row("blocks_simulated", Measure.SIM_BLOCKS_SIMULATED, decimals=None),
            _row("blocks_analyzed", Measure.SIM_BLOCKS_ANALYZED, decimals=None),
        ),
        _measures,
    ),
    ResultSection(
        "vehicles",
        "Vehicles",
        (
            _row("mean_count", Measure.VEHICLE_MEAN_COUNT),
            _row("fraction_p1", Measure.VEHICLE_FRACTION_P1),
            _row("fraction_p2", Measure.VEHICLE_FRACTION_P2),
            _row("fraction_p3", Measure.VEHICLE_FRACTION_P3),
            _row(
                "fraction_parked", Measure.VEHICLE_FRACTION_PARKED, relevant=_can_park
            ),
            _row("median_p1", Measure.VEHICLE_MEDIAN_P1),
            _row("median_p2", Measure.VEHICLE_MEDIAN_P2),
            _row("median_p3", Measure.VEHICLE_MEDIAN_P3),
        ),
        _measures,
    ),
    ResultSection(
        "trips",
        "Trips",
        (
            _row("mean_request_rate", Measure.TRIP_MEAN_REQUEST_RATE, unit="rate"),
            _row("mean_wait_time", Measure.TRIP_MEAN_WAIT_TIME, unit="time"),
            _row("mean_ride_time", Measure.TRIP_MEAN_RIDE_TIME, unit="time"),
            _row("mean_wait_fraction_total", Measure.TRIP_MEAN_WAIT_FRACTION_TOTAL),
            _row("median_wait_time", Measure.TRIP_MEDIAN_WAIT_TIME, unit="time"),
            _row(
                "median_wait_fraction_total",
                Measure.TRIP_MEDIAN_WAIT_FRACTION_TOTAL,
            ),
            _row(
                "completed_fraction",
                Measure.TRIP_COMPLETED_FRACTION,
                relevant=_cancels,
            ),
        ),
        _measures,
        units=(("rate", "request rate"), ("time", "times")),
    ),
    ResultSection(
        "dispatch",
        "Dispatch",
        (
            _row(
                "forward_dispatch_fraction",
                Measure.TRIP_FORWARD_DISPATCH_FRACTION,
            ),
        ),
        _measures,
        relevant=_forward_dispatch,
    ),
    ResultSection(
        "income_and_costs",
        "Income and costs: the platform's in total, the rest per vehicle",
        (
            _row("gross_income", Measure.VEHICLE_GROSS_INCOME, unit="income"),
            _row("net_income", Measure.VEHICLE_NET_INCOME, unit="income"),
            _row("surplus", Measure.VEHICLE_MEAN_SURPLUS, unit="income"),
            _row("mean_price", Measure.TRIP_MEAN_PRICE, unit="price"),
            ResultRow(
                "platform_total_income",
                "PLATFORM_TOTAL_INCOME",
                unit="income",
            ),
        ),
        lambda results: results.measures
        | {
            "PLATFORM_TOTAL_INCOME": results.measures[Measure.PLATFORM_MEAN_INCOME.name]
        },
        units=(("income", "incomes"), ("price", "price")),
    ),
    ResultSection(
        "validation",
        "Validation: checks should be close to 1, the residual close to 0",
        (
            _row("check_np3_over_rl", Measure.SIM_CHECK_NP3_OVER_RL),
            _row("check_np2_over_rw", Measure.SIM_CHECK_NP2_OVER_RW),
            _row("check_p1_p2_p3", Measure.SIM_CHECK_P1_P2_P3),
            _row("max_rms_residual", Measure.SIM_CONVERGENCE_MAX_RMS_RESIDUAL),
        ),
        _measures,
    ),
    ResultSection(
        "strategy",
        "The seated car's strategy over the shift, to compare with the fleet",
        tuple(
            ResultRow(key, f"STRATEGY_{key.upper()}", **kwargs)
            for key, kwargs in (
                ("fraction_p1", {}),
                ("fraction_p2", {}),
                ("fraction_p3", {}),
                ("fraction_parked", {"relevant": _can_park}),
                ("gross_income", {"unit": "income"}),
                ("net_income", {"unit": "income"}),
                ("surplus", {"unit": "income"}),
                ("offers", {"decimals": None}),
                ("accepts", {"decimals": None}),
                ("idle_per_accept", {"unit": "time"}),
            )
        ),
        _strategy,
        relevant=lambda results: results.sim.strategy_controller is not None,
        units=(("income", "incomes"), ("time", "idle_per_accept")),
    ),
)


def _rounded(value, decimals):
    if value is None or decimals is None:
        return value
    return round(float(value), decimals)


class RideHailSimulationResults:
    """
    The results of a RideHailSimulation, as of its current block.
    """

    def __init__(self, sim):
        self.sim = sim
        self._measures = None

    @property
    def measures(self):
        """get_result_measures(), computed once."""
        if self._measures is None:
            self._measures = self.get_result_measures()
        return self._measures

    def available(self):
        """
        Results need a full results_window of blocks, and a block before it
        (time_blocks greater than results_window, as sequences and
        use_strategy require).
        """
        return self.sim.block_index > self.sim.results_window

    def unit_label(self, unit):
        """A unit kind (UNITS) as a label, e.g. "minutes"; "" for none."""
        if unit is None:
            return ""
        return UNITS[unit][0 if self.sim.use_city_scale else 1]

    def sections(self):
        """
        The relevant sections, each as (section, [(row, value), ...]),
        values rounded as the layout says. Empty if results are not
        available.
        """
        if not self.available():
            return []
        reported = []
        for section in RESULTS_LAYOUT:
            if section.relevant and not section.relevant(self):
                continue
            values = section.values(self)
            rows = [
                (row, _rounded(values.get(row.name), row.decimals))
                for row in section.rows
                if not row.relevant or row.relevant(self)
            ]
            reported.append((section, rows))
        return reported

    def get_result_measures(self, timestamp=None, duration_seconds=None):
        """
        The final state measures, averaged over the last results_window
        blocks of the simulation, keyed by Measure name, with SIM_TIMESTAMP,
        SIM_RIDEHAIL_VERSION and (if given) SIM_DURATION_SECONDS.

        Use strings for keys instead of enums as this needs to be callable from
        outside environments.

        The shared computation (identical to RideHailSimulation._update_measures(),
        aside from which History buffer/window is used) lives in
        ridehail.measures.compute_measures().
        """
        # check for case where results_window is bigger than time_blocks
        block_index = self.sim.block_index
        block_lower_bound = max((block_index - self.sim.results_window), 0)
        window = block_index - block_lower_bound
        measures = compute_measures(self.sim, self.sim.history_results, window)
        # Simulation checks
        measures[Measure.SIM_CONVERGENCE_MAX_RMS_RESIDUAL.name] = (
            self.sim.history_results[History.SIM_CONVERGENCE_MAX_RMS_RESIDUAL].sum
            / window
        )
        # These simulation checks rely only on measures, not history values.
        # With use_city_scale the rate is per minute and the times are in
        # minutes, so the units cancel as they do in blocks.
        # Guard against division by zero when there are no trips or zero times
        denominator_p3 = (
            measures[Measure.TRIP_MEAN_REQUEST_RATE.name]
            * measures[Measure.TRIP_MEAN_RIDE_TIME.name]
        )
        measures[Measure.SIM_CHECK_NP3_OVER_RL.name] = (
            measures[Measure.VEHICLE_MEAN_COUNT.name]
            * measures[Measure.VEHICLE_FRACTION_P3.name]
            / denominator_p3
            if denominator_p3 > 0
            else 0.0
        )

        denominator_p2 = (
            measures[Measure.TRIP_MEAN_REQUEST_RATE.name]
            * measures[Measure.TRIP_MEAN_WAIT_TIME.name]
        )
        measures[Measure.SIM_CHECK_NP2_OVER_RW.name] = (
            measures[Measure.VEHICLE_MEAN_COUNT.name]
            * measures[Measure.VEHICLE_FRACTION_P2.name]
            / denominator_p2
            if denominator_p2 > 0
            else 0.0
        )
        measures[Measure.SIM_CHECK_P1_P2_P3.name] = (
            measures[Measure.VEHICLE_FRACTION_P1.name]
            + measures[Measure.VEHICLE_FRACTION_P2.name]
            + measures[Measure.VEHICLE_FRACTION_P3.name]
        )
        measures[Measure.SIM_BLOCKS_SIMULATED.name] = block_index
        measures[Measure.SIM_BLOCKS_ANALYZED.name] = window
        # Add version and other extra items using literal keys
        # Add timestamp (use provided or generate now)
        if timestamp:
            measures["SIM_TIMESTAMP"] = timestamp
        else:
            measures["SIM_TIMESTAMP"] = datetime.now().isoformat()

        measures["SIM_RIDEHAIL_VERSION"] = self.sim.config.version.value

        # Add duration if provided
        if duration_seconds is not None:
            measures["SIM_DURATION_SECONDS"] = round(duration_seconds, 2)
        return measures

    def get_end_state(self):
        """
        The results as {section: {key: value}}: the text animation's table,
        the JSONL end_state record and (flattened) the sequence CSV row.
        Empty, with a warning, if results are not available.
        """
        if not self.available():
            logging.warning(
                f"{self.sim.block_index} blocks run, not more than "
                f"results_window ({self.sim.results_window}): no results."
            )
            return {}
        return {
            section.key: {row.key: value for row, value in rows}
            for section, rows in self.sections()
        }

    def format_results_section(self, timestamp=None, duration_seconds=None):
        """
        The results as the [RESULTS] section of a config file, keyed by row
        name (mostly Measure names). Empty if results are not available.
        """
        if not self.available():
            return ""
        measures = self.get_result_measures(
            timestamp=timestamp, duration_seconds=duration_seconds
        )
        self._measures = measures
        comment_line = "# " + "-" * 76 + "\n"
        lines = [
            "[RESULTS]\n\n",
            comment_line,
            "# Simulation Results\n",
            f"# Generated: {measures['SIM_TIMESTAMP']}\n",
            "# This section is automatically generated and will be overwritten "
            "on each run\n",
            "# Do not manually edit this section\n",
            "#\n",
            "# If configuration parameters in this file were overwritten by "
            "command-line\n",
            "# options or interactively, the results will not be reproducible.\n",
            comment_line,
            "\n",
        ]
        for section, rows in self.sections():
            title = section.title
            notes = []
            for unit, noun in section.units:
                if any(row.unit == unit for row, _ in rows):
                    label = self.unit_label(unit)
                    notes.append(
                        f"{noun} in {label}" if unit == "time" else f"{noun} {label}"
                    )
            if notes:
                title += f" ({'; '.join(notes)})"
            lines.append(f"# {title}\n")
            if section.key == "simulation":
                for name in (
                    "SIM_TIMESTAMP",
                    "SIM_RIDEHAIL_VERSION",
                    "SIM_DURATION_SECONDS",
                ):
                    if name in measures:
                        lines.append(f"{name} = {measures[name]}\n")
            for row, value in rows:
                if value is not None and row.decimals is not None:
                    value = f"{value:.{row.decimals}f}"
                lines.append(f"{row.name} = {value}\n")
            lines.append("\n")
            if section.key == "simulation":
                lines.append(
                    "# The results below are averages over the blocks analyzed\n\n"
                )
        return "".join(lines)
