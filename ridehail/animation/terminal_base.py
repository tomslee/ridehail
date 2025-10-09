"""
Textual-based animation base class for ridehail simulation.
"""

import logging
from typing import Optional, Dict, Any

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, VerticalScroll
from textual.widgets import (
    Header,
    Footer,
    Static,
    ProgressBar,
    Label,
    Button,
    DataTable,
    TabbedContent,
    TabPane,
)
from textual.message import Message
from textual.timer import Timer
from textual.screen import ModalScreen

from ridehail.atom import Measure
from ridehail.keyboard_mappings import generate_textual_bindings
from .base import RideHailAnimation


class SimulationControlPanel(Container):
    """
    Control panel for simulation playback and parameters.

    NOTE: This is a reference implementation used by the base RidehailTextualApp.
    Specific animation types (console, map, stats) override compose() entirely
    and typically rely on keyboard bindings instead of UI buttons.
    """

    def __init__(self, sim, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim
        self.is_paused = False

    def compose(self) -> ComposeResult:
        yield Static("Simulation Controls", classes="panel-title")
        with Horizontal(classes="control-buttons"):
            yield Button("⏸️ Pause", id="pause_btn", variant="primary")
            yield Button("⏹️ Stop", id="stop_btn", variant="error")
            yield Button("⚙️ Settings", id="settings_btn")

        yield Static("Vehicle Count: ", classes="control-label")
        with Horizontal(classes="control-row"):
            yield Button("-10", id="vehicles_minus_10", classes="small-btn")
            yield Button("-1", id="vehicles_minus_1", classes="small-btn")
            yield Label(str(self.sim.vehicle_count), id="vehicle_count_display")
            yield Button("+1", id="vehicles_plus_1", classes="small-btn")
            yield Button("+10", id="vehicles_plus_10", classes="small-btn")

        yield Static("Base Demand: ", classes="control-label")
        with Horizontal(classes="control-row"):
            yield Button("-0.1", id="demand_minus", classes="small-btn")
            yield Label(f"{self.sim.base_demand:.1f}", id="demand_display")
            yield Button("+0.1", id="demand_plus", classes="small-btn")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button presses for simulation control"""
        button_id = event.button.id

        if button_id == "pause_btn":
            self.is_paused = not self.is_paused
            event.button.label = "▶️ Resume" if self.is_paused else "⏸️ Pause"
            self.post_message(SimulationPaused(self.is_paused))

        elif button_id == "stop_btn":
            self.post_message(SimulationStopped())

        elif button_id == "vehicles_minus_10":
            handler = self.sim.get_keyboard_handler()
            new_count = handler.handle_ui_action("decrease_vehicles", 10)
            self.query_one("#vehicle_count_display").update(str(new_count))

        elif button_id == "vehicles_minus_1":
            handler = self.sim.get_keyboard_handler()
            new_count = handler.handle_ui_action("decrease_vehicles", 1)
            self.query_one("#vehicle_count_display").update(str(new_count))

        elif button_id == "vehicles_plus_1":
            handler = self.sim.get_keyboard_handler()
            new_count = handler.handle_ui_action("increase_vehicles", 1)
            self.query_one("#vehicle_count_display").update(str(new_count))

        elif button_id == "vehicles_plus_10":
            handler = self.sim.get_keyboard_handler()
            new_count = handler.handle_ui_action("increase_vehicles", 10)
            self.query_one("#vehicle_count_display").update(str(new_count))

        elif button_id == "demand_minus":
            handler = self.sim.get_keyboard_handler()
            new_demand = handler.handle_ui_action("decrease_demand", 0.1)
            self.query_one("#demand_display").update(f"{new_demand:.1f}")

        elif button_id == "demand_plus":
            handler = self.sim.get_keyboard_handler()
            new_demand = handler.handle_ui_action("increase_demand", 0.1)
            self.query_one("#demand_display").update(f"{new_demand:.1f}")


class ProgressPanel(Container):
    """
    Progress display panel with multiple metrics.

    NOTE: This is a reference implementation used by the base RidehailTextualApp.
    Specific animation types (console, map, stats) override compose() entirely
    and provide their own specialized panels.
    """

    def __init__(self, sim, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim

    def compose(self) -> ComposeResult:
        yield Static("Simulation Progress", classes="panel-title")

        # Main progress bar
        yield Label("Block Progress")
        yield ProgressBar(total=1.0, show_eta=False, id="main_progress")

        # Vehicle status bars
        yield Static("Vehicle Status", classes="subsection-title")
        yield Label("P1 (Idle)")
        yield ProgressBar(total=1.0, show_percentage=True, id="vehicle_p1")
        yield Label("P2 (Dispatched)")
        yield ProgressBar(total=1.0, show_percentage=True, id="vehicle_p2")
        yield Label("P3 (Occupied)")
        yield ProgressBar(total=1.0, show_percentage=True, id="vehicle_p3")

        # Trip metrics
        yield Static("Trip Metrics", classes="subsection-title")
        yield Label("Mean Wait Time")
        yield ProgressBar(
            total=self.sim.city.city_size, show_percentage=False, id="wait_time"
        )
        yield Label("Mean Ride Time")
        yield ProgressBar(
            total=self.sim.city.city_size, show_percentage=False, id="ride_time"
        )

    def update_progress(self, results: Dict[str, Any]) -> None:
        """Update all progress bars with simulation results"""
        # Main progress
        if self.sim.time_blocks > 0:
            progress = results["block"] / self.sim.time_blocks
            self.query_one("#main_progress").update(progress=progress)

        # Vehicle status
        self.query_one("#vehicle_p1").update(
            progress=results[Measure.VEHICLE_FRACTION_P1.name]
        )
        self.query_one("#vehicle_p2").update(
            progress=results[Measure.VEHICLE_FRACTION_P2.name]
        )
        self.query_one("#vehicle_p3").update(
            progress=results[Measure.VEHICLE_FRACTION_P3.name]
        )

        # Trip metrics
        self.query_one("#wait_time").update(
            progress=results[Measure.TRIP_MEAN_WAIT_TIME.name]
        )
        self.query_one("#ride_time").update(
            progress=results[Measure.TRIP_MEAN_RIDE_TIME.name]
        )


class ConfigPanel(Container):
    """Configuration display panel"""

    def __init__(self, sim, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim

    def compose(self) -> ComposeResult:
        yield Static("Configuration", classes="panel-title")

        # Display title prominently if it exists and is not empty
        if hasattr(self.sim, "title") and self.sim.title:
            yield Static(f"{self.sim.title}", classes="config-title")

        table = DataTable(show_header=False, zebra_stripes=True)
        table.add_column("Setting", width=20)
        table.add_column("Value", width=20)

        # Build dynamic exclusion list based on current configuration
        # Exclude 'title' since it's displayed separately above
        exclude_attrs = self._get_excluded_attrs()
        exclude_attrs.add("title")

        # Group attributes by config section for organized display
        attrs_by_section = self._group_attrs_by_section(exclude_attrs)

        # Display attributes in section order: DEFAULT first, then others alphabetically
        # Within each section, order by weight (lower weight = earlier)
        for section in attrs_by_section:
            # Add section divider for all sections except DEFAULT
            if section != "DEFAULT" and len(attrs_by_section[section]) > 0:
                table.add_row(f"[dim]{'─' * 20}[/dim]", f"[dim]{section}[/dim]")

            for attr_name in attrs_by_section[section]:  # Already sorted by weight
                # Access config value directly (not runtime-modified simulation attribute)
                config_item = getattr(self.sim.config, attr_name)
                value = config_item.value
                table.add_row(attr_name, str(value))

        yield table

    def _group_attrs_by_section(self, exclude_attrs: set) -> dict:
        """
        Group simulation attributes by their config section.

        Organizes attributes by section (DEFAULT, ANIMATION, EQUILIBRATION, etc.)
        for logical grouping in the display. DEFAULT section appears first, followed
        by other sections in alphabetical order. Within each section, attributes are
        sorted by their weight (lower weight appears first).

        Args:
            exclude_attrs: Set of attribute names to exclude

        Returns:
            dict: Ordered dict mapping section names to lists of attribute names
                  Example: {'DEFAULT': ['title', 'city_size', 'vehicle_count', ...],
                           'ANIMATION': ['animation_delay', ...], ...}
                  Each list is sorted by the attribute's weight parameter.
        """
        from collections import defaultdict, OrderedDict

        by_section = defaultdict(list)

        # Collect all displayable config attributes with their weights
        # Loop over config items (not simulation attributes) to include all parameters
        attrs_with_weights = []
        for attr_name in dir(self.sim.config):
            if attr_name.startswith("_") or attr_name in exclude_attrs:
                continue

            # Get the config item
            config_item = getattr(self.sim.config, attr_name)

            # Check if it's a ConfigItem (has config_section and value attributes)
            if hasattr(config_item, "config_section") and hasattr(config_item, "value"):
                section = config_item.config_section or "OTHER"
                weight = getattr(
                    config_item, "weight", 999
                )  # Default weight if not set
                attrs_with_weights.append((attr_name, section, weight))

        # Group by section and sort by weight
        for attr_name, section, weight in attrs_with_weights:
            by_section[section].append((attr_name, weight))

        # Sort each section by weight, then extract just the attribute names
        for section in by_section:
            by_section[section] = [
                name for name, weight in sorted(by_section[section], key=lambda x: x[1])
            ]

        # Return ordered dict with DEFAULT first, then others alphabetically
        # Exclude 'OTHER' section - these are runtime/internal attributes
        ordered = OrderedDict()
        if "DEFAULT" in by_section:
            ordered["DEFAULT"] = by_section["DEFAULT"]

        for section in sorted(by_section.keys()):
            if section != "DEFAULT" and section != "OTHER":
                ordered[section] = by_section[section]

        return ordered

    def _get_excluded_attrs(self) -> set:
        """
        Build set of attributes to exclude from configuration display.

        Excludes:
        - Complex objects (cities, vehicles, etc.)
        - Internal/implementation details
        - Section-specific parameters when that section is disabled:
          * Animation parameters when animate=False
          * Equilibration parameters when equilibrate=False
          * Sequence parameters when run_sequence=False
          * City scale parameters when use_city_scale=False
          * Advanced dispatch parameters when use_advanced_dispatch=False

        Returns:
            set: Attribute names to exclude from display
        """
        # Always exclude: config parameters that shouldn't be displayed
        # (Most runtime attributes are excluded automatically via the 'OTHER' section rule)
        exclude = {
            "annotation",  # User-added text, not a core simulation parameter
            "impulse_list",  # Advanced feature, rarely used
        }

        # Conditionally exclude entire sections based on feature flags
        # This is more robust than hardcoding parameter names
        sections_to_exclude = set()

        # Conditionally exclude animation parameters when animate=False
        if not self.sim.animate:
            sections_to_exclude.add("ANIMATION")
        if not self.sim.equilibrate:
            sections_to_exclude.add("EQUILIBRATION")
        if not self.sim.run_sequence:
            sections_to_exclude.add("SEQUENCE")
        if not self.sim.use_city_scale:
            sections_to_exclude.add("CITY_SCALE")
        if not self.sim.use_advanced_dispatch:
            sections_to_exclude.add("ADVANCED_DISPATCH")

        # Exclude all parameters from disabled sections
        for attr_name in dir(self.sim.config):
            if attr_name.startswith("_"):
                continue
            attr = getattr(self.sim.config, attr_name)
            if hasattr(attr, "config_section"):
                if attr.config_section in sections_to_exclude:
                    exclude.add(attr_name)

        return exclude


class SimulationPaused(Message):
    """Message sent when simulation is paused/resumed"""

    def __init__(self, is_paused: bool):
        self.is_paused = is_paused
        super().__init__()


class SimulationStopped(Message):
    """Message sent when simulation is stopped"""

    pass


class KeyboardShortcutsModal(ModalScreen):
    """Modal screen showing keyboard shortcuts help"""

    DEFAULT_CSS = """
    KeyboardShortcutsModal {
        align: center middle;
    }

    KeyboardShortcutsModal > Container {
        width: 70;
        height: auto;
        max-height: 90%;
        background: $panel;
        border: thick $primary;
    }

    KeyboardShortcutsModal .modal-title {
        width: 100%;
        content-align: center middle;
        text-style: bold;
        background: $primary;
        color: $text;
        padding: 1;
    }

    KeyboardShortcutsModal DataTable {
        height: 1fr;
        margin: 1;
    }

    KeyboardShortcutsModal .modal-footer {
        width: 100%;
        content-align: center middle;
        color: $text-muted;
        padding: 1;
        text-style: italic;
    }
    """

    BINDINGS = [
        ("escape", "dismiss", "Close"),
        ("h", "dismiss", "Close"),
        ("question_mark", "dismiss", "Close"),
    ]

    def compose(self) -> ComposeResult:
        """Create the modal layout"""
        with Container():
            yield Static("Keyboard Shortcuts", classes="modal-title")
            with VerticalScroll():
                yield self._create_shortcuts_table()
            yield Static("Press Esc, h, or ? to close", classes="modal-footer")

    def _create_shortcuts_table(self) -> DataTable:
        """Create a DataTable with keyboard shortcuts"""
        table = DataTable(show_header=True, zebra_stripes=True)
        table.add_column("Key", width=15)
        table.add_column("Description", width=40)

        # Get the app's BINDINGS to show accurate shortcuts for current context
        app = self.app
        if hasattr(app, "BINDINGS") and app.BINDINGS:
            # Use the app's bindings directly
            for binding in app.BINDINGS:
                if len(binding) >= 3:
                    key, action, description = binding[0], binding[1], binding[2]
                    # Format the key nicely
                    display_key = self._format_key(key)
                    table.add_row(display_key, description)
        else:
            # Fallback: generate from keyboard_mappings
            from ridehail.keyboard_mappings import get_mappings_for_platform

            for mapping in get_mappings_for_platform("textual"):
                keys_str = "/".join(mapping.keys)
                table.add_row(keys_str, mapping.description)

        return table

    def _format_key(self, key: str) -> str:
        """Format key binding for display"""
        # Replace textual key names with more readable versions
        replacements = {
            "question_mark": "?",
            "ctrl+": "Ctrl+",
            "shift+": "Shift+",
        }
        display_key = key
        for old, new in replacements.items():
            display_key = display_key.replace(old, new)
        return display_key

    def action_dismiss(self) -> None:
        """Dismiss the modal"""
        self.app.pop_screen()


class RidehailTextualApp(App):
    """
    Base Textual application for ridehail animations.

    This base class provides a reference implementation with basic progress
    and control panels. Specific animation types (console, map, stats, sequence)
    override compose() to provide specialized layouts tailored to their needs.
    """

    CSS = """
    /* Common styling for all Textual-based animations */

    Header {
        background: $primary;
    }

    Footer {
        background: $secondary;
    }

    /* ConfigPanel styling - shared across all animations */
    #config_panel {
        width: 45;
        height: 1fr;
        border: solid $primary;
        margin: 0;
        padding: 1;
    }

    .panel-title {
        text-style: bold;
        background: $primary;
        color: $text;
        padding: 1;
        margin: 1 0;
    }

    .config-title {
        text-style: bold;
        color: $text;
        padding: 0 1;
        margin: 0 0 1 0;
    }

    .subsection-title {
        text-style: bold;
        margin: 1 0 0 0;
    }

    /* Layout containers - shared pattern */
    #layout_container {
        width: 1fr;
        height: 1fr;
    }

    /* Control panel styling (for console animation) */
    .control-buttons {
        height: 3;
        margin: 1 0;
    }

    .control-row {
        height: 3;
        margin: 0 0 1 0;
    }

    .control-label {
        margin: 1 0 0 0;
    }

    .small-btn {
        width: 6;
        margin: 0 1;
    }

    ProgressBar {
        margin: 0 0 1 0;
    }
    """

    # Generate BINDINGS from shared keyboard mappings
    # Add "h" as alternative to "?" for help (generate_textual_bindings only takes first key)
    BINDINGS = generate_textual_bindings(platform="textual") + [
        ("h", "show_help", "Help"),
    ]

    def __init__(self, sim, animation=None, **kwargs):
        super().__init__(**kwargs)
        self.sim = sim
        self.animation = animation
        self.is_paused = False
        self.simulation_timer: Optional[Timer] = None

        # Set theme for consistent color scheme across all textual animations
        self.theme = "textual-dark"

    def compose(self) -> ComposeResult:
        """Create child widgets for the app"""
        yield self.create_header()

        with TabbedContent(initial="main"):
            with TabPane("Main", id="main"):
                with Horizontal():
                    with Vertical(classes="left-panel"):
                        yield self.create_progress_panel()
                        yield self.create_control_panel()
                    with Vertical(classes="right-panel"):
                        yield self.create_config_panel()

        yield self.create_footer()

    def create_header(self):
        """Create the header widget"""
        return Header()

    def create_footer(self):
        """Create the footer widget"""
        return Footer()

    def create_progress_panel(self):
        """Create the progress panel widget"""
        return ProgressPanel(self.sim, id="progress_panel")

    def create_control_panel(self):
        """Create the control panel widget"""
        return SimulationControlPanel(self.sim, id="control_panel")

    def create_config_panel(self):
        """Create the config panel widget"""
        return ConfigPanel(self.sim, id="config_panel")

    def on_mount(self) -> None:
        """Called when app starts"""
        self.title = f"Ridehail Simulation - {self.sim.config.title.value}"
        self.start_simulation()

    def start_simulation(self) -> None:
        """Start the simulation timer"""
        if not self.simulation_timer:
            try:
                # Use configurable animation_delay from config for consistent timing across all animations
                frame_interval = self.sim.config.animation_delay.value
                if frame_interval is None:
                    frame_interval = self.sim.config.animation_delay.default

                # Ensure minimum interval for Textual timer (0 means run as fast as possible)
                # Use a very small value instead of 0 to ensure timer fires reliably
                if frame_interval <= 0:
                    frame_interval = (
                        0.001  # 1ms - effectively immediate but allows UI refresh
                    )

                self.simulation_timer = self.set_interval(
                    interval=frame_interval, callback=self.simulation_step, repeat=0
                )
            except Exception as e:
                logging.error(f"Simulation step failed: {e}")
                self.stop_simulation()
        else:
            with open("/tmp/textual_debug.log", "a") as f:
                f.write("simulation_timer already exists, not starting again\n")
                f.flush()

    def simulation_step(self) -> None:
        """Execute one simulation step"""
        # Increment step counter for debugging
        self._step_count = getattr(self, "_step_count", 0) + 1

        if self.is_paused:
            return

        try:
            print(f"textual_base simulation step at index {self.sim.block_index}...")
            results = self.sim.next_block(
                jsonl_file_handle=None,
                csv_file_handle=None,
                return_values="stats",
                dispatch=self.animation.dispatch,
            )

            # Update title to show current progress
            self.title = f"Ridehail Simulation - Block {self.sim.block_index}/{self.sim.time_blocks}"

            # Update progress panel
            progress_panel = self.query_one("#progress_panel")
            progress_panel.update_progress(results)

            # Check if simulation is complete
            if (
                self.sim.time_blocks > 0
                and self.sim.block_index >= self.sim.time_blocks
            ):
                self.stop_simulation()

        except Exception as e:
            logging.error(f"Simulation step failed: {e}")
            self.stop_simulation()

    def stop_simulation(self) -> None:
        """Stop the simulation timer"""
        if self.simulation_timer:
            self.simulation_timer.stop()
            self.simulation_timer = None

    def on_simulation_paused(self, event: SimulationPaused) -> None:
        """Handle simulation pause/resume"""
        self.is_paused = event.is_paused

    def on_simulation_stopped(self, event: SimulationStopped) -> None:
        """Handle simulation stop"""
        self.stop_simulation()
        self.exit()

    def action_quit(self) -> None:
        """Quit the application"""
        self.stop_simulation()
        self.exit()

    def action_pause(self) -> None:
        """Toggle pause/resume"""
        # Use centralized keyboard handler for consistent behavior
        handler = self.sim.get_keyboard_handler()
        self.is_paused = handler.handle_ui_action("pause")

    def action_decrease_vehicles(self) -> None:
        """Decrease vehicle count by 1"""
        # Use centralized keyboard handler for consistent behavior
        handler = self.sim.get_keyboard_handler()
        handler.handle_ui_action("decrease_vehicles", 1)

    def action_increase_vehicles(self) -> None:
        """Increase vehicle count by 1"""
        # Use centralized keyboard handler for consistent behavior
        handler = self.sim.get_keyboard_handler()
        handler.handle_ui_action("increase_vehicles", 1)

    def action_decrease_demand(self) -> None:
        """Decrease base demand by 0.1"""
        # Use centralized keyboard handler for consistent behavior
        handler = self.sim.get_keyboard_handler()
        handler.handle_ui_action("decrease_demand", 0.1)

    def action_increase_demand(self) -> None:
        """Increase base demand by 0.1"""
        # Use centralized keyboard handler for consistent behavior
        handler = self.sim.get_keyboard_handler()
        handler.handle_ui_action("increase_demand", 0.1)

    def action_decrease_animation_delay(self) -> None:
        """Decrease animation delay by 0.05s"""
        handler = self.sim.get_keyboard_handler()
        new_delay = handler.handle_ui_action("decrease_animation_delay", 0.05)
        # Restart timer with new interval
        self._restart_simulation_timer()

    def action_increase_animation_delay(self) -> None:
        """Increase animation delay by 0.05s"""
        handler = self.sim.get_keyboard_handler()
        new_delay = handler.handle_ui_action("increase_animation_delay", 0.05)
        # Restart timer with new interval
        self._restart_simulation_timer()

    def _restart_simulation_timer(self) -> None:
        """Restart the simulation timer with updated animation_delay"""
        if self.simulation_timer:
            self.simulation_timer.stop()
            self.simulation_timer = None
            self.start_simulation()

    def action_show_help(self) -> None:
        """Show keyboard shortcuts help modal"""
        self.push_screen(KeyboardShortcutsModal())

    def action_toggle_config_panel(self) -> None:
        """Toggle visibility of config panel (zoom to main display)"""
        try:
            config_panel = self.query_one("#config_panel")
            config_panel.display = not config_panel.display
        except Exception:
            # Config panel doesn't exist (e.g., narrow terminal or not included in layout)
            pass


class TextualBasedAnimation(RideHailAnimation):
    """
    Base class for Textual-based terminal animations.
    Provides common functionality for TextualConsoleAnimation and TextualMapAnimation.
    """

    def __init__(self, sim):
        super().__init__(sim)
        self.app: Optional[RidehailTextualApp] = None
        self.textual_compatible = self._check_textual_compatibility()

    def _check_textual_compatibility(self) -> bool:
        """Check if terminal supports Textual features"""
        try:
            # Basic import test
            from textual.app import App

            return True
        except ImportError as e:
            logging.error(f"Textual not available: {e}")
            return False
        except Exception as e:
            logging.error(f"Textual compatibility check failed: {e}")
            return False

    def create_app(self) -> RidehailTextualApp:
        """Create the Textual app instance (to be overridden by subclasses)"""
        return RidehailTextualApp(self.sim, animation=self)

    def animate(self):
        """Main animation loop using Textual app"""
        if not self.textual_compatible:
            raise RuntimeError(
                "Textual library is required for terminal animations. "
                "Please install it with: pip install textual"
            )

        try:
            self.app = self.create_app()
            self.app.run()
        except KeyboardInterrupt:
            logging.info("Animation interrupted by user")
        except Exception as e:
            logging.error(f"Textual animation failed: {e}")
            raise RuntimeError(f"Textual animation error: {e}") from e
        finally:
            if self.app:
                self.app.exit()
