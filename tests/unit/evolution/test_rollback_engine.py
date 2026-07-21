"""
Unit tests for the RollbackEngine module.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock
import asyncio

from src.evolution.rollback_engine import RollbackEngine, ArchitectureRollback


class TestRollbackEngine:
    """Test cases for the RollbackEngine class."""

    def test_init_default(self):
        """Test initialization of RollbackEngine with default parameters."""
        engine = RollbackEngine()
        assert isinstance(engine, RollbackEngine)
        assert engine.cooldown_period == 300.0  # Default value
        assert engine.last_rollback_time == 0.0

    def test_init_custom_cooldown(self):
        """Test initialization of RollbackEngine with custom cooldown period."""
        engine = RollbackEngine(cooldown_period=60.0)
        assert isinstance(engine, RollbackEngine)
        assert engine.cooldown_period == 60.0
        assert engine.last_rollback_time == 0.0

    @pytest.mark.asyncio
    async def test_monitor_canary_no_rollback_needed(self):
        """Test monitoring a canary when no rollback is needed."""
        engine = RollbackEngine()
        deployment_id = uuid.uuid4()
        previous_stable_version_id = uuid.uuid4()
        
        # Failure rate below threshold
        current_failure_rate = 0.01
        threshold_failure_rate = 0.05
        
        result = await engine.monitor_canary(
            deployment_id, current_failure_rate, threshold_failure_rate, previous_stable_version_id
        )
        
        assert result is None  # No rollback needed

    @pytest.mark.asyncio
    async def test_monitor_canary_rollback_needed(self):
        """Test monitoring a canary when rollback is needed."""
        engine = RollbackEngine()
        deployment_id = uuid.uuid4()
        previous_stable_version_id = uuid.uuid4()
        
        # Failure rate above threshold
        current_failure_rate = 0.08
        threshold_failure_rate = 0.05
        
        result = await engine.monitor_canary(
            deployment_id, current_failure_rate, threshold_failure_rate, previous_stable_version_id
        )
        
        assert result is not None
        assert isinstance(result, ArchitectureRollback)
        assert result.deployment_id == deployment_id
        assert result.reverted_to_version_id == previous_stable_version_id
        assert result.failure_rate == current_failure_rate
        assert "exceeded threshold" in result.reason
        assert result.rollback_time is not None

    @pytest.mark.asyncio
    async def test_monitor_canary_cooldown_period(self):
        """Test that rollback respects cooldown period."""
        engine = RollbackEngine(cooldown_period=0.1)  # Short cooldown for testing
        deployment_id = uuid.uuid4()
        previous_stable_version_id = uuid.uuid4()
        
        # Failure rate above threshold - should trigger rollback
        current_failure_rate = 0.08
        threshold_failure_rate = 0.05
        
        result1 = await engine.monitor_canary(
            deployment_id, current_failure_rate, threshold_failure_rate, previous_stable_version_id
        )
        assert result1 is not None  # First call should trigger rollback
        
        # Immediate second call - should be in cooldown
        result2 = await engine.monitor_canary(
            deployment_id, current_failure_rate, threshold_failure_rate, previous_stable_version_id
        )
        assert result2 is None  # Should be in cooldown period
        
        # Wait for cooldown to expire
        await asyncio.sleep(0.15)
        
        # Third call after cooldown - should trigger rollback again
        result3 = await engine.monitor_canary(
            deployment_id, current_failure_rate, threshold_failure_rate, previous_stable_version_id
        )
        assert result3 is not None  # Should trigger rollback again after cooldown

    @pytest.mark.asyncio
    async def test_execute_rollback(self):
        """Test executing a rollback operation."""
        engine = RollbackEngine()
        
        rollback = ArchitectureRollback(
            rollback_id=uuid.uuid4(),
            deployment_id=uuid.uuid4(),
            reverted_to_version_id=uuid.uuid4(),
            rollback_time=datetime.now(timezone.utc),
            reason="Test rollback",
            failure_rate=0.08
        )
        
        result = await engine.execute_rollback(rollback)
        assert result is True  # Should succeed in simulation

    def test_architecture_rollback_model(self):
        """Test the ArchitectureRollback model."""
        rollback_time = datetime.now(timezone.utc)
        rollback = ArchitectureRollback(
            rollback_id=uuid.uuid4(),
            deployment_id=uuid.uuid4(),
            reverted_to_version_id=uuid.uuid4(),
            rollback_time=rollback_time,
            reason="Test reason",
            failure_rate=0.05
        )
        
        assert isinstance(rollback.rollback_id, uuid.UUID)
        assert isinstance(rollback.deployment_id, uuid.UUID)
        assert isinstance(rollback.reverted_to_version_id, uuid.UUID)
        assert rollback.reason == "Test reason"
        assert rollback.failure_rate == 0.05
        assert rollback.rollback_time == rollback_time
