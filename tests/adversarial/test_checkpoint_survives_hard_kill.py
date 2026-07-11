"""Adversarial checkpoint tests, including a real SIGKILL and restart."""

import asyncio
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.runtime.execution_loop import ExecutionLoop
from src.autonomy.objective_manager import ObjectiveManager
from src.autonomy.checkpoint_manager import CheckpointManager, RuntimeRecovery
from src.autonomy.progress_tracker import ProgressTracker


def _latest_checkpoint(state_file: Path, objective_id: str):
    document = json.loads(state_file.read_text(encoding="utf-8"))
    return document["objectives"][objective_id][-1]


def _wait_for_checkpoint(
    state_file: Path,
    objective_id: str,
    minimum_step: int,
    timeout: float = 15.0,
):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        try:
            checkpoint = _latest_checkpoint(state_file, objective_id)
        except (FileNotFoundError, json.JSONDecodeError, KeyError, IndexError):
            time.sleep(0.05)
            continue
        if checkpoint["progress_snapshot"]["step"] >= minimum_step:
            return checkpoint
        time.sleep(0.05)
    raise AssertionError(
        f"Timed out waiting for objective {objective_id} to reach step {minimum_step}"
    )


def test_checkpoint_survives_sigkill(tmp_path):
    """A second process must resume from the last checkpoint after SIGKILL."""
    repository_root = Path(__file__).resolve().parents[2]
    state_file = tmp_path / "checkpoints.json"
    pid_file = tmp_path / "harness.pid"
    objective_id = "obj_sigkill_adversarial"
    environment = os.environ.copy()
    environment["PYTHONPATH"] = os.pathsep.join(
        filter(None, [str(repository_root), environment.get("PYTHONPATH")])
    )

    run_command = [
        sys.executable,
        "-m",
        "src.cli.execution_loop_harness",
        "run",
        "Verify process checkpoint recovery",
        "--objective-id",
        objective_id,
        "--total-steps",
        "40",
        "--step-delay",
        "0.05",
        "--state-file",
        str(state_file),
        "--pid-file",
        str(pid_file),
    ]
    process = subprocess.Popen(
        run_command,
        cwd=repository_root,
        env=environment,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        text=True,
    )

    try:
        checkpoint_before_kill = _wait_for_checkpoint(state_file, objective_id, 2)
        assert checkpoint_before_kill["state_snapshot"]["status"] == "running"
        assert checkpoint_before_kill["progress_snapshot"]["step"] < 40

        os.kill(process.pid, signal.SIGKILL)
        assert process.wait(timeout=5) == -signal.SIGKILL

        durable_step = _latest_checkpoint(
            state_file,
            objective_id,
        )["progress_snapshot"]["step"]

        restore_command = [
            sys.executable,
            "-m",
            "src.cli.execution_loop_harness",
            "restore",
            objective_id,
            "--step-delay",
            "0.005",
            "--state-file",
            str(state_file),
            "--pid-file",
            str(pid_file),
        ]
        restored = subprocess.run(
            restore_command,
            cwd=repository_root,
            env=environment,
            capture_output=True,
            text=True,
            timeout=15,
        )
        assert restored.returncode == 0, restored.stderr or restored.stdout

        final_checkpoint = _latest_checkpoint(state_file, objective_id)
        assert final_checkpoint["state_snapshot"]["status"] == "completed"
        assert final_checkpoint["progress_snapshot"]["step"] == 40
        assert final_checkpoint["metadata"]["sequence"] > durable_step
    finally:
        if process.poll() is None:
            process.kill()
            process.wait(timeout=5)

@pytest.mark.asyncio
async def test_checkpoint_on_progress_saves_state():
    """Test that auto-checkpoint on progress saves the correct state."""
    # Direct test of RuntimeRecovery.auto_checkpoint_on_progress
    session = AsyncMock()
    checkpoint_manager = CheckpointManager(session=session)
    runtime_recovery = RuntimeRecovery(checkpoint_manager)
    
    # Mock the checkpoint creation to capture what would be saved
    captured_checkpoint = None
    
    async def mock_create(*args, **kwargs):
        nonlocal captured_checkpoint
        captured_checkpoint = {
            "args": args,
            "kwargs": kwargs,
        }
        # Return a mock checkpoint
        mock_checkpoint = MagicMock()
        mock_checkpoint.id = "test-checkpoint-id"
        return mock_checkpoint
    
    checkpoint_manager.create_checkpoint = mock_create
    
    # Call auto_checkpoint_on_progress directly
    state_snapshot = {
        "tick_count": 5,
        "objective_id": "test-obj-123",
        "objective_description": "test objective",
        "running": True,
    }
    progress_snapshot = {"status": "in_progress"}
    
    await runtime_recovery.auto_checkpoint_on_progress(
        objective_id="test-obj-123",
        session=session,
        state_snapshot=state_snapshot,
        progress_snapshot=progress_snapshot,
    )
    
    # Verify checkpoint was called with correct state
    assert captured_checkpoint is not None, "FAIL: no checkpoint was created"
    
    # Check that the state snapshot includes the tick count
    saved_state = captured_checkpoint["kwargs"].get("state_snapshot", {})
    assert saved_state.get("tick_count") == 5, (
        f"FAIL: checkpoint state tick_count is {saved_state.get('tick_count')}, expected 5"
    )
    
    # Check that objective_id is preserved
    assert saved_state.get("objective_id") == "test-obj-123", (
        f"FAIL: checkpoint objective_id is {saved_state.get('objective_id')}, expected test-obj-123"
    )

