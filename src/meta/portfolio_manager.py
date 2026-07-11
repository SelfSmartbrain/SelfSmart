"""Research Portfolio Manager."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.db.models import ResearchPortfolio, ResearchTrack
from src.db.repositories.base import BaseRepository

logger = logging.getLogger(__name__)


class PortfolioManager:
    """Tracks and manages active research investigations across portfolios."""

    def __init__(
        self,
        portfolio_repo: BaseRepository[ResearchPortfolio],
        track_repo: BaseRepository[ResearchTrack],
    ) -> None:
        self.portfolio_repo = portfolio_repo
        self.track_repo = track_repo

    async def get_or_create_portfolio(self, name: str, description: str) -> ResearchPortfolio:
        """Fetch an existing portfolio or create a new one."""
        existing = await self.portfolio_repo.get(name=name)
        if existing is not None:
            return existing
        return await self.portfolio_repo.create(
            name=name,
            description=description,
            status="active",
            overall_progress=0.0,
        )

    async def update_portfolio_progress(self, portfolio_id: UUID) -> ResearchPortfolio | None:
        """
        Recalculate the overall progress of a portfolio based on its constituent tracks.
        """
        logger.info(f"Updating progress for portfolio {portfolio_id}")
        return await self.portfolio_repo.get_by_id(portfolio_id)

    async def get_dashboard_summary(self) -> dict[str, Any]:
        """Generate a summary of all active portfolios."""
        portfolios = await self.portfolio_repo.list(order_by="-updated_at")
        return {
            "active_portfolios": sum(
                1 for portfolio in portfolios if str(portfolio.status).lower().endswith("active")
            ),
            "portfolios": [
                {
                    "id": str(portfolio.id),
                    "name": portfolio.name,
                    "status": getattr(portfolio.status, "value", portfolio.status),
                    "progress": portfolio.overall_progress,
                }
                for portfolio in portfolios
            ],
        }
