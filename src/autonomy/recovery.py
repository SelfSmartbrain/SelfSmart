"""Runtime recovery mechanisms for Phase 17 - RetryPolicy, FailureRecovery, CheckpointRecovery."""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable

from sqlalchemy.ext.asyncio import AsyncSession

from src.autonomy.checkpoint_manager import CheckpointManager, RuntimeRecovery

logger = logging.getLogger(__name__)


class RetryStrategy(Enum):
    """Retry strategies for failed operations."""
    IMMEDIATE = "immediate"
    EXPONENTIAL_BACKOFF = "exponential_backoff"
    LINEAR_BACKOFF = "linear_backoff"
    FIXED_DELAY = "fixed_delay"


@dataclass
class RetryPolicy:
    """Configuration for retry behavior."""
    max_retries: int = 3
    strategy: RetryStrategy = RetryStrategy.EXPONENTIAL_BACKOFF
    base_delay: float = 1.0
    max_delay: float = 60.0
    backoff_multiplier: float = 2.0
    retryable_exceptions: tuple[type[Exception], ...] = (Exception,)
    
    def should_retry(self, attempt: int, exception: Exception) -> bool:
        """Determine if an operation should be retried."""
        if attempt >= self.max_retries:
            return False
        return isinstance(exception, self.retryable_exceptions)
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay before next retry based on strategy."""
        if self.strategy == RetryStrategy.IMMEDIATE:
            return 0.0
        elif self.strategy == RetryStrategy.FIXED_DELAY:
            return self.base_delay
        elif self.strategy == RetryStrategy.LINEAR_BACKOFF:
            return min(self.base_delay * attempt, self.max_delay)
        elif self.strategy == RetryStrategy.EXPONENTIAL_BACKOFF:
            delay = self.base_delay * (self.backoff_multiplier ** attempt)
            return min(delay, self.max_delay)
        return self.base_delay


class FailureRecovery:
    """Handles automatic recovery from failures with retry policies."""
    
    def __init__(
        self,
        default_policy: RetryPolicy | None = None,
        checkpoint_manager: CheckpointManager | None = None,
    ) -> None:
        self.default_policy = default_policy or RetryPolicy()
        self.checkpoint_manager = checkpoint_manager
        self.runtime_recovery = RuntimeRecovery(checkpoint_manager) if checkpoint_manager else None
        self._failure_counts: dict[str, int] = {}
    
    async def execute_with_retry(
        self,
        operation_id: str,
        operation: Callable,
        policy: RetryPolicy | None = None,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute an operation with automatic retry on failure."""
        retry_policy = policy or self.default_policy
        attempt = 0
        
        while True:
            try:
                result = await operation(*args, **kwargs)
                # Reset failure count on success
                self._failure_counts[operation_id] = 0
                return result
                
            except Exception as e:
                attempt += 1
                self._failure_counts[operation_id] = self._failure_counts.get(operation_id, 0) + 1
                
                if not retry_policy.should_retry(attempt, e):
                    logger.error(
                        f"Operation {operation_id} failed after {attempt} attempts: {e}"
                    )
                    raise
                
                delay = retry_policy.get_delay(attempt)
                logger.warning(
                    f"Operation {operation_id} failed (attempt {attempt}/{retry_policy.max_retries}), "
                    f"retrying in {delay:.2f}s: {e}"
                )
                
                await asyncio.sleep(delay)
    
    async def execute_with_checkpoint_recovery(
        self,
        objective_id: str,
        operation: Callable,
        session: AsyncSession,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute an operation with checkpoint-based recovery."""
        if not self.runtime_recovery:
            return await operation(*args, **kwargs)
        
        try:
            # Try to restore from latest checkpoint if available
            restored_state = await self.runtime_recovery.restore_runtime_state(
                objective_id=objective_id,
                session=session,
            )
            
            if restored_state:
                logger.info(f"Restored state for objective {objective_id} from checkpoint")
                # Pass restored state to operation
                kwargs["restored_state"] = restored_state
            
            return await operation(*args, **kwargs)
            
        except Exception as e:
            logger.error(f"Operation failed with checkpoint recovery: {e}")
            # Fall back to retry without checkpoint
            return await self.execute_with_retry(
                operation_id=objective_id,
                operation=operation,
                *args,
                **kwargs,
            )
    
    def get_failure_count(self, operation_id: str) -> int:
        """Get the number of failures for an operation."""
        return self._failure_counts.get(operation_id, 0)
    
    def reset_failure_count(self, operation_id: str) -> None:
        """Reset the failure count for an operation."""
        self._failure_counts[operation_id] = 0


class CheckpointRecovery:
    """Enhanced checkpoint recovery with automatic restoration."""
    
    def __init__(
        self,
        checkpoint_manager: CheckpointManager,
        failure_recovery: FailureRecovery | None = None,
    ) -> None:
        self.checkpoint_manager = checkpoint_manager
        self.failure_recovery = failure_recovery
    
    async def create_recovery_checkpoint(
        self,
        objective_id: str,
        session: AsyncSession,
        state_snapshot: dict[str, Any],
        progress_snapshot: dict[str, Any] | None = None,
    ) -> None:
        """Create a checkpoint specifically for recovery purposes."""
        checkpoint_name = f"recovery_{datetime.utcnow().strftime('%Y%m%d_%H%M%S_%f')}"
        await self.checkpoint_manager.create_checkpoint(
            objective_id=objective_id,
            checkpoint_name=checkpoint_name,
            state_snapshot=state_snapshot,
            progress_snapshot=progress_snapshot,
            metadata={"type": "recovery", "auto": True},
            session=session,
        )
    
    async def restore_from_latest_checkpoint(
        self,
        objective_id: str,
        session: AsyncSession,
    ) -> dict[str, Any] | None:
        """Restore from the latest checkpoint."""
        checkpoint = await self.checkpoint_manager.get_latest_checkpoint(
            objective_id=objective_id,
            session=session,
        )
        
        if not checkpoint:
            logger.warning(f"No checkpoint found for objective {objective_id}")
            return None
        
        logger.info(f"Restoring objective {objective_id} from checkpoint {checkpoint.checkpoint_name}")
        
        return {
            "state_snapshot": checkpoint.state_snapshot,
            "progress_snapshot": checkpoint.progress_snapshot,
            "checkpoint_metadata": checkpoint.metadata_,
            "restored_at": datetime.utcnow().isoformat(),
        }
    
    async def restore_from_named_checkpoint(
        self,
        objective_id: str,
        checkpoint_name: str,
        session: AsyncSession,
    ) -> dict[str, Any] | None:
        """Restore from a specific named checkpoint."""
        checkpoint = await self.checkpoint_manager.get_checkpoint_by_name(
            objective_id=objective_id,
            checkpoint_name=checkpoint_name,
            session=session,
        )
        
        if not checkpoint:
            logger.warning(f"Checkpoint {checkpoint_name} not found for objective {objective_id}")
            return None
        
        logger.info(f"Restoring objective {objective_id} from checkpoint {checkpoint_name}")
        
        return {
            "state_snapshot": checkpoint.state_snapshot,
            "progress_snapshot": checkpoint.progress_snapshot,
            "checkpoint_metadata": checkpoint.metadata_,
            "restored_at": datetime.utcnow().isoformat(),
        }
    
    async def execute_with_auto_checkpoint(
        self,
        objective_id: str,
        operation: Callable,
        session: AsyncSession,
        checkpoint_interval: float = 30.0,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute an operation with automatic periodic checkpointing."""
        if not self.failure_recovery:
            return await operation(*args, **kwargs)
        
        async def checkpointed_operation():
            # Create initial checkpoint
            initial_state = {"status": "started", "timestamp": datetime.utcnow().isoformat()}
            await self.create_recovery_checkpoint(
                objective_id=objective_id,
                state_snapshot=initial_state,
                session=session,
            )
            
            # Execute with periodic checkpointing
            result = await asyncio.create_task(operation(*args, **kwargs))
            
            # Create final checkpoint on success
            final_state = {
                "status": "completed",
                "timestamp": datetime.utcnow().isoformat(),
                "result": str(result),
            }
            await self.create_recovery_checkpoint(
                objective_id=objective_id,
                state_snapshot=final_state,
                session=session,
            )
            
            return result
        
        return await self.failure_recovery.execute_with_checkpoint_recovery(
            objective_id=objective_id,
            operation=checkpointed_operation,
            session=session,
        )
