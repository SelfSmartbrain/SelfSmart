"""objective_engine.py

Defines and manages objectives for the system.
Objectives define what the system should achieve and optimize for.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class ObjectiveStatus(str, Enum):
    """Status of an objective."""
    ACTIVE = "active"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ObjectivePriority(str, Enum):
    """Priority levels for objectives."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Objective:
    """An objective that the system should achieve."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    status: ObjectiveStatus = ObjectiveStatus.ACTIVE
    priority: ObjectivePriority = ObjectivePriority.MEDIUM
    target_value: float = 1.0
    current_value: float = 0.0
    progress: float = 0.0  # 0.0 to 1.0
    deadline: Optional[datetime] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def update_progress(self, new_value: float) -> None:
        """Update progress toward the objective."""
        self.current_value = new_value
        self.progress = min(1.0, new_value / self.target_value if self.target_value > 0 else 0.0)
        self.updated_at = datetime.now(timezone.utc)
        
        if self.progress >= 1.0:
            self.status = ObjectiveStatus.COMPLETED
    
    def is_overdue(self) -> bool:
        """Check if the objective is overdue."""
        if self.deadline is None:
            return False
        return datetime.now(timezone.utc) > self.deadline and self.status != ObjectiveStatus.COMPLETED
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "status": self.status.value,
            "priority": self.priority.value,
            "target_value": self.target_value,
            "current_value": self.current_value,
            "progress": self.progress,
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }


class ObjectiveEngine:
    """Manages objectives for the system."""
    
    def __init__(self):
        self.objectives: Dict[str, Objective] = {}
        self.objective_hierarchy: Dict[str, List[str]] = {}  # parent_id -> child_ids
        logger.info("ObjectiveEngine initialized")
    
    def create_objective(
        self,
        name: str,
        description: str,
        priority: ObjectivePriority = ObjectivePriority.MEDIUM,
        target_value: float = 1.0,
        deadline: Optional[datetime] = None,
        parent_id: Optional[str] = None,
    ) -> Objective:
        """Create a new objective."""
        objective = Objective(
            name=name,
            description=description,
            priority=priority,
            target_value=target_value,
            deadline=deadline,
        )
        
        self.objectives[objective.id] = objective
        
        if parent_id and parent_id in self.objectives:
            if parent_id not in self.objective_hierarchy:
                self.objective_hierarchy[parent_id] = []
            self.objective_hierarchy[parent_id].append(objective.id)
        
        logger.info(f"Created objective: {name}")
        return objective
    
    def get_objective(self, objective_id: str) -> Optional[Objective]:
        """Get an objective by ID."""
        return self.objectives.get(objective_id)
    
    def update_objective(
        self,
        objective_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Objective]:
        """Update an objective."""
        objective = self.get_objective(objective_id)
        if objective is None:
            return None
        
        for key, value in updates.items():
            if hasattr(objective, key):
                setattr(objective, key, value)
        
        objective.updated_at = datetime.now(timezone.utc)
        logger.info(f"Updated objective: {objective_id}")
        return objective
    
    def update_progress(self, objective_id: str, progress: float) -> None:
        """Update progress for an objective."""
        objective = self.get_objective(objective_id)
        if objective is None:
            return
        
        objective.update_progress(progress)
        
        # If this is a parent objective, update based on children
        if objective_id in self.objective_hierarchy:
            child_progress = self._aggregate_child_progress(objective_id)
            objective.update_progress(child_progress)
    
    def _aggregate_child_progress(self, parent_id: str) -> float:
        """Aggregate progress from child objectives."""
        child_ids = self.objective_hierarchy.get(parent_id, [])
        if not child_ids:
            return 0.0
        
        total_progress = 0.0
        for child_id in child_ids:
            child = self.get_objective(child_id)
            if child:
                total_progress += child.progress
        
        return total_progress / len(child_ids)
    
    def complete_objective(self, objective_id: str) -> None:
        """Mark an objective as completed."""
        objective = self.get_objective(objective_id)
        if objective:
            objective.status = ObjectiveStatus.COMPLETED
            objective.progress = 1.0
            objective.current_value = objective.target_value
            objective.updated_at = datetime.now(timezone.utc)
            logger.info(f"Completed objective: {objective_id}")
    
    def fail_objective(self, objective_id: str) -> None:
        """Mark an objective as failed."""
        objective = self.get_objective(objective_id)
        if objective:
            objective.status = ObjectiveStatus.FAILED
            objective.updated_at = datetime.now(timezone.utc)
            logger.info(f"Failed objective: {objective_id}")
    
    def delete_objective(self, objective_id: str) -> bool:
        """Delete an objective."""
        if objective_id in self.objectives:
            del self.objectives[objective_id]
            # Remove from hierarchy
            for parent_id in list(self.objective_hierarchy.keys()):
                if objective_id in self.objective_hierarchy[parent_id]:
                    self.objective_hierarchy[parent_id].remove(objective_id)
            logger.info(f"Deleted objective: {objective_id}")
            return True
        return False
    
    def list_objectives(
        self,
        status: Optional[ObjectiveStatus] = None,
        priority: Optional[ObjectivePriority] = None,
    ) -> List[Objective]:
        """List objectives, optionally filtered by status or priority."""
        objectives = list(self.objectives.values())
        
        if status:
            objectives = [o for o in objectives if o.status == status]
        
        if priority:
            objectives = [o for o in objectives if o.priority == priority]
        
        return objectives
    
    def get_active_objectives(self) -> List[Objective]:
        """Get all active objectives."""
        return self.list_objectives(status=ObjectiveStatus.ACTIVE)
    
    def get_overdue_objectives(self) -> List[Objective]:
        """Get all overdue objectives."""
        return [o for o in self.objectives.values() if o.is_overdue()]
    
    def get_objective_hierarchy(self, objective_id: str) -> Dict[str, Any]:
        """Get the hierarchy of an objective (parents and children)."""
        # Find parent
        parent_id = None
        for pid, children in self.objective_hierarchy.items():
            if objective_id in children:
                parent_id = pid
                break
        
        # Get children
        children = self.objective_hierarchy.get(objective_id, [])
        
        return {
            "objective_id": objective_id,
            "parent_id": parent_id,
            "child_ids": children,
        }
    
    def prioritize_objectives(self) -> List[Objective]:
        """Get objectives sorted by priority and deadline."""
        active = self.get_active_objectives()
        
        priority_order = {
            ObjectivePriority.CRITICAL: 0,
            ObjectivePriority.HIGH: 1,
            ObjectivePriority.MEDIUM: 2,
            ObjectivePriority.LOW: 3,
        }
        
        return sorted(
            active,
            key=lambda o: (
                priority_order.get(o.priority, 99),
                o.deadline if o.deadline else datetime.max,
            ),
        )
    
    def get_objective_statistics(self) -> Dict[str, Any]:
        """Get statistics about objectives."""
        objectives = list(self.objectives.values())
        
        if not objectives:
            return {"total_objectives": 0}
        
        return {
            "total_objectives": len(objectives),
            "by_status": {
                status.value: sum(1 for o in objectives if o.status == status)
                for status in ObjectiveStatus
            },
            "by_priority": {
                priority.value: sum(1 for o in objectives if o.priority == priority)
                for priority in ObjectivePriority
            },
            "average_progress": sum(o.progress for o in objectives) / len(objectives),
            "overdue_count": len(self.get_overdue_objectives()),
        }
