"""
Independent test — not derived from test_phase_14_17_integration.py.
Tests failure-type-specific recovery logic in AutonomyRecovery.
"""
import pytest
from src.autonomy.autonomy_recovery import AutonomyRecovery

@pytest.mark.asyncio
async def test_network_timeout_vs_validation_error_differ():
    """Test that different failure types produce different recovery actions."""
    recovery = AutonomyRecovery()

    # Failure type 1: transient/retryable (e.g. network timeout)
    result_a = await recovery.handle_failure(
        error_message="Network timeout occurred",
        exception_type="TimeoutError",
        context={"attempt": 1, "objective_id": "x"},
    )

    # Failure type 2: non-retryable / structural (e.g. validation error
    # on the objective itself — retrying won't help)
    result_b = await recovery.handle_failure(
        error_message="Invalid input validation failed",
        exception_type="ValueError",
        context={"attempt": 1, "objective_id": "x"},
    )

    # FAIL if both produce the same action (e.g. both just "retry")
    assert result_a["recovery_action"]["strategy"] != result_b["recovery_action"]["strategy"], (
        f"FAIL: both failure types produced action={result_a['recovery_action']['strategy']!r}; "
        "this suggests a single generic handler regardless of label"
    )

@pytest.mark.asyncio
async def test_exponential_backoff_actually_increases():
    """Test that backoff increases exponentially across attempts."""
    recovery = AutonomyRecovery()
    delays = []
    for attempt in range(1, 5):
        result = await recovery.handle_failure(
            error_message="Network timeout occurred",
            exception_type="TimeoutError",
            context={"attempt": attempt, "objective_id": "x"},
        )
        backoff = result["recovery_action"]["parameters"].get("backoff_seconds", 0)
        delays.append(backoff)

    # FAIL if backoff is flat or non-monotonic
    assert all(delays[i] < delays[i+1] for i in range(len(delays)-1)), (
        f"FAIL: backoff did not increase across attempts: {delays}"
    )

@pytest.mark.asyncio
async def test_unrecoverable_failure_escalates_to_human_not_silent_retry():
    """Test that unrecoverable failures escalate to human oversight."""
    recovery = AutonomyRecovery()
    result = await recovery.handle_failure(
        error_message="Self-modification rejected by safety gate",
        exception_type="PermissionError",
        context={"attempt": 1, "objective_id": "x"},
    )
    # Unknown failures should escalate to human intervention
    assert result["recovery_action"]["strategy"] in ["request_human_intervention", "escalate"], (
        f"FAIL: a forbidden/self-modify failure was handled as {result['recovery_action']['strategy']!r} "
        "instead of escalating — this is a safety-relevant gap, not a minor miss"
    )
