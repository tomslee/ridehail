"""
Textual-based map animation for ridehail simulation - simplified map-only version.
"""

from textual.app import ComposeResult
from textual.widgets import (
    Header,
    Footer,
)
from textual.widget import Widget
from textual.reactive import reactive
from textual.geometry import Offset
from rich.console import RenderResult
from rich.panel import Panel

from .textual_base import TextualBasedAnimation, RidehailTextualApp


# Fast epsilon for floating point comparisons (more efficient than math.isclose)
EPSILON = 1e-9


def _is_close_to_integer(value, epsilon=EPSILON):
    """Check if a value is close to an integer."""
    return abs(value - round(value)) < epsilon


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
        "empty_space": "[dim]·[/dim]",
    }

    def __init__(self, map_size, **kwargs):
        super().__init__(**kwargs)
        self.map_size = map_size

        # Caching for spacing calculations (performance optimization)
        self._cached_spacing = None
        self._last_widget_size = None

    def _get_road_character(self, x, y):
        """Get the appropriate road/intersection character for position (x, y)"""
        # Intersections
        if _is_close_to_integer(x) and _is_close_to_integer(y):
            return self.MAP_CHARS["intersection"]
        # road segments
        elif _is_close_to_integer(x):
            return self.MAP_CHARS["road_vertical"]
        elif _is_close_to_integer(y):
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

        # Debug: ensure we always return something visible
        if h_spacing <= 0 or v_spacing <= 0:
            return "[red]Grid Error: Invalid spacing[/red]"

        map_lines = []

        # Use the same display-to-city coordinate transformation as original
        for y in range(v_spacing * self.map_size, 0, -1):
            line_chars = []
            # Transform display coordinates to city coordinates
            city_y = y / v_spacing
            for x in range(h_spacing * self.map_size):
                # Transform display coordinates to city coordinates
                city_x = x / h_spacing
                char = self._get_road_character(city_x, city_y)
                line_chars.append(char)
            map_lines.append("".join(line_chars))

        # Ensure we have content
        if not map_lines:
            return "[yellow]Grid: No content generated[/yellow]"

        return "\n".join(map_lines)


