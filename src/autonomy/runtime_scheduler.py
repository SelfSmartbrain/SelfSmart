"""Runtime scheduler for autonomous objectives with priority-based execution."""

from __future__ import annotations

import asyncio
import heapq
import logging
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from src.autonomy.objective_manager import Objective, ObjectiveManager
from src.autonomy.checkpoint_manager import CheckpointManager, RuntimeRecovery

logger = logging.getLogger(__name__)


class ObjectivePriority(Enum):
    """Priority levels for autonomous objectives."""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


@dataclass(order=True)
class ScheduledObjective:
    """An objective scheduled for execution."""
    priority: ObjectivePriority
    timestamp: float = field(compare=False)
    objective: Objective = field(compare=False)
    execution_func: Callable = field(compare=False)
    timeout: float = field(default=300.0, compare=False)
    retries: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)


class RuntimeSchedule:
    """
    Manages scheduling and execution of autonomous objectives.
    
    Features:
    - Priority-based execution queue
    - Pause/resume/cancel objectives
    - Automatic retry on failure
    - Checkpoint integration for recovery
    """

    def __init__(
        self,
        objective_manager: ObjectiveManager,
        checkpoint_manager: CheckpointManager | None = None,
    ) -> None:
        self.objective_manager = objective_manager
        self.checkpoint_manager = checkpoint_manager
        self.runtime_recovery = RuntimeRecovery(checkpoint_manager) if checkpoint_manager else None
        
        self._priority_queue: list[ScheduledObjective] = []
        self._running = False
        self._lock = asyncio.Lock()
        self._active_objectives: dict[str, asyncio.Task] = {}
        self._paused_objectives: dict[str, ScheduledObjective] = {}
        
        # Metrics
        self._objectives_scheduled = 0
        self._objectives_completed = 0
        self._objectives_failed = 0
        self._objectives_cancelled = 0
        self._total_execution_time = 0.0

    async def schedule_objective(
        self,
        objective: Objective,
        execution_func: Callable,
        priority: ObjectivePriority = ObjectivePriority.MEDIUM,
        timeout: float = 300.0,
        max_retries: int = 3,
    ) -> None:
        """Schedule an objective for execution."""
        async with self._lock:
            scheduled = ScheduledObjective(
                priority=priority,
                timestamp=datetime.now().timestamp(),
                objective=objective,
                execution_func=execution_func,
                timeout=timeout,
                max_retries=max_retries,
            )
            heapq.heappush(self._priority_queue, scheduled)
            self._objectives_scheduled += 1
            logger.info(f"Scheduled objective {objective.objective_id} with priority {priority.name}")

    async def pause_objective(self, objective_id: str) -> bool:
        """Pause an active objective."""
        async with self._lock:
            # Check if it's in the queue
            for i, scheduled in enumerate(self._priority_queue):
                if scheduled.objective.objective_id == objective_id:
                    paused = self._priority_queue.pop(i)
                    heapq.heapify(self._priority_queue)
                    self._paused_objectives[objective_id] = paused
                    await self.objective_manager.pause_objective(objective_id)
                    logger.info(f"Paused objective {objective_id}")
                    return True
            
            # Check if it's currently executing
            if objective_id in self._active_objectives:
                task = self._active_objectives[objective_id]
                task.cancel()
                del self._active_objectives[objective_id]
                await self.objective_manager.pause_objective(objective_id)
                logger.info(f"Cancelled and paused objective {objective_id}")
                return True
            
            return False

    async def resume_objective(self, objective_id: str) -> bool:
        """Resume a paused objective."""
        async with self._lock:
            if objective_id in self._paused_objectives:
                scheduled = self._paused_objectives.pop(objective_id)
                heapq.heappush(self._priority_queue, scheduled)
                await self.objective_manager.resume_objective(objective_id)
                logger.info(f"Resumed objective {objective_id}")
                return True
            return False

    async def cancel_objective(self, objective_id: str) -> bool:
        """Cancel an objective."""
        async with self._lock:
            # Remove from queue
            for i, scheduled in enumerate(self._priority_queue):
                if scheduled.objective.objective_id == objective_id:
                    self._priority_queue.pop(i)
                    heapq.heapify(self._priority_queue)
                    await self.objective_manager.cancel_objective(objective_id)
                    self._objectives_cancelled += 1
                    logger.info(f"Cancelled objective {objective_id}")
                    return True
            
            # Cancel if active
            if objective_id in self._active_objectives:
                task = self._active_objectives[objective_id]
                task.cancel()
                del self._active_objectives[objective_id]
                await self.objective_manager.cancel_objective(objective_id)
                self._objectives_cancelled += 1
                logger.info(f"Cancelled active objective {objective_id}")
                return True
            
            # Remove from paused
            if objective_id in self._paused_objectives:
                del self._paused_objectives[objective_id]
                await self.objective_manager.cancel_objective(objective_id)
                self._objectives_cancelled += 1
                logger.info(f"Cancelled paused objective {objective_id}")
                return True
            
            return False

    async def get_next_objective(self) -> ScheduledObjective | None:
        """Get the next highest priority objective from the queue."""
        async with self._lock:
            if self._priority_queue:
                return heapq.heappop(self._priority_queue)
            return None

    async def execute_objective(self, scheduled: ScheduledObjective) -> None:
        """Execute a scheduled objective with timeout and retry logic."""
        objective_id = scheduled.objective.objective_id
        start_time = datetime.now()

        try:
            # Create checkpoint before execution if available
            if self.runtime_recovery and self.checkpoint_manager.session:
                state_snapshot = {
                    "objective_id": objective_id,
                    "priority": scheduled.objective.priority,
                    "status": scheduled.objective.status,
                }
                await self.runtime_recovery.auto_checkpoint_before_critical(
                    objective_id=scheduled.objective.db_id,
                    state_snapshot=state_snapshot,
                    session=self.checkpoint_manager.session,
                )

            # Execute with timeout
            task_coroutine = scheduled.execution_func(scheduled.objective)
            asyncio_task = asyncio.create_task(
                asyncio.wait_for(task_coroutine, timeout=scheduled.timeout)
            )

            self._active_objectives[objective_id] = asyncio_task
            await asyncio_task

            # Mark as completed
            await self.objective_manager.complete_objective(objective_id)
            self._objectives_completed += 1
            execution_time = (datetime.now() - start_time).total_seconds()
            self._total_execution_time += execution_time

            logger.info(f"Objective {objective_id} completed in {execution_time:.2f}s")

        except asyncio.TimeoutError:
            logger.warning(f"Objective {objective_id} timed out after {scheduled.timeout}s")
            
            # Retry if possible
            if scheduled.retries < scheduled.max_retries:
                scheduled.retries += 1
                heapq.heappush(self._priority_queue, scheduled)
                logger.info(f"Retrying objective {objective_id} (attempt {scheduled.retries}/{scheduled.max_retries})")
            else:
                await self.objective_manager.fail_objective(objective_id)
                self._objectives_failed += 1
                logger.error(f"Objective {objective_id} failed after {scheduled.max_retries} retries")

        except asyncio.CancelledError:
            logger.info(f"Objective {objective_id} was cancelled")

        except Exception as e:
            logger.error(f"Objective {objective_id} failed with error: {e}")
            await self.objective_manager.fail_objective(objective_id)
            self._objectives_failed += 1

        finally:
            if objective_id in self._active_objectives:
                del self._active_objectives[objective_id]

    async def run(self) -> None:
        """Main scheduler loop."""
        self._running = True
        logger.info("RuntimeScheduler started")

        while self._running:
            try:
                scheduled = await self.get_next_objective()

                if scheduled:
                    await self.execute_objective(scheduled)
                else:
                    await asyncio.sleep(0.1)

            except asyncio.CancelledError:
                logger.info("Scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(0.1)

    def stop(self) -> None:
        """Stop the scheduler."""
        self._running = False

    def get_metrics(self) -> dict[str, Any]:
        """Get scheduler metrics."""
        avg_cycle_time = (
            self._total_execution_time / self._objectives_completed
            if self._objectives_completed > 0
            else 0.0
        )
        
        return {
            "objectives_scheduled": self._objectives_scheduled,
            "objectives_completed": self._objectives_completed,
            "objectives_failed": self._objectives_failed,
            "objectives_cancelled": self._objectives_cancelled,
            "queue_size": len(self._priority_queue),
            "active_objectives": len(self._active_objectives),
            "paused_objectives": len(self._paused_objectives),
            "average_cycle_time": avg_cycle_time,
            "completion_rate": (
                self._objectives_completed / self._objectives_scheduled
                if self._objectives_scheduled > 0
                else 0.0
            ),
            "failure_rate": (
                self._objectives_failed / self._objectives_scheduled
                if self._objectives_scheduled > 0
                else 0.0
            ),
        }
