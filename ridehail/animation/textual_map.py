"""
Textual-based map animation for ridehail simulation - simplified map-only version.
"""

from textual.app import ComposeResult
from textual.widgets import (
    Header,
    Footer,
)
from textual.widget import Widget
from textual.geometry import Offset
from rich.console import RenderResult

from .textual_base import TextualBasedAnimation, RidehailTextualApp


# Fast epsilon for floating point comparisons (more efficient than math.isclose)
EPSILON = 1e-9


def _is_close_to_integer(value, epsilon=EPSILON):
    """Check if a value is close to an integer."""
    return abs(value - round(value)) < epsilon


def city_to_display_offset(city_x, city_y, map_size, h_spacing, v_spacing):
    """Convert city coordinates to display offset using coordinate transformation.

    Args:
        city_x, city_y: City coordinates
        map_size: Size of the city grid
        h_spacing, v_spacing: Character spacing per city unit

    Returns:
        Offset: Display coordinates for positioning widgets
    """
    # Wrap coordinates to handle city boundaries
    city_x = city_x % map_size
    city_y = city_y % map_size

    h_shift = round(0.5 * h_spacing)
    v_shift = round(0.5 * v_spacing)

    display_x = int((city_x * h_spacing) + h_shift)
    display_y = int((map_size - city_y) * v_spacing) - v_shift

    return Offset(display_x, display_y)


# ============================================================================
# LAYER-BASED ARCHITECTURE - Phase 1 Step 1
# ============================================================================


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

    def _get_road_character(self, x, y):
        """Get the appropriate road/intersection character for
        position (x, y) in new coordinate range"""
        city_x_at_intersection = _is_close_to_integer(x)
        city_y_at_intersection = _is_close_to_integer(y)

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
    """Individual vehicle widget with positioning and native Textual animation"""

    def __init__(self, vehicle, map_size, h_spacing, v_spacing, **kwargs):
        super().__init__(**kwargs)
        self.vehicle = vehicle
        self.map_size = map_size
        self.h_spacing = h_spacing
        self.v_spacing = v_spacing

        # Animation state tracking
        self.current_direction = getattr(vehicle.direction, "name", "north").lower()
        self.current_phase = getattr(vehicle.phase, "name", "P1")
        self.is_animating = False

        # Set initial position based on vehicle location
        initial_offset = city_to_display_offset(
            vehicle.location[0],
            vehicle.location[1],
            self.map_size,
            self.h_spacing,
            self.v_spacing,
        )
        self.styles.offset = initial_offset

    def move_and_update(
        self, destination_city_coords, new_direction, new_phase, duration=1.0
    ):
        """Native Textual animation with midpoint state updates"""
        # TS if self.is_animating:
        # TS return  # Skip if already animating

        self.is_animating = True

        # Store animation parameters
        self._animation_destination = destination_city_coords
        self._animation_new_direction = new_direction
        self._animation_new_phase = new_phase
        self._animation_duration = duration

        # Get current position for midpoint calculation
        current_offset = self.styles.offset or Offset(0, 0)
        destination_offset = city_to_display_offset(
            destination_city_coords[0],
            destination_city_coords[1],
            self.map_size,
            self.h_spacing,
            self.v_spacing,
        )
        # TS print(
        # TS (
        # TS f"Vehicle moving to city {destination_city_coords}, "
        # TS f"display {destination_offset}"
        # TS )
        # TS )

        # Extract numeric values safely
        current_x = (
            getattr(current_offset.x, "value", current_offset.x)
            if hasattr(current_offset, "x")
            else 0
        )
        current_y = (
            getattr(current_offset.y, "value", current_offset.y)
            if hasattr(current_offset, "y")
            else 0
        )

        # Calculate midpoint (intersection center)
        mid_x = (current_x + destination_offset.x) / 2
        mid_y = (current_y + destination_offset.y) / 2
        midpoint = Offset(int(mid_x), int(mid_y))

        # Stage 1: Move to midpoint using native Textual animation
        self.animate(
            "offset",
            value=midpoint,
            duration=duration / 2,
            on_complete=self._midpoint_state_update,
        )

    def _midpoint_state_update(self):
        """Update vehicle state at midpoint (direction, phase, visual effects)"""
        # Update direction arrow and phase color at logical intersection point
        direction_changed = False
        phase_changed = False

        if self._animation_new_direction != self.current_direction:
            self.current_direction = self._animation_new_direction
            direction_changed = True

        if self._animation_new_phase != self.current_phase:
            self.current_phase = self._animation_new_phase
            phase_changed = True

        # Trigger re-render if state changed
        if direction_changed or phase_changed:
            self.refresh()

        # Stage 2: Continue to final destination using native Textual animation
        final_destination = city_to_display_offset(
            self._animation_destination[0],
            self._animation_destination[1],
            self.map_size,
            self.h_spacing,
            self.v_spacing,
        )

        self.animate(
            "offset",
            value=final_destination,
            duration=self._animation_duration / 2,
            on_complete=self._animation_complete,
        )

    def _animation_complete(self):
        """Called when animation sequence is complete"""
        self.is_animating = False

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
        direction_name = self.current_direction

        # Vehicle direction characters
        vehicle_chars = {"north": "▲", "east": "►", "south": "▼", "west": "◄"}
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

    def add_vehicle(self, vehicle_id, vehicle):
        """Add a vehicle widget to this layer"""
        if vehicle_id not in self.vehicle_widgets:
            # Get current spacing from static grid
            h_spacing, v_spacing = self.static_grid._calculate_spacing()
            vehicle_widget = VehicleWidget(vehicle, self.map_size, h_spacing, v_spacing)
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

    def update_vehicles(self, vehicles, frame_timeout=1.0):
        """Update all vehicles in the layer with optional native animation"""
        current_vehicle_ids = set(id(v) for v in vehicles)

        # Get current spacing from static grid
        h_spacing, v_spacing = self.static_grid._calculate_spacing()

        # Update spacing for all existing vehicle widgets
        for vehicle_widget in self.vehicle_widgets.values():
            vehicle_widget.update_spacing(h_spacing, v_spacing)

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

                # Check if position changed for animation
                previous_pos = self.previous_positions.get(vehicle_id, current_pos)

                if previous_pos != current_pos:
                    # Trigger native Textual animation with midpoint strategy
                    vehicle_widget.move_and_update(
                        current_pos,
                        current_direction,
                        current_phase,
                        duration=frame_timeout,
                    )

                # Store current position for next frame
                self.previous_positions[vehicle_id] = current_pos

    def get_vehicle_at_position(self, city_x, city_y):
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


