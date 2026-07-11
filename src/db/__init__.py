"""
Database layer for the Autonomous Agent Platform.

Exports the core components needed by the rest of the application::

    from src.db import Base, get_session, get_engine
    from src.db.enums import SessionStatus, TaskStatus
    from src.db.models import Session, Task, Memory
"""

from src.db.enums import (
    ExecutionStatus,
    MemoryType,
    Priority,
    ReflectionType,
    SessionStatus,
    SourceType,
    TaskStatus,
)
from src.db.models import (
    AgentLog,
    Base,
    Execution,
    KnowledgeChunk,
    KnowledgeDocument,
    Memory,
    ReflectionRecord,
    Session,
    Task,
    User,
)
from src.db.session import get_engine, get_session, get_session_factory

__all__ = [
    # Base
    "Base",
    # Models
    "AgentLog",
    "Execution",
    "KnowledgeChunk",
    "KnowledgeDocument",
    "Memory",
    "ReflectionRecord",
    "Session",
    "Task",
    "User",
    # Enums
    "ExecutionStatus",
    "MemoryType",
    "Priority",
    "ReflectionType",
    "SessionStatus",
    "SourceType",
    "TaskStatus",
    # Session management
    "get_engine",
    "get_session",
    "get_session_factory",
]
