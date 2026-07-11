"""
Task repository for managing tasks within sessions.

Provides domain-specific query methods for task lifecycle management,
dependency tracking, and work queue operations.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.enums import Priority, TaskStatus
from src.db.models import Task
from src.db.repositories.base import BaseRepository


class TaskRepository(BaseRepository[Task]):
    """Repository for session tasks."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Task, session)

    async def create_task(
        self,
        *,
        session_id: UUID,
        title: str,
        description: str | None = None,
        parent_task_id: UUID | None = None,
        priority: Priority = Priority.NORMAL,
        agent_type: str | None = None,
        dependencies: list[UUID] | None = None,
    ) -> Task:
        """Create a new task within a session.

        Args:
            session_id: The parent session's UUID.
            title: Short title describing the task.
            description: Detailed description of what the task should accomplish.
            parent_task_id: Optional parent task for hierarchical decomposition.
            priority: Task priority level (default NORMAL).
            agent_type: The agent type designated to handle this task.
            dependencies: UUIDs of tasks that must complete before this one.

        Returns:
            The newly created ``Task``.
        """
        dep_strings: list[str] | None = None
        if dependencies:
            dep_strings = [str(d) for d in dependencies]

        return await self.create(
            session_id=session_id,
            title=title,
            description=description,
            parent_task_id=parent_task_id,
            status=TaskStatus.PENDING,
            priority=priority,
            agent_type=agent_type,
            dependencies=dep_strings,
        )

    async def get_task(self, task_id: UUID) -> Task | None:
        """Fetch a task by its ID.

        Args:
            task_id: The task's UUID.

        Returns:
            The ``Task`` or ``None``.
        """
        return await self.get_by_id(task_id)

    async def update_status(
        self,
        task_id: UUID,
        status: TaskStatus,
        *,
        result: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> Task | None:
        """Update the status of a task.

        Automatically sets ``started_at`` when transitioning to IN_PROGRESS,
        and ``completed_at`` when transitioning to a terminal state.

        Args:
            task_id: The task's UUID.
            status: The new status value.
            result: Optional result payload (set on COMPLETED).
            error: Optional error message (set on FAILED).

        Returns:
            The updated ``Task``, or ``None`` if not found.
        """
        now = datetime.now(timezone.utc)
        updates: dict[str, Any] = {"status": status}

        if status == TaskStatus.IN_PROGRESS:
            updates["started_at"] = now

        terminal = {TaskStatus.COMPLETED, TaskStatus.FAILED, TaskStatus.CANCELLED}
        if status in terminal:
            updates["completed_at"] = now

        if result is not None:
            updates["result"] = result
        if error is not None:
            updates["error"] = error

        return await self.update(task_id, **updates)

    async def get_session_tasks(
        self,
        session_id: UUID,
        *,
        status: TaskStatus | None = None,
        offset: int = 0,
        limit: int = 100,
    ) -> list[Task]:
        """List all tasks belonging to a session.

        Args:
            session_id: The parent session's UUID.
            status: Optional status filter.
            offset: Pagination offset.
            limit: Maximum results to return.

        Returns:
            A list of ``Task`` instances ordered by creation time.
        """
        stmt = (
            select(Task)
            .where(Task.session_id == session_id)
            .order_by(Task.created_at.asc())
            .offset(offset)
            .limit(min(limit, 1000))
        )
        if status is not None:
            stmt = stmt.where(Task.status == status)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_pending_tasks(
        self,
        session_id: UUID,
        *,
        limit: int = 50,
    ) -> list[Task]:
        """Get pending tasks for a session, ordered by priority and creation time.

        Args:
            session_id: The parent session's UUID.
            limit: Maximum number of tasks to return.

        Returns:
            A list of pending ``Task`` instances, highest priority first.
        """
        priority_order = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.NORMAL: 2,
            Priority.LOW: 3,
        }

        stmt = (
            select(Task)
            .where(Task.session_id == session_id)
            .where(Task.status == TaskStatus.PENDING)
            .order_by(Task.created_at.asc())
            .limit(min(limit, 1000))
        )
        result = await self.session.execute(stmt)
        tasks = list(result.scalars().all())

        # Sort in Python for enum-based priority ordering
        tasks.sort(key=lambda t: (priority_order.get(t.priority, 2), t.created_at))
        return tasks

    async def get_next_task(self, session_id: UUID) -> Task | None:
        """Get the highest-priority pending task for a session.

        This is a convenience wrapper around ``get_pending_tasks``
        that returns only the first task.

        Args:
            session_id: The parent session's UUID.

        Returns:
            The next ``Task`` to execute, or ``None`` if the queue is empty.
        """
        tasks = await self.get_pending_tasks(session_id, limit=1)
        return tasks[0] if tasks else None

    async def increment_retry(self, task_id: UUID) -> Task | None:
        """Increment the retry count for a failed task and reset to PENDING.

        Args:
            task_id: The task's UUID.

        Returns:
            The updated ``Task``, or ``None`` if not found.
        """
        task = await self.get_by_id(task_id)
        if task is None:
            return None
        return await self.update(
            task_id,
            retry_count=task.retry_count + 1,
            status=TaskStatus.PENDING,
            error=None,
            started_at=None,
            completed_at=None,
        )
