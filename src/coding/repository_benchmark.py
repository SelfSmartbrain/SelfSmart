"""Repository benchmark suite for coding capability validation."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from .repository_analyzer import RepositoryAnalyzer, RepositoryMetadata
from .test_runner import TestRunner, TestResult
from .code_editor import CodeEditor
from .planner import Planner, ExecutionPlan
from .patch_generator import PatchGenerator


class RepositorySize(Enum):
    """Repository size categories."""
    SMALL = "small"  # 1k-5k LOC
    MEDIUM = "medium"  # 10k-50k LOC
    LARGE = "large"  # 100k+ LOC


class BenchmarkTaskType(Enum):
    """Types of benchmark tasks."""
    BUG_FIXING = "bug_fixing"
    FEATURE_DEVELOPMENT = "feature_development"
    REFACTORING = "refactoring"
    TEST_GENERATION = "test_generation"


@dataclass
class BenchmarkTask:
    """A single benchmark task."""
    task_id: str
    task_type: BenchmarkTaskType
    description: str
    repository_path: str
    expected_changes: List[str] = field(default_factory=list)
    difficulty: str = "medium"
    time_limit: int = 300  # seconds

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'task_id': self.task_id,
            'task_type': self.task_type.value,
            'description': self.description,
            'repository_path': self.repository_path,
            'expected_changes': self.expected_changes,
            'difficulty': self.difficulty,
            'time_limit': self.time_limit
        }


@dataclass
class BenchmarkResult:
    """Result of a benchmark run."""
    task_id: str
    success: bool
    execution_time: float
    test_result: Optional[TestResult] = None
    changes_made: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'task_id': self.task_id,
            'success': self.success,
            'execution_time': self.execution_time,
            'test_result': self.test_result.to_dict() if self.test_result else None,
            'changes_made': self.changes_made,
            'errors': self.errors,
            'metadata': self.metadata
        }


@dataclass
class BenchmarkSuite:
    """A collection of benchmark tasks for a repository size category."""
    size: RepositorySize
    loc_range: tuple
    tasks: List[BenchmarkTask] = field(default_factory=list)
    repositories: List[str] = field(default_factory=list)

    def add_task(self, task: BenchmarkTask):
        """Add a task to the suite."""
        self.tasks.append(task)

    def add_repository(self, repository_path: str):
        """Add a repository to the suite."""
        self.repositories.append(repository_path)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'size': self.size.value,
            'loc_range': self.loc_range,
            'tasks': [task.to_dict() for task in self.tasks],
            'repositories': self.repositories
        }


class RepositoryBenchmark:
    """Benchmark suite for coding capability validation."""

    SIZE_RANGES = {
        RepositorySize.SMALL: (1000, 5000),
        RepositorySize.MEDIUM: (10000, 50000),
        RepositorySize.LARGE: (100000, float('inf'))
    }

    def __init__(self, benchmark_root: str):
        self.benchmark_root = Path(benchmark_root)
        self.suites: Dict[RepositorySize, BenchmarkSuite] = {}
        self.results: List[BenchmarkResult] = []

        # Initialize suites
        for size in RepositorySize:
            self.suites[size] = BenchmarkSuite(
                size=size,
                loc_range=self.SIZE_RANGES[size]
            )

    def register_repository(self, repository_path: str, size: Optional[RepositorySize] = None):
        """Register a repository for benchmarking."""
        analyzer = RepositoryAnalyzer(repository_path)
        metadata = analyzer.analyze()

        if size is None:
            size = self._classify_repository(metadata)

        self.suites[size].add_repository(repository_path)
        return size

    def _classify_repository(self, metadata: RepositoryMetadata) -> RepositorySize:
        """Classify repository by size."""
        loc = metadata.total_loc

        for size, (min_loc, max_loc) in self.SIZE_RANGES.items():
            if min_loc <= loc < max_loc:
                return size

        return RepositorySize.LARGE  # Default to large

    def create_benchmark_task(
        self,
        task_id: str,
        task_type: BenchmarkTaskType,
        description: str,
        repository_path: str,
        expected_changes: Optional[List[str]] = None,
        difficulty: str = "medium"
    ) -> BenchmarkTask:
        """Create a benchmark task."""
        task = BenchmarkTask(
            task_id=task_id,
            task_type=task_type,
            description=description,
            repository_path=repository_path,
            expected_changes=expected_changes or [],
            difficulty=difficulty
        )

        # Classify repository and add to appropriate suite
        size = self._classify_repository_by_path(repository_path)
        self.suites[size].add_task(task)

        return task

    def _classify_repository_by_path(self, repository_path: str) -> RepositorySize:
        """Classify repository by path."""
        analyzer = RepositoryAnalyzer(repository_path)
        metadata = analyzer.analyze()
        return self._classify_repository(metadata)

    def run_benchmark_task(self, task: BenchmarkTask) -> BenchmarkResult:
        """Run a single benchmark task."""
        import time
        start_time = time.time()

        result = BenchmarkResult(
            task_id=task.task_id,
            success=False,
            execution_time=0.0
        )

        try:
            # Initialize components
            analyzer = RepositoryAnalyzer(task.repository_path)
            editor = CodeEditor(task.repository_path)
            planner = Planner(analyzer)
            patch_generator = PatchGenerator(task.repository_path)
            test_runner = TestRunner(task.repository_path)

            # Analyze repository
            metadata = analyzer.analyze()
            result.metadata['repository'] = metadata.to_dict()

            # Create execution plan
            plan = planner.create_plan(task.description)
            result.metadata['plan'] = plan.to_dict()

            # Generate patches
            patch = patch_generator.generate_patch(plan)
            result.metadata['patch'] = patch.to_dict()

            # Apply patches
            for file_change in patch.file_changes:
                edit_result = editor.apply_patch(file_change)
                if edit_result.success:
                    result.changes_made.append(file_change.file_path)
                else:
                    result.errors.append(f"Failed to apply patch to {file_change.file_path}: {edit_result.error}")

            # Run tests
            test_result = test_runner.run_tests()
            result.test_result = test_result

            # Determine success
            result.success = (
                len(result.errors) == 0 and
                test_result.success and
                test_result.pass_rate >= 0.8
            )

        except Exception as e:
            result.errors.append(str(e))

        finally:
            result.execution_time = time.time() - start_time
            self.results.append(result)

        return result

    def run_suite(self, size: RepositorySize) -> List[BenchmarkResult]:
        """Run all tasks in a size suite."""
        suite = self.suites[size]
        results = []

        for task in suite.tasks:
            result = self.run_benchmark_task(task)
            results.append(result)

        return results

    def run_all_benchmarks(self) -> Dict[RepositorySize, List[BenchmarkResult]]:
        """Run all benchmarks across all suites."""
        all_results = {}

        for size in RepositorySize:
            all_results[size] = self.run_suite(size)

        return all_results

    def get_statistics(self) -> Dict[str, Any]:
        """Get benchmark statistics."""
        stats = {
            'total_tasks': len(self.results),
            'successful_tasks': sum(1 for r in self.results if r.success),
            'failed_tasks': sum(1 for r in self.results if not r.success),
            'average_execution_time': sum(r.execution_time for r in self.results) / len(self.results) if self.results else 0,
            'by_size': {},
            'by_type': {}
        }

        # Statistics by size
        for size in RepositorySize:
            size_results = [r for r in self.results if self._get_task_size(r.task_id) == size]
            stats['by_size'][size.value] = {
                'total': len(size_results),
                'successful': sum(1 for r in size_results if r.success),
                'failed': sum(1 for r in size_results if not r.success)
            }

        # Statistics by task type
        for task_type in BenchmarkTaskType:
            type_results = [r for r in self.results if self._get_task_type(r.task_id) == task_type]
            stats['by_type'][task_type.value] = {
                'total': len(type_results),
                'successful': sum(1 for r in type_results if r.success),
                'failed': sum(1 for r in type_results if not r.success)
            }

        return stats

    def _get_task_size(self, task_id: str) -> Optional[RepositorySize]:
        """Get size category for a task."""
        for size, suite in self.suites.items():
            if any(task.task_id == task_id for task in suite.tasks):
                return size
        return None

    def _get_task_type(self, task_id: str) -> Optional[BenchmarkTaskType]:
        """Get task type for a task."""
        for suite in self.suites.values():
            for task in suite.tasks:
                if task.task_id == task_id:
                    return task.task_type
        return None

    def export_results(self, output_path: str):
        """Export benchmark results to JSON."""
        import json
        output_data = {
            'statistics': self.get_statistics(),
            'results': [r.to_dict() for r in self.results],
            'suites': {size.value: suite.to_dict() for size, suite in self.suites.items()}
        }

        with open(output_path, 'w') as f:
            json.dump(output_data, f, indent=2)


# Predefined benchmark configurations
SMALL_REPOSITORIES = [
    # Todo apps
    "examples/todo-app-python",
    "examples/todo-app-javascript",
    # CLI utilities
    "examples/cli-tool",
    # FastAPI starters
    "examples/fastapi-starter",
]

MEDIUM_REPOSITORIES = [
    # SaaS backends
    "examples/saas-backend",
    # Open source tools
    "examples/oss-tool",
]

LARGE_REPOSITORIES = [
    # ModelX itself
    "/Users/subh/Documents/ModelX",
    # Large OSS projects (placeholders)
    "examples/large-oss-project",
]


def create_default_benchmark_suite(benchmark_root: str) -> RepositoryBenchmark:
    """Create a default benchmark suite with example repositories."""
    benchmark = RepositoryBenchmark(benchmark_root)

    # Register repositories
    for repo in SMALL_REPOSITORIES:
        if Path(repo).exists():
            benchmark.register_repository(repo, RepositorySize.SMALL)

    for repo in MEDIUM_REPOSITORIES:
        if Path(repo).exists():
            benchmark.register_repository(repo, RepositorySize.MEDIUM)

    for repo in LARGE_REPOSITORIES:
        if Path(repo).exists():
            benchmark.register_repository(repo, RepositorySize.LARGE)

    return benchmark
