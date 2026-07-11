"""Integration tests for Phase 14-17 components.

Tests the actual behavior of:
- ExecutionLoop checkpointing integration
- ObjectiveManager autonomous generation
- AutonomyRecovery failure handling
- AssumptionDetector testing loop
- SelfPatchSafetyGate sandbox testing
"""

import pytest
import asyncio
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, AsyncMock, patch

from src.runtime.execution_loop import ExecutionLoop, LoopStepResult
from src.runtime.agent_runtime import AgentRuntime
from src.autonomy.objective_manager import ObjectiveManager, Objective
from src.autonomy.checkpoint_manager import CheckpointManager, RuntimeRecovery
from src.autonomy.autonomy_recovery import AutonomyRecovery, FailureType, RecoveryStrategy
from src.governance.assumption_detector import AssumptionDetector, Assumption, AssumptionType
from src.safety.self_patch_safety_gate import (
    SelfPatchSafetyGate,
    PatchSafetyLevel,
    TestResult,
    FileChange,
)


@pytest.fixture
def objective_manager():
    """Create a test ObjectiveManager."""
    return ObjectiveManager()


@pytest.fixture
def checkpoint_manager():
    """Create a mock CheckpointManager."""
    manager = Mock(spec=CheckpointManager)
    manager.create_checkpoint = AsyncMock()
    manager.get_latest_checkpoint = AsyncMock(return_value=None)
    return manager


@pytest.fixture
def execution_loop(checkpoint_manager):
    """Create an ExecutionLoop with checkpointing enabled."""
    return ExecutionLoop(
        checkpoint_manager=checkpoint_manager,
        auto_checkpoint_interval=2,
    )


class TestExecutionLoopCheckpointing:
    """Tests for ExecutionLoop checkpointing integration."""
    
    @pytest.mark.asyncio
    async def test_auto_checkpoint_on_progress(self, execution_loop, checkpoint_manager):
        """Test that automatic checkpoints are created on progress."""
        # Setup
        objective = Objective(description="Test objective", priority=0.8)
        execution_loop.objective_manager.active_objectives = [objective]
        execution_loop.objective_manager.session = Mock()
        
        # Run steps to trigger checkpoint
        with patch.object(execution_loop, '_process_objective', return_value={}):
            with patch.object(execution_loop.task_runtime, 'execute_task', return_value={"status": "completed"}):
                session = Mock()
                
                # Step 1 - no checkpoint (tick 1)
                await execution_loop.step(session)
                assert checkpoint_manager.create_checkpoint.call_count == 0
                
                # Step 2 - checkpoint created (tick 2, interval=2)
                await execution_loop.step(session)
                assert checkpoint_manager.create_checkpoint.call_count == 1
    
    @pytest.mark.asyncio
    async def test_checkpoint_on_failure(self, execution_loop, checkpoint_manager):
        """Test that checkpoints are created on failure."""
        # Setup
        objective = Objective(description="Test objective", priority=0.8)
        execution_loop.objective_manager.active_objectives = [objective]
        execution_loop.objective_manager.session = Mock()
        
        # Simulate failure
        with patch.object(execution_loop, '_process_objective', side_effect=Exception("Test error")):
            session = Mock()
            
            await execution_loop.step(session)
            
            # Should have created a failure checkpoint
            assert checkpoint_manager.create_checkpoint.call_count >= 1


