"""Task Distributor for Swarm Orchestration (Phase 8).

Distributes tasks across sub-orchestrators based on capabilities and load.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional
from uuid import UUID

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class Task(BaseModel):
    """Task to be distributed."""
    
    id: UUID
    description: str
    required_capabilities: List[str] = Field(default_factory=list)
    priority: int = Field(default=5, ge=1, le=10)
    estimated_duration: int = Field(default=300)  # seconds
    dependencies: List[UUID] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SubOrchestratorCapabilities(BaseModel):
    """Capabilities of a sub-orchestrator."""
    
    sub_orchestrator_id: UUID
    capabilities: List[str] = Field(default_factory=list)
    current_load: int = Field(default=0)
    max_capacity: int = Field(default=10)
    status: str = "idle"


class TaskDistributor:
    """Distributes tasks to sub-orchestrators based on capabilities and load."""
    
    def __init__(self):
        """Initialize task distributor."""
        self.sub_orchestrator_capabilities: Dict[UUID, SubOrchestratorCapabilities] = {}
        self.task_queue: List[Task] = []
        self.completed_tasks: List[Task] = []
        
        logger.info("TaskDistributor initialized")
    
    def register_sub_orchestrator(
        self,
        sub_orchestrator_id: UUID,
        capabilities: List[str],
        max_capacity: int = 10
    ) -> None:
        """Register a sub-orchestrator with its capabilities."""
        self.sub_orchestrator_capabilities[sub_orchestrator_id] = SubOrchestratorCapabilities(
            sub_orchestrator_id=sub_orchestrator_id,
            capabilities=capabilities,
            max_capacity=max_capacity
        )
        logger.info(f"Registered sub-orchestrator {sub_orchestrator_id} with capabilities: {capabilities}")
    
    def unregister_sub_orchestrator(self, sub_orchestrator_id: UUID) -> None:
        """Unregister a sub-orchestrator."""
        if sub_orchestrator_id in self.sub_orchestrator_capabilities:
            del self.sub_orchestrator_capabilities[sub_orchestrator_id]
            logger.info(f"Unregistered sub-orchestrator {sub_orchestrator_id}")
    
    def submit_task(self, task: Task) -> None:
        """Submit a task to the distribution queue."""
        self.task_queue.append(task)
        logger.info(f"Submitted task {task.id} to distribution queue")
    
    def distribute_task(self, task: Task) -> Optional[UUID]:
        """Distribute a task to the best matching sub-orchestrator."""
        # Find sub-orchestrators with matching capabilities
        matching_orchestrators = [
            sub_id for sub_id, caps in self.sub_orchestrator_capabilities.items()
            if all(
                cap in caps.capabilities
                for cap in task.required_capabilities
            ) and caps.current_load < caps.max_capacity
        ]
        
        if not matching_orchestrators:
            logger.warning(f"No matching sub-orchestrator for task {task.id}")
            return None
        
        # Select the one with lowest load
        best_orchestrator = min(
            matching_orchestrators,
            key=lambda sub_id: self.sub_orchestrator_capabilities[sub_id].current_load
        )
        
        # Update load
        self.sub_orchestrator_capabilities[best_orchestrator].current_load += 1
        
        logger.info(f"Distributed task {task.id} to sub-orchestrator {best_orchestrator}")
        return best_orchestrator
    
    def distribute_all_tasks(self) -> Dict[UUID, UUID]:
        """Distribute all pending tasks."""
        assignments = {}
        
        for task in self.task_queue[:]:  # Copy to avoid modification during iteration
            sub_orch_id = self.distribute_task(task)
            if sub_orch_id:
                assignments[task.id] = sub_orch_id
                self.task_queue.remove(task)
        
        logger.info(f"Distributed {len(assignments)} tasks")
        return assignments
    
    def mark_task_complete(self, task_id: UUID, sub_orchestrator_id: UUID) -> None:
        """Mark a task as complete and free up capacity."""
        if sub_orchestrator_id in self.sub_orchestrator_capabilities:
            caps = self.sub_orchestrator_capabilities[sub_orchestrator_id]
            caps.current_load = max(0, caps.current_load - 1)
        
        # Move task from queue to completed
        self.task_queue = [t for t in self.task_queue if t.id != task_id]
        logger.info(f"Marked task {task_id} complete, freed capacity on {sub_orchestrator_id}")
    
    def get_pending_tasks(self) -> List[Task]:
        """Get all pending tasks."""
        return self.task_queue.copy()
    
    def get_sub_orchestrator_status(self, sub_orchestrator_id: UUID) -> Optional[SubOrchestratorCapabilities]:
        """Get status of a specific sub-orchestrator."""
        return self.sub_orchestrator_capabilities.get(sub_orchestrator_id)
    
    def get_all_sub_orchestrator_status(self) -> List[SubOrchestratorCapabilities]:
        """Get status of all sub-orchestrators."""
        return list(self.sub_orchestrator_capabilities.values())
    
    def get_distribution_stats(self) -> Dict[str, Any]:
        """Get distribution statistics."""
        total_capacity = sum(
            caps.max_capacity for caps in self.sub_orchestrator_capabilities.values()
        )
        total_load = sum(
            caps.current_load for caps in self.sub_orchestrator_capabilities.values()
        )
        
        return {
            "total_sub_orchestrators": len(self.sub_orchestrator_capabilities),
            "total_capacity": total_capacity,
            "total_load": total_load,
            "utilization": total_load / total_capacity if total_capacity > 0 else 0.0,
            "pending_tasks": len(self.task_queue)
        }