class TripMarkerWidget(Widget):
    """Individual trip marker widget"""

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
        print(
            (
                f"Marker {self.marker_type} at city {self.city_coords}, "
                f"display {self.styles.offset}"
            )
        )
        if self.marker_type == "origin":
            return "[orange3]●[/orange3]"
        elif self.marker_type == "destination":
            return "[green1]★[/green1]"
        return "?"


class TripMarkerLayer(Widget):
    """Container for trip origin and destination markers using individual widgets"""

    def __init__(self, map_size, static_grid, **kwargs):
        super().__init__(**kwargs)
        self.map_size = map_size
        self.static_grid = static_grid
        self.trip_marker_widgets = {}  # trip_id -> widget

    def update_trip_markers(self, trips, map_size):
        """Update trip marker widgets"""
        current_trip_ids = set()
        h_spacing, v_spacing = self.static_grid._calculate_spacing()

        # Track which trips should have markers
        for trip in trips:
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
                elif trip.phase.name == "RIDING":
                    # Show destination marker
                    marker_type = "destination"
                    coords = (int(trip.destination[0]), int(trip.destination[1]))
                elif trip.phase.name in ("COMPLETED", "CANCELLED"):
                    self.trip_marker_widgets[trip_id].remove()
                    continue
                else:
                    continue

                if trip_id not in self.trip_marker_widgets:
                    # Create new marker widget
                    marker_widget = TripMarkerWidget(
                        marker_type, coords, map_size, h_spacing, v_spacing
                    )
                    self.trip_marker_widgets[trip_id] = marker_widget
                    self.mount(marker_widget)
                else:
                    # Check if existing marker needs to be updated
                    existing_widget = self.trip_marker_widgets[trip_id]
                    if existing_widget.marker_type != marker_type:
                        existing_widget.remove()
                    if (
                        existing_widget.marker_type == "origin"
                        and marker_type == "destination"
                    ):
                        # Create new one
                        marker_widget = TripMarkerWidget(
                            marker_type, coords, map_size, h_spacing, v_spacing
                        )
                        self.trip_marker_widgets[trip_id] = marker_widget
                        self.mount(marker_widget)

        # Remove markers for trips that no longer exist
        existing_ids = set(self.trip_marker_widgets.keys())
        for trip_id in existing_ids - current_trip_ids:
            marker_widget = self.trip_marker_widgets[trip_id]
            marker_widget.remove()
            del self.trip_marker_widgets[trip_id]

    def render(self) -> RenderResult:
        """Render empty - trip markers are positioned as child widgets"""
        return ""


class MapContainer(Widget):
    """Container that composes all map layers together"""

    DEFAULT_CSS = """
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
        width: 1;
        height: 1;
        visibility: visible;
        dock: top;
    }

    TripMarkerWidget {
        width: 1;
        height: 1;
        visibility: visible;
        dock: top;
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
        frame_timeout = self.sim.config.frame_timeout.value
        if frame_timeout is None:
            frame_timeout = self.sim.config.frame_timeout.default

        self.vehicle_layer.update_vehicles(
            self.sim.vehicles, frame_timeout=frame_timeout
        )

        # Update trip markers
        self.trip_layer.update_trip_markers(self.sim.trips, self.map_size)

        # All layers refresh automatically as child widgets


class TextualMapApp(RidehailTextualApp):
    """Textual app using native animation with MapContainer"""

    def __init__(self, sim, animation=None, **kwargs):
        super().__init__(sim, animation, **kwargs)
        self.frame_index = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the map app"""
        yield Header()
        yield MapContainer(self.sim, id="map_container")
        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts"""
        self.title = (
            f"Ridehail Map - Block {self.sim.block_index}/{self.sim.time_blocks}"
        )
        self.start_simulation()

    def simulation_step(self) -> None:
        """Simulation step with native animation"""
        if self.is_paused:
            return

        try:
            # Get map container
            map_container = self.query_one("#map_container", expect_type=MapContainer)

            # Advance simulation
            results = self.sim.next_block(
                jsonl_file_handle=None,
                csv_file_handle=None,
                return_values="stats",
                dispatch=self.animation.dispatch,
            )

            # Update title to show progress
            self.title = (
                f"Ridehail Map - Block {self.sim.block_index}/{self.sim.time_blocks}"
            )

            # Update map display with native animation
            map_container.update_map(self.frame_index, update_positions=True)

            # Increment frame counter
            self.frame_index += 1

            # Check if simulation is complete
            if (
                self.sim.time_blocks > 0
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
