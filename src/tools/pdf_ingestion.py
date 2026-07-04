"""
PDF ingestion tool for the Autonomous Agent Platform.

Extracts text content from PDF files using ``pypdf``.  Returns page-level
text along with document metadata (page count, author, title, etc.).
Handles encrypted PDFs gracefully.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

from pydantic import BaseModel, Field
from pypdf import PdfReader
from pypdf.errors import PdfReadError

from src.config.logging import get_logger
from src.tools.base import AgentTool, ToolExecutionError

logger = get_logger(__name__)

# Maximum PDF file size we'll attempt to process (100 MB)
_MAX_FILE_SIZE_BYTES = 100 * 1024 * 1024


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class PDFIngestionInput(BaseModel):
    """Input schema for PDFIngestionTool."""

    file_path: str = Field(
        ...,
        min_length=1,
        description="Absolute or relative path to the PDF file",
    )


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

class PDFIngestionTool(AgentTool):
    """Extract text content from a PDF document.

    Uses ``pypdf`` to read PDF files and extract text page-by-page.
    Returns the extracted text alongside document metadata such as
    author, title, creator, and page count.

    Encrypted PDFs are detected and a clear error message is returned
    rather than raising an exception.

    Example usage::

        tool = PDFIngestionTool()
        result = await tool._arun(file_path="/data/paper.pdf")
    """

    name: str = "pdf_ingestion"
    description: str = (
        "Extract text content from PDF files. Returns extracted text "
        "with page numbers and document metadata."
    )
    args_schema: type[BaseModel] = PDFIngestionInput
    timeout_seconds: float = 120.0
    max_retries: int = 1  # PDF reading is deterministic — little value in retrying

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        """Extract text from a PDF file.

        Args:
            **kwargs: Validated fields from :class:`PDFIngestionInput`.

        Returns:
            A dict with ``file_path``, ``metadata``, ``pages`` (list of
            dicts with ``page_number`` and ``text``), ``total_pages``,
            and ``total_characters``.

        Raises:
            ToolExecutionError: If the file is missing, too large,
                encrypted, or otherwise unreadable.
        """
        file_path: str = kwargs["file_path"]
        log = logger.bind(tool=self.name, file_path=file_path)
        log.debug("pdf_ingestion.start")

        # --- Validate file existence and size ---
        if not os.path.isfile(file_path):
            raise ToolExecutionError(
                tool_name=self.name,
                message=f"File not found: {file_path}",
            )

        file_size = os.path.getsize(file_path)
        if file_size > _MAX_FILE_SIZE_BYTES:
            raise ToolExecutionError(
                tool_name=self.name,
                message=(
                    f"File too large ({file_size / (1024 * 1024):.1f} MB). "
                    f"Maximum allowed size is {_MAX_FILE_SIZE_BYTES / (1024 * 1024):.0f} MB."
                ),
            )

        # Run the synchronous PDF reading in a thread pool to avoid blocking
        def _sync_pdf_read():
            # --- Read the PDF ---
            try:
                reader = PdfReader(file_path)
            except PdfReadError as exc:
                raise ToolExecutionError(
                    tool_name=self.name,
                    message=f"Failed to parse PDF: {exc}",
                    cause=exc,
                ) from exc

            # --- Handle encryption ---
            if reader.is_encrypted:
                try:
                    # Attempt decryption with an empty password (common for
                    # restriction-only encrypted PDFs).
                    if not reader.decrypt(""):
                        return {
                            "file_path": file_path,
                            "error": (
                                "PDF is encrypted with a non-empty password. "
                                "Cannot extract text without the correct password."
                            ),
                            "metadata": {},
                            "pages": [],
                            "total_pages": 0,
                            "total_characters": 0,
                        }
                except Exception:
                    return {
                        "file_path": file_path,
                        "error": "PDF is encrypted and could not be decrypted.",
                        "metadata": {},
                        "pages": [],
                        "total_pages": 0,
                        "total_characters": 0,
                    }

            # --- Extract metadata ---
            raw_meta = reader.metadata
            metadata: dict[str, Any] = {}
            if raw_meta:
                metadata = {
                    "title": raw_meta.title or None,
                    "author": raw_meta.author or None,
                    "subject": raw_meta.subject or None,
                    "creator": raw_meta.creator or None,
                    "producer": raw_meta.producer or None,
                    "creation_date": str(raw_meta.creation_date) if raw_meta.creation_date else None,
                    "modification_date": (
                        str(raw_meta.modification_date) if raw_meta.modification_date else None
                    ),
                }

            # --- Extract text page by page ---
            pages: list[dict[str, Any]] = []
            total_chars = 0

            for page_num, page in enumerate(reader.pages, start=1):
                try:
                    text = page.extract_text() or ""
                except Exception as exc:
                    log.warning(
                        "pdf_ingestion.page_error",
                        page=page_num,
                        error=str(exc),
                    )
                    text = f"[Error extracting page {page_num}: {exc}]"

                total_chars += len(text)
                pages.append(
                    {
                        "page_number": page_num,
                        "text": text,
                        "character_count": len(text),
                    }
                )

            result: dict[str, Any] = {
                "file_path": file_path,
                "metadata": metadata,
                "pages": pages,
                "total_pages": len(pages),
                "total_characters": total_chars,
                "file_size_bytes": file_size,
            }

            return result

        result = await asyncio.to_thread(_sync_pdf_read)

        log.info(
            "pdf_ingestion.complete",
            total_pages=result.get("total_pages", 0),
            total_characters=result.get("total_characters", 0),
        )

        return result


PdfIngestionTool = PDFIngestionTool
