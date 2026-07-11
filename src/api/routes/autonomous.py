"""Autonomous Research API Routes."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.agents.goal_generator import GoalGenerator
from src.api.schemas.autonomous import (
    GeneratedGoalResponse,
    GenerateGoalsRequest,
    KnowledgeGapResponse,
    ResearchPortfolioResponse,
    ResearchTrackResponse,
)
from src.db.models import GeneratedGoal, KnowledgeGap, ResearchPortfolio, ResearchTrack
from src.db.repositories.base import BaseRepository
from src.db.session import get_session

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/autonomous", tags=["autonomous"])


@router.get("/gaps", response_model=list[KnowledgeGapResponse])
async def list_knowledge_gaps(
    db: AsyncSession = Depends(get_session),
) -> list[KnowledgeGap]:
    """List all detected knowledge gaps."""
    result = await db.execute(select(KnowledgeGap).order_by(KnowledgeGap.created_at.desc()))
    return list(result.scalars().all())


@router.get("/goals", response_model=list[GeneratedGoalResponse])
async def list_generated_goals(
    db: AsyncSession = Depends(get_session),
) -> list[GeneratedGoal]:
    """List all autonomously generated goals."""
    result = await db.execute(select(GeneratedGoal).order_by(GeneratedGoal.created_at.desc()))
    return list(result.scalars().all())


@router.post("/goals/generate")
async def generate_goals(
    request: GenerateGoalsRequest,
    db: AsyncSession = Depends(get_session),
) -> dict[str, int]:
    """Generate goals for the highest-value unresolved knowledge gaps."""
    result = await db.execute(
        select(KnowledgeGap)
        .where(KnowledgeGap.is_resolved.is_(False))
        .order_by(KnowledgeGap.importance.desc(), KnowledgeGap.confidence.desc())
        .limit(max(1, min(request.limit, 100)))
    )
    gaps = list(result.scalars().all())
    generator = GoalGenerator(BaseRepository(GeneratedGoal, db))
    created = 0
    for gap in gaps:
        curiosity_score = max(
            0.0,
            min(1.0, (gap.importance + gap.confidence) / 2),
        )
        if await generator.generate_from_gap(gap, curiosity_score) is not None:
            created += 1
    await db.commit()
    return {"requested": request.limit, "considered": len(gaps), "created": created}


@router.get("/tracks", response_model=list[ResearchTrackResponse])
async def list_research_tracks(
    db: AsyncSession = Depends(get_session),
) -> list[ResearchTrack]:
    """List all active research tracks."""
    result = await db.execute(select(ResearchTrack).order_by(ResearchTrack.created_at.desc()))
    return list(result.scalars().all())


@router.get("/portfolios", response_model=list[ResearchPortfolioResponse])
async def list_portfolios(
    db: AsyncSession = Depends(get_session),
) -> list[ResearchPortfolio]:
    """List all research portfolios."""
    result = await db.execute(
        select(ResearchPortfolio).order_by(ResearchPortfolio.created_at.desc())
    )
    return list(result.scalars().all())
