"""Runtime metrics integration for Phase 17."""

from __future__ import annotations

from typing import Any

from src.monitoring.prometheus import (
    OBJECTIVE_COMPLETION_RATE,
    OBJECTIVE_FAILURE_RATE,
    RUNTIME_UTILIZATION,
    AVERAGE_CYCLE_TIME,
    ACTIVE_OBJECTIVES,
)


class RuntimeMetricsCollector:
    """Collects and updates runtime metrics for Prometheus."""

    def __init__(self) -> None:
        self._total_objectives = 0
        self._completed_objectives = 0
        self._failed_objectives = 0
        self._total_cycle_time = 0.0

    def update_from_scheduler_metrics(self, metrics: dict[str, Any]) -> None:
        """Update Prometheus metrics from scheduler metrics."""
        completion_rate = metrics.get("completion_rate", 0.0)
        failure_rate = metrics.get("failure_rate", 0.0)
        avg_cycle_time = metrics.get("average_cycle_time", 0.0)
        active_count = metrics.get("active_objectives", 0)
        queue_size = metrics.get("queue_size", 0)
        
        # Calculate utilization (active + queued / max capacity)
        # Assuming max capacity of 10 concurrent objectives
        max_capacity = 10
        utilization = min((active_count + queue_size) / max_capacity, 1.0)

        # Update Prometheus gauges
        OBJECTIVE_COMPLETION_RATE.set(completion_rate)
        OBJECTIVE_FAILURE_RATE.set(failure_rate)
        RUNTIME_UTILIZATION.set(utilization)
        AVERAGE_CYCLE_TIME.set(avg_cycle_time)
        ACTIVE_OBJECTIVES.set(active_count)

    def record_objective_completed(self, cycle_time: float) -> None:
        """Record a completed objective."""
        self._completed_objectives += 1
        self._total_objectives += 1
        self._total_cycle_time += cycle_time
        
        completion_rate = self._completed_objectives / self._total_objectives
        avg_cycle_time = self._total_cycle_time / self._completed_objectives
        
        OBJECTIVE_COMPLETION_RATE.set(completion_rate)
        AVERAGE_CYCLE_TIME.set(avg_cycle_time)

    def record_objective_failed(self) -> None:
        """Record a failed objective."""
        self._failed_objectives += 1
        self._total_objectives += 1
        
        failure_rate = self._failed_objectives / self._total_objectives
        OBJECTIVE_FAILURE_RATE.set(failure_rate)

    def update_active_objectives(self, count: int) -> None:
        """Update the count of active objectives."""
        ACTIVE_OBJECTIVES.set(count)

    def update_utilization(self, utilization: float) -> None:
        """Update runtime utilization (0.0 to 1.0)."""
        RUNTIME_UTILIZATION.set(utilization)

    def reset(self) -> None:
        """Reset all metrics."""
        self._total_objectives = 0
        self._completed_objectives = 0
        self._failed_objectives = 0
        self._total_cycle_time = 0.0
        
        OBJECTIVE_COMPLETION_RATE.set(0.0)
        OBJECTIVE_FAILURE_RATE.set(0.0)
        RUNTIME_UTILIZATION.set(0.0)
        AVERAGE_CYCLE_TIME.set(0.0)
        ACTIVE_OBJECTIVES.set(0)
