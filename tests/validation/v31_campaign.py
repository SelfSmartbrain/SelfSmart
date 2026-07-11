#!/usr/bin/env python3
"""
V3.1 Benchmark Campaign - Real Capability Validation

This is the transition from architecture-driven development to evidence-driven architecture.
Instead of building more phases, we gather real performance data through benchmark campaigns.

Campaign Structure:
- Small Repository Campaign: 200 tasks (1k-5k LOC)
- Medium Repository Campaign: 200 tasks (10k-50k LOC)
- Large Repository Campaign: 100-500 tasks (100k+ LOC)

Task Types:
- Bug fixing
- Refactoring
- Test generation
- Feature implementation

Metrics Collected:
- Task Success
- Test Pass Rate
- Patch Acceptance
- Rollback Rate
- Latency
- Cost
- Memory Usage
- Planning Quality
- Decision Quality

Ablation Configurations:
- Full ModelX (all subsystems enabled)
- Memory Disabled
- Concepts Disabled
- World Model Disabled
- Governance Disabled
- Decision Intelligence Disabled
"""

import sys
import argparse
import json
import time
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import subprocess
import tempfile
import shutil
from collections import Counter, defaultdict

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from tests.validation.v31_executor import get_executor, ExecutionContext

logger = logging.getLogger(__name__)


class RepositorySize(Enum):
    """Repository size categories."""
    SMALL = "small"  # 1k-5k LOC
    MEDIUM = "medium"  # 10k-50k LOC
    LARGE = "large"  # 100k+ LOC


class TaskType(Enum):
    """Types of coding tasks."""
    BUG_FIXING = "bug_fixing"
    REFACTORING = "refactoring"
    TEST_GENERATION = "test_generation"
    FEATURE_IMPLEMENTATION = "feature_implementation"


class AblationConfig(Enum):
    """Ablation configurations for subsystem testing."""
    FULL = "full"  # All subsystems enabled
    NO_MEMORY = "no_memory"  # Memory disabled
    NO_CONCEPTS = "no_concepts"  # Concepts disabled
    NO_WORLD_MODEL = "no_world_model"  # World Model disabled
    NO_GOVERNANCE = "no_governance"  # Governance disabled
    NO_DECISION_INTELLIGENCE = "no_decision_intelligence"  # Decision Intelligence disabled


@dataclass
class BenchmarkTask:
    """A single benchmark task."""
    task_id: str
    task_type: TaskType
    description: str
    repository_path: str
    repository_size: RepositorySize
    expected_changes: List[str] = field(default_factory=list)
    difficulty: str = "medium"
    time_limit_seconds: int = 300


@dataclass
class TaskResult:
    """Result of executing a benchmark task."""
    task_id: str
    success: bool
    test_pass_rate: float
    patch_accepted: bool
    rollback_required: bool
    latency_seconds: float
    cost_usd: float
    memory_usage_mb: float
    planning_quality: float  # 0-1 score
    decision_quality: float  # 0-1 score
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CampaignConfig:
    """Configuration for a benchmark campaign."""
    name: str
    repository_size: RepositorySize
    target_task_count: int
    ablation_config: AblationConfig = AblationConfig.FULL
    repositories: List[str] = field(default_factory=list)


