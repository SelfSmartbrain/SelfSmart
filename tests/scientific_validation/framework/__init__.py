"""
Scientific Validation Framework for ModelX.

A publication-quality evaluation suite that measures REAL capability improvements
without fake numbers, hardcoded scores, or fallback implementations.
"""

from .experiment_runner import ExperimentRunner
from .dataset_manager import DatasetManager
from .result_store import ResultStore
from .config import ValidationConfig

__all__ = [
    "ExperimentRunner",
    "DatasetManager",
    "ResultStore",
    "ValidationConfig",
]
