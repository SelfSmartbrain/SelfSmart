"""Long-horizon validation framework for extended capability testing."""

import time
import json
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from pathlib import Path
from datetime import datetime
from .repository_benchmark import RepositoryBenchmark, BenchmarkTask, BenchmarkResult
from .benchmark_tasks import BenchmarkTaskLibrary, populate_benchmark_suite


@dataclass
class LongHorizonMetrics:
    """Metrics tracked during long-horizon validation."""
    total_tasks: int = 0
    completed_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    success_rate: float = 0.0
    recovery_rate: float = 0.0
    average_execution_time: float = 0.0
    memory_utilization: float = 0.0
    decision_quality: float = 0.0
    concept_growth: int = 0
    knowledge_growth: int = 0
    task_history: List[Dict] = field(default_factory=list)
    checkpoint_data: Dict[str, Any] = field(default_factory=dict)

    def update(self, result: BenchmarkResult):
        """Update metrics with a new result."""
        self.total_tasks += 1
        self.completed_tasks += 1
        
        if result.success:
            self.successful_tasks += 1
        else:
            self.failed_tasks += 1
        
        self.success_rate = self.successful_tasks / self.completed_tasks if self.completed_tasks > 0 else 0
        self.average_execution_time = (
            sum(h['execution_time'] for h in self.task_history) + result.execution_time
        ) / self.completed_tasks if self.completed_tasks > 0 else result.execution_time
        
        self.task_history.append({
            'task_id': result.task_id,
            'success': result.success,
            'execution_time': result.execution_time,
            'timestamp': datetime.now().isoformat()
        })

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'successful_tasks': self.successful_tasks,
            'failed_tasks': self.failed_tasks,
            'success_rate': self.success_rate,
            'recovery_rate': self.recovery_rate,
            'average_execution_time': self.average_execution_time,
            'memory_utilization': self.memory_utilization,
            'decision_quality': self.decision_quality,
            'concept_growth': self.concept_growth,
            'knowledge_growth': self.knowledge_growth,
            'task_history': self.task_history,
            'checkpoint_data': self.checkpoint_data
        }


@dataclass
class ValidationCheckpoint:
    """Checkpoint data for resuming validation runs."""
    task_index: int
    metrics: LongHorizonMetrics
    timestamp: str
    state: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'task_index': self.task_index,
            'metrics': self.metrics.to_dict(),
            'timestamp': self.timestamp,
            'state': self.state
        }


