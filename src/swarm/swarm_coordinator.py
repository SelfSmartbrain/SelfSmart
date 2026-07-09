"""Swarm Coordinator for Swarm Orchestration (Phase 8).

Central coordinator for managing the entire swarm of agents.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.swarm.director import DirectorAgent, SwarmGoal

logger = get_logger(__name__)


class SwarmMetrics(BaseModel):
    """Metrics for the entire swarm."""
    
    total_directors: int
    total_sub_orchestrators: int
    active_goals: int
    completed_goals: int
    failed_goals: int
    average_task_duration: float
    total_tasks_completed: int
    swarm_utilization: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SwarmCoordinator:
    """Central coordinator for managing multiple director agents."""
    
    def __init__(self, num_directors: int = 5, sub_orchestrators_per_director: int = 10):
        """Initialize swarm coordinator."""
        self.num_directors = num_directors
        self.sub_orchestrators_per_director = sub_orchestrators_per_director
        
        self.directors: Dict[UUID, DirectorAgent] = {}
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        
        logger.info(
            f"SwarmCoordinator initialized with {num_directors} directors, "
            f"{sub_orchestrators_per_director} sub-orchestrators per director"
        )
    
    async def initialize(self) -> None:
        """Initialize swarm coordinator and all directors."""
        logger.info("Initializing SwarmCoordinator")
        self._running = True
        
        # Initialize director agents
        for i in range(self.num_directors):
            director = DirectorAgent(
                max_sub_orchestrators=self.sub_orchestrators_per_director
            )
            await director.initialize()
            self.directors[uuid4()] = director
        
        # Start monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_loop())
        
        logger.info(f"SwarmCoordinator initialized with {len(self.directors)} directors")
    
    async def shutdown(self) -> None:
        """Shutdown swarm coordinator and all directors."""
        logger.info("Shutting down SwarmCoordinator")
        self._running = False
        
        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass
        
        # Shutdown all directors
        for director in self.directors.values():
            await director.shutdown()
        
        self.directors.clear()
        logger.info("SwarmCoordinator shutdown complete")
    
    async def submit_goal(self, goal: SwarmGoal) -> UUID:
        """Submit a goal to the swarm (assigns to least loaded director)."""
        logger.info(f"Submitting goal to swarm: {goal.description}")

        # Also register with the global runtime's ObjectiveManager
        try:
            from src.runtime.runtime_singleton import get_runtime
            runtime = get_runtime()
            runtime.objective_manager.set_objective(
                goal.description,
                priority=goal.priority,
                metadata={"swarm_goal": True, "goal_id": str(goal.goal_id)},
            )
        except RuntimeError:
            pass  # Runtime not initialized yet (startup)

        # Find director with least load
        director = await self._get_least_loaded_director()

        if not director:
            raise RuntimeError("No available directors")

        goal_id = await director.submit_goal(goal)
        logger.info(f"Goal {goal_id} assigned to director")

        return goal_id
    
    async def _get_least_loaded_director(self) -> Optional[DirectorAgent]:
        """Get the director with the least current load."""
        if not self.directors:
            return None
        
        min_load = float('inf')
        least_loaded = None
        
        for director in self.directors.values():
            status = await director.monitor_swarm()
            load = status.get("busy_sub_orchestrators", 0)
            
            if load < min_load:
                min_load = load
                least_loaded = director
        
        return least_loaded
    
    async def get_goal_status(self, goal_id: UUID) -> Optional[Dict[str, Any]]:
        """Get status of a goal from its director."""
        for director in self.directors.values():
            status = await director.get_goal_status(goal_id)
            if status:
                return status
        
        return None
    
    async def get_swarm_metrics(self) -> SwarmMetrics:
        """Get comprehensive metrics for the entire swarm."""
        total_sub_orchestrators = 0
        active_goals = 0
        completed_goals = 0
        failed_goals = 0
        total_tasks_completed = 0
        
        for director in self.directors.values():
            status = await director.monitor_swarm()
            total_sub_orchestrators += status.get("total_sub_orchestrators", 0)
            active_goals += status.get("active_goals", 0)
            
            # Count completed/failed goals from director's active_goals
            for goal in director.active_goals.values():
                if goal.status == "completed":
                    completed_goals += 1
                elif goal.status == "failed":
                    failed_goals += 1
        
        busy_orchestrators = sum(
            status.get("busy_sub_orchestrators", 0)
            for director in self.directors.values()
            if hasattr(director, 'monitor_swarm')
        )
        
        swarm_utilization = (
            busy_orchestrators / total_sub_orchestrators
            if total_sub_orchestrators > 0 else 0.0
        )
        
        return SwarmMetrics(
            total_directors=len(self.directors),
            total_sub_orchestrators=total_sub_orchestrators,
            active_goals=active_goals,
            completed_goals=completed_goals,
            failed_goals=failed_goals,
            average_task_duration=0.0,  # Would be calculated from task history
            total_tasks_completed=total_tasks_completed,
            swarm_utilization=swarm_utilization
        )
    
    async def _monitor_loop(self) -> None:
        """Background monitoring loop for swarm health."""
        logger.info("SwarmCoordinator monitor loop started")
        
        while self._running:
            try:
                # Collect metrics
                metrics = await self.get_swarm_metrics()
                logger.info(
                    f"Swarm metrics: {metrics.total_sub_orchestrators} sub-orchestrators, "
                    f"{metrics.active_goals} active goals, "
                    f"{metrics.swarm_utilization:.2%} utilization"
                )
                
                # Auto-scale if needed
                await self._auto_scale(metrics)
                
                # Sleep for monitoring interval
                await asyncio.sleep(30)
                
            except asyncio.CancelledError:
                logger.info("SwarmCoordinator monitor loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in swarm monitor loop: {e}")
                await asyncio.sleep(30)
        
        logger.info("SwarmCoordinator monitor loop ended")
    
    async def _auto_scale(self, metrics: SwarmMetrics) -> None:
        """Auto-scale the swarm based on utilization."""
        # Scale up if utilization > 80%
        if metrics.swarm_utilization > 0.8:
            logger.info("High utilization detected, considering scale-up")
            # Would implement scale-up logic here
        
        # Scale down if utilization < 20%
        elif metrics.swarm_utilization < 0.2:
            logger.info("Low utilization detected, considering scale-down")
            # Would implement scale-down logic here
    
    async def scale_directors(self, target_count: int) -> bool:
        """Scale the number of directors."""
        current_count = len(self.directors)
        
        if target_count > current_count:
            # Scale up
            for i in range(target_count - current_count):
                director = DirectorAgent(
                    max_sub_orchestrators=self.sub_orchestrators_per_director
                )
                await director.initialize()
                self.directors[uuid4()] = director
            logger.info(f"Scaled directors from {current_count} to {target_count}")
        elif target_count < current_count:
            # Scale down (remove idle directors)
            idle_directors = [
                director_id for director_id, director in self.directors.items()
                if all(
                    goal.status not in ["planning", "executing"]
                    for goal in director.active_goals.values()
                )
            ]
            
            to_remove = current_count - target_count
            for i in range(min(to_remove, len(idle_directors))):
                director_id = idle_directors[i]
                await self.directors[director_id].shutdown()
                del self.directors[director_id]
            
            logger.info(f"Scaled directors from {current_count} to {target_count}")
        
        return True
    
    async def get_director_status(self) -> List[Dict[str, Any]]:
        """Get status of all directors."""
        statuses = []
        for director_id, director in self.directors.items():
            status = await director.monitor_swarm()
            statuses.append({
                "director_id": str(director_id),
                **status
            })
        return statuses
