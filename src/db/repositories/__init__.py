"""
Repository layer for the Autonomous Agent Platform.

Re-exports all concrete repository classes for convenient access::

    from src.db.repositories import SessionRepository, TaskRepository
"""

from src.db.repositories.base import BaseRepository
from src.db.repositories.execution_repo import ExecutionRepository
from src.db.repositories.memory_repo import MemoryRepository
from src.db.repositories.reflection_repo import ReflectionRepository
from src.db.repositories.session_repo import SessionRepository
from src.db.repositories.task_repo import TaskRepository

__all__ = [
    "BaseRepository",
    "ExecutionRepository",
    "MemoryRepository",
    "ReflectionRepository",
    "SessionRepository",
    "TaskRepository",
]
