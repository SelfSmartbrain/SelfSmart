"""
Memory repository for managing agent memory entries.

Supports the episodic / semantic / procedural memory model with
importance scoring and access tracking.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.enums import MemoryType
from src.db.models import Memory
from src.db.repositories.base import BaseRepository


class MemoryRepository(BaseRepository[Memory]):
    """Repository for agent memory entries."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Memory, session)

    async def store_memory(
        self,
        *,
        user_id: UUID,
        memory_type: MemoryType,
        content: str,
        session_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
        importance_score: float = 0.5,
        embedding_id: str | None = None,
    ) -> Memory:
        """Store a new memory entry.

        Args:
            user_id: The owning user's ID.
            memory_type: Classification of the memory (episodic/semantic/procedural).
            content: The textual content of the memory.
            session_id: Optional session this memory is associated with.
            metadata: Optional metadata dict (JSONB).
            importance_score: Importance score from 0.0 to 1.0 (default 0.5).
            embedding_id: Optional reference to the vector embedding.

        Returns:
            The newly created ``Memory``.
        """
        return await self.create(
            user_id=user_id,
            session_id=session_id,
            memory_type=memory_type,
            content=content,
            metadata_=metadata,
            importance_score=importance_score,
            embedding_id=embedding_id,
        )

    async def get_memory(self, memory_id: UUID) -> Memory | None:
        """Fetch a memory by its ID.

        Args:
            memory_id: The memory's UUID.

        Returns:
            The ``Memory`` or ``None``.
        """
        return await self.get_by_id(memory_id)

    async def search_by_type(
        self,
        user_id: UUID,
        memory_type: MemoryType,
        *,
        offset: int = 0,
        limit: int = 50,
    ) -> list[Memory]:
        """Search memories by type for a specific user.

        Args:
            user_id: The owning user's ID.
            memory_type: The memory type to filter on.
            offset: Pagination offset.
            limit: Maximum results to return.

        Returns:
            A list of ``Memory`` instances, ordered by importance descending.
        """
        stmt = (
            select(Memory)
            .where(Memory.user_id == user_id)
            .where(Memory.memory_type == memory_type)
            .order_by(Memory.importance_score.desc())
            .offset(offset)
            .limit(min(limit, 1000))
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def update_access(self, memory_id: UUID) -> Memory | None:
        """Record an access to a memory, incrementing the counter and timestamp.

        Args:
            memory_id: The memory's UUID.

        Returns:
            The updated ``Memory``, or ``None`` if not found.
        """
        memory = await self.get_by_id(memory_id)
        if memory is None:
            return None
        return await self.update(
            memory_id,
            access_count=memory.access_count + 1,
            last_accessed=datetime.now(timezone.utc),
        )

    async def get_recent_memories(
        self,
        user_id: UUID,
        *,
        memory_type: MemoryType | None = None,
        limit: int = 20,
    ) -> list[Memory]:
        """Retrieve the most recently created memories for a user.

        Args:
            user_id: The owning user's ID.
            memory_type: Optional type filter.
            limit: Maximum results to return.

        Returns:
            A list of ``Memory`` instances, newest first.
        """
        stmt = (
            select(Memory)
            .where(Memory.user_id == user_id)
            .order_by(Memory.created_at.desc())
            .limit(min(limit, 1000))
        )
        if memory_type is not None:
            stmt = stmt.where(Memory.memory_type == memory_type)

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def delete_memory(self, memory_id: UUID) -> bool:
        """Delete a memory entry.

        Args:
            memory_id: The memory's UUID.

        Returns:
            ``True`` if the memory was deleted, ``False`` if not found.
        """
        return await self.delete(memory_id)
