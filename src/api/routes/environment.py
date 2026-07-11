from __future__ import annotations

from typing import List
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends
from src.config.logging import get_logger
from src.api.schemas.projects import EnvironmentContextCreate, EnvironmentContextResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/environment", tags=["environment"])

@router.post("/contexts", response_model=EnvironmentContextResponse, status_code=201)
async def create_environment_context(context: EnvironmentContextCreate):
    logger.info("Creating environment context")
    raise HTTPException(status_code=501, detail="Not implemented yet")

@router.get("/contexts/{context_id}", response_model=EnvironmentContextResponse)
async def get_environment_context(context_id: UUID):
    logger.info(f"Fetching environment context: {context_id}")
    raise HTTPException(status_code=501, detail="Not implemented yet")

@router.get("/contexts", response_model=List[EnvironmentContextResponse])
async def list_environment_contexts():
    logger.info("Listing environment contexts")
    return []
