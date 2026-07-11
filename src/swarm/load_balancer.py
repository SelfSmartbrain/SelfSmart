"""Load Balancer for Swarm Orchestration (Phase 8).

Balances load across sub-orchestrators and directors.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID
from collections import deque
import time

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class LoadMetrics(BaseModel):
    """Load metrics for a sub-orchestrator."""
    
    sub_orchestrator_id: UUID
    current_tasks: int = Field(default=0)
    cpu_usage: float = Field(default=0.0, ge=0.0, le=100.0)
    memory_usage: float = Field(default=0.0, ge=0.0, le=100.0)
    avg_task_duration: float = Field(default=0.0)
    success_rate: float = Field(default=1.0, ge=0.0, le=1.0)
    last_updated: float = Field(default_factory=time.time)


class LoadBalancer:
    """Load balancer for distributing work across sub-orchestrators."""
    
    def __init__(self, strategy: str = "least_loaded"):
        """Initialize load balancer.
        
        Args:
            strategy: Load balancing strategy (least_loaded, round_robin, weighted)
        """
        self.strategy = strategy
        self.load_metrics: Dict[UUID, LoadMetrics] = {}
        self.round_robin_index = 0
        self.task_history: deque = deque(maxlen=1000)
        
        logger.info(f"LoadBalancer initialized with strategy: {strategy}")
    
    def register_sub_orchestrator(self, sub_orchestrator_id: UUID) -> None:
        """Register a sub-orchestrator for load balancing."""
        self.load_metrics[sub_orchestrator_id] = LoadMetrics(
            sub_orchestrator_id=sub_orchestrator_id
        )
        logger.info(f"Registered sub-orchestrator {sub_orchestrator_id} for load balancing")
    
    def unregister_sub_orchestrator(self, sub_orchestrator_id: UUID) -> None:
        """Unregister a sub-orchestrator."""
        if sub_orchestrator_id in self.load_metrics:
            del self.load_metrics[sub_orchestrator_id]
            logger.info(f"Unregistered sub-orchestrator {sub_orchestrator_id}")
    
    def update_metrics(self, metrics: LoadMetrics) -> None:
        """Update load metrics for a sub-orchestrator."""
        self.load_metrics[metrics.sub_orchestrator_id] = metrics
        logger.debug(f"Updated metrics for {metrics.sub_orchestrator_id}")
    
    def select_sub_orchestrator(
        self,
        exclude: Optional[List[UUID]] = None
    ) -> Optional[UUID]:
        """Select the best sub-orchestrator based on load balancing strategy."""
        if not self.load_metrics:
            return None
        
        exclude = exclude or []
        available_orchestrators = [
            sub_id for sub_id in self.load_metrics.keys()
            if sub_id not in exclude
        ]
        
        if not available_orchestrators:
            return None
        
        if self.strategy == "least_loaded":
            return self._select_least_loaded(available_orchestrators)
        elif self.strategy == "round_robin":
            return self._select_round_robin(available_orchestrators)
        elif self.strategy == "weighted":
            return self._select_weighted(available_orchestrators)
        else:
            logger.warning(f"Unknown strategy: {self.strategy}, using least_loaded")
            return self._select_least_loaded(available_orchestrators)
    
    def _select_least_loaded(self, available: List[UUID]) -> UUID:
        """Select sub-orchestrator with least current tasks."""
        return min(
            available,
            key=lambda sub_id: self.load_metrics[sub_id].current_tasks
        )
    
    def _select_round_robin(self, available: List[UUID]) -> UUID:
        """Select sub-orchestrator using round-robin."""
        selected = available[self.round_robin_index % len(available)]
        self.round_robin_index += 1
        return selected
    
    def _select_weighted(self, available: List[UUID]) -> UUID:
        """Select sub-orchestrator using weighted selection based on success rate."""
        # Calculate weights based on success rate and current load
        weights = []
        for sub_id in available:
            metrics = self.load_metrics[sub_id]
            # Higher success rate and lower load = higher weight
            weight = metrics.success_rate / (metrics.current_tasks + 1)
            weights.append(weight)
        
        # Normalize weights
        total_weight = sum(weights)
        if total_weight == 0:
            return available[0]
        
        import random
        r = random.uniform(0, total_weight)
        cumulative = 0
        
        for i, weight in enumerate(weights):
            cumulative += weight
            if r <= cumulative:
                return available[i]
        
        return available[-1]
    
    def record_task_completion(
        self,
        sub_orchestrator_id: UUID,
        duration: float,
        success: bool
    ) -> None:
        """Record task completion for metrics."""
        if sub_orchestrator_id not in self.load_metrics:
            return
        
        metrics = self.load_metrics[sub_orchestrator_id]
        
        # Update task count
        metrics.current_tasks = max(0, metrics.current_tasks - 1)
        
        # Update average task duration
        if metrics.avg_task_duration == 0:
            metrics.avg_task_duration = duration
        else:
            metrics.avg_task_duration = (
                metrics.avg_task_duration * 0.9 + duration * 0.1
            )
        
        # Update success rate
        if metrics.success_rate == 0:
            metrics.success_rate = 1.0 if success else 0.0
        else:
            metrics.success_rate = (
                metrics.success_rate * 0.95 + (1.0 if success else 0.0) * 0.05
            )
        
        metrics.last_updated = time.time()
        
        # Record in history
        self.task_history.append({
            "sub_orchestrator_id": sub_orchestrator_id,
            "duration": duration,
            "success": success,
            "timestamp": time.time()
        })
        
        logger.debug(f"Recorded task completion for {sub_orchestrator_id}")
    
    def get_overall_load(self) -> Dict[str, Any]:
        """Get overall load statistics."""
        if not self.load_metrics:
            return {
                "total_sub_orchestrators": 0,
                "total_tasks": 0,
                "avg_cpu_usage": 0.0,
                "avg_memory_usage": 0.0,
                "avg_success_rate": 0.0
            }
        
        total_tasks = sum(m.current_tasks for m in self.load_metrics.values())
        avg_cpu = sum(m.cpu_usage for m in self.load_metrics.values()) / len(self.load_metrics)
        avg_memory = sum(m.memory_usage for m in self.load_metrics.values()) / len(self.load_metrics)
        avg_success = sum(m.success_rate for m in self.load_metrics.values()) / len(self.load_metrics)
        
        return {
            "total_sub_orchestrators": len(self.load_metrics),
            "total_tasks": total_tasks,
            "avg_cpu_usage": avg_cpu,
            "avg_memory_usage": avg_memory,
            "avg_success_rate": avg_success
        }
    
    def get_overloaded_sub_orchestrators(self, threshold: float = 0.8) -> List[UUID]:
        """Get sub-orchestrators that are overloaded."""
        overloaded = []
        for sub_id, metrics in self.load_metrics.items():
            if metrics.current_tasks >= threshold * 10:  # Assuming max 10 tasks
                overloaded.append(sub_id)
        return overloaded
    
    def get_idle_sub_orchestrators(self, idle_threshold: int = 0) -> List[UUID]:
        """Get sub-orchestrators that are idle."""
        idle = [
            sub_id for sub_id, metrics in self.load_metrics.items()
            if metrics.current_tasks <= idle_threshold
        ]
        return idle
