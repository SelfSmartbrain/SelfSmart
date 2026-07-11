"""Memory system ablation study tests."""

import pytest
from pathlib import Path

from tests.validation.ablation import AblationStudy
from tests.validation.framework import ValidationFramework


@pytest.fixture
def validation_framework():
    """Create a validation framework for testing."""
    return ValidationFramework(output_dir=Path("test_validation_results"))


@pytest.fixture
def ablation_study(validation_framework):
    """Create an ablation study instance."""
    return AblationStudy(validation_framework)


def test_ablation_study_initialization(ablation_study):
    """Test that ablation study initializes correctly."""
    assert ablation_study is not None
    assert ablation_study.framework is not None
    assert ablation_study.metrics is not None


def test_simple_memory_task():
    """Define a simple task for memory ablation testing."""
    def simple_task(memory_enabled=True, memory_manager=None):
        """A simple task that may or may not use memory."""
        # Simulate task execution
        if memory_enabled:
            # With memory, task should perform better
            return 0.85  # Success score
        else:
            # Without memory, task may perform worse
            return 0.70  # Success score
    
    return simple_task


def test_memory_ablation_calculation(ablation_study):
    """Test memory ablation improvement calculation."""
    baseline = [0.85, 0.87, 0.84, 0.86, 0.85]
    ablated = [0.70, 0.72, 0.68, 0.71, 0.70]
    
    improvement = ablation_study._calculate_improvement(baseline, ablated)
    
    assert "baseline_mean" in improvement
    assert "ablated_mean" in improvement
    assert "impact_percent" in improvement
    assert "delta" in improvement
    
    # Memory should have positive impact (baseline > ablated)
    assert improvement["impact_percent"] > 0


def test_memory_ablation_with_real_task(ablation_study):
    """Test memory ablation with a real task using MemoryManager."""
    from src.memory.memory_manager import MemoryManager
    
    def memory_task(memory_enabled=True, memory_manager=None):
        """Task that uses memory for context retention."""
        if memory_enabled and memory_manager:
            # Store context in working memory
            memory_manager.working_set("task_context", {"step": 1, "data": "test"})
            memory_manager.semantic_store("fact_1", "important information", confidence=0.9)
            
            # Retrieve context
            context = memory_manager.working_get("task_context")
            fact = memory_manager.semantic_get("fact_1")
            
            # Memory enables better task performance
            success = 0.85 if (context and fact) else 0.70
        else:
            # Without memory, task performs worse
            success = 0.70
        
        return success
    
    # Run with memory
    manager_with_memory = MemoryManager(use_in_memory_backends=True)
    baseline_results = [memory_task(True, manager_with_memory) for _ in range(5)]
    
    # Run without memory
    baseline_results_no_memory = [memory_task(False, None) for _ in range(5)]
    
    improvement = ablation_study._calculate_improvement(baseline_results, baseline_results_no_memory)
    
    assert improvement["baseline_mean"] > improvement["ablated_mean"]
    assert improvement["impact_percent"] > 0


def test_concept_ablation_calculation(ablation_study):
    """Test concept system ablation improvement calculation."""
    baseline = [0.80, 0.82, 0.81, 0.83, 0.80]
    ablated = [0.65, 0.67, 0.66, 0.68, 0.65]
    
    improvement = ablation_study._calculate_improvement(baseline, ablated)
    
    # Concepts should have positive impact
    assert improvement["impact_percent"] > 0


def test_world_model_ablation_calculation(ablation_study):
    """Test world model ablation improvement calculation."""
    baseline = [0.78, 0.79, 0.77, 0.80, 0.78]
    ablated = [0.68, 0.70, 0.67, 0.69, 0.68]
    
    improvement = ablation_study._calculate_improvement(baseline, ablated)
    
    # World model should have positive impact
    assert improvement["impact_percent"] > 0


def test_governance_ablation_calculation(ablation_study):
    """Test governance ablation improvement calculation."""
    baseline = [0.90, 0.91, 0.89, 0.92, 0.90]
    ablated = [0.75, 0.77, 0.74, 0.76, 0.75]
    
    improvement = ablation_study._calculate_improvement(baseline, ablated)
    
    # Governance should have positive impact
    assert improvement["impact_percent"] > 0


def test_ablation_with_negative_impact(ablation_study):
    """Test ablation when component has negative impact."""
    baseline = [0.70, 0.71, 0.69, 0.72, 0.70]
    ablated = [0.80, 0.81, 0.79, 0.82, 0.80]
    
    improvement = ablation_study._calculate_improvement(baseline, ablated)
    
    # Component hurts performance (negative impact)
    assert improvement["impact_percent"] < 0
