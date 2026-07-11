import asyncio
from typing import Optional, Callable
from rich.console import Console
from rich.live import Live
from rich.layout import Layout
from rich.panel import Panel
from rich.text import Text
from rich.align import Align
from rich.table import Table
from rich.box import ROUNDED
import time


class VoiceTerminalUI:
    def __init__(self):
        self.console = Console()
        self.layout = Layout()
        self._setup_layout()
        self._live: Optional[Live] = None
        self._listening = False
        self._processing = False
        self._user_text = ""
        self._assistant_text = ""
        self._status = "Ready"
        self._voice_level = 0.0
        self._stats = {}

    def _setup_layout(self):
        self.layout.split(
            Layout(name="header", size=3),
            Layout(name="main", ratio=1),
            Layout(name="footer", size=4),
        )
        self.layout["main"].split_row(
            Layout(name="conversation", ratio=2),
            Layout(name="sidebar", ratio=1),
        )

    def start(self):
        self._live = Live(self.layout, console=self.console, refresh_per_second=10, screen=True)
        self._live.start()
        self._update_display()

    def stop(self):
        if self._live:
            self._live.stop()
            self._live = None

    def set_listening(self, listening: bool):
        self._listening = listening
        self._status = "Listening..." if listening else "Ready"
        self._update_display()

    def set_processing(self, processing: bool):
        self._processing = processing
        if processing:
            self._status = "Thinking..."
        self._update_display()

    def set_user_text(self, text: str):
        self._user_text = text
        self._update_display()

    def append_user_text(self, text: str):
        self._user_text += text
        self._update_display()

    def set_assistant_text(self, text: str):
        self._assistant_text = text
        self._update_display()

    def append_assistant_text(self, text: str):
        self._assistant_text += text
        self._update_display()

    def set_voice_level(self, level: float):
        self._voice_level = max(0.0, min(1.0, level))
        self._update_display()

    def set_stats(self, stats: dict):
        self._stats = stats
        self._update_display()

    def clear_texts(self):
        self._user_text = ""
        self._assistant_text = ""
        self._update_display()

    def _update_display(self):
        if not self._live:
            return
        
        self.layout["header"].update(self._render_header())
        self.layout["conversation"].update(self._render_conversation())
        self.layout["sidebar"].update(self._render_sidebar())

    def _render_header(self) -> Panel:
        status_icon = "🟢" if self._listening else "🔴" if self._processing else "⚪"
        status_text = f"{status_icon} {self._status}"
        
        voice_bar = self._render_voice_bar()
        
        header_text = Text()
        header_text.append("🎤 ModelX Voice Assistant  ", style="bold cyan")
        header_text.append(status_text, style="bold")
        header_text.append("  ")
        header_text.append(voice_bar)
        
        return Panel(Align.center(header_text), style="cyan", box=ROUNDED)

    def _render_voice_bar(self) -> Text:
        bars = int(self._voice_level * 20)
        bar_text = Text()
        bar_text.append("█" * bars, style="green")
        bar_text.append("░" * (20 - bars), style="dim")
        return bar_text

    def _render_conversation(self) -> Panel:
        content = Text()
        
        if self._user_text:
            content.append("You: ", style="bold blue")
            content.append(self._user_text + "\n\n", style="blue")
        
        if self._assistant_text:
            content.append("ModelX: ", style="bold green")
            content.append(self._assistant_text, style="green")
        
        if not self._user_text and not self._assistant_text:
            content.append("Press Ctrl+Space to start talking...", style="dim italic")
        
        return Panel(content, title="Conversation", border_style="blue", box=ROUNDED)

    def _render_sidebar(self) -> Panel:
        table = Table(box=None, show_header=False, padding=(0, 1))
        table.add_column("Key", style="cyan")
        table.add_column("Value", style="white")
        
        if self._stats:
            table.add_row("Provider", self._stats.get("provider", "N/A"))
            table.add_row("Model", self._stats.get("model", "N/A"))
            table.add_row("Turns", str(self._stats.get("turns", 0)))
            table.add_row("Tokens", str(self._stats.get("total_tokens", 0)))
        
        table.add_row("", "")
        table.add_row("Controls", "")
        table.add_row("Ctrl+Space", "Push-to-talk")
        table.add_row("Ctrl+C", "Quit")
        table.add_row("Ctrl+L", "Clear history")
        table.add_row("Ctrl+S", "Save conversation")
        
        return Panel(table, title="Status", border_style="green", box=ROUNDED)


class SimpleVoiceUI:
    def __init__(self):
        self.console = Console()
        self._listening = False
        self._processing = False

    def print_status(self, message: str, style: str = "white"):
        self.console.print(f"[{style}]{message}[/{style}]")

    def print_user(self, text: str):
        self.console.print(f"[bold blue]You:[/bold blue] {text}")

    def print_assistant(self, text: str, end: str = "\n"):
        self.console.print(f"[bold green]ModelX:[/bold green] {text}", end=end)

    def print_listening(self):
        self.console.print("[bold green]🎤 Listening...[/bold green]", end="\r")

    def print_processing(self):
        self.console.print("[bold yellow]🤔 Thinking...[/bold yellow]", end="\r")

    def clear_line(self):
        self.console.print(" " * 50, end="\r")

    def print_error(self, message: str):
        self.console.print(f"[bold red]Error:[/bold red] {message}")

    def print_info(self, message: str):
        self.console.print(f"[dim]{message}[/dim]")