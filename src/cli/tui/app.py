"""Main TUI application for ModelX."""

from __future__ import annotations

from textual.app import App

from src.cli.api_client import ModelXClient
from src.cli.tui.screens import MainScreen


class ModelXTUI(App):
    """ModelX Terminal User Interface."""

    CSS = """
    App {
        background: $background;
    }
    
    .header {
        text-align: center;
        text-style: bold;
        padding: 1;
    }
    """

    def __init__(self, api_url: str = "http://localhost:8000", api_key: str | None = None) -> None:
        super().__init__()
        self.client = ModelXClient(api_url, api_key)

    def on_mount(self) -> None:
        """Initialize the app on mount."""
        self.push_screen(MainScreen(self.client))
        self.title = "ModelX TUI"

    def action_quit(self) -> None:
        """Quit the application."""
        self.exit()
