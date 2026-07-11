"""Phase V2: Scientific Validation & Capability Measurement

This module provides comprehensive validation, benchmarking, and ablation studies
to prove that ModelX components create genuine capability improvements.
"""

from .framework import ValidationFramework, ValidationResult
from .metrics import MetricsCollector, MetricType
from .ablation import AblationStudy
from .benchmarks import CodingBenchmark

__all__ = [
    "ValidationFramework",
    "ValidationResult",
    "MetricsCollector",
    "MetricType",
    "AblationStudy",
    "CodingBenchmark",
]