@pytest.mark.asyncio
async def test_restore_from_checkpoint_recovers_state():
    """Test that restore_from_checkpoint recovers the saved state."""
    # Setup
    session = AsyncMock()
    checkpoint_manager = CheckpointManager(session=session)
    runtime_recovery = RuntimeRecovery(checkpoint_manager)
    
    # Mock the checkpoint retrieval
    mock_checkpoint = MagicMock()
    mock_checkpoint.state_snapshot = {
        "tick_count": 5,
        "objective_id": "test-obj-123",
        "objective_description": "test objective",
        "running": True,
    }
    mock_checkpoint.progress_snapshot = {"status": "in_progress"}
    mock_checkpoint.metadata_ = {"auto": True, "type": "progress"}
    
    checkpoint_manager.get_latest_checkpoint = AsyncMock(return_value=mock_checkpoint)
    
    # Restore state
    restored = await runtime_recovery.restore_runtime_state(
        objective_id="test-obj-123",
        session=session,
    )
    
    # Verify restored state matches saved state
    assert restored is not None, "FAIL: restore returned None"
    assert restored["state_snapshot"]["tick_count"] == 5, (
        f"FAIL: restored tick_count is {restored['state_snapshot']['tick_count']}, expected 5"
    )
    assert restored["state_snapshot"]["objective_id"] == "test-obj-123", (
        f"FAIL: restored objective_id is {restored['state_snapshot']['objective_id']}, expected test-obj-123"
    )
    assert restored["state_snapshot"]["running"] is True, (
        f"FAIL: restored running is {restored['state_snapshot']['running']}, expected True"
    )

@pytest.mark.asyncio
async def test_checkpoint_on_failure_saves_error_state():
    """Test that checkpoint on failure saves error state."""
    session = AsyncMock()
    checkpoint_manager = CheckpointManager(session=session)
    runtime_recovery = RuntimeRecovery(checkpoint_manager)
    
    # Use a simple objective without DB persistence
    from src.autonomy.objective_manager import Objective
    obj = Objective(description="test-objective-1")
    
    objective_manager = ObjectiveManager(session=None)
    objective_manager.active_objectives.append(obj)
    
    progress_tracker = ProgressTracker(session=None)
    
    execution_loop = ExecutionLoop(
        objective_manager=objective_manager,
        progress_tracker=progress_tracker,
        checkpoint_manager=checkpoint_manager,
        auto_checkpoint_interval=10,
    )
    
    # Mock task_runtime to raise an error
    execution_loop.task_runtime = AsyncMock()
    execution_loop.task_runtime.execute_task = AsyncMock(
        side_effect=RuntimeError("simulated failure")
    )
    
    # Mock the checkpoint creation to capture what would be saved
    captured_checkpoint = None
    
    async def mock_create(*args, **kwargs):
        nonlocal captured_checkpoint
        captured_checkpoint = {
            "args": args,
            "kwargs": kwargs,
        }
        mock_checkpoint = MagicMock()
        mock_checkpoint.id = "test-checkpoint-id"
        return mock_checkpoint
    
    checkpoint_manager.create_checkpoint = mock_create
    
    # Run a step (this should fail and trigger failure checkpoint)
    await execution_loop.step(session=session)
    
    # Verify failure checkpoint was created
    assert captured_checkpoint is not None, "FAIL: no failure checkpoint was created"
    
    # Check that error state is captured
    state_snapshot = captured_checkpoint["kwargs"].get("state_snapshot", {})
    assert "error" in state_snapshot, (
        f"FAIL: checkpoint state does not contain error field: {state_snapshot}"
    )
    assert state_snapshot["error"] == "simulated failure", (
        f"FAIL: checkpoint error is {state_snapshot['error']}, expected 'simulated failure'"
    )
