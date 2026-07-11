"""
Prediction metrics for probabilistic forecasts.
"""

from typing import List, Tuple
import numpy as np
from .metric_types import Metric, MetricType


class PredictionMetrics:
    """Compute prediction quality metrics."""
    
    @staticmethod
    def brier_score(
        probabilities: List[float],
        ground_truth: List[int],
    ) -> float:
        """Compute Brier score for probabilistic predictions."""
        if len(probabilities) != len(ground_truth):
            raise ValueError("Probabilities and ground truth must have same length")
        
        squared_errors = [(p - t) ** 2 for p, t in zip(probabilities, ground_truth)]
        return np.mean(squared_errors)
    
    @staticmethod
    def rmse(
        predictions: List[float],
        ground_truth: List[float],
    ) -> float:
        """Compute root mean squared error."""
        if len(predictions) != len(ground_truth):
            raise ValueError("Predictions and ground truth must have same length")
        
        squared_errors = [(p - t) ** 2 for p, t in zip(predictions, ground_truth)]
        return np.sqrt(np.mean(squared_errors))
    
    @staticmethod
    def mae(
        predictions: List[float],
        ground_truth: List[float],
    ) -> float:
        """Compute mean absolute error."""
        if len(predictions) != len(ground_truth):
            raise ValueError("Predictions and ground truth must have same length")
        
        absolute_errors = [abs(p - t) for p, t in zip(predictions, ground_truth)]
        return np.mean(absolute_errors)
    
    @staticmethod
    def expected_calibration_error(
        probabilities: List[float],
        ground_truth: List[int],
        n_bins: int = 10,
    ) -> float:
        """Compute expected calibration error (ECE)."""
        if len(probabilities) != len(ground_truth):
            raise ValueError("Probabilities and ground truth must have same length")
        
        # Bin predictions by confidence
        bin_edges = np.linspace(0, 1, n_bins + 1)
        bin_indices = np.digitize(probabilities, bin_edges) - 1
        
        ece = 0.0
        total_samples = len(probabilities)
        
        for i in range(n_bins):
            # Get samples in this bin
            mask = bin_indices == i
            if not np.any(mask):
                continue
            
            bin_probs = np.array(probabilities)[mask]
            bin_truths = np.array(ground_truth)[mask]
            
            # Compute average confidence and accuracy in bin
            avg_confidence = np.mean(bin_probs)
            accuracy = np.mean(bin_truths)
            
            # Weight by bin size
            bin_weight = len(bin_probs) / total_samples
            
            # Add weighted calibration error
            ece += bin_weight * abs(avg_confidence - accuracy)
        
        return ece
    
    @staticmethod
    def calibration_curve(
        probabilities: List[float],
        ground_truth: List[int],
        n_bins: int = 10,
    ) -> Tuple[List[float], List[float]]:
        """Compute calibration curve (reliability diagram)."""
        if len(probabilities) != len(ground_truth):
            raise ValueError("Probabilities and ground truth must have same length")
        
        bin_edges = np.linspace(0, 1, n_bins + 1)
        bin_indices = np.digitize(probabilities, bin_edges) - 1
        
        bin_confidences = []
        bin_accuracies = []
        
        for i in range(n_bins):
            mask = bin_indices == i
            if not np.any(mask):
                continue
            
            bin_probs = np.array(probabilities)[mask]
            bin_truths = np.array(ground_truth)[mask]
            
            avg_confidence = np.mean(bin_probs)
            accuracy = np.mean(bin_truths)
            
            bin_confidences.append(avg_confidence)
            bin_accuracies.append(accuracy)
        
        return bin_confidences, bin_accuracies
