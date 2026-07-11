"""
Memory-related API schemas.

Defines request/response models for memory storage, recall, and management.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class MemoryType(StrEnum):
    """Types of memory storage."""

    EPISODIC = "episodic"
    SEMANTIC = "semantic"
    PROCEDURAL = "procedural"


class MemoryCreate(BaseModel):
    """Request schema for storing a new memory."""

    content: str = Field(
        ...,
        min_length=1,
        max_length=50000,
        description="Memory content to store",
    )
    memory_type: MemoryType = Field(
        default=MemoryType.SEMANTIC,
        description="Type of memory",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata tags",
    )
    importance_score: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Importance score (0.0 to 1.0)",
    )


class MemoryRecall(BaseModel):
    """Request schema for recalling memories."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query for memory recall",
    )
    memory_type: MemoryType | None = Field(
        default=None,
        description="Filter by memory type",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of memories to return",
    )
    min_importance: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum importance score filter",
    )


class MemoryResponse(BaseModel):
    """Response schema for a memory record."""

    id: uuid.UUID
    content: str
    memory_type: MemoryType
    metadata: dict[str, Any] = Field(default_factory=dict)
    importance_score: float
    relevance_score: float = Field(
        default=0.0,
        description="Relevance to the recall query (0.0 to 1.0)",
    )
    access_count: int
    last_accessed: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class MemoryListResponse(BaseModel):
    """List of memory records."""

    memories: list[MemoryResponse]
    total: int
    query: str | None = None


class MemoryStats(BaseModel):
    """Memory system statistics."""

    total_memories: int
    episodic_count: int
    semantic_count: int
    procedural_count: int
    avg_importance: float
    oldest_memory: datetime | None
    newest_memory: datetime | None