class LongHorizonValidator:
    """Framework for running long-horizon validation (100-1000 tasks)."""

    def __init__(
        self,
        benchmark_root: str,
        target_tasks: int = 100,
        checkpoint_interval: int = 10,
        output_dir: str = "validation_results"
    ):
        self.benchmark_root = Path(benchmark_root)
        self.target_tasks = target_tasks
        self.checkpoint_interval = checkpoint_interval
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.benchmark = RepositoryBenchmark(str(benchmark_root))
        self.metrics = LongHorizonMetrics()
        self.current_task_index = 0
        self.checkpoints: List[ValidationCheckpoint] = []
        
        # Cognitive system integration points
        self.memory_tracker: Optional[Callable] = None
        self.concept_tracker: Optional[Callable] = None
        self.decision_tracker: Optional[Callable] = None

    def setup_benchmark(self):
        """Setup benchmark with tasks."""
        populate_benchmark_suite(self.benchmark)
        
        # Ensure we have enough tasks
        total_available = sum(len(suite.tasks) for suite in self.benchmark.suites.values())
        if total_available < self.target_tasks:
            print(f"Warning: Only {total_available} tasks available, but target is {self.target_tasks}")
            self.target_tasks = total_available

    def set_memory_tracker(self, tracker: Callable):
        """Set callback for tracking memory utilization."""
        self.memory_tracker = tracker

    def set_concept_tracker(self, tracker: Callable):
        """Set callback for tracking concept growth."""
        self.concept_tracker = tracker

    def set_decision_tracker(self, tracker: Callable):
        """Set callback for tracking decision quality."""
        self.decision_tracker = tracker

    def run_validation(
        self,
        resume_from_checkpoint: Optional[str] = None,
        progress_callback: Optional[Callable] = None
    ) -> LongHorizonMetrics:
        """Run long-horizon validation."""
        if resume_from_checkpoint:
            self._load_checkpoint(resume_from_checkpoint)
        
        self.setup_benchmark()
        
        # Flatten all tasks
        all_tasks = []
        for suite in self.benchmark.suites.values():
            all_tasks.extend(suite.tasks)
        
        # Start from current index
        tasks_to_run = all_tasks[self.current_task_index:self.current_task_index + self.target_tasks]
        
        for i, task in enumerate(tasks_to_run):
            self.current_task_index = self.current_task_index + i
            
            print(f"Running task {self.current_task_index + 1}/{self.target_tasks}: {task.task_id}")
            
            # Run task
            result = self.benchmark.run_benchmark_task(task)
            self.metrics.update(result)
            
            # Track cognitive metrics
            self._track_cognitive_metrics()
            
            # Progress callback
            if progress_callback:
                progress_callback(self.current_task_index + 1, self.target_tasks, self.metrics)
            
            # Checkpoint
            if (self.current_task_index + 1) % self.checkpoint_interval == 0:
                self._save_checkpoint()
            
            # Early stop if target reached
            if self.current_task_index + 1 >= self.target_tasks:
                break
        
        # Final checkpoint
        self._save_checkpoint()
        
        # Generate report
        self._generate_report()
        
        return self.metrics

    def _track_cognitive_metrics(self):
        """Track cognitive system metrics."""
        # Memory utilization
        if self.memory_tracker:
            self.metrics.memory_utilization = self.memory_tracker()
        
        # Concept growth
        if self.concept_tracker:
            self.metrics.concept_growth = self.concept_tracker()
        
        # Decision quality
        if self.decision_tracker:
            self.metrics.decision_quality = self.decision_tracker()
        
        # Knowledge growth (simplified - would integrate with actual knowledge system)
        self.metrics.knowledge_growth = self.metrics.successful_tasks

    def _save_checkpoint(self):
        """Save current state as checkpoint."""
        checkpoint = ValidationCheckpoint(
            task_index=self.current_task_index,
            metrics=self.metrics,
            timestamp=datetime.now().isoformat()
        )
        
        checkpoint_file = self.output_dir / f"checkpoint_{self.current_task_index}.json"
        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint.to_dict(), f, indent=2)
        
        self.checkpoints.append(checkpoint)
        print(f"Checkpoint saved at task {self.current_task_index + 1}")

    def _load_checkpoint(self, checkpoint_path: str):
        """Load state from checkpoint."""
        with open(checkpoint_path, 'r') as f:
            data = json.load(f)
        
        self.current_task_index = data['task_index']
        self.metrics = LongHorizonMetrics(**data['metrics'])
        print(f"Resumed from checkpoint at task {self.current_task_index + 1}")

    def _generate_report(self):
        """Generate validation report."""
        report = {
            'validation_summary': {
                'target_tasks': self.target_tasks,
                'completed_tasks': self.metrics.completed_tasks,
                'success_rate': self.metrics.success_rate,
                'average_execution_time': self.metrics.average_execution_time
            },
            'cognitive_metrics': {
                'memory_utilization': self.metrics.memory_utilization,
                'decision_quality': self.metrics.decision_quality,
                'concept_growth': self.metrics.concept_growth,
                'knowledge_growth': self.metrics.knowledge_growth
            },
            'task_breakdown': {
                'successful': self.metrics.successful_tasks,
                'failed': self.metrics.failed_tasks
            },
            'detailed_metrics': self.metrics.to_dict()
        }
        
        report_file = self.output_dir / "validation_report.json"
        with open(report_file, 'w') as f:
            json.dump(report, f, indent=2)
        
        print(f"Validation report saved to {report_file}")

    def get_progress_summary(self) -> Dict[str, Any]:
        """Get current progress summary."""
        return {
            'progress': (self.metrics.completed_tasks / self.target_tasks * 100) if self.target_tasks > 0 else 0,
            'completed': self.metrics.completed_tasks,
            'target': self.target_tasks,
            'success_rate': self.metrics.success_rate,
            'current_task_index': self.current_task_index
        }


