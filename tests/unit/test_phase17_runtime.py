"""Tests for Phase 17 - Runtime Completion & Production Readiness."""

import asyncio
import pytest
from datetime import datetime
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.autonomy.objective_manager import Objective, ObjectiveManager
from src.autonomy.progress_tracker import ProgressTracker, ProgressRecord
from src.autonomy.checkpoint_manager import CheckpointManager, RuntimeRecovery
from src.autonomy.runtime_scheduler import RuntimeSchedule, ObjectivePriority
from src.autonomy.runtime_metrics import RuntimeMetricsCollector
from src.autonomy.recovery import RetryPolicy, RetryStrategy, FailureRecovery, CheckpointRecovery
from src.db.models import Objective as ObjectiveModel, ObjectiveProgress, ObjectiveCheckpoint


@pytest.mark.asyncio
async def test_objective_persistence(mock_db_session: AsyncSession):
    """Test that objectives survive database restart."""
    manager = ObjectiveManager(mock_db_session)

    # Create an objective
    objective = await manager.set_objective(
        "Test objective",
        priority=0.8,
        metadata={"test": True},
    )

    # Verify it's in memory
    assert len(manager.active_objectives) == 1
    assert manager.active_objectives[0].objective_id == objective.objective_id

    # Verify it's in database
    result = await mock_db_session.execute(
        select(ObjectiveModel).where(ObjectiveModel.objective_id == objective.objective_id)
    )
    db_obj = result.scalar_one_or_none()
    assert db_obj is not None
    assert db_obj.description == "Test objective"
    assert db_obj.priority == 0.8

    # Simulate restart by creating new manager
    new_manager = ObjectiveManager()
    await new_manager.load_from_db(mock_db_session)
    
    # Verify objective was loaded
    assert len(new_manager.active_objectives) == 1
    assert new_manager.active_objectives[0].objective_id == objective.objective_id
    assert new_manager.active_objectives[0].description == "Test objective"


@pytest.mark.asyncio
async def test_progress_persistence(mock_db_session: AsyncSession):
    """Test that progress records survive database restart."""
    tracker = ProgressTracker(mock_db_session)

    # Create a progress record
    objective = Objective(description="Test", objective_id="test_obj")
    record = await tracker.track_progress(
        objective,
        status="in_progress",
        detail="Working on it",
        result={"progress": 0.5},
    )

    # Verify it's in database
    result = await mock_db_session.execute(
        select(ObjectiveProgress).where(ObjectiveProgress.id == record.db_id)
    )
    db_record = result.scalar_one_or_none()
    assert db_record is not None
    assert db_record.status == "in_progress"
    assert db_record.detail == "Working on it"

    # Simulate restart
    new_tracker = ProgressTracker()
    await new_tracker.load_from_db(mock_db_session, objective_id="test_obj")

    # Verify record was loaded
    assert len(new_tracker.records) == 1
    assert new_tracker.records[0].status == "in_progress"


@pytest.mark.asyncio
async def test_checkpoint_creation_and_restore(mock_db_session: AsyncSession):
    """Test checkpoint creation and restoration."""
    checkpoint_manager = CheckpointManager(mock_db_session)
    recovery = RuntimeRecovery(checkpoint_manager)

    objective_id = uuid4()

    # Create a checkpoint
    state_snapshot = {"status": "active", "progress": 0.5}
    checkpoint = await checkpoint_manager.create_checkpoint(
        objective_id=objective_id,
        checkpoint_name="test_checkpoint",
        state_snapshot=state_snapshot,
        progress_snapshot={"step": 1},
        session=mock_db_session,
    )

    assert checkpoint is not None
    assert checkpoint.checkpoint_name == "test_checkpoint"

    # Restore from checkpoint
    restored = await recovery.restore_runtime_state(objective_id, session=mock_db_session)

    assert restored is not None
    assert restored["state_snapshot"]["status"] == "active"
    assert restored["state_snapshot"]["progress"] == 0.5


@pytest.mark.asyncio
async def test_runtime_scheduler_pause_resume(mock_db_session: AsyncSession):
    """Test runtime scheduler pause and resume functionality."""
    objective_manager = ObjectiveManager(mock_db_session)
    checkpoint_manager = CheckpointManager(mock_db_session)
    scheduler = RuntimeSchedule(objective_manager, checkpoint_manager)

    # Create and schedule an objective
    objective = await objective_manager.set_objective("Test objective")

    async def dummy_execution(obj: Objective):
        await asyncio.sleep(0.1)
        return "done"

    await scheduler.schedule_objective(
        objective,
        dummy_execution,
        priority=ObjectivePriority.MEDIUM,
    )

    # Pause the objective
    paused = await scheduler.pause_objective(objective.objective_id)
    assert paused is True

    # Verify it's paused
    assert objective.objective_id in scheduler._paused_objectives

    # Resume the objective
    resumed = await scheduler.resume_objective(objective.objective_id)
    assert resumed is True

    # Verify it's back in queue
    assert objective.objective_id not in scheduler._paused_objectives


@pytest.mark.asyncio
async def test_runtime_scheduler_cancel(mock_db_session: AsyncSession):
    """Test runtime scheduler cancel functionality."""
    objective_manager = ObjectiveManager(mock_db_session)
    checkpoint_manager = CheckpointManager(mock_db_session)
    scheduler = RuntimeSchedule(objective_manager, checkpoint_manager)
    
    # Create and schedule an objective
    objective = await objective_manager.set_objective("Test objective")
    
    async def dummy_execution(obj: Objective):
        await asyncio.sleep(0.1)
        return "done"
    
    await scheduler.schedule_objective(
        objective,
        dummy_execution,
        priority=ObjectivePriority.MEDIUM,
    )
    
    # Cancel the objective
    cancelled = await scheduler.cancel_objective(objective.objective_id)
    assert cancelled is True
    
    # Verify metrics updated
    metrics = scheduler.get_metrics()
    assert metrics["objectives_cancelled"] == 1


