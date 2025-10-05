"""
Textual-based map animation for ridehail simulation - simplified map-only version.
"""

import logging
import sys
import time
from textual.app import ComposeResult
from textual.widgets import (
    Header,
    Footer,
    Static,
)
from textual.widget import Widget
from textual.geometry import Offset
from rich.console import RenderResult

from .textual_base import TextualBasedAnimation, RidehailTextualApp


# Fast epsilon for floating point comparisons (more efficient than math.isclose)
EPSILON = 1e-9

# Terminal capability detection - done once at module load
_TERMINAL_SUPPORTS_EMOJI = None
_ANIMATION_DURATION_INCREMENT_STEP = 0.05
_ANIMATION_DURATION_INITIAL_FRACTION = 0.3
_ANIMATION_THRESHOLD = 0.1


def _detect_emoji_support():
    """Detect if terminal supports emoji rendering properly (run once)"""
    # TODO: return to this topic and improve it
    return False
    global _TERMINAL_SUPPORTS_EMOJI
    if _TERMINAL_SUPPORTS_EMOJI is not None:
        return _TERMINAL_SUPPORTS_EMOJI
    try:
        import os

        # Most modern terminals support emoji, including Windows Terminal
        # The main exceptions are very old terminals or minimal SSH clients
        term = os.environ.get("TERM", "").lower()
        # Known good terminals
        if any(
            good_term in term
            for good_term in ["xterm", "xterm-256color", "screen", "tmux"]
        ):
            _TERMINAL_SUPPORTS_EMOJI = True
        # Conservative fallback - try emoji since most terminals now support it
        else:
            _TERMINAL_SUPPORTS_EMOJI = True
    except Exception:
        # Any import or environment issues, be conservative
        _TERMINAL_SUPPORTS_EMOJI = False

    return _TERMINAL_SUPPORTS_EMOJI


def city_to_display_offset(city_x, city_y, map_size, h_spacing, v_spacing):
    """Convert city coordinates to display offset using coordinate transformation.

    Args:
        city_x, city_y: City coordinates (may include negative values for torus wrapping)
        map_size: Size of the city grid
        h_spacing, v_spacing: Character spacing per city unit

    Returns:
        Offset: Display coordinates for positioning widgets
    """
    # Handle torus coordinates - Chart.js uses values like -0.5 and citySize-0.5
    # Don't automatically wrap here since we want to preserve Chart.js coordinate ranges
    # The wrapping logic is handled explicitly in the vehicle widgets

    h_shift = round(0.5 * h_spacing)
    v_shift = round(0.5 * v_spacing)

    display_x = int((city_x * h_spacing) + h_shift)
    display_y = int((map_size - city_y) * v_spacing) - v_shift

    return Offset(display_x, display_y)


class AdaptiveAnimationManager:
    """
    Manages adaptive animation duration based on real-time completion rates.
    Automatically adjusts animation timing based on system performance and spacing.
    """

    def __init__(
        self, initial_duration=_ANIMATION_DURATION_INITIAL_FRACTION, animation_delay=1.0
    ):
        # Core state
        self.current_duration = initial_duration
        self.animation_delay = animation_delay

        # Statistics tracking (rolling window)
        self.animation_overrun_count = 0
        self.vehicle_count = 1

        # Tuning parameters
        self.increment_step = _ANIMATION_DURATION_INCREMENT_STEP
        self.max_duration = min(0.8, animation_delay * 0.8)
        self.min_duration = 0.1  # Minimum 100ms for visual smoothness
        self.target_completion_rate = 0.95  # 95% success rate target

        # Spacing-aware parameters
        self.animation_spacing_threshold = 3  # Minimum spacing for useful animation
        self.current_spacing = (1, 1)  # Track current terminal spacing
        self.animation_enabled = True  # Whether animation is currently beneficial

    def update_spacing(self, h_spacing, v_spacing):
        """Update current spacing and recalculate animation utility"""
        self.current_spacing = (h_spacing, v_spacing)

        # Determine if animation is beneficial
        min_spacing = min(h_spacing, v_spacing)
        self.animation_enabled = min_spacing >= self.animation_spacing_threshold

        # Adjust strategy based on spacing
        if not self.animation_enabled:
            # For small spacing, no need for adaptive duration tracking
            self.current_duration = 0.0  # Will trigger immediate refresh
            logging.debug(
                (
                    f"Animation disabled: spacing {h_spacing}x{v_spacing} "
                    f"below threshold {self.animation_spacing_threshold}"
                )
            )
        else:
            # Re-enable adaptive tracking if it was disabled
            if self.current_duration == 0.0:
                self.current_duration = 0.3  # Start with reasonable default
                logging.debug(f"Animation re-enabled: spacing {h_spacing}x{v_spacing}")

    def get_completion_rate(self):
        """Calculate recent completion rate"""
        if self.vehicle_count == 0:
            return 0
        return (self.vehicle_count - self.animation_overrun_count) / self.vehicle_count

    def adjust_duration(self):
        """Core adaptive algorithm"""
        if not self.animation_enabled:
            return

        completion_rate = self.get_completion_rate()

        # Determine adjustment direction
        if completion_rate < self.target_completion_rate:
            # Too many overruns - decrease duration
            adjustment = -self.increment_step
        elif completion_rate >= 0.98:  # Very high success rate
            # Try increasing duration for smoother animation
            adjustment = self.increment_step
        else:
            # In acceptable range - no adjustment
            adjustment = 0

        # Apply adjustment with bounds
        if adjustment != 0:
            new_duration = self.current_duration + adjustment
            new_duration = max(self.min_duration, min(new_duration, self.max_duration))

            if new_duration != self.current_duration:
                self.current_duration = new_duration

    def should_animate(self):
        """Determine if animation should be used based on current conditions"""
        return self.animation_enabled and self.current_duration > 0.05

    def get_animation_duration(self):
        """Get duration - 0.0 means use immediate refresh"""
        if not self.should_animate():
            return 0.0
        return self.current_duration

    def get_animation_threshold(self):
        return self.animation_spacing_threshold

    def get_statistics(self):
        """Get current performance statistics"""
        return {
            "current_duration": self.current_duration,
            "completion_rate": self.get_completion_rate(),
            "animation_overrun_count": self.animation_overrun_count,
            "animation_enabled": self.animation_enabled,
            "spacing": self.current_spacing,
        }