class TestObjectiveManagerTemplateSuggestion:
    """Tests for ObjectiveManager template-based follow-up suggestions."""
    
    @pytest.mark.asyncio
    async def test_suggest_followup_template_from_completed(self, objective_manager):
        """Test a follow-up template suggestion from a completed objective."""
        # Setup: add a completed objective
        completed = Objective(
            description="Implement feature X",
            priority=0.7,
            status="completed",
        )
        objective_manager.completed_objectives = [completed]
        
        # Generate next objective
        session = Mock()
        session.commit = AsyncMock()
        session.flush = AsyncMock()
        objective_manager.save_objective = AsyncMock()
        
        next_obj = await objective_manager.suggest_followup_template(
            session,
            context={"follow_up_pattern": 0},
        )
        
        assert next_obj is not None
        assert next_obj.metadata.get("autonomous") is False  # Template-based, not autonomous
        assert next_obj.metadata.get("generation_method") == "template_based"
        assert "Implement feature X" in next_obj.description or "feature X" in next_obj.description.lower()
        assert next_obj.status == "active"
        assert next_obj in objective_manager.active_objectives
    
    @pytest.mark.asyncio
    async def test_no_generation_without_completed(self, objective_manager):
        """Test that no objective is generated without completed objectives."""
        objective_manager.completed_objectives = []
        
        session = Mock()
        next_obj = await objective_manager.suggest_followup_template(session)
        
        assert next_obj is None
    
    @pytest.mark.asyncio
    async def test_should_generate_when_idle(self, objective_manager):
        """Test generation decision when idle with history."""
        objective_manager.active_objectives = []
        objective_manager.completed_objectives = [
            Objective(description="Test", status="completed"),
        ]
        
        should_generate = await objective_manager.should_suggest_followup_template()
        assert should_generate is True
    
    @pytest.mark.asyncio
    async def test_should_not_generate_when_active(self, objective_manager):
        """Test that generation is skipped when objectives are active."""
        objective_manager.active_objectives = [
            Objective(description="Active objective", status="active"),
        ]
        objective_manager.completed_objectives = [
            Objective(description="Test", status="completed"),
        ]
        
        should_generate = await objective_manager.should_suggest_followup_template()
        assert should_generate is False
    
    @pytest.mark.asyncio
    async def test_context_override_generation(self, objective_manager):
        """Test context override for generation decision."""
        objective_manager.active_objectives = []
        objective_manager.completed_objectives = [
            Objective(description="Test", status="completed"),
        ]
        
        # Force generation
        should_generate = await objective_manager.should_suggest_followup_template(
            context={"force_followup_suggestion": True}
        )
        assert should_generate is True
        
        # Disable generation
        should_generate = await objective_manager.should_suggest_followup_template(
            context={"disable_followup_suggestion": True}
        )
        assert should_generate is False


class TestAutonomyRecovery:
    """Tests for AutonomyRecovery failure handling."""
    
    def test_classify_timeout_failure(self):
        """Test classification of timeout failures."""
        recovery = AutonomyRecovery()
        
        failure_type = recovery.classify_failure("Operation timed out")
        assert failure_type == FailureType.TIMEOUT
        
        failure_type = recovery.classify_failure("TimeoutError: connection timed out")
        assert failure_type == FailureType.TIMEOUT
    
    def test_classify_resource_failure(self):
        """Test classification of resource failures."""
        recovery = AutonomyRecovery()
        
        failure_type = recovery.classify_failure("Out of memory")
        assert failure_type == FailureType.RESOURCE_EXHAUSTION
    
    def test_classify_tool_failure(self):
        """Test classification of tool failures."""
        recovery = AutonomyRecovery()
        
        failure_type = recovery.classify_failure("Tool 'search' failed")
        assert failure_type == FailureType.TOOL_FAILURE
    
    def test_determine_retry_with_backoff(self):
        """Test retry with backoff strategy."""
        recovery = AutonomyRecovery()
        
        from src.autonomy.autonomy_recovery import FailureContext, RecoveryAction
        
        context = FailureContext(
            failure_type=FailureType.TIMEOUT,
            error_message="Timeout",
            retry_count=0,
        )
        
        action = recovery.determine_recovery_action(context)
        assert action.strategy == RecoveryStrategy.RETRY_WITH_BACKOFF
        assert "backoff" in action.description.lower()
        assert action.parameters.get("backoff_seconds") > 0
    
    def test_exponential_backoff_calculation(self):
        """Test exponential backoff calculation."""
        recovery = AutonomyRecovery(base_backoff_seconds=1.0, max_backoff_seconds=60.0)
        
        backoff_0 = recovery._calculate_backoff(0)
        backoff_1 = recovery._calculate_backoff(1)
        backoff_2 = recovery._calculate_backoff(2)
        
        assert backoff_0 == 1.0
        assert backoff_1 == 2.0
        assert backoff_2 == 4.0
    
    def test_max_backoff_limit(self):
        """Test that backoff is capped at max."""
        recovery = AutonomyRecovery(base_backoff_seconds=1.0, max_backoff_seconds=10.0)
        
        backoff_10 = recovery._calculate_backoff(10)
        assert backoff_10 <= 10.0
    
    @pytest.mark.asyncio
    async def test_execute_retry_with_backoff(self):
        """Test execution of retry with backoff."""
        recovery = AutonomyRecovery(base_backoff_seconds=0.1)  # Fast for testing
        
        from src.autonomy.autonomy_recovery import FailureContext, RecoveryAction
        
        context = FailureContext(
            failure_type=FailureType.TIMEOUT,
            error_message="Timeout",
            retry_count=0,
        )
        
        action = RecoveryAction(
            strategy=RecoveryStrategy.RETRY_WITH_BACKOFF,
            description="Retry with backoff",
            parameters={"backoff_seconds": 0.1},
        )
        
        result = await recovery.execute_recovery(context, action)
        
        assert result["success"] is True
        assert "backoff" in result["message"].lower()
    
    @pytest.mark.asyncio
    async def test_handle_failure_end_to_end(self):
        """Test end-to-end failure handling."""
        recovery = AutonomyRecovery(base_backoff_seconds=0.1)
        
        result = await recovery.handle_failure(
            error_message="Operation timed out",
            exception_type="TimeoutError",
            context={"objective_id": "obj_123"},
        )
        
        assert "failure_context" in result
        assert "recovery_action" in result
        assert "recovery_result" in result
        assert result["failure_context"]["failure_type"] == FailureType.TIMEOUT.value
        assert result["should_retry"] is True


