"""Experience Replay component."""

from __future__ import annotations

import logging
from uuid import UUID

from src.db.models import ExperienceRecord
from src.db.repositories.learning_repo import LearningRepository
from src.rag.vector_store import VectorStoreManager
from src.rag.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class ExperienceReplay:
    """Manages retrieval of relevant past experiences to inform current execution."""

    def __init__(
        self,
        learning_repo: LearningRepository,
        vector_store: VectorStoreManager,
        embedding_service: EmbeddingService,
    ) -> None:
        self.repo = learning_repo
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.collection = "experiences"

    async def store_experience(
        self,
        session_id: UUID,
        task_id: UUID,
        task_type: str,
        outcome: str,
        score: float,
        context_summary: str,
    ) -> ExperienceRecord:
        """Store an experience in the database and vector store."""
        
        embedding_content = f"{task_type}: {context_summary} -> {outcome}"
        embedding = await self.embedding_service.embed_text(embedding_content)
        
        experience = await self.repo.record_experience(
            session_id=session_id,
            task_id=task_id,
            task_type=task_type,
            outcome=outcome,
            score=score,
            context_summary=context_summary,
        )
        
        embedding_id = str(experience.id)
        experience = await self.repo.experiences.update(experience.id, embedding_id=embedding_id)
        
        if experience and embedding:
            await self.vector_store.upsert(
                collection=self.collection,
                id=embedding_id,
                vector=embedding,
                payload={
                    "task_type": task_type,
                    "outcome": outcome,
                    "score": score,
                    "context_summary": context_summary,
                }
            )
            
        return experience

    async def get_similar_experiences(self, task: str, limit: int = 3) -> list[ExperienceRecord]:
        """Fetch similar past experiences to inform current strategy."""
        
        query_vector = await self.embedding_service.embed_text(task)
        if not query_vector:
            return []
            
        # We look for experiences with a high score (successes) or very low score (failures to avoid)
        search_results = await self.vector_store.search(
            collection=self.collection,
            query_vector=query_vector,
            limit=limit,
        )
        
        relevant_experiences = []
        for result in search_results:
            exp_id = UUID(str(result.id))
            experience = await self.repo.experiences.get_by_id(exp_id)
            if experience:
                relevant_experiences.append(experience)
                
        return relevant_experiences
