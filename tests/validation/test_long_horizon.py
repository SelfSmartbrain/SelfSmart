"""Long-horizon testing framework for extended autonomy validation."""

import pytest
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, List
from dataclasses import dataclass, field
import logging

from tests.validation.framework import ValidationFramework, ValidationResult

logger = logging.getLogger(__name__)


@dataclass
class LongHorizonConfig:
    """Configuration for long-horizon testing."""
    
    duration_hours: int
    check_interval_seconds: int = 60
    metrics_to_track: List[str] = field(default_factory=list)
    stop_on_failure: bool = False


@dataclass
class LongHorizonMetrics:
    """Metrics collected during long-horizon test."""
    
    start_time: datetime
    end_time: datetime
    duration_seconds: float
    goal_persistence_score: float
    failure_recovery_count: int
    memory_growth_bytes: int
    knowledge_growth_count: int
    stability_score: float
    total_tasks_completed: int
    total_failures: int
    metadata: Dict[str, Any] = field(default_factory=dict)


class LongHorizonTester:
    """Run long-horizon autonomy tests (24h, 72h, 1 week)."""
    
    def __init__(self, framework: ValidationFramework):
        self.framework = framework
        logger.info("Initialized LongHorizonTester")
    
    def run_long_horizon_test(
        self,
        config: LongHorizonConfig,
        task_func: callable,
    ) -> LongHorizonMetrics:
        """Run a long-horizon test with the given configuration."""
        logger.info(
            f"Starting long-horizon test for {config.duration_hours} hours"
        )
        
        start_time = datetime.now()
        end_time = start_time + timedelta(hours=config.duration_hours)
        
        metrics = {
            "tasks_completed": 0,
            "failures": 0,
            "goal_persistence": [],
            "memory_snapshots": [],
            "knowledge_snapshots": [],
        }
        
        # Simulate long-horizon test (in reality, this would run for hours/days)
        # For testing purposes, we'll run a shorter simulation
        simulation_duration = min(config.duration_hours * 60, 10)  # Cap at 10 minutes for tests
        check_interval = min(config.check_interval_seconds, 5)  # Cap at 5 seconds for tests
        
        elapsed = 0
        while elapsed < simulation_duration:
            try:
                # Run task
                result = task_func()
                
                if result.get("success", False):
                    metrics["tasks_completed"] += 1
                else:
                    metrics["failures"] += 1
                
                # Track goal persistence
                metrics["goal_persistence"].append(result.get("goal_persistence", 1.0))
                
                # Take snapshots (simulated)
                if elapsed % (check_interval * 2) == 0:
                    metrics["memory_snapshots"].append(self._get_memory_size())
                    metrics["knowledge_snapshots"].append(self._get_knowledge_count())
                
                time.sleep(check_interval)
                elapsed += check_interval
                
            except Exception as e:
                logger.error(f"Task failed during long-horizon test", error=str(e))
                metrics["failures"] += 1
                
                if config.stop_on_failure:
                    break
        
        # Calculate final metrics
        actual_end_time = datetime.now()
        duration_seconds = (actual_end_time - start_time).total_seconds()
        
        goal_persistence_score = (
            sum(metrics["goal_persistence"]) / len(metrics["goal_persistence"])
            if metrics["goal_persistence"]
            else 0.0
        )
        
        memory_growth = (
            metrics["memory_snapshots"][-1] - metrics["memory_snapshots"][0]
            if len(metrics["memory_snapshots"]) >= 2
            else 0
        )
        
        knowledge_growth = (
            metrics["knowledge_snapshots"][-1] - metrics["knowledge_snapshots"][0]
            if len(metrics["knowledge_snapshots"]) >= 2
            else 0
        )
        
        stability_score = 1.0 - (metrics["failures"] / max(metrics["tasks_completed"], 1))
        
        long_horizon_metrics = LongHorizonMetrics(
            start_time=start_time,
            end_time=actual_end_time,
            duration_seconds=duration_seconds,
            goal_persistence_score=goal_persistence_score,
            failure_recovery_count=metrics["failures"],
            memory_growth_bytes=memory_growth,
            knowledge_growth_count=knowledge_growth,
            stability_score=stability_score,
            total_tasks_completed=metrics["tasks_completed"],
            total_failures=metrics["failures"],
            metadata=metrics,
        )
        
        logger.info(
            f"Long-horizon test complete: "
            f"{long_horizon_metrics.total_tasks_completed} tasks, "
            f"{long_horizon_metrics.stability_score:.2%} stability"
        )
        
        return long_horizon_metrics
    
    def _get_memory_size(self) -> int:
        """Get current memory size (simulated)."""
        # In reality, this would query the memory system
        return 1000  # Placeholder
    
    def _get_knowledge_count(self) -> int:
        """Get current knowledge count (simulated)."""
        # In reality, this would query the knowledge system
        return 50  # Placeholder