class TestAssumptionDetectorTesting:
    """Tests for AssumptionDetector testing loop."""
    
    @pytest.mark.asyncio
    async def test_assumption_with_context(self):
        """Test assumption testing with context."""
        detector = AssumptionDetector()
        
        assumption = Assumption(
            assumption_type=AssumptionType.RESOURCE,
            description="We have enough compute resources",
            testable=True,
        )
        
        test_context = {
            "available_resources": {"compute": "high", "memory": "sufficient"},
        }
        
        tested = await detector.test_assumption(assumption, test_context)
        
        assert tested.tested is True
        assert tested.test_result is True
    
    @pytest.mark.asyncio
    async def test_assumption_without_context(self):
        """Test assumption testing without context."""
        detector = AssumptionDetector()
        
        assumption = Assumption(
            assumption_type=AssumptionType.RESOURCE,
            description="We have enough compute resources",
            testable=True,
        )
        
        tested = await detector.test_assumption(assumption)  # No context
        
        assert tested.tested is True
        assert tested.test_result is False  # Should fail without context
    
    @pytest.mark.asyncio
    async def test_untestable_assumption(self):
        """Test that untestable assumptions are marked appropriately."""
        detector = AssumptionDetector()
        
        assumption = Assumption(
            assumption_type=AssumptionType.UNCERTAINTY,
            description="Market conditions will remain stable",
            testable=False,
        )
        
        tested = await detector.test_assumption(assumption)
        
        assert tested.tested is True
        assert tested.test_result is None
    
    @pytest.mark.asyncio
    async def test_batch_testing(self):
        """Test batch assumption testing."""
        detector = AssumptionDetector()
        
        assumptions = [
            Assumption(
                assumption_type=AssumptionType.RESOURCE,
                description="Resource 1",
                testable=True,
            ),
            Assumption(
                assumption_type=AssumptionType.TIME,
                description="Time constraint",
                testable=True,
            ),
        ]
        
        test_context = {
            "available_resources": {"compute": "high"},
            "time_horizon": "medium",
        }
        
        tested = await detector.test_assumptions_batch(assumptions, test_context)
        
        assert len(tested) == 2
        assert all(a.tested for a in tested)
    
    @pytest.mark.asyncio
    async def test_invalidate_assumption(self):
        """Test assumption invalidation."""
        detector = AssumptionDetector()
        
        assumption = Assumption(
            assumption_type=AssumptionType.RESOURCE,
            description="Resource assumption",
            testable=True,
        )
        
        invalidated = await detector.invalidate_assumption(assumption, "Resource not available")
        
        assert invalidated.tested is True
        assert invalidated.test_result is False
        assert invalidated.metadata.get("invalidated") is True
        assert invalidated.metadata.get("invalidation_reason") == "Resource not available"
    
    @pytest.mark.asyncio
    async def test_retest_invalidated_assumptions(self):
        """Test re-testing of invalidated assumptions."""
        detector = AssumptionDetector()
        
        assumptions = [
            Assumption(
                assumption_type=AssumptionType.RESOURCE,
                description="Resource 1",
                testable=True,
            )
        ]
        
        # Invalidate first
        await detector.invalidate_assumption(assumptions[0], "Test invalidation")
        
        # Re-test
        test_context = {"available_resources": {"compute": "high"}}
        retested = await detector.retest_invalidated_assumptions(assumptions, test_context)
        
        assert len(retested) == 1
        assert retested[0].metadata.get("invalidated") is False
    
    def test_test_summary(self):
        """Test assumption test summary."""
        detector = AssumptionDetector()
        
        assumptions = [
            Assumption(tested=True, test_result=True),
            Assumption(tested=True, test_result=False),
            Assumption(tested=False, test_result=None),
        ]
        
        summary = detector.get_assumption_test_summary(assumptions)
        
        assert summary["total_assumptions"] == 3
        assert summary["tested"] == 2
        assert summary["untested"] == 1
        assert summary["passed"] == 1
        assert summary["failed"] == 1


