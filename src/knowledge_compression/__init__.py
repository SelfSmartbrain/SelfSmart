"""Knowledge Compression Engine - Phase 14D

This module provides infrastructure for compressing knowledge from
many observations into a smaller set of reusable insights.
"""

from .compression_engine import CompressionEngine
from .abstraction_engine import AbstractionEngine
from .knowledge_distiller import KnowledgeDistiller

__all__ = [
    "CompressionEngine",
    "AbstractionEngine",
    "KnowledgeDistiller",
]
