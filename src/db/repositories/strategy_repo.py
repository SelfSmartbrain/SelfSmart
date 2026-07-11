"""Repository for Strategy and StrategyExecution entities."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.enums import TaskType
from src.db.models import Strategy, StrategyExecution
from src.db.repositories.base import BaseRepository


class StrategyRepository(BaseRepository[Strategy]):
    """Repository for managing learned execution strategies."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Strategy, session)

    async def get_by_task_type(
        self,
        task_type: TaskType | str,
        limit: int = 10,
        active_only: bool = True,
    ) -> list[Strategy]:
        """Get top strategies for a given task type."""
        stmt = select(Strategy).where(Strategy.task_type == task_type)
        if active_only:
            stmt = stmt.where(Strategy.status == "active")
        
        # Order by success_rate and confidence descending
        stmt = stmt.order_by(Strategy.success_rate.desc(), Strategy.confidence.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def record_execution(
        self,
        strategy_id: UUID,
        session_id: UUID,
        task_id: UUID,
        success: bool,
        duration_ms: int | None = None,
        tokens_used: int | None = None,
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> StrategyExecution:
        """Record the outcome of a strategy execution."""
        execution = StrategyExecution(
            strategy_id=strategy_id,
            session_id=session_id,
            task_id=task_id,
            success=success,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            error=error,
            metadata_=metadata,
        )
        self.session.add(execution)
        
        # Update strategy stats (simplified version, should ideally be bulk updated)
        strategy = await self.get_by_id(strategy_id)
        if strategy:
            strategy.usage_count += 1
            # Recalculate success rate (moving average)
            total_successes = (strategy.success_rate * (strategy.usage_count - 1)) + (1 if success else 0)
            strategy.success_rate = total_successes / strategy.usage_count
            
        await self.session.flush()
        return execution
