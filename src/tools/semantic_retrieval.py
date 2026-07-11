"""
Semantic retrieval tool for the Autonomous Agent Platform.

Queries a Qdrant vector store for semantically relevant knowledge
chunks.  Uses the platform's EmbeddingService (OpenAI) to encode the
query, then performs a nearest-neighbour search.
"""

from __future__ import annotations

from typing import Any

import httpx
from pydantic import BaseModel, Field
from qdrant_client import AsyncQdrantClient
from qdrant_client.http.models import ScoredPoint

from src.config.logging import get_logger
from src.config.settings import get_settings
from src.tools.base import AgentTool, ToolExecutionError

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class SemanticRetrievalInput(BaseModel):
    """Input schema for SemanticRetrievalTool."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=2000,
        description="Natural-language query to search for",
    )
    collection: str = Field(
        default="knowledge",
        min_length=1,
        max_length=128,
        description="Qdrant collection name to search",
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of results to return",
    )
    score_threshold: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Minimum similarity score threshold (0.0 = no filter)",
    )


# ---------------------------------------------------------------------------
# Lightweight embedding helper
# ---------------------------------------------------------------------------

class _EmbeddingService:
    """Minimal async wrapper around the OpenAI Embeddings API.

    Encapsulates a single-purpose ``embed`` method so the retrieval
    tool doesn't depend on a heavyweight service layer.
    """

    def __init__(self, api_key: str, model: str, dimensions: int) -> None:
        self._api_key = api_key
        self._model = model
        self._dimensions = dimensions
        self._url = "https://api.openai.com/v1/embeddings"

    async def embed(self, text: str) -> list[float]:
        """Embed a single text string.

        Args:
            text: Input text to embed.

        Returns:
            A list of floats representing the embedding vector.

        Raises:
            ToolExecutionError: On API failure.
        """
        headers = {
            "Authorization": f"Bearer {self._api_key}",
            "Content-Type": "application/json",
        }
        payload: dict[str, Any] = {
            "input": text,
            "model": self._model,
            "dimensions": self._dimensions,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(self._url, json=payload, headers=headers)

            if resp.status_code != 200:
                raise ToolExecutionError(
                    tool_name="semantic_retrieval",
                    message=f"Embedding API error ({resp.status_code}): {resp.text[:500]}",
                )

            data = resp.json()
            return data["data"][0]["embedding"]


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

class SemanticRetrievalTool(AgentTool):
    """Query the Qdrant vector store for semantically relevant knowledge.

    The tool embeds the query using OpenAI's embedding model and
    performs a nearest-neighbour search against the specified Qdrant
    collection.  Results are ranked by cosine similarity and returned
    with their content, score, and associated metadata.

    Example usage::

        tool = SemanticRetrievalTool()
        result = await tool._arun(
            query="How does attention work in transformers?",
            collection="knowledge",
            limit=5,
        )
    """

    name: str = "semantic_retrieval"
    description: str = (
        "Query the Qdrant vector store for relevant knowledge. "
        "Returns ranked results with content, similarity score, and metadata."
    )
    args_schema: type[BaseModel] = SemanticRetrievalInput
    timeout_seconds: float = 30.0

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        """Embed the query and search the vector store.

        Args:
            **kwargs: Validated fields from :class:`SemanticRetrievalInput`.

        Returns:
            A dict with ``query``, ``collection``, ``results`` (list of
            dicts with ``content``, ``score``, ``metadata``), and
            ``result_count``.
        """
        query: str = kwargs["query"]
        collection: str = kwargs.get("collection", "knowledge")
        limit: int = kwargs.get("limit", 5)
        score_threshold: float = kwargs.get("score_threshold", 0.0)

        settings = get_settings()
        log = logger.bind(
            tool=self.name, query=query[:80], collection=collection, limit=limit,
        )
        log.debug("semantic_retrieval.start")

        # --- Embed the query ---
        embedder = _EmbeddingService(
            api_key=settings.openai_api_key.get_secret_value(),
            model=settings.embedding_model,
            dimensions=settings.embedding_dimensions,
        )

        query_vector = await embedder.embed(query)
        log.debug("semantic_retrieval.embedded", vector_dim=len(query_vector))

        # --- Search Qdrant ---
        qdrant = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=self.timeout_seconds,
        )

        try:
            hits: list[ScoredPoint] = await qdrant.search(
                collection_name=collection,
                query_vector=query_vector,
                limit=limit,
                score_threshold=score_threshold if score_threshold > 0 else None,
                with_payload=True,
            )
        except Exception as exc:
            raise ToolExecutionError(
                tool_name=self.name,
                message=f"Qdrant search failed: {exc}",
                cause=exc,
            ) from exc
        finally:
            await qdrant.close()

        # --- Format results ---
        results = self._format_hits(hits)

        log.info(
            "semantic_retrieval.complete",
            result_count=len(results),
        )

        return {
            "query": query,
            "collection": collection,
            "results": results,
            "result_count": len(results),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_hits(hits: list[ScoredPoint]) -> list[dict[str, Any]]:
        """Convert Qdrant scored points to a clean dict format.

        Args:
            hits: Scored points from a Qdrant search.

        Returns:
            A list of dicts with ``id``, ``score``, ``content``, and
            ``metadata`` keys.
        """
        results: list[dict[str, Any]] = []

        for hit in hits:
            payload = hit.payload or {}

            # Extract content — try common field names
            content = (
                payload.get("content")
                or payload.get("text")
                or payload.get("page_content")
                or ""
            )

            # Everything except the content field is metadata
            metadata = {
                k: v
                for k, v in payload.items()
                if k not in {"content", "text", "page_content"}
            }

            results.append(
                {
                    "id": str(hit.id),
                    "score": round(hit.score, 6),
                    "content": content,
                    "metadata": metadata,
                }
            )

        return results
