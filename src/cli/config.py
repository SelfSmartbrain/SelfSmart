"""Configuration Manager for ModelX CLI."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv

from src.config.logging import get_logger

logger = get_logger(__name__)


class ConfigManager:
    """Manages CLI configuration including LLM provider API keys."""
    
    def __init__(self, config_path: Optional[Path] = None):
        """Initialize configuration manager.
        
        Args:
            config_path: Path to config file. Defaults to ~/.modelx/config.json
        """
        if config_path is None:
            config_dir = Path.home() / ".modelx"
            config_dir.mkdir(exist_ok=True)
            config_path = config_dir / "config.json"
        
        self.config_path = config_path
        self.config: Dict[str, Any] = self._load_config()
        
        # Load environment variables
        load_dotenv()
    
    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if self.config_path.exists():
            try:
                with open(self.config_path, "r") as f:
                    return json.load(f)
            except Exception as e:
                logger.error(f"Error loading config: {e}")
                return {}
        return {}
    
    def _save_config(self) -> None:
        """Save configuration to file."""
        try:
            self.config_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.config_path, "w") as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving config: {e}")
    
    def add_provider(self, provider: str, api_key: str, model: Optional[str] = None) -> None:
        """Add an LLM provider configuration.
        
        Args:
            provider: Provider name (anthropic, openai, custom)
            api_key: API key for the provider
            model: Default model to use
        """
        if "providers" not in self.config:
            self.config["providers"] = {}
        
        self.config["providers"][provider] = {
            "api_key": api_key,
            "model": model
        }
        
        self._save_config()
        logger.info(f"Added provider: {provider}")
    
    def remove_provider(self, provider: str) -> None:
        """Remove an LLM provider configuration.
        
        Args:
            provider: Provider name to remove
        """
        if "providers" in self.config and provider in self.config["providers"]:
            del self.config["providers"][provider]
            self._save_config()
            logger.info(f"Removed provider: {provider}")
    
    def list_providers(self) -> List[Dict[str, Any]]:
        """List all configured providers.
        
        Returns:
            List of provider configurations
        """
        providers = []
        if "providers" in self.config:
            for provider_name, config in self.config["providers"].items():
                providers.append({
                    "provider": provider_name,
                    "api_key": config.get("api_key", ""),
                    "model": config.get("model", "N/A")
                })
        return providers
    
    def get_provider(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get configuration for a specific provider.
        
        Args:
            provider: Provider name
            
        Returns:
            Provider configuration or None
        """
        if "providers" in self.config and provider in self.config["providers"]:
            return self.config["providers"][provider]
        return None
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        self.config[key] = value
        self._save_config()
        logger.info(f"Set config: {key} = {value}")
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        # Check config file first
        if key in self.config:
            return self.config[key]
        
        # Check environment variables
        env_key = f"MODELX_{key.upper()}"
        env_value = os.getenv(env_key)
        if env_value is not None:
            return env_value
        
        return default
    
    def get_api_url(self) -> str:
        """Get the ModelX API URL."""
        return self.get("api_url", "http://localhost:8000")
    
    def get_api_key(self) -> Optional[str]:
        """Get the ModelX API key."""
        return self.get("api_key")
    
    def get_llm_provider(self, provider: str) -> Optional[Dict[str, Any]]:
        """Get LLM provider configuration with fallback to environment variables.
        
        Args:
            provider: Provider name
            
        Returns:
            Provider configuration or None
        """
        # Check config file
        provider_config = self.get_provider(provider)
        if provider_config:
            return provider_config
        
        # Check environment variables
        env_key_map = {
            "anthropic": "ANTHROPIC_API_KEY",
            "openai": "OPENAI_API_KEY",
            "custom": "CUSTOM_API_KEY"
        }
        
        env_key = env_key_map.get(provider)
        if env_key:
            api_key = os.getenv(env_key)
            if api_key:
                return {"api_key": api_key, "model": None}
        
        return None
