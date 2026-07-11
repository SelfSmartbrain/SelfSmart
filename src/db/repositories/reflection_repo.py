"""
Reflection repository for managing agent self-reflection records.

Supports the agent's continuous improvement loop by storing structured
reflections about successes, failures, root causes, and suggested
improvements.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.enums import ReflectionType
from src.db.models import ReflectionRecord
from src.db.repositories.base import BaseRepository


class ReflectionRepository(BaseRepository[ReflectionRecord]):
    """Repository for agent reflection records."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(ReflectionRecord, session)

    async def create_reflection(
        self,
        *,
        session_id: UUID,
        reflection_type: ReflectionType,
        task_id: UUID | None = None,
        successes: list[str] | None = None,
        failures: list[str] | None = None,
        root_causes: list[str] | None = None,
        improvements: list[str] | None = None,
        confidence_score: float = 0.5,
    ) -> ReflectionRecord:
        """Create a new reflection record.

        Args:
            session_id: The session this reflection belongs to.
            reflection_type: Scope of the reflection (task/session/strategy).
            task_id: Optional task this reflection is about.
            successes: List of things that went well.
            failures: List of things that went wrong.
            root_causes: List of identified root causes for failures.
            improvements: List of suggested improvements.
            confidence_score: Agent's confidence in the reflection (0.0–1.0).

        Returns:
            The newly created ``ReflectionRecord``.
        """
        return await self.create(
            session_id=session_id,
            task_id=task_id,
            reflection_type=reflection_type,
            successes=successes,
            failures=failures,
            root_causes=root_causes,
            improvements=improvements,
            confidence_score=confidence_score,
            applied=False,
        )

    async def get_session_reflections(
        self,
        session_id: UUID,
        *,
        reflection_type: ReflectionType | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[ReflectionRecord]:
        """List reflections for a session with optional type filter.

        Args:
            session_id: The session's UUID.
            reflection_type: Optional reflection type filter.
            offset: Pagination offset.
            limit: Maximum results to return.

        Returns:
            A list of ``ReflectionRecord`` instances, newest first.
        """
        stmt = (
            select(ReflectionRecord)
            .where(ReflectionRecord.session_id == session_id)
            .order_by(ReflectionRecord.created_at.desc())
            .offset(offset)
            .limit(min(limit, 1000))
        )
        if reflection_type is not None:
            stmt = stmt.where(ReflectionRecord.reflection_type == reflection_type)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def get_unapplied_improvements(
        self,
        *,
        session_id: UUID | None = None,
        limit: int = 20,
    ) -> list[ReflectionRecord]:
        """Fetch reflection records with unapplied improvements.

        These are reflections where ``applied`` is ``False`` and the
        ``improvements`` array is non-empty, ordered by confidence score
        descending so the most confident suggestions come first.

        Args:
            session_id: Optional session filter. If ``None``, returns
                unapplied improvements across all sessions.
            limit: Maximum results to return.

        Returns:
            A list of ``ReflectionRecord`` instances with pending improvements.
        """
        stmt = (
            select(ReflectionRecord)
            .where(ReflectionRecord.applied == False)  # noqa: E712
            .where(ReflectionRecord.improvements.isnot(None))
            .order_by(ReflectionRecord.confidence_score.desc())
            .limit(min(limit, 1000))
        )
        if session_id is not None:
            stmt = stmt.where(ReflectionRecord.session_id == session_id)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
