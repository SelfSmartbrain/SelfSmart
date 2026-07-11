"""Checkpoint management for objective state restoration."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.models import ObjectiveCheckpoint as ObjectiveCheckpointModel


class CheckpointManager:
    """Manages objective checkpoints for runtime recovery."""

    def __init__(self, session: AsyncSession | None = None) -> None:
        self.session = session

    async def create_checkpoint(
        self,
        objective_id: UUID,
        checkpoint_name: str,
        state_snapshot: dict[str, Any],
        progress_snapshot: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        session: AsyncSession | None = None,
    ) -> ObjectiveCheckpointModel:
        """Create a checkpoint for an objective."""
        checkpoint = ObjectiveCheckpointModel(
            objective_id=objective_id,
            checkpoint_name=checkpoint_name,
            state_snapshot=state_snapshot,
            progress_snapshot=progress_snapshot,
            metadata_=metadata,
        )
        db_session = session or self.session
        if db_session:
            db_session.add(checkpoint)
            await db_session.flush()
            await db_session.commit()
        return checkpoint

    async def get_latest_checkpoint(
        self,
        objective_id: UUID,
        session: AsyncSession,
    ) -> ObjectiveCheckpointModel | None:
        """Get the most recent checkpoint for an objective."""
        result = await session.execute(
            select(ObjectiveCheckpointModel)
            .where(ObjectiveCheckpointModel.objective_id == objective_id)
            .order_by(ObjectiveCheckpointModel.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_checkpoint_by_name(
        self,
        objective_id: UUID,
        checkpoint_name: str,
        session: AsyncSession,
    ) -> ObjectiveCheckpointModel | None:
        """Get a specific checkpoint by name."""
        result = await session.execute(
            select(ObjectiveCheckpointModel)
            .where(
                ObjectiveCheckpointModel.objective_id == objective_id,
                ObjectiveCheckpointModel.checkpoint_name == checkpoint_name,
            )
        )
        return result.scalar_one_or_none()

    async def list_checkpoints(
        self,
        objective_id: UUID,
        session: AsyncSession,
    ) -> list[ObjectiveCheckpointModel]:
        """List all checkpoints for an objective."""
        result = await session.execute(
            select(ObjectiveCheckpointModel)
            .where(ObjectiveCheckpointModel.objective_id == objective_id)
            .order_by(ObjectiveCheckpointModel.created_at.desc())
        )
        return list(result.scalars().all())

    async def delete_checkpoint(
        self,
        checkpoint_id: UUID,
        session: AsyncSession,
    ) -> bool:
        """Delete a checkpoint."""
        result = await session.execute(
            select(ObjectiveCheckpointModel).where(ObjectiveCheckpointModel.id == checkpoint_id)
        )
        checkpoint = result.scalar_one_or_none()
        if checkpoint:
            await session.delete(checkpoint)
            await session.commit()
            return True
        return False

    async def delete_old_checkpoints(
        self,
        objective_id: UUID,
        session: AsyncSession,
        keep_count: int = 5,
    ) -> int:
        """Delete old checkpoints, keeping only the most recent N."""
        checkpoints = await self.list_checkpoints(objective_id, session)
        if len(checkpoints) <= keep_count:
            return 0

        to_delete = checkpoints[keep_count:]
        deleted_count = 0
        for checkpoint in to_delete:
            await session.delete(checkpoint)
            deleted_count += 1

        await session.commit()
        return deleted_count


class RuntimeRecovery:
    """Handles runtime recovery from checkpoints."""

    def __init__(self, checkpoint_manager: CheckpointManager) -> None:
        self.checkpoint_manager = checkpoint_manager

    async def restore_runtime_state(
        self,
        objective_id: UUID,
        session: AsyncSession,
        checkpoint_name: str | None = None,
    ) -> dict[str, Any] | None:
        """Restore runtime state from a checkpoint."""
        if checkpoint_name:
            checkpoint = await self.checkpoint_manager.get_checkpoint_by_name(
                objective_id, checkpoint_name, session
            )
        else:
            checkpoint = await self.checkpoint_manager.get_latest_checkpoint(
                objective_id, session
            )

        if not checkpoint:
            return None

        return {
            "state_snapshot": checkpoint.state_snapshot,
            "progress_snapshot": checkpoint.progress_snapshot,
            "checkpoint_metadata": checkpoint.metadata_,
            "restored_at": datetime.utcnow().isoformat(),
        }

    async def auto_checkpoint_before_critical(
        self,
        objective_id: UUID,
        session: AsyncSession,
        state_snapshot: dict[str, Any],
        progress_snapshot: dict[str, Any] | None = None,
    ) -> ObjectiveCheckpointModel:
        """Create an automatic checkpoint before critical operations."""
        checkpoint_name = f"auto_critical_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        return await self.checkpoint_manager.create_checkpoint(
            objective_id=objective_id,
            checkpoint_name=checkpoint_name,
            state_snapshot=state_snapshot,
            progress_snapshot=progress_snapshot,
            metadata={"auto": True, "type": "pre_critical"},
            session=session,
        )

    async def auto_checkpoint_on_progress(
        self,
        objective_id: UUID,
        session: AsyncSession,
        state_snapshot: dict[str, Any],
        progress_snapshot: dict[str, Any] | None = None,
    ) -> ObjectiveCheckpointModel:
        """Create an automatic checkpoint on significant progress."""
        checkpoint_name = f"auto_progress_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}"
        return await self.checkpoint_manager.create_checkpoint(
            objective_id=objective_id,
            checkpoint_name=checkpoint_name,
            state_snapshot=state_snapshot,
            progress_snapshot=progress_snapshot,
            metadata={"auto": True, "type": "progress"},
            session=session,
        )
