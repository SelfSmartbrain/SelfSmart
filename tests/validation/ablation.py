"""Ablation study framework for testing component contributions."""

from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass
import logging

from .framework import ValidationFramework, ValidationResult
from .metrics import MetricsCollector, MetricType

logger = logging.getLogger(__name__)


@dataclass
class AblationConfig:
    """Configuration for an ablation study."""
    
    component_name: str
    baseline_func: Callable  # Function with component enabled
    ablated_func: Callable  # Function with component disabled
    num_trials: int = 10
    metadata: Optional[Dict[str, Any]] = None


class AblationStudy:
    """Run ablation studies to measure component contributions."""
    
    def __init__(self, framework: ValidationFramework):
        self.framework = framework
        self.metrics = MetricsCollector()
        logger.info("Initialized AblationStudy")
    
    def run_ablation(self, config: AblationConfig) -> Dict[str, ValidationResult]:
        """Run a single ablation study comparing baseline vs ablated."""
        logger.info(
            f"Running ablation study for {config.component_name} "
            f"with {config.num_trials} trials"
        )
        
        results = {}
        
        # Run baseline trials
        baseline_metrics = []
        for i in range(config.num_trials):
            with self.metrics.measure_latency(f"{config.component_name}_baseline_trial_{i}"):
                result = config.baseline_func()
                baseline_metrics.append(result)
        
        # Run ablated trials
        ablated_metrics = []
        for i in range(config.num_trials):
            with self.metrics.measure_latency(f"{config.component_name}_ablated_trial_{i}"):
                result = config.ablated_func()
                ablated_metrics.append(result)
        
        # Calculate improvement
        improvement = self._calculate_improvement(baseline_metrics, ablated_metrics)
        
        # Store results
        results["baseline"] = ValidationResult(
            experiment_id=f"{config.component_name}_baseline",
            experiment_name=f"{config.component_name}_baseline",
            status=ValidationResult.__annotations__["status"](),
            start_time=None,  # Would be set by framework
            metrics={"trials": baseline_metrics, "mean": sum(baseline_metrics) / len(baseline_metrics)},
            metadata=config.metadata,
        )
        
        results["ablated"] = ValidationResult(
            experiment_id=f"{config.component_name}_ablated",
            experiment_name=f"{config.component_name}_ablated",
            status=ValidationResult.__annotations__["status"](),
            start_time=None,
            metrics={"trials": ablated_metrics, "mean": sum(ablated_metrics) / len(ablated_metrics)},
            metadata=config.metadata,
        )
        
        results["improvement"] = improvement
        
        logger.info(
            f"Ablation study complete for {config.component_name}: "
            f"improvement={improvement.get('improvement_percent', 0):.2f}%"
        )
        
        return results
    
    def _calculate_improvement(
        self,
        baseline: List[float],
        ablated: List[float],
    ) -> Dict[str, float]:
        """Calculate the impact of removing a component."""
        baseline_mean = sum(baseline) / len(baseline)
        ablated_mean = sum(ablated) / len(ablated)
        
        # If higher is better (success rate, accuracy)
        # Improvement = (baseline - ablated) / baseline * 100
        # This shows how much performance drops when component is removed
        impact = ((baseline_mean - ablated_mean) / baseline_mean) * 100
        
        return {
            "baseline_mean": baseline_mean,
            "ablated_mean": ablated_mean,
            "impact_percent": impact,  # Positive = component helps, Negative = component hurts
            "delta": baseline_mean - ablated_mean,
        }
    
    def run_memory_ablation(
        self,
        task_func: Callable,
        num_trials: int = 10,
    ) -> Dict[str, Any]:
        """Ablation study for memory system."""
        logger.info("Running memory ablation study")
        
        # Import here to avoid circular dependencies
        from src.memory.memory_manager import MemoryManager
        
        def with_memory():
            manager = MemoryManager()
            return task_func(memory_enabled=True, memory_manager=manager)
        
        def without_memory():
            return task_func(memory_enabled=False, memory_manager=None)
        
        config = AblationConfig(
            component_name="memory",
            baseline_func=with_memory,
            ablated_func=without_memory,
            num_trials=num_trials,
            metadata={"component": "memory_system"},
        )
        
        return self.run_ablation(config)
    
    def run_concept_ablation(
        self,
        task_func: Callable,
        num_trials: int = 10,
    ) -> Dict[str, Any]:
        """Ablation study for concept/knowledge system."""
        logger.info("Running concept system ablation study")
        
        def with_concepts():
            return task_func(concepts_enabled=True)
        
        def without_concepts():
            return task_func(concepts_enabled=False)
        
        config = AblationConfig(
            component_name="concepts",
            baseline_func=with_concepts,
            ablated_func=without_concepts,
            num_trials=num_trials,
            metadata={"component": "concept_system"},
        )
        
        return self.run_ablation(config)
    
    def run_world_model_ablation(
        self,
        task_func: Callable,
        num_trials: int = 10,
    ) -> Dict[str, Any]:
        """Ablation study for world model/prediction engine."""
        logger.info("Running world model ablation study")
        
        def with_world_model():
            return task_func(world_model_enabled=True)
        
        def without_world_model():
            return task_func(world_model_enabled=False)
        
        config = AblationConfig(
            component_name="world_model",
            baseline_func=with_world_model,
            ablated_func=without_world_model,
            num_trials=num_trials,
            metadata={"component": "world_model"},
        )
        
        return self.run_ablation(config)
    
    def run_governance_ablation(
        self,
        task_func: Callable,
        num_trials: int = 10,
    ) -> Dict[str, Any]:
        """Ablation study for governance system."""
        logger.info("Running governance ablation study")
        
        def with_governance():
            return task_func(governance_enabled=True)
        
        def without_governance():
            return task_func(governance_enabled=False)
        
        config = AblationConfig(
            component_name="governance",
            baseline_func=with_governance,
            ablated_func=without_governance,
            num_trials=num_trials,
            metadata={"component": "governance_system"},
        )
        
        return self.run_ablation(config)
