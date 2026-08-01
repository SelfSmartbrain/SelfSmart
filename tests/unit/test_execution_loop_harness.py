"""
Unit tests for Execution Loop Harness - Phase 6: Continuous Execution Runtime Harness
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4
from datetime import datetime, timezone

from src.cli.execution_loop_harness import (
    FileCheckpointStore,
    ExecutionLoopHarness,
    DEFAULT_STATE_FILE,
    DEFAULT_PID_FILE,
)


class TestFileCheckpointStore:
    """Test FileCheckpointStore"""

    @pytest.fixture
    def temp_state_file(self):
        """Create a temporary state file"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_path = Path(f.name)
        yield temp_path
        # Cleanup
        if temp_path.exists():
            temp_path.unlink()
        # Also cleanup any .tmp files
        for tmp_file in temp_path.parent.glob(f".{temp_path.name}.*"):
            tmp_file.unlink(missing_ok=True)

    def test_init_creates_parent_dirs(self, temp_state_file):
        """Test that parent directories are created"""
        store = FileCheckpointStore(temp_state_file)
        assert store.path == temp_state_file

    def test_append_first_checkpoint(self, temp_state_file):
        """Test appending first checkpoint"""
        store = FileCheckpointStore(temp_state_file)

        checkpoint = store.append(
            objective_id="obj_123",
            description="Test objective",
            current_step=1,
            total_steps=5,
            status="running",
        )

        assert checkpoint["objective_id"] == "obj_123"
        assert checkpoint["state_snapshot"]["tick_count"] == 1
        assert checkpoint["progress_snapshot"]["step"] == 1
        assert checkpoint["progress_snapshot"]["total_steps"] == 5
        assert checkpoint["state_snapshot"]["status"] == "running"
        assert checkpoint["metadata"]["sequence"] == 1
        assert "created_at" in checkpoint

    def test_append_multiple_checkpoints(self, temp_state_file):
        """Test appending multiple checkpoints increments sequence"""
        store = FileCheckpointStore(temp_state_file)

        ckpt1 = store.append(objective_id="obj_1", description="Test", current_step=1, total_steps=3, status="running")
        ckpt2 = store.append(objective_id="obj_1", description="Test", current_step=2, total_steps=3, status="running")
        ckpt3 = store.append(objective_id="obj_1", description="Test", current_step=3, total_steps=3, status="completed")

        assert ckpt1["metadata"]["sequence"] == 1
        assert ckpt2["metadata"]["sequence"] == 2
        assert ckpt3["metadata"]["sequence"] == 3

    def test_latest_returns_last_checkpoint(self, temp_state_file):
        """Test latest() returns the most recent checkpoint"""
        store = FileCheckpointStore(temp_state_file)

        store.append(objective_id="obj_1", description="Test", current_step=1, total_steps=3, status="running")
        ckpt2 = store.append(objective_id="obj_1", description="Test", current_step=2, total_steps=3, status="running")
        store.append(objective_id="obj_1", description="Test", current_step=3, total_steps=3, status="completed")

        latest = store.latest("obj_1")

        assert latest is not None
        assert latest["metadata"]["sequence"] == 3
        assert latest["progress_snapshot"]["step"] == 3

    def test_latest_none_for_unknown_objective(self, temp_state_file):
        """Test latest() returns None for unknown objective"""
        store = FileCheckpointStore(temp_state_file)

        latest = store.latest("unknown_obj")

        assert latest is None

    def test_list_returns_all_checkpoints(self, temp_state_file):
        """Test list() returns all checkpoints for an objective"""
        store = FileCheckpointStore(temp_state_file)

        store.append(objective_id="obj_1", description="Test", current_step=1, total_steps=3, status="running")
        store.append(objective_id="obj_1", description="Test", current_step=2, total_steps=3, status="running")
        store.append(objective_id="obj_1", description="Test", current_step=3, total_steps=3, status="completed")

        checkpoints = store.list("obj_1")

        assert len(checkpoints) == 3
        assert checkpoints[0]["metadata"]["sequence"] == 1
        assert checkpoints[2]["metadata"]["sequence"] == 3

    def test_atomic_write(self, temp_state_file):
        """Test atomic write creates valid JSON"""
        store = FileCheckpointStore(temp_state_file)

        store.append(objective_id="obj_1", description="Test", current_step=1, total_steps=3, status="running")

        # Verify file exists and is valid JSON
        assert temp_state_file.exists()
        with temp_state_file.open() as f:
            data = json.load(f)

        assert data["version"] == 1
        assert "objectives" in data
        assert "obj_1" in data["objectives"]

    def test_read_nonexistent_file(self, temp_state_file):
        """Test reading non-existent file returns empty document"""
        # Don't create the file
        store = FileCheckpointStore(temp_state_file)

        doc = store._read_document()

        assert doc == {"version": 1, "objectives": {}}

    def test_invalid_version_raises(self, temp_state_file):
        """Test invalid version raises error"""
        # Write invalid version
        with temp_state_file.open('w') as f:
            json.dump({"version": 2, "objectives": {}}, f)

        store = FileCheckpointStore(temp_state_file)

        with pytest.raises(Exception) as exc_info:
            store._read_document()

        assert "Invalid checkpoint store" in str(exc_info.value)