class V31BenchmarkCampaign:
    """V3.1 Benchmark Campaign runner."""
    
    def __init__(self, output_dir: Path = Path("benchmark_results/v3.1"), use_real_executor: bool = False):
        self.output_dir = output_dir
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.results: List[TaskResult] = []
        self.campaigns: Dict[str, CampaignConfig] = {}
        self.executor = get_executor(use_real=use_real_executor)
        
        logger.info(f"Initialized V3.1 Benchmark Campaign with output_dir={output_dir}, use_real_executor={use_real_executor}")
    
    def register_campaign(self, config: CampaignConfig) -> None:
        """Register a benchmark campaign."""
        self.campaigns[config.name] = config
        logger.info(f"Registered campaign: {config.name} ({config.repository_size.value})")
    
    async def run_campaign(self, campaign_name: str) -> Dict[str, Any]:
        """Run a registered benchmark campaign."""
        if campaign_name not in self.campaigns:
            raise ValueError(f"Campaign {campaign_name} not registered")

        config = self.campaigns[campaign_name]
        logger.info(f"Starting campaign: {campaign_name}")

        # Generate tasks for the campaign
        tasks = self._generate_tasks(config)
        logger.info(f"Generated {len(tasks)} tasks for campaign")

        # Execute tasks
        campaign_results = []
        for task in tasks:
            result = await self._execute_task(task, config.ablation_config)
            campaign_results.append(result)
            self.results.append(result)

        # Calculate campaign statistics
        stats = self._calculate_campaign_statistics(campaign_results)

        # Save campaign results
        self._save_campaign_results(campaign_name, stats, campaign_results)

        return stats
    
    def _generate_tasks(self, config: CampaignConfig) -> List[BenchmarkTask]:
        """Generate benchmark tasks for a campaign."""
        tasks = []
        
        # For now, use existing task definitions from benchmark_tasks.py
        # In production, this would dynamically generate tasks from repositories
        from src.coding.benchmark_tasks import BenchmarkTaskLibrary
        
        task_library = BenchmarkTaskLibrary()
        
        # Map task types
        type_mapping = {
            TaskType.BUG_FIXING: task_library.get_bug_fixing_tasks(),
            TaskType.FEATURE_IMPLEMENTATION: task_library.get_feature_development_tasks(),
            TaskType.REFACTORING: task_library.get_refactoring_tasks(),
            TaskType.TEST_GENERATION: task_library.get_test_generation_tasks(),
        }
        
        # Distribute tasks across types
        tasks_per_type = config.target_task_count // len(TaskType)
        
        for task_type, task_definitions in type_mapping.items():
            for i, task_def in enumerate(task_definitions[:tasks_per_type]):
                # Filter by repository size
                repo_path = task_def['repository_path']
                if self._matches_repository_size(repo_path, config.repository_size):
                    task = BenchmarkTask(
                        task_id=f"{config.name}_{task_type.value}_{i}",
                        task_type=task_type,
                        description=task_def['description'],
                        repository_path=repo_path,
                        repository_size=config.repository_size,
                        expected_changes=task_def.get('expected_changes', []),
                        difficulty=task_def.get('difficulty', 'medium'),
                    )
                    tasks.append(task)
        
        # If we don't have enough tasks, pad with generic tasks
        while len(tasks) < config.target_task_count:
            task_type = list(TaskType)[len(tasks) % len(TaskType)]
            task = BenchmarkTask(
                task_id=f"{config.name}_{task_type.value}_{len(tasks)}",
                task_type=task_type,
                description=f"Generic {task_type.value} task",
                repository_path=config.repositories[0] if config.repositories else "/Users/subh/Documents/ModelX",
                repository_size=config.repository_size,
                difficulty="medium",
            )
            tasks.append(task)
        
        return tasks[:config.target_task_count]
    
    def _matches_repository_size(self, repo_path: str, size: RepositorySize) -> bool:
        """Check if repository matches size category."""
        # For now, return True - in production, this would analyze LOC
        return True
    
    async def _execute_task(self, task: BenchmarkTask, ablation_config: AblationConfig) -> TaskResult:
        """Execute a single benchmark task with real integration."""
        logger.info(f"Executing task: {task.task_id}")

        start_time = time.time()

        try:
            # Apply ablation configuration
            env_vars = self._get_ablation_env_vars(ablation_config)

            # Execute task using the actual ModelX coding agent
            result = await self._execute_with_modelx(task, env_vars)

            latency = time.time() - start_time

            return TaskResult(
                task_id=task.task_id,
                success=result.get('success', False),
                test_pass_rate=result.get('test_pass_rate', 0.0),
                patch_accepted=result.get('patch_accepted', False),
                rollback_required=result.get('rollback_required', False),
                latency_seconds=latency,
                cost_usd=result.get('cost_usd', 0.0),
                memory_usage_mb=result.get('memory_usage_mb', 0.0),
                planning_quality=result.get('planning_quality', 0.0),
                decision_quality=result.get('decision_quality', 0.0),
                error_message=result.get('error_message'),
                metadata={
                    **result.get('metadata', {}),
                    'task_type': task.task_type.value,
                    'difficulty': task.difficulty,
                    'expected_changes': task.expected_changes,
                },
            )

        except Exception as e:
            logger.error(f"Task execution failed: {task.task_id}", exc_info=True)
            return TaskResult(
                task_id=task.task_id,
                success=False,
                test_pass_rate=0.0,
                patch_accepted=False,
                rollback_required=False,
                latency_seconds=time.time() - start_time,
                cost_usd=0.0,
                memory_usage_mb=0.0,
                planning_quality=0.0,
                decision_quality=0.0,
                error_message=str(e),
            )
    
    def _get_ablation_env_vars(self, config: AblationConfig) -> Dict[str, str]:
        """Get environment variables for ablation configuration."""
        env_vars = {}
        
        if config == AblationConfig.NO_MEMORY:
            env_vars['MODELX_DISABLE_MEMORY'] = '1'
        elif config == AblationConfig.NO_CONCEPTS:
            env_vars['MODELX_DISABLE_CONCEPTS'] = '1'
        elif config == AblationConfig.NO_WORLD_MODEL:
            env_vars['MODELX_DISABLE_WORLD_MODEL'] = '1'
        elif config == AblationConfig.NO_GOVERNANCE:
            env_vars['MODELX_DISABLE_GOVERNANCE'] = '1'
        elif config == AblationConfig.NO_DECISION_INTELLIGENCE:
            env_vars['MODELX_DISABLE_DECISION_INTELLIGENCE'] = '1'
        
        return env_vars
    
    async def _execute_with_modelx(self, task: BenchmarkTask, env_vars: Dict[str, str]) -> Dict[str, Any]:
        """Execute task using ModelX coding agent via executor."""
        # Create execution context
        context = ExecutionContext(
            repository_path=task.repository_path,
            task_description=task.description,
            task_type=task.task_type.value,
            ablation_config=env_vars,
            timeout_seconds=task.time_limit_seconds
        )

        # Execute using the executor
        result = await self.executor.execute_task(context)

        return result
    
    def _calculate_campaign_statistics(self, results: List[TaskResult]) -> Dict[str, Any]:
        """Calculate statistics for a campaign."""
        if not results:
            return {}
        
        successful = [r for r in results if r.success]
        failed = [r for r in results if not r.success]
        
        stats = {
            'total_tasks': len(results),
            'successful_tasks': len(successful),
            'failed_tasks': len(failed),
            'success_rate': len(successful) / len(results),
            'avg_test_pass_rate': sum(r.test_pass_rate for r in results) / len(results),
            'patch_acceptance_rate': sum(1 for r in results if r.patch_accepted) / len(results),
            'rollback_rate': sum(1 for r in results if r.rollback_required) / len(results),
            'avg_latency_seconds': sum(r.latency_seconds for r in results) / len(results),
            'total_cost_usd': sum(r.cost_usd for r in results),
            'avg_cost_usd': sum(r.cost_usd for r in results) / len(results),
            'avg_memory_usage_mb': sum(r.memory_usage_mb for r in results) / len(results),
            'avg_planning_quality': sum(r.planning_quality for r in results) / len(results),
            'avg_decision_quality': sum(r.decision_quality for r in results) / len(results),
            'failure_distribution': self._calculate_failure_distribution(results),
            'by_task_type': {},
            'by_difficulty': {},
        }
        
        # Statistics by task type
        for task_type in TaskType:
            type_results = [r for r in results if r.metadata.get('task_type') == task_type.value]
            if type_results:
                stats['by_task_type'][task_type.value] = {
                    'total': len(type_results),
                    'success_rate': sum(1 for r in type_results if r.success) / len(type_results),
                    'avg_latency': sum(r.latency_seconds for r in type_results) / len(type_results),
                }
        
        # Statistics by difficulty
        for difficulty in ['easy', 'medium', 'hard']:
            diff_results = [r for r in results if r.metadata.get('difficulty') == difficulty]
            if diff_results:
                stats['by_difficulty'][difficulty] = {
                    'total': len(diff_results),
                    'success_rate': sum(1 for r in diff_results if r.success) / len(diff_results),
                }
        
        return stats

    def _calculate_failure_distribution(self, results: List[TaskResult]) -> Dict[str, Any]:
        """Group failed tasks by the most likely failure cause."""
        failed = [r for r in results if not r.success]
        categories = Counter()
        examples = defaultdict(list)

        for result in failed:
            category = self._classify_failure(result)
            categories[category] += 1
            if len(examples[category]) < 5:
                examples[category].append({
                    'task_id': result.task_id,
                    'task_type': result.metadata.get('task_type'),
                    'error': result.error_message,
                })

        return {
            'total_failed': len(failed),
            'by_category': dict(categories),
            'examples': dict(examples),
        }

    def _classify_failure(self, result: TaskResult) -> str:
        """Classify the dominant failure cause for a task result."""
        if result.success:
            return 'success'

        metadata = result.metadata or {}
        execution_result = metadata.get('execution_result') or {}
        test_result = metadata.get('test_result') or {}
        execution_errors = execution_result.get('errors') or []
        test_errors = test_result.get('errors') or []
        all_errors = " ".join(
            str(error) for error in [result.error_message, *execution_errors, *test_errors]
            if error
        ).lower()

        if any(token in all_errors for token in ['api', 'llm', 'anthropic', 'openrouter', 'rate limit', 'authentication', 'error code: 402']):
            return 'provider_or_llm'

        if result.error_message:
            return 'task_execution_error'

        if result.planning_quality < 0.4:
            return 'planning'

        if not result.patch_accepted:
            if any(token in all_errors for token in ['file not found', 'failed to read', 'no such file']):
                return 'repository_understanding'
            if any(token in all_errors for token in ['old content not found', 'failed to apply']):
                return 'patch_application'
            return 'patch_generation'

        if any(token in all_errors for token in ['no module named', 'modulenotfounderror', 'importerror']):
            return 'dependency_issues'

        if any(token in all_errors for token in ['syntaxerror', 'invalid syntax', 'outside async function']):
            return 'syntax_errors'

        if result.rollback_required or not test_result.get('success', True):
            return 'test_failures'

        return 'unknown'
    
    def _save_campaign_results(self, campaign_name: str, stats: Dict[str, Any], results: List[TaskResult]) -> None:
        """Save campaign results to file."""
        campaign_dir = self.output_dir / campaign_name
        campaign_dir.mkdir(parents=True, exist_ok=True)
        
        # Save statistics
        stats_path = campaign_dir / "statistics.json"
        with open(stats_path, 'w') as f:
            json.dump(stats, f, indent=2)
        
        # Save detailed results
        results_path = campaign_dir / "results.json"
        with open(results_path, 'w') as f:
            json.dump([r.__dict__ for r in results], f, indent=2)
        
        logger.info(f"Saved campaign results to {campaign_dir}")
    
    def generate_benchmark_results_json(self) -> None:
        """Generate comprehensive benchmark_results.json aggregating all campaigns."""
        benchmark_results = {
            "campaign_version": "V3.1",
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "total_campaigns": len(self.campaigns),
            "total_tasks": len(self.results),
            "campaigns": {},
            "aggregate_statistics": self._calculate_aggregate_statistics(),
        }
        
        # Add individual campaign results
        for campaign_name, config in self.campaigns.items():
            if self.results and not self._has_results_for_campaign(campaign_name):
                continue
            campaign_dir = self.output_dir / campaign_name
            stats_path = campaign_dir / "statistics.json"
            
            if stats_path.exists():
                with open(stats_path, 'r') as f:
                    campaign_stats = json.load(f)
                
                benchmark_results["campaigns"][campaign_name] = {
                    "config": {
                        "repository_size": config.repository_size.value,
                        "target_task_count": config.target_task_count,
                        "ablation_config": config.ablation_config.value,
                        "repositories": config.repositories,
                    },
                    "statistics": campaign_stats,
                }
        
        # Save benchmark results
        results_path = self.output_dir / "benchmark_results.json"
        with open(results_path, 'w') as f:
            json.dump(benchmark_results, f, indent=2)
        
        logger.info(f"Generated benchmark_results.json at {results_path}")
    
    def _calculate_aggregate_statistics(self) -> Dict[str, Any]:
        """Calculate aggregate statistics across all campaigns."""
        if not self.results:
            return {}
        
        successful = [r for r in self.results if r.success]
        failed = [r for r in self.results if not r.success]
        
        return {
            "total_tasks": len(self.results),
            "successful_tasks": len(successful),
            "failed_tasks": len(failed),
            "overall_success_rate": len(successful) / len(self.results),
            "avg_test_pass_rate": sum(r.test_pass_rate for r in self.results) / len(self.results),
            "patch_acceptance_rate": sum(1 for r in self.results if r.patch_accepted) / len(self.results),
            "rollback_rate": sum(1 for r in self.results if r.rollback_required) / len(self.results),
            "avg_latency_seconds": sum(r.latency_seconds for r in self.results) / len(self.results),
            "total_cost_usd": sum(r.cost_usd for r in self.results),
            "avg_cost_usd": sum(r.cost_usd for r in self.results) / len(self.results),
            "avg_memory_usage_mb": sum(r.memory_usage_mb for r in self.results) / len(self.results),
            "avg_planning_quality": sum(r.planning_quality for r in self.results) / len(self.results),
            "avg_decision_quality": sum(r.decision_quality for r in self.results) / len(self.results),
            "failure_distribution": self._calculate_failure_distribution(self.results),
            "by_task_type": self._aggregate_by_task_type(),
        }
    
    def _aggregate_by_task_type(self) -> Dict[str, Any]:
        """Aggregate statistics by task type."""
        by_type = {}
        
        for task_type in TaskType:
            type_results = [r for r in self.results if r.metadata.get('task_type') == task_type.value]
            if type_results:
                by_type[task_type.value] = {
                    "total": len(type_results),
                    "successful": sum(1 for r in type_results if r.success),
                    "success_rate": sum(1 for r in type_results if r.success) / len(type_results),
                    "avg_latency": sum(r.latency_seconds for r in type_results) / len(type_results),
                    "avg_planning_quality": sum(r.planning_quality for r in type_results) / len(type_results),
                    "avg_decision_quality": sum(r.decision_quality for r in type_results) / len(type_results),
                }
        
        return by_type
    
    async def run_ablation_study(self, base_campaign: str) -> Dict[str, Any]:
        """Run ablation study comparing different subsystem configurations."""
        logger.info(f"Starting ablation study for base campaign: {base_campaign}")

        base_config = self.campaigns[base_campaign]
        ablation_results = {}

        # Run each ablation configuration
        for ablation_config in AblationConfig:
            campaign_name = f"{base_campaign}_{ablation_config.value}"

            config = CampaignConfig(
                name=campaign_name,
                repository_size=base_config.repository_size,
                target_task_count=base_config.target_task_count,
                ablation_config=ablation_config,
                repositories=base_config.repositories,
            )

            self.register_campaign(config)
            stats = await self.run_campaign(campaign_name)
            ablation_results[ablation_config.value] = stats

        # Calculate impact of each subsystem
        full_stats = ablation_results['full']
        impact_analysis = {}

        for ablation_name, stats in ablation_results.items():
            if ablation_name == 'full':
                continue

            # Calculate impact on success rate
            success_rate_delta = full_stats['success_rate'] - stats['success_rate']
            impact_percent = (success_rate_delta / stats['success_rate'] * 100) if stats['success_rate'] > 0 else 0

            impact_analysis[ablation_name] = {
                'success_rate': stats['success_rate'],
                'success_rate_delta': success_rate_delta,
                'impact_percent': impact_percent,
                'planning_quality_delta': full_stats['avg_planning_quality'] - stats['avg_planning_quality'],
                'decision_quality_delta': full_stats['avg_decision_quality'] - stats['avg_decision_quality'],
            }

        # Save ablation results
        ablation_path = self.output_dir / "ablation_results.json"
        with open(ablation_path, 'w') as f:
            json.dump({
                'base_campaign': base_campaign,
                'ablation_results': ablation_results,
                'impact_analysis': impact_analysis,
            }, f, indent=2)

        logger.info(f"Saved ablation results to {ablation_path}")

        return impact_analysis
    
    def generate_benchmark_report(self) -> None:
        """Generate comprehensive benchmark report."""
        report_path = self.output_dir / "benchmark_report.md"
        
        with open(report_path, 'w') as f:
            f.write("# V3.1 Benchmark Campaign Report\n\n")
            f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## Campaign Summary\n\n")
            f.write(f"- **Total Campaigns:** {len(self.campaigns)}\n")
            f.write(f"- **Total Tasks Executed:** {len(self.results)}\n")
            
            # Overall statistics
            if self.results:
                successful = sum(1 for r in self.results if r.success)
                f.write(f"- **Overall Success Rate:** {successful / len(self.results):.2%}\n")
                f.write(f"- **Average Test Pass Rate:** {sum(r.test_pass_rate for r in self.results) / len(self.results):.2%}\n")
                f.write(f"- **Average Planning Quality:** {sum(r.planning_quality for r in self.results) / len(self.results):.2f}\n")
                f.write(f"- **Average Decision Quality:** {sum(r.decision_quality for r in self.results) / len(self.results):.2f}\n")
            
            f.write("\n## Campaign Details\n\n")
            
            for campaign_name, config in self.campaigns.items():
                if self.results and not self._has_results_for_campaign(campaign_name):
                    continue
                campaign_dir = self.output_dir / campaign_name
                stats_path = campaign_dir / "statistics.json"
                
                if stats_path.exists():
                    with open(stats_path, 'r') as sf:
                        stats = json.load(sf)
                    
                    f.write(f"### {campaign_name}\n\n")
                    f.write(f"- **Repository Size:** {config.repository_size.value}\n")
                    f.write(f"- **Target Tasks:** {config.target_task_count}\n")
                    f.write(f"- **Ablation Config:** {config.ablation_config.value}\n")
                    f.write(f"- **Success Rate:** {stats.get('success_rate', 0):.2%}\n")
                    f.write(f"- **Average Latency:** {stats.get('avg_latency_seconds', 0):.2f}s\n")
                    f.write(f"- **Total Cost:** ${stats.get('total_cost_usd', 0):.4f}\n\n")
                    failure_distribution = stats.get('failure_distribution', {})
                    by_category = failure_distribution.get('by_category', {})
                    if by_category:
                        f.write("#### Failure Distribution\n\n")
                        for category, count in sorted(by_category.items(), key=lambda item: item[1], reverse=True):
                            f.write(f"- **{category.replace('_', ' ').title()}:** {count}\n")
                        f.write("\n")
        
        logger.info(f"Generated benchmark report at {report_path}")

    def _has_results_for_campaign(self, campaign_name: str) -> bool:
        """Return True if this process has task results for a campaign."""
        prefix = f"{campaign_name}_"
        return any(result.task_id.startswith(prefix) for result in self.results)
    
    def generate_capability_growth_report(self) -> None:
        """Generate capability growth report comparing subsystem contributions."""
        report_path = self.output_dir / "capability_growth_report.md"
        
        # Load ablation results if available
        ablation_path = self.output_dir / "ablation_results.json"
        
        with open(report_path, 'w') as f:
            f.write("# Capability Growth Report\n\n")
            f.write(f"**Generated:** {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            if ablation_path.exists():
                with open(ablation_path, 'r') as af:
                    ablation_data = json.load(af)
                
                impact_analysis = ablation_data.get('impact_analysis', {})
                
                f.write("## Subsystem Impact Analysis\n\n")
                f.write("Which subsystem contributes the most to real coding performance?\n\n")
                
                # Sort by impact
                sorted_impacts = sorted(
                    impact_analysis.items(),
                    key=lambda x: x[1]['impact_percent'],
                    reverse=True
                )
                
                for subsystem, impact in sorted_impacts:
                    f.write(f"### {subsystem.replace('_', ' ').title()}\n\n")
                    f.write(f"- **Success Rate Impact:** +{impact['impact_percent']:.2f}%\n")
                    f.write(f"- **Planning Quality Delta:** {impact['planning_quality_delta']:.3f}\n")
                    f.write(f"- **Decision Quality Delta:** {impact['decision_quality_delta']:.3f}\n\n")
                
                f.write("## Key Finding\n\n")
                if sorted_impacts:
                    top_subsystem = sorted_impacts[0]
                    f.write(f"The **{top_subsystem[0].replace('_', ' ').title()}** subsystem contributes the most to coding performance ")
                    f.write(f"with a **+{top_subsystem[1]['impact_percent']:.2f}%** impact on success rate.\n\n")
            else:
                f.write("No ablation results available. Run ablation study first.\n\n")
        
        logger.info(f"Generated capability growth report at {report_path}")


async def main():
    """Main entry point for V3.1 Benchmark Campaign."""
    parser = argparse.ArgumentParser(description="Run V3.1 Benchmark Campaign")
    parser.add_argument("--campaign", type=str, help="Specific campaign to run")
    parser.add_argument("--ablation", type=str, help="Run ablation study on base campaign")
    parser.add_argument("--output-dir", type=Path, default=Path("benchmark_results/v3.1"), help="Output directory")
    parser.add_argument("--use-real", action="store_true", help="Use real executor instead of mock")

    args = parser.parse_args()

    campaign = V31BenchmarkCampaign(output_dir=args.output_dir, use_real_executor=args.use_real)

    # Register default campaigns
    campaign.register_campaign(CampaignConfig(
        name="small_repo_campaign",
        repository_size=RepositorySize.SMALL,
        target_task_count=200,
        repositories=["/Users/subh/Documents/ModelX"],  # Will be replaced with actual small repos
    ))

    # Register small real campaign for evidence-driven iteration
    campaign.register_campaign(CampaignConfig(
        name="small_real_campaign",
        repository_size=RepositorySize.SMALL,
        target_task_count=60,  # 20 bug fixes, 20 feature, 10 refactors, 10 test generation
        repositories=["/Users/subh/Documents/ModelX"],
    ))

    # Register smoke test campaign (20 tasks: 10 feature, 10 bug fixes)
    campaign.register_campaign(CampaignConfig(
        name="smoke_test_campaign",
        repository_size=RepositorySize.SMALL,
        target_task_count=20,
        repositories=["/Users/subh/Documents/ModelX"],
    ))

    campaign.register_campaign(CampaignConfig(
        name="medium_repo_campaign",
        repository_size=RepositorySize.MEDIUM,
        target_task_count=200,
        repositories=["/Users/subh/Documents/ModelX"],
    ))

    campaign.register_campaign(CampaignConfig(
        name="large_repo_campaign",
        repository_size=RepositorySize.LARGE,
        target_task_count=100,
        repositories=["/Users/subh/Documents/ModelX"],
    ))

    if args.ablation:
        # Run ablation study
        impact = await campaign.run_ablation_study(args.ablation)
        print(f"\nAblation study complete. Top contributing subsystem identified.")
    elif args.campaign:
        # Run specific campaign
        stats = await campaign.run_campaign(args.campaign)
        campaign.generate_benchmark_results_json()
        campaign.generate_benchmark_report()
        print(f"\nCampaign {args.campaign} complete. Success rate: {stats['success_rate']:.2%}")
    else:
        # Run all campaigns
        for campaign_name in campaign.campaigns:
            stats = await campaign.run_campaign(campaign_name)
            print(f"Campaign {campaign_name}: {stats['success_rate']:.2%} success rate")

        # Run ablation study on small campaign
        impact = await campaign.run_ablation_study("small_repo_campaign")

        # Generate reports
        campaign.generate_benchmark_results_json()
        campaign.generate_benchmark_report()
        campaign.generate_capability_growth_report()

        print("\n" + "="*60)
        print("V3.1 BENCHMARK CAMPAIGN COMPLETE")
        print("="*60)
        print(f"\nResults saved to: {args.output_dir}")
        print("="*60 + "\n")


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
