"""Repository for Skill and SkillExecution entities."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import Skill, SkillExecution
from src.db.repositories.base import BaseRepository


class SkillRepository(BaseRepository[Skill]):
    """Repository for managing reusable skills."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(Skill, session)

    async def get_by_name(self, name: str) -> Skill | None:
        """Get a skill by its exact name."""
        return await self.get(name=name)

    async def search(self, task_type: str | None = None, limit: int = 20) -> list[Skill]:
        """Search skills, optionally filtering by task_type."""
        stmt = select(Skill).where(Skill.status == "active")
        
        if task_type:
            # Check if task_type is in the task_types array
            stmt = stmt.where(Skill.task_types.any(task_type))
            
        stmt = stmt.order_by(Skill.usage_count.desc(), Skill.success_rate.desc()).limit(limit)
        
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def record_execution(
        self,
        skill_id: UUID,
        session_id: UUID,
        success: bool,
        duration_ms: int | None = None,
        tokens_used: int | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> SkillExecution:
        """Record the outcome of a skill execution."""
        execution = SkillExecution(
            skill_id=skill_id,
            session_id=session_id,
            success=success,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            metadata_=metadata,
        )
        self.session.add(execution)
        
        skill = await self.get_by_id(skill_id)
        if skill:
            skill.usage_count += 1
            total_successes = (skill.success_rate * (skill.usage_count - 1)) + (1 if success else 0)
            skill.success_rate = total_successes / skill.usage_count
            
        await self.session.flush()
        return execution
