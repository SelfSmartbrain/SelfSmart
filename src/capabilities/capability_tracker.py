from __future__ import annotations
from datetime import datetime
from uuid import UUID, uuid4
from typing import List, Optional
from pydantic import BaseModel, Field
from src.config.logging import get_logger
from fastapi import APIRouter, HTTPException, Depends

logger = get_logger(__name__)
router = APIRouter(prefix="/capability/tracker", tags=["capability-tracker"])

class CapabilityRecord(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    model_id: UUID
    generation: int
    capability_name: str
    score: float
    recorded_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {"from_attributes": True}

@router.post("/", response_model=CapabilityRecord)
async def track_capability(record: CapabilityRecord) -> CapabilityRecord:
    logger.info(f"Tracking capability {record.capability_name} for model {record.model_id}")
    # In a real app, save to database
    return record

@router.get("/{model_id}", response_model=List[CapabilityRecord])
async def get_capabilities(model_id: UUID) -> List[CapabilityRecord]:
    logger.info(f"Fetching capabilities for {model_id}")
    return []
