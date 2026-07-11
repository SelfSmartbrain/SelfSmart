"""
Generic async repository base class.

Provides standard CRUD operations on any SQLAlchemy model that
inherits from ``Base``. Concrete repositories extend this class
and add domain-specific query methods.
"""

from __future__ import annotations

from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Base

ModelT = TypeVar("ModelT", bound=Base)


class BaseRepository(Generic[ModelT]):
    """Generic async repository with CRUD operations.

    Parameters:
        model: The SQLAlchemy ORM model class this repository manages.
        session: The async database session to use for queries.
    """

    def __init__(self, model: type[ModelT], session: AsyncSession) -> None:
        self.model = model
        self.session = session

    async def get_by_id(self, entity_id: UUID) -> ModelT | None:
        """Fetch a single entity by its primary key.

        Args:
            entity_id: UUID primary key of the entity.

        Returns:
            The entity instance, or ``None`` if not found.
        """
        return await self.session.get(self.model, entity_id)

    async def get(self, **filters: Any) -> ModelT | None:
        """Fetch a single entity matching the given column filters.

        Args:
            **filters: Column-name / value pairs used as equality filters.

        Returns:
            The first matching entity, or ``None``.
        """
        stmt = select(self.model).filter_by(**filters)
        result = await self.session.execute(stmt)
        return result.scalars().first()

    async def list(
        self,
        *,
        offset: int = 0,
        limit: int = 100,
        order_by: str | None = None,
        **filters: Any,
    ) -> list[ModelT]:
        """List entities with optional filtering, ordering, and pagination.

        Args:
            offset: Number of rows to skip (default 0).
            limit: Maximum number of rows to return (default 100, max 1000).
            order_by: Column name to order by. Prefix with ``-`` for descending.
            **filters: Column-name / value pairs used as equality filters.

        Returns:
            A list of matching entities.
        """
        limit = min(limit, 1000)
        stmt = select(self.model).filter_by(**filters).offset(offset).limit(limit)

        if order_by is not None:
            descending = order_by.startswith("-")
            col_name = order_by.lstrip("-")
            column = getattr(self.model, col_name)
            stmt = stmt.order_by(column.desc() if descending else column.asc())

        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def create(self, **kwargs: Any) -> ModelT:
        """Create and persist a new entity.

        Args:
            **kwargs: Column values for the new entity.

        Returns:
            The newly created entity with server-generated fields populated.
        """
        entity = self.model(**kwargs)
        self.session.add(entity)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def update(self, entity_id: UUID, **kwargs: Any) -> ModelT | None:
        """Update an existing entity by ID.

        Args:
            entity_id: UUID primary key of the entity to update.
            **kwargs: Column values to update.

        Returns:
            The updated entity, or ``None`` if not found.
        """
        entity = await self.get_by_id(entity_id)
        if entity is None:
            return None
        for key, value in kwargs.items():
            setattr(entity, key, value)
        await self.session.flush()
        await self.session.refresh(entity)
        return entity

    async def delete(self, entity_id: UUID) -> bool:
        """Delete an entity by ID.

        Args:
            entity_id: UUID primary key of the entity to delete.

        Returns:
            ``True`` if the entity was found and deleted, ``False`` otherwise.
        """
        entity = await self.get_by_id(entity_id)
        if entity is None:
            return False
        await self.session.delete(entity)
        await self.session.flush()
        return True
