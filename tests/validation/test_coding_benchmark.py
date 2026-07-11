"""Coding capability benchmark tests."""

import pytest
from pathlib import Path

from tests.validation.benchmarks import CodingBenchmark, CodingTask, CodingTaskType
from tests.validation.framework import ValidationFramework


@pytest.fixture
def validation_framework():
    """Create a validation framework for testing."""
    return ValidationFramework(output_dir=Path("test_validation_results"))


@pytest.fixture
def coding_benchmark(validation_framework):
    """Create a coding benchmark instance."""
    return CodingBenchmark(validation_framework)


def test_coding_benchmark_initialization(coding_benchmark):
    """Test that coding benchmark initializes correctly."""
    assert coding_benchmark is not None
    assert len(coding_benchmark.tasks) == 0


def test_add_coding_task(coding_benchmark):
    """Test adding coding tasks to the benchmark."""
    task = CodingTask(
        task_id="test_bug_fix_1",
        task_type=CodingTaskType.BUG_FIXING,
        description="Fix a simple bug in the codebase",
        difficulty="easy",
    )
    
    coding_benchmark.add_task(task)
    assert len(coding_benchmark.tasks) == 1
    assert coding_benchmark.tasks[0].task_id == "test_bug_fix_1"


def test_run_single_task(coding_benchmark):
    """Test running a single coding task."""
    task = CodingTask(
        task_id="test_feature_1",
        task_type=CodingTaskType.FEATURE_IMPLEMENTATION,
        description="Implement a simple feature",
        difficulty="easy",
    )
    
    coding_benchmark.add_task(task)
    result = coding_benchmark.run_task(task)
    
    assert result.task_id == "test_feature_1"
    assert result.time_taken_seconds >= 0


def test_run_benchmark_suite(coding_benchmark):
    """Test running the full benchmark suite."""
    # Add multiple tasks
    tasks = [
        CodingTask(
            task_id=f"task_{i}",
            task_type=list(CodingTaskType)[i % len(CodingTaskType)],
            description=f"Test task {i}",
            difficulty="easy",
        )
        for i in range(5)
    ]
    
    for task in tasks:
        coding_benchmark.add_task(task)
    
    results = coding_benchmark.run_benchmark_suite()
    
    assert results["total_tasks"] == 5
    assert "success_rate" in results
    assert "average_time_seconds" in results
    assert "results" in results


def test_coding_task_types():
    """Test that all coding task types are defined."""
    task_types = [
        CodingTaskType.BUG_FIXING,
        CodingTaskType.FEATURE_IMPLEMENTATION,
        CodingTaskType.TEST_GENERATION,
        CodingTaskType.REFACTORING,
        CodingTaskType.REPOSITORY_ANALYSIS,
    ]
    
    assert len(task_types) == 5


def test_generate_benchmark_report(coding_benchmark):
    """Test generating a comprehensive benchmark report."""
    task = CodingTask(
        task_id="report_test",
        task_type=CodingTaskType.BUG_FIXING,
        description="Test report generation",
        difficulty="medium",
    )
    
    coding_benchmark.add_task(task)
    report = coding_benchmark.generate_report()
    
    assert report["benchmark_type"] == "coding_capability"
    assert "timestamp" in report
    assert "results" in report
    assert "metrics_summary" in report
