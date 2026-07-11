"""Knowledge Lineage Tracking System - Phase 14H

This module provides Git-like history tracking for knowledge structures,
tracking the evolution from concepts to theories to mental models to strategies.
"""

from .knowledge_lineage import KnowledgeLineage, LineageNode, LineageEdge

__all__ = [
    "KnowledgeLineage",
    "LineageNode",
    "LineageEdge",
]
