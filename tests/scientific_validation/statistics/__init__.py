"""
Statistics engine for scientific validation.

Provides statistical analysis including t-tests, confidence intervals,
effect sizes, and other statistical tests.
"""

from .statistical_tests import StatisticalTests
from .confidence_intervals import ConfidenceIntervals
from .effect_sizes import EffectSizes
from .bootstrap import Bootstrap

__all__ = [
    "StatisticalTests",
    "ConfidenceIntervals",
    "EffectSizes",
    "Bootstrap",
]
