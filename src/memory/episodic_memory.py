"""Episodic Memory with Checkpoint Support

Provides persistence for project runs, failures, experiments, and interactions.
Implements checkpointing for long-horizon task resumption.
"""

from datetime import datetime, timezone
from typing import List, Optional, Dict, Any
from sqlalchemy import Column, Integer, String, DateTime, JSON, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

Base = declarative_base()


def utcnow() -> datetime:
    """Get current UTC time as timezone-aware datetime."""
    return datetime.now(timezone.utc)


class EpisodicMemory(Base):
    __tablename__ = "episodic_memory"
    id = Column(Integer, primary_key=True, autoincrement=True)
    project_id = Column(String, nullable=False)
    timestamp = Column(DateTime(timezone=True), default=utcnow)
    data = Column(JSON, nullable=False)  # raw event payload
    outcome = Column(String, nullable=True)

    def __repr__(self):
        return f"<EpisodicMemory id={self.id} project={self.project_id}>"


class TaskCheckpoint(Base):
    __tablename__ = "task_checkpoints"
    id = Column(Integer, primary_key=True, autoincrement=True)
    agent_id = Column(String, nullable=False, index=True)
    task_id = Column(String, nullable=False, index=True)
    checkpoint_name = Column(String, nullable=False)
    state_snapshot = Column(JSON, nullable=False)  # full agent/task state
    working_memory = Column(JSON, nullable=True)  # compressed working memory
    progress = Column(JSON, nullable=True)  # task progress info
    checkpoint_metadata = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=utcnow)
    parent_checkpoint_id = Column(Integer, nullable=True)  # for checkpoint chains

    def __repr__(self):
        return f"<TaskCheckpoint agent={self.agent_id} task={self.task_id} name={self.checkpoint_name}>"


# Helper functions
def store_episode(session, project_id: str, data: dict, outcome: Optional[str] = None):
    episode = EpisodicMemory(project_id=project_id, data=data, outcome=outcome)
    session.add(episode)
    session.commit()
    return episode


async def create_checkpoint(
    async_session: AsyncSession,
    agent_id: str,
    task_id: str,
    checkpoint_name: str,
    state_snapshot: Dict[str, Any],
    working_memory: Optional[List[Dict[str, Any]]] = None,
    progress: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    parent_checkpoint_id: Optional[int] = None,
) -> TaskCheckpoint:
    """
    Create a checkpoint for a long-running task to enable resumption.
    
    Args:
        async_session: SQLAlchemy async session
        agent_id: Agent identifier
        task_id: Task identifier
        checkpoint_name: Descriptive name for this checkpoint
        state_snapshot: Complete agent state (context, goals, plans, etc.)
        working_memory: Current working memory entries (will be compressed)
        progress: Task progress information
        metadata: Additional metadata
        parent_checkpoint_id: Previous checkpoint ID for chain
        
    Returns:
        Created TaskCheckpoint object
    """
    checkpoint = TaskCheckpoint(
        agent_id=agent_id,
        task_id=task_id,
        checkpoint_name=checkpoint_name,
        state_snapshot=state_snapshot,
        working_memory=working_memory,
        progress=progress,
        checkpoint_metadata=metadata,
        parent_checkpoint_id=parent_checkpoint_id,
    )
    async_session.add(checkpoint)
    await async_session.commit()
    await async_session.refresh(checkpoint)
    return checkpoint


async def get_latest_checkpoint(
    async_session: AsyncSession,
    agent_id: str,
    task_id: str,
) -> Optional[TaskCheckpoint]:
    """Get the most recent checkpoint for a task"""
    from sqlalchemy import select
    result = await async_session.execute(
        select(TaskCheckpoint)
        .where(TaskCheckpoint.agent_id == agent_id)
        .where(TaskCheckpoint.task_id == task_id)
        .order_by(TaskCheckpoint.created_at.desc())
        .limit(1)
    )
    return result.scalar_one_or_none()


async def get_checkpoint_chain(
    async_session: AsyncSession,
    agent_id: str,
    task_id: str,
) -> List[TaskCheckpoint]:
    """Get all checkpoints for a task in chronological order"""
    from sqlalchemy import select
    result = await async_session.execute(
        select(TaskCheckpoint)
        .where(TaskCheckpoint.agent_id == agent_id)
        .where(TaskCheckpoint.task_id == task_id)
        .order_by(TaskCheckpoint.created_at.asc())
    )
    return result.scalars().all()


async def resume_from_checkpoint(
    async_session: AsyncSession,
    checkpoint_id: int,
) -> Optional[TaskCheckpoint]:
    """Load a checkpoint for task resumption"""
    from sqlalchemy import select
    result = await async_session.execute(
        select(TaskCheckpoint).where(TaskCheckpoint.id == checkpoint_id)
    )
    return result.scalar_one_or_none()


async def delete_old_checkpoints(
    async_session: AsyncSession,
    agent_id: str,
    task_id: str,
    keep_latest: int = 5,
) -> int:
    """Clean up old checkpoints, keeping only the latest N"""
    from sqlalchemy import select, delete
    # Get IDs of checkpoints to keep
    result = await async_session.execute(
        select(TaskCheckpoint.id)
        .where(TaskCheckpoint.agent_id == agent_id)
        .where(TaskCheckpoint.task_id == task_id)
        .order_by(TaskCheckpoint.created_at.desc())
        .limit(keep_latest)
    )
    keep_ids = [row[0] for row in result.fetchall()]
    
    if len(keep_ids) >= keep_latest:
        # Delete older checkpoints
        await async_session.execute(
            delete(TaskCheckpoint)
            .where(TaskCheckpoint.agent_id == agent_id)
            .where(TaskCheckpoint.task_id == task_id)
            .where(TaskCheckpoint.id.notin_(keep_ids))
        )
        await async_session.commit()
        return len(keep_ids)
    return 0