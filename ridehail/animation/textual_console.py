"""
Textual-based console animation for ridehail simulation.
"""
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import TabbedContent, TabPane

from .textual_base import TextualBasedAnimation, RidehailTextualApp


class TextualConsoleApp(RidehailTextualApp):
    """Textual app specifically for console animation"""

    def compose(self) -> ComposeResult:
        """Create child widgets for the console app"""
        yield self.create_header()

        with TabbedContent(initial="main"):
            with TabPane("Console", id="main"):
                with Horizontal():
                    with Vertical(classes="left-panel"):
                        yield self.create_progress_panel()
                        yield self.create_control_panel()
                    with Vertical(classes="right-panel"):
                        yield self.create_config_panel()

        yield self.create_footer()


class TextualConsoleAnimation(TextualBasedAnimation):
    """Textual-based console animation with enhanced interactivity"""

    def create_app(self) -> TextualConsoleApp:
        """Create the Textual console app instance"""
        return TextualConsoleApp(self.sim)