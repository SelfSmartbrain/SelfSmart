"""
Central metrics collector for experiments.
"""

from typing import List, Dict, Any, Optional
from collections import defaultdict
import time

from .metric_types import Metric, MetricType
from .classification_metrics import ClassificationMetrics
from .prediction_metrics import PredictionMetrics
from .performance_metrics import PerformanceMetrics, LatencyTimer


class MetricsCollector:
    """Collect and aggregate metrics from experiments."""
    
    def __init__(self):
        self.metrics: Dict[str, List[Metric]] = defaultdict(list)
        self.timers: Dict[str, LatencyTimer] = {}
    
    def record_metric(
        self,
        name: str,
        metric_type: MetricType,
        value: float,
        unit: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a metric."""
        metric = Metric(
            name=name,
            metric_type=metric_type,
            value=value,
            unit=unit,
            metadata=metadata or {},
        )
        self.metrics[name].append(metric)
    
    def record_classification_metrics(
        self,
        predictions: List[int],
        ground_truth: List[int],
        prefix: str = "",
    ) -> Dict[str, float]:
        """Record classification metrics."""
        metrics_dict = ClassificationMetrics.compute_binary_metrics(
            predictions, ground_truth
        )
        
        for metric_name, value in metrics_dict.items():
            full_name = f"{prefix}{metric_name}" if prefix else metric_name
            
            metric_type = MetricType.CUSTOM
            if metric_name == "accuracy":
                metric_type = MetricType.ACCURACY
            elif metric_name == "precision":
                metric_type = MetricType.PRECISION
            elif metric_name == "recall":
                metric_type = MetricType.RECALL
            elif metric_name == "f1":
                metric_type = MetricType.F1
            
            self.record_metric(
                name=full_name,
                metric_type=metric_type,
                value=value,
            )
        
        return metrics_dict
    
    def record_prediction_metrics(
        self,
        probabilities: List[float],
        ground_truth: List[int],
        prefix: str = "",
    ) -> Dict[str, float]:
        """Record prediction metrics."""
        brier = PredictionMetrics.brier_score(probabilities, ground_truth)
        ece = PredictionMetrics.expected_calibration_error(
            probabilities, ground_truth
        )
        
        metrics_dict = {
            "brier_score": brier,
            "expected_calibration_error": ece,
        }
        
        for metric_name, value in metrics_dict.items():
            full_name = f"{prefix}{metric_name}" if prefix else metric_name
            
            metric_type = (
                MetricType.BRIER_SCORE
                if metric_name == "brier_score"
                else MetricType.EXPECTED_CALIBRATION_ERROR
            )
            
            self.record_metric(
                name=full_name,
                metric_type=metric_type,
                value=value,
            )
        
        return metrics_dict
    
    def record_performance_metrics(
        self,
        latencies: List[float],
        total_tokens: int,
        total_cost_usd: float,
        num_operations: int,
        duration_seconds: float,
        prefix: str = "",
    ) -> Dict[str, float]:
        """Record performance metrics."""
        latency_stats = PerformanceMetrics.compute_latency_stats(latencies)
        throughput = PerformanceMetrics.compute_throughput(
            num_operations, duration_seconds
        )
        cost_per_op = PerformanceMetrics.compute_cost_per_operation(
            total_cost_usd, num_operations
        )
        tokens_per_op = PerformanceMetrics.compute_token_efficiency(
            total_tokens, num_operations
        )
        
        metrics_dict = {
            **{f"latency_{k}": v for k, v in latency_stats.items()},
            "throughput": throughput,
            "cost_per_operation": cost_per_op,
            "tokens_per_operation": tokens_per_op,
        }
        
        for metric_name, value in metrics_dict.items():
            full_name = f"{prefix}{metric_name}" if prefix else metric_name
            
            metric_type = MetricType.CUSTOM
            if "latency" in metric_name:
                metric_type = MetricType.LATENCY
            elif metric_name == "throughput":
                metric_type = MetricType.THROUGHPUT
            elif metric_name == "cost_per_operation":
                metric_type = MetricType.COST
            elif metric_name == "tokens_per_operation":
                metric_type = MetricType.TOKEN_USAGE
            
            unit = None
            if "latency" in metric_name:
                unit = "seconds"
            elif metric_name == "throughput":
                unit = "ops/sec"
            elif metric_name == "cost_per_operation":
                unit = "USD"
            elif metric_name == "tokens_per_operation":
                unit = "tokens"
            
            self.record_metric(
                name=full_name,
                metric_type=metric_type,
                value=value,
                unit=unit,
            )
        
        return metrics_dict
    
    @contextmanager
    def measure_latency(self, name: str):
        """Context manager to measure latency of an operation."""
        timer = LatencyTimer(name)
        self.timers[name] = timer
        
        with timer:
            yield timer
        
        duration = timer.get_duration()
        self.record_metric(
            name=name,
            metric_type=MetricType.LATENCY,
            value=duration,
            unit="seconds",
        )
    
    def get_metric_values(self, name: str) -> List[float]:
        """Get all values for a metric."""
        return [m.value for m in self.metrics.get(name, [])]
    
    def get_metric_summary(self, name: Optional[str] = None) -> Dict[str, Any]:
        """Get summary of metrics."""
        if name:
            values = self.get_metric_values(name)
            if not values:
                return {}
            
            import numpy as np
            
            return {
                "name": name,
                "count": len(values),
                "mean": np.mean(values),
                "median": np.median(values),
                "std": np.std(values),
                "min": np.min(values),
                "max": np.max(values),
            }
        else:
            # Summary of all metrics
            summary = {}
            for metric_name in self.metrics.keys():
                summary[metric_name] = self.get_metric_summary(metric_name)
            return summary
    
    def reset(self) -> None:
        """Reset all metrics."""
        self.metrics.clear()
        self.timers.clear()
