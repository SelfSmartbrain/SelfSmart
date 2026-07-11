"""Repository for learning-related entities: LearningPattern, Policy, ExperienceRecord."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import LearningPattern, Policy, ExperienceRecord
from src.db.repositories.base import BaseRepository


class LearningRepository:
    """Repository for managing learning and self-improvement data."""

    def __init__(self, session: AsyncSession) -> None:
        self.session = session
        self.patterns = BaseRepository(LearningPattern, session)
        self.policies = BaseRepository(Policy, session)
        self.experiences = BaseRepository(ExperienceRecord, session)

    async def get_active_policies(self) -> list[Policy]:
        """Fetch all currently active policies."""
        return await self.policies.list(is_active=True, order_by="-confidence")

    async def get_recent_experiences(
        self,
        task_type: str,
        limit: int = 10,
    ) -> list[ExperienceRecord]:
        """Fetch recent experiences for a given task type."""
        return await self.experiences.list(
            task_type=task_type,
            order_by="-created_at",
            limit=limit,
        )

    async def record_experience(
        self,
        session_id: UUID,
        task_id: UUID,
        task_type: str,
        outcome: str,
        score: float,
        context_summary: str,
        strategy_used: dict[str, Any] | None = None,
        lessons: list[str] | None = None,
        embedding_id: str | None = None,
    ) -> ExperienceRecord:
        """Create a new experience record."""
        return await self.experiences.create(
            session_id=session_id,
            task_id=task_id,
            task_type=task_type,
            outcome=outcome,
            score=score,
            context_summary=context_summary,
            strategy_used=strategy_used,
            lessons=lessons,
            embedding_id=embedding_id,
        )
