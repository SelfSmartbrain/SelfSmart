"""
Cognitive Attention System - Phase 13

The Cognitive Attention System decides:
- What deserves thinking?
- What deserves memory?
- What deserves action?

Similar to biological attention, this system allocates cognitive
resources based on salience, importance, and goals.
"""

from .attention_engine import AttentionEngine
from .salience_detector import SalienceDetector
from .priority_manager import PriorityManager

__all__ = [
    "AttentionEngine",
    "SalienceDetector",
    "PriorityManager",
]
