"""
Bootstrap resampling for confidence intervals.
"""

from typing import List, Tuple, Callable, Optional
import numpy as np


class Bootstrap:
    """Bootstrap resampling for robust confidence intervals."""
    
    @staticmethod
    def bootstrap_ci(
        values: List[float],
        statistic: Callable[[List[float]], float] = np.mean,
        n_bootstrap: int = 10000,
        confidence_level: float = 0.95,
        random_seed: Optional[int] = None,
    ) -> Tuple[float, float, float]:
        """
        Compute bootstrap confidence interval for any statistic.
        
        Returns:
            (statistic_value, lower_bound, upper_bound)
        """
        if not values:
            return 0.0, 0.0, 0.0
        
        if random_seed is not None:
            np.random.seed(random_seed)
        
        values_array = np.array(values)
        n = len(values_array)
        
        # Compute observed statistic
        observed_statistic = statistic(values_array)
        
        # Bootstrap resampling
        bootstrap_statistics = []
        for _ in range(n_bootstrap):
            # Resample with replacement
            resample = np.random.choice(values_array, size=n, replace=True)
            bootstrap_stat = statistic(resample)
            bootstrap_statistics.append(bootstrap_stat)
        
        bootstrap_statistics = np.array(bootstrap_statistics)
        
        # Compute percentile confidence interval
        alpha = 1 - confidence_level
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        lower_bound = np.percentile(bootstrap_statistics, lower_percentile)
        upper_bound = np.percentile(bootstrap_statistics, upper_percentile)
        
        return observed_statistic, lower_bound, upper_bound
    
    @staticmethod
    def bootstrap_mean_ci(
        values: List[float],
        n_bootstrap: int = 10000,
        confidence_level: float = 0.95,
        random_seed: Optional[int] = None,
    ) -> Tuple[float, float, float]:
        """Bootstrap confidence interval for the mean."""
        return Bootstrap.bootstrap_ci(
            values,
            statistic=np.mean,
            n_bootstrap=n_bootstrap,
            confidence_level=confidence_level,
            random_seed=random_seed,
        )
    
    @staticmethod
    def bootstrap_median_ci(
        values: List[float],
        n_bootstrap: int = 10000,
        confidence_level: float = 0.95,
        random_seed: Optional[int] = None,
    ) -> Tuple[float, float, float]:
        """Bootstrap confidence interval for the median."""
        return Bootstrap.bootstrap_ci(
            values,
            statistic=np.median,
            n_bootstrap=n_bootstrap,
            confidence_level=confidence_level,
            random_seed=random_seed,
        )
    
    @staticmethod
    def bootstrap_std_ci(
        values: List[float],
        n_bootstrap: int = 10000,
        confidence_level: float = 0.95,
        random_seed: Optional[int] = None,
    ) -> Tuple[float, float, float]:
        """Bootstrap confidence interval for standard deviation."""
        return Bootstrap.bootstrap_ci(
            values,
            statistic=np.std,
            n_bootstrap=n_bootstrap,
            confidence_level=confidence_level,
            random_seed=random_seed,
        )
    
    @staticmethod
    def bootstrap_difference_ci(
        group1: List[float],
        group2: List[float],
        n_bootstrap: int = 10000,
        confidence_level: float = 0.95,
        random_seed: Optional[int] = None,
    ) -> Tuple[float, float, float]:
        """
        Bootstrap confidence interval for the difference between two groups.
        
        Returns:
            (mean_difference, lower_bound, upper_bound)
        """
        if not group1 or not group2:
            return 0.0, 0.0, 0.0
        
        if random_seed is not None:
            np.random.seed(random_seed)
        
        group1_array = np.array(group1)
        group2_array = np.array(group2)
        
        n1 = len(group1_array)
        n2 = len(group2_array)
        
        # Observed difference
        observed_diff = np.mean(group1) - np.mean(group2)
        
        # Bootstrap resampling
        bootstrap_diffs = []
        for _ in range(n_bootstrap):
            # Resample each group independently
            resample1 = np.random.choice(group1_array, size=n1, replace=True)
            resample2 = np.random.choice(group2_array, size=n2, replace=True)
            
            diff = np.mean(resample1) - np.mean(resample2)
            bootstrap_diffs.append(diff)
        
        bootstrap_diffs = np.array(bootstrap_diffs)
        
        # Compute percentile confidence interval
        alpha = 1 - confidence_level
        lower_percentile = (alpha / 2) * 100
        upper_percentile = (1 - alpha / 2) * 100
        
        lower_bound = np.percentile(bootstrap_diffs, lower_percentile)
        upper_bound = np.percentile(bootstrap_diffs, upper_percentile)
        
        return observed_diff, lower_bound, upper_bound
