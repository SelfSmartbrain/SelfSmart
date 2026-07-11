from __future__ import annotations

from typing import List
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Depends
from src.config.logging import get_logger
from src.api.schemas.strategy import StrategyCreate, StrategyUpdate, StrategyResponse

logger = get_logger(__name__)
router = APIRouter(prefix="/strategies", tags=["Strategies"])

@router.get("/", response_model=List[StrategyResponse])
async def list_strategies(skip: int = Query(0, ge=0), limit: int = Query(100, le=1000)) -> List[StrategyResponse]:
    """List all strategies with pagination."""
    logger.info(f"Listing strategies: skip={skip}, limit={limit}")
    return []

@router.post("/", response_model=StrategyResponse, status_code=201)
async def create_strategy(strategy_in: StrategyCreate) -> StrategyResponse:
    """Create a new strategy."""
    logger.info(f"Creating strategy: {strategy_in.name}")
    raise HTTPException(status_code=501, detail="Not implemented")

@router.get("/{strategy_id}", response_model=StrategyResponse)
async def get_strategy(strategy_id: UUID) -> StrategyResponse:
    """Get a specific strategy by ID."""
    logger.info(f"Fetching strategy: {strategy_id}")
    raise HTTPException(status_code=404, detail="Strategy not found")

@router.patch("/{strategy_id}", response_model=StrategyResponse)
async def update_strategy(strategy_id: UUID, strategy_in: StrategyUpdate) -> StrategyResponse:
    """Update a strategy by ID."""
    logger.info(f"Updating strategy: {strategy_id}")
    raise HTTPException(status_code=404, detail="Strategy not found")

@router.delete("/{strategy_id}", status_code=204)
async def delete_strategy(strategy_id: UUID) -> None:
    """Delete a strategy by ID."""
    logger.info(f"Deleting strategy: {strategy_id}")
    raise HTTPException(status_code=404, detail="Strategy not found")
