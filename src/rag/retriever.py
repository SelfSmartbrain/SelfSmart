"""
Semantic retriever for the RAG pipeline.

Embeds a query, searches Qdrant, and optionally reranks results using a
cross-encoder–style rescoring heuristic.  Includes contextual compression
to summarise retrieved chunks into a bounded context window.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from src.config.logging import get_logger
from src.rag.chunking import TextChunker, _count_tokens
from src.rag.embeddings import EmbeddingService
from src.rag.vector_store import VectorStoreManager

logger = get_logger(__name__)


@dataclass(frozen=True, slots=True)
class RetrievalResult:
    """A single retrieval result returned to the caller.

    Attributes:
        content: The chunk text.
        score: Relevance score (cosine similarity or reranked score).
        metadata: The full payload dictionary from Qdrant.
        source: Origin path / URL of the document.
        chunk_id: The Qdrant point ID for this chunk.
    """

    content: str
    score: float
    metadata: dict[str, Any]
    source: str
    chunk_id: str | int


@dataclass
class Retriever:
    """Async semantic retriever combining embedding, vector search, and reranking.

    Usage::

        retriever = Retriever(embedding_service=emb, vector_store=vsm)
        results = await retriever.retrieve("How does X work?", collection="knowledge")
    """

    embedding_service: EmbeddingService
    vector_store: VectorStoreManager
    _chunker: TextChunker = field(default_factory=TextChunker, repr=False)

    # --------------------------------------------------------------------- #
    # Core retrieval
    # --------------------------------------------------------------------- #

    async def retrieve(
        self,
        query: str,
        collection: str = "knowledge",
        limit: int = 10,
        filters: dict[str, Any] | None = None,
        score_threshold: float | None = None,
    ) -> list[RetrievalResult]:
        """Embed the query and search the vector store.

        Args:
            query: Natural-language query.
            collection: Qdrant collection to search.
            limit: Maximum number of results.
            filters: Optional payload filters (field → value).
            score_threshold: Minimum score to include.

        Returns:
            A list of :class:`RetrievalResult` sorted by descending score.
        """
        query_vector = await self.embedding_service.embed_text(query)
        search_results = await self.vector_store.search(
            collection=collection,
            query_vector=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            filters=filters,
        )

        results = [
            RetrievalResult(
                content=sr.payload.get("content", ""),
                score=sr.score,
                metadata=sr.payload,
                source=sr.payload.get("source", ""),
                chunk_id=sr.id,
            )
            for sr in search_results
        ]
        logger.debug("retrieval_complete", query_len=len(query), results=len(results))
        return results

    # --------------------------------------------------------------------- #
    # Retrieval with reranking
    # --------------------------------------------------------------------- #

    async def retrieve_with_reranking(
        self,
        query: str,
        collection: str = "knowledge",
        limit: int = 5,
        rerank_top_k: int = 20,
        filters: dict[str, Any] | None = None,
        score_threshold: float | None = None,
    ) -> list[RetrievalResult]:
        """Retrieve candidates and rerank them for higher relevance.

        1. Retrieve *rerank_top_k* candidates from the vector store.
        2. Compute a reranking score for each candidate based on lexical
           overlap and embedding similarity (lightweight heuristic that does
           not require a separate cross-encoder model).
        3. Return the top *limit* reranked results.

        Args:
            query: Natural-language query.
            collection: Qdrant collection to search.
            limit: Number of final results after reranking.
            rerank_top_k: Number of candidates to fetch before reranking.
            filters: Optional payload filters.
            score_threshold: Minimum initial vector score.

        Returns:
            Reranked list of :class:`RetrievalResult`.
        """
        candidates = await self.retrieve(
            query=query,
            collection=collection,
            limit=rerank_top_k,
            filters=filters,
            score_threshold=score_threshold,
        )

        if not candidates:
            return []

        reranked = self._rerank(query, candidates)
        final = reranked[:limit]

        logger.info(
            "reranking_complete",
            candidates=len(candidates),
            returned=len(final),
        )
        return final

    # --------------------------------------------------------------------- #
    # Contextual compression
    # --------------------------------------------------------------------- #

    async def retrieve_compressed(
        self,
        query: str,
        collection: str = "knowledge",
        limit: int = 10,
        max_context_tokens: int = 4096,
        filters: dict[str, Any] | None = None,
        score_threshold: float | None = None,
    ) -> list[RetrievalResult]:
        """Retrieve and compress results to fit within a token budget.

        Greedily adds the highest-scoring results until the token budget is
        exhausted.  Results that would exceed the budget are truncated.

        Args:
            query: Natural-language query.
            collection: Qdrant collection to search.
            limit: Maximum number of results to consider.
            max_context_tokens: Token budget for the combined context.
            filters: Optional payload filters.
            score_threshold: Minimum score to include.

        Returns:
            A list of results whose combined token count ≤ *max_context_tokens*.
        """
        results = await self.retrieve(
            query=query,
            collection=collection,
            limit=limit,
            filters=filters,
            score_threshold=score_threshold,
        )

        compressed: list[RetrievalResult] = []
        remaining_tokens = max_context_tokens

        for result in results:
            chunk_tokens = _count_tokens(result.content)
            if chunk_tokens <= remaining_tokens:
                compressed.append(result)
                remaining_tokens -= chunk_tokens
            elif remaining_tokens > 50:
                # Truncate the chunk to fit the remaining budget
                truncated_content = self._truncate_to_tokens(result.content, remaining_tokens)
                compressed.append(
                    RetrievalResult(
                        content=truncated_content,
                        score=result.score,
                        metadata={**result.metadata, "truncated": True},
                        source=result.source,
                        chunk_id=result.chunk_id,
                    )
                )
                break
            else:
                break

        logger.debug(
            "compressed_retrieval",
            total_candidates=len(results),
            compressed_count=len(compressed),
            budget=max_context_tokens,
            used=max_context_tokens - remaining_tokens,
        )
        return compressed

    # --------------------------------------------------------------------- #
    # Multi-collection retrieval
    # --------------------------------------------------------------------- #

    async def retrieve_multi(
        self,
        query: str,
        collections: list[str] | None = None,
        limit_per_collection: int = 5,
        filters: dict[str, Any] | None = None,
        score_threshold: float | None = None,
    ) -> list[RetrievalResult]:
        """Search across multiple collections and merge results by score.

        Args:
            query: Natural-language query.
            collections: Collections to search (defaults to knowledge + memories).
            limit_per_collection: Limit per individual collection.
            filters: Optional filters applied to each collection.
            score_threshold: Minimum score.

        Returns:
            Merged list sorted by descending score.
        """
        if collections is None:
            collections = ["knowledge", "memories"]

        all_results: list[RetrievalResult] = []
        for coll in collections:
            results = await self.retrieve(
                query=query,
                collection=coll,
                limit=limit_per_collection,
                filters=filters,
                score_threshold=score_threshold,
            )
            for r in results:
                all_results.append(
                    RetrievalResult(
                        content=r.content,
                        score=r.score,
                        metadata={**r.metadata, "collection": coll},
                        source=r.source,
                        chunk_id=r.chunk_id,
                    )
                )

        all_results.sort(key=lambda r: r.score, reverse=True)
        return all_results

    # --------------------------------------------------------------------- #
    # Private helpers
    # --------------------------------------------------------------------- #

    @staticmethod
    def _rerank(query: str, candidates: list[RetrievalResult]) -> list[RetrievalResult]:
        """Lightweight reranking using lexical overlap + vector score blending.

        Computes a combined score:
            ``reranked_score = 0.6 * vector_score + 0.4 * lexical_score``

        where *lexical_score* is the Jaccard similarity between the query
        tokens and the chunk tokens.
        """
        query_tokens = set(query.lower().split())
        if not query_tokens:
            return candidates

        scored: list[tuple[float, RetrievalResult]] = []
        for candidate in candidates:
            chunk_tokens = set(candidate.content.lower().split())
            intersection = query_tokens & chunk_tokens
            union = query_tokens | chunk_tokens
            lexical_score = len(intersection) / max(len(union), 1)

            blended = 0.6 * candidate.score + 0.4 * lexical_score
            scored.append(
                (
                    blended,
                    RetrievalResult(
                        content=candidate.content,
                        score=blended,
                        metadata={
                            **candidate.metadata,
                            "original_vector_score": candidate.score,
                            "lexical_score": lexical_score,
                        },
                        source=candidate.source,
                        chunk_id=candidate.chunk_id,
                    ),
                )
            )

        scored.sort(key=lambda t: t[0], reverse=True)
        return [r for _, r in scored]

    @staticmethod
    def _truncate_to_tokens(text: str, max_tokens: int) -> str:
        """Truncate *text* to at most *max_tokens* tokens."""
        import tiktoken  # noqa: PLC0415

        enc = tiktoken.get_encoding("cl100k_base")
        tokens = enc.encode(text, disallowed_special=())
        if len(tokens) <= max_tokens:
            return text
        return enc.decode(tokens[:max_tokens])
