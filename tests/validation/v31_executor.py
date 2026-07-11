"""
Real Task Execution Framework for V3.1 Benchmark Campaign

Integrates with actual ModelX coding components:
- Planner (src/coding/planner.py)
- CodeEditor (src/coding/code_editor.py)
- TestRunner (src/coding/test_runner.py)
- RepositoryAnalyzer (src/coding/repository_analyzer.py)

This replaces the placeholder simulation with real execution.
"""

import sys
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.coding.planner import Planner, ExecutionPlan
from src.coding.code_editor import CodeEditor, EditResult
from src.coding.test_runner import TestRunner, TestResult
from src.coding.repository_analyzer import RepositoryAnalyzer, RepositoryMetadata
from src.coding.patch_generator import PatchGenerator
from .v31_metrics import V31MetricsCollector, PlanningQualityMetrics, DecisionQualityMetrics

logger = logging.getLogger(__name__)


@dataclass
class ExecutionContext:
    """Context for task execution."""
    repository_path: str
    task_description: str
    task_type: str
    ablation_config: Optional[Dict[str, str]] = None
    timeout_seconds: int = 300


class RealTaskExecutor:
    """Executes benchmark tasks using real ModelX components."""
    
    def __init__(self):
        self.metrics_collector = V31MetricsCollector()
        self.execution_trace: List[Dict[str, Any]] = []
        self.decisions: List[Dict[str, Any]] = []
        logger.info("Initialized RealTaskExecutor")

    async def execute_task(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        Execute a task using real ModelX components.
        
        Returns:
            Dictionary with all required metrics for V3.1 campaign
        """
        logger.info(f"Executing task: {context.task_description}")
        
        start_time = time.time()
        self.execution_trace = []
        self.decisions = []
        
        try:
            # Apply ablation configuration if provided
            if context.ablation_config:
                self._apply_ablation(context.ablation_config)
            
            # Initialize components
            analyzer = RepositoryAnalyzer(context.repository_path)
            editor = CodeEditor(context.repository_path)
            planner = Planner(analyzer)
            patch_generator = PatchGenerator(context.repository_path)
            test_runner = TestRunner(context.repository_path)
            
            # Step 1: Analyze repository
            logger.info("Analyzing repository...")
            metadata = analyzer.analyze()
            self._record_trace("analyze", {"metadata": metadata.to_dict()})
            
            # Step 2: Create execution plan
            logger.info("Creating execution plan...")
            plan = planner.create_plan(context.task_description)
            self._record_trace("plan", {"plan": plan.to_dict()})
            
            # Measure planning quality
            planning_quality = self._measure_planning_quality(
                plan, context.task_description, metadata
            )
            
            # Step 3: Execute plan
            logger.info("Executing plan...")
            execution_result = await self._execute_plan(plan, editor, patch_generator, context)
            
            # Step 4: Run tests
            logger.info("Running tests...")
            test_result = test_runner.run_tests()
            test_pass_rate = test_result.pass_rate
            
            # Step 5: Measure patch acceptance
            patch_accepted = self._measure_patch_acceptance(editor, execution_result)
            
            # Step 6: Measure rollback requirement
            rollback_required = self._measure_rollback_requirement(
                context.repository_path, test_result
            )
            
            # Step 7: Measure decision quality
            decision_quality = self._measure_decision_quality(
                context.task_description, execution_result
            )
            
            # Step 8: Measure resource usage
            memory_usage = self.metrics_collector.measure_memory_usage()
            
            # Step 9: Calculate cost
            token_usage = self._estimate_token_usage(plan, execution_result)
            cost = self.metrics_collector.measure_cost(token_usage)
            
            latency = time.time() - start_time
            
            # Determine overall success
            success = (
                execution_result['success'] and
                test_pass_rate >= 0.8 and
                patch_accepted and
                not rollback_required
            )
            
            result = {
                'success': success,
                'test_pass_rate': test_pass_rate,
                'patch_accepted': patch_accepted,
                'rollback_required': rollback_required,
                'latency_seconds': latency,
                'cost_usd': cost,
                'memory_usage_mb': memory_usage,
                'planning_quality': planning_quality.overall_score(),
                'decision_quality': decision_quality.overall_score(),
                'metadata': {
                    'task_type': context.task_type,
                    'repository_metadata': metadata.to_dict(),
                    'test_result': test_result.to_dict(),
                    'execution_result': execution_result,
                    'execution_trace': self.execution_trace,
                }
            }
            
            logger.info(f"Task execution complete: success={success}")
            return result
        
        except Exception as e:
            logger.error(f"Task execution failed: {e}", exc_info=True)
            return {
                'success': False,
                'test_pass_rate': 0.0,
                'patch_accepted': False,
                'rollback_required': True,
                'latency_seconds': time.time() - start_time,
                'cost_usd': 0.0,
                'memory_usage_mb': 0.0,
                'planning_quality': 0.0,
                'decision_quality': 0.0,
                'error_message': str(e),
                'metadata': {}
            }
    
    def _apply_ablation(self, ablation_config: Dict[str, str]) -> None:
        """Apply ablation configuration by setting environment variables."""
        import os
        for key, value in ablation_config.items():
            os.environ[key] = value
        logger.info(f"Applied ablation config: {ablation_config}")
    
    def _record_trace(self, step_type: str, data: Dict[str, Any]) -> None:
        """Record a step in the execution trace."""
        self.execution_trace.append({
            'type': step_type,
            'timestamp': time.time(),
            'data': data
        })
    
    def _record_decision(self, decision_type: str, reason: str, context: Dict[str, Any]) -> None:
        """Record a decision made during execution."""
        self.decisions.append({
            'type': decision_type,
            'reason': reason,
            'timestamp': time.time(),
            'context': context,
            'id': f"decision_{len(self.decisions)}"
        })
    
    async def _execute_plan(
        self,
        plan: ExecutionPlan,
        editor: CodeEditor,
        patch_generator: PatchGenerator,
        context: ExecutionContext
    ) -> Dict[str, Any]:
        """Execute the execution plan using thecode editor and patch generator."""
        changes_made = []
        errors = []
        success = True

        for step in plan.steps:
            logger.info(f"Executing step: {step.description}")

            try:
                if step.step_type.value == 'generate':
                    # Use PatchGenerator with LLM for code generation
                    self._record_decision(
                        'code_generation',
                        f"Generate code for {step.description}",
                        {'step': step.to_dict()}
                    )

                    # Build context for patch generation
                    gen_context = {
                        'file_path': step.file_path,
                        'repository_structure': context.repository_path,
                        'related_files': []
                    }

                    # Read current code if file exists
                    if step.file_path:
                        read_result = editor.read_file(step.file_path)
                        if read_result.success:
                            gen_context['current_code'] = read_result.before

                    # Generate patch using LLM
                    patch = await patch_generator.generate_patch(plan, gen_context)

                    # Apply generated changes
                    for file_change in patch.file_changes:
                        apply_result = editor.apply_patch(file_change)
                        if apply_result.success:
                            changes_made.append(file_change.file_path)
                            logger.info(f"Applied change to {file_change.file_path}")
                        else:
                            errors.append(f"Failed to apply change to {file_change.file_path}: {apply_result.error}")
                            success = False

                elif step.step_type.value == 'apply':
                    # Apply changes
                    if step.file_path:
                        self._record_decision(
                            'apply_change',
                            f"Apply change to {step.file_path}",
                            {'step': step.to_dict()}
                        )
                        changes_made.append(step.file_path)

                elif step.step_type.value == 'read':
                    # Read file
                    if step.file_path:
                        result = editor.read_file(step.file_path)
                        if not result.success:
                            errors.append(f"Failed to read {step.file_path}: {result.error}")
                            success = False

                elif step.step_type.value == 'analyze':
                    # Analysis step, no file changes
                    self._record_decision(
                        'analysis',
                        f"Analyze: {step.description}",
                        {'step': step.to_dict()}
                    )

                elif step.step_type.value == 'locate':
                    # Locate step, no file changes
                    self._record_decision(
                        'location',
                        f"Locate: {step.description}",
                        {'step': step.to_dict()}
                    )

                elif step.step_type.value == 'test':
                    # Test step - handled by test_runner later
                    self._record_decision(
                        'test',
                        f"Test: {step.description}",
                        {'step': step.to_dict()}
                    )

                elif step.step_type.value == 'verify':
                    # Verify step - validation check
                    self._record_decision(
                        'verification',
                        f"Verify: {step.description}",
                        {'step': step.to_dict()}
                    )

                else:
                    logger.warning(f"Unknown step type: {step.step_type.value}")

            except Exception as e:
                error_msg = f"Step execution failed: {e}"
                errors.append(error_msg)
                success = False
                logger.error(error_msg)

        return {
            'success': success,
            'changes_made': changes_made,
            'errors': errors,
            'steps_executed': len(plan.steps)
        }
    
    def _measure_planning_quality(
        self,
        plan: ExecutionPlan,
        task_description: str,
        metadata: RepositoryMetadata
    ) -> PlanningQualityMetrics:
        """Measure the quality of the execution plan."""
        # Extract expected steps from task description
        expected_steps = self._extract_expected_steps(task_description)
        
        # Build repository context
        repository_context = {
            'files': set(metadata.file_structure.keys()) if hasattr(metadata, 'file_structure') else set(),
            'languages': metadata.languages if hasattr(metadata, 'languages') else [],
            'total_loc': metadata.total_loc if hasattr(metadata, 'total_loc') else 0
        }
        
        return self.metrics_collector.measure_planning_quality(
            plan.to_dict(),
            expected_steps,
            repository_context
        )
    
    def _extract_expected_steps(self, task_description: str) -> List[str]:
        """Extract expected steps from task description."""
        # This is a simplified extraction
        # In production, this would use NLP to extract steps
        steps = []
        
        desc_lower = task_description.lower()
        
        if 'fix' in desc_lower or 'bug' in desc_lower:
            steps.extend(['analyze', 'locate', 'read', 'generate', 'apply', 'test'])
        elif 'add' in desc_lower or 'implement' in desc_lower or 'feature' in desc_lower:
            steps.extend(['analyze', 'locate', 'read', 'generate', 'apply', 'test', 'verify'])
        elif 'refactor' in desc_lower:
            steps.extend(['analyze', 'locate', 'read', 'generate', 'apply', 'test'])
        elif 'test' in desc_lower:
            steps.extend(['analyze', 'locate', 'read', 'generate', 'apply', 'test', 'verify'])
        else:
            steps.extend(['analyze', 'locate', 'read', 'generate', 'apply', 'test'])
        
        return steps
    
    def _measure_decision_quality(
        self,
        task_goal: str,
        execution_result: Dict[str, Any]
    ) -> DecisionQualityMetrics:
        """Measure the quality of decisions made during execution."""
        return self.metrics_collector.measure_decision_quality(
            self.decisions,
            task_goal,
            self.execution_trace
        )
    
    def _measure_patch_acceptance(
        self,
        editor: CodeEditor,
        execution_result: Dict[str, Any]
    ) -> bool:
        """Measure if patches were accepted."""
        # Check if all changes were successfully applied
        if execution_result['success'] and len(execution_result['errors']) == 0:
            return True
        return False
    
    def _measure_rollback_requirement(
        self,
        repository_path: str,
        test_result: TestResult
    ) -> bool:
        """Measure if rollback is required based on test results."""
        # If tests failed, rollback is required
        return not test_result.success or test_result.pass_rate < 0.8
    
    def _estimate_token_usage(
        self,
        plan: ExecutionPlan,
        execution_result: Dict[str, Any]
    ) -> int:
        """Estimate token usage for the task."""
        # This is a rough estimate
        # In production, this would track actual API calls
        
        # Base tokens for planning
        planning_tokens = len(plan.steps) * 500
        
        # Tokens for execution (per step)
        execution_tokens = execution_result['steps_executed'] * 1000
        
        # Tokens for testing
        testing_tokens = 500
        
        total_tokens = planning_tokens + execution_tokens + testing_tokens
        
        return total_tokens


class MockTaskExecutor:
    """
    Mock executor for testing when infrastructure is not fully ready.
    
    This provides realistic metrics without requiring full LLM integration.
    Used for initial campaign setup and validation.
    """
    
    def __init__(self):
        self.metrics_collector = V31MetricsCollector()
        logger.info("Initialized MockTaskExecutor")
    
    def execute_task(self, context: ExecutionContext) -> Dict[str, Any]:
        """
        Execute a task with simulated but realistic metrics.
        
        This is used when the full ModelX integration is not yet available.
        """
        import random
        
        logger.info(f"Executing mock task: {context.task_description}")
        
        start_time = time.time()
        
        # Simulate realistic success rates based on task type
        task_type_success_rates = {
            'bug_fixing': 0.75,
            'refactoring': 0.85,
            'test_generation': 0.90,
            'feature_implementation': 0.65,
        }
        
        base_success = task_type_success_rates.get(context.task_type, 0.75)
        success = random.random() < base_success
        
        if success:
            return {
                'success': True,
                'test_pass_rate': random.uniform(0.85, 1.0),
                'patch_accepted': True,
                'rollback_required': False,
                'latency_seconds': random.uniform(10.0, 60.0),
                'cost_usd': random.uniform(0.05, 0.20),
                'memory_usage_mb': random.uniform(50, 200),
                'planning_quality': random.uniform(0.7, 0.95),
                'decision_quality': random.uniform(0.7, 0.95),
                'metadata': {
                    'task_type': context.task_type,
                    'executor': 'mock',
                }
            }
        else:
            return {
                'success': False,
                'test_pass_rate': random.uniform(0.0, 0.5),
                'patch_accepted': False,
                'rollback_required': True,
                'latency_seconds': random.uniform(5.0, 30.0),
                'cost_usd': random.uniform(0.01, 0.10),
                'memory_usage_mb': random.uniform(30, 100),
                'planning_quality': random.uniform(0.3, 0.6),
                'decision_quality': random.uniform(0.3, 0.6),
                'metadata': {
                    'task_type': context.task_type,
                    'executor': 'mock',
                }
            }


def get_executor(use_real: bool = False) -> Any:
    """
    Get the appropriate task executor.

    Args:
        use_real: If True, use RealTaskExecutor. If False, use MockTaskExecutor.

    Returns:
        Task executor instance
    """
    if use_real:
        return RealTaskExecutor()
    else:
        return MockTaskExecutor()
