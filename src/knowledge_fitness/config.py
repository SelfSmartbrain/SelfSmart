"""Configuration for knowledge fitness evaluation."""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from enum import Enum
from datetime import timedelta


class FitnessMetric(Enum):
    """Metrics used to evaluate knowledge fitness."""

    AGE = "age"  # How old is the memory
    ACCESS_FREQUENCY = "access_frequency"  # How often accessed
    CONFIDENCE = "confidence"  # Original confidence score
    VALIDATION_COUNT = "validation_count"  # Times validated against reality
    CONTRADICTION_COUNT = "contradiction_count"  # Times contradicted
    SEMANTIC_COHERENCE = "semantic_coherence"  # Internal consistency
    UTILITY_SCORE = "utility_score"  # Practical usefulness


@dataclass
class FitnessConfig:
    """Configuration for knowledge fitness evaluation."""

    # Weights for different metrics (must sum to ~1.0)
    metric_weights: Dict[FitnessMetric, float] = field(
        default_factory=lambda: {
            FitnessMetric.AGE: 0.20,
            FitnessMetric.ACCESS_FREQUENCY: 0.20,
            FitnessMetric.CONFIDENCE: 0.15,
            FitnessMetric.VALIDATION_COUNT: 0.15,
            FitnessMetric.CONTRADICTION_COUNT: 0.15,
            FitnessMetric.SEMANTIC_COHERENCE: 0.10,
            FitnessMetric.UTILITY_SCORE: 0.05,
        }
    )

    # Thresholds
    min_fitness_threshold: float = 0.3  # Below this: candidate for pruning
    critical_fitness_threshold: float = 0.15  # Below this: immediate pruning
    high_value_threshold: float = 0.75  # Above this: protected from pruning

    # Time-based decay
    max_age_days: int = 365  # Maximum age before decay accelerates
    half_life_days: int = 90  # Half-life for access frequency

    # Pruning behavior
    max_prune_per_run: int = 100  # Max beliefs to prune in one run
    prune_batch_size: int = 10  # Batch size for pruning
    dry_run: bool = True  # If True, only report what would be pruned

    # Validation
    require_validation_after_days: int = 30  # Re-validate after this many days
    validation_sample_rate: float = 0.1  # Fraction of beliefs to validate per run

    # Semantic coherence
    coherence_threshold: float = 0.6  # Minimum semantic coherence
    contradiction_penalty: float = 0.3  # Penalty per contradiction

    # Collections to evaluate (Qdrant)
    qdrant_collections: List[str] = field(
        default_factory=lambda: [
            "knowledge",
            "memories",
            "reflections",
            "strategies",
            "skills",
            "experiences",
            "memory_clusters",
        ]
    )

    # Neo4j node labels to evaluate
    neo4j_labels: List[str] = field(
        default_factory=lambda: [
            "Belief",
            "Fact",
            "Concept",
            "Rule",
            "Pattern",
            "Memory",
        ]
    )


@dataclass
class PruningConfig:
    """Configuration for belief pruning."""

    # Safety
    dry_run: bool = True
    require_confirmation: bool = True
    backup_before_prune: bool = True

    # Thresholds
    fitness_threshold: float = 0.3
    max_prune_per_run: int = 100

    # Behavior
    prune_contradictions: bool = True
    prune_duplicates: bool = True
    prune_unvalidated: bool = True

    # Batch processing
    batch_size: int = 10
    delay_between_batches: float = 0.5  # seconds


# Default configurations
DEFAULT_FITNESS_CONFIG = FitnessConfig()
DEFAULT_PRUNING_CONFIG = PruningConfig()
