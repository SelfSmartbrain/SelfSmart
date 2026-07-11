"""Benchmark task definitions for coding capability validation."""

from typing import List, Dict, Any
from .repository_benchmark import BenchmarkTask, BenchmarkTaskType, RepositoryBenchmark


class BenchmarkTaskLibrary:
    """Library of predefined benchmark tasks."""

    @staticmethod
    def get_bug_fixing_tasks() -> List[Dict[str, Any]]:
        """Get bug fixing benchmark tasks."""
        return [
            {
                'task_id': 'bug_fix_001',
                'description': 'Fix failing test in user authentication module',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/api/auth.py'],
                'difficulty': 'easy'
            },
            {
                'task_id': 'bug_fix_002',
                'description': 'Fix memory leak in data processing pipeline',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/agents/memory_agent.py'],
                'difficulty': 'hard'
            },
            {
                'task_id': 'bug_fix_003',
                'description': 'Fix race condition in concurrent task scheduler',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/agents/orchestrator.py'],
                'difficulty': 'hard'
            },
            {
                'task_id': 'bug_fix_004',
                'description': 'Fix incorrect API response format',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/api/routes.py'],
                'difficulty': 'easy'
            },
            {
                'task_id': 'bug_fix_005',
                'description': 'Fix database connection timeout issue',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/db/models.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'bug_fix_006',
                'description': 'Fix off-by-one error in array indexing',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/coding/code_editor.py'],
                'difficulty': 'easy'
            },
            {
                'task_id': 'bug_fix_007',
                'description': 'Fix JSON parsing error in configuration loader',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/config/settings.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'bug_fix_008',
                'description': 'Fix null pointer exception in user profile service',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/api/dependencies.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'bug_fix_009',
                'description': 'Fix infinite loop in recursive tree traversal',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/mental_models/mental_models.py'],
                'difficulty': 'hard'
            },
            {
                'task_id': 'bug_fix_010',
                'description': 'Fix encoding issue in file reader',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/coding/repository_analyzer.py'],
                'difficulty': 'easy'
            },
        ]

    @staticmethod
    def get_feature_development_tasks() -> List[Dict[str, Any]]:
        """Get feature development benchmark tasks."""
        return [
            {
                'task_id': 'feature_001',
                'description': 'Add user password reset functionality',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/api/auth.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'feature_002',
                'description': 'Add file upload endpoint to API',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/api/routes.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'feature_003',
                'description': 'Add command-line argument for verbose mode',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/cli/main.py'],
                'difficulty': 'easy'
            },
            {
                'task_id': 'feature_004',
                'description': 'Add real-time notifications using WebSocket',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/api/routes.py'],
                'difficulty': 'hard'
            },
            {
                'task_id': 'feature_005',
                'description': 'Add data export to CSV functionality',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/coding/code_editor.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'feature_006',
                'description': 'Add caching layer for database queries',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/db/models.py'],
                'difficulty': 'hard'
            },
            {
                'task_id': 'feature_007',
                'description': 'Add search functionality with filters',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/rag/vector_store.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'feature_008',
                'description': 'Add API rate limiting middleware',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/api/dependencies.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'feature_009',
                'description': 'Add batch processing for large datasets',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/agents/execution_agent.py'],
                'difficulty': 'hard'
            },
            {
                'task_id': 'feature_010',
                'description': 'Add user activity logging and analytics',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/cognition/intelligence_reporter.py'],
                'difficulty': 'hard'
            },
        ]

    @staticmethod
    def get_refactoring_tasks() -> List[Dict[str, Any]]:
        """Get refactoring benchmark tasks."""
        return [
            {
                'task_id': 'refactor_001',
                'description': 'Extract duplicate code into reusable function',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/agents/orchestrator.py'],
                'difficulty': 'easy'
            },
            {
                'task_id': 'refactor_002',
                'description': 'Replace magic numbers with named constants',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/config/settings.py'],
                'difficulty': 'easy'
            },
            {
                'task_id': 'refactor_003',
                'description': 'Simplify complex conditional logic',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/agents/execution_agent.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'refactor_004',
                'description': 'Extract large class into smaller modules',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/agents/orchestrator.py'],
                'difficulty': 'hard'
            },
            {
                'task_id': 'refactor_005',
                'description': 'Replace nested callbacks with async/await',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/agents/memory_agent.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'refactor_006',
                'description': 'Improve function naming and documentation',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/coding/planner.py'],
                'difficulty': 'easy'
            },
            {
                'task_id': 'refactor_007',
                'description': 'Remove dead code and unused imports',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/api/routes.py'],
                'difficulty': 'easy'
            },
            {
                'task_id': 'refactor_008',
                'description': 'Implement dependency injection pattern',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/api/dependencies.py'],
                'difficulty': 'hard'
            },
            {
                'task_id': 'refactor_009',
                'description': 'Consolidate similar database queries',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/db/models.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'refactor_010',
                'description': 'Replace string concatenation with f-strings',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['src/coding/patch_generator.py'],
                'difficulty': 'easy'
            },
        ]

    @staticmethod
    def get_test_generation_tasks() -> List[Dict[str, Any]]:
        """Get test generation benchmark tasks."""
        return [
            {
                'task_id': 'test_001',
                'description': 'Generate unit tests for user authentication',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['tests/test_api_auth.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'test_002',
                'description': 'Generate integration tests for API endpoints',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['tests/test_api_routes.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'test_003',
                'description': 'Generate edge case tests for data validation',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['tests/test_coding.py'],
                'difficulty': 'easy'
            },
            {
                'task_id': 'test_004',
                'description': 'Generate performance tests for data pipeline',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['tests/test_agents.py'],
                'difficulty': 'hard'
            },
            {
                'task_id': 'test_005',
                'description': 'Generate tests for error handling paths',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['tests/test_db.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'test_006',
                'description': 'Generate tests for concurrent operations',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['tests/test_concurrency.py'],
                'difficulty': 'hard'
            },
            {
                'task_id': 'test_007',
                'description': 'Generate tests for file I/O operations',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['tests/test_io.py'],
                'difficulty': 'easy'
            },
            {
                'task_id': 'test_008',
                'description': 'Generate tests for database transactions',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['tests/test_db_models.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'test_009',
                'description': 'Generate tests for API authentication middleware',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['tests/test_middleware.py'],
                'difficulty': 'medium'
            },
            {
                'task_id': 'test_010',
                'description': 'Generate tests for configuration loading',
                'repository_path': '/Users/subh/Documents/ModelX',
                'expected_changes': ['tests/test_config.py'],
                'difficulty': 'easy'
            },
        ]

    @staticmethod
    def get_all_tasks() -> Dict[BenchmarkTaskType, List[Dict[str, Any]]]:
        """Get all benchmark tasks by type."""
        return {
            BenchmarkTaskType.BUG_FIXING: BenchmarkTaskLibrary.get_bug_fixing_tasks(),
            BenchmarkTaskType.FEATURE_DEVELOPMENT: BenchmarkTaskLibrary.get_feature_development_tasks(),
            BenchmarkTaskType.REFACTORING: BenchmarkTaskLibrary.get_refactoring_tasks(),
            BenchmarkTaskType.TEST_GENERATION: BenchmarkTaskLibrary.get_test_generation_tasks(),
        }


def populate_benchmark_suite(benchmark: RepositoryBenchmark):
    """Populate a benchmark suite with predefined tasks."""
    all_tasks = BenchmarkTaskLibrary.get_all_tasks()

    for task_type, tasks in all_tasks.items():
        for task_data in tasks:
            benchmark.create_benchmark_task(
                task_id=task_data['task_id'],
                task_type=task_type,
                description=task_data['description'],
                repository_path=task_data['repository_path'],
                expected_changes=task_data.get('expected_changes', []),
                difficulty=task_data.get('difficulty', 'medium')
            )


def get_task_statistics() -> Dict[str, Any]:
    """Get statistics about available benchmark tasks."""
    all_tasks = BenchmarkTaskLibrary.get_all_tasks()

    stats = {
        'total_tasks': sum(len(tasks) for tasks in all_tasks.values()),
        'by_type': {},
        'by_difficulty': {'easy': 0, 'medium': 0, 'hard': 0}
    }

    for task_type, tasks in all_tasks.items():
        stats['by_type'][task_type.value] = len(tasks)
        
        for task in tasks:
            difficulty = task.get('difficulty', 'medium')
            stats['by_difficulty'][difficulty] += 1

    return stats