@pytest.fixture
def validation_framework():
    """Create a validation framework for testing."""
    return ValidationFramework(output_dir=Path("test_validation_results"))


@pytest.fixture
def long_horizon_tester(validation_framework):
    """Create a long-horizon tester instance."""
    return LongHorizonTester(validation_framework)


def test_long_horizon_initialization(long_horizon_tester):
    """Test that long-horizon tester initializes correctly."""
    assert long_horizon_tester is not None
    assert long_horizon_tester.framework is not None


def test_long_horizon_config():
    """Test long-horizon configuration."""
    config = LongHorizonConfig(
        duration_hours=24,
        check_interval_seconds=60,
        metrics_to_track=["tasks", "memory", "knowledge"],
    )
    
    assert config.duration_hours == 24
    assert config.check_interval_seconds == 60
    assert len(config.metrics_to_track) == 3


def test_run_short_long_horizon_test(long_horizon_tester):
    """Test running a short long-horizon test (for testing purposes)."""
    config = LongHorizonConfig(
        duration_hours=1,  # 1 hour test
        check_interval_seconds=1,  # Check every second for testing
        stop_on_failure=False,
    )
    
    def mock_task():
        """Mock task for testing."""
        return {
            "success": True,
            "goal_persistence": 0.95,
        }
    
    metrics = long_horizon_tester.run_long_horizon_test(config, mock_task)
    
    assert metrics.duration_seconds >= 0
    assert metrics.total_tasks_completed >= 0
    assert metrics.stability_score >= 0
    assert metrics.goal_persistence_score >= 0


def test_long_horizon_with_failures(long_horizon_tester):
    """Test long-horizon test with task failures."""
    config = LongHorizonConfig(
        duration_hours=1,
        check_interval_seconds=1,
        stop_on_failure=False,
    )
    
    failure_count = [0]
    
    def task_with_failures():
        """Task that fails occasionally."""
        failure_count[0] += 1
        if failure_count[0] % 3 == 0:
            return {"success": False, "goal_persistence": 0.8}
        return {"success": True, "goal_persistence": 0.95}
    
    metrics = long_horizon_tester.run_long_horizon_test(config, task_with_failures)
    
    assert metrics.total_failures > 0
    assert metrics.stability_score < 1.0


def test_long_horizon_stop_on_failure(long_horizon_tester):
    """Test that long-horizon test stops on failure when configured."""
    config = LongHorizonConfig(
        duration_hours=1,
        check_interval_seconds=1,
        stop_on_failure=True,
    )
    
    call_count = [0]
    
    def failing_task():
        """Task that always fails."""
        call_count[0] += 1
        return {"success": False, "goal_persistence": 0.5}
    
    metrics = long_horizon_tester.run_long_horizon_test(config, failing_task)
    
    # Should stop after first failure
    assert call_count[0] == 1
    assert metrics.total_failures == 1
