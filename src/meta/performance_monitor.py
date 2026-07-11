"""Performance Monitor component."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.db.enums import MetricType
from src.db.repositories.analytics_repo import AnalyticsRepository

logger = logging.getLogger(__name__)


class PerformanceMonitor:
    """Logs and tracks performance metrics across the system."""

    def __init__(self, analytics_repo: AnalyticsRepository) -> None:
        self.repo = analytics_repo

    async def log_metric(
        self,
        user_id: UUID,
        metric_type: MetricType | str,
        value: float,
        session_id: UUID | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Log a specific metric asynchronously."""
        try:
            await self.repo.record_metric(
                user_id=user_id,
                metric_type=metric_type,
                value=value,
                session_id=session_id,
                metadata=metadata,
            )
            logger.debug(f"Logged metric {metric_type}: {value}")
        except Exception as e:
            logger.error(f"Failed to log metric {metric_type}: {e}")

    async def get_performance_summary(self, user_id: UUID) -> dict[str, float]:
        """Get an aggregated summary of recent system performance."""
        summary = {}
        for m_type in MetricType:
            avg_val = await self.repo.get_average_metric(user_id=user_id, metric_type=m_type.value)
            summary[m_type.value] = avg_val
            
        return summary
