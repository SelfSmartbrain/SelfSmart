"""Progress tracking for autonomous objectives."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ObjectiveProgress as ObjectiveProgressModel


@dataclass
class ProgressRecord:
    objective_id: str
    status: str
    detail: str = ""
    result: dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.utcnow)
    db_id: Any = None
    _await_hook: Callable[[], Awaitable[None]] | None = field(
        default=None,
        repr=False,
        compare=False,
    )

    def __await__(self):
        async def resolve() -> ProgressRecord:
            if self._await_hook is not None:
                hook = self._await_hook
                self._await_hook = None
                await hook()
            return self

        return resolve().__await__()

    def to_dict(self) -> dict[str, Any]:
        return {
            "objective_id": self.objective_id,
            "status": self.status,
            "detail": self.detail,
            "result": self.result,
            "timestamp": self.timestamp.isoformat(),
        }

    @classmethod
    def from_db_model(cls, model: ObjectiveProgressModel) -> ProgressRecord:
        """Create a ProgressRecord from a database model."""
        return cls(
            objective_id=str(model.objective_id),
            status=model.status,
            detail=model.detail or "",
            result=model.result or {},
            timestamp=model.timestamp,
            db_id=model.id,
        )


class ProgressTracker:
    """Records every runtime tick against an objective with persistence."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.records: list[ProgressRecord] = []
        self.session = session

    async def load_from_db(self, session: AsyncSession, objective_id: str | None = None) -> None:
        """Load progress records from the database."""
        self.session = session
        query = select(ObjectiveProgressModel)
        if objective_id:
            query = query.where(ObjectiveProgressModel.objective_id == objective_id)

        result = await session.execute(query)
        db_records = result.scalars().all()

        self.records = [ProgressRecord.from_db_model(rec) for rec in db_records]

    async def save_record(self, record: ProgressRecord, session: AsyncSession) -> ProgressRecord:
        """Save a progress record to the database."""
        db_record = ObjectiveProgressModel(
            objective_id=record.objective_id,
            status=record.status,
            detail=record.detail,
            result=record.result,
            timestamp=record.timestamp,
        )
        session.add(db_record)
        await session.flush()
        record.db_id = db_record.id
        await session.commit()
        return record

    def track_progress(
        self,
        objective: Any,
        status: str = "in_progress",
        detail: str = "",
        result: dict[str, Any] | None = None,
    ) -> ProgressRecord:
        objective_id = getattr(objective, "objective_id", str(objective))
        record = ProgressRecord(
            objective_id=objective_id,
            status=status,
            detail=detail,
            result=result or {},
        )
        self.records.append(record)

        if self.session:

            async def persist() -> None:
                await self.save_record(record, self.session)

            record._await_hook = persist

        return record

    def get_history(self, objective_id: str | None = None) -> list[ProgressRecord]:
        if objective_id is None:
            return list(self.records)
        return [record for record in self.records if record.objective_id == objective_id]

    def get_latest(self, objective_id: str | None = None) -> ProgressRecord | None:
        history = self.get_history(objective_id)
        return history[-1] if history else None

    def summarize(self) -> dict[str, Any]:
        by_status: dict[str, int] = {}
        for record in self.records:
            by_status[record.status] = by_status.get(record.status, 0) + 1
        return {"total_records": len(self.records), "by_status": by_status}