class TestExecutionLoopHarness:
    """Test ExecutionLoopHarness"""

    @pytest.fixture
    def temp_files(self):
        """Create temporary state and pid files"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            state_file = Path(f.name)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pid', delete=False) as f:
            pid_file = Path(f.name)

        yield state_file, pid_file

        # Cleanup
        for p in [state_file, pid_file]:
            if p.exists():
                p.unlink()
        # Cleanup tmp files
        for tmp_file in state_file.parent.glob(f".{state_file.name}.*"):
            tmp_file.unlink(missing_ok=True)

    def test_init_validates_step_delay(self, temp_files):
        """Test that negative step_delay raises error"""
        state_file, pid_file = temp_files

        with pytest.raises(Exception) as exc_info:
            ExecutionLoopHarness(
                checkpoint_store=FileCheckpointStore(state_file),
                pid_file=pid_file,
                step_delay=-0.1,
            )

        assert "step-delay must be zero or greater" in str(exc_info.value)

    def test_run_objective_creates_checkpoints(self, temp_files):
        """Test run_objective creates checkpoints for each step"""
        state_file, pid_file = temp_files

        harness = ExecutionLoopHarness(
            checkpoint_store=FileCheckpointStore(state_file),
            pid_file=pid_file,
            step_delay=0.01,  # Fast for testing
        )

        objective_id = "test_obj_123"
        result = harness.run_objective(
            objective_id=objective_id,
            description="Test objective",
            total_steps=3,
        )

        assert result["state_snapshot"]["status"] == "completed"
        assert result["progress_snapshot"]["step"] == 3
        assert result["progress_snapshot"]["total_steps"] == 3

        # Verify checkpoints were created (step 0 + 3 steps + final completed = 5)
        store = FileCheckpointStore(state_file)
        checkpoints = store.list(objective_id)
        assert len(checkpoints) == 5  # step 0 + 3 steps + final completed

    def test_run_objective_rejects_duplicate(self, temp_files):
        """Test run_objective rejects duplicate objective_id"""
        state_file, pid_file = temp_files

        harness = ExecutionLoopHarness(
            checkpoint_store=FileCheckpointStore(state_file),
            pid_file=pid_file,
            step_delay=0.01,
        )

        objective_id = "test_obj_123"
        harness.run_objective(objective_id=objective_id, description="Test", total_steps=1)

        with pytest.raises(Exception) as exc_info:
            harness.run_objective(objective_id=objective_id, description="Test", total_steps=1)

        assert "already has checkpoints" in str(exc_info.value)

    def test_run_objective_validates_total_steps(self, temp_files):
        """Test run_objective validates total_steps >= 1"""
        state_file, pid_file = temp_files

        harness = ExecutionLoopHarness(
            checkpoint_store=FileCheckpointStore(state_file),
            pid_file=pid_file,
            step_delay=0.01,
        )

        with pytest.raises(Exception) as exc_info:
            harness.run_objective(objective_id="test", description="Test", total_steps=0)

        assert "total-steps must be at least 1" in str(exc_info.value)

    def test_restore_and_resume(self, temp_files):
        """Test restore_and_resume continues from latest checkpoint"""
        state_file, pid_file = temp_files

        harness = ExecutionLoopHarness(
            checkpoint_store=FileCheckpointStore(state_file),
            pid_file=pid_file,
            step_delay=0.01,
        )

        objective_id = "test_obj_123"
        # First run completes 2 of 5 steps - manually create checkpoints to simulate this
        store = FileCheckpointStore(state_file)
        # Simulate: objective was created with total_steps=5, but only 2 steps completed
        store.append(objective_id=objective_id, description="Test objective", current_step=0, total_steps=5, status="running")
        store.append(objective_id=objective_id, description="Test objective", current_step=1, total_steps=5, status="running")
        store.append(objective_id=objective_id, description="Test objective", current_step=2, total_steps=5, status="running")

        # Now restore and resume - should continue from step 2 to step 5
        result = harness.restore_and_resume(objective_id)

        assert result["progress_snapshot"]["step"] == 5
        assert result["progress_snapshot"]["total_steps"] == 5
        assert result["state_snapshot"]["status"] == "completed"

        # Verify all checkpoints exist
        checkpoints = store.list(objective_id)
        # Should have: step 0, 1, 2 (original) + 3, 4, 5 (running) + final completed = 7
        assert len(checkpoints) == 7

    def test_restore_and_resume_nonexistent_fails(self, temp_files):
        """Test restore_and_resume fails for nonexistent objective"""
        state_file, pid_file = temp_files

        harness = ExecutionLoopHarness(
            checkpoint_store=FileCheckpointStore(state_file),
            pid_file=pid_file,
            step_delay=0.01,
        )

        with pytest.raises(Exception) as exc_info:
            harness.restore_and_resume("nonexistent")

        assert "No checkpoint found" in str(exc_info.value)

    def test_restore_completed_objective_returns_immediately(self, temp_files):
        """Test restore on completed objective returns immediately"""
        state_file, pid_file = temp_files

        harness = ExecutionLoopHarness(
            checkpoint_store=FileCheckpointStore(state_file),
            pid_file=pid_file,
            step_delay=0.01,
        )

        objective_id = "test_obj_123"
        # Complete the objective
        harness.run_objective(objective_id=objective_id, description="Test", total_steps=2)

        # Restore should return immediately with completed status
        result = harness.restore_and_resume(objective_id)

        assert result["state_snapshot"]["status"] == "completed"

    def test_pid_file_management(self, temp_files):
        """Test PID file is created and removed"""
        state_file, pid_file = temp_files

        harness = ExecutionLoopHarness(
            checkpoint_store=FileCheckpointStore(state_file),
            pid_file=pid_file,
            step_delay=0.01,
        )

        objective_id = "test_obj_123"
        harness.run_objective(objective_id=objective_id, description="Test", total_steps=1)

        # PID file should be cleaned up after completion
        assert not pid_file.exists()

    def test_kill_command_reads_pid(self, temp_files):
        """Test kill command reads PID from file"""
        state_file, pid_file = temp_files

        # Write a fake PID
        pid_file.write_text("99999", encoding="utf-8")

        # Mock os.kill to avoid actually killing process
        with patch('os.kill') as mock_kill:
            from src.cli.execution_loop_harness import kill
            from click.testing import CliRunner

            runner = CliRunner()
            result = runner.invoke(kill, ['--pid-file', str(pid_file)])

            mock_kill.assert_called_once_with(99999, 9)  # SIGKILL = 9
            assert result.exit_code == 0

    def test_kill_command_missing_pid_file(self, temp_files):
        """Test kill command fails if PID file missing"""
        state_file, pid_file = temp_files
        # Don't create pid_file - it shouldn't exist at all
        if pid_file.exists():
            pid_file.unlink()

        from src.cli.execution_loop_harness import kill
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(kill, ['--pid-file', str(pid_file)])

        assert result.exit_code != 0
        assert "PID file not found" in result.output

    def test_kill_command_invalid_pid(self, temp_files):
        """Test kill command fails if PID file has invalid content"""
        state_file, pid_file = temp_files
        pid_file.write_text("not_a_number", encoding="utf-8")

        from src.cli.execution_loop_harness import kill
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(kill, ['--pid-file', str(pid_file)])

        assert result.exit_code != 0
        assert "Invalid PID file" in result.output

    def test_list_checkpoints_command(self, temp_files):
        """Test list-checkpoints command"""
        state_file, pid_file = temp_files

        # Create some checkpoints
        store = FileCheckpointStore(state_file)
        store.append(objective_id="obj_1", description="Test", current_step=1, total_steps=3, status="running")
        store.append(objective_id="obj_1", description="Test", current_step=2, total_steps=3, status="running")
        store.append(objective_id="obj_1", description="Test", current_step=3, total_steps=3, status="completed")

        from src.cli.execution_loop_harness import list_checkpoints
        from click.testing import CliRunner

        runner = CliRunner()
        result = runner.invoke(list_checkpoints, ['obj_1', '--state-file', str(state_file)])

        assert result.exit_code == 0
        assert "harness_0001" in result.output
        assert "harness_0002" in result.output
        assert "harness_0003" in result.output
        assert "completed" in result.output


class TestCheckpointSurvival:
    """Test checkpoint survival across process restarts"""

    @pytest.fixture
    def temp_files(self):
        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            state_file = Path(f.name)
        with tempfile.NamedTemporaryFile(mode='w', suffix='.pid', delete=False) as f:
            pid_file = Path(f.name)

        yield state_file, pid_file

        for p in [state_file, pid_file]:
            if p.exists():
                p.unlink()
        for tmp_file in state_file.parent.glob(f".{state_file.name}.*"):
            tmp_file.unlink(missing_ok=True)

    def test_checkpoint_survives_process_restart(self, temp_files):
        """Test that checkpoints survive process restart (simulated by new harness instance)"""
        state_file, pid_file = temp_files

        # First harness instance runs 2 steps of 5
        store = FileCheckpointStore(state_file)
        objective_id = "survival_test_obj"
        # Simulate partial completion: 2 of 5 steps
        store.append(objective_id=objective_id, description="Survival test", current_step=0, total_steps=5, status="running")
        store.append(objective_id=objective_id, description="Survival test", current_step=1, total_steps=5, status="running")
        store.append(objective_id=objective_id, description="Survival test", current_step=2, total_steps=5, status="running")

        # Verify checkpoints exist
        checkpoints = store.list(objective_id)
        assert len(checkpoints) == 3  # step 0, 1, 2

        # Simulate process restart by creating new harness instance
        harness2 = ExecutionLoopHarness(
            checkpoint_store=FileCheckpointStore(state_file),
            pid_file=pid_file,
            step_delay=0.01,
        )

        # Resume from step 2 to step 5
        result = harness2.restore_and_resume(objective_id)

        assert result["progress_snapshot"]["step"] == 5
        assert result["progress_snapshot"]["total_steps"] == 5
        assert result["state_snapshot"]["status"] == "completed"

        # Verify all checkpoints still exist
        checkpoints = store.list(objective_id)
        # Should have: step 0, 1, 2 (original) + 3, 4, 5 (running) + final completed = 7
        assert len(checkpoints) == 7

    def test_checkpoint_data_integrity(self, temp_files):
        """Test that checkpoint data maintains integrity"""
        state_file, pid_file = temp_files

        harness = ExecutionLoopHarness(
            checkpoint_store=FileCheckpointStore(state_file),
            pid_file=pid_file,
            step_delay=0.01,
        )

        objective_id = "integrity_test"
        description = "Test data integrity"
        total_steps = 3

        harness.run_objective(objective_id=objective_id, description=description, total_steps=total_steps)

        store = FileCheckpointStore(state_file)
        checkpoints = store.list(objective_id)

        # Should have 5 checkpoints: step 0, 1, 2, 3 running + final completed
        assert len(checkpoints) == 5

        for i, ckpt in enumerate(checkpoints):
            assert ckpt["objective_id"] == objective_id
            assert ckpt["state_snapshot"]["objective_description"] == description
            assert ckpt["progress_snapshot"]["total_steps"] == total_steps
            # Step should be i for steps 0-3, then final completed also at step 3
            expected_step = i if i < total_steps else total_steps
            assert ckpt["progress_snapshot"]["step"] == expected_step
            assert ckpt["metadata"]["type"] == "process_harness"
            assert "created_at" in ckpt


if __name__ == "__main__":
    pytest.main([__file__, "-v"])