class VehicleWidget(Widget):
    """Individual vehicle widget with positioning and native Textual animation"""

    # CSS for smooth transitions
    DEFAULT_CSS = """
    VehicleWidget {
        transition: offset 0.5s linear;
        visibility: visible;
    }
    """

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
        initial_offset = self._city_to_display_offset(
            vehicle.location[0], vehicle.location[1]
        )
        self.styles.offset = initial_offset

    def _city_to_display_offset(self, city_x, city_y):
        """Convert city coordinates to display offset"""
        # Wrap coordinates to handle city boundaries
        city_x = city_x % self.map_size
        city_y = city_y % self.map_size

        # Convert to display coordinates
        # Add 1 to account for MapContainer panel border
        display_x = int(city_x * self.h_spacing) + 1
        display_y = int((self.map_size - city_y) * self.v_spacing) + 1

        return Offset(display_x, display_y)

    def move_and_update(
        self, destination_city_coords, new_direction, new_phase, duration=1.0
    ):
        """Timer-based two-stage animation with midpoint state updates (preserves all benefits)"""
        if self.is_animating:
            return  # Skip if already animating

        self.is_animating = True

        # Store animation parameters
        self._animation_destination = destination_city_coords
        self._animation_new_direction = new_direction
        self._animation_new_phase = new_phase
        self._animation_duration = duration

        # Get current position for midpoint calculation
        current_offset = self.styles.offset or Offset(0, 0)
        destination_offset = self._city_to_display_offset(
            destination_city_coords[0], destination_city_coords[1]
        )

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

        # Stage 1: Move to midpoint using CSS transitions
        self.styles.offset = Offset(int(mid_x), int(mid_y))
        self.styles.transitions = {"offset": f"{duration/2}s"}

        # Schedule midpoint state update
        self.set_timer(duration / 2, self._midpoint_state_update)

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

        # Stage 2: Continue to final destination
        final_destination = self._city_to_display_offset(
            self._animation_destination[0], self._animation_destination[1]
        )

        self.styles.offset = final_destination
        self.styles.transitions = {"offset": f"{self._animation_duration/2}s"}

        # Schedule animation completion
        self.set_timer(self._animation_duration / 2, self._animation_complete)

    def _animation_complete(self):
        """Called when animation sequence is complete"""
        self.is_animating = False

    def update_position_immediately(self, city_coords):
        """Update position immediately without animation (for initialization)"""
        new_offset = self._city_to_display_offset(city_coords[0], city_coords[1])
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

    def update_vehicles_with_animation(self, vehicles, use_animation=True):
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

                if use_animation and previous_pos != current_pos:
                    # Trigger native Textual animation with midpoint strategy
                    vehicle_widget.move_and_update(
                        current_pos, current_direction, current_phase, duration=1.0
                    )
                else:
                    # Update immediately without animation
                    vehicle_widget.update_position_immediately(current_pos)
                    vehicle_widget.current_direction = current_direction
                    vehicle_widget.current_phase = current_phase

                # Store current position for next frame
                self.previous_positions[vehicle_id] = current_pos
                print((f"Vehicle {vehicle_id} at {current_pos}"))

    def update_vehicles(self, vehicles):
        """Update all vehicles in the layer (legacy method, no animation)"""
        self.update_vehicles_with_animation(vehicles, use_animation=False)

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
        self.styles.offset = self._city_to_display_offset()

    def _city_to_display_offset(self):
        """Convert city coordinates to display offset"""
        city_x, city_y = self.city_coords
        city_x = city_x % self.map_size
        city_y = city_y % self.map_size

        # Add 1 to account for MapContainer panel border
        display_x = int(city_x * self.h_spacing) + 1
        display_y = int((self.map_size - city_y) * self.v_spacing) + 1

        return Offset(display_x, display_y)

    def render(self) -> RenderResult:
        """Render the trip marker character"""
        if self.marker_type == "origin":
            return "[orange3]●[/orange3]"
        elif self.marker_type == "destination":
            return "[green]★[/green]"
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

        # Add a debug marker at (0,0) if no trips exist
        if len(trips) == 0:
            debug_trip_id = "debug_marker"
            current_trip_ids.add(debug_trip_id)
            if debug_trip_id not in self.trip_marker_widgets:
                marker_widget = TripMarkerWidget(
                    "origin", (0, 0), map_size, h_spacing, v_spacing
                )
                self.trip_marker_widgets[debug_trip_id] = marker_widget
                self.mount(marker_widget)

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
                else:
                    continue

                if trip_id not in self.trip_marker_widgets:
                    # Create new marker widget
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
    }

    TripMarkerWidget {
        width: 1;
        height: 1;
        visibility: visible;
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
        self.vehicle_layer.update_vehicles_with_animation(
            self.sim.vehicles, use_animation=True
        )

        # Update trip markers
        self.trip_layer.update_trip_markers(self.sim.trips, self.map_size)

        # All layers refresh automatically as child widgets


# ============================================================================
# ORIGINAL MAPWIDGET (PRESERVED FOR REFERENCE)
# ============================================================================


class MapWidget(Widget):
    """Simple Unicode map widget for displaying ridehail simulation"""

    # Reactive attributes for automatic re-rendering
    frame_index: reactive[int] = reactive(0)

    # Unicode characters for map rendering (from Rich terminal_map.py)
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

    # Vehicle direction characters
    VEHICLE_CHARS = {"north": "▲", "east": "►", "south": "▼", "west": "◄"}

    # Trip markers
    TRIP_CHARS = {"origin": "●", "destination": "★"}

    # Pre-formatted colored vehicle characters (avoids string formatting in hot path)
    COLORED_VEHICLES = {
        "P1": {  # Idle vehicles - steel blue
            "north": "[sky_blue1]▲[/sky_blue1]",
            "east": "[sky_blue1]►[/sky_blue1]",
            "south": "[sky_blue1]▼[/sky_blue1]",
            "west": "[sky_blue1]◄[/sky_blue1]",
        },
        "P2": {  # Dispatched vehicles - orange
            "north": "[orange3]▲[/orange3]",
            "east": "[orange3]►[/orange3]",
            "south": "[orange3]▼[/orange3]",
            "west": "[orange3]◄[/orange3]",
        },
        "P3": {  # Occupied vehicles - green
            "north": "[green]▲[/green]",
            "east": "[green]►[/green]",
            "south": "[green]▼[/green]",
            "west": "[green]◄[/green]",
        },
    }

    # Pre-formatted colored trip markers
    COLORED_TRIP_ORIGIN = "[orange3]●[/orange3]"
    COLORED_TRIP_DESTINATION = "[green]★[/green]"

    def __init__(self, sim, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim
        # Let's say the map_size is city_size, but for large values it is
        # capped because the map could not be reasonably depicted with one
        # character per intersection at larger sizes.
        # TS: Let's just let the map_size be the same as the city_size.
        self.map_size = min(sim.city.city_size, 250)  # Reasonable max size

        # Animation properties (from Rich terminal_map.py)
        self.interpolation_points = sim.interpolate
        self.current_interpolation_points = self.interpolation_points
        # frame_index is now a reactive attribute (defined at class level)

        # Vehicle position tracking for smooth interpolation
        self.vehicle_previous_positions = {}
        self.vehicle_current_positions = {}

        # Caching for spacing calculations (performance optimization)
        self._cached_spacing = None
        self._last_widget_size = None

        # Native animation support (Step 5 enhancement)
        self.use_native_animation = False  # Start with legacy mode for compatibility
        self.vehicle_layer = (
            None  # Will be initialized when native animation is enabled
        )

    def enable_native_animation(self):
        """Enable native Textual animation with VehicleLayer"""
        if not self.use_native_animation:
            # Create static grid for coordinate calculations
            static_grid = StaticMapGrid(self.map_size)
            self.vehicle_layer = VehicleLayer(self.map_size, static_grid)
            self.use_native_animation = True

    def disable_native_animation(self):
        """Disable native animation, use legacy interpolation"""
        self.use_native_animation = False
        self.vehicle_layer = None

    def toggle_animation_mode(self):
        """Toggle between native and legacy animation modes"""
        if self.use_native_animation:
            self.disable_native_animation()
            return "Legacy interpolation mode"
        else:
            self.enable_native_animation()
            return "Native animation mode"

    def _interpolation(self, frame_index):
        """Calculate interpolation step (distance from current sim position)
        for smooth vehicle movement"""
        return frame_index % (self.current_interpolation_points + 1)

    def update_vehicle_positions(self):
        """Update vehicle position tracking for interpolation"""
        # TS: these positions are in City coordinates, and reflect
        # TS: simulation steps (not interpolations)
        # Store previous positions
        self.vehicle_previous_positions = self.vehicle_current_positions.copy()

        # Update current positions
        self.vehicle_current_positions = {}
        for vehicle in self.sim.vehicles:
            # Use vehicle ID or create a unique identifier
            vehicle_id = id(vehicle)  # Use object ID as unique identifier
            self.vehicle_current_positions[vehicle_id] = (
                vehicle.location[0],
                vehicle.location[1],
            )

            # If this is the first time seeing this vehicle, set previous = current
            if vehicle_id not in self.vehicle_previous_positions:
                self.vehicle_previous_positions[vehicle_id] = (
                    self.vehicle_current_positions[vehicle_id]
                )

    def get_interpolated_position(self, vehicle, interpolation_step):
        """Get interpolated position for a vehicle based on interpolation step"""
        # TS: The interpolated positions are in City coordinates
        vehicle_id = id(vehicle)

        # Get current and previous positions
        sim_position = self.vehicle_current_positions.get(vehicle_id, vehicle.location)
        direction_name = vehicle.direction.name.lower()

        # Calculate interpolation factor (0.0 to 1.0)
        factor = interpolation_step / (self.current_interpolation_points + 1)

        interp_x = sim_position[0]
        interp_y = sim_position[1]
        # Linear interpolation between previous and current position
        if direction_name == "north":
            interp_y += factor
        elif direction_name == "east":
            interp_x += factor
        elif direction_name == "south":
            interp_y -= factor
        elif direction_name == "west":
            interp_x -= factor
        return (interp_x, interp_y)

    def _is_vehicle_closest_to_position(self, vx, vy, grid_x, grid_y):
        """Check if this grid position is the closest one to the vehicle's fractional position"""
        # TS: grid_x, grid_y are in city coordinates
        # TS: vx, vy are in city coordinates
        # TS: vehicles should be displayed only on roads!
        if not _is_close_to_integer(grid_x) and not _is_close_to_integer(grid_y):
            return False
        # Wrap coordinates to handle city boundaries
        vx = vx % self.map_size
        vy = vy % self.map_size

        # Calculate distance to this grid position
        dx = abs(vx - grid_x)
        dy = abs(vy - grid_y)

        # Handle wrapping at city boundaries
        dx = min(dx, self.map_size - dx)
        dy = min(dy, self.map_size - dy)

        # Check if this is the closest grid position
        # A vehicle appears at a grid position if it's within 1/(interpolation) units of it
        is_closest = dx < (0.5 / (self.current_interpolation_points + 1)) and dy < (
            0.5 / (self.current_interpolation_points + 1)
        )
        return is_closest

    def _create_interpolated_vehicle_positions(self, interpolation_step):
        """Pre-compute all vehicle interpolated positions for this frame"""
        interpolated_vehicles = []

        for vehicle in self.sim.vehicles:
            interp_pos = self.get_interpolated_position(vehicle, interpolation_step)
            vx, vy = interp_pos
            interpolated_vehicles.append((vx, vy, vehicle))

        return interpolated_vehicles

    def _find_vehicle_at_display_position(self, interpolated_vehicles, city_x, city_y):
        """Fast check if any vehicle should display at this city coordinate"""
        for vx, vy, vehicle in interpolated_vehicles:
            if self._is_vehicle_closest_to_position(vx, vy, city_x, city_y):
                return vehicle
        return None

    def _create_trip_markers_map(self):
        """Pre-compute trip origin and destination positions for fast lookups"""
        trip_origins = set()
        trip_destinations = set()

        for trip in self.sim.trips:
            if (
                hasattr(trip, "origin")
                and hasattr(trip, "destination")
                and hasattr(trip.phase, "name")
            ):
                # Calculate wrapped coordinates once per trip
                ox = int(trip.origin[0]) % self.map_size
                oy = int(trip.origin[1]) % self.map_size
                dx = int(trip.destination[0]) % self.map_size
                dy = int(trip.destination[1]) % self.map_size

                # Check trip phase and add to appropriate set
                if trip.phase.name in ("UNASSIGNED", "WAITING"):
                    trip_origins.add((ox, oy))
                elif trip.phase.name == "RIDING":
                    trip_destinations.add((dx, dy))

        return trip_origins, trip_destinations

    def _get_road_character(self, x, y):
        """Get the appropriate road/intersection character for position (x, y)"""
        # TS x,y are in City coordinates, but may be floating values
        # because of interpolation.
        # Intersections
        if _is_close_to_integer(x) and _is_close_to_integer(y):
            return self.MAP_CHARS["intersection"]
        # road segments
        elif _is_close_to_integer(x):
            return self.MAP_CHARS["road_vertical"]
        elif _is_close_to_integer(y):
            return self.MAP_CHARS["road_horizontal"]
        # interior spaces between roads
        else:
            return self.MAP_CHARS["empty_space"]

    def _calculate_spacing(self):
        """Calculate optimal spacing based on available terminal space with caching"""
        # The spacing is the integer number of pixels between intersections.
        # Get widget size (will be set by Textual layout)
        widget_size = self.size

        # Check cache - return cached result if widget size hasn't changed
        if widget_size == self._last_widget_size and self._cached_spacing is not None:
            return self._cached_spacing

        # Calculate spacing (widget size changed or first calculation)
        # Account for panel borders and padding (roughly 4 chars horizontal, 3 lines vertical)
        # available_width is the number of pixels.
        available_width = widget_size.width - 4
        available_height = widget_size.height - 3

        # Calculate spacing. The map is square, with sides self.map_size
        horizontal_spacing = available_width // self.map_size
        vertical_spacing = available_height // self.map_size
        # vertical_spacing = max(
        # 0, (available_height - self.map_size) // max(self.map_size - 1, 1)
        # )

        # Limit spacing to reasonable values
        horizontal_spacing = max(horizontal_spacing, 1)
        vertical_spacing = max(vertical_spacing, 1)

        # Cache the result
        self._last_widget_size = widget_size
        self._cached_spacing = (horizontal_spacing, vertical_spacing)

        return horizontal_spacing, vertical_spacing

    def _create_map_display(self):
        """Create the Unicode-based map display with optional native animation"""
        # Calculate dynamic spacing
        h_spacing, v_spacing = self._calculate_spacing()

        # Handle vehicle rendering based on animation mode
        if self.use_native_animation and self.vehicle_layer is not None:
            # Native animation mode: update vehicle layer and render without vehicles in grid
            self.vehicle_layer.update_vehicles_with_animation(
                self.sim.vehicles, use_animation=True
            )
            interpolated_vehicles = []  # No vehicles in character grid - they're positioned absolutely
        else:
            # Legacy mode: use manual interpolation
            interpolation_step = self._interpolation(self.frame_index)
            interpolated_vehicles = self._create_interpolated_vehicle_positions(
                interpolation_step
            )

        # Pre-compute trip marker positions for fast lookups (performance optimization)
        trip_origins, trip_destinations = self._create_trip_markers_map()

        map_lines = []

        # Create grid representation - but allow fractional positions
        # TS: the grid representation is the displayed map grid, and so
        # TS: the range should go from 0 to .
        for y in range(v_spacing * self.map_size, 0, -1):
            line_chars = []  # Use list for efficient character collection
            city_y = (y - int(self.current_interpolation_points / 2)) / v_spacing
            for x in range(h_spacing * self.map_size):
                # (x,y) is in Display coordinates
                # Get base road character
                city_x = (x - int(self.current_interpolation_points / 2)) / h_spacing
                char = self._get_road_character(city_x, city_y)

                # Check for vehicles at this location (optimized: single lookup instead of nested loop)
                vehicle_here = self._find_vehicle_at_display_position(
                    interpolated_vehicles, city_x, city_y
                )

                # Check for trips at this location (optimized: O(1) set lookups instead of nested loop)
                # Only show trip markers at actual intersections (integer coordinates)
                trip_origin_here = False
                trip_dest_here = False
                if _is_close_to_integer(city_x) and _is_close_to_integer(city_y):
                    city_pos = (int(round(city_x)), int(round(city_y)))
                    trip_origin_here = city_pos in trip_origins
                    trip_dest_here = city_pos in trip_destinations

                # Priority: vehicles > trip destinations > trip origins > background
                if vehicle_here:
                    direction_name = (
                        vehicle_here.direction.name.lower()
                        if hasattr(vehicle_here.direction, "name")
                        else "north"
                    )
                    # Use pre-formatted colored vehicle characters (much faster than f-strings)
                    if (
                        hasattr(vehicle_here.phase, "name")
                        and vehicle_here.phase.name in self.COLORED_VEHICLES
                    ):
                        char = self.COLORED_VEHICLES[vehicle_here.phase.name].get(
                            direction_name, "•"
                        )
                    else:
                        # Fallback for unknown phases
                        char = self.VEHICLE_CHARS.get(direction_name, "•")
                elif trip_origin_here:
                    char = self.COLORED_TRIP_ORIGIN
                elif trip_dest_here:
                    char = self.COLORED_TRIP_DESTINATION
                else:
                    pass

                line_chars.append(
                    char
                )  # Efficient list append instead of string concatenation

                # Add horizontal spacing between characters (except after last character)
                # if x < self.map_size - 1:
                # line_chars.extend([" "] * h_spacing)

            map_lines.append("".join(line_chars))  # Single join operation per line

        return "\n".join(map_lines)

    def render(self) -> RenderResult:
        """Render the map widget"""
        map_display = self._create_map_display()

        # Create title with block info
        interpolation_info = ""
        if self.current_interpolation_points > 0:
            frame_in_cycle = self.frame_index % (self.current_interpolation_points + 1)
            interpolation_info = (
                f" (frame {frame_in_cycle}/{self.current_interpolation_points})"
            )

        title = f"City Map ({self.map_size}x{self.map_size}) - Block {self.sim.block_index}{interpolation_info}"

        return Panel(
            map_display, title=title, border_style="steel_blue", padding=(1, 1)
        )

    def update_map(self, frame_index: int, update_positions: bool = False):
        """Update the map display for the given frame (uses reactive rendering)"""
        # Update vehicle positions when simulation advances (not on interpolation frames)
        if update_positions:
            self.update_vehicle_positions()

        self.current_interpolation_points = self.interpolation_points
        # Setting reactive attribute automatically triggers re-render (no explicit refresh needed)
        self.frame_index = frame_index


class TextualMapApp(RidehailTextualApp):
    """Simple Textual app for map animation"""

    CSS = """
    MapContainer {
        border: solid $primary;
        padding: 1;
        height: 1fr;
        width: 1fr;
    }
    """

    BINDINGS = [
        ("q", "quit", "Quit"),
        ("space", "pause", "Pause/Resume"),
        ("n", "decrease_vehicles", "Vehicles -1"),
        ("N", "increase_vehicles", "Vehicles +1"),
        ("k", "decrease_demand", "Demand -0.1"),
        ("K", "increase_demand", "Demand +0.1"),
        ("c", "decrease_city", "City -1"),
        ("C", "increase_city", "City +1"),
    ]

    def __init__(self, sim, animation=None, **kwargs):
        super().__init__(sim, animation, **kwargs)
        self.frame_index = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the map app"""
        yield Header()
        yield MapContainer(self.sim, id="map_container")
        yield Footer()

    def on_mount(self) -> None:
        """Called when app starts - inherit timer from parent and set title"""
        self.title = (
            f"Ridehail Map - Block {self.sim.block_index}/{self.sim.time_blocks}"
        )
        self.start_simulation()

    def simulation_step(self) -> None:
        """Simulation step with map updates"""
        if self.is_paused:
            return

        try:
            # Get map container
            map_container = self.query_one("#map_container", expect_type=MapContainer)

            # Native animation mode: advance simulation every frame
            # Textual handles smooth movement automatically
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

            # Update map display - native animation handles vehicle movement
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

    # Keyboard actions for simulation control
    def action_decrease_vehicles(self) -> None:
        """Decrease vehicle count by 1"""
        self.sim.target_state["vehicle_count"] = max(
            self.sim.target_state["vehicle_count"] - 1, 0
        )

    def action_increase_vehicles(self) -> None:
        """Increase vehicle count by 1"""
        self.sim.target_state["vehicle_count"] += 1

    def action_decrease_demand(self) -> None:
        """Decrease base demand by 0.1"""
        self.sim.target_state["base_demand"] = max(
            self.sim.target_state["base_demand"] - 0.1, 0
        )

    def action_increase_demand(self) -> None:
        """Increase base demand by 0.1"""
        self.sim.target_state["base_demand"] += 0.1

    def action_decrease_city(self) -> None:
        """Decrease city size by 1"""
        new_size = max(
            self.sim.target_state.get("city_size", self.sim.city.city_size) - 1, 2
        )
        self.sim.target_state["city_size"] = new_size

    def action_increase_city(self) -> None:
        """Increase city size by 1"""
        new_size = self.sim.target_state.get("city_size", self.sim.city.city_size) + 1
        self.sim.target_state["city_size"] = new_size


class TextualMapAnimation(TextualBasedAnimation):
    """Simple Textual-based map animation focusing on the map display"""

    def create_app(self) -> TextualMapApp:
        """Create the Textual map app instance"""
        return TextualMapApp(self.sim, animation=self)
