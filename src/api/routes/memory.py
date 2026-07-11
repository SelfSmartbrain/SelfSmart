"""
Memory endpoints.

Provides store, recall, and management operations for the memory system.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, HTTPException, status

from src.api.dependencies import CurrentUser, DB_MemoryRepo
from src.api.schemas.memory import (
    MemoryCreate,
    MemoryRecall,
    MemoryResponse,
    MemoryListResponse,
    MemoryStats,
)
from src.config.logging import get_logger

logger = get_logger(__name__)

router = APIRouter()


@router.post(
    "/store",
    response_model=MemoryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Store a new memory",
)
async def store_memory(
    body: MemoryCreate,
    user: CurrentUser,
    memory_repo: DB_MemoryRepo,
) -> MemoryResponse:
    """Store a new memory entry in the long-term memory system."""
    from src.db.enums import MemoryType as DBMemoryType
    from datetime import datetime, timezone

    memory = await memory_repo.store_memory(
        user_id=user.id,
        content=body.content,
        memory_type=DBMemoryType(body.memory_type.value.upper()),
        metadata=body.metadata,
        importance_score=body.importance_score,
    )

    return MemoryResponse(
        id=memory.id,
        content=memory.content,
        memory_type=body.memory_type,
        metadata=memory.metadata or {},
        importance_score=memory.importance_score,
        relevance_score=0.0,
        access_count=memory.access_count,
        last_accessed=memory.last_accessed,
        created_at=memory.created_at,
    )


@router.post(
    "/recall",
    response_model=MemoryListResponse,
    summary="Recall memories by query",
)
async def recall_memories(
    body: MemoryRecall,
    user: CurrentUser,
    memory_repo: DB_MemoryRepo,
) -> MemoryListResponse:
    """
    Search memories using semantic similarity.

    Note: This endpoint uses DB-based search for metadata filtering.
    Full semantic recall (vector search) is handled by the agent pipeline.
    """
    from src.db.enums import MemoryType as DBMemoryType

    memory_type = DBMemoryType(body.memory_type.value.upper()) if body.memory_type else None

    memories = await memory_repo.search_by_type(
        user_id=user.id,
        memory_type=memory_type,
        limit=body.limit,
    )

    results = [
        MemoryResponse(
            id=m.id,
            content=m.content,
            memory_type=m.memory_type.value.lower(),
            metadata=m.metadata or {},
            importance_score=m.importance_score,
            relevance_score=0.0,
            access_count=m.access_count,
            last_accessed=m.last_accessed,
            created_at=m.created_at,
        )
        for m in memories
    ]

    return MemoryListResponse(
        memories=results,
        total=len(results),
        query=body.query,
    )


@router.get(
    "/{memory_id}",
    response_model=MemoryResponse,
    summary="Get a specific memory",
)
async def get_memory(
    memory_id: uuid.UUID,
    user: CurrentUser,
    memory_repo: DB_MemoryRepo,
) -> MemoryResponse:
    """Retrieve a specific memory by its ID."""
    memory = await memory_repo.get_memory(memory_id)
    if not memory:
        raise HTTPException(status_code=404, detail="Memory not found")

    return MemoryResponse(
        id=memory.id,
        content=memory.content,
        memory_type=memory.memory_type.value.lower(),
        metadata=memory.metadata or {},
        importance_score=memory.importance_score,
        relevance_score=0.0,
        access_count=memory.access_count,
        last_accessed=memory.last_accessed,
        created_at=memory.created_at,
    )


@router.delete(
    "/{memory_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a memory",
)
async def delete_memory(
    memory_id: uuid.UUID,
    user: CurrentUser,
    memory_repo: DB_MemoryRepo,
) -> None:
    """Delete a specific memory by its ID."""
    await memory_repo.delete_memory(memory_id)
