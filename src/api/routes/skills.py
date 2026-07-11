from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from src.config.logging import get_logger
from src.api.schemas.skill import SkillCreate, SkillUpdate, SkillResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/skills", tags=["Skills"])

@router.get("/", response_model=List[SkillResponse])
async def list_skills(skip: int = Query(0, ge=0), limit: int = Query(100, le=1000)) -> List[SkillResponse]:
    """List all skills with pagination."""
    logger.info(f"Listing skills: skip={skip}, limit={limit}")
    return []

@router.post("/", response_model=SkillResponse, status_code=201)
async def create_skill(skill_in: SkillCreate) -> SkillResponse:
    """Create a new skill."""
    logger.info(f"Creating skill: {skill_in.name}")
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{skill_id}", response_model=SkillResponse)
async def get_skill(skill_id: UUID) -> SkillResponse:
    """Get a specific skill by ID."""
    logger.info(f"Fetching skill: {skill_id}")
    raise HTTPException(status_code=404, detail="Skill not found")

@router.patch("/{skill_id}", response_model=SkillResponse)
async def update_skill(skill_id: UUID, skill_in: SkillUpdate) -> SkillResponse:
    """Update a skill by ID."""
    logger.info(f"Updating skill: {skill_id}")
    raise HTTPException(status_code=404, detail="Skill not found")

@router.delete("/{skill_id}", status_code=204)
async def delete_skill(skill_id: UUID) -> None:
    """Delete a skill by ID."""
    logger.info(f"Deleting skill: {skill_id}")
    raise HTTPException(status_code=404, detail="Skill not found")
