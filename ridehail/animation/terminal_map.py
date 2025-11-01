"""
Textual-based map animation for ridehail simulation - simplified map-only version.
"""

from textual.app import ComposeResult
from textual.widgets import (
    Header,
    Footer,
    Static,
)
from textual.widget import Widget
from textual.geometry import Offset
from textual.reactive import reactive
from rich.console import RenderResult
from rich import print

from .terminal_base import TextualBasedAnimation, RidehailTextualApp


# Fast epsilon for floating point comparisons (more efficient than math.isclose)
EPSILON = 1e-9

# Terminal capability detection - done once at module load
_TERMINAL_SUPPORTS_EMOJI = None


def _detect_emoji_support():
    """Detect if terminal supports emoji rendering properly (run once)"""
    # TODO: return to this topic and improve it
    return False

    global _TERMINAL_SUPPORTS_EMOJI
    print(f"TERMINAL_SUPPORTS_EMOJI is {_TERMINAL_SUPPORTS_EMOJI}")
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
        print(f"TERMINAL_SUPPORTS_EMOJI is {_TERMINAL_SUPPORTS_EMOJI}")
    except Exception:
        # Any import or environment issues, be conservative
        _TERMINAL_SUPPORTS_EMOJI = False

    return _TERMINAL_SUPPORTS_EMOJI


