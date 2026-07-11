"""
Statistical hypothesis tests.
"""

from typing import List, Tuple, Dict, Any, Optional
import numpy as np
from scipy import stats


class StatisticalTests:
    """Perform statistical hypothesis tests."""
    
    @staticmethod
    def welch_t_test(
        group1: List[float],
        group2: List[float],
    ) -> Dict[str, Any]:
        """
        Perform Welch's t-test (unequal variances t-test).
        
        Returns:
            Dictionary with test statistics and p-value.
        """
        if not group1 or not group2:
            return {
                "statistic": 0.0,
                "p_value": 1.0,
                "degrees_of_freedom": 0,
                "significant": False,
            }
        
        statistic, p_value = stats.ttest_ind(group1, group2, equal_var=False)
        
        # Calculate degrees of freedom (Welch-Satterthwaite equation)
        n1 = len(group1)
        n2 = len(group2)
        var1 = np.var(group1, ddof=1)
        var2 = np.var(group2, ddof=1)
        
        numerator = (var1 / n1 + var2 / n2) ** 2
        denominator = (var1 ** 2) / (n1 ** 2 * (n1 - 1)) + (var2 ** 2) / (n2 ** 2 * (n2 - 1))
        df = numerator / denominator if denominator > 0 else 0
        
        return {
            "statistic": statistic,
            "p_value": p_value,
            "degrees_of_freedom": df,
            "significant": p_value < 0.05,
        }
    
    @staticmethod
    def students_t_test(
        group1: List[float],
        group2: List[float],
    ) -> Dict[str, Any]:
        """
        Perform Student's t-test (equal variances t-test).
        
        Returns:
            Dictionary with test statistics and p-value.
        """
        if not group1 or not group2:
            return {
                "statistic": 0.0,
                "p_value": 1.0,
                "degrees_of_freedom": 0,
                "significant": False,
            }
        
        statistic, p_value = stats.ttest_ind(group1, group2, equal_var=True)
        
        df = len(group1) + len(group2) - 2
        
        return {
            "statistic": statistic,
            "p_value": p_value,
            "degrees_of_freedom": df,
            "significant": p_value < 0.05,
        }
    
    @staticmethod
    def paired_t_test(
        before: List[float],
        after: List[float],
    ) -> Dict[str, Any]:
        """
        Perform paired t-test.
        
        Returns:
            Dictionary with test statistics and p-value.
        """
        if len(before) != len(after) or not before:
            return {
                "statistic": 0.0,
                "p_value": 1.0,
                "degrees_of_freedom": 0,
                "significant": False,
            }
        
        statistic, p_value = stats.ttest_rel(before, after)
        
        df = len(before) - 1
        
        return {
            "statistic": statistic,
            "p_value": p_value,
            "degrees_of_freedom": df,
            "significant": p_value < 0.05,
        }
    
    @staticmethod
    def mann_whitney_u(
        group1: List[float],
        group2: List[float],
    ) -> Dict[str, Any]:
        """
        Perform Mann-Whitney U test (non-parametric).
        
        Returns:
            Dictionary with test statistics and p-value.
        """
        if not group1 or not group2:
            return {
                "statistic": 0,
                "p_value": 1.0,
                "significant": False,
            }
        
        statistic, p_value = stats.mannwhitneyu(group1, group2, alternative='two-sided')
        
        return {
            "statistic": statistic,
            "p_value": p_value,
            "significant": p_value < 0.05,
        }
    
    @staticmethod
    def wilcoxon_signed_rank(
        before: List[float],
        after: List[float],
    ) -> Dict[str, Any]:
        """
        Perform Wilcoxon signed-rank test (non-parametric paired).
        
        Returns:
            Dictionary with test statistics and p-value.
        """
        if len(before) != len(after) or not before:
            return {
                "statistic": 0,
                "p_value": 1.0,
                "significant": False,
            }
        
        statistic, p_value = stats.wilcoxon(before, after)
        
        return {
            "statistic": statistic,
            "p_value": p_value,
            "significant": p_value < 0.05,
        }
    
    @staticmethod
    def chi_square_test(
        observed: List[int],
        expected: Optional[List[int]] = None,
    ) -> Dict[str, Any]:
        """
        Perform chi-square goodness of fit test.
        
        Returns:
            Dictionary with test statistics and p-value.
        """
        if expected is None:
            # Test for uniform distribution
            expected = [sum(observed) / len(observed)] * len(observed)
        
        if len(observed) != len(expected) or not observed:
            return {
                "statistic": 0.0,
                "p_value": 1.0,
                "degrees_of_freedom": 0,
                "significant": False,
            }
        
        statistic, p_value = stats.chisquare(f_obs=observed, f_exp=expected)
        
        df = len(observed) - 1
        
        return {
            "statistic": statistic,
            "p_value": p_value,
            "degrees_of_freedom": df,
            "significant": p_value < 0.05,
        }
    
    @staticmethod
    def kruskal_wallis(*groups: List[float]) -> Dict[str, Any]:
        """
        Perform Kruskal-Wallis H-test (non-parametric ANOVA).
        
        Returns:
            Dictionary with test statistics and p-value.
        """
        if not groups or any(len(g) == 0 for g in groups):
            return {
                "statistic": 0.0,
                "p_value": 1.0,
                "significant": False,
            }
        
        statistic, p_value = stats.kruskal(*groups)
        
        return {
            "statistic": statistic,
            "p_value": p_value,
            "significant": p_value < 0.05,
        }
    
    @staticmethod
    def anova(*groups: List[float]) -> Dict[str, Any]:
        """
        Perform one-way ANOVA.
        
        Returns:
            Dictionary with test statistics and p-value.
        """
        if not groups or any(len(g) == 0 for g in groups):
            return {
                "statistic": 0.0,
                "p_value": 1.0,
                "degrees_of_freedom_between": 0,
                "degrees_of_freedom_within": 0,
                "significant": False,
            }
        
        statistic, p_value = stats.f_oneway(*groups)
        
        k = len(groups)
        n = sum(len(g) for g in groups)
        
        df_between = k - 1
        df_within = n - k
        
        return {
            "statistic": statistic,
            "p_value": p_value,
            "degrees_of_freedom_between": df_between,
            "degrees_of_freedom_within": df_within,
            "significant": p_value < 0.05,
        }
    
    @staticmethod
    def shapiro_wilk(values: List[float]) -> Dict[str, Any]:
        """
        Perform Shapiro-Wilk test for normality.
        
        Returns:
            Dictionary with test statistics and p-value.
        """
        if len(values) < 3:
            return {
                "statistic": 0.0,
                "p_value": 1.0,
                "normal": False,
            }
        
        statistic, p_value = stats.shapiro(values)
        
        return {
            "statistic": statistic,
            "p_value": p_value,
            "normal": p_value > 0.05,
        }
