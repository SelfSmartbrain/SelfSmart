"""Knowledge Fitness System - Phase 14G

This module provides infrastructure for measuring the quality and
utility of knowledge structures through fitness metrics and benchmarks.
"""

from .knowledge_fitness import KnowledgeFitness
from .knowledge_benchmark import KnowledgeBenchmark

__all__ = [
    "KnowledgeFitness",
    "KnowledgeBenchmark",
]
