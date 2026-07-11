"""
Metric type definitions.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class MetricType(Enum):
    """Types of metrics."""
    
    # Classification metrics
    ACCURACY = "accuracy"
    PRECISION = "precision"
    RECALL = "recall"
    F1 = "f1"
    TRUE_POSITIVES = "true_positives"
    TRUE_NEGATIVES = "true_negatives"
    FALSE_POSITIVES = "false_positives"
    FALSE_NEGATIVES = "false_negatives"
    
    # Prediction metrics
    BRIER_SCORE = "brier_score"
    RMSE = "rmse"
    MAE = "mae"
    CALIBRATION_ERROR = "calibration_error"
    EXPECTED_CALIBRATION_ERROR = "expected_calibration_error"
    
    # Performance metrics
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    TOKEN_USAGE = "token_usage"
    COST = "cost"
    
    # Ranking metrics
    ROC_AUC = "roc_auc"
    PR_AUC = "pr_auc"
    
    # Custom metrics
    CUSTOM = "custom"


@dataclass
class Metric:
    """A single metric measurement."""
    
    name: str
    metric_type: MetricType
    value: float
    unit: Optional[str] = None
    metadata: dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}
    
    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "metric_type": self.metric_type.value,
            "value": self.value,
            "unit": self.unit,
            "metadata": self.metadata,
        }
