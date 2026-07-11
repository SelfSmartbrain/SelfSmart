"""
Qdrant vector store manager for the RAG pipeline.

Manages three collections — *knowledge*, *memories*, and *reflections* — and
exposes async CRUD and search operations backed by ``qdrant_client.AsyncQdrantClient``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Sequence

from qdrant_client import AsyncQdrantClient, models

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)

# The canonical collections this manager creates / uses.
MANAGED_COLLECTIONS: tuple[str, ...] = (
    "knowledge", 
    "memories", 
    "reflections",
    "strategies",
    "skills",
    "experiences",
    "memory_clusters",
)


@dataclass
class SearchResult:
    """A single search result returned by the vector store.

    Attributes:
        id: The Qdrant point id.
        score: Cosine similarity score.
        payload: The stored payload dictionary.
        vector: The stored vector (only if ``with_vectors`` was requested).
    """

    id: str | int
    score: float
    payload: dict[str, Any]
    vector: list[float] | None = None


@dataclass
class VectorStoreManager:
    """Async manager for Qdrant collections.

    Create a single instance and call :meth:`initialize` at application startup
    to ensure all required collections exist.

    Usage::

        vsm = VectorStoreManager()
        await vsm.initialize()
        await vsm.upsert("knowledge", "doc-1", vector, {"title": "hello"})
        results = await vsm.search("knowledge", query_vec, limit=5)
        await vsm.close()
    """

    _client: AsyncQdrantClient = field(init=False, repr=False)
    _vector_size: int = field(init=False)

    def __post_init__(self) -> None:
        settings = get_settings()
        self._vector_size = settings.embedding_dimensions
        self._client = AsyncQdrantClient(
            url=settings.qdrant_url,
            api_key=settings.qdrant_api_key,
            timeout=30,
        )
        logger.info(
            "vector_store_manager_created",
            qdrant_url=settings.qdrant_url,
            vector_size=self._vector_size,
        )

    # --------------------------------------------------------------------- #
    # Lifecycle
    # --------------------------------------------------------------------- #

    async def initialize(self) -> None:
        """Create all managed collections if they do not already exist.

        Each collection is configured with:
        - Vector size = ``embedding_dimensions`` from settings (default 3072).
        - Distance metric = Cosine.
        - On-disk payload indexing for efficient filtering.
        """
        for name in MANAGED_COLLECTIONS:
            if not await self._client.collection_exists(name):
                await self._client.create_collection(
                    collection_name=name,
                    vectors_config=models.VectorParams(
                        size=self._vector_size,
                        distance=models.Distance.COSINE,
                        on_disk=True,
                    ),
                    on_disk_payload=True,
                )
                logger.info("collection_created", collection=name, vector_size=self._vector_size)
            else:
                logger.debug("collection_exists", collection=name)

    async def close(self) -> None:
        """Close the underlying Qdrant client connection."""
        await self._client.close()
        logger.info("vector_store_connection_closed")

    # --------------------------------------------------------------------- #
    # CRUD
    # --------------------------------------------------------------------- #

    async def upsert(
        self,
        collection: str,
        id: str | int,
        vector: list[float],
        payload: dict[str, Any],
    ) -> None:
        """Insert or update a single point in *collection*.

        Args:
            collection: Target collection name.
            id: Unique point identifier.
            vector: The embedding vector.
            payload: Metadata dictionary stored alongside the vector.
        """
        self._validate_collection(collection)
        await self._client.upsert(
            collection_name=collection,
            points=[
                models.PointStruct(
                    id=id,
                    vector=vector,
                    payload=payload,
                ),
            ],
        )
        logger.debug("point_upserted", collection=collection, point_id=id)

    async def upsert_batch(
        self,
        collection: str,
        ids: Sequence[str | int],
        vectors: Sequence[list[float]],
        payloads: Sequence[dict[str, Any]],
        batch_size: int = 64,
    ) -> None:
        """Insert or update multiple points in *collection* in sub-batches.

        Args:
            collection: Target collection name.
            ids: Sequence of unique point identifiers.
            vectors: Corresponding embedding vectors.
            payloads: Corresponding payload dictionaries.
            batch_size: Maximum points per upsert call.

        Raises:
            ValueError: If the lengths of *ids*, *vectors*, and *payloads* differ.
        """
        self._validate_collection(collection)
        if not (len(ids) == len(vectors) == len(payloads)):
            raise ValueError(
                f"Length mismatch: ids={len(ids)}, vectors={len(vectors)}, payloads={len(payloads)}"
            )

        total = len(ids)
        for start in range(0, total, batch_size):
            end = min(start + batch_size, total)
            points = [
                models.PointStruct(id=ids[i], vector=vectors[i], payload=payloads[i])
                for i in range(start, end)
            ]
            await self._client.upsert(collection_name=collection, points=points)
            logger.debug(
                "batch_upserted",
                collection=collection,
                batch=f"{start}-{end}",
                total=total,
            )

        logger.info("batch_upsert_complete", collection=collection, total=total)

    async def search(
        self,
        collection: str,
        query_vector: list[float],
        limit: int = 10,
        score_threshold: float | None = None,
        filters: dict[str, Any] | None = None,
        with_vectors: bool = False,
    ) -> list[SearchResult]:
        """Search for the nearest vectors in *collection*.

        Args:
            collection: The collection to search.
            query_vector: The query embedding vector.
            limit: Maximum number of results to return.
            score_threshold: Minimum cosine similarity score (optional).
            filters: Qdrant filter conditions as a dict mapping field names
                     to match values (simple equality filtering).
            with_vectors: If True, include the stored vector in results.

        Returns:
            An ordered list of ``SearchResult`` objects (highest score first).
        """
        self._validate_collection(collection)
        query_filter = self._build_filter(filters) if filters else None

        hits = await self._client.query_points(
            collection_name=collection,
            query=query_vector,
            limit=limit,
            score_threshold=score_threshold,
            query_filter=query_filter,
            with_payload=True,
            with_vectors=with_vectors,
        )

        results: list[SearchResult] = []
        for point in hits.points:
            vec: list[float] | None = None
            if with_vectors and isinstance(point.vector, list):
                vec = point.vector
            results.append(
                SearchResult(
                    id=point.id,
                    score=point.score if point.score is not None else 0.0,
                    payload=point.payload if point.payload else {},
                    vector=vec,
                )
            )

        logger.debug(
            "search_complete",
            collection=collection,
            results=len(results),
            limit=limit,
        )
        return results

    async def delete(self, collection: str, ids: Sequence[str | int]) -> None:
        """Remove points from *collection* by their IDs.

        Args:
            collection: Target collection name.
            ids: Point IDs to delete.
        """
        self._validate_collection(collection)
        await self._client.delete(
            collection_name=collection,
            points_selector=models.PointIdsList(points=list(ids)),
        )
        logger.debug("points_deleted", collection=collection, count=len(ids))

    async def get(self, collection: str, id: str | int) -> dict[str, Any] | None:
        """Retrieve a single point's payload by ID.

        Args:
            collection: Target collection name.
            id: The point ID.

        Returns:
            The payload dict if the point exists, otherwise ``None``.
        """
        self._validate_collection(collection)
        result = await self._client.retrieve(
            collection_name=collection,
            ids=[id],
            with_payload=True,
            with_vectors=False,
        )
        if result:
            return result[0].payload if result[0].payload else {}
        return None

    async def count(self, collection: str) -> int:
        """Return the number of points in *collection*.

        Args:
            collection: Target collection name.

        Returns:
            Point count.
        """
        info = await self._client.get_collection(collection)
        return info.points_count or 0

    # --------------------------------------------------------------------- #
    # Private helpers
    # --------------------------------------------------------------------- #

    @staticmethod
    def _validate_collection(collection: str) -> None:
        """Raise ``ValueError`` if *collection* is not a managed collection."""
        if collection not in MANAGED_COLLECTIONS:
            raise ValueError(
                f"Unknown collection '{collection}'. "
                f"Must be one of: {', '.join(MANAGED_COLLECTIONS)}"
            )

    @staticmethod
    def _build_filter(filters: dict[str, Any]) -> models.Filter:
        """Build a Qdrant filter from a simple ``{field: value}`` dict.

        Supports:
        - scalar values → MatchValue
        - list values → MatchAny
        """
        must_conditions: list[models.FieldCondition] = []
        for key, value in filters.items():
            if isinstance(value, list):
                must_conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchAny(any=value),
                    )
                )
            else:
                must_conditions.append(
                    models.FieldCondition(
                        key=key,
                        match=models.MatchValue(value=value),
                    )
                )
        return models.Filter(must=must_conditions)