@pytest.mark.asyncio
async def test_runtime_metrics():
    """Test runtime metrics collection."""
    collector = RuntimeMetricsCollector()
    
    # Record some metrics
    collector.record_objective_completed(10.0)
    collector.record_objective_completed(20.0)
    collector.record_objective_failed()
    
    # Verify metrics
    assert collector._completed_objectives == 2
    assert collector._failed_objectives == 1
    assert collector._total_objectives == 3
    
    # Update from scheduler metrics
    scheduler_metrics = {
        "completion_rate": 0.8,
        "failure_rate": 0.2,
        "average_cycle_time": 15.0,
        "active_objectives": 3,
        "queue_size": 2,
    }
    
    collector.update_from_scheduler_metrics(scheduler_metrics)
    
    # Reset
    collector.reset()
    assert collector._total_objectives == 0


@pytest.mark.asyncio
async def test_retry_policy():
    """Test retry policy logic."""
    policy = RetryPolicy(
        max_retries=3,
        strategy=RetryStrategy.EXPONENTIAL_BACKOFF,
        base_delay=1.0,
        backoff_multiplier=2.0,
    )
    
    # Test should_retry
    assert policy.should_retry(1, Exception()) is True
    assert policy.should_retry(3, Exception()) is False
    
    # Test delay calculation
    delay1 = policy.get_delay(1)
    delay2 = policy.get_delay(2)
    assert delay2 > delay1  # Exponential backoff
    
    # Test max delay
    policy.max_delay = 5.0
    delay = policy.get_delay(10)
    assert delay <= 5.0


@pytest.mark.asyncio
async def test_failure_recovery():
    """Test failure recovery with retry."""
    failure_recovery = FailureRecovery()
    
    call_count = 0
    
    async def failing_operation():
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("Temporary failure")
        return "success"
    
    # Execute with retry
    result = await failure_recovery.execute_with_retry(
        operation_id="test_op",
        operation=failing_operation,
        policy=RetryPolicy(max_retries=3, strategy=RetryStrategy.IMMEDIATE),
    )
    
    assert result == "success"
    assert call_count == 3  # Failed twice, succeeded on third try


@pytest.mark.asyncio
async def test_checkpoint_recovery(mock_db_session: AsyncSession):
    """Test checkpoint recovery mechanism."""
    checkpoint_manager = CheckpointManager(mock_db_session)
    failure_recovery = FailureRecovery(checkpoint_manager)
    checkpoint_recovery = CheckpointRecovery(checkpoint_manager, failure_recovery)

    objective_id = uuid4()

    # Create a recovery checkpoint
    state = {"status": "processing", "data": "test"}
    await checkpoint_recovery.create_recovery_checkpoint(
        objective_id=str(objective_id),
        state_snapshot=state,
        session=mock_db_session,
    )

    # Restore from checkpoint
    restored = await checkpoint_recovery.restore_from_latest_checkpoint(
        objective_id=str(objective_id),
        session=mock_db_session,
    )
    
    assert restored is not None
    assert restored["state_snapshot"]["status"] == "processing"
    
    # Test named checkpoint restore
    await checkpoint_manager.create_checkpoint(
        objective_id=objective_id,
        checkpoint_name="specific_checkpoint",
        state_snapshot={"status": "specific"},
        session=mock_db_session,
    )

    restored_named = await checkpoint_recovery.restore_from_named_checkpoint(
        objective_id=str(objective_id),
        checkpoint_name="specific_checkpoint",
        session=mock_db_session,
    )

    assert restored_named is not None
    assert restored_named["state_snapshot"]["status"] == "specific"


@pytest.mark.asyncio
async def test_objective_status_transitions(mock_db_session: AsyncSession):
    """Test objective status transitions with persistence."""
    manager = ObjectiveManager(mock_db_session)

    # Create objective
    objective = await manager.set_objective("Test objective")
    assert objective.status == "active"

    # Pause objective
    paused = await manager.pause_objective(objective.objective_id)
    assert paused is not None
    assert paused.status == "paused"

    # Resume objective
    resumed = await manager.resume_objective(objective.objective_id)
    assert resumed is not None
    assert resumed.status == "active"

    # Complete objective
    completed = await manager.complete_objective(objective.objective_id)
    assert completed is not None
    assert completed.status == "completed"

    # Verify in database
    result = await mock_db_session.execute(
        select(ObjectiveModel).where(ObjectiveModel.objective_id == objective.objective_id)
    )
    db_obj = result.scalar_one_or_none()
    assert db_obj.status.value == "completed"
    assert db_obj.completed_at is not None


@pytest.mark.asyncio
async def test_runtime_scheduler_metrics(mock_db_session: AsyncSession):
    """Test runtime scheduler metrics calculation."""
    objective_manager = ObjectiveManager(mock_db_session)
    checkpoint_manager = CheckpointManager(mock_db_session)
    scheduler = RuntimeSchedule(objective_manager, checkpoint_manager)

    # Schedule some objectives
    for i in range(5):
        objective = await objective_manager.set_objective(f"Objective {i}")
        async def dummy(obj): return "done"
        await scheduler.schedule_objective(objective, dummy)

    # Get metrics
    metrics = scheduler.get_metrics()

    assert metrics["objectives_scheduled"] == 5
    assert metrics["queue_size"] == 5
    assert metrics["active_objectives"] == 0
    assert metrics["completion_rate"] == 0.0
