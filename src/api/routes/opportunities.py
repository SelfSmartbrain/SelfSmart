from __future__ import annotations

from typing import List
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from src.config.logging import get_logger
from src.api.schemas.projects import OpportunityCreate, OpportunityResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/opportunities", tags=["opportunities"])

@router.post("/", response_model=OpportunityResponse, status_code=201)
async def create_opportunity(opportunity: OpportunityCreate):
    logger.info("Creating opportunity")
    raise HTTPException(status_code=501, detail="Not implemented yet")

@router.get("/{opportunity_id}", response_model=OpportunityResponse)
async def get_opportunity(opportunity_id: UUID):
    logger.info(f"Fetching opportunity: {opportunity_id}")
    raise HTTPException(status_code=501, detail="Not implemented yet")

@router.get("/", response_model=List[OpportunityResponse])
async def list_opportunities():
    logger.info("Listing opportunities")
    return []