def location_to_offset(city_x, city_y, map_size, h_spacing, v_spacing):
    """Convert location (city coordinates) to offset (display coordinates)
    using coordinate transformation.

    Args:
        city_x, city_y: city coordinates (may include negative values for torus wrapping)
        map_size: Size of the city grid
        h_spacing, v_spacing: Character spacing per city unit

    Returns:
        Offset: display coordinates for positioning widgets
    """
    # Handle torus coordinates - Chart.js uses values like -0.5 and citySize-0.5
    # Don't automatically wrap here since we want to preserve Chart.js coordinate ranges
    # The wrapping logic is handled explicitly in the vehicle widgets

    h_shift = round(0.5 * h_spacing)
    v_shift = round(0.5 * v_spacing)

    display_x = int((city_x * h_spacing) + h_shift)
    display_y = int((map_size - city_y) * v_spacing) - v_shift

    return Offset(display_x, display_y)


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
        location (x, y) in new coordinate range"""
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
        h_spacing, v_spacing = self._calculate_spacing()
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
                char = self._get_road_character(city_x, city_y)
                line_chars.append(char)
            map_lines.append("".join(line_chars))

        # Ensure we have content
        if not map_lines:
            return "[yellow]Grid: No content generated[/yellow]"

        return "\n".join(map_lines)


class VehicleWidget(Widget):
    """Individual vehicle widget"""

    needs_edge_wrapping = reactive(False)

    def __init__(self, vehicle, map_size, static_grid, **kwargs):
        super().__init__(**kwargs)
        self.vehicle = vehicle
        self.map_size = map_size
        self.static_grid = static_grid  # Reference to get dynamic spacing

        # Animation state tracking
        self.location = vehicle.location
        self.current_direction = getattr(vehicle.direction, "name", "north").lower()
        self.current_phase = getattr(vehicle.phase, "name", "P1")
        self.animation_duration = 1.0
        self.is_animating = False

        # Target state for next update (Chart.js pattern)
        self.target_direction = self.current_direction
        self.target_phase = self.current_phase

        # Set initial location based on vehicle location
        h_spacing, v_spacing = self.static_grid._calculate_spacing()
        initial_offset = location_to_offset(
            self.location[0],
            self.location[1],
            self.map_size,
            h_spacing,
            v_spacing,
        )
        self.styles.offset = initial_offset

        # Set initial CSS class for phase color
        self._update_phase_class()

    def move_to_intersection(
        self,
        vehicle_id,
        new_direction,
        new_phase,
        animation_duration=1.0,
        animation_threshold=0.1,
    ):
        """Move vehicle to intersection (single animation, no midpoint)"""
        if self.is_animating:
            pass
            # return  # Skip if already animating

        # Store TARGET state for updates at midpoint (Chart.js pattern)
        # Don't update current_direction/current_phase yet - that happens at midpoint
        try:
            self.target_direction = new_direction
            self.target_phase = new_phase
            self.animation_duration = animation_duration

            # Get current spacing dynamically
            h_spacing, v_spacing = self.static_grid._calculate_spacing()

            # Get destination for normal movement
            intersection_offset = location_to_offset(
                self.location[0],
                self.location[1],
                self.map_size,
                h_spacing,
                v_spacing,
            )
            self.needs_edge_wrapping = self._needs_edge_wrapping()

            # Conditional animation: if duration < threshold, update immediately
            if animation_duration < animation_threshold:
                # Update offset immediately without animation
                self.styles.offset = intersection_offset
                # Refresh display to show changes
                # self.refresh()
                return

            # Otherwise, use single animation to intersection
            self.is_animating = True

            self.animate(
                "offset",
                value=intersection_offset,
                duration=animation_duration,
                on_complete=self._animation_complete,
                easing="linear",
            )
        except Exception as e:
            print(f"Exception in move_to_intersection: {e}")

    def move_to_midpoint(self, frame_index):
        """Move vehicle to midpoint based on target direction (for odd frames)

        This is where we apply the Chart.js midpoint pattern:
        - Update visual state (direction arrow, phase color) at intersection center
        - Move to midpoint based on NEW direction
        - Skip midpoint movement if vehicle is waiting for pickup
        """
        if self.is_animating:
            # return  # Don't override ongoing animation
            pass

        try:
            # Skip midpoint movement if vehicle is waiting for pickup
            if (
                self.vehicle.pickup_countdown is not None
                and self.vehicle.pickup_countdown > 0
            ):
                # Vehicle is at pickup location, waiting for boarding
                # Update visual state but don't move to midpoint
                direction_changed = self.target_direction != self.current_direction
                phase_changed = self.target_phase != self.current_phase

                if direction_changed or phase_changed:
                    self.current_direction = self.target_direction
                    self.current_phase = self.target_phase
                    if phase_changed:
                        self._update_phase_class()
                        self._update_phase_color()
                    self.refresh()
                return

            # Chart.js pattern: Update display state at midpoint (intersection center)
            direction_changed = self.target_direction != self.current_direction
            phase_changed = self.target_phase != self.current_phase

            if direction_changed or phase_changed:
                self.current_direction = self.target_direction
                self.current_phase = self.target_phase
                if phase_changed:
                    self._update_phase_class()
                # Visual update will happen via refresh() in animation

            # Calculate midpoint location based on NEW direction (after update)
            current_location = self.location
            midpoint_location = [current_location[0], current_location[1]]

            if self.current_direction == "north":
                midpoint_location[1] += 0.5
            elif self.current_direction == "east":
                midpoint_location[0] += 0.5
            elif self.current_direction == "south":
                midpoint_location[1] -= 0.5
            elif self.current_direction == "west":
                midpoint_location[0] -= 0.5
            self.location = midpoint_location
            self.needs_edge_wrapping = self._needs_edge_wrapping()

            # Get current spacing dynamically
            h_spacing, v_spacing = self.static_grid._calculate_spacing()

            # Move to midpoint position
            midpoint_offset = location_to_offset(
                midpoint_location[0],
                midpoint_location[1],
                self.map_size,
                h_spacing,
                v_spacing,
            )

            # self.styles.offset = midpoint_offset
            # self.refresh()
            # Otherwise, use single animation to intersection
            self.is_animating = True
            self.animate(
                "offset",
                value=midpoint_offset,
                duration=self.animation_duration,
                on_complete=self._animation_complete,
                easing="linear",
            )
        except Exception as e:
            print(f"Exception in move_to_midpoint: {e}")

    def _animation_complete(self):
        """Called when animation sequence is complete"""
        self.is_animating = False

    def _needs_edge_wrapping(self):
        """Check if coordinates need edge wrapping using Chart.js boundary thresholds

        Uses buffer zones like Chart.js implementation to prevent edge case flickering:
        - Right edge: x > citySize - 0.6
        - Left edge: x < -0.1
        - Top edge: y > citySize - 0.9
        - Bottom edge: y < -0.1
        """
        x, y = self.location
        city_size = self.map_size

        needs_edge_wrapping = (
            x > city_size - 0.6  # Right edge
            or x < -0.1  # Left edge
            or y > city_size - 0.9  # Top edge
            or y < -0.1  # Bottom edge
        )
        return needs_edge_wrapping

    def calculate_wrapped_location(self):
        """Calculate wrapped position using Chart.js teleportation logic

        Mirrors the Chart.js boundary handling:
        - Right edge (x > citySize - 0.6) → teleport to x = -0.5
        - Left edge (x < -0.1) → teleport to x = citySize - 0.5
        - Top edge (y > citySize - 0.9) → teleport to y = -0.5
        - Bottom edge (y < -0.1) → teleport to y = citySize - 0.5
        """
        city_size = self.map_size
        x, y = self.location
        new_x, new_y = self.location

        # Apply Chart.js boundary thresholds and teleportation targets
        if x > city_size - 0.6:  # Right edge
            new_x = -0.5  # Teleport to left side
        elif x < -0.1:  # Left edge
            new_x = city_size - 0.5  # Teleport to right side

        if y > city_size - 0.9:  # Top edge
            new_y = -0.5  # Teleport to bottom
        elif y < -0.1:  # Bottom edge
            new_y = city_size - 0.5  # Teleport to top

        # Update the city-based coordinates of the vehicle widget
        self.location = (new_x, new_y)
        return (new_x, new_y)

    def update_offset_immediately(self):
        """Update offset immediately without animation (for edge wrapping)"""
        # CRITICAL: Stop any ongoing animation before setting new offset
        # self.stop_animation("offset")
        # self.animation.stop()
        self.is_animating = False

        # Get current spacing dynamically
        h_spacing, v_spacing = self.static_grid._calculate_spacing()

        new_offset = location_to_offset(
            self.location[0],
            self.location[1],
            self.map_size,
            h_spacing,
            v_spacing,
        )
        self.styles.offset = new_offset
        self.refresh()

    def get_vehicle_character(self):
        """Get the appropriate character for this vehicle (color via CSS)"""
        PICKUP_CHARACTER = "\u25cf"  # Solid circle
        # Show reference mark during pickup (passenger boarding)
        if (
            self.vehicle.pickup_countdown is not None
            and self.vehicle.pickup_countdown > 0
        ):
            return PICKUP_CHARACTER

        # Use current tracked state for consistent display during animations
        direction_name = self.current_direction

        # Vehicle direction characters - large block arrows for better volume
        vehicle_chars = {"north": "⬆", "east": "➡", "south": "⬇", "west": "⬅"}

        return vehicle_chars.get(direction_name, "•")

    def update_direction_display(self, direction):
        """Update vehicle direction (used by animation system)"""
        self.current_direction = direction
        self.refresh()

    def update_phase_color(self, phase):
        """Update vehicle phase color via CSS class"""
        self.current_phase = phase
        self._update_phase_class()
        self.refresh()

    def _update_phase_class(self):
        """Update CSS class based on current phase"""
        # Remove all phase classes (including pickup)
        self.remove_class("phase-p1", "phase-p2", "phase-p3", "phase-pickup")

        """Get the appropriate character for this vehicle (color via CSS)"""
        # Show reference mark during pickup (passenger boarding)
        if (
            self.vehicle.pickup_countdown is not None
            and self.vehicle.pickup_countdown > 0
        ):
            self.add_class("phase-pickup")
            return

        # Add the appropriate phase class
        if self.current_phase == "P1":
            self.add_class("phase-p1")
        elif self.current_phase == "P2":
            self.add_class("phase-p2")
        elif self.current_phase == "P3":
            self.add_class("phase-p3")

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
        self.previous_locations = {}

    def add_vehicle(self, vehicle_id, vehicle):
        """Add a vehicle widget to this layer"""
        if vehicle_id not in self.vehicle_widgets:
            # Pass static_grid reference for reactive spacing
            vehicle_widget = VehicleWidget(vehicle, self.map_size, self.static_grid)
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
            if vehicle_id in self.previous_locations:
                del self.previous_locations[vehicle_id]

    def update_vehicles(self, vehicles, animation_delay=1.0, frame_index=0):
        """Update all vehicles with proper frame-based timing

        Frame-based approach matching Chart.js:
        - Even frames (0,2,4...): Vehicles at intersections
        - Odd frames (1,3,5...): Vehicles at midpoints
        """
        try:
            current_vehicle_ids = set(id(v) for v in vehicles)

            # Get current spacing from static grid
            h_spacing, v_spacing = self.static_grid._calculate_spacing()
            self._handle_batch_edge_wrapping()

            # Remove vehicles that no longer exist
            existing_ids = set(self.vehicle_widgets.keys())
            for vehicle_id in existing_ids - current_vehicle_ids:
                self.remove_vehicle(vehicle_id)

            # Add new vehicles or update existing ones
            for vehicle in vehicles:
                vehicle_id = id(vehicle)
                current_location = (vehicle.location[0], vehicle.location[1])
                current_direction = getattr(vehicle.direction, "name", "north").lower()
                current_phase = getattr(vehicle.phase, "name", "P1")

                if vehicle_id not in self.vehicle_widgets:
                    # New vehicle - add without animation
                    self.add_vehicle(vehicle_id, vehicle)
                    self.previous_locations[vehicle_id] = current_location
                else:
                    # Update existing vehicle
                    vehicle_widget = self.vehicle_widgets[vehicle_id]
                    vehicle_widget.vehicle = vehicle
                    vehicle_widget.location = vehicle.location

                    # Update phase class to check for pickup_countdown changes
                    vehicle_widget._update_phase_class()
                    vehicle_widget.refresh()

                    if frame_index % 2 == 0:
                        # Even frame: Vehicles should be at intersections
                        previous_location = self.previous_locations.get(
                            vehicle_id, current_location
                        )

                        if previous_location != current_location:
                            # Check if current position needs edge wrapping
                            animation_duration = 0.9 * animation_delay
                            vehicle_widget.move_to_intersection(
                                vehicle_id=vehicle_id,
                                new_direction=current_direction,
                                new_phase=current_phase,
                                animation_duration=animation_duration,
                            )
                            self.previous_locations[vehicle_id] = current_location
                    else:
                        # Odd frame: Move vehicles to midpoints
                        # Update target state from current vehicle state
                        vehicle_widget.target_direction = current_direction
                        vehicle_widget.target_phase = current_phase
                        vehicle_widget.move_to_midpoint(frame_index)
        except Exception as e:
            print(f"Exception in update_vehicles: {e}")

    def _handle_batch_edge_wrapping(self):
        """Handle batch edge wrapping for multiple vehicles (Chart.js pattern)

        Mirrors Chart.js logic:
        - Suppress animations for all wrapped vehicles
        - Update positions instantly to opposite edges
        - Refresh display once for all changes
        """
        # Batch update all vehicles that need edge wrapping
        try:
            for vehicle_widget in self.vehicle_widgets.values():
                # Calculate wrapped position using Chart.js thresholds
                if vehicle_widget.needs_edge_wrapping:
                    vehicle_widget.calculate_wrapped_location()

                    # Instant update without animation (equivalent to chart.update("none"))
                    # update_offset_immediately() now gets spacing dynamically
                    vehicle_widget.update_offset_immediately()
                    vehicle_widget.is_animating = False
                    vehicle_widget.needs_edge_wrapping = False
        except Exception as e:
            print(f"Exception in _handle_batch_edge_wrapping: {e}")

    def get_vehicle_at_location(self, city_x, city_y):
        """Get vehicle widget at the specified position"""
        for vehicle_widget in self.vehicle_widgets.values():
            vehicle = vehicle_widget.vehicle
            vx, vy = vehicle.location[0], vehicle.location[1]
            # Simple proximity check
            if abs(vx - city_x) < 0.5 and abs(vy - city_y) < 0.5:
                return vehicle_widget
        return None

    def get_vehicle_count(self):
        """Get current number of vehicles in layer"""
        return len(self.vehicle_widgets)

    def render(self) -> RenderResult:
        """Render empty - vehicles will be positioned absolutely via native animation"""
        return ""


class TripMarkerWidget(Static):
    """Individual trip marker widget"""

    def __init__(self, marker_type, city_coords, map_size, static_grid, **kwargs):
        super().__init__(**kwargs)
        self.marker_type = marker_type  # "origin" or "destination"
        self.city_coords = city_coords
        self.map_size = map_size
        self.static_grid = static_grid  # Reference to get dynamic spacing

        # Get current spacing dynamically
        h_spacing, v_spacing = self.static_grid._calculate_spacing()

        # Set position
        self.styles.offset = location_to_offset(
            self.city_coords[0],
            self.city_coords[1],
            self.map_size,
            h_spacing,
            v_spacing,
        )

        # Set CSS class for marker type color
        if self.marker_type == "origin":
            self.add_class("trip-origin")
        elif self.marker_type == "destination":
            self.add_class("trip-destination")

    def render(self) -> RenderResult:
        """Render the trip marker character (color via CSS)"""
        if self.marker_type == "origin":
            # Use cached terminal capability check for efficiency
            if _detect_emoji_support():
                return ":adult:"
            else:
                return "●"  # Color applied via CSS class
        elif self.marker_type == "destination":
            if _detect_emoji_support():
                return ":house:"
            else:
                return "★"  # Color applied via CSS class
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
        # Always collect trip data (like Chart.js tripLocations, tripColors, tripStyles)
        trip_data = []
        current_trip_ids = set()

        for trip in trips.values():
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
            self._update_trip_marker_display(trip_data, map_size)

        # Always handle removal of completed/cancelled trips (regardless of frame)
        existing_ids = set(self.trip_marker_widgets.keys())
        for trip_id in existing_ids - current_trip_ids:
            if trip_id in self.trip_marker_widgets:
                marker_widget = self.trip_marker_widgets[trip_id]
                marker_widget.remove()
                del self.trip_marker_widgets[trip_id]

    def _update_trip_marker_display(self, trip_data, map_size):
        """Update the actual trip marker display (called only on odd frames)"""
        for trip_id, marker_type, coords in trip_data:
            if trip_id not in self.trip_marker_widgets:
                # Create new marker widget with static_grid reference
                marker_widget = TripMarkerWidget(
                    marker_type, coords, map_size, self.static_grid
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
                        marker_type, coords, map_size, self.static_grid
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

    DEFAULT_CSS = (
        RidehailTextualApp.CSS
        + """

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
            color: $secondary;
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
            text-style: bold;
        }

        VehicleWidget.phase-p1 {
            color: deepskyblue;
        }

        VehicleWidget.phase-p2 {
            color: gold;
        }

        VehicleWidget.phase-pickup {
            color: black;
            background: yellow;
        }

        VehicleWidget.phase-p3 {
            color: lime;
        }

        TripMarkerWidget {
            width:  1;
            height: 1;
            visibility: visible;
            dock: top;
            text-style: bold;
        }

        TripMarkerWidget.trip-origin {
            color: orange;
        }

        TripMarkerWidget.trip-destination {
            color: lime;
        }
        """
    )

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
        self.vehicle_previous_locations = {}
        self.vehicle_current_locations = {}

    def compose(self) -> ComposeResult:
        """Compose all map layers with proper z-ordering"""
        yield self.static_grid
        yield self.trip_layer
        yield self.vehicle_layer

    def update_vehicle_locations(self):
        """Update vehicle position tracking for interpolation (temporary)"""
        self.vehicle_previous_locations = self.vehicle_current_locations.copy()

        self.vehicle_current_locations = {}
        for vehicle in self.sim.vehicles:
            vehicle_id = id(vehicle)
            self.vehicle_current_locations[vehicle_id] = (
                vehicle.location[0],
                vehicle.location[1],
            )

            if vehicle_id not in self.vehicle_previous_locations:
                self.vehicle_previous_locations[vehicle_id] = (
                    self.vehicle_current_locations[vehicle_id]
                )

    def render(self) -> RenderResult:
        """Render empty - all content is handled by layered child widgets"""
        return ""

    def update_map(self, frame_index: int, update_locations: bool = False):
        """Update the map display for the given frame"""
        if update_locations:
            self.update_vehicle_locations()

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

    CSS = (
        RidehailTextualApp.CSS
        + """
    /* Map-specific styling */

    #map_container {
        width: 1fr;
        height: 1fr;
    }
    """
    )

    def __init__(self, sim, animation=None, **kwargs):
        super().__init__(sim, animation, **kwargs)
        self.frame_index = 0
        self.current_step_vehicles = (
            None  # Store vehicle state for both frames of current step
        )

    def compose(self) -> ComposeResult:
        """Create child widgets for the map app"""
        from textual.containers import Horizontal
        from .terminal_base import ConfigPanel

        yield self.create_header()

        # Check if terminal is wide enough for config panel
        # Note: self.size may not be available yet in compose(),
        # so we use console.size instead
        terminal_width = (
            self.console.size.width if hasattr(self.console, "size") else 80
        )

        if terminal_width >= 100:
            # Two-column layout with config panel
            with Horizontal(id="layout_container"):
                yield MapContainer(self.sim, id="map_container")
                yield ConfigPanel(self.sim, id="config_panel")
        else:
            # Single-column layout (current behavior)
            yield MapContainer(self.sim, id="map_container")

        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts"""
        version = self.sim.config.version.value
        self.title = f"Ridehail Simulation - version {version}"
        self.start_simulation()

    def _execute_simulation_step(self) -> None:
        """Execute one simulation step as two animation frames (Template Method hook)

        Each simulation step consists of:
        - Frame 0 (even): Vehicles at intersections, advance simulation
        - Frame 1 (odd): Vehicles at midpoints (interpolated locations)
        """
        try:
            # Get map container
            map_container = self.query_one("#map_container", expect_type=MapContainer)

            if self.frame_index % 2 == 0:
                # Even frame: Real simulation step - vehicles reach intersections
                self.sim.next_block(
                    jsonl_file_handle=None,
                    csv_file_handle=None,
                    return_values="stats",
                )

                # Store current vehicle state for interpolation frame
                self.current_step_vehicles = list(self.sim.vehicles)

                # Update map display - Frame 0: vehicles at intersections
                map_container.update_map(self.frame_index, update_locations=True)

            else:
                # Odd frame: Interpolation frame - vehicles at midpoints
                # Don't advance simulation, just update display with interpolated locations
                map_container.update_map(self.frame_index, update_locations=False)

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
        return TextualMapApp(self.sim, animation=self)
