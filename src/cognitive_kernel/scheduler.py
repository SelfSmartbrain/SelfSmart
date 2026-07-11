"""
Cognitive Scheduler - Manages cognitive resource scheduling

The CognitiveScheduler is responsible for:
- Scheduling cognitive tasks
- Prioritizing based on attention and importance
- Managing resource allocation
- Balancing between different cognitive operations
"""

import asyncio
import heapq
import logging
from datetime import datetime, timedelta
from typing import Any, Callable, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class TaskPriority(Enum):
    """Priority levels for cognitive tasks"""
    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


@dataclass(order=True)
class ScheduledTask:
    """A task scheduled for cognitive processing"""
    priority: TaskPriority
    timestamp: float = field(compare=False)
    task_id: str = field(compare=False)
    task_func: Callable = field(compare=False)
    task_args: tuple = field(default_factory=tuple, compare=False)
    task_kwargs: dict = field(default_factory=dict, compare=False)
    timeout: float = field(default=30.0, compare=False)
    retries: int = field(default=0, compare=False)
    max_retries: int = field(default=3, compare=False)


class CognitiveScheduler:
    """
    Scheduler for cognitive operations.
    
    Manages the execution of cognitive tasks with priority-based scheduling,
    timeout handling, and retry logic.
    """
    
    def __init__(self, kernel: Any):
        self.kernel = kernel
        self._task_queue: List[ScheduledTask] = []
        self._running = False
        self._lock = asyncio.Lock()
        self._active_tasks: Dict[str, asyncio.Task] = {}
        
        # Scheduler metrics
        self._tasks_scheduled = 0
        self._tasks_completed = 0
        self._tasks_failed = 0
        self._tasks_timeout = 0
    
    async def initialize(self) -> None:
        """Initialize the scheduler"""
        logger.info("CognitiveScheduler initialized")
    
    async def shutdown(self) -> None:
        """Shutdown the scheduler"""
        self._running = False
        
        # Cancel all active tasks
        for task_id, task in self._active_tasks.items():
            task.cancel()
            logger.info(f"Cancelled task {task_id}")
        
        logger.info("CognitiveScheduler shutdown complete")
    
    async def run(self) -> None:
        """Main scheduler loop"""
        self._running = True
        logger.info("CognitiveScheduler started")
        
        while self._running:
            try:
                # Get next task from queue
                task = await self._get_next_task()
                
                if task:
                    # Execute the task
                    await self._execute_task(task)
                else:
                    # No tasks, sleep briefly
                    await asyncio.sleep(0.1)
                    
            except asyncio.CancelledError:
                logger.info("Scheduler cancelled")
                break
            except Exception as e:
                logger.error(f"Scheduler error: {e}")
                await asyncio.sleep(0.1)
    
    async def schedule(
        self,
        task_id: str,
        task_func: Callable,
        priority: TaskPriority = TaskPriority.MEDIUM,
        timeout: float = 30.0,
        max_retries: int = 3,
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """
        Schedule a cognitive task for execution.
        
        Args:
            task_id: Unique identifier for the task
            task_func: The async function to execute
            priority: Task priority level
            timeout: Maximum execution time in seconds
            max_retries: Maximum number of retry attempts
            *args: Positional arguments for the task function
            **kwargs: Keyword arguments for the task function
        """
        async with self._lock:
            task = ScheduledTask(
                priority=priority,
                timestamp=datetime.now().timestamp(),
                task_id=task_id,
                task_func=task_func,
                task_args=args,
                task_kwargs=kwargs,
                timeout=timeout,
                max_retries=max_retries,
            )
            
            heapq.heappush(self._task_queue, task)
            self._tasks_scheduled += 1
            
            logger.debug(f"Scheduled task {task_id} with priority {priority.name}")
    
    async def _get_next_task(self) -> Optional[ScheduledTask]:
        """Get the next highest priority task from the queue"""
        async with self._lock:
            if self._task_queue:
                return heapq.heappop(self._task_queue)
            return None
    
    async def _execute_task(self, task: ScheduledTask) -> None:
        """Execute a scheduled task with timeout and retry logic"""
        task_id = task.task_id
        
        try:
            # Create the task with timeout
            task_coroutine = task.task_func(*task.task_args, **task.task_kwargs)
            asyncio_task = asyncio.create_task(
                asyncio.wait_for(task_coroutine, timeout=task.timeout)
            )
            
            self._active_tasks[task_id] = asyncio_task
            
            # Wait for completion
            await asyncio_task
            
            # Task completed successfully
            self._tasks_completed += 1
            del self._active_tasks[task_id]
            
            logger.debug(f"Task {task_id} completed successfully")
            
        except asyncio.TimeoutError:
            self._tasks_timeout += 1
            logger.warning(f"Task {task_id} timed out after {task.timeout}s")
            
            # Retry if possible
            if task.retries < task.max_retries:
                task.retries += 1
                await self.schedule(
                    task_id,
                    task.task_func,
                    task.priority,
                    task.timeout,
                    task.max_retries - task.retries,
                    *task.task_args,
                    **task.task_kwargs,
                )
            else:
                self._tasks_failed += 1
                logger.error(f"Task {task_id} failed after {task.max_retries} retries")
                
        except Exception as e:
            self._tasks_failed += 1
            logger.error(f"Task {task_id} failed with error: {e}")
            
        finally:
            if task_id in self._active_tasks:
                del self._active_tasks[task_id]
    
    def get_queue_size(self) -> int:
        """Get the current size of the task queue"""
        return len(self._task_queue)
    
    def get_active_task_count(self) -> int:
        """Get the number of currently active tasks"""
        return len(self._active_tasks)
    
    def get_metrics(self) -> Dict[str, int]:
        """Get scheduler metrics"""
        return {
            "tasks_scheduled": self._tasks_scheduled,
            "tasks_completed": self._tasks_completed,
            "tasks_failed": self._tasks_failed,
            "tasks_timeout": self._tasks_timeout,
            "queue_size": self.get_queue_size(),
            "active_tasks": self.get_active_task_count(),
        }