class ValidationOrchestrator:
    """Orchestrates multiple validation runs with different configurations."""

    def __init__(self, benchmark_root: str):
        self.benchmark_root = benchmark_root
        self.runs: Dict[str, LongHorizonValidator] = {}

    def create_validation_run(
        self,
        run_id: str,
        target_tasks: int = 100,
        checkpoint_interval: int = 10
    ) -> LongHorizonValidator:
        """Create a new validation run."""
        output_dir = f"validation_results/{run_id}"
        validator = LongHorizonValidator(
            benchmark_root=self.benchmark_root,
            target_tasks=target_tasks,
            checkpoint_interval=checkpoint_interval,
            output_dir=output_dir
        )
        self.runs[run_id] = validator
        return validator

    def run_comparison(
        self,
        configurations: List[Dict[str, Any]]
    ) -> Dict[str, LongHorizonMetrics]:
        """Run multiple validation configurations for comparison."""
        results = {}
        
        for i, config in enumerate(configurations):
            run_id = f"comparison_run_{i}"
            validator = self.create_validation_run(
                run_id=run_id,
                target_tasks=config.get('target_tasks', 100),
                checkpoint_interval=config.get('checkpoint_interval', 10)
            )
            
            # Set cognitive trackers if provided
            if 'memory_tracker' in config:
                validator.set_memory_tracker(config['memory_tracker'])
            if 'concept_tracker' in config:
                validator.set_concept_tracker(config['concept_tracker'])
            if 'decision_tracker' in config:
                validator.set_decision_tracker(config['decision_tracker'])
            
            # Run validation
            metrics = validator.run_validation()
            results[run_id] = metrics
        
        # Generate comparison report
        self._generate_comparison_report(results)
        
        return results

    def _generate_comparison_report(self, results: Dict[str, LongHorizonMetrics]):
        """Generate comparison report across runs."""
        comparison = {
            'runs': {},
            'summary': {
                'best_success_rate': 0,
                'best_run': None,
                'average_success_rate': 0,
                'average_execution_time': 0
            }
        }
        
        total_success_rate = 0
        total_execution_time = 0
        
        for run_id, metrics in results.items():
            comparison['runs'][run_id] = metrics.to_dict()
            
            total_success_rate += metrics.success_rate
            total_execution_time += metrics.average_execution_time
            
            if metrics.success_rate > comparison['summary']['best_success_rate']:
                comparison['summary']['best_success_rate'] = metrics.success_rate
                comparison['summary']['best_run'] = run_id
        
        if results:
            comparison['summary']['average_success_rate'] = total_success_rate / len(results)
            comparison['summary']['average_execution_time'] = total_execution_time / len(results)
        
        report_file = Path("validation_results/comparison_report.json")
        with open(report_file, 'w') as f:
            json.dump(comparison, f, indent=2)


# Example cognitive system trackers (placeholders for actual integration)
def example_memory_tracker() -> float:
    """Example memory utilization tracker."""
    # In production, this would query the actual memory system
    import psutil
    process = psutil.Process()
    return process.memory_info().rss / (1024 * 1024)  # MB


def example_concept_tracker() -> int:
    """Example concept growth tracker."""
    # In production, this would query the concept registry
    return 0  # Placeholder


def example_decision_tracker() -> float:
    """Example decision quality tracker."""
    # In production, this would analyze decision history
    return 0.8  # Placeholder


def run_standard_validation(benchmark_root: str, target_tasks: int = 100):
    """Run a standard long-horizon validation."""
    validator = LongHorizonValidator(
        benchmark_root=benchmark_root,
        target_tasks=target_tasks,
        checkpoint_interval=10
    )
    
    # Set up cognitive trackers
    validator.set_memory_tracker(example_memory_tracker)
    validator.set_concept_tracker(example_concept_tracker)
    validator.set_decision_tracker(example_decision_tracker)
    
    # Progress callback
    def progress_callback(current, total, metrics):
        print(f"Progress: {current}/{total} ({current/total*100:.1f}%)")
        print(f"Success Rate: {metrics.success_rate:.}")
    
    # Run validation
    metrics = validator.run_validation(progress_callback=progress_callback)
    
    return metrics
