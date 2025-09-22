"""
Textual-based map animation for ridehail simulation - simplified map-only version.
"""

from typing import Dict, Any
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    TabbedContent,
    TabPane,
    Header,
    Footer,
)
from textual.widget import Widget
from textual.reactive import reactive
from rich.console import RenderResult
from rich.text import Text
from rich.panel import Panel

from .textual_base import TextualBasedAnimation, RidehailTextualApp


class MapWidget(Widget):
    """Simple Unicode map widget for displaying ridehail simulation"""

    # Unicode characters for map rendering (from Rich terminal_map.py)
    MAP_CHARS = {
        'intersection': '┼',
        'road_horizontal': '─',
        'road_vertical': '│',
        'corner_tl': '┌',
        'corner_tr': '┐',
        'corner_bl': '└',
        'corner_br': '┘',
        'tee_up': '┴',
        'tee_down': '┬',
        'tee_left': '┤',
        'tee_right': '├'
    }

    # Vehicle direction characters
    VEHICLE_CHARS = {
        'north': '▲',
        'east': '►',
        'south': '▼',
        'west': '◄'
    }

    # Trip markers
    TRIP_CHARS = {
        'origin': '●',
        'destination': '★'
    }

    def __init__(self, sim, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim
        self.map_size = min(sim.city.city_size, 25)  # Reasonable max size

        # Animation properties (from Rich terminal_map.py)
        self.interpolation_points = sim.interpolate
        self.current_interpolation_points = self.interpolation_points
        self.frame_index = 0

        # Vehicle position tracking for smooth interpolation
        self.vehicle_previous_positions = {}
        self.vehicle_current_positions = {}

    def _interpolation(self, frame_index):
        """Calculate interpolation step for smooth vehicle movement"""
        return frame_index % (self.current_interpolation_points + 1)

    def update_vehicle_positions(self):
        """Update vehicle position tracking for interpolation"""
        # Store previous positions
        self.vehicle_previous_positions = self.vehicle_current_positions.copy()

        # Update current positions
        self.vehicle_current_positions = {}
        for vehicle in self.sim.vehicles:
            # Use vehicle ID or create a unique identifier
            vehicle_id = id(vehicle)  # Use object ID as unique identifier
            self.vehicle_current_positions[vehicle_id] = (vehicle.location[0], vehicle.location[1])

            # If this is the first time seeing this vehicle, set previous = current
            if vehicle_id not in self.vehicle_previous_positions:
                self.vehicle_previous_positions[vehicle_id] = self.vehicle_current_positions[vehicle_id]

    def get_interpolated_position(self, vehicle, interpolation_step):
        """Get interpolated position for a vehicle based on interpolation step"""
        vehicle_id = id(vehicle)

        # Get current and previous positions
        current_pos = self.vehicle_current_positions.get(vehicle_id, vehicle.location)
        previous_pos = self.vehicle_previous_positions.get(vehicle_id, vehicle.location)

        if interpolation_step == 0 or current_pos == previous_pos:
            # No interpolation needed
            return current_pos

        # Calculate interpolation factor (0.0 to 1.0)
        factor = interpolation_step / (self.current_interpolation_points + 1)

        # Linear interpolation between previous and current position
        interp_x = previous_pos[0] + (current_pos[0] - previous_pos[0]) * factor
        interp_y = previous_pos[1] + (current_pos[1] - previous_pos[1]) * factor

        return (interp_x, interp_y)

    def _is_vehicle_closest_to_position(self, vx, vy, grid_x, grid_y):
        """Check if this grid position is the closest one to the vehicle's fractional position"""
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
        # A vehicle appears at a grid position if it's within 0.5 units of it
        return dx < 0.5 and dy < 0.5

    def _get_road_character(self, x, y):
        """Get the appropriate road/intersection character for position (x, y)"""
        # Corners
        if x == 0 and y == 0:
            return self.MAP_CHARS['corner_bl']
        elif x == 0 and y == self.map_size - 1:
            return self.MAP_CHARS['corner_tl']
        elif x == self.map_size - 1 and y == 0:
            return self.MAP_CHARS['corner_br']
        elif x == self.map_size - 1 and y == self.map_size - 1:
            return self.MAP_CHARS['corner_tr']
        # Edges
        elif x == 0:  # Left edge
            return self.MAP_CHARS['tee_right']
        elif x == self.map_size - 1:  # Right edge
            return self.MAP_CHARS['tee_left']
        elif y == 0:  # Bottom edge
            return self.MAP_CHARS['tee_up']
        elif y == self.map_size - 1:  # Top edge
            return self.MAP_CHARS['tee_down']
        # Interior intersections
        else:
            return self.MAP_CHARS['intersection']

    def _calculate_spacing(self):
        """Calculate optimal spacing based on available terminal space"""
        # Get widget size (will be set by Textual layout)
        widget_size = self.size

        # Account for panel borders and padding (roughly 4 chars horizontal, 3 lines vertical)
        available_width = max(widget_size.width - 4, self.map_size)
        available_height = max(widget_size.height - 3, self.map_size)

        # Calculate spacing
        horizontal_spacing = max(0, (available_width - self.map_size) // max(self.map_size - 1, 1))
        vertical_spacing = max(0, (available_height - self.map_size) // max(self.map_size - 1, 1))

        # Limit spacing to reasonable values
        horizontal_spacing = min(horizontal_spacing, 8)
        vertical_spacing = min(vertical_spacing, 4)

        return horizontal_spacing, vertical_spacing

    def _create_map_display(self):
        """Create the Unicode-based map display with interpolation and dynamic spacing"""
        # Calculate interpolation step for smooth vehicle movement
        interpolation_step = self._interpolation(self.frame_index)

        # Calculate dynamic spacing
        h_spacing, v_spacing = self._calculate_spacing()

        map_lines = []

        # Create grid representation - but allow fractional positions
        for y in range(self.map_size):
            line = ""
            for x in range(self.map_size):
                # Get base road character
                char = self._get_road_character(x, y)

                # Check for vehicles at this location (with improved interpolation)
                vehicle_here = None
                for vehicle in self.sim.vehicles:
                    # Get interpolated position for this vehicle
                    interp_pos = self.get_interpolated_position(vehicle, interpolation_step)
                    vx, vy = interp_pos

                    # Simple approach: check if vehicle is closest to this grid position
                    if self._is_vehicle_closest_to_position(vx, vy, x, y):
                        vehicle_here = vehicle
                        break

                # Check for trips at this location
                trip_origin_here = False
                trip_dest_here = False
                for trip in self.sim.trips:
                    if hasattr(trip, 'origin') and hasattr(trip, 'destination'):
                        ox, oy = int(trip.origin[0]) % self.map_size, int(trip.origin[1]) % self.map_size
                        dx, dy = int(trip.destination[0]) % self.map_size, int(trip.destination[1]) % self.map_size

                        if ox == x and oy == y and hasattr(trip.phase, 'name') and trip.phase.name in ('UNASSIGNED', 'WAITING'):
                            trip_origin_here = True
                        elif dx == x and dy == y and hasattr(trip.phase, 'name') and trip.phase.name == 'RIDING':
                            trip_dest_here = True

                # Priority: vehicles > trip destinations > trip origins > background
                if vehicle_here:
                    direction_name = vehicle_here.direction.name.lower() if hasattr(vehicle_here.direction, 'name') else 'north'
                    char = self.VEHICLE_CHARS.get(direction_name, '•')
                    # Color by vehicle phase
                    if hasattr(vehicle_here.phase, 'name'):
                        if vehicle_here.phase.name == 'P1':  # Idle
                            char = f"[steel_blue]{char}[/steel_blue]"
                        elif vehicle_here.phase.name == 'P2':  # Dispatched
                            char = f"[orange3]{char}[/orange3]"
                        elif vehicle_here.phase.name == 'P3':  # Occupied
                            char = f"[dark_sea_green]{char}[/dark_sea_green]"
                elif trip_dest_here:
                    char = f"[yellow]{self.TRIP_CHARS['destination']}[/yellow]"
                elif trip_origin_here:
                    char = f"[red]{self.TRIP_CHARS['origin']}[/red]"
                else:
                    # Hide road/intersection characters - show blank space
                    char = " "
                    # COMMENTED OUT - road intersection display:
                    # char = f"[dim]{char}[/dim]"

                line += char

                # Add horizontal spacing between characters (except after last character)
                if x < self.map_size - 1:
                    line += " " * h_spacing

            map_lines.append(line)

            # Add vertical spacing between rows (except after last row)
            if y < self.map_size - 1:
                for _ in range(v_spacing):
                    map_lines.append("")

        return "\n".join(map_lines)

    def render(self) -> RenderResult:
        """Render the map widget"""
        map_display = self._create_map_display()

        # Create title with block info
        interpolation_info = ""
        if self.current_interpolation_points > 0:
            frame_in_cycle = self.frame_index % (self.current_interpolation_points + 1)
            interpolation_info = f" (frame {frame_in_cycle}/{self.current_interpolation_points})"

        title = f"City Map ({self.map_size}x{self.map_size}) - Block {self.sim.block_index}{interpolation_info}"

        return Panel(
            map_display,
            title=title,
            border_style="steel_blue",
            padding=(1, 1)
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
        self.title = f"Ridehail Map - Block {self.sim.block_index}/{self.sim.time_blocks}"
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