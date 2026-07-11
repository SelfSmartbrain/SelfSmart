"""
Scientific validation experiments.

Each experiment measures REAL capability improvements using production components.
"""

from .memory_ablation import MemoryAblationExperiment
from .concept_engine import ConceptEngineExperiment
from .world_model import WorldModelExperiment
from .governance import GovernanceExperiment
from .coding_benchmark import CodingBenchmarkExperiment
from .long_horizon import LongHorizonExperiment
from .ablation_study import AblationStudyExperiment

__all__ = [
    "MemoryAblationExperiment",
    "ConceptEngineExperiment",
    "WorldModelExperiment",
    "GovernanceExperiment",
    "CodingBenchmarkExperiment",
    "LongHorizonExperiment",
    "AblationStudyExperiment",
]
