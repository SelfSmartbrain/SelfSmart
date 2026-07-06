"""
Task Marketplace - Task distribution and delegation

The TaskMarketplace is responsible for:
- Task posting and discovery
- Agent bidding on tasks
- Task assignment
- Delegation management
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import heapq


logger = logging.getLogger(__name__)


class TaskStatus(Enum):
    """Status of a task"""

    OPEN = "open"
    BIDDING = "bidding"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


@dataclass
class Task:
    """A task in the marketplace"""

    task_id: str
    title: str
    description: str
    required_capabilities: List[str]
    priority: int = 5
    reward: float = 0.0
    status: TaskStatus = TaskStatus.OPEN
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    assigned_to: Optional[str] = None
    deadline: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Bid:
    """A bid on a task"""

    bid_id: str
    task_id: str
    agent_id: str
    proposed_price: float
    estimated_duration: float
    confidence: float = 0.5
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class TaskMarketplace:
    """
    Marketplace for task distribution and delegation.

    Provides:
    - Task posting and discovery
    - Agent bidding system
    - Task assignment
    - Delegation tracking
    """

    def __init__(self):
        self._tasks: Dict[str, Task] = {}
        self._bids: Dict[str, List[Bid]] = defaultdict(list)
        self._agent_tasks: Dict[str, Set[str]] = defaultdict(set)

        # Task queue by priority
        self._task_queue: List[Tuple[int, float, str]] = []  # (priority, timestamp, task_id)

        # Statistics
        self._tasks_posted = 0
        self._tasks_assigned = 0
        self._tasks_completed = 0
        self._bids_received = 0

    async def initialize(self) -> None:
        """Initialize the task marketplace"""
        logger.info("TaskMarketplace initialized")

    async def post_task(
        self,
        title: str,
        description: str,
        required_capabilities: List[str],
        priority: int = 5,
        reward: float = 0.0,
        deadline: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Task:
        """
        Post a task to the marketplace.

        Args:
            title: Task title
            description: Task description
            required_capabilities: Required capabilities
            priority: Task priority (0-10)
            reward: Task reward
            deadline: Optional deadline
            metadata: Additional metadata

        Returns:
            Posted task
        """
        task_id = f"task_{datetime.now().timestamp()}"

        task = Task(
            task_id=task_id,
            title=title,
            description=description,
            required_capabilities=required_capabilities,
            priority=priority,
            reward=reward,
            deadline=deadline,
            metadata=metadata or {},
        )

        self._tasks[task_id] = task

        # Add to priority queue
        heapq.heappush(
            self._task_queue,
            (-priority, datetime.now().timestamp(), task_id),  # Negative for max-heap
        )

        self._tasks_posted += 1

        logger.info(f"Posted task {task_id}: {title} (priority: {priority})")
        return task

    async def bid_on_task(
        self,
        task_id: str,
        agent_id: str,
        proposed_price: float,
        estimated_duration: float,
        confidence: float = 0.5,
    ) -> bool:
        """
        Bid on a task.

        Args:
            task_id: Task identifier
            agent_id: Agent identifier
            proposed_price: Proposed price
            estimated_duration: Estimated duration
            confidence: Confidence in completion

        Returns:
            True if bid accepted
        """
        if task_id not in self._tasks:
            logger.warning(f"Task {task_id} not found")
            return False

        task = self._tasks[task_id]

        if task.status != TaskStatus.OPEN and task.status != TaskStatus.BIDDING:
            logger.warning(f"Task {task_id} is not open for bidding")
            return False

        bid = Bid(
            bid_id=f"bid_{datetime.now().timestamp()}",
            task_id=task_id,
            agent_id=agent_id,
            proposed_price=proposed_price,
            estimated_duration=estimated_duration,
            confidence=confidence,
        )

        self._bids[task_id].append(bid)
        self._bids_received += 1

        # Update task status
        if task.status == TaskStatus.OPEN:
            task.status = TaskStatus.BIDDING

        logger.debug(f"Agent {agent_id} bid on task {task_id}")
        return True

    async def assign_task(
        self,
        task_id: str,
        agent_id: str,
    ) -> bool:
        """
        Assign a task to an agent.

        Args:
            task_id: Task identifier
            agent_id: Agent identifier

        Returns:
            True if assigned successfully
        """
        if task_id not in self._tasks:
            logger.warning(f"Task {task_id} not found")
            return False

        task = self._tasks[task_id]

        if task.status not in (TaskStatus.OPEN, TaskStatus.BIDDING):
            logger.warning(f"Task {task_id} is not available for assignment")
            return False

        task.status = TaskStatus.ASSIGNED
        task.assigned_to = agent_id

        self._agent_tasks[agent_id].add(task_id)
        self._tasks_assigned += 1

        logger.info(f"Assigned task {task_id} to agent {agent_id}")
        return True

    async def start_task(self, task_id: str) -> bool:
        """
        Mark a task as in progress.

        Args:
            task_id: Task identifier

        Returns:
            True if started successfully
        """
        if task_id not in self._tasks:
            logger.warning(f"Task {task_id} not found")
            return False

        task = self._tasks[task_id]
        task.status = TaskStatus.IN_PROGRESS

        logger.debug(f"Started task {task_id}")
        return True

    async def complete_task(
        self,
        task_id: str,
        results: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        Mark a task as completed.

        Args:
            task_id: Task identifier
            results: Task results

        Returns:
            True if completed successfully
        """
        if task_id not in self._tasks:
            logger.warning(f"Task {task_id} not found")
            return False

        task = self._tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.metadata["results"] = results or {}

        if task.assigned_to:
            self._agent_tasks[task.assigned_to].discard(task_id)

        self._tasks_completed += 1

        logger.info(f"Completed task {task_id}")
        return True

    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a task.

        Args:
            task_id: Task identifier

        Returns:
            True if cancelled successfully
        """
        if task_id not in self._tasks:
            logger.warning(f"Task {task_id} not found")
            return False

        task = self._tasks[task_id]
        task.status = TaskStatus.CANCELLED

        if task.assigned_to:
            self._agent_tasks[task.assigned_to].discard(task_id)

        logger.info(f"Cancelled task {task_id}")
        return True

    def get_task(self, task_id: str) -> Optional[Task]:
        """Get a task by ID"""
        return self._tasks.get(task_id)

    def find_tasks(
        self,
        capability: Optional[str] = None,
        status: Optional[TaskStatus] = None,
        min_priority: int = 0,
        limit: int = 50,
    ) -> List[Task]:
        """
        Find tasks matching criteria.

        Args:
            capability: Filter by required capability
            status: Filter by status
            min_priority: Minimum priority
            limit: Maximum results

        Returns:
            List of matching tasks
        """
        tasks = list(self._tasks.values())

        if capability:
            tasks = [t for t in tasks if capability in t.required_capabilities]

        if status:
            tasks = [t for t in tasks if t.status == status]

        tasks = [t for t in tasks if t.priority >= min_priority]

        # Sort by priority
        tasks.sort(key=lambda t: t.priority, reverse=True)

        return tasks[:limit]

    def get_agent_tasks(
        self,
        agent_id: str,
        status: Optional[TaskStatus] = None,
    ) -> List[Task]:
        """
        Get tasks assigned to an agent.

        Args:
            agent_id: Agent identifier
            status: Filter by status

        Returns:
            List of tasks
        """
        task_ids = self._agent_tasks.get(agent_id, set())

        tasks = [self._tasks[tid] for tid in task_ids if tid in self._tasks]

        if status:
            tasks = [t for t in tasks if t.status == status]

        return tasks

    def get_task_bids(self, task_id: str) -> List[Bid]:
        """Get bids for a task"""
        return self._bids.get(task_id, [])

    def select_best_bid(
        self,
        task_id: str,
        criteria: str = "price",  # price, duration, confidence, balanced
    ) -> Optional[Bid]:
        """
        Select the best bid for a task.

        Args:
            task_id: Task identifier
            criteria: Selection criteria

        Returns:
            Best bid or None
        """
        bids = self._bids.get(task_id, [])

        if not bids:
            return None

        if criteria == "price":
            # Lowest price
            return min(bids, key=lambda b: b.proposed_price)
        elif criteria == "duration":
            # Shortest duration
            return min(bids, key=lambda b: b.estimated_duration)
        elif criteria == "confidence":
            # Highest confidence
            return max(bids, key=lambda b: b.confidence)
        else:  # balanced
            # Combined score
            def score(bid: Bid) -> float:
                return (
                    bid.confidence * 0.5
                    + (1.0 - min(1.0, bid.proposed_price / 100.0)) * 0.3
                    + (1.0 - min(1.0, bid.estimated_duration / 3600.0)) * 0.2
                )

            return max(bids, key=score)

    def get_metrics(self) -> Dict[str, Any]:
        """Get marketplace metrics"""
        return {
            "tasks_posted": self._tasks_posted,
            "tasks_assigned": self._tasks_assigned,
            "tasks_completed": self._tasks_completed,
            "bids_received": self._bids_received,
            "open_tasks": sum(1 for t in self._tasks.values() if t.status == TaskStatus.OPEN),
            "in_progress_tasks": sum(
                1 for t in self._tasks.values() if t.status == TaskStatus.IN_PROGRESS
            ),
            "average_bids_per_task": (
                sum(len(bids) for bids in self._bids.values()) / len(self._bids)
                if self._bids
                else 0.0
            ),
        }
