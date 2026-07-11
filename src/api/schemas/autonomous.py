"""Pydantic schemas for autonomous research endpoints."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from src.db.enums import ResearchTrackStatus, PortfolioStatus, GoalStatus


class KnowledgeGapResponse(BaseModel):
    """Schema for returning a Knowledge Gap."""
    id: UUID
    domain: str
    description: str
    importance: float
    confidence: float
    is_resolved: bool

    class Config:
        from_attributes = True


class GeneratedGoalResponse(BaseModel):
    """Schema for returning a Generated Goal."""
    id: UUID
    gap_id: UUID | None
    title: str
    description: str
    status: GoalStatus
    curiosity_score: float

    class Config:
        from_attributes = True


class ResearchTrackResponse(BaseModel):
    """Schema for returning a Research Track."""
    id: UUID
    goal_id: UUID
    title: str
    status: ResearchTrackStatus
    progress_percentage: float

    class Config:
        from_attributes = True


class ResearchPortfolioResponse(BaseModel):
    """Schema for returning a Research Portfolio."""
    id: UUID
    name: str
    description: str
    status: PortfolioStatus
    overall_progress: float

    class Config:
        from_attributes = True


class GenerateGoalsRequest(BaseModel):
    """Request payload to manually trigger goal generation."""
    limit: int = 5
