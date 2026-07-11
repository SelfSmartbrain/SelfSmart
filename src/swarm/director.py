"""Director Agent for Swarm Orchestration (Phase 8).

Top-level agent that manages sub-orchestrators for large-scale goals.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class SwarmGoal(BaseModel):
    """High-level goal for the swarm to execute."""
    
    id: UUID = Field(default_factory=uuid4)
    description: str = Field(..., description="High-level goal description")
    priority: int = Field(default=5, ge=1, le=10)
    estimated_complexity: int = Field(default=5, ge=1, le=10)
    required_capabilities: List[str] = Field(default_factory=list)
    resource_requirements: Dict[str, Any] = Field(default_factory=dict)
    deadline: Optional[datetime] = None
    status: str = Field(default="pending") # pending, planning, executing, completed, failed
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SubOrchestratorAssignment(BaseModel):
    """Assignment of a sub-task to a sub-orchestrator."""
    
    sub_orchestrator_id: UUID
    task_description: str
    priority: int
    dependencies: List[UUID] = Field(default_factory=list)
    estimated_duration: Optional[int] = None
    status: str = Field(default="assigned")


class DirectorAgent:
    """Director agent that manages sub-orchestrators for large-scale goals."""
    
    def __init__(self, max_sub_orchestrators: int = 50):
        """Initialize director agent."""
        self.max_sub_orchestrators = max_sub_orchestrators
        self.active_goals: Dict[UUID, SwarmGoal] = {}
        self.sub_orchestrators: Dict[UUID, Any] = {}  # Will hold SubOrchestrator instances
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        
        logger.info(f"DirectorAgent initialized with max {max_sub_orchestrators} sub-orchestrators")
    
    async def initialize(self) -> None:
        """Initialize director agent and sub-orchestrators."""
        logger.info("Initializing DirectorAgent")
        self._running = True
        
        # Initialize sub-orchestrator pool
        for i in range(self.max_sub_orchestrators):
            from src.swarm.sub_orchestrator import SubOrchestrator
            sub_orch = SubOrchestrator(id=uuid4(), director_id=uuid4())
            await sub_orch.initialize()
            self.sub_orchestrators[sub_orch.id] = sub_orch
        
        logger.info(f"Initialized {len(self.sub_orchestrators)} sub-orchestrators")
    
    async def shutdown(self) -> None:
        """Shutdown director agent and all sub-orchestrators."""
        logger.info("Shutting down DirectorAgent")
        self._running = False
        
        # Shutdown all sub-orchestrators
        for sub_orch in self.sub_orchestrators.values():
            await sub_orch.shutdown()
        
        self.sub_orchestrators.clear()
        logger.info("DirectorAgent shutdown complete")
    
    async def submit_goal(self, goal: SwarmGoal) -> UUID:
        """Submit a high-level goal to the swarm."""
        logger.info(f"Submitting goal: {goal.description}")
        
        goal.status = "planning"
        self.active_goals[goal.id] = goal
        
        # Decompose goal into sub-tasks
        sub_tasks = await self._decompose_goal(goal)
        
        # Assign sub-tasks to sub-orchestrators
        assignments = await self._assign_sub_tasks(sub_tasks)
        
        goal.status = "executing"
        goal.metadata["assignments"] = [a.model_dump() for a in assignments]
        goal.metadata["sub_task_count"] = len(assignments)
        
        logger.info(f"Goal {goal.id} decomposed into {len(assignments)} sub-tasks")
        return goal.id
    
    async def _decompose_goal(self, goal: SwarmGoal) -> List[Dict[str, Any]]:
        """Decompose high-level goal into executable sub-tasks."""
        # This would use LLM to decompose the goal
        # For now, return placeholder sub-tasks
        
        sub_tasks = []
        
        # Simple decomposition based on complexity
        num_subtasks = min(goal.estimated_complexity * 2, self.max_sub_orchestrators)
        
        for i in range(num_subtasks):
            sub_task = {
                "id": uuid4(),
                "description": f"Sub-task {i+1} for: {goal.description}",
                "priority": goal.priority,
                "estimated_duration": 300,  # 5 minutes default
                "required_capabilities": goal.required_capabilities,
                "parent_goal_id": goal.id
            }
            sub_tasks.append(sub_task)
        
        logger.info(f"Decomposed goal into {len(sub_tasks)} sub-tasks")
        return sub_tasks
    
    async def _assign_sub_tasks(
        self,
        sub_tasks: List[Dict[str, Any]]
    ) -> List[SubOrchestratorAssignment]:
        """Assign sub-tasks to available sub-orchestrators."""
        assignments = []
        available_orchestrators = [
            sub_id for sub_id, sub_orch in self.sub_orchestrators.items()
            if sub_orch.status == "idle"
        ]
        
        for i, sub_task in enumerate(sub_tasks):
            if i >= len(available_orchestrators):
                logger.warning("Not enough available sub-orchestrators")
                break
            
            sub_orch_id = available_orchestrators[i]
            sub_orch = self.sub_orchestrators[sub_orch_id]
            
            assignment = SubOrchestratorAssignment(
                sub_orchestrator_id=sub_orch_id,
                task_description=sub_task["description"],
                priority=sub_task["priority"],
                estimated_duration=sub_task.get("estimated_duration")
            )
            
            # Assign task to sub-orchestrator
            await sub_orch.assign_task(assignment)
            
            assignments.append(assignment)
        
        return assignments
    
    async def get_goal_status(self, goal_id: UUID) -> Optional[Dict[str, Any]]:
        """Get status of a goal and its sub-tasks."""
        if goal_id not in self.active_goals:
            return None
        
        goal = self.active_goals[goal_id]
        
        # Get status of all sub-tasks
        sub_task_statuses = []
        for assignment in goal.metadata.get("assignments", []):
            sub_orch_id = assignment["sub_orchestrator_id"]
            sub_orch = self.sub_orchestrators.get(sub_orch_id)
            if sub_orch:
                sub_task_statuses.append({
                    "sub_orchestrator_id": str(sub_orch_id),
                    "status": sub_orch.status,
                    "progress": sub_orch.progress
                })
        
        return {
            "goal_id": str(goal_id),
            "description": goal.description,
            "status": goal.status,
            "sub_task_count": goal.metadata.get("sub_task_count", 0),
            "sub_task_statuses": sub_task_statuses
        }
    
    async def monitor_swarm(self) -> Dict[str, Any]:
        """Get overall swarm status and metrics."""
        total_orchestrators = len(self.sub_orchestrators)
        idle_orchestrators = sum(
            1 for sub_orch in self.sub_orchestrators.values()
            if sub_orch.status == "idle"
        )
        busy_orchestrators = total_orchestrators - idle_orchestrators
        
        active_goals_count = sum(
            1 for goal in self.active_goals.values()
            if goal.status in ["planning", "executing"]
        )
        
        return {
            "total_sub_orchestrators": total_orchestrators,
            "idle_sub_orchestrators": idle_orchestrators,
            "busy_sub_orchestrators": busy_orchestrators,
            "active_goals": active_goals_count,
            "total_goals": len(self.active_goals),
            "running": self._running
        }
    
    async def scale_swarm(self, target_size: int) -> bool:
        """Scale the swarm to target size."""
        if target_size > self.max_sub_orchestrators:
            logger.warning(f"Cannot scale beyond max {self.max_sub_orchestrators}")
            return False
        
        current_size = len(self.sub_orchestrators)
        
        if target_size > current_size:
            # Scale up
            for i in range(target_size - current_size):
                from src.swarm.sub_orchestrator import SubOrchestrator
                sub_orch = SubOrchestrator(id=uuid4(), director_id=uuid4())
                await sub_orch.initialize()
                self.sub_orchestrators[sub_orch.id] = sub_orch
            logger.info(f"Scaled up from {current_size} to {target_size}")
        elif target_size < current_size:
            # Scale down (remove idle orchestrators)
            idle_orchestrators = [
                sub_id for sub_id, sub_orch in self.sub_orchestrators.items()
                if sub_orch.status == "idle"
            ]
            
            to_remove = current_size - target_size
            for i in range(min(to_remove, len(idle_orchestrators))):
                sub_id = idle_orchestrators[i]
                await self.sub_orchestrators[sub_id].shutdown()
                del self.sub_orchestrators[sub_id]
            
            logger.info(f"Scaled down from {current_size} to {target_size}")
        
        return True
