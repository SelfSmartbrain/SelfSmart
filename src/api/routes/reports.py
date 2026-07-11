from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from src.config.logging import get_logger
from src.api.schemas.report import ReportResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/reports", tags=["Reports"])

@router.get("/daily", response_model=ReportResponse)
async def get_daily_report() -> ReportResponse:
    """Get the daily system report."""
    logger.info("Fetching daily report")
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/weekly", response_model=ReportResponse)
async def get_weekly_report() -> ReportResponse:
    """Get the weekly system report."""
    logger.info("Fetching weekly report")
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/monthly", response_model=ReportResponse)
async def get_monthly_report() -> ReportResponse:
    """Get the monthly system report."""
    logger.info("Fetching monthly report")
    raise HTTPException(status_code=501, detail="Not implemented")
