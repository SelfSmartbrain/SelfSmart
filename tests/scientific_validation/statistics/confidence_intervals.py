"""
Confidence interval computation.
"""

from typing import List, Tuple, Optional
import numpy as np
from scipy import stats


class ConfidenceIntervals:
    """Compute confidence intervals for metrics."""
    
    @staticmethod
    def mean_ci(
        values: List[float],
        confidence_level: float = 0.95,
    ) -> Tuple[float, float, float]:
        """
        Compute confidence interval for the mean.
        
        Returns:
            (mean, lower_bound, upper_bound)
        """
        if not values:
            return 0.0, 0.0, 0.0
        
        values_array = np.array(values)
        mean = np.mean(values)
        std_error = stats.sem(values_array)
        
        alpha = 1 - confidence_level
        t_critical = stats.t.ppf(1 - alpha / 2, len(values) - 1)
        
        margin_of_error = t_critical * std_error
        
        lower_bound = mean - margin_of_error
        upper_bound = mean + margin_of_error
        
        return mean, lower_bound, upper_bound
    
    @staticmethod
    def median_ci(
        values: List[float],
        confidence_level: float = 0.95,
    ) -> Tuple[float, float, float]:
        """
        Compute confidence interval for the median using binomial method.
        
        Returns:
            (median, lower_bound, upper_bound)
        """
        if not values:
            return 0.0, 0.0, 0.0
        
        values_sorted = sorted(values)
        n = len(values_sorted)
        median = np.median(values_sorted)
        
        # Use binomial method for median CI
        alpha = 1 - confidence_level
        k = int(stats.binom.ppf(alpha / 2, n, 0.5))
        l = n - k - 1
        
        lower_bound = values_sorted[k] if k >= 0 else values_sorted[0]
        upper_bound = values_sorted[l] if l < n else values_sorted[-1]
        
        return median, lower_bound, upper_bound
    
    @staticmethod
    def proportion_ci(
        successes: int,
        total: int,
        confidence_level: float = 0.95,
        method: str = "wilson",
    ) -> Tuple[float, float, float]:
        """
        Compute confidence interval for a proportion.
        
        Returns:
            (proportion, lower_bound, upper_bound)
        """
        if total == 0:
            return 0.0, 0.0, 0.0
        
        p = successes / total
        
        if method == "normal":
            # Normal approximation
            std_error = np.sqrt(p * (1 - p) / total)
            z_critical = stats.norm.ppf(1 - (1 - confidence_level) / 2)
            margin_of_error = z_critical * std_error
            
            lower_bound = max(0.0, p - margin_of_error)
            upper_bound = min(1.0, p + margin_of_error)
        
        elif method == "wilson":
            # Wilson score interval (better for small samples)
            z = stats.norm.ppf(1 - (1 - confidence_level) / 2)
            denominator = 1 + z**2 / total
            center = (p + z**2 / (2 * total)) / denominator
            margin = z * np.sqrt(p * (1 - p) / total + z**2 / (4 * total**2)) / denominator
            
            lower_bound = max(0.0, center - margin)
            upper_bound = min(1.0, center + margin)
        
        elif method == "clopper-pearson":
            # Exact Clopper-Pearson interval
            alpha = 1 - confidence_level
            lower_bound = stats.beta.ppf(alpha / 2, successes, total - successes + 1)
            upper_bound = stats.beta.ppf(1 - alpha / 2, successes + 1, total - successes)
            
            # Handle edge cases
            if successes == 0:
                lower_bound = 0.0
            if successes == total:
                upper_bound = 1.0
        else:
            raise ValueError(f"Unknown method: {method}")
        
        return p, lower_bound, upper_bound
    
    @staticmethod
    def percentile_ci(
        values: List[float],
        percentile: float,
        confidence_level: float = 0.95,
    ) -> Tuple[float, float, float]:
        """
        Compute confidence interval for a percentile.
        
        Returns:
            (percentile_value, lower_bound, upper_bound)
        """
        if not values:
            return 0.0, 0.0, 0.0
        
        values_sorted = sorted(values)
        n = len(values_sorted)
        
        # Compute percentile
        percentile_value = np.percentile(values_sorted, percentile)
        
        # Use binomial method for percentile CI
        alpha = 1 - confidence_level
        k = int(stats.binom.ppf(alpha / 2, n, percentile / 100))
        l = n - k - 1
        
        lower_bound = values_sorted[k] if k >= 0 else values_sorted[0]
        upper_bound = values_sorted[l] if l < n else values_sorted[-1]
        
        return percentile_value, lower_bound, upper_bound
