"""
Long-Term Memory (PostgreSQL + Qdrant).

Manages persistent storage of episodic, semantic, and procedural memories.
Combines structured relational storage (PostgreSQL) with semantic search (Qdrant).
"""

from __future__ import annotations

import uuid
from typing import Any

from src.config.logging import get_logger
from src.db.enums import MemoryType
from src.db.repositories.memory_repo import MemoryRepository
from src.rag.embeddings import EmbeddingService
from src.rag.vector_store import VectorStoreManager

logger = get_logger(__name__)


class LongTermMemory:
    """
    Persistent memory system combining relational metadata and vector embeddings.
    """

    def __init__(
        self,
        db_repo: MemoryRepository,
        vector_store: VectorStoreManager,
        embedding_service: EmbeddingService,
    ) -> None:
        """
        Initialize long-term memory.

        Args:
            db_repo: Repository for PostgreSQL memory records.
            vector_store: Manager for Qdrant vector collections.
            embedding_service: Service to generate embeddings.
        """
        self.db = db_repo
        self.vector_store = vector_store
        self.embedder = embedding_service
        self.collection_name = "memories"

    async def store(
        self,
        content: str,
        user_id: str,
        memory_type: str = "semantic",
        metadata: dict[str, Any] | None = None,
        importance: float = 0.5,
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """
        Store a new memory in both Postgres and Qdrant.

        Args:
            content: The memory content.
            user_id: The owner of the memory.
            memory_type: episodic, semantic, or procedural.
            metadata: Optional tags and context.
            importance: How important this memory is (0.0 to 1.0).
            session_id: Optional session identifier.

        Returns:
            Dictionary representing the stored memory record.
        """
        metadata = metadata or {}
        
        try:
            # 1. Generate embedding
            embedding = await self.embedder.embed_text(content)
            
            # 2. Store in PostgreSQL
            m_type = MemoryType(memory_type.lower())
            user_uuid = uuid.UUID(user_id)
            session_uuid = uuid.UUID(session_id) if session_id else None
            
            memory_record = await self.db.store_memory(
                user_id=user_uuid,
                content=content,
                memory_type=m_type,
                metadata=metadata,
                importance_score=importance,
                session_id=session_uuid,
            )
            
            # 3. Store in Qdrant
            embedding_id = memory_record.embedding_id or str(uuid.uuid4())
            if not memory_record.embedding_id:
                # Update DB with the ID if it wasn't auto-generated
                memory_record = await self.db.update(memory_record.id, embedding_id=embedding_id)
                
            payload = {
                "memory_id": str(memory_record.id),
                "user_id": user_id,
                "memory_type": memory_type,
                "content": content,
                "importance": importance,
                **metadata,
            }
            
            await self.vector_store.upsert(
                collection=self.collection_name,
                id=embedding_id,
                vector=embedding,
                payload=payload,
            )
            
            logger.info(
                "Stored long-term memory", 
                memory_id=str(memory_record.id), 
                type=memory_type
            )
            
            return {
                "id": str(memory_record.id),
                "content": content,
                "memory_type": memory_type,
                "importance_score": importance,
            }
            
        except ValueError as e:
            logger.error("Invalid memory type provided", error=str(e), memory_type=memory_type)
            raise ValueError(f"Invalid memory type: {memory_type}") from e
        except uuid.UUIDError as e:
            logger.error("Invalid UUID format for user or session", error=str(e))
            raise ValueError("Invalid user_id or session_id format") from e
        except Exception as e:
            logger.error("Failed to store long-term memory", error=str(e), error_type=type(e).__name__)
            raise RuntimeError(f"Failed to store memory: {str(e)}") from e

    async def recall(
        self,
        query: str,
        user_id: str,
        memory_type: str | None = None,
        limit: int = 10,
        min_importance: float = 0.0,
    ) -> list[dict[str, Any]]:
        """
        Recall relevant memories based on semantic similarity.

        Args:
            query: The search string.
            user_id: Filter by owner.
            memory_type: Optional filter by memory type.
            limit: Maximum memories to return.
            min_importance: Minimum importance score threshold.

        Returns:
            List of memory records sorted by relevance.
        """
        try:
            # 1. Generate query embedding
            query_vector = await self.embedder.embed_text(query)
            
            # 2. Prepare filters
            filters: dict[str, Any] = {"user_id": user_id}
            if memory_type:
                filters["memory_type"] = memory_type.lower()
                
            # 3. Search vector store
            results = await self.vector_store.search(
                collection=self.collection_name,
                query_vector=query_vector,
                limit=limit * 2,  # Fetch more to filter by importance
                filters=filters,
            )
            
            # 4. Filter and format results
            memories = []
            for r in results:
                importance = r.payload.get("importance", 0.0)
                if importance >= min_importance:
                    # Increment access count in background
                    mem_id = r.payload.get("memory_id")
                    if mem_id:
                        await self.db.update_access(uuid.UUID(mem_id))
                        
                    memories.append({
                        "id": mem_id,
                        "content": r.payload.get("content", ""),
                        "memory_type": r.payload.get("memory_type", ""),
                        "importance_score": importance,
                        "relevance_score": r.score,
                        "metadata": {k: v for k, v in r.payload.items() 
                                     if k not in ["memory_id", "user_id", "memory_type", "content", "importance"]}
                    })
                    
            # Return top N
            return sorted(memories, key=lambda x: x["relevance_score"] + (x["importance_score"] * 0.2), reverse=True)[:limit]
            
        except ValueError as e:
            logger.error("Invalid query parameters", error=str(e), query=query[:50])
            raise ValueError(f"Invalid recall parameters: {str(e)}") from e
        except ConnectionError as e:
            logger.error("Vector store connection failed", error=str(e))
            raise RuntimeError("Failed to connect to vector store for recall") from e
        except Exception as e:
            logger.error("Failed to recall memories", error=str(e), query=query[:50], error_type=type(e).__name__)
            raise RuntimeError(f"Failed to recall memories: {str(e)}") from e

    async def consolidate(self, user_id: str) -> None:
        """
        Consolidate similar memories for a user.
        Delegates to MemoryConsolidation engine for the actual implementation.
        """
        logger.info("Memory consolidation triggered", user_id=user_id)
        # Import and use the MemoryConsolidation engine
        try:
            from .memory_consolidation import MemoryConsolidation
            from src.db.repositories.memory_repo import MemoryRepository
            from src.rag.embeddings import EmbeddingService
            
            # This would be properly injected in production
            consolidation = MemoryConsolidation(None, MemoryRepository(None), EmbeddingService())
            await consolidation.run(uuid.UUID(user_id))
        except Exception as e:
            logger.error(f"Memory consolidation failed: {e}")
            raise
