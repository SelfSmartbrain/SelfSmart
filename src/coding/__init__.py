"""Coding capability verification stack for ModelX."""

from .repository_analyzer import RepositoryAnalyzer, RepositoryMetadata
from .code_editor import CodeEditor, EditResult, FileChange
from .planner import Planner, ExecutionPlan, ExecutionStep, TaskType, StepType
from .patch_generator import PatchGenerator, GeneratedPatch
from .test_runner import TestRunner, TestResult, TestFramework
from .repository_benchmark import (
    RepositoryBenchmark,
    BenchmarkTask,
    BenchmarkResult,
    BenchmarkSuite,
    RepositorySize,
    BenchmarkTaskType
)
from .benchmark_tasks import BenchmarkTaskLibrary, populate_benchmark_suite
from .long_horizon_validation import (
    LongHorizonValidator,
    LongHorizonMetrics,
    ValidationOrchestrator,
    run_standard_validation
)

__all__ = [
    # Repository Analysis
    'RepositoryAnalyzer',
    'RepositoryMetadata',
    
    # Code Editing
    'CodeEditor',
    'EditResult',
    'FileChange',
    
    # Planning
    'Planner',
    'ExecutionPlan',
    'ExecutionStep',
    'TaskType',
    'StepType',
    
    # Patch Generation
    'PatchGenerator',
    'GeneratedPatch',
    
    # Test Running
    'TestRunner',
    'TestResult',
    'TestFramework',
    
    # Benchmarking
    'RepositoryBenchmark',
    'BenchmarkTask',
    'BenchmarkResult',
    'BenchmarkSuite',
    'RepositorySize',
    'BenchmarkTaskType',
    
    # Benchmark Tasks
    'BenchmarkTaskLibrary',
    'populate_benchmark_suite',
    
    # Long-Horizon Validation
    'LongHorizonValidator',
    'LongHorizonMetrics',
    'ValidationOrchestrator',
    'run_standard_validation',
]
