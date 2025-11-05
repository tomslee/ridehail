"""
Base animation class and shared utilities for ridehail animations.
"""

import logging
import enum
import numpy as np
import sys

from ridehail.atom import Animation, Measure


def _get_color_palette():
    """
    Get color palette for animations.
    Tries to use seaborn if available, otherwise returns a default palette.
    """
    try:
        import seaborn as sns

        return sns.color_palette()
    except ImportError:
        # Default color palette (matplotlib tab10 colors) as fallback
        return [
            (0.12156862745098039, 0.4666666666666667, 0.7058823529411765),  # blue
            (1.0, 0.4980392156862745, 0.054901960784313725),  # orange
            (0.17254901960784313, 0.6274509803921569, 0.17254901960784313),  # green
            (0.8392156862745098, 0.15294117647058825, 0.1568627450980392),  # red
            (0.5803921568627451, 0.403921568627451, 0.7411764705882353),  # purple
            (0.5490196078431373, 0.33725490196078434, 0.29411764705882354),  # brown
            (0.8901960784313725, 0.4666666666666667, 0.7607843137254902),  # pink
            (0.4980392156862745, 0.4980392156862745, 0.4980392156862745),  # gray
            (0.7372549019607844, 0.7411764705882353, 0.13333333333333333),  # yellow
            (0.09019607843137255, 0.7450980392156863, 0.8117647058823529),  # cyan
        ]


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
        self.animation = sim.config.animation.value
        self.animate_update_period = sim.config.animate_update_period.value
        self.interpolation_points = sim.interpolate
        self.annotation = sim.config.annotation.value
        self.smoothing_window = sim.config.smoothing_window.value
        self.animation_output_file = sim.config.animation_output_file.value
        self.time_blocks = sim.config.time_blocks.value
        self.frame_index = 0
        self.display_fringe = self._DISPLAY_FRINGE
        self.color_palette = _get_color_palette()
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

    def _on_key_press(self, event):
        """Respond to shortcut keys"""
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
            if self.animation in (
                Animation.ALL,
                Animation.MAP,
                Animation.TERMINAL_MAP,
            ):
                self.interpolation_points = max(
                    self.current_interpolation_points + 1, 0
                )
        elif event.key == "V":
            if self.animation in (
                Animation.ALL,
                Animation.MAP,
                Animation.TERMINAL_MAP,
            ):
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
