"""
Text chunking strategies for the RAG pipeline.

Supports recursive character splitting, semantic (paragraph-based) splitting,
and Markdown-aware splitting that respects document structure.
All strategies produce ``Chunk`` objects annotated with positional and token metadata.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache

import tiktoken

from src.config.logging import get_logger

logger = get_logger(__name__)

_ENCODING_NAME = "cl100k_base"


@lru_cache(maxsize=1)
def _get_encoding() -> tiktoken.Encoding:
    """Return the cached tiktoken encoding."""
    return tiktoken.get_encoding(_ENCODING_NAME)


def _count_tokens(text: str) -> int:
    """Count tokens in *text* using the cl100k_base encoding."""
    return len(_get_encoding().encode(text, disallowed_special=()))


class ChunkingStrategy(str, Enum):
    """Supported chunking strategies."""

    RECURSIVE = "recursive"
    SEMANTIC = "semantic"
    MARKDOWN = "markdown"


@dataclass(frozen=True, slots=True)
class ChunkMetadata:
    """Positional and token metadata for a single chunk.

    Attributes:
        start_pos: Character start offset in the original text.
        end_pos: Character end offset (exclusive) in the original text.
        token_count: Number of tokens in the chunk content.
    """

    start_pos: int
    end_pos: int
    token_count: int


@dataclass(frozen=True, slots=True)
class Chunk:
    """An individual chunk of text produced by a chunking strategy.

    Attributes:
        content: The textual content of the chunk.
        index: The zero-based index of this chunk in the sequence.
        metadata: Positional and token metadata.
    """

    content: str
    index: int
    metadata: ChunkMetadata


@dataclass
class TextChunker:
    """Stateless text chunker supporting multiple strategies.

    Usage::

        chunker = TextChunker()
        chunks = chunker.chunk_text(text, ChunkingStrategy.RECURSIVE, chunk_size=800)
    """

    # Default separators for recursive splitting (ordered by priority)
    _recursive_separators: list[str] = field(
        default_factory=lambda: ["\n\n", "\n", ". ", "! ", "? ", "; ", ", ", " "],
        repr=False,
    )

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    def chunk_text(
        self,
        text: str,
        strategy: ChunkingStrategy = ChunkingStrategy.RECURSIVE,
        chunk_size: int = 1000,
        overlap: int = 200,
    ) -> list[Chunk]:
        """Split *text* into chunks using the specified strategy.

        Args:
            text: The source text to chunk.
            strategy: One of ``RECURSIVE``, ``SEMANTIC``, or ``MARKDOWN``.
            chunk_size: Target maximum number of *tokens* per chunk.
            overlap: Number of overlapping *tokens* between consecutive chunks
                     (only used by RECURSIVE strategy).

        Returns:
            An ordered list of ``Chunk`` objects.
        """
        if not text or not text.strip():
            return []

        if strategy == ChunkingStrategy.RECURSIVE:
            return self._recursive_chunk(text, chunk_size, overlap)
        if strategy == ChunkingStrategy.SEMANTIC:
            return self._semantic_chunk(text, chunk_size)
        if strategy == ChunkingStrategy.MARKDOWN:
            return self.chunk_markdown(text, chunk_size)

        raise ValueError(f"Unknown chunking strategy: {strategy}")

    def chunk_markdown(self, text: str, chunk_size: int = 1000) -> list[Chunk]:
        """Split Markdown text respecting structural elements.

        Splits on headings (``# … ######``), horizontal rules, and fenced code
        blocks so that each section stays together whenever possible.  Sections
        that still exceed *chunk_size* tokens are recursively split.

        Args:
            text: Markdown-formatted text.
            chunk_size: Maximum tokens per chunk.

        Returns:
            An ordered list of ``Chunk`` objects.
        """
        if not text or not text.strip():
            return []

        sections = self._split_markdown_sections(text)
        chunks: list[Chunk] = []

        for section in sections:
            section_tokens = _count_tokens(section)
            if section_tokens <= chunk_size:
                chunks.append(self._make_chunk(section, len(chunks), text))
            else:
                # Section too large — recursively split it
                sub_chunks = self._recursive_chunk(section, chunk_size, overlap=100)
                for sc in sub_chunks:
                    chunks.append(
                        self._make_chunk(sc.content, len(chunks), text)
                    )

        logger.debug("markdown_chunking_complete", total_chunks=len(chunks))
        return chunks

    # --------------------------------------------------------------------- #
    # Recursive strategy
    # --------------------------------------------------------------------- #

    def _recursive_chunk(
        self, text: str, chunk_size: int, overlap: int
    ) -> list[Chunk]:
        """Recursively split text trying increasingly fine-grained separators."""
        raw_chunks = self._recursive_split(text, self._recursive_separators, chunk_size)
        # Merge very small pieces and apply overlap
        merged = self._merge_with_overlap(raw_chunks, chunk_size, overlap)
        return [self._make_chunk(c, idx, text) for idx, c in enumerate(merged)]

    def _recursive_split(
        self,
        text: str,
        separators: list[str],
        chunk_size: int,
    ) -> list[str]:
        """Core recursive split: try separators in order until pieces fit."""
        if _count_tokens(text) <= chunk_size:
            return [text]

        for sep in separators:
            parts = text.split(sep)
            if len(parts) == 1:
                continue  # separator not found, try the next one

            result: list[str] = []
            current = parts[0]
            for part in parts[1:]:
                candidate = current + sep + part
                if _count_tokens(candidate) <= chunk_size:
                    current = candidate
                else:
                    if current.strip():
                        result.append(current)
                    current = part
            if current.strip():
                result.append(current)

            if result:
                final: list[str] = []
                for piece in result:
                    if _count_tokens(piece) > chunk_size:
                        # Still too large — recurse with the remaining separators
                        remaining_seps = separators[separators.index(sep) + 1 :]
                        if remaining_seps:
                            final.extend(
                                self._recursive_split(piece, remaining_seps, chunk_size)
                            )
                        else:
                            # No more separators — force-split by characters
                            final.extend(self._force_split(piece, chunk_size))
                    else:
                        final.append(piece)
                return final

        # No separators matched at all — force character split
        return self._force_split(text, chunk_size)

    def _force_split(self, text: str, chunk_size: int) -> list[str]:
        """Force-split text into equal-sized token chunks as a last resort."""
        enc = _get_encoding()
        tokens = enc.encode(text, disallowed_special=())
        pieces: list[str] = []
        for i in range(0, len(tokens), chunk_size):
            decoded = enc.decode(tokens[i : i + chunk_size])
            if decoded.strip():
                pieces.append(decoded)
        return pieces

    def _merge_with_overlap(
        self,
        segments: list[str],
        chunk_size: int,
        overlap: int,
    ) -> list[str]:
        """Merge small adjacent segments and add token-level overlap between chunks."""
        if not segments:
            return []

        enc = _get_encoding()
        merged: list[str] = []
        current_tokens: list[int] = []

        for segment in segments:
            seg_tokens = enc.encode(segment, disallowed_special=())
            if current_tokens and len(current_tokens) + len(seg_tokens) > chunk_size:
                merged.append(enc.decode(current_tokens))
                # Keep the tail as overlap for the next chunk
                overlap_tokens = current_tokens[-overlap:] if overlap > 0 else []
                current_tokens = overlap_tokens + seg_tokens
            else:
                current_tokens.extend(seg_tokens)

        if current_tokens:
            merged.append(enc.decode(current_tokens))

        return merged

    # --------------------------------------------------------------------- #
    # Semantic strategy
    # --------------------------------------------------------------------- #

    def _semantic_chunk(self, text: str, chunk_size: int) -> list[Chunk]:
        """Split on paragraph boundaries (double newlines) and merge small paragraphs."""
        paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]

        if not paragraphs:
            return []

        merged_sections: list[str] = []
        current = paragraphs[0]

        for para in paragraphs[1:]:
            candidate = current + "\n\n" + para
            if _count_tokens(candidate) <= chunk_size:
                current = candidate
            else:
                merged_sections.append(current)
                current = para
        merged_sections.append(current)

        chunks: list[Chunk] = []
        for section in merged_sections:
            if _count_tokens(section) > chunk_size:
                sub_chunks = self._recursive_chunk(section, chunk_size, overlap=100)
                for sc in sub_chunks:
                    chunks.append(self._make_chunk(sc.content, len(chunks), text))
            else:
                chunks.append(self._make_chunk(section, len(chunks), text))

        logger.debug("semantic_chunking_complete", total_chunks=len(chunks))
        return chunks

    # --------------------------------------------------------------------- #
    # Markdown helpers
    # --------------------------------------------------------------------- #

    _MD_HEADING_RE = re.compile(r"^(#{1,6})\s", re.MULTILINE)
    _MD_HR_RE = re.compile(r"^(?:---|\*\*\*|___)\s*$", re.MULTILINE)
    _MD_FENCE_RE = re.compile(r"^```", re.MULTILINE)

    def _split_markdown_sections(self, text: str) -> list[str]:
        """Split Markdown by headings and horizontal rules, keeping fenced code blocks intact."""
        lines = text.split("\n")
        sections: list[str] = []
        current_lines: list[str] = []
        in_code_block = False

        for line in lines:
            # Track fenced code block boundaries
            if self._MD_FENCE_RE.match(line):
                in_code_block = not in_code_block
                current_lines.append(line)
                continue

            if in_code_block:
                current_lines.append(line)
                continue

            # Split on headings and horizontal rules (outside code blocks)
            is_heading = self._MD_HEADING_RE.match(line)
            is_hr = self._MD_HR_RE.match(line)

            if is_heading or is_hr:
                if current_lines:
                    joined = "\n".join(current_lines).strip()
                    if joined:
                        sections.append(joined)
                    current_lines = []
                if is_heading:
                    current_lines.append(line)
                # Horizontal rules are consumed as split markers
            else:
                current_lines.append(line)

        if current_lines:
            joined = "\n".join(current_lines).strip()
            if joined:
                sections.append(joined)

        return sections

    # --------------------------------------------------------------------- #
    # Utility
    # --------------------------------------------------------------------- #

    @staticmethod
    def _make_chunk(content: str, index: int, source_text: str) -> Chunk:
        """Create a Chunk with computed positional metadata."""
        content_stripped = content.strip()
        start_pos = source_text.find(content_stripped)
        if start_pos == -1:
            start_pos = 0
        end_pos = start_pos + len(content_stripped)
        return Chunk(
            content=content_stripped,
            index=index,
            metadata=ChunkMetadata(
                start_pos=start_pos,
                end_pos=end_pos,
                token_count=_count_tokens(content_stripped),
            ),
        )