class TestSelfPatchSafetyGate:
    """Tests for SelfPatchSafetyGate."""
    
    @pytest.fixture
    def safety_gate(self, tmp_path):
        """Create a SafetyGate with a temporary repository."""
        return SelfPatchSafetyGate(repository_path=str(tmp_path))
    
    def test_critical_path_detection(self, safety_gate):
        """Test detection of critical file paths."""
        assert safety_gate._is_critical_path("src/runtime/execution_loop.py") is True
        assert safety_gate._is_critical_path("src/autonomy/objective_manager.py") is True
        assert safety_gate._is_critical_path("src/api/auth.py") is True
        assert safety_gate._is_critical_path("src/utils/helpers.py") is False
    
    def test_forbidden_path_detection(self, safety_gate):
        """Test detection of forbidden file paths."""
        assert safety_gate._is_forbidden_path("src/safety/self_patch_safety_gate.py") is True
        assert safety_gate._is_forbidden_path("src/runtime/execution_loop.py") is False
    
    def test_blast_radius_calculation(self, safety_gate):
        """Test blast radius calculation."""
        changes = [
            FileChange(file_path="src/utils/helpers.py", operation="write"),
            FileChange(file_path="src/runtime/execution_loop.py", operation="write"),
        ]
        
        radius = safety_gate._calculate_blast_radius(changes)
        
        assert radius > 0.0
        assert radius <= 1.0
    
    def test_safety_check_safe_patch(self, safety_gate):
        """Test safety check for a safe patch."""
        changes = [
            FileChange(
                file_path="src/utils/helpers.py",
                operation="write",
                new_content="def helper(): pass",
            )
        ]
        
        check = safety_gate.perform_safety_check(changes)
        
        assert check.safety_level == PatchSafetyLevel.SAFE
        assert check.can_apply is True
        assert check.requires_human_approval is False
        assert len(check.critical_files_touched) == 0
    
    def test_safety_check_critical_patch(self, safety_gate):
        """Test safety check for a critical patch."""
        changes = [
            FileChange(
                file_path="src/runtime/execution_loop.py",
                operation="write",
                new_content="# critical change",
            )
        ]
        
        check = safety_gate.perform_safety_check(changes)
        
        assert check.safety_level == PatchSafetyLevel.CRITICAL
        assert check.requires_human_approval is True
        assert len(check.critical_files_touched) > 0
    
    def test_safety_check_forbidden_patch(self, safety_gate):
        """Test safety check for a forbidden patch."""
        changes = [
            FileChange(
                file_path="src/safety/self_patch_safety_gate.py",
                operation="write",
                new_content="# forbidden change",
            )
        ]
        
        check = safety_gate.perform_safety_check(changes)
        
        assert check.safety_level == PatchSafetyLevel.FORBIDDEN
        assert check.can_apply is False
        assert len(check.forbidden_files_touched) > 0
        assert check.rejection_reason is not None
    
    def test_large_diff_requires_approval(self, safety_gate):
        """Test that large diffs require human approval."""
        large_content = "x" * 6000  # Exceeds MAX_AUTO_APPROVE_DIFF_SIZE
        
        changes = [
            FileChange(
                file_path="src/utils/helpers.py",
                operation="write",
                new_content=large_content,
            )
        ]
        
        check = safety_gate.perform_safety_check(changes)
        
        assert check.safety_level == PatchSafetyLevel.MODERATE
        assert check.requires_human_approval is True
    
    @pytest.mark.asyncio
    async def test_patch_rejection_without_human_approval(self, safety_gate):
        """Test that critical patches are rejected without human approval."""
        changes = [
            FileChange(
                file_path="src/runtime/execution_loop.py",
                operation="write",
                new_content="# critical change",
            )
        ]
        
        result = await safety_gate.apply_patch_with_safety(
            file_changes=changes,
            human_approval=False,
            skip_tests=True,
        )
        
        assert result.success is False
        assert result.rejection_reason is not None
        assert "human approval" in result.rejection_reason.lower()
    
    @pytest.mark.asyncio
    async def test_forbidden_patch_always_rejected(self, safety_gate):
        """Test that forbidden patches are always rejected."""
        changes = [
            FileChange(
                file_path="src/safety/self_patch_safety_gate.py",
                operation="write",
                new_content="# forbidden",
            )
        ]
        
        result = await safety_gate.apply_patch_with_safety(
            file_changes=changes,
            human_approval=True,  # Even with approval
            skip_tests=True,
        )
        
        assert result.success is False
        assert result.rejection_reason is not None
    
    def test_patch_statistics(self, safety_gate):
        """Test patch statistics tracking."""
        # Initially empty
        stats = safety_gate.get_patch_statistics()
        assert stats["total_patches_applied"] == 0
        assert stats["total_patches_rejected"] == 0


