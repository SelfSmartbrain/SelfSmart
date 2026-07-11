from __future__ import annotations

from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.schemas.capability import ReviewCreate, ReviewInDB, ReviewUpdate
from src.config.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/reviews", tags=["Reviews"])

async def get_db_session():
    yield None

@router.post("/", response_model=ReviewInDB, status_code=status.HTTP_201_CREATED)
async def create_review(
    review_in: ReviewCreate,
    session: Any = Depends(get_db_session)
) -> ReviewInDB:
    logger.info(f"Creating review for entity {review_in.entity_id}")
    raise HTTPException(status_code=501, detail="Not Implemented")

@router.get("/", response_model=List[ReviewInDB])
async def list_reviews(
    skip: int = 0,
    limit: int = 100,
    session: Any = Depends(get_db_session)
) -> List[ReviewInDB]:
    logger.info("Listing reviews")
    raise HTTPException(status_code=501, detail="Not Implemented")

@router.get("/{review_id}", response_model=ReviewInDB)
async def get_review(
    review_id: UUID,
    session: Any = Depends(get_db_session)
) -> ReviewInDB:
    logger.info(f"Fetching review {review_id}")
    raise HTTPException(status_code=501, detail="Not Implemented")

@router.patch("/{review_id}", response_model=ReviewInDB)
async def update_review(
    review_id: UUID,
    review_update: ReviewUpdate,
    session: Any = Depends(get_db_session)
) -> ReviewInDB:
    logger.info(f"Updating review {review_id}")
    raise HTTPException(status_code=501, detail="Not Implemented")

@router.delete("/{review_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_review(
    review_id: UUID,
    session: Any = Depends(get_db_session)
) -> None:
    logger.info(f"Deleting review {review_id}")
    raise HTTPException(status_code=501, detail="Not Implemented")
