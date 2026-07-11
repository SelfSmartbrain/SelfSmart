"""
Cognitive Kernel - Phase 13

The central brain for all agents in ModelX. This module provides:
- Global context management
- Attention allocation
- Memory prioritization
- Agent coordination
- Cognitive resource scheduling

This transforms ModelX from a collection of intelligent components
into a unified cognitive organism.
"""

from .kernel import CognitiveKernel
from .scheduler import CognitiveScheduler
from .attention_manager import AttentionManager
from .cognitive_bus import CognitiveBus
from .context_manager import ContextManager

__all__ = [
    "CognitiveKernel",
    "CognitiveScheduler",
    "AttentionManager",
    "CognitiveBus",
    "ContextManager",
]