class TestIntegrationEndToEnd:
    """End-to-end integration tests."""
    
    @pytest.mark.asyncio
    async def test_full_recovery_flow(self):
        """Test full recovery flow from failure to recovery."""
        recovery = AutonomyRecovery(base_backoff_seconds=0.1)
        
        # Simulate a failure
        result = await recovery.handle_failure(
            error_message="Tool 'search' failed",
            context={"tool_name": "search", "objective_id": "obj_123"},
        )
        
        # Verify classification
        assert result["failure_context"]["failure_type"] == FailureType.TOOL_FAILURE.value
        
        # Verify recovery action
        assert result["recovery_action"]["strategy"] == RecoveryStrategy.RETRY_IMMEDIATE.value
        
        # Verify recovery execution
        assert result["recovery_result"]["success"] is True
        
        # Verify statistics
        stats = recovery.get_failure_statistics()
        assert stats["total_failures"] == 1
    
    @pytest.mark.asyncio
    async def test_assumption_lifecycle(self):
        """Test full assumption lifecycle: detect -> test -> invalidate -> retest."""
        detector = AssumptionDetector()
        
        # Detect assumption
        assumptions = detector.detect_assumptions(
            "We have enough resources to complete this task",
            context={"available_resources": {"compute": "high"}},
        )
        
        assert len(assumptions) > 0
        assumption = assumptions[0]
        
        # Test assumption
        test_context = {"available_resources": {"compute": "high"}}
        tested = await detector.test_assumption(assumption, test_context)
        assert tested.tested is True
        
        # Invalidate assumption
        invalidated = await detector.invalidate_assumption(tested, "Resources depleted")
        assert invalidated.metadata.get("invalidated") is True
        
        # Re-test assumption
        retested = await detector.retest_invalidated_assumptions([invalidated], test_context)
        assert retested[0].metadata.get("invalidated") is False
