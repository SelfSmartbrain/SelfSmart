"""
Embedding service using the OpenAI text-embedding-3-large model.

Provides single-text and batch embedding generation with retry logic,
token counting to stay within model limits, and LRU caching for deduplication.
"""

from __future__ import annotations

import asyncio
import hashlib
from dataclasses import dataclass, field
from functools import lru_cache
from typing import TYPE_CHECKING

import tiktoken
from openai import AsyncOpenAI, RateLimitError
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from src.config.logging import get_logger
from src.config.settings import get_settings

if TYPE_CHECKING:
    pass

logger = get_logger(__name__)

# OpenAI embedding models use cl100k_base encoding
_ENCODING_NAME = "cl100k_base"
# text-embedding-3-large supports up to 8191 input tokens
_MAX_INPUT_TOKENS = 8191


@lru_cache(maxsize=1)
def _get_encoding() -> tiktoken.Encoding:
    """Return the cached tiktoken encoding for embedding token counting."""
    return tiktoken.get_encoding(_ENCODING_NAME)


def count_tokens(text: str) -> int:
    """Count the number of tokens in a text string using cl100k_base encoding.

    Args:
        text: The input text to tokenize.

    Returns:
        The number of tokens.
    """
    encoding = _get_encoding()
    return len(encoding.encode(text, disallowed_special=()))


def _truncate_to_token_limit(text: str, max_tokens: int = _MAX_INPUT_TOKENS) -> str:
    """Truncate text to fit within the token limit.

    Args:
        text: The input text.
        max_tokens: Maximum allowed tokens.

    Returns:
        The (possibly truncated) text that fits within the token limit.
    """
    encoding = _get_encoding()
    tokens = encoding.encode(text, disallowed_special=())
    if len(tokens) <= max_tokens:
        return text
    truncated_tokens = tokens[:max_tokens]
    return encoding.decode(truncated_tokens)


def _text_cache_key(text: str) -> str:
    """Generate a deterministic cache key for an input text.

    Args:
        text: The input text.

    Returns:
        A hex digest suitable as a dictionary key.
    """
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass
class EmbeddingService:
    """Async embedding service wrapping the OpenAI embeddings API.

    Supports single and batch embedding, with LRU caching, token-aware
    truncation, and exponential-backoff retry on rate-limit errors.

    Attributes:
        model: The OpenAI model name to use.
        dimensions: The dimensionality of the returned vectors.
    """

    model: str = field(default_factory=lambda: get_settings().embedding_model)
    dimensions: int = field(default_factory=lambda: get_settings().embedding_dimensions)
    _client: AsyncOpenAI = field(init=False, repr=False)
    _cache: dict[str, list[float]] = field(init=False, default_factory=dict, repr=False)
    _cache_max_size: int = field(default=2048, repr=False)

    def __post_init__(self) -> None:
        settings = get_settings()
        self._client = AsyncOpenAI(api_key=settings.openai_api_key.get_secret_value())
        logger.info(
            "embedding_service_initialized",
            model=self.model,
            dimensions=self.dimensions,
        )

    # --------------------------------------------------------------------- #
    # Public API
    # --------------------------------------------------------------------- #

    async def embed_text(self, text: str) -> list[float]:
        """Generate an embedding vector for a single text.

        The text is automatically truncated if it exceeds the model's 8191-token
        limit.  Results are cached in an in-memory LRU dictionary so that
        repeated calls with the same text avoid redundant API requests.

        Args:
            text: The input text to embed.

        Returns:
            A list of floats representing the embedding vector (length = self.dimensions).

        Raises:
            ValueError: If *text* is empty or contains only whitespace.
            openai.OpenAIError: On non-recoverable API errors.
        """
        text = text.strip()
        if not text:
            raise ValueError("Cannot embed empty text.")

        cache_key = _text_cache_key(text)
        if cache_key in self._cache:
            return self._cache[cache_key]

        safe_text = _truncate_to_token_limit(text)
        vector = await self._call_api([safe_text])
        embedding = vector[0]

        self._put_cache(cache_key, embedding)
        return embedding

    async def embed_batch(
        self,
        texts: list[str],
        batch_size: int = 100,
    ) -> list[list[float]]:
        """Generate embeddings for a batch of texts.

        Texts are processed in sub-batches of *batch_size* to stay within
        API rate limits.  Each text is individually truncated if needed, and
        the cache is consulted/updated per text.

        Args:
            texts: A list of strings to embed.
            batch_size: Maximum number of texts to send in one API call.

        Returns:
            A list of embedding vectors, one per input text, in the same order.

        Raises:
            ValueError: If *texts* is empty.
        """
        if not texts:
            raise ValueError("Cannot embed an empty list of texts.")

        results: list[list[float] | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        for idx, raw_text in enumerate(texts):
            text = raw_text.strip()
            if not text:
                raise ValueError(f"Text at index {idx} is empty after stripping.")
            cache_key = _text_cache_key(text)
            if cache_key in self._cache:
                results[idx] = self._cache[cache_key]
            else:
                uncached_indices.append(idx)
                uncached_texts.append(_truncate_to_token_limit(text))

        if uncached_texts:
            logger.info(
                "embedding_batch_request",
                total=len(texts),
                cached=len(texts) - len(uncached_texts),
                to_embed=len(uncached_texts),
            )
            all_vectors: list[list[float]] = []
            for start in range(0, len(uncached_texts), batch_size):
                chunk = uncached_texts[start : start + batch_size]
                vectors = await self._call_api(chunk)
                all_vectors.extend(vectors)
                # Small delay between sub-batches to be a good API citizen
                if start + batch_size < len(uncached_texts):
                    await asyncio.sleep(0.1)

            for vec_idx, original_idx in enumerate(uncached_indices):
                vector = all_vectors[vec_idx]
                results[original_idx] = vector
                # Cache the result keyed on the *original* (untrimmed-but-stripped) text
                original_text = texts[original_idx].strip()
                self._put_cache(_text_cache_key(original_text), vector)

        # At this point every slot in *results* must be filled.
        return [r for r in results if r is not None]  # type: ignore[misc]

    def clear_cache(self) -> None:
        """Clear the in-memory embedding cache."""
        self._cache.clear()
        logger.debug("embedding_cache_cleared")

    @property
    def cache_size(self) -> int:
        """Return the current number of cached embeddings."""
        return len(self._cache)

    # --------------------------------------------------------------------- #
    # Internal helpers
    # --------------------------------------------------------------------- #

    @retry(
        retry=retry_if_exception_type(RateLimitError),
        wait=wait_exponential(multiplier=1, min=1, max=60),
        stop=stop_after_attempt(6),
        reraise=True,
    )
    async def _call_api(self, texts: list[str]) -> list[list[float]]:
        """Call the OpenAI embeddings endpoint with retry on rate limits.

        Args:
            texts: Pre-processed texts (already truncated).

        Returns:
            A list of embedding vectors.
        """
        response = await self._client.embeddings.create(
            input=texts,
            model=self.model,
            dimensions=self.dimensions,
        )
        return [item.embedding for item in response.data]

    def _put_cache(self, key: str, value: list[float]) -> None:
        """Insert into the bounded cache, evicting the oldest entry if full."""
        if len(self._cache) >= self._cache_max_size:
            # Evict the first (oldest-inserted) key — dict preserves insertion order
            oldest_key = next(iter(self._cache))
            del self._cache[oldest_key]
        self._cache[key] = value
