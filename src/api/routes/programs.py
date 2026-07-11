from __future__ import annotations

from typing import Any, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status

from src.api.schemas.capability import ProgramCreate, ProgramInDB, ProgramUpdate
from src.config.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/programs", tags=["Programs"])

async def get_db_session():
    yield None

@router.post("/", response_model=ProgramInDB, status_code=status.HTTP_201_CREATED)
async def create_program(
    program_in: ProgramCreate,
    session: Any = Depends(get_db_session)
) -> ProgramInDB:
    logger.info(f"Creating program {program_in.title}")
    raise HTTPException(status_code=501, detail="Not Implemented")

@router.get("/", response_model=List[ProgramInDB])
async def list_programs(
    skip: int = 0,
    limit: int = 100,
    session: Any = Depends(get_db_session)
) -> List[ProgramInDB]:
    logger.info("Listing programs")
    raise HTTPException(status_code=501, detail="Not Implemented")

@router.get("/{program_id}", response_model=ProgramInDB)
async def get_program(
    program_id: UUID,
    session: Any = Depends(get_db_session)
) -> ProgramInDB:
    logger.info(f"Fetching program {program_id}")
    raise HTTPException(status_code=501, detail="Not Implemented")

@router.patch("/{program_id}", response_model=ProgramInDB)
async def update_program(
    program_id: UUID,
    program_update: ProgramUpdate,
    session: Any = Depends(get_db_session)
) -> ProgramInDB:
    logger.info(f"Updating program {program_id}")
    raise HTTPException(status_code=501, detail="Not Implemented")

@router.delete("/{program_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_program(
    program_id: UUID,
    session: Any = Depends(get_db_session)
) -> None:
    logger.info(f"Deleting program {program_id}")
    raise HTTPException(status_code=501, detail="Not Implemented")
