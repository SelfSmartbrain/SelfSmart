"""Objective management for runtime loops."""

from __future__ import annotations

import random
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.config.logging import get_logger
from src.db.enums import ObjectiveStatus
from src.db.models import Objective as ObjectiveModel

logger = get_logger(__name__)


@dataclass
class Objective:
    """A durable unit of autonomous intent."""

    description: str
    priority: float = 0.5
    metadata: dict[str, Any] = field(default_factory=dict)
    objective_id: str = field(default_factory=lambda: f"obj_{uuid4().hex[:12]}")
    status: str = "active"
    created_at: datetime = field(default_factory=datetime.utcnow)
    updated_at: datetime = field(default_factory=datetime.utcnow)
    db_id: Any = None
    _await_hook: Callable[[], Awaitable[None]] | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def __await__(self):
        async def resolve() -> Objective:
            if self._await_hook is not None:
                hook = self._await_hook
                self._await_hook = None
                await hook()
            return self

        return resolve().__await__()

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "description": self.description,
            "priority": self.priority,
            "metadata": self.metadata,
            "status": self.status,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }

    @classmethod
    def from_db_model(cls, model: ObjectiveModel) -> Objective:
        """Create an Objective from a database model."""
        return cls(
            description=model.description,
            priority=model.priority,
            metadata=model.metadata_ or {},
            objective_id=model.objective_id,
            status=model.status.value,
            created_at=model.created_at,
            updated_at=model.updated_at,
            db_id=model.id,
        )


