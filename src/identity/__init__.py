"""
Long-Term Identity System - Phase 13

The Long-Term Identity System provides:
- Persistent identity across sessions
- Self-model and capabilities tracking
- Mission and goal management
- Long-term learning and adaptation
"""

from .identity_engine import IdentityEngine
from .self_model import SelfModel
from .mission_manager import MissionManager

__all__ = [
    "IdentityEngine",
    "SelfModel",
    "MissionManager",
]