class StaticMapGrid(Widget):
    """Static background grid showing roads and intersections"""

    # Unicode characters for map rendering
    MAP_CHARS = {
        "intersection": "[grey42]┼[/grey42]",
        "road_horizontal": "[grey42]─[/grey42]",
        "road_vertical": "[grey42]│[/grey42]",
        "corner_tl": "[grey42]┌[/grey42]",
        "corner_tr": "[grey42]┐[/grey42]",
        "corner_bl": "[grey42]└[/grey42]",
        "corner_br": "[grey42]┘[/grey42]",
        "tee_up": "[grey42]┴[/grey42]",
        "tee_down": "[grey42]┬[/grey42]",
        "tee_left": "[grey42]┤[/grey42]",
        "tee_right": "[grey42]├[/grey42]",
        "empty_space": " ",
    }

    def __init__(self, map_size, **kwargs):
        super().__init__(**kwargs)
        self.map_size = map_size

        # Caching for spacing calculations (performance optimization)
        self._cached_spacing = None
        self._last_widget_size = None

    def _is_close_to_integer(self, value, epsilon=EPSILON):
        """Check if a value is close to an integer."""
        return abs(value - round(value)) < epsilon

    def _get_road_character(self, x, y):
        """Get the appropriate road/intersection character for
        position (x, y) in new coordinate range"""
        city_x_at_intersection = self._is_close_to_integer(x)
        city_y_at_intersection = self._is_close_to_integer(y)

        # Intersections: both coordinates are at city intersections
        if city_x_at_intersection and city_y_at_intersection:
            return self.MAP_CHARS["intersection"]
        # road segments
        elif city_x_at_intersection:
            return self.MAP_CHARS["road_vertical"]
        elif city_y_at_intersection:
            return self.MAP_CHARS["road_horizontal"]
        # interior spaces between roads
        else:
            return self.MAP_CHARS["empty_space"]

    def _calculate_spacing(self):
        """Calculate optimal spacing based on available terminal space with caching"""
        widget_size = self.size

        # Check cache - return cached result if widget size hasn't changed
        if widget_size == self._last_widget_size and self._cached_spacing is not None:
            return self._cached_spacing

        # Calculate spacing (widget size changed or first calculation)
        # Account for panel borders and padding (roughly 4 chars horizontal, 3 lines vertical)
        available_width = widget_size.width - 4
        available_height = widget_size.height - 3

        # Calculate spacing. The map is square, with sides self.map_size
        horizontal_spacing = max(available_width // self.map_size, 1)
        vertical_spacing = max(available_height // self.map_size, 1)

        # Cache the result
        self._last_widget_size = widget_size
        self._cached_spacing = (horizontal_spacing, vertical_spacing)

        return horizontal_spacing, vertical_spacing

    def render(self) -> RenderResult:
        """Render the static map grid (roads and intersections only)"""
        t_start = time.perf_counter()

        h_spacing, v_spacing = self._calculate_spacing()
        t_spacing = time.perf_counter()

        h_shift = round(0.5 * h_spacing)
        v_shift = round(0.5 * v_spacing)

        # Debug: ensure we always return something visible
        if h_spacing <= 0 or v_spacing <= 0:
            return "[red]Grid Error: Invalid spacing[/red]"

        map_lines = []

        # Use new coordinate range: -0.5 to (city_size-0.5) for easier wrapping
        # Adjust starting points to ensure we hit integer city coordinates (0, 1, 2, etc.)
        # We want city_coord = (display_coord / spacing) - 0.5 to equal integers
        # So display_coord / spacing = city_coord + 0.5
        # So display_coord = spacing * (city_coord + 0.5)
        # For city_coord = 0: display_coord = spacing * 0.5

        # Find the starting display coordinate closest to our desired range that aligns with grid

        # Generate coordinates that will align with integer city coordinates
        for display_y in range(
            self.map_size * v_spacing - v_shift,
            -v_shift,
            -1,
        ):
            line_chars = []
            # Transform display coordinates to city coordinates with -0.5 offset
            city_y = display_y / v_spacing
            for display_x in range(-h_shift, self.map_size * h_spacing - h_shift):
                # Transform display coordinates to city coordinates with -0.5 offset
                city_x = display_x / h_spacing
                char = f"[grey82]{self._get_road_character(city_x, city_y)}[/grey82]"
                line_chars.append(char)
            map_lines.append("".join(line_chars))

        t_grid = time.perf_counter()

        # Ensure we have content
        if not map_lines:
            return "[yellow]Grid: No content generated[/yellow]"

        result = "\n".join(map_lines)
        t_end = time.perf_counter()

        print(
            f"PROFILE: StaticMapGrid.render spacing: {(t_spacing - t_start) * 1000:.1f}ms, grid_gen: {(t_grid - t_spacing) * 1000:.1f}ms, join: {(t_end - t_grid) * 1000:.1f}ms, TOTAL: {(t_end - t_start) * 1000:.1f}ms",
            file=sys.stderr,
            flush=True,
        )

        return result


class VehicleWidget(Widget):
    """Individual vehicle widget with positioning and native Textual animation"""

    # Disable automatic color styling to allow Rich markup colors to show through
    auto_color = False

    def __init__(
        self, vehicle, map_size, h_spacing, v_spacing, animation_manager=None, **kwargs
    ):
        super().__init__(**kwargs)
        self.vehicle = vehicle
        self.map_size = map_size
        self.h_spacing = h_spacing
        self.v_spacing = v_spacing
        self.animation_manager = animation_manager

        self.current_direction = getattr(vehicle.direction, "name", "north").lower()
        self.current_phase = getattr(vehicle.phase, "name", "P1")
        # Target state for next update (Chart.js pattern)
        self.target_direction = self.current_direction
        self.target_phase = self.current_phase
        # Animation state tracking
        self.is_animating = False
        self.needs_edge_wrapping = False

        # Set initial position based on vehicle location
        initial_offset = city_to_display_offset(
            vehicle.location[0],
            vehicle.location[1],
            self.map_size,
            self.h_spacing,
            self.v_spacing,
        )
        self.styles.offset = initial_offset

    def move_to_intersection(
        self,
        vehicle_id,
        intersection_city_coords,
        new_direction,
        new_phase,
    ):
        # Calculate destination offset
        intersection_offset = city_to_display_offset(
            intersection_city_coords[0],
            intersection_city_coords[1],
            self.map_size,
            self.h_spacing,
            self.v_spacing,
        )
        # Store target state (direction and phase taken on at the intersection)
        self.target_direction = new_direction
        self.target_phase = new_phase
        # Spacing-aware animation decision
        min_spacing = min(self.h_spacing, self.v_spacing)
        use_immediate_refresh = (
            min_spacing <= self.animation_manager.get_animation_threshold()
        )

        if self.is_animating:
            # Skip if already animating
            self.notify("! vehicle is animating. Incrementing animation overrun")
            self.is_animating = False
            self.animation_manager.animation_overrun_count += 1
            self._move_immediately(intersection_offset)
            return
        if use_immediate_refresh:
            self.notify(
                (
                    "! move_to_intersection: "
                    f"use_immediate_refresh={use_immediate_refresh}"
                ),
            )
            # Immediate position update - no animation benefit
            self._move_immediately(intersection_offset)
        else:
            # Use animation for meaningful spacing
            self.notify("OK: calling move_with_animation for intersection")
            self._move_with_animation(intersection_offset)

    def _move_immediately(self, target_offset):
        """Immediate position update with state changes"""
        # Update position instantly
        self.styles.offset = target_offset
        self.is_animating = False
        # Refresh display
        self.refresh()

    def _move_with_animation(self, target_offset):
        """Animated movement with completion tracking"""
        # self.is_animating = True
        try:
            self.notify(
                "OK: _move_with_aniumation calling animate..."
                f"target_offset={target_offset}"
            )
            self.animate(
                "offset",
                value=target_offset,
                # duration=self.animation_manager.get_animation_duration(),
                duration=0.3,
                on_complete=self._animation_complete,
                easing="linear",
            )
        except Exception as e:
            self.notify(f"! animate exception: {e}")

    def move_to_midpoint(self, vehicle_id, midpoint_city_coords):
        self.current_direction = self.target_direction
        self.current_phase = self.target_phase

        # For small spacing, midpoint movement is also pointless
        min_spacing = min(self.h_spacing, self.v_spacing)
        if min_spacing <= 2:
            # No visible midpoint - just refresh with current state
            # Update state immediately for consistency
            self.refresh()
            return

        # Calculate midpoint position based on NEW direction (after update)
        current_pos = self.vehicle.location
        midpoint_coords = [current_pos[0], current_pos[1]]

        if self.current_direction == "north":
            midpoint_coords[1] += 0.5
        elif self.current_direction == "east":
            midpoint_coords[0] += 0.5
        elif self.current_direction == "south":
            midpoint_coords[1] -= 0.5
        elif self.current_direction == "west":
            midpoint_coords[0] -= 0.5
        self.needs_edge_wrapping = self._needs_edge_wrapping(midpoint_coords)

        # Move to midpoint position
        midpoint_offset = city_to_display_offset(
            midpoint_coords[0],
            midpoint_coords[1],
            self.map_size,
            self.h_spacing,
            self.v_spacing,
        )
        use_immediate_refresh = (
            min_spacing <= self.animation_manager.get_animation_threshold()
        )

        if self.is_animating:
            self.notify("! move_to_midpoint: is animating so move immediately")
            self.is_animating = False
            self.animation_manager.animation_overrun_count += 1
            self._move_immediately(midpoint_offset)
            return  # Don't interfere with ongoing animation
        if use_immediate_refresh:
            # Immediate position update - no animation benefit
            self.notify("! move_to_midpoint: use_immediate_refresh so move immediately")
            self._move_immediately(midpoint_offset)
        else:
            self.notify("OK: calling move_with_animation for midpoint")
            self._move_with_animation(midpoint_offset)

    def _animation_complete(self):
        """Called when animation sequence is complete (legacy method)"""
        print("animation complete, setting is_animating to False")
        self.is_animating = False

    def _needs_edge_wrapping(self, coords):
        """Check if coordinates need edge wrapping using Chart.js boundary thresholds

        Uses buffer zones like Chart.js implementation to prevent edge case flickering:
        - Right edge: x > citySize - 0.6
        - Left edge: x < -0.1
        - Top edge: y > citySize - 0.9
        - Bottom edge: y < -0.1
        """
        x, y = coords
        city_size = self.map_size

        needs_edge_wrapping = (
            x > city_size - 0.6  # Right edge
            or x < -0.1  # Left edge
            or y > city_size - 0.9  # Top edge
            or y < -0.1  # Bottom edge
        )
        print(f"_needs_edge_wrapping: (x,y)={(x, y)}, new is {needs_edge_wrapping}")
        return needs_edge_wrapping

    def calculate_wrapped_position(self, coords):
        """Calculate wrapped position using Chart.js teleportation logic

        Mirrors the Chart.js boundary handling:
        - Right edge (x > citySize - 0.6) → teleport to x = -0.5
        - Left edge (x < -0.1) → teleport to x = citySize - 0.5
        - Top edge (y > citySize - 0.9) → teleport to y = -0.5
        - Bottom edge (y < -0.1) → teleport to y = citySize - 0.5
        """
        x, y = coords
        city_size = self.map_size

        new_x, new_y = x, y

        # Apply Chart.js boundary thresholds and teleportation targets
        if x > city_size - 0.6:  # Right edge
            new_x = -0.5  # Teleport to left side
        elif x < -0.1:  # Left edge
            new_x = city_size - 0.5  # Teleport to right side

        if y > city_size - 0.9:  # Top edge
            new_y = -0.5  # Teleport to bottom
        elif y < -0.1:  # Bottom edge
            new_y = city_size - 0.5  # Teleport to top

        return (new_x, new_y)

    def _handle_edge_wrapping(self, dest_coords, new_direction, new_phase):
        """Handle edge wrapping by immediately positioning vehicle on opposite edge

        Mirrors Chart.js logic:
        1. Update position immediately without animation (chart.update("none"))
        2. Update vehicle state (direction, phase)
        3. Refresh display to show teleported vehicle
        """
        # Update position immediately without animation (like JavaScript needsRefresh logic)
        dest_offset = city_to_display_offset(
            dest_coords[0],
            dest_coords[1],
            self.map_size,
            self.h_spacing,
            self.v_spacing,
        )

        # Immediate update without animation (equivalent to chart.update("none"))
        self.styles.offset = dest_offset
        # For edge wrapping, update both current and target state immediately
        self.current_direction = new_direction
        self.current_phase = new_phase
        self.target_direction = new_direction
        self.target_phase = new_phase

        # Mark animation as complete to prevent further animation steps
        self.is_animating = False

        # Refresh display to show the "teleported" vehicle (equivalent to second chart.update("none"))
        self.refresh()

    def update_position_immediately(self, city_coords):
        """Update position immediately without animation (for initialization)"""
        new_offset = city_to_display_offset(
            city_coords[0],
            city_coords[1],
            self.map_size,
            self.h_spacing,
            self.v_spacing,
        )
        self.styles.offset = new_offset

    def update_spacing(self, h_spacing, v_spacing):
        """Update spacing parameters when container resizes"""
        self.h_spacing = h_spacing
        self.v_spacing = v_spacing
        # Update current position with new spacing
        if hasattr(self.vehicle, "location"):
            self.update_position_immediately(self.vehicle.location)

    def get_vehicle_character(self):
        """Get the appropriate character and color for this vehicle"""
        # Use current tracked state for consistent display during animations
        # return ":car:"
        direction_name = self.current_direction

        # Vehicle direction characters - large block arrows for better volume
        vehicle_chars = {"north": "⬆", "east": "➡", "south": "⬇", "west": "⬅"}
        phase_colors = {"P1": "sky_blue1", "P2": "orange3", "P3": "green"}

        if self.current_phase in phase_colors:
            color = phase_colors[self.current_phase]
            vehicle_char = vehicle_chars.get(direction_name, "•")
            return f"[{color}]{vehicle_char}[/{color}]"
        else:
            return vehicle_chars.get(direction_name, "•")

    def update_direction_display(self, direction):
        """Update vehicle direction (used by animation system)"""
        self.current_direction = direction
        self.refresh()

    def update_phase_color(self, phase):
        """Update vehicle phase color (used by animation system)"""
        self.current_phase = phase
        self.refresh()

    def render(self) -> RenderResult:
        """Render the vehicle character"""
        return self.get_vehicle_character()


class VehicleLayer(Widget):
    """Container for individual vehicle widgets with native animation support"""

    def __init__(self, map_size, static_grid, **kwargs):
        super().__init__(**kwargs)
        self.vehicle_widgets = {}
        self.map_size = map_size
        self.static_grid = static_grid

        # Track vehicle positions for animation triggers
        self.previous_positions = {}

        # Add adaptive animation manager
        self.animation_manager = AdaptiveAnimationManager()

    def add_vehicle(self, vehicle_id, vehicle):
        """Enhanced vehicle creation with animation manager"""
        if vehicle_id not in self.vehicle_widgets:
            # Get current spacing from static grid
            h_spacing, v_spacing = self.static_grid._calculate_spacing()
            vehicle_widget = VehicleWidget(
                vehicle,
                self.map_size,
                h_spacing,
                v_spacing,
                animation_manager=self.animation_manager,  # Pass manager to widget
            )
            self.vehicle_widgets[vehicle_id] = vehicle_widget
            # Mount the widget to make it visible in the widget tree
            self.mount(vehicle_widget)

    def remove_vehicle(self, vehicle_id):
        """Remove a vehicle widget from this layer"""
        if vehicle_id in self.vehicle_widgets:
            vehicle_widget = self.vehicle_widgets[vehicle_id]
            # Remove from widget tree
            vehicle_widget.remove()
            del self.vehicle_widgets[vehicle_id]
            if vehicle_id in self.previous_positions:
                del self.previous_positions[vehicle_id]

    def update_vehicles(self, vehicles, animation_delay=1.0, frame_index=0):
        # Update animation manager for this update
        self.animation_manager.animation_delay = animation_delay
        self.animation_manager.animation_overrun_count = 0
        self.animation_manager.vehicle_count = len(vehicles)
        h_spacing, v_spacing = self.static_grid._calculate_spacing()
        self.animation_manager.update_spacing(h_spacing, v_spacing)

        # Update vehicle spacing for the current terminal window
        for vehicle_widget in self.vehicle_widgets.values():
            vehicle_widget.update_spacing(h_spacing, v_spacing)

        # Get effective duration (may be 0.0 for immediate refresh)
        self.animation_duration = self.animation_manager.get_animation_duration()

        current_vehicle_ids = set(id(v) for v in vehicles)

        # Remove vehicles that no longer exist
        existing_ids = set(self.vehicle_widgets.keys())
        for vehicle_id in existing_ids - current_vehicle_ids:
            self.remove_vehicle(vehicle_id)

        # Add new vehicles or update existing ones
        for vehicle in vehicles:
            vehicle_id = id(vehicle)
            current_pos = (vehicle.location[0], vehicle.location[1])
            current_direction = getattr(vehicle.direction, "name", "north").lower()
            current_phase = getattr(vehicle.phase, "name", "P1")

            if vehicle_id not in self.vehicle_widgets:
                # New vehicle - add without animation
                self.add_vehicle(vehicle_id, vehicle)
                self.previous_positions[vehicle_id] = current_pos
            else:
                # Update existing vehicle
                vehicle_widget = self.vehicle_widgets[vehicle_id]
                vehicle_widget.vehicle = vehicle

                if frame_index % 2 == 0:
                    # Even frame: Use effective duration (could be 0.0)
                    previous_pos = self.previous_positions.get(vehicle_id, current_pos)

                    if previous_pos != current_pos:
                        vehicle_widget.move_to_intersection(
                            vehicle_id=vehicle_id,
                            intersection_city_coords=current_pos,
                            new_direction=current_direction,
                            new_phase=current_phase,
                        )
                        self.previous_positions[vehicle_id] = current_pos
                else:
                    # Odd frame: Move vehicles to midpoints
                    vehicle_widget.move_to_midpoint(
                        vehicle_id=vehicle_id,
                        midpoint_city_coords=current_pos,
                    )
        if frame_index % 2 == 1:
            self._handle_batch_edge_wrapping()

        # End of frame: adjust duration based on completion rates
        self.animation_manager.adjust_duration()

    def _handle_batch_edge_wrapping(self):
        """Handle batch edge wrapping for multiple vehicles (Chart.js pattern)

        Mirrors Chart.js logic:
        - Suppress animations for all wrapped vehicles
        - Update positions instantly to opposite edges
        - Refresh display once for all changes
        """
        # Batch update all vehicles that need edge wrapping
        for vehicle_widget in self.vehicle_widgets.values():
            # Calculate wrapped position using Chart.js thresholds
            if vehicle_widget.needs_edge_wrapping:
                wrapped_pos = vehicle_widget.calculate_wrapped_position(
                    vehicle_widget.vehicle.location
                )
                print(f"wrapping vehicle to {wrapped_pos}")

                # Instant update without animation (equivalent to chart.update("none"))
                wrapped_offset = city_to_display_offset(
                    wrapped_pos[0],
                    wrapped_pos[1],
                    vehicle_widget.map_size,
                    vehicle_widget.h_spacing,
                    vehicle_widget.v_spacing,
                )

                # Update widget state immediately
                vehicle_widget.styles.offset = wrapped_offset
                vehicle_widget.is_animating = False
                vehicle_widget.needs_edge_wrapping = False

                # Individual refresh for each wrapped vehicle
                vehicle_widget.refresh()

    def get_vehicle_count(self):
        """Get current number of vehicles in layer"""
        return len(self.vehicle_widgets)

    def render(self) -> RenderResult:
        """Render empty - vehicles will be positioned absolutely via native animation"""
        return ""


class TripMarkerWidget(Static):
    """Individual trip marker widget"""

    # Disable automatic color styling to allow Rich markup colors to show through
    auto_color = False

    def __init__(
        self, marker_type, city_coords, map_size, h_spacing, v_spacing, **kwargs
    ):
        super().__init__(**kwargs)
        self.marker_type = marker_type  # "origin" or "destination"
        self.city_coords = city_coords
        self.map_size = map_size
        self.h_spacing = h_spacing
        self.v_spacing = v_spacing

        # Set position
        self.styles.offset = city_to_display_offset(
            self.city_coords[0],
            self.city_coords[1],
            self.map_size,
            self.h_spacing,
            self.v_spacing,
        )

    def render(self) -> RenderResult:
        """Render the trip marker character"""
        if self.marker_type == "origin":
            # Use cached terminal capability check for efficiency
            if _detect_emoji_support():
                return ":adult:"
            else:
                return "[orange3]●[/orange3]"  # Fallback to current character
        elif self.marker_type == "destination":
            if _detect_emoji_support():
                return ":house:"  # ADULT emoji - default skin tone, no color markup
            else:
                return "[green1]★[/green1]"
        return "?"


class TripMarkerLayer(Widget):
    """Container for trip origin and destination markers using individual widgets"""

    def __init__(self, map_size, static_grid, **kwargs):
        super().__init__(**kwargs)
        self.map_size = map_size
        self.static_grid = static_grid
        self.trip_marker_widgets = {}  # trip_id -> widget

    def update_trip_markers(self, trips, map_size, frame_index):
        """Update trip marker widgets with Chart.js timing pattern

        Mirrors Chart.js logic (map.js:434-442):
        - Trip data is collected on every frame
        - Trip marker display updates happen ONLY on odd frames (interpolation points)
        - This ensures markers change at intersection midpoints, not before vehicle arrival
        """
        h_spacing, v_spacing = self.static_grid._calculate_spacing()

        # Always collect trip data (like Chart.js tripLocations, tripColors, tripStyles)
        trip_data = []
        current_trip_ids = set()

        # Handle both dict.values() and lists for backwards compatibility
        trips_iterable = trips.values() if isinstance(trips, dict) else trips

        for trip in trips_iterable:
            if (
                hasattr(trip, "origin")
                and hasattr(trip, "destination")
                and hasattr(trip.phase, "name")
            ):
                trip_id = id(trip)
                current_trip_ids.add(trip_id)

                if trip.phase.name in ("UNASSIGNED", "WAITING"):
                    # Show origin marker
                    marker_type = "origin"
                    coords = (int(trip.origin[0]), int(trip.origin[1]))
                    trip_data.append((trip_id, marker_type, coords))
                elif trip.phase.name == "RIDING":
                    # Show destination marker
                    marker_type = "destination"
                    coords = (int(trip.destination[0]), int(trip.destination[1]))
                    trip_data.append((trip_id, marker_type, coords))
                # COMPLETED/CANCELLED trips are handled in removal logic below

        # Chart.js pattern: Only update display on odd frames (interpolation points)
        if frame_index % 2 != 0:
            # interpolation point: change trip marker location and styles
            self._update_trip_marker_display(trip_data, map_size, h_spacing, v_spacing)

        # Always handle removal of completed/cancelled trips (regardless of frame)
        existing_ids = set(self.trip_marker_widgets.keys())
        for trip_id in existing_ids - current_trip_ids:
            if trip_id in self.trip_marker_widgets:
                marker_widget = self.trip_marker_widgets[trip_id]
                marker_widget.remove()
                del self.trip_marker_widgets[trip_id]

    def _update_trip_marker_display(self, trip_data, map_size, h_spacing, v_spacing):
        """Update the actual trip marker display (called only on odd frames)"""
        for trip_id, marker_type, coords in trip_data:
            if trip_id not in self.trip_marker_widgets:
                # Create new marker widget
                marker_widget = TripMarkerWidget(
                    marker_type, coords, map_size, h_spacing, v_spacing
                )
                self.trip_marker_widgets[trip_id] = marker_widget
                self.mount(marker_widget)
            else:
                # Check if existing marker needs to be updated (origin -> destination)
                existing_widget = self.trip_marker_widgets[trip_id]
                if existing_widget.marker_type != marker_type:
                    # Remove old marker and create new one
                    existing_widget.remove()
                    marker_widget = TripMarkerWidget(
                        marker_type, coords, map_size, h_spacing, v_spacing
                    )
                    self.trip_marker_widgets[trip_id] = marker_widget
                    self.mount(marker_widget)

    def render(self) -> RenderResult:
        """Render empty - trip markers are positioned as child widgets"""
        return ""


class MapContainer(Widget):
    """Container that composes all map layers together"""

    # No explicit render() in this class, as all layers refresh
    # automatically as child widgets

    DEFAULT_CSS = """
    Header {
        background: $secondary;
    }

    Footer {
        background: $secondary;
    }

    MapContainer {
        border: solid $primary;
        padding: 1;
        height: 1fr;
        width: 1fr;
        layers: grid trips vehicles;
    }

    StaticMapGrid {
        height: 100%;
        width: 100%;
        layer: grid;
        color: ansi_bright_black;
    }

    TripMarkerLayer {
        height: 100%;
        width: 100%;
        layer: trips;
        visibility: hidden;
    }

    VehicleLayer {
        height: 100%;
        width: 100%;
        layer: vehicles;
        visibility: hidden;
    }

    VehicleWidget {
        width:  1;
        height: 1;
        visibility: visible;
        dock: top;
        color: auto;
    }

    TripMarkerWidget {
        width:  1;
        height: 1;
        visibility: visible;
        dock: top;
        color: auto;
    }
    """

    def __init__(self, sim, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim
        self.map_size = min(sim.city.city_size, 250)

        # Create layer instances
        self.static_grid = StaticMapGrid(self.map_size)
        self.trip_layer = TripMarkerLayer(self.map_size, self.static_grid)
        self.vehicle_layer = VehicleLayer(self.map_size, self.static_grid)

        # Animation mode control
        self.use_native_animation = True  # Native animation is now the default

        # Vehicle position tracking (used by vehicle layer for animation triggers)
        self.vehicle_previous_positions = {}
        self.vehicle_current_positions = {}

    def compose(self) -> ComposeResult:
        """Compose all map layers with proper z-ordering"""
        yield self.static_grid
        yield self.trip_layer
        yield self.vehicle_layer

    def update_vehicle_positions(self):
        """Update vehicle position tracking for interpolation (temporary)"""
        self.vehicle_previous_positions = self.vehicle_current_positions.copy()

        self.vehicle_current_positions = {}
        for vehicle in self.sim.vehicles:
            vehicle_id = id(vehicle)
            self.vehicle_current_positions[vehicle_id] = (
                vehicle.location[0],
                vehicle.location[1],
            )

            if vehicle_id not in self.vehicle_previous_positions:
                self.vehicle_previous_positions[vehicle_id] = (
                    self.vehicle_current_positions[vehicle_id]
                )

    def render(self) -> RenderResult:
        """Render empty - all content is handled by layered child widgets"""
        return ""

    def update_map(self, frame_index: int, update_positions: bool = False):
        """Update the map display for the given frame"""
        if update_positions:
            self.update_vehicle_positions()

        # Update the vehicle layer with native animation
        animation_delay = self.sim.config.animation_delay.value
        if animation_delay is None:
            animation_delay = self.sim.config.animation_delay.default

        self.vehicle_layer.update_vehicles(
            self.sim.vehicles, animation_delay=animation_delay, frame_index=frame_index
        )

        # Update trip markers with frame index for Chart.js timing pattern
        self.trip_layer.update_trip_markers(self.sim.trips, self.map_size, frame_index)


class TextualMapApp(RidehailTextualApp):
    """Textual app using native animation with MapContainer"""

    def __init__(self, sim, animation=None, **kwargs):
        super().__init__(sim, animation, **kwargs)
        self.frame_index = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the map app"""
        t_start = time.perf_counter()

        header = Header()
        t_header = time.perf_counter()
        print(
            f"PROFILE: compose Header: {(t_header - t_start) * 1000:.1f}ms",
            file=sys.stderr,
        )

        map_container = MapContainer(self.sim, id="map_container")
        t_map = time.perf_counter()
        print(
            f"PROFILE: compose MapContainer: {(t_map - t_header) * 1000:.1f}ms",
            file=sys.stderr,
        )

        footer = Footer()
        t_footer = time.perf_counter()
        print(
            f"PROFILE: compose Footer: {(t_footer - t_map) * 1000:.1f}ms",
            file=sys.stderr,
        )
        print(
            f"PROFILE: compose TOTAL: {(t_footer - t_start) * 1000:.1f}ms",
            file=sys.stderr,
        )

        yield header
        yield map_container
        yield footer

    def on_mount(self) -> None:
        """Called when app starts"""
        t_start = time.perf_counter()
        self.title = (
            f"Ridehail Map - Block {self.sim.block_index}/{self.sim.time_blocks}"
        )
        t_title = time.perf_counter()
        print(
            f"PROFILE: on_mount title set: {(t_title - t_start) * 1000:.1f}ms",
            file=sys.stderr,
            flush=True,
        )

        self.start_simulation()
        t_start_sim = time.perf_counter()
        print(
            f"PROFILE: on_mount start_simulation: {(t_start_sim - t_title) * 1000:.1f}ms",
            file=sys.stderr,
            flush=True,
        )
        print(
            f"PROFILE: on_mount TOTAL: {(t_start_sim - t_start) * 1000:.1f}ms",
            file=sys.stderr,
            flush=True,
        )

    def simulation_step(self) -> None:
        """Execute one simulation step as two animation frames
        Each simulation step consists of:
        - Frame 0 (even): move vehicles to intersections, advance simulation
        - Frame 1 (odd): move vehicles to midpoints (interpolated positions)
        """
        t_step_start = time.perf_counter()
        print(f"textual_map simulation step at frame {self.frame_index}...")
        if self.is_paused:
            print("simulation_step: paused...")
            return
        try:
            # Get map container
            map_container = self.query_one("#map_container", expect_type=MapContainer)
            t_query = time.perf_counter()
            if self.frame_index == 0:
                print(
                    f"PROFILE: simulation_step query_one: {(t_query - t_step_start) * 1000:.1f}ms",
                    file=sys.stderr,
                    flush=True,
                )

            if self.frame_index % 2 == 0:
                # Even frame: Real simulation step - vehicles reach intersections
                t_sim_start = time.perf_counter()
                self.sim.next_block(
                    jsonl_file_handle=None,
                    csv_file_handle=None,
                    return_values="stats",
                    dispatch=self.animation.dispatch,
                )
                t_sim_end = time.perf_counter()
                if self.frame_index == 0:
                    print(
                        f"PROFILE: simulation_step sim.next_block: {(t_sim_end - t_sim_start) * 1000:.1f}ms",
                        file=sys.stderr,
                        flush=True,
                    )

                # Update title to show progress and adaptive animation status
                if hasattr(map_container, "vehicle_layer") and hasattr(
                    map_container.vehicle_layer, "animation_manager"
                ):
                    mgr = map_container.vehicle_layer.animation_manager
                    spacing = mgr.current_spacing
                    if mgr.should_animate():
                        mode = f"ADAPTIVE({mgr.current_duration:.2f}s)"
                        completion_rate = f"completion_rate={mgr.get_completion_rate()}"
                    else:
                        mode = "IMMEDIATE"
                        completion_rate = "N/A"
                    self.title = (
                        "Ridehail Map - Block "
                        f"{self.sim.block_index}/{self.sim.time_blocks} "
                        f"- {spacing[0]}x{spacing[1]} spacing - {mode} "
                        f"- {completion_rate}"
                    )
                else:
                    self.title = (
                        "Ridehail Map - Block "
                        f"{self.sim.block_index}/{self.sim.time_blocks}"
                    )

                t_title = time.perf_counter()
                if self.frame_index == 0:
                    print(
                        f"PROFILE: simulation_step title update: {(t_title - t_sim_end) * 1000:.1f}ms",
                        file=sys.stderr,
                        flush=True,
                    )

                # Even frames: simulation step - move vehicles to intersections
                map_container.update_map(self.frame_index, update_positions=True)
                t_map_update = time.perf_counter()
                if self.frame_index == 0:
                    print(
                        f"PROFILE: simulation_step update_map (even): {(t_map_update - t_title) * 1000:.1f}ms",
                        file=sys.stderr,
                        flush=True,
                    )
            else:
                # Odd frame: interpolation frame - move vehicles to midpoints
                t_odd_start = time.perf_counter()
                map_container.update_map(self.frame_index, update_positions=False)
                t_odd_end = time.perf_counter()
                if self.frame_index == 1:
                    print(
                        f"PROFILE: simulation_step update_map (odd): {(t_odd_end - t_odd_start) * 1000:.1f}ms",
                        file=sys.stderr,
                        flush=True,
                    )

            # Increment frame counter (2 frames per simulation step)
            self.frame_index += 1

            # Check if simulation is complete (only on even frames after advancing simulation)
            if (
                self.frame_index % 2 == 0
                and self.sim.time_blocks > 0
                and self.sim.block_index >= self.sim.time_blocks
            ):
                self.stop_simulation()

        except Exception as e:
            print(f"Map simulation step exception: {e}")
            self.stop_simulation()


class TextualMapAnimation(TextualBasedAnimation):
    """Textual-based map animation using native animation with MapContainer"""

    def create_app(self) -> TextualMapApp:
        """Create the Textual map app instance"""
        t_start = time.perf_counter()
        app = TextualMapApp(self.sim, animation=self)
        t_end = time.perf_counter()
        print(
            f"PROFILE: TextualMapAnimation.create_app: {(t_end - t_start) * 1000:.1f}ms",
            file=sys.stderr,
            flush=True,
        )
        return app
