"""
Terminal-based map animation for ridehail simulation using Unicode characters and Rich library.
"""

import logging
import time

from rich.console import Console
from rich.layout import Layout
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from .rich_base import RichBasedAnimation


class TerminalMapAnimation(RichBasedAnimation):
    """
    Terminal-based animation with real-time map visualization using Unicode characters.
    Combines the statistics display from ConsoleAnimation with a visual map.
    """

    # Unicode characters for map rendering
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
    }

    # Vehicle direction characters
    VEHICLE_CHARS = {"north": "▲", "east": "►", "south": "▼", "west": "◄"}

    # Trip markers
    TRIP_CHARS = {"origin": "●", "destination": "★"}

    def __init__(self, sim):
        super().__init__(sim)

        # Map-specific attributes - responsive sizing based on terminal
        self.map_size = self._calculate_optimal_map_size(sim.city.city_size)

        # Interpolation support (similar to matplotlib animation)
        self.interpolation_points = sim.interpolate
        self.current_interpolation_points = self.interpolation_points
        self.frame_index = 0

    def _check_terminal_compatibility(self):
        """Check if terminal supports Rich features and Unicode characters"""
        try:
            from rich.console import Console

            console = Console()
            # Basic checks for terminal capabilities
            if not console.is_terminal:
                logging.warning(
                    "Not running in a terminal - Rich features may not work properly"
                )
                return False
            if console.size.width < 100 or console.size.height < 30:
                logging.warning(
                    f"Terminal size ({console.size.width}x{console.size.height}) may be too small for map display"
                )
                return False
            # Test Unicode support
            try:
                console.print("Testing Unicode: ┼▲►▼◄●★", end="")
                print("\r" + " " * 50 + "\r", end="")  # Clear the test line
                return True
            except UnicodeEncodeError:
                logging.warning(
                    "Terminal does not support Unicode characters needed for map display"
                )
                return False
        except Exception as e:
            logging.error(f"Terminal compatibility check failed: {e}")
            return False

    def _calculate_optimal_map_size(self, city_size):
        """Calculate optimal map size based on terminal dimensions"""
        try:
            from rich.console import Console

            console = Console()
            terminal_width = console.size.width
            terminal_height = console.size.height

            # Reserve space for panels: config (left), stats (right), borders
            # Left side gets ~60% of width, map gets ~80% of left side height
            available_width = int(terminal_width * 0.6 * 0.8)
            available_height = int(terminal_height * 0.6)

            # Map should be square, so use the smaller dimension
            max_map_size = min(
                available_width, available_height, 25
            )  # Hard limit of 25
            optimal_size = min(city_size, max_map_size)

            logging.info(
                f"Terminal: {terminal_width}x{terminal_height}, "
                f"City: {city_size}, Map: {optimal_size}"
            )
            return max(optimal_size, 5)  # Minimum size of 5

        except Exception as e:
            logging.warning(f"Could not calculate optimal map size: {e}")
            return min(city_size, 20)  # Fallback to conservative size

    def _interpolation(self, frame_index):
        """
        For plotting, we use interpolation points to give smoother
        motion in the map. This function tells us if the frame represents
        a new block or is an interpolation point.
        Returns the interpolation step (0 = real simulation step)
        """
        return frame_index % (self.current_interpolation_points + 1)

    def _setup_progress_bars(self):
        """Setup simplified progress bars for map view"""
        # Use basic progress bars from parent class
        self._setup_basic_progress_bars()

    def _create_map_display(self, frame_index=None):
        """Create the Unicode-based map display with optional interpolation"""
        if frame_index is None:
            frame_index = self.frame_index

        map_lines = []

        # Calculate interpolation offset for smooth vehicle movement
        interpolation_step = self._interpolation(frame_index)
        distance_increment = interpolation_step / (
            self.current_interpolation_points + 1
        )

        # Create grid representation
        for y in range(self.map_size):
            line = ""
            for x in range(self.map_size):
                # Determine appropriate road/intersection character based on position
                char = f"[blue]{self._get_road_character(x, y)}[/blue]"

                # Check for vehicles at this location (with interpolation)
                vehicle_here = None
                for vehicle in self.sim.vehicles:
                    # Apply interpolation to vehicle position
                    vx = vehicle.location[0]
                    vy = vehicle.location[1]

                    # Add interpolation offset based on vehicle direction (only for moving vehicles)
                    if vehicle.phase.name != "P1" or getattr(
                        self.sim, "idle_vehicles_moving", False
                    ):
                        vx += distance_increment * vehicle.direction.value[0]
                        vy += distance_increment * vehicle.direction.value[1]

                    # Convert to grid coordinates and handle wrapping
                    grid_x = int(vx) % self.map_size
                    grid_y = int(vy) % self.map_size

                    if grid_x == x and grid_y == y:
                        vehicle_here = vehicle
                        break

                # Check for trips at this location
                trip_origin_here = False
                trip_dest_here = False
                for trip in self.sim.trips.values():
                    if hasattr(trip, "origin") and hasattr(trip, "destination"):
                        ox, oy = (
                            int(trip.origin[0]) % self.map_size,
                            int(trip.origin[1]) % self.map_size,
                        )
                        dx, dy = (
                            int(trip.destination[0]) % self.map_size,
                            int(trip.destination[1]) % self.map_size,
                        )

                        if (
                            ox == x
                            and oy == y
                            and trip.phase.name in ("UNASSIGNED", "WAITING")
                        ):
                            trip_origin_here = True
                        elif dx == x and dy == y and trip.phase.name == "RIDING":
                            trip_dest_here = True

                # Priority: vehicles > trip destinations > trip origins > intersections
                if vehicle_here:
                    direction_name = vehicle_here.direction.name.lower()
                    char = self.VEHICLE_CHARS.get(direction_name, "•")
                    # Color by vehicle phase
                    if vehicle_here.phase.name == "P1":  # Idle
                        char = f"[cyan]{char}[/cyan]"
                    elif vehicle_here.phase.name == "P2":  # Dispatched
                        char = f"[yellow]{char}[/yellow]"
                    elif vehicle_here.phase.name == "P3":  # Occupied
                        char = f"[green]{char}[/green]"
                elif trip_dest_here:
                    char = f"[yellow]{self.TRIP_CHARS['destination']}[/yellow]"
                elif trip_origin_here:
                    char = f"[red]{self.TRIP_CHARS['origin']}[/red]"
                else:
                    char = f"[dim]{char}[/dim]"

                line += char
            map_lines.append(line)

        return "\n".join(map_lines)

    def _get_road_character(self, x, y):
        """Get the appropriate road/intersection character for position (x, y)"""
        # Corners
        if x == 0 and y == 0:
            return self.MAP_CHARS["corner_bl"]
        elif x == 0 and y == self.map_size - 1:
            return self.MAP_CHARS["corner_tl"]
        elif x == self.map_size - 1 and y == 0:
            return self.MAP_CHARS["corner_br"]
        elif x == self.map_size - 1 and y == self.map_size - 1:
            return self.MAP_CHARS["corner_tr"]

        # Edges
        elif x == 0:  # Left edge
            return self.MAP_CHARS["tee_right"]
        elif x == self.map_size - 1:  # Right edge
            return self.MAP_CHARS["tee_left"]
        elif y == 0:  # Bottom edge
            return self.MAP_CHARS["tee_up"]
        elif y == self.map_size - 1:  # Top edge
            return self.MAP_CHARS["tee_down"]

        # Interior intersections
        else:
            return self.MAP_CHARS["intersection"]

    def _create_control_info_panel(self):
        """Create control information panel showing keyboard shortcuts"""
        controls_table = Table.grid(expand=True)
        controls_table.add_column("Key", style="cyan", no_wrap=True)
        controls_table.add_column("Action", style="white")

        # Add keyboard controls (simplified from matplotlib animation)
        controls_table.add_row("Space", "Pause/Resume simulation")
        controls_table.add_row("Ctrl+C", "Quit simulation")
        controls_table.add_row("q", "Quit simulation")

        # Vehicle controls
        controls_table.add_row("", "")  # Spacer
        controls_table.add_row("[bold]Vehicle Control:[/bold]", "")
        controls_table.add_row("N/n", "Increase/decrease vehicles")
        controls_table.add_row("K/k", "Increase/decrease demand")

        # Map controls
        controls_table.add_row("", "")  # Spacer
        controls_table.add_row("[bold]Map Control:[/bold]", "")
        controls_table.add_row("C/c", "Increase/decrease city size")
        controls_table.add_row("V/v", "Increase/decrease speed")

        return Panel(
            controls_table,
            title="[b]Keyboard Controls",
            border_style="steel_blue",
            padding=(1, 1),
        )

    def _setup_layout(self, config_table):
        """Setup the Rich layout with map, config, and statistics panels"""
        # Create map panel
        map_display = self._create_map_display()
        map_panel = Panel(
            map_display,
            title=f"[b]City Map ({self.map_size}x{self.map_size})",
            border_style="steel_blue",
            padding=(1, 1),
        )

        # Create statistics panel
        statistics_table = Table.grid(expand=True)
        statistics_table.add_row(
            Panel(
                self.progress_bars["progress"],
                title="[b]Progress",
                border_style="steel_blue",
            )
        )
        statistics_table.add_row(
            Panel(
                self.progress_bars["vehicle"],
                title="[b]Vehicle Status",
                border_style="steel_blue",
                padding=(1, 1),
            )
        )
        statistics_table.add_row(
            Panel(
                self.progress_bars["trip"],
                title="[b]Trip Metrics",
                border_style="steel_blue",
                padding=(1, 1),
            )
        )

        # Create control info panel
        control_panel = self._create_control_info_panel()

        # Create main layout with 4 panels as planned
        self.layout = Layout()

        # Split into top and bottom halves
        self.layout.split_column(
            Layout(name="top"),
            Layout(name="bottom", size=10),  # Bottom smaller for config/controls
        )

        # Top half: map (left) and statistics (right)
        self.layout["top"].split_row(
            Layout(map_panel, name="map"),
            Layout(
                Panel(
                    statistics_table, title="[b]Statistics", border_style="steel_blue"
                ),
                name="stats",
            ),
        )

        # Bottom half: config (left) and controls (right)
        self.layout["bottom"].split_row(
            Layout(
                Panel(config_table, title="Configuration", border_style="steel_blue"),
                name="config",
            ),
            Layout(control_panel, name="controls"),
        )

    def _next_frame(self):
        """Execute one frame of the animation and update displays"""
        # Only advance simulation on "real" time points (not interpolation frames)
        if self._interpolation(self.frame_index) == 0:
            return_values = "stats"
            results = self.sim.next_block(
                jsonl_file_handle=None,
                csv_file_handle=None,
                return_values=return_values,
                dispatch=self.dispatch,
            )
            # Update current interpolation points (allows dynamic adjustment)
            self.current_interpolation_points = self.interpolation_points

            # Update progress bars only on real simulation steps
            self._update_basic_progress_bars(results)

        else:
            # For interpolation frames, use the last known results
            results = getattr(self, "_last_results", {"block": self.sim.block_index})

        # Always update map display (including interpolation frames)
        map_display = self._create_map_display(self.frame_index)
        block_display = results.get("block", self.sim.block_index)
        interpolation_info = (
            f" (frame {self.frame_index % (self.current_interpolation_points + 1)}/{self.current_interpolation_points})"
            if self.current_interpolation_points > 0
            else ""
        )

        self.layout["top"]["map"].update(
            Panel(
                map_display,
                title=f"[b]City Map ({self.map_size}x{self.map_size}) - Block {block_display}{interpolation_info}",
                border_style="steel_blue",
                padding=(1, 1),
            )
        )

        # Store results for interpolation frames
        if self._interpolation(self.frame_index) == 0:
            self._last_results = results

        # Increment frame counter
        self.frame_index += 1

        return results

    def _fallback_animation(self):
        """Fallback to ConsoleAnimation for terminals that don't support terminal maps"""
        print("Warning: Terminal does not support map display features.")
        print("Falling back to console animation...")

        # Import here to avoid circular imports
        from .console import ConsoleAnimation

        fallback = ConsoleAnimation(self.sim)
        fallback.animate()

    def animate(self):
        """Main animation loop with real-time map updates"""
        # Check terminal compatibility first
        if not self.terminal_compatible:
            self._fallback_animation()
            return

        try:
            console = Console()
            self._setup_signal_handler()
            config_table = self._setup_config_table()
            self._setup_progress_bars()
            self._setup_layout(config_table)
            console.print(self.layout)

            # Adjust refresh rate based on interpolation points for smooth animation
            refresh_rate = max(4, 4 * (self.interpolation_points + 1))
            with Live(self.layout, screen=True, refresh_per_second=refresh_rate):
                if self.time_blocks > 0:
                    # Calculate total frames including interpolation
                    total_frames = (self.time_blocks + 1) * (
                        self.interpolation_points + 1
                    )
                    for frame in range(total_frames):
                        if self.quit_requested:
                            break
                        self._next_frame()
                        # Break early if simulation is complete
                        if self.sim.block_index > self.time_blocks:
                            break
                else:
                    frame = 0
                    while not self.quit_requested:
                        self._next_frame()
                        frame += 1

                # Leave final frame visible unless quit was requested
                if not self.quit_requested:
                    while not self.quit_requested:
                        time.sleep(self.FINAL_DISPLAY_SLEEP)

        except KeyboardInterrupt:
            self.quit_requested = True
        except Exception as e:
            logging.error(f"Terminal map animation failed: {e}")
            print(f"Map animation error: {e}")
            print("Falling back to console animation...")
            self._fallback_animation()
