"""Metrics collection and analysis for validation experiments."""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from enum import Enum
from contextlib import contextmanager
import logging

logger = logging.getLogger(__name__)


class MetricType(Enum):
    """Types of metrics to collect."""
    
    # Performance metrics
    LATENCY = "latency"
    THROUGHPUT = "throughput"
    
    # Resource metrics
    CPU_USAGE = "cpu_usage"
    MEMORY_USAGE = "memory_usage"
    TOKEN_USAGE = "token_usage"
    
    # Quality metrics
    SUCCESS_RATE = "success_rate"
    ACCURACY = "accuracy"
    ERROR_RATE = "error_rate"
    
    # Cost metrics
    API_COST = "api_cost"
    TOTAL_COST = "total_cost"
    
    # Task-specific metrics
    TASK_COMPLETION_TIME = "task_completion_time"
    TASK_SUCCESS = "task_success"
    PREDICTION_ACCURACY = "prediction_accuracy"
    PLANNING_QUALITY = "planning_quality"


@dataclass
class Metric:
    """A single metric measurement."""
    
    name: str
    value: float
    unit: str
    metric_type: MetricType
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


class MetricsCollector:
    """Collect and aggregate metrics during experiments."""
    
    def __init__(self):
        self.metrics: List[Metric] = []
        logger.info("Initialized MetricsCollector")
    
    def record_metric(
        self,
        name: str,
        value: float,
        unit: str,
        metric_type: MetricType,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Record a single metric."""
        metric = Metric(
            name=name,
            value=value,
            unit=unit,
            metric_type=metric_type,
            metadata=metadata or {},
        )
        self.metrics.append(metric)
    
    @contextmanager
    def measure_latency(self, metric_name: str):
        """Context manager to measure operation latency."""
        start_time = time.time()
        try:
            yield
        finally:
            elapsed = time.time() - start_time
            self.record_metric(
                name=metric_name,
                value=elapsed,
                unit="seconds",
                metric_type=MetricType.LATENCY,
            )
    
    @contextmanager
    def measure_resource_usage(self, metric_prefix: str):
        """Context manager to measure resource usage (placeholder)."""
        # Resource monitoring disabled due to psutil dependency issues
        # In production, this would track CPU and memory usage
        try:
            yield
        finally:
            pass
    
    def get_metrics_by_type(self, metric_type: MetricType) -> List[Metric]:
        """Get all metrics of a specific type."""
        return [m for m in self.metrics if m.metric_type == metric_type]
    
    def get_metric_summary(self) -> Dict[str, Any]:
        """Get summary statistics of all collected metrics."""
        summary = {}
        
        for metric_type in MetricType:
            type_metrics = self.get_metrics_by_type(metric_type)
            if type_metrics:
                values = [m.value for m in type_metrics]
                summary[metric_type.value] = {
                    "count": len(values),
                    "mean": sum(values) / len(values) if values else 0,
                    "min": min(values) if values else 0,
                    "max": max(values) if values else 0,
                    "sum": sum(values),
                }
        
        return summary
    
    def calculate_improvement(
        self,
        baseline_metrics: List[Metric],
        treatment_metrics: List[Metric],
    ) -> Dict[str, float]:
        """Calculate percentage improvement between baseline and treatment."""
        if not baseline_metrics or not treatment_metrics:
            return {}
        
        baseline_values = [m.value for m in baseline_metrics]
        treatment_values = [m.value for m in treatment_metrics]
        
        baseline_mean = sum(baseline_values) / len(baseline_values)
        treatment_mean = sum(treatment_values) / len(treatment_values)
        
        # Calculate percentage improvement
        # For metrics where higher is better (success rate, accuracy)
        if baseline_metrics[0].metric_type in [
            MetricType.SUCCESS_RATE,
            MetricType.ACCURACY,
            MetricType.PREDICTION_ACCURACY,
            MetricType.PLANNING_QUALITY,
        ]:
            improvement = ((treatment_mean - baseline_mean) / baseline_mean) * 100
        else:
            # For metrics where lower is better (latency, error rate, cost)
            improvement = ((baseline_mean - treatment_mean) / baseline_mean) * 100
        
        return {
            "baseline_mean": baseline_mean,
            "treatment_mean": treatment_mean,
            "improvement_percent": improvement,
        }
    
    def reset(self) -> None:
        """Clear all collected metrics."""
        self.metrics.clear()
        logger.info("Reset MetricsCollector")
