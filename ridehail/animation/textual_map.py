"""
Textual-based map animation for ridehail simulation - simplified map-only version.
"""

from textual.app import ComposeResult
from textual.widgets import (
    Header,
    Footer,
)
from textual.widget import Widget
from rich.console import RenderResult
from rich.panel import Panel

from .textual_base import TextualBasedAnimation, RidehailTextualApp


# Fast epsilon for floating point comparisons (more efficient than math.isclose)
EPSILON = 1e-9


def _is_close_to_integer(value, epsilon=EPSILON):
    """Fast check if a value is close to an integer (more efficient than math.isclose)"""
    return abs(value - round(value)) < epsilon


class MapWidget(Widget):
    """Simple Unicode map widget for displaying ridehail simulation"""

    # Unicode characters for map rendering (from Rich terminal_map.py)
    MAP_CHARS = {
        "intersection": "┼",
        "road_horizontal": "─",
        "road_vertical": "│",
        "corner_tl": "┌",
        "corner_tr": "┐",
        "corner_bl": "└",
        "corner_br": "┘",
        "tee_up": "┴",
        "tee_down": "┬",
        "tee_left": "┤",
        "tee_right": "├",
        "empty_space": " ",
    }

    # Vehicle direction characters
    VEHICLE_CHARS = {"north": "▲", "east": "►", "south": "▼", "west": "◄"}

    # Trip markers
    TRIP_CHARS = {"origin": "●", "destination": "★"}

    # Pre-formatted colored vehicle characters (avoids string formatting in hot path)
    COLORED_VEHICLES = {
        "P1": {  # Idle vehicles - steel blue
            "north": "[steel_blue]▲[/steel_blue]",
            "east": "[steel_blue]►[/steel_blue]",
            "south": "[steel_blue]▼[/steel_blue]",
            "west": "[steel_blue]◄[/steel_blue]"
        },
        "P2": {  # Dispatched vehicles - orange
            "north": "[orange3]▲[/orange3]",
            "east": "[orange3]►[/orange3]",
            "south": "[orange3]▼[/orange3]",
            "west": "[orange3]◄[/orange3]"
        },
        "P3": {  # Occupied vehicles - green
            "north": "[green]▲[/green]",
            "east": "[green]►[/green]",
            "south": "[green]▼[/green]",
            "west": "[green]◄[/green]"
        }
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
        self.frame_index = 0

        # Vehicle position tracking for smooth interpolation
        self.vehicle_previous_positions = {}
        self.vehicle_current_positions = {}

        # Caching for spacing calculations (performance optimization)
        self._cached_spacing = None
        self._last_widget_size = None

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
            if hasattr(trip, "origin") and hasattr(trip, "destination") and hasattr(trip.phase, "name"):
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
        # TS: What is the "spacing"?
        # TS: It's the integer number of pixels between intersections.
        # Get widget size (will be set by Textual layout)
        widget_size = self.size

        # Check cache - return cached result if widget size hasn't changed
        if widget_size == self._last_widget_size and self._cached_spacing is not None:
            return self._cached_spacing

        # Calculate spacing (widget size changed or first calculation)
        # Account for panel borders and padding (roughly 4 chars horizontal, 3 lines vertical)
        # available_width is the number of pixels.
        # available_width = max(widget_size.width - 4, self.map_size)
        # available_height = max(widget_size.height - 3, self.map_size)
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
        """Create the Unicode-based map display with interpolation and dynamic spacing"""
        # Calculate interpolation step for smooth vehicle movement
        interpolation_step = self._interpolation(self.frame_index)

        # Calculate dynamic spacing
        h_spacing, v_spacing = self._calculate_spacing()

        # Pre-compute all vehicle interpolated positions once per frame (performance optimization)
        interpolated_vehicles = self._create_interpolated_vehicle_positions(interpolation_step)

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
                    if hasattr(vehicle_here.phase, "name") and vehicle_here.phase.name in self.COLORED_VEHICLES:
                        char = self.COLORED_VEHICLES[vehicle_here.phase.name].get(direction_name, "•")
                    else:
                        # Fallback for unknown phases
                        char = self.VEHICLE_CHARS.get(direction_name, "•")
                elif trip_origin_here:
                    char = self.COLORED_TRIP_ORIGIN
                elif trip_dest_here:
                    char = self.COLORED_TRIP_DESTINATION
                else:
                    pass

                line_chars.append(char)  # Efficient list append instead of string concatenation

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
        """Update the map display for the given frame"""
        self.frame_index = frame_index
        self.current_interpolation_points = self.interpolation_points

        # Update vehicle positions when simulation advances (not on interpolation frames)
        if update_positions:
            self.update_vehicle_positions()

        self.refresh()


class TextualMapApp(RidehailTextualApp):
    """Simple Textual app for map animation"""

    CSS = """
    MapWidget {
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
        yield MapWidget(self.sim, id="map_widget")
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
            # Get map widget to check interpolation
            map_widget = self.query_one("#map_widget", expect_type=MapWidget)
            interpolation_step = map_widget._interpolation(self.frame_index)

            # Only advance simulation on "real" time points (not interpolation frames)
            if interpolation_step == 0:
                results = self.sim.next_block(
                    jsonl_file_handle=None,
                    csv_file_handle=None,
                    return_values="stats",
                    dispatch=self.animation.dispatch,
                )

                # Update title to show progress
                self.title = f"Ridehail Map - Block {self.sim.block_index}/{self.sim.time_blocks}"

                # Store results for interpolation frames
                self._last_results = results

                # Update map display with new vehicle positions
                map_widget.update_map(self.frame_index, update_positions=True)
            else:
                # Update map display for interpolation frame (no position update)
                map_widget.update_map(self.frame_index, update_positions=False)

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
