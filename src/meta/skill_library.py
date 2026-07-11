"""Skill Library component."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from src.db.enums import SkillStatus
from src.db.models import Skill
from src.db.repositories.skill_repo import SkillRepository
from src.rag.vector_store import VectorStoreManager
from src.rag.embeddings import EmbeddingService

logger = logging.getLogger(__name__)


class SkillLibrary:
    """Manages the dynamic ingestion, verification, and retrieval of reusable skills."""

    def __init__(
        self,
        skill_repo: SkillRepository,
        vector_store: VectorStoreManager,
        embedding_service: EmbeddingService,
    ) -> None:
        self.repo = skill_repo
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.collection = "skills"

    async def ingest_skill(
        self,
        name: str,
        description: str,
        steps: list[dict[str, Any]],
        task_types: list[str],
        tags: list[str] | None = None,
    ) -> Skill:
        """Add a new draft skill to the library and index it."""
        logger.info(f"Ingesting new skill: {name}")
        
        # Check if skill exists
        existing = await self.repo.get_by_name(name)
        if existing:
            raise ValueError(f"Skill with name '{name}' already exists.")

        # Embed for semantic search
        embedding_content = f"{name}: {description}"
        embedding = await self.embedding_service.embed_text(embedding_content)
        
        # Create DB record
        skill = await self.repo.create(
            name=name,
            description=description,
            steps=steps,
            task_types=task_types,
            tags=tags,
            status=SkillStatus.DRAFT,
        )
        
        # Update with embedding id
        embedding_id = str(skill.id)
        skill = await self.repo.update(skill.id, embedding_id=embedding_id)
        
        # Upsert to Qdrant
        if skill and embedding:
            await self.vector_store.upsert(
                collection=self.collection,
                id=embedding_id,
                vector=embedding,
                payload={
                    "name": skill.name,
                    "description": skill.description,
                    "status": skill.status.value,
                    "task_types": skill.task_types,
                }
            )
            
        return skill

    async def verify_skill(self, skill_id: UUID) -> Skill | None:
        """Promote a draft skill to active status after verification."""
        skill = await self.repo.get_by_id(skill_id)
        if not skill:
            return None
            
        if skill.status == SkillStatus.DRAFT:
            skill = await self.repo.update(skill_id, status=SkillStatus.ACTIVE)
            logger.info(f"Skill '{skill.name}' promoted to active.")
            
        return skill

    async def find_relevant_skills(
        self,
        query: str,
        task_type: str | None = None,
        limit: int = 5,
    ) -> list[Skill]:
        """Find relevant active skills for a specific task using semantic search."""
        query_vector = await self.embedding_service.embed_text(query)
        if not query_vector:
            return await self.repo.search(task_type=task_type, limit=limit)
            
        filters = {"status": "active"}
        if task_type:
            # We can't do an array intersection filter easily in all vector DBs,
            # so we'll just filter post-retrieval if needed, or if supported, add to filters.
            pass

        search_results = await self.vector_store.search(
            collection=self.collection,
            query_vector=query_vector,
            limit=limit * 2,  # Fetch extra for post-filtering
            filters=filters,
        )
        
        relevant_skills = []
        for result in search_results:
            skill_id = UUID(str(result.id))
            skill = await self.repo.get_by_id(skill_id)
            if not skill:
                continue
                
            if task_type and task_type not in skill.task_types:
                continue
                
            relevant_skills.append(skill)
            if len(relevant_skills) >= limit:
                break
                
        return relevant_skills
