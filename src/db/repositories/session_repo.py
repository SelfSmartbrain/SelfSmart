"""
Session repository for managing agent sessions.

Provides domain-specific query methods on top of ``BaseRepository``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.enums import SessionStatus
from src.db.models import Session
from src.db.repositories.base import BaseRepository


class SessionRepository(BaseRepository[Session]):
    """Repository for agent sessions."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Session, session)

    async def create_session(
        self,
        *,
        user_id: UUID,
        goal: str,
        context: dict | None = None,
    ) -> Session:
        """Create a new agent session.

        Args:
            user_id: The owning user's ID.
            goal: The high-level goal for this session.
            context: Optional initial context (JSONB).

        Returns:
            The newly created ``Session``.
        """
        return await self.create(
            user_id=user_id,
            goal=goal,
            status=SessionStatus.PENDING,
            context=context,
        )

    async def get_session(self, session_id: UUID) -> Session | None:
        """Fetch a session by ID.

        Args:
            session_id: The session's UUID.

        Returns:
            The ``Session`` or ``None``.
        """
        return await self.get_by_id(session_id)

    async def update_status(
        self,
        session_id: UUID,
        status: SessionStatus,
    ) -> Session | None:
        """Update the status of a session.

        Automatically sets ``completed_at`` when transitioning to a
        terminal state (COMPLETED, FAILED, CANCELLED).

        Args:
            session_id: The session's UUID.
            status: The new status value.

        Returns:
            The updated ``Session``, or ``None`` if not found.
        """
        updates: dict = {"status": status}
        terminal = {SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED}
        if status in terminal:
            updates["completed_at"] = datetime.now(timezone.utc)
        return await self.update(session_id, **updates)

    async def get_user_sessions(
        self,
        user_id: UUID,
        *,
        status: SessionStatus | None = None,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Session]:
        """List sessions belonging to a user with optional status filter.

        Args:
            user_id: The owning user's ID.
            status: Optional status filter.
            offset: Pagination offset.
            limit: Maximum results to return.

        Returns:
            A list of matching ``Session`` instances, newest first.
        """
        stmt = (
            select(Session)
            .where(Session.user_id == user_id)
            .order_by(Session.created_at.desc())
            .offset(offset)
            .limit(min(limit, 1000))
        )
        if status is not None:
            stmt = stmt.where(Session.status == status)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())
