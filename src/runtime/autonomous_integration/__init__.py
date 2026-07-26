"""
Autonomous Cognitive Integration - Connects CognitiveKernel with Runtime for continuous thinking.

This module implements the "heartbeat" that drives the agent's autonomous cognitive cycle:
- Background thinking when idle
- Memory consolidation during downtime  
- Goal reflection and replanning
- Continuous learning from experience
"""

from .cognitive_runtime_bridge import CognitiveRuntimeBridge, BridgeConfig
from .background_thinker import BackgroundThinker, ThinkingConfig
from .goal_reflector import GoalReflector, ReflectionConfig
from .memory_consolidator import MemoryConsolidator, ConsolidationConfig

__all__ = [
    "CognitiveRuntimeBridge",
    "BridgeConfig",
    "BackgroundThinker", 
    "ThinkingConfig",
    "GoalReflector",
    "ReflectionConfig",
    "MemoryConsolidator",
    "ConsolidationConfig",
]