class ObjectiveManager:
    """Keeps track of active and historical objectives with persistence."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.active_objectives: list[Objective] = []
        self.completed_objectives: list[Objective] = []
        self.blocked_objectives: list[Objective] = []
        self.failed_objectives: list[Objective] = []
        self.paused_objectives: list[Objective] = []
        self.session = session

    async def load_from_db(self, session: AsyncSession) -> None:
        """Load all objectives from the database."""
        self.session = session
        result = await session.execute(select(ObjectiveModel))
        db_objectives = result.scalars().all()

        self.active_objectives = []
        self.completed_objectives = []
        self.blocked_objectives = []
        self.failed_objectives = []
        self.paused_objectives = []

        for db_obj in db_objectives:
            obj = Objective.from_db_model(db_obj)
            if db_obj.status == ObjectiveStatus.ACTIVE:
                self.active_objectives.append(obj)
            elif db_obj.status == ObjectiveStatus.COMPLETED:
                self.completed_objectives.append(obj)
            elif db_obj.status == ObjectiveStatus.BLOCKED:
                self.blocked_objectives.append(obj)
            elif db_obj.status == ObjectiveStatus.FAILED:
                self.failed_objectives.append(obj)
            elif db_obj.status == ObjectiveStatus.PAUSED:
                self.paused_objectives.append(obj)

    async def save_objective(self, objective: Objective, session: AsyncSession) -> Objective:
        """Save or update an objective in the database."""
        if objective.db_id:
            result = await session.execute(
                select(ObjectiveModel).where(ObjectiveModel.id == objective.db_id)
            )
            db_obj = result.scalar_one_or_none()
            if db_obj:
                db_obj.description = objective.description
                db_obj.priority = objective.priority
                db_obj.status = ObjectiveStatus(objective.status)
                db_obj.metadata_ = objective.metadata
                db_obj.updated_at = objective.updated_at
                if objective.status == "completed":
                    db_obj.completed_at = objective.updated_at
        else:
            db_obj = ObjectiveModel(
                objective_id=objective.objective_id,
                description=objective.description,
                priority=objective.priority,
                status=ObjectiveStatus(objective.status),
                metadata_=objective.metadata,
                created_at=objective.created_at,
                updated_at=objective.updated_at,
            )
            session.add(db_obj)
            await session.flush()
            objective.db_id = db_obj.id

        await session.commit()
        return objective

    async def delete_objective(self, objective_id: str, session: AsyncSession) -> bool:
        """Delete an objective from the database."""
        result = await session.execute(
            select(ObjectiveModel).where(ObjectiveModel.objective_id == objective_id)
        )
        db_obj = result.scalar_one_or_none()
        if db_obj:
            await session.delete(db_obj)
            await session.commit()
            return True
        return False

    def get_current_objective(self) -> Objective | None:
        """Return the highest-priority active objective, if one exists."""
        if not self.active_objectives:
            return None
        return max(self.active_objectives, key=lambda objective: objective.priority)

    def set_objective(
        self,
        objective: str | Objective,
        priority: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> Objective:
        """Create or register an active objective."""
        if isinstance(objective, Objective):
            next_objective = objective
        else:
            next_objective = Objective(
                description=objective,
                priority=priority,
                metadata=metadata or {},
            )

        next_objective.status = "active"
        next_objective.updated_at = datetime.utcnow()
        self.active_objectives.append(next_objective)

        if self.session:

            async def persist() -> None:
                await self.save_objective(next_objective, self.session)

            next_objective._await_hook = persist

        return next_objective

    async def complete_objective(self, objective_id: str) -> Objective | None:
        obj = self._move_objective(objective_id, "completed", self.completed_objectives)
        if obj and self.session:
            await self.save_objective(obj, self.session)
        return obj

    async def block_objective(self, objective_id: str) -> Objective | None:
        obj = self._move_objective(objective_id, "blocked", self.blocked_objectives)
        if obj and self.session:
            await self.save_objective(obj, self.session)
        return obj

    async def fail_objective(self, objective_id: str) -> Objective | None:
        obj = self._move_objective(objective_id, "failed", self.failed_objectives)
        if obj and self.session:
            await self.save_objective(obj, self.session)
        return obj

    async def pause_objective(self, objective_id: str) -> Objective | None:
        obj = self._move_objective(objective_id, "paused", self.paused_objectives)
        if obj and self.session:
            await self.save_objective(obj, self.session)
        return obj

    async def resume_objective(self, objective_id: str) -> Objective | None:
        for index, objective in enumerate(self.paused_objectives):
            if objective.objective_id == objective_id:
                moved = self.paused_objectives.pop(index)
                moved.status = "active"
                moved.updated_at = datetime.utcnow()
                self.active_objectives.append(moved)
                if self.session:
                    await self.save_objective(moved, self.session)
                return moved
        return None

    async def cancel_objective(self, objective_id: str) -> Objective | None:
        for index, objective in enumerate(self.active_objectives):
            if objective.objective_id == objective_id:
                moved = self.active_objectives.pop(index)
                moved.status = "cancelled"
                moved.updated_at = datetime.utcnow()
                if self.session:
                    await self.save_objective(moved, self.session)
                    await self.delete_objective(objective_id, self.session)
                return moved
        return None

    def list_objectives(self, status: str = "active") -> list[Objective]:
        buckets = {
            "active": self.active_objectives,
            "completed": self.completed_objectives,
            "blocked": self.blocked_objectives,
            "failed": self.failed_objectives,
            "paused": self.paused_objectives,
        }
        return list(buckets.get(status, []))

    def _move_objective(
        self,
        objective_id: str,
        status: str,
        destination: list[Objective],
    ) -> Objective | None:
        for index, objective in enumerate(self.active_objectives):
            if objective.objective_id == objective_id:
                moved = self.active_objectives.pop(index)
                moved.status = status
                moved.updated_at = datetime.utcnow()
                destination.append(moved)
                return moved
        return None

    async def suggest_followup_template(
        self,
        session: AsyncSession | None = None,
        context: dict[str, Any] | None = None,
    ) -> Objective | None:
        """Suggest a follow-up objective using templated patterns.

        This is a templated suggestion system, not autonomous LLM-based generation.
        It generates follow-up objectives based on:
        - Completed objectives in the same domain
        - System context (available resources, time constraints, etc.)
        - Priority heuristics
        - Predefined pattern templates

        The method name explicitly indicates this is a template-based suggestion,
        not autonomous reasoning. For true autonomous generation, an LLM-based
        implementation would be required.
        """
        context = context or {}

        # A template suggestion needs a completed objective to build on.
        if not self.completed_objectives:
            logger.info("No completed objectives available for a follow-up suggestion")
            return None

        # Get the most recently completed objective
        last_completed = max(self.completed_objectives, key=lambda obj: obj.updated_at)

        # Generate follow-up objective based on patterns
        follow_up_patterns = [
            f"Refine and optimize: {last_completed.description}",
            f"Validate and test: {last_completed.description}",
            f"Document and share: {last_completed.description}",
            f"Scale and deploy: {last_completed.description}",
            f"Monitor and maintain: {last_completed.description}",
        ]

        # Select pattern based on context or random
        pattern_index = context.get(
            "follow_up_pattern", random.randint(0, len(follow_up_patterns) - 1)
        )
        pattern_index = min(pattern_index, len(follow_up_patterns) - 1)

        new_description = follow_up_patterns[pattern_index]

        # Adjust priority based on context
        base_priority = last_completed.priority
        context_priority = context.get("priority_adjustment", 0.0)
        new_priority = max(0.1, min(1.0, base_priority + context_priority))

        # Create metadata tracking the source
        new_metadata = {
            "autonomous": False,  # This is templated, not autonomous
            "source_objective_id": last_completed.objective_id,
            "generation_method": "template_based",
            "generated_at": datetime.utcnow().isoformat(),
        }

        new_objective = Objective(
            description=new_description,
            priority=new_priority,
            metadata=new_metadata,
        )

        logger.info(
            f"Suggested template-based objective: {new_description} (priority={new_priority})"
        )

        # Add to active objectives and persist if session available
        new_objective.status = "active"
        new_objective.updated_at = datetime.utcnow()
        self.active_objectives.append(new_objective)

        if session:
            await self.save_objective(new_objective, session)

        return new_objective

    async def should_suggest_followup_template(
        self,
        context: dict[str, Any] | None = None,
    ) -> bool:
        """Determine whether a templated follow-up should be suggested.

        Returns True if:
        - There are completed objectives to build on
        - There are no active objectives (idle state)
        - Context allows a follow-up suggestion
        """
        context = context or {}

        # Don't generate if we have active objectives
        if self.active_objectives:
            return False

        # Don't generate if we have no completed objectives
        if not self.completed_objectives:
            return False

        # Check context override
        if context.get("force_followup_suggestion") is True:
            return True

        if context.get("disable_followup_suggestion") is True:
            return False

        # Default: generate when idle with history
        return True
