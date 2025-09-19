"""
Base animation class and shared utilities for ridehail animations.
"""
import logging
import enum
import numpy as np
import sys
import seaborn as sns

from ridehail.atom import Animation, Measure
from ridehail.dispatch import Dispatch


class HistogramArray(enum.Enum):
    HIST_TRIP_WAIT_TIME = "Wait time"
    HIST_TRIP_DISTANCE = "Trip distance"


class RideHailAnimation:
    """Base class for all ridehail animations"""

    __all__ = ["RideHailAnimation"]
    _ROADWIDTH_BASE = 60.0
    _FRAME_INTERVAL = 50
    _FRAME_COUNT_UPPER_LIMIT = 99999
    _DISPLAY_FRINGE = 0.25

    def __init__(self, sim):
        self.sim = sim
        self.title = sim.config.title.value
        self.animation_style = sim.config.animation_style.value
        self.animate_update_period = sim.config.animate_update_period.value
        self.interpolation_points = sim.interpolate
        self.annotation = sim.config.annotation.value
        self.smoothing_window = sim.config.smoothing_window.value
        self.animation_output_file = sim.config.animation_output_file.value
        self.time_blocks = sim.config.time_blocks.value
        self.frame_index = 0
        self.display_fringe = self._DISPLAY_FRINGE
        self.color_palette = sns.color_palette()
        self.current_interpolation_points = self.interpolation_points
        self.pause_plot = False
        self.axes = []
        self.in_jupyter = False
        self.plot_arrays = {}
        for plot_array in list(Measure):
            self.plot_arrays[plot_array] = np.zeros(sim.time_blocks + 1)
        self.histograms = {}
        for histogram in list(HistogramArray):
            self.histograms[histogram] = np.zeros(sim.city.city_size + 1)
        self.plotstat_list = []
        self.changed_plotstat_flag = False
        self.state_dict = {}
        self.dispatch = Dispatch(sim.dispatch_method, sim.forward_dispatch_bias)

    def _on_key_press(self, event):
        """Respond to shortcut keys"""
        logging.info(f"key pressed: {event.key}")
        sys.stdout.flush()
        if event.key == "N":
            self.sim.target_state["vehicle_count"] += 1
        elif event.key == "n":
            self.sim.target_state["vehicle_count"] = max(
                (self.sim.target_state["vehicle_count"] - 1), 0
            )
        elif event.key == "ctrl+N":
            self.sim.target_state["vehicle_count"] += 10
        elif event.key == "ctrl+n":
            self.sim.target_state["vehicle_count"] = max(
                (self.sim.target_state["vehicle_count"] - 10), 0
            )
        elif event.key == "K":
            self.sim.target_state["base_demand"] = (
                self.sim.target_state["base_demand"] + 0.1
            )
        elif event.key == "k":
            self.sim.target_state["base_demand"] = max(
                (self.sim.target_state["base_demand"] - 0.1), 0
            )
        elif event.key == "v":
            # Only apply if the map is being displayed
            if self.animation_style in (Animation.ALL, Animation.MAP, Animation.TERMINAL_MAP):
                self.interpolation_points = max(
                    self.current_interpolation_points + 1, 0
                )
        elif event.key == "V":
            if self.animation_style in (Animation.ALL, Animation.MAP, Animation.TERMINAL_MAP):
                self.interpolation_points = max(
                    self.current_interpolation_points - 1, 0
                )
        elif event.key == "c":
            self.sim.target_state["city_size"] = max(
                self.sim.target_state["city_size"] - 1, 2
            )
        elif event.key == "C":
            self.sim.target_state["city_size"] = max(
                self.sim.target_state["city_size"] + 1, 2
            )
        elif event.key in ("escape", " "):
            self.pause_plot ^= True

    def _on_click(self, event):
        self.pause_plot ^= True