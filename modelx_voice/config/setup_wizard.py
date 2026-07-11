import asyncio
import os
import sys
from typing import Optional, Dict, Any
from pathlib import Path
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich import box

from .manager import ConfigManager, ModelXConfig

console = Console()

PROVIDERS = {
    "1": ("anthropic", "Anthropic (Claude)", "claude-sonnet-4-20250514"),
    "2": ("openai", "OpenAI (GPT)", "gpt-4o"),
    "3": ("openrouter", "OpenRouter (Multi-provider)", "anthropic/claude-sonnet-4"),
    "4": ("ollama", "Local (Ollama)", "llama3.2"),
}

VOICE_PROFILES = {
    "1": ("professional", "Professional (Male)", "en_US-lessac-medium.onnx"),
    "2": ("casual", "Casual (Female)", "en_US-amy-low.onnx"),
    "3": ("clear", "Clear (Female)", "en_US-libritts-medium.onnx"),
}


class SetupWizard:
    def __init__(self, config_manager: ConfigManager = None):
        self.config_manager = config_manager or ConfigManager()
        self.config: ModelXConfig = self.config_manager.load()

    def run(self) -> bool:
        console.clear()
        self._print_header()
        
        if self.config_manager.is_configured() and not Confirm.ask("\n[bold]Reconfigure existing setup?[/bold]"):
            console.print("[green]Using existing configuration.[/green]")
            return True

        try:
            self._select_provider()
            self._get_api_key()
            self._select_voice()
            self._configure_audio()
            self._configure_behavior()
            self._save_config()
            
            console.print("\n[bold green]✓ Setup complete![/bold green]")
            return True
        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled.[/yellow]")
            return False
        except Exception as e:
            console.print(f"\n[red]Setup failed: {e}[/red]")
            return False

    def _print_header(self):
        console.print(Panel.fit(
            "[bold cyan]ModelX Voice Assistant - Setup[/bold cyan]\n"
            "Welcome! Let's configure your voice assistant.",
            border_style="cyan",
        ))

    def _select_provider(self):
        console.print("\n[bold]Step 1: Choose LLM Provider[/bold]")
        
        table = Table(box=box.SIMPLE)
        table.add_column("Option", style="cyan")
        table.add_column("Provider", style="white")
        table.add_column("Description", style="dim")
        
        for key, (pid, name, model) in PROVIDERS.items():
            table.add_row(key, name, f"Default model: {model}")
        
        console.print(table)
        
        choice = Prompt.ask(
            "Select provider",
            choices=list(PROVIDERS.keys()),
            default="1",
        )
        
        provider_id, provider_name, default_model = PROVIDERS[choice]
        self.config.api.provider = provider_id
        
        if provider_id != "ollama":
            model = Prompt.ask(
                f"Model (default: {default_model})",
                default=default_model,
            )
            self.config.api.model = model
        else:
            base_url = Prompt.ask(
                "Ollama base URL",
                default="http://localhost:11434",
            )
            self.config.api.base_url = base_url
            self.config.api.model = default_model

    def _get_api_key(self):
        if self.config.api.provider == "ollama":
            console.print("[dim]No API key needed for local Ollama.[/dim]")
            return

        console.print("\n[bold]Step 2: Enter API Key[/bold]")
        console.print(f"[dim]Your {self.config.api.provider} API key will be stored securely in the system keyring.[/dim]")
        
        api_key = Prompt.ask(
            "API Key",
            password=True,
        )
        
        if not api_key:
            raise ValueError("API key is required")
        
        self.config.api.api_key = api_key

    def _select_voice(self):
        console.print("\n[bold]Step 3: Select Voice Profile[/bold]")
        
        table = Table(box=box.SIMPLE)
        table.add_column("Option", style="cyan")
        table.add_column("Profile", style="white")
        table.add_column("Description", style="dim")
        
        for key, (pid, name, model) in VOICE_PROFILES.items():
            table.add_row(key, name, f"Model: {model}")
        
        console.print(table)
        
        choice = Prompt.ask(
            "Select voice",
            choices=list(VOICE_PROFILES.keys()),
            default="3",
        )
        
        voice_id, voice_name, voice_model = VOICE_PROFILES[choice]
        self.config.voice.selected_voice = voice_id

    def _configure_audio(self):
        console.print("\n[bold]Step 4: Audio Devices (Optional)[/bold]")
        
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            
            input_devices = [(i, d["name"]) for i, d in enumerate(devices) if d["max_input_channels"] > 0]
            output_devices = [(i, d["name"]) for i, d in enumerate(devices) if d["max_output_channels"] > 0]
            
            if input_devices:
                console.print("\n[cyan]Input devices:[/cyan]")
                for idx, (dev_id, name) in enumerate(input_devices):
                    console.print(f"  {idx}: {name} (id: {dev_id})")
                
                if Confirm.ask("Configure input device?", default=False):
                    choice = Prompt.ask("Select input device", default="0")
                    try:
                        self.config.audio.input_device = input_devices[int(choice)][0]
                    except (ValueError, IndexError):
                        pass
            
            if output_devices:
                console.print("\n[cyan]Output devices:[/cyan]")
                for idx, (dev_id, name) in enumerate(output_devices):
                    console.print(f"  {idx}: {name} (id: {dev_id})")
                
                if Confirm.ask("Configure output device?", default=False):
                    choice = Prompt.ask("Select output device", default="0")
                    try:
                        self.config.audio.output_device = output_devices[int(choice)][0]
                    except (ValueError, IndexError):
                        pass
                        
        except Exception as e:
            console.print(f"[yellow]Could not detect audio devices: {e}[/yellow]")

    def _configure_behavior(self):
        console.print("\n[bold]Step 5: Behavior Settings[/bold]")
        
        self.config.behavior.wake_word = Prompt.ask(
            "Wake word (or empty for push-to-talk)",
            default="hey modelx",
        )
        
        self.config.behavior.auto_listen = Confirm.ask(
            "Auto-listen after response?",
            default=True,
        )
        
        self.config.behavior.vad_aggressiveness = int(Prompt.ask(
            "Voice detection sensitivity (0-3, higher = more sensitive)",
            default="2",
        ))

    def _save_config(self):
        self.config_manager.save()
        console.print(f"\n[green]Configuration saved to {self.config_manager.config_file}[/green]")


async def run_setup_wizard(config_manager: ConfigManager = None) -> bool:
    wizard = SetupWizard(config_manager)
    return wizard.run()


def quick_setup(provider: str, api_key: str, voice: str = "clear") -> bool:
    config_manager = ConfigManager()
    config = config_manager.load()
    
    if provider not in [p[0] for p in PROVIDERS.values()]:
        console.print(f"[red]Unknown provider: {provider}[/red]")
        return False
    
    config.api.provider = provider
    config.api.api_key = api_key
    config.voice.selected_voice = voice
    
    from modelx_voice.brain import get_default_model
    config.api.model = get_default_model(provider)
    
    config_manager.save()
    return True