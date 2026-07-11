"""
Performance metrics for latency, throughput, and cost.
"""

from typing import List, Optional
import time
from contextlib import contextmanager
from .metric_types import Metric, MetricType


class PerformanceMetrics:
    """Compute performance metrics."""
    
    @staticmethod
    def compute_latency_stats(latencies: List[float]) -> dict:
        """Compute latency statistics."""
        if not latencies:
            return {
                "mean": 0.0,
                "median": 0.0,
                "std": 0.0,
                "min": 0.0,
                "max": 0.0,
                "p50": 0.0,
                "p95": 0.0,
                "p99": 0.0,
            }
        
        import numpy as np
        
        sorted_latencies = sorted(latencies)
        
        return {
            "mean": np.mean(latencies),
            "median": np.median(latencies),
            "std": np.std(latencies),
            "min": np.min(latencies),
            "max": np.max(latencies),
            "p50": np.percentile(latencies, 50),
            "p95": np.percentile(latencies, 95),
            "p99": np.percentile(latencies, 99),
        }
    
    @staticmethod
    def compute_throughput(
        num_operations: int,
        duration_seconds: float,
    ) -> float:
        """Compute throughput (operations per second)."""
        if duration_seconds <= 0:
            return 0.0
        return num_operations / duration_seconds
    
    @staticmethod
    def compute_cost_per_operation(
        total_cost_usd: float,
        num_operations: int,
    ) -> float:
        """Compute cost per operation."""
        if num_operations <= 0:
            return 0.0
        return total_cost_usd / num_operations
    
    @staticmethod
    def compute_token_efficiency(
        total_tokens: int,
        num_operations: int,
    ) -> float:
        """Compute average tokens per operation."""
        if num_operations <= 0:
            return 0.0
        return total_tokens / num_operations


class LatencyTimer:
    """Context manager for timing operations."""
    
    def __init__(self, metric_name: str = "latency"):
        self.metric_name = metric_name
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.duration: Optional[float] = None
    
    def __enter__(self):
        self.start_time = time.time()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.end_time = time.time()
        self.duration = self.end_time - self.start_time
    
    def get_duration(self) -> float:
        """Get the measured duration."""
        if self.duration is None:
            raise RuntimeError("Timer has not been used in a context manager")
        return self.duration
