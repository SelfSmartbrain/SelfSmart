"""Command-line entry point for ModelX TUI."""

from __future__ import annotations

import os

from src.cli.tui.app import ModelXTUI


def main() -> None:
    """Launch the ModelX Terminal User Interface."""
    api_url = os.getenv("MODELX_API_URL", "http://localhost:8000")
    api_key = os.getenv("MODELX_API_KEY")
    
    app = ModelXTUI(api_url=api_url, api_key=api_key)
    app.run()


if __name__ == "__main__":
    main()
