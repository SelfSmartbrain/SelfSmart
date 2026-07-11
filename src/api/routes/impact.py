from __future__ import annotations

from typing import List
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from src.config.logging import get_logger
from src.api.schemas.projects import ImpactAnalysisCreate, ImpactAnalysisResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/impact", tags=["impact"])

@router.post("/analyses", response_model=ImpactAnalysisResponse, status_code=201)
async def create_impact_analysis(analysis: ImpactAnalysisCreate):
    logger.info("Creating impact analysis")
    raise HTTPException(status_code=501, detail="Not implemented yet")

@router.get("/analyses/{analysis_id}", response_model=ImpactAnalysisResponse)
async def get_impact_analysis(analysis_id: UUID):
    logger.info(f"Fetching impact analysis: {analysis_id}")
    raise HTTPException(status_code=501, detail="Not implemented yet")

@router.get("/analyses/project/{project_id}", response_model=List[ImpactAnalysisResponse])
async def get_project_impact_analyses(project_id: UUID):
    logger.info(f"Listing impact analyses for project: {project_id}")
    return []
