"""Repository for PerformanceMetric entities."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.enums import MetricType
from src.db.models import PerformanceMetric
from src.db.repositories.base import BaseRepository


class AnalyticsRepository(BaseRepository[PerformanceMetric]):
    """Repository for managing performance metrics."""

    def __init__(self, session: AsyncSession) -> None:
        super().__init__(PerformanceMetric, session)

    async def record_metric(
        self,
        user_id: UUID,
        metric_type: MetricType | str,
        value: float,
        session_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> PerformanceMetric:
        """Record a single performance metric."""
        metric = PerformanceMetric(
            user_id=user_id,
            session_id=session_id,
            metric_type=metric_type,
            value=value,
            metadata_=metadata,
        )
        self.session.add(metric)
        await self.session.flush()
        return metric

    async def get_average_metric(
        self,
        user_id: UUID,
        metric_type: MetricType | str,
        limit: int = 100,
    ) -> float:
        """Get the average value of a metric type over the last N records."""
        stmt = (
            select(func.avg(PerformanceMetric.value))
            .where(
                PerformanceMetric.user_id == user_id,
                PerformanceMetric.metric_type == metric_type,
            )
            .order_by(PerformanceMetric.recorded_at.desc())
            .limit(limit)
        )
        result = await self.session.execute(stmt)
        avg_val = result.scalar()
        return float(avg_val) if avg_val is not None else 0.0
