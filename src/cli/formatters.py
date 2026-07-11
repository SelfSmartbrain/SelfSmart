"""Output Formatters for ModelX CLI."""

from __future__ import annotations

import json
from typing import Any, Dict, List

from rich.console import Console
from rich.table import Table
from rich.json import JSON

from src.config.logging import get_logger

logger = get_logger(__name__)


class OutputFormatter:
    """Formats output in different formats (table, json, stream)."""
    
    def __init__(self):
        """Initialize output formatter."""
        self.console = Console()
    
    def output(self, data: Any, format_type: str = "table") -> None:
        """Output data in specified format.
        
        Args:
            data: Data to output
            format_type: Output format (table, json, stream)
        """
        if format_type == "json":
            self._output_json(data)
        elif format_type == "stream":
            self._output_stream(data)
        else:  # table (default)
            self._output_table(data)
    
    def _output_json(self, data: Any) -> None:
        """Output data as JSON."""
        json_str = json.dumps(data, indent=2, default=str)
        self.console.print(JSON(json_str))
    
    def _output_stream(self, data: Any) -> None:
        """Output data as stream (for streaming responses)."""
        if isinstance(data, list):
            for item in data:
                self.console.print(json.dumps(item, default=str))
        else:
            self.console.print(json.dumps(data, default=str))
    
    def _output_table(self, data: Any) -> None:
        """Output data as table."""
        if isinstance(data, list):
            if not data:
                self.console.print("[yellow]No data to display[/yellow]")
                return
            
            # Determine if this is a list of dicts or simple list
            if isinstance(data[0], dict):
                self._output_dict_table(data)
            else:
                self._output_simple_list(data)
        elif isinstance(data, dict):
            self._output_single_dict(data)
        else:
            self.console.print(str(data))
    
    def _output_dict_table(self, data: List[Dict[str, Any]]) -> None:
        """Output list of dicts as table."""
        if not data:
            return
        
        # Get all unique keys from all dicts
        keys = set()
        for item in data:
            keys.update(item.keys())
        keys = sorted(list(keys))
        
        # Create table
        table = Table()
        for key in keys:
            table.add_column(key.replace("_", " ").title(), style="cyan")
        
        # Add rows
        for item in data:
            row = []
            for key in keys:
                value = item.get(key, "")
                if isinstance(value, (list, dict)):
                    value = json.dumps(value, default=str)
                row.append(str(value)[:50])  # Truncate long values
            table.add_row(*row)
        
        self.console.print(table)
    
    def _output_simple_list(self, data: List[Any]) -> None:
        """Output simple list as table."""
        table = Table()
        table.add_column("Value", style="cyan")
        
        for item in data:
            table.add_row(str(item))
        
        self.console.print(table)
    
    def _output_single_dict(self, data: Dict[str, Any]) -> None:
        """Output single dict as table."""
        table = Table()
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="magenta")
        
        for key, value in data.items():
            if isinstance(value, (list, dict)):
                value = json.dumps(value, default=str)
            table.add_row(key.replace("_", " ").title(), str(value))
        
        self.console.print(table)
    
    def output_success(self, message: str) -> None:
        """Output success message."""
        self.console.print(f"[green]✓[/green] {message}")
    
    def output_error(self, message: str) -> None:
        """Output error message."""
        self.console.print(f"[red]✗[/red] {message}")
    
    def output_warning(self, message: str) -> None:
        """Output warning message."""
        self.console.print(f"[yellow]⚠[/yellow] {message}")
    
    def output_info(self, message: str) -> None:
        """Output info message."""
        self.console.print(f"[blue]ℹ[/blue] {message}")
