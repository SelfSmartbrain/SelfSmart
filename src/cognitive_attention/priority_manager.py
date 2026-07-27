"""
Priority Manager - Manages task and information priority

The PriorityManager is responsible for:
- Prioritizing tasks and information
- Managing priority queues
- Adjusting priorities based on context
- Implementing priority escalation and decay
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import heapq

logger = logging.getLogger(__name__)


class PriorityLevel(Enum):
    """Priority levels"""

    CRITICAL = 0
    HIGH = 1
    MEDIUM = 2
    LOW = 3
    BACKGROUND = 4


@dataclass(order=True)
class PriorityTask:
    """A task with priority"""

    priority: PriorityLevel
    created_at: float
    task_id: str = field(compare=False)
    task_data: Dict[str, Any] = field(compare=False, default_factory=dict)
    deadline: Optional[float] = field(compare=False, default=None)
    estimated_duration: float = field(compare=False, default=10.0)
    dependencies: List[str] = field(compare=False, default_factory=list)

    @property
    def is_overdue(self) -> bool:
        """Check if task is overdue"""
        if self.deadline is None:
            return False
        return datetime.now().timestamp() > self.deadline

    @property
    def urgency(self) -> float:
        """Calculate urgency based on deadline"""
        if self.deadline is None:
            return 0.0

        time_remaining = self.deadline - datetime.now().timestamp()
        if time_remaining <= 0:
            return 1.0

        # Urgency increases as deadline approaches
        urgency = 1.0 - min(1.0, time_remaining / 3600.0)  # 1 hour window
        return urgency


class PriorityManager:
    """
    Manages task and information priority.

    Features:
    - Priority queues for different task types
    - Dynamic priority adjustment
    - Deadline-based escalation
    - Priority decay over time
    - Dependency management
    """

    def __init__(
        self,
        max_queue_size: int = 1000,
        priority_decay_rate: float = 0.95,
        escalation_threshold: float = 0.8,
    ):
        self.max_queue_size = max_queue_size
        self.priority_decay_rate = priority_decay_rate
        self.escalation_threshold = escalation_threshold

        # Priority queues
        self._queues: Dict[PriorityLevel, List[PriorityTask]] = {
            level: [] for level in PriorityLevel
        }

        # Task lookup
        self._tasks: Dict[str, PriorityTask] = {}

        # Dependencies
        self._dependency_graph: Dict[str, Set[str]] = defaultdict(set)

        # Statistics
        self._tasks_added = 0
        self._tasks_completed = 0
        self._priorities_escalated = 0
        self._priorities_decayed = 0

    async def initialize(self) -> None:
        """Initialize the priority manager"""
        logger.info("PriorityManager initialized")

    async def add_task(
        self,
        task_id: str,
        task_data: Dict[str, Any],
        priority: PriorityLevel = PriorityLevel.MEDIUM,
        deadline: Optional[float] = None,
        estimated_duration: float = 10.0,
        dependencies: Optional[List[str]] = None,
    ) -> bool:
        """
        Add a task to the priority queue.

        Args:
            task_id: Task identifier
            task_data: Task data
            priority: Initial priority
            deadline: Optional deadline timestamp
            estimated_duration: Estimated duration in seconds
            dependencies: List of task IDs this task depends on

        Returns:
            True if added successfully
        """
        if task_id in self._tasks:
            logger.warning(f"Task {task_id} already exists")
            return False

        if len(self._tasks) >= self.max_queue_size:
            logger.warning(f"Priority queue full, cannot add task {task_id}")
            return False

        task = PriorityTask(
            priority=priority,
            created_at=datetime.now().timestamp(),
            task_id=task_id,
            task_data=task_data,
            deadline=deadline,
            estimated_duration=estimated_duration,
            dependencies=dependencies or [],
        )

        # Add to queue
        heapq.heappush(self._queues[priority], task)

        # Add to lookup
        self._tasks[task_id] = task

        # Add dependencies
        for dep_id in task.dependencies:
            self._dependency_graph[dep_id].add(task_id)

        self._tasks_added += 1

        logger.debug(f"Added task {task_id} with priority {priority.name}")
        return True

    async def get_next_task(self) -> Optional[PriorityTask]:
        """
        Get the next highest priority task.

        Returns:
            Next task or None if queue is empty
        """
        # Check queues in priority order
        for level in PriorityLevel:
            queue = self._queues[level]

            while queue:
                task = heapq.heappop(queue)

                # Check if task still exists (might have been removed)
                if task.task_id not in self._tasks:
                    continue

                # Check if dependencies are satisfied
                if not self._are_dependencies_satisfied(task):
                    # Put back in queue
                    heapq.heappush(queue, task)
                    continue

                # Task is ready
                return task

        return None

    def _are_dependencies_satisfied(self, task: PriorityTask) -> bool:
        """Check if task dependencies are satisfied"""
        for dep_id in task.dependencies:
            if dep_id in self._tasks:
                # Dependency still in queue, not satisfied
                return False
        return True

    async def complete_task(self, task_id: str) -> bool:
        """
        Mark a task as completed.

        Args:
            task_id: Task identifier

        Returns:
            True if completed successfully
        """
        if task_id not in self._tasks:
            logger.warning(f"Task {task_id} not found")
            return False

        # Remove from lookup
        del self._tasks[task_id]

        # Remove from queue (will be skipped on next get)
        self._tasks_completed += 1

        logger.debug(f"Completed task {task_id}")
        return True

    async def update_priority(
        self,
        task_id: str,
        new_priority: PriorityLevel,
    ) -> bool:
        """
        Update task priority.

        Args:
            task_id: Task identifier
            new_priority: New priority level

        Returns:
            True if updated successfully
        """
        if task_id not in self._tasks:
            logger.warning(f"Task {task_id} not found")
            return False

        task = self._tasks[task_id]
        old_priority = task.priority

        # Remove from old queue
        old_queue = self._queues[old_priority]
        # Note: we can't easily remove from heap, so we'll mark it as removed
        # and let it be skipped when popped

        # Update priority
        task.priority = new_priority

        # Add to new queue
        heapq.heappush(self._queues[new_priority], task)

        logger.debug(f"Updated task {task_id} priority: {old_priority.name} -> {new_priority.name}")
        return True

    async def escalate_priorities(self) -> int:
        """
        Escalate priorities based on urgency and deadlines.

        Returns:
            Number of tasks escalated
        """
        escalated = 0

        for task_id, task in self._tasks.items():
            if task.urgency > self.escalation_threshold:
                # Escalate to higher priority
                current_level = task.priority
                new_level = PriorityLevel(max(0, current_level.value - 1))

                if new_level != current_level:
                    await self.update_priority(task_id, new_level)
                    escalated += 1
                    self._priorities_escalated += 1

        if escalated > 0:
            logger.info(f"Escalated {escalated} tasks due to urgency")

        return escalated

    async def decay_priorities(self) -> int:
        """
        Decay priorities of old tasks.

        Returns:
            Number of tasks decayed
        """
        decayed = 0
        now = datetime.now().timestamp()

        for task_id, task in self._tasks.items():
            age = now - task.created_at

            # Decay tasks older than 1 hour
            if age > 3600:
                current_level = task.priority
                new_level = PriorityLevel(min(len(PriorityLevel) - 1, current_level.value + 1))

                if new_level != current_level:
                    await self.update_priority(task_id, new_level)
                    decayed += 1
                    self._priorities_decayed += 1

        if decayed > 0:
            logger.debug(f"Decayed {decayed} old tasks")

        return decayed

    async def get_queue_status(self) -> Dict[str, Any]:
        """
        Get status of all priority queues.

        Returns:
            Queue status information
        """
        return {
            "total_tasks": len(self._tasks),
            "queues": {level.name: len(queue) for level, queue in self._queues.items()},
            "overdue_tasks": sum(1 for task in self._tasks.values() if task.is_overdue),
            "high_urgency_tasks": sum(1 for task in self._tasks.values() if task.urgency > 0.7),
        }

    async def get_task(self, task_id: str) -> Optional[PriorityTask]:
        """
        Get a specific task.

        Args:
            task_id: Task identifier

        Returns:
            Task or None if not found
        """
        return self._tasks.get(task_id)

    def get_metrics(self) -> Dict[str, Any]:
        """Get priority manager metrics"""
        return {
            "tasks_added": self._tasks_added,
            "tasks_completed": self._tasks_completed,
            "priorities_escalated": self._priorities_escalated,
            "priorities_decayed": self._priorities_decayed,
            "active_tasks": len(self._tasks),
            "dependency_edges": sum(len(deps) for deps in self._dependency_graph.values()),
        }
