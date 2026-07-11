"""
Effect size computation for statistical significance.
"""

from typing import List, Optional
import numpy as np
from scipy import stats


class EffectSizes:
    """Compute effect sizes for comparing groups."""
    
    @staticmethod
    def cohens_d(
        group1: List[float],
        group2: List[float],
    ) -> float:
        """
        Compute Cohen's d effect size.
        
        d = (mean1 - mean2) / pooled_std
        
        Interpretation:
        - 0.2: small effect
        - 0.5: medium effect
        - 0.8: large effect
        """
        if not group1 or not group2:
            return 0.0
        
        mean1 = np.mean(group1)
        mean2 = np.mean(group2)
        
        n1 = len(group1)
        n2 = len(group2)
        
        # Pooled standard deviation
        var1 = np.var(group1, ddof=1)
        var2 = np.var(group2, ddof=1)
        
        pooled_std = np.sqrt(((n1 - 1) * var1 + (n2 - 1) * var2) / (n1 + n2 - 2))
        
        if pooled_std == 0:
            return 0.0
        
        return (mean1 - mean2) / pooled_std
    
    @staticmethod
    def hedges_g(
        group1: List[float],
        group2: List[float],
    ) -> float:
        """
        Compute Hedges' g (bias-corrected Cohen's d for small samples).
        """
        d = EffectSizes.cohens_d(group1, group2)
        
        n1 = len(group1)
        n2 = len(group2)
        total_n = n1 + n2
        
        # Correction factor
        correction = 1 - (3 / (4 * total_n - 9))
        
        return d * correction
    
    @staticmethod
    def cliffs_delta(
        group1: List[float],
        group2: List[float],
    ) -> float:
        """
        Compute Cliff's Delta (non-parametric effect size).
        
        Returns value in [-1, 1]:
        - 0: no effect
        - 1: all values in group1 > group2
        - -1: all values in group1 < group2
        """
        if not group1 or not group2:
            return 0.0
        
        n1 = len(group1)
        n2 = len(group2)
        
        # Count comparisons
        greater = 0
        less = 0
        
        for x in group1:
            for y in group2:
                if x > y:
                    greater += 1
                elif x < y:
                    less += 1
        
        total = n1 * n2
        if total == 0:
            return 0.0
        
        return (greater - less) / total
    
    @staticmethod
    def glass_delta(
        group1: List[float],
        group2: List[float],
    ) -> float:
        """
        Compute Glass's Delta (uses control group SD instead of pooled).
        
        Uses group2 as the control group.
        """
        if not group1 or not group2:
            return 0.0
        
        mean1 = np.mean(group1)
        mean2 = np.mean(group2)
        
        # Use group2's standard deviation
        std2 = np.std(group2, ddof=1)
        
        if std2 == 0:
            return 0.0
        
        return (mean1 - mean2) / std2
    
    @staticmethod
    def pearson_r(
        x: List[float],
        y: List[float],
    ) -> float:
        """Compute Pearson correlation coefficient."""
        if len(x) != len(y) or len(x) < 2:
            return 0.0
        
        correlation, _ = stats.pearsonr(x, y)
        return correlation
    
    @staticmethod
    def r_squared(
        x: List[float],
        y: List[float],
    ) -> float:
        """Compute R-squared (coefficient of determination)."""
        r = EffectSizes.pearson_r(x, y)
        return r ** 2
    
    @staticmethod
    def interpret_cohens_d(d: float) -> str:
        """Interpret Cohen's d effect size."""
        abs_d = abs(d)
        
        if abs_d < 0.2:
            return "negligible"
        elif abs_d < 0.5:
            return "small"
        elif abs_d < 0.8:
            return "medium"
        else:
            return "large"
