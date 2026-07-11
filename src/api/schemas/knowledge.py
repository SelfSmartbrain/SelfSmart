"""
Knowledge-related API schemas.

Defines request/response models for knowledge ingestion and search.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class SourceType(StrEnum):
    """Knowledge source types."""

    ARXIV = "arxiv"
    WEB = "web"
    WIKIPEDIA = "wikipedia"
    PDF = "pdf"
    MANUAL = "manual"


class KnowledgeIngest(BaseModel):
    """Request schema for ingesting knowledge."""

    content: str | None = Field(
        default=None,
        max_length=500000,
        description="Raw text content to ingest",
    )
    url: str | None = Field(
        default=None,
        max_length=2048,
        description="URL to fetch and ingest content from",
    )
    title: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Document title",
    )
    source_type: SourceType = Field(
        default=SourceType.MANUAL,
        description="Source type of the knowledge",
    )
    metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="Additional metadata",
    )

    def model_post_init(self, __context: Any) -> None:
        """Validate that at least one of content or url is provided."""
        if not self.content and not self.url:
            raise ValueError("Either 'content' or 'url' must be provided")


class KnowledgeSearch(BaseModel):
    """Request schema for searching knowledge."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query",
    )
    source_type: SourceType | None = Field(
        default=None,
        description="Filter by source type",
    )
    limit: int = Field(
        default=10,
        ge=1,
        le=50,
        description="Maximum number of results",
    )
    score_threshold: float = Field(
        default=0.5,
        ge=0.0,
        le=1.0,
        description="Minimum relevance score",
    )


class KnowledgeChunkResponse(BaseModel):
    """A single knowledge chunk result."""

    chunk_id: str
    content: str
    score: float
    document_id: uuid.UUID | None = None
    document_title: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class KnowledgeResponse(BaseModel):
    """Response schema for a knowledge document."""

    id: uuid.UUID
    title: str
    source: str
    source_type: SourceType
    chunk_count: int
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime

    model_config = {"from_attributes": True}


class KnowledgeSearchResponse(BaseModel):
    """Search results for knowledge queries."""

    results: list[KnowledgeChunkResponse]
    total: int
    query: str
