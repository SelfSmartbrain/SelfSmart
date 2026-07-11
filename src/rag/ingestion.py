"""
Document ingestion pipeline for the RAG system.

Handles parsing, chunking, embedding, and storing documents in Qdrant with
metadata indexed in PostgreSQL.  Supports plain text, PDF, and URL sources.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import Column, DateTime, Integer, String, Text, text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped

from src.config.logging import get_logger
from src.config.settings import get_settings
from src.rag.chunking import ChunkingStrategy, TextChunker
from src.rag.embeddings import EmbeddingService
from src.rag.vector_store import VectorStoreManager

logger = get_logger(__name__)


# ------------------------------------------------------------------ #
# SQLAlchemy model for the document index in PostgreSQL
# ------------------------------------------------------------------ #


class _Base(DeclarativeBase):
    pass


class DocumentRecord(_Base):
    """PostgreSQL record tracking an ingested document."""

    __tablename__ = "ingested_documents"

    id: Mapped[str] = Column(String(64), primary_key=True)
    title: Mapped[str] = Column(String(512), nullable=False)
    source: Mapped[str] = Column(String(2048), nullable=False)
    source_type: Mapped[str] = Column(String(32), nullable=False)
    content_hash: Mapped[str] = Column(String(64), nullable=False, unique=True, index=True)
    chunk_count: Mapped[int] = Column(Integer, nullable=False, default=0)
    token_count: Mapped[int] = Column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )
    summary: Mapped[str | None] = Column(Text, nullable=True)


# ------------------------------------------------------------------ #
# Data models
# ------------------------------------------------------------------ #


class SourceType(str, Enum):
    """Known source types for ingested documents."""

    TEXT = "text"
    PDF = "pdf"
    URL = "url"
    MARKDOWN = "markdown"


@dataclass(frozen=True, slots=True)
class KnowledgeDocument:
    """Result of a successful document ingestion.

    Attributes:
        id: Unique document identifier.
        title: Human-readable title.
        source: Origin path / URL / label.
        source_type: The kind of source (text, pdf, url, markdown).
        chunk_count: Number of chunks stored.
        total_tokens: Sum of tokens across all chunks.
        created_at: UTC timestamp of ingestion.
    """

    id: str
    title: str
    source: str
    source_type: str
    chunk_count: int
    total_tokens: int
    created_at: datetime


# ------------------------------------------------------------------ #
# Ingestion pipeline
# ------------------------------------------------------------------ #


@dataclass
class IngestionPipeline:
    """End-to-end ingestion pipeline: parse → chunk → embed → store.

    Requires an initialised :class:`EmbeddingService` and
    :class:`VectorStoreManager`.  Call :meth:`initialize` once at startup to
    create the PostgreSQL index table.

    Usage::

        pipeline = IngestionPipeline(
            embedding_service=embedding_svc,
            vector_store=vsm,
        )
        await pipeline.initialize()
        doc = await pipeline.ingest_text(
            text="...",
            title="My Document",
            source="manual",
        )
    """

    embedding_service: EmbeddingService
    vector_store: VectorStoreManager
    _chunker: TextChunker = field(default_factory=TextChunker, repr=False)
    _engine: Any = field(init=False, repr=False, default=None)

    async def initialize(self) -> None:
        """Create the PostgreSQL index table if it does not exist."""
        settings = get_settings()
        self._engine = create_async_engine(settings.database_url, echo=False)
        async with self._engine.begin() as conn:
            await conn.run_sync(_Base.metadata.create_all)
        logger.info("ingestion_pipeline_initialized")

    async def close(self) -> None:
        """Dispose of the database engine."""
        if self._engine:
            await self._engine.dispose()

    # ------------------------------------------------------------------ #
    # Public ingestion methods
    # ------------------------------------------------------------------ #

    async def ingest_text(
        self,
        text_content: str,
        title: str,
        source: str = "manual",
        source_type: SourceType = SourceType.TEXT,
        metadata: dict[str, Any] | None = None,
        chunking_strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        on_progress: Any | None = None,
    ) -> KnowledgeDocument:
        """Ingest a plain-text document.

        Args:
            text_content: The raw text.
            title: Document title.
            source: Origin label (file path, name, etc.).
            source_type: Classification of the source.
            metadata: Extra metadata stored alongside each chunk.
            chunking_strategy: Which chunking strategy to use.
            chunk_size: Target tokens per chunk.
            chunk_overlap: Overlap tokens (for recursive).
            on_progress: Optional async callable ``(completed, total) -> None``.

        Returns:
            A :class:`KnowledgeDocument` descriptor.

        Raises:
            ValueError: If the text is empty or the document is a duplicate.
        """
        if not text_content or not text_content.strip():
            raise ValueError("Cannot ingest empty text.")

        content_hash = self._hash_content(text_content)
        await self._check_duplicate(content_hash)

        doc_id = str(uuid.uuid4())
        extra_meta = metadata or {}

        # 1. Chunk
        if source_type == SourceType.MARKDOWN or chunking_strategy == ChunkingStrategy.MARKDOWN:
            chunks = self._chunker.chunk_markdown(text_content, chunk_size)
        else:
            chunks = self._chunker.chunk_text(
                text_content, chunking_strategy, chunk_size, chunk_overlap
            )

        if not chunks:
            raise ValueError("Chunking produced zero chunks.")

        total_tokens = sum(c.metadata.token_count for c in chunks)
        total_chunks = len(chunks)

        # 2. Embed
        chunk_texts = [c.content for c in chunks]
        vectors = await self.embedding_service.embed_batch(chunk_texts)

        # 3. Store in Qdrant
        point_ids: list[str] = []
        payloads: list[dict[str, Any]] = []
        for idx, chunk in enumerate(chunks):
            point_id = f"{doc_id}::{idx}"
            point_ids.append(point_id)
            payloads.append(
                {
                    "document_id": doc_id,
                    "title": title,
                    "source": source,
                    "source_type": source_type.value,
                    "chunk_index": idx,
                    "content": chunk.content,
                    "token_count": chunk.metadata.token_count,
                    "start_pos": chunk.metadata.start_pos,
                    "end_pos": chunk.metadata.end_pos,
                    **extra_meta,
                }
            )
            if on_progress:
                await on_progress(idx + 1, total_chunks)

        await self.vector_store.upsert_batch("knowledge", point_ids, vectors, payloads)

        # 4. Index in PostgreSQL
        now = datetime.now(timezone.utc)
        await self._save_document_record(
            doc_id=doc_id,
            title=title,
            source=source,
            source_type=source_type.value,
            content_hash=content_hash,
            chunk_count=total_chunks,
            token_count=total_tokens,
            created_at=now,
        )

        logger.info(
            "document_ingested",
            doc_id=doc_id,
            title=title,
            chunks=total_chunks,
            tokens=total_tokens,
        )
        return KnowledgeDocument(
            id=doc_id,
            title=title,
            source=source,
            source_type=source_type.value,
            chunk_count=total_chunks,
            total_tokens=total_tokens,
            created_at=now,
        )

    async def ingest_pdf(
        self,
        file_path: str | Path | None = None,
        pdf_bytes: bytes | None = None,
        title: str = "Untitled PDF",
        metadata: dict[str, Any] | None = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        on_progress: Any | None = None,
    ) -> KnowledgeDocument:
        """Ingest a PDF document by extracting text and running the pipeline.

        Supply either *file_path* or *pdf_bytes*, not both.

        Args:
            file_path: Path to a PDF file on disk.
            pdf_bytes: Raw PDF bytes.
            title: Document title.
            metadata: Extra metadata.
            chunk_size: Target tokens per chunk.
            chunk_overlap: Overlap tokens.
            on_progress: Optional progress callback.

        Returns:
            A :class:`KnowledgeDocument` descriptor.
        """
        import pypdf  # noqa: PLC0415 – lazy import keeps module light

        if file_path and pdf_bytes:
            raise ValueError("Provide either file_path or pdf_bytes, not both.")
        if not file_path and not pdf_bytes:
            raise ValueError("Provide either file_path or pdf_bytes.")

        if file_path:
            path = Path(file_path)
            reader = pypdf.PdfReader(str(path))
            source = str(path)
        else:
            import io  # noqa: PLC0415

            reader = pypdf.PdfReader(io.BytesIO(pdf_bytes))  # type: ignore[arg-type]
            source = "uploaded_pdf"

        pages: list[str] = []
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                pages.append(page_text)

        full_text = "\n\n".join(pages)
        if not full_text.strip():
            raise ValueError("PDF contains no extractable text.")

        return await self.ingest_text(
            text_content=full_text,
            title=title,
            source=source,
            source_type=SourceType.PDF,
            metadata={**(metadata or {}), "page_count": len(reader.pages)},
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            on_progress=on_progress,
        )

    async def ingest_url(
        self,
        url: str,
        title: str | None = None,
        metadata: dict[str, Any] | None = None,
        chunk_size: int = 1000,
        chunk_overlap: int = 200,
        on_progress: Any | None = None,
    ) -> KnowledgeDocument:
        """Fetch a URL and ingest its text content.

        Performs a simple HTML-to-text conversion by stripping tags.

        Args:
            url: The URL to fetch.
            title: Document title (defaults to the URL).
            metadata: Extra metadata.
            chunk_size: Target tokens per chunk.
            chunk_overlap: Overlap tokens.
            on_progress: Optional progress callback.

        Returns:
            A :class:`KnowledgeDocument` descriptor.
        """
        async with httpx.AsyncClient(timeout=30, follow_redirects=True) as client:
            response = await client.get(url)
            response.raise_for_status()

        content_type = response.headers.get("content-type", "")
        raw_text = response.text

        # Simple HTML stripping
        if "html" in content_type.lower():
            raw_text = self._strip_html(raw_text)

        if not raw_text.strip():
            raise ValueError(f"No extractable text from URL: {url}")

        doc_title = title or url
        return await self.ingest_text(
            text_content=raw_text,
            title=doc_title,
            source=url,
            source_type=SourceType.URL,
            metadata={**(metadata or {}), "url": url},
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            on_progress=on_progress,
        )

    # ------------------------------------------------------------------ #
    # Helpers
    # ------------------------------------------------------------------ #

    @staticmethod
    def _hash_content(content: str) -> str:
        """Return a SHA-256 hex digest for deduplication."""
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    async def _check_duplicate(self, content_hash: str) -> None:
        """Raise ``ValueError`` if a document with the same content hash already exists."""
        if not self._engine:
            return  # Gracefully skip if PG is not initialised yet

        async with AsyncSession(self._engine) as session:
            result = await session.execute(
                text("SELECT id FROM ingested_documents WHERE content_hash = :h"),
                {"h": content_hash},
            )
            existing = result.scalar_one_or_none()
            if existing:
                raise ValueError(
                    f"Duplicate document detected — existing document id: {existing}"
                )

    async def _save_document_record(
        self,
        doc_id: str,
        title: str,
        source: str,
        source_type: str,
        content_hash: str,
        chunk_count: int,
        token_count: int,
        created_at: datetime,
    ) -> None:
        """Persist a document index record in PostgreSQL."""
        if not self._engine:
            logger.warning("pg_engine_not_available_skipping_record")
            return

        async with AsyncSession(self._engine) as session:
            async with session.begin():
                record = DocumentRecord(
                    id=doc_id,
                    title=title,
                    source=source,
                    source_type=source_type,
                    content_hash=content_hash,
                    chunk_count=chunk_count,
                    token_count=token_count,
                    created_at=created_at,
                )
                session.add(record)

    @staticmethod
    def _strip_html(html: str) -> str:
        """Naïve but fast HTML-to-text conversion."""
        import re  # noqa: PLC0415

        # Remove script and style blocks
        html = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html, flags=re.DOTALL | re.IGNORECASE)
        # Remove all tags
        text = re.sub(r"<[^>]+>", " ", html)
        # Collapse whitespace
        text = re.sub(r"\s+", " ", text)
        return text.strip()
