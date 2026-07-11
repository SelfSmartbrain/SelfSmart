"""uncertainty_model.py

Models and quantifies uncertainty in decisions.
Provides methods to handle and reduce uncertainty.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

import numpy as np

from src.config.logging import get_logger

logger = get_logger(__name__)


class UncertaintyType(str, Enum):
    """Types of uncertainty."""
    EPISTEMIC = "epistemic"  # Knowledge uncertainty
    ALEATORIC = "aleatoric"  # Random uncertainty
    ONTOLOGICAL = "ontological"  # Model uncertainty


@dataclass
class UncertaintyEstimate:
    """An estimate of uncertainty."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    source: str = ""
    uncertainty_type: UncertaintyType = UncertaintyType.EPISTEMIC
    mean: float = 0.0
    std_dev: float = 0.1
    confidence_interval: Tuple[float, float] = (0.0, 1.0)
    sample_size: int = 1
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "source": self.source,
            "uncertainty_type": self.uncertainty_type.value,
            "mean": self.mean,
            "std_dev": self.std_dev,
            "confidence_interval": self.confidence_interval,
            "sample_size": self.sample_size,
            "metadata": self.metadata,
        }


class UncertaintyModel:
    """Models uncertainty in decision-making."""
    
    def __init__(self):
        self.uncertainty_estimates: Dict[str, UncertaintyEstimate] = {}
        logger.info("UncertaintyModel initialized")
    
    def estimate_uncertainty(
        self,
        source: str,
        values: List[float],
        uncertainty_type: UncertaintyType = UncertaintyType.EPISTEMIC,
    ) -> UncertaintyEstimate:
        """Estimate uncertainty from a set of values."""
        if not values:
            raise ValueError("Cannot estimate uncertainty from empty values")
        
        mean = np.mean(values)
        std_dev = np.std(values)
        
        # Calculate 95% confidence interval
        if len(values) > 1:
            from scipy import stats
            ci = stats.t.interval(0.95, len(values) - 1, loc=mean, scale=std_dev / np.sqrt(len(values)))
        else:
            ci = (mean - std_dev, mean + std_dev)
        
        estimate = UncertaintyEstimate(
            source=source,
            uncertainty_type=uncertainty_type,
            mean=mean,
            std_dev=std_dev,
            confidence_interval=ci,
            sample_size=len(values),
        )
        
        self.uncertainty_estimates[estimate.id] = estimate
        logger.info(f"Estimated uncertainty for {source}: {std_dev:.3f}")
        
        return estimate
    
    def combine_uncertainties(
        self,
        estimates: List[UncertaintyEstimate],
        method: str = "weighted_average",
    ) -> UncertaintyEstimate:
        """Combine multiple uncertainty estimates."""
        if not estimates:
            raise ValueError("Cannot combine empty estimates")
        
        if method == "weighted_average":
            return self._weighted_average_combine(estimates)
        elif method == "maximum":
            return self._maximum_combine(estimates)
        elif method == "independent":
            return self._independent_combine(estimates)
        else:
            return self._weighted_average_combine(estimates)
    
    def _weighted_average_combine(
        self,
        estimates: List[UncertaintyEstimate],
    ) -> UncertaintyEstimate:
        """Combine using weighted average (weights by sample size)."""
        total_weight = sum(e.sample_size for e in estimates)
        
        weighted_mean = sum(e.mean * e.sample_size for e in estimates) / total_weight
        weighted_std = sum(e.std_dev * e.sample_size for e in estimates) / total_weight
        
        return UncertaintyEstimate(
            source="combined",
            uncertainty_type=estimates[0].uncertainty_type,
            mean=weighted_mean,
            std_dev=weighted_std,
            confidence_interval=(weighted_mean - 2 * weighted_std, weighted_mean + 2 * weighted_std),
            sample_size=total_weight,
        )
    
    def _maximum_combine(
        self,
        estimates: List[UncertaintyEstimate],
    ) -> UncertaintyEstimate:
        """Combine using maximum uncertainty (conservative)."""
        max_std = max(e.std_dev for e in estimates)
        mean = np.mean([e.mean for e in estimates])
        
        return UncertaintyEstimate(
            source="combined_max",
            uncertainty_type=estimates[0].uncertainty_type,
            mean=mean,
            std_dev=max_std,
            confidence_interval=(mean - 2 * max_std, mean + 2 * max_std),
            sample_size=sum(e.sample_size for e in estimates),
        )
    
    def _independent_combine(
        self,
        estimates: List[UncertaintyEstimate],
    ) -> UncertaintyEstimate:
        """Combine assuming independent uncertainties."""
        mean = np.mean([e.mean for e in estimates])
        
        # Variance adds for independent variables
        variances = [e.std_dev ** 2 for e in estimates]
        combined_std = np.sqrt(sum(variances))
        
        return UncertaintyEstimate(
            source="combined_independent",
            uncertainty_type=estimates[0].uncertainty_type,
            mean=mean,
            std_dev=combined_std,
            confidence_interval=(mean - 2 * combined_std, mean + 2 * combined_std),
            sample_size=min(e.sample_size for e in estimates),
        )
    
    def reduce_uncertainty(
        self,
        estimate_id: str,
        new_values: List[float],
    ) -> UncertaintyEstimate:
        """Reduce uncertainty by adding more data."""
        if estimate_id not in self.uncertainty_estimates:
            raise ValueError(f"Estimate {estimate_id} not found")
        
        old_estimate = self.uncertainty_estimates[estimate_id]
        
        # Combine old and new data
        all_values = new_values  # In practice, would combine with old data
        
        new_estimate = self.estimate_uncertainty(
            source=old_estimate.source,
            values=all_values,
            uncertainty_type=old_estimate.uncertainty_type,
        )
        
        self.uncertainty_estimates[estimate_id] = new_estimate
        logger.info(f"Reduced uncertainty for {estimate_id}: {old_estimate.std_dev:.3f} -> {new_estimate.std_dev:.3f}")
        
        return new_estimate
    
    def calculate_information_gain(
        self,
        before: UncertaintyEstimate,
        after: UncertaintyEstimate,
    ) -> float:
        """Calculate information gain from reducing uncertainty."""
        # Information gain = reduction in variance
        before_variance = before.std_dev ** 2
        after_variance = after.std_dev ** 2
        
        return before_variance - after_variance
    
    def value_of_information(
        self,
        estimate: UncertaintyEstimate,
        decision_value: float,
    ) -> float:
        """Calculate the value of reducing uncertainty."""
        # Simple heuristic: value proportional to current uncertainty
        # and decision value
        uncertainty_ratio = estimate.std_dev / estimate.mean if estimate.mean > 0 else estimate.std_dev
        
        return decision_value * uncertainty_ratio
    
    def get_uncertainty_summary(self) -> Dict[str, Any]:
        """Get a summary of all uncertainty estimates."""
        if not self.uncertainty_estimates:
            return {"total_estimates": 0}
        
        estimates = list(self.uncertainty_estimates.values())
        
        return {
            "total_estimates": len(estimates),
            "by_type": {
                utype.value: sum(1 for e in estimates if e.uncertainty_type == utype)
                for utype in UncertaintyType
            },
            "average_std_dev": np.mean([e.std_dev for e in estimates]),
            "max_std_dev": max(e.std_dev for e in estimates),
            "min_std_dev": min(e.std_dev for e in estimates),
        }
