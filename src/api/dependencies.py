"""
API Dependencies.

Provides dependency injection for database sessions, vector stores,
and agent instances required by the API routes.
"""

import asyncio
from typing import Annotated

from fastapi import Depends

from src.api.auth import User, get_current_user
from src.db.repositories.analytics_repo import AnalyticsRepository
from src.db.repositories.learning_repo import LearningRepository
from src.db.repositories.memory_repo import MemoryRepository
from src.db.repositories.reflection_repo import ReflectionRepository
from src.db.repositories.session_repo import SessionRepository
from src.db.repositories.skill_repo import SkillRepository
from src.db.repositories.strategy_repo import StrategyRepository
from src.db.repositories.task_repo import TaskRepository
from src.db.repositories.user_repo import UserRepository
from src.db.session import get_session
from src.rag.embeddings import EmbeddingService
from src.rag.retriever import Retriever
from src.rag.vector_store import VectorStoreManager

# Thread-safe singleton initialization
_vector_store: VectorStoreManager | None = None
_embedding_service: EmbeddingService | None = None
_vector_store_lock = asyncio.Lock()
_embedding_service_lock = asyncio.Lock()

# Stable aliases used by older route modules.
get_db = get_session
get_db_session = get_session


async def get_vector_store() -> VectorStoreManager:
    """Get the VectorStoreManager singleton with thread-safe initialization."""
    global _vector_store
    async with _vector_store_lock:
        if _vector_store is None:
            _vector_store = VectorStoreManager()
    return _vector_store


async def get_embedding_service() -> EmbeddingService:
    """Get the EmbeddingService singleton with thread-safe initialization."""
    global _embedding_service
    async with _embedding_service_lock:
        if _embedding_service is None:
            _embedding_service = EmbeddingService()
    return _embedding_service


async def get_retriever(
    vector_store: Annotated[VectorStoreManager, Depends(get_vector_store)],
    embedding_service: Annotated[EmbeddingService, Depends(get_embedding_service)],
) -> Retriever:
    """Get an initialized Retriever."""
    return Retriever(vector_store, embedding_service)


async def get_session_repo(db_session=Depends(get_session)) -> SessionRepository:
    """Get the SessionRepository bound to the current DB session."""
    return SessionRepository(db_session)


async def get_task_repo(db_session=Depends(get_session)) -> TaskRepository:
    """Get the TaskRepository bound to the current DB session."""
    return TaskRepository(db_session)


async def get_memory_repo(db_session=Depends(get_session)) -> MemoryRepository:
    """Get the MemoryRepository bound to the current DB session."""
    return MemoryRepository(db_session)


async def get_reflection_repo(db_session=Depends(get_session)) -> ReflectionRepository:
    """Get the ReflectionRepository bound to the current DB session."""
    return ReflectionRepository(db_session)


async def get_strategy_repo(db_session=Depends(get_session)) -> StrategyRepository:
    """Get the StrategyRepository bound to the current DB session."""
    return StrategyRepository(db_session)


async def get_skill_repo(db_session=Depends(get_session)) -> SkillRepository:
    """Get the SkillRepository bound to the current DB session."""
    return SkillRepository(db_session)


async def get_analytics_repo(db_session=Depends(get_session)) -> AnalyticsRepository:
    """Get the AnalyticsRepository bound to the current DB session."""
    return AnalyticsRepository(db_session)


async def get_learning_repo(db_session=Depends(get_session)) -> LearningRepository:
    """Get the LearningRepository bound to the current DB session."""
    return LearningRepository(db_session)


async def get_user_repo(db_session=Depends(get_session)) -> UserRepository:
    """Get the UserRepository bound to the current DB session."""
    return UserRepository(db_session)


# Export standard dependency types for routes
CurrentUser = Annotated[User, Depends(get_current_user)]
DB_SessionRepo = Annotated[SessionRepository, Depends(get_session_repo)]
DB_TaskRepo = Annotated[TaskRepository, Depends(get_task_repo)]
DB_MemoryRepo = Annotated[MemoryRepository, Depends(get_memory_repo)]
DB_ReflectionRepo = Annotated[ReflectionRepository, Depends(get_reflection_repo)]
DB_StrategyRepo = Annotated[StrategyRepository, Depends(get_strategy_repo)]
DB_SkillRepo = Annotated[SkillRepository, Depends(get_skill_repo)]
DB_AnalyticsRepo = Annotated[AnalyticsRepository, Depends(get_analytics_repo)]
DB_LearningRepo = Annotated[LearningRepository, Depends(get_learning_repo)]
RAG_Retriever = Annotated[Retriever, Depends(get_retriever)]
