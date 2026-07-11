"""
Execution repository for tracking agent execution attempts.

Each task can have multiple execution records representing individual
agent invocations and their outcomes.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.enums import ExecutionStatus
from src.db.models import Execution
from src.db.repositories.base import BaseRepository


class ExecutionRepository(BaseRepository[Execution]):
    """Repository for agent execution records."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Execution, session)

    async def create_execution(
        self,
        *,
        task_id: UUID,
        agent_type: str,
        input_data: dict[str, Any] | None = None,
    ) -> Execution:
        """Create a new execution record for a task.

        The execution starts in RUNNING status.

        Args:
            task_id: The parent task's UUID.
            agent_type: Identifier of the agent performing execution.
            input_data: Optional input payload (JSONB).

        Returns:
            The newly created ``Execution``.
        """
        return await self.create(
            task_id=task_id,
            agent_type=agent_type,
            input_data=input_data,
            status=ExecutionStatus.RUNNING,
        )

    async def update_execution(
        self,
        execution_id: UUID,
        *,
        status: ExecutionStatus,
        output_data: dict[str, Any] | None = None,
        tokens_used: int | None = None,
        duration_ms: int | None = None,
        error: str | None = None,
    ) -> Execution | None:
        """Update an execution record with results.

        Args:
            execution_id: The execution's UUID.
            status: The final execution status.
            output_data: Optional output payload (JSONB).
            tokens_used: Total tokens consumed during execution.
            duration_ms: Wall-clock execution time in milliseconds.
            error: Error message if the execution failed.

        Returns:
            The updated ``Execution``, or ``None`` if not found.
        """
        updates: dict[str, Any] = {"status": status}
        if output_data is not None:
            updates["output_data"] = output_data
        if tokens_used is not None:
            updates["tokens_used"] = tokens_used
        if duration_ms is not None:
            updates["duration_ms"] = duration_ms
        if error is not None:
            updates["error"] = error

        return await self.update(execution_id, **updates)

    async def get_task_executions(
        self,
        task_id: UUID,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Execution]:
        """List all execution attempts for a task.

        Args:
            task_id: The parent task's UUID.
            offset: Pagination offset.
            limit: Maximum results to return.

        Returns:
            A list of ``Execution`` records, ordered by creation time.
        """
        stmt = (
            select(Execution)
            .where(Execution.task_id == task_id)
            .order_by(Execution.created_at.asc())
            .offset(offset)
            .limit(min(limit, 1000))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
