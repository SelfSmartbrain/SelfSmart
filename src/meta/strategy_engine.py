"""Strategy Engine component."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.db.enums import TaskType, StrategyStatus
from src.db.models import Strategy, StrategyExecution
from src.db.repositories.strategy_repo import StrategyRepository
from src.rag.vector_store import VectorStoreManager
from src.rag.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class StrategyEngine:
    """Manages strategy storage, retrieval, ranking, and effectiveness tracking."""

    def __init__(
        self,
        strategy_repo: StrategyRepository,
        vector_store: VectorStoreManager,
        embedding_service: EmbeddingService,
    ) -> None:
        self.repo = strategy_repo
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.collection = "strategies"

    async def create_strategy(
        self,
        task_type: TaskType | str,
        name: str,
        description: str,
        steps: list[dict[str, Any]],
        source_session_id: UUID | None = None,
        confidence: float = 0.5,
        tags: list[str] | None = None,
        is_global: bool = False,
    ) -> Strategy:
        """Create a new strategy and index it in the vector store."""
        
        # Embed the strategy description for semantic search
        embedding_content = f"{name}: {description}"
        embedding = await self.embedding_service.embed_text(embedding_content)
        
        # Create DB record
        strategy = await self.repo.create(
            task_type=task_type,
            name=name,
            description=description,
            steps=steps,
            source_session_id=source_session_id,
            confidence=confidence,
            tags=tags,
            is_global=is_global,
            status=StrategyStatus.TESTING,
        )
        
        # Update with embedding id
        embedding_id = str(strategy.id)
        strategy = await self.repo.update(strategy.id, embedding_id=embedding_id)
        
        # Upsert to Qdrant
        if strategy and embedding:
            await self.vector_store.upsert(
                collection=self.collection,
                id=embedding_id,
                vector=embedding,
                payload={
                    "task_type": strategy.task_type.value,
                    "name": strategy.name,
                    "description": strategy.description,
                    "status": strategy.status.value,
                    "is_global": strategy.is_global,
                }
            )
            
        return strategy

    async def get_strategies(self, task_type: TaskType | str, limit: int = 10) -> list[Strategy]:
        """Get the top-ranked active strategies for a given task type."""
        return await self.repo.get_by_task_type(task_type, limit=limit, active_only=True)

    async def get_best_strategy(
        self,
        task_type: TaskType | str,
        context: str,
    ) -> Strategy | None:
        """Find the best strategy using semantic similarity + statistical ranking."""
        # Embed context
        context_vector = await self.embedding_service.embed_text(context)
        if not context_vector:
            # Fallback to DB stats if embedding fails
            strategies = await self.get_strategies(task_type, limit=1)
            return strategies[0] if strategies else None

        # Search vector store for relevant strategies
        filters = {"task_type": task_type if isinstance(task_type, str) else task_type.value, "status": "active"}
        search_results = await self.vector_store.search(
            collection=self.collection,
            query_vector=context_vector,
            limit=5,
            filters=filters,
        )
        
        if not search_results:
            strategies = await self.get_strategies(task_type, limit=1)
            return strategies[0] if strategies else None
            
        # We need to combine semantic relevance score with historic success_rate and confidence
        best_strategy = None
        best_score = -1.0
        
        for result in search_results:
            strategy_id = UUID(str(result.id))
            strategy = await self.repo.get_by_id(strategy_id)
            if not strategy:
                continue
                
            # Score formula: (success_rate * 0.6) + (confidence * 0.2) + (semantic_relevance * 0.2)
            score = (strategy.success_rate * 0.6) + (strategy.confidence * 0.2) + (result.score * 0.2)
            if score > best_score:
                best_score = score
                best_strategy = strategy
                
        return best_strategy

    async def record_execution(
        self,
        strategy_id: UUID,
        session_id: UUID,
        task_id: UUID,
        success: bool,
        duration_ms: int | None = None,
        tokens_used: int | None = None,
        error: str | None = None,
    ) -> StrategyExecution:
        """Record the outcome of executing a strategy."""
        return await self.repo.record_execution(
            strategy_id=strategy_id,
            session_id=session_id,
            task_id=task_id,
            success=success,
            duration_ms=duration_ms,
            tokens_used=tokens_used,
            error=error,
        )
