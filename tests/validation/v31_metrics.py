"""
V3.1 Metrics Collection for Real Benchmark Campaign

Implements measurement of:
- Patch Acceptance
- Rollback Rate
- Planning Quality
- Decision Quality
- Test Pass Rate
- Cost
- Memory Usage
- Latency
"""

import time
import subprocess
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
import logging
import json

logger = logging.getLogger(__name__)


@dataclass
class PlanningQualityMetrics:
    """Metrics for planning quality assessment."""
    plan_completeness: float  # 0-1: Does the plan cover all necessary steps?
    plan_correctness: float  # 0-1: Are the steps in the plan correct?
    plan_efficiency: float  # 0-1: Is the plan efficient (no unnecessary steps)?
    plan_feasibility: float  # 0-1: Is the plan actually executable?
    
    def overall_score(self) -> float:
        """Calculate overall planning quality score."""
        return (self.plan_completeness + self.plan_correctness + 
                self.plan_efficiency + self.plan_feasibility) / 4


@dataclass
class DecisionQualityMetrics:
    """Metrics for decision quality assessment."""
    decision_correctness: float  # 0-1: Were decisions correct?
    decision_consistency: float  # 0-1: Were decisions consistent with goals?
    decision_timeliness: float  # 0-1: Were decisions made in reasonable time?
    error_recovery: float  # 0-1: How well were errors recovered from?
    
    def overall_score(self) -> float:
        """Calculate overall decision quality score."""
        return (self.decision_correctness + self.decision_consistency + 
                self.decision_timeliness + self.error_recovery) / 4


class V31MetricsCollector:
    """Collects comprehensive metrics for V3.1 benchmark campaign."""
    
    def __init__(self):
        self.metrics: Dict[str, Any] = {}
        logger.info("Initialized V31MetricsCollector")
    
    def measure_patch_acceptance(
        self,
        repository_path: str,
        patch_diff: str,
        timeout_seconds: int = 60
    ) -> bool:
        """
        Measure patch acceptance by attempting to apply the patch.
        
        Returns True if patch is accepted (applies cleanly), False otherwise.
        """
        logger.info("Measuring patch acceptance")
        
        try:
            # Create a temporary copy of the repository
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_repo = Path(temp_dir) / "repo"
                shutil.copytree(repository_path, temp_repo)
                
                # Try to apply the patch
                patch_file = temp_repo / "changes.patch"
                with open(patch_file, 'w') as f:
                    f.write(patch_diff)
                
                # Try to apply with git apply
                result = subprocess.run(
                    ['git', 'apply', str(patch_file)],
                    cwd=temp_repo,
                    capture_output=True,
                    timeout=timeout_seconds
                )
                
                accepted = result.returncode == 0
                logger.info(f"Patch acceptance: {accepted}")
                return accepted
        
        except subprocess.TimeoutExpired:
            logger.warning("Patch acceptance measurement timed out")
            return False
        except Exception as e:
            logger.error(f"Patch acceptance measurement failed: {e}")
            return False
    
    def measure_rollback_rate(
        self,
        repository_path: str,
        task_changes: List[str],
        test_command: Optional[List[str]] = None
    ) -> bool:
        """
        Measure rollback rate by checking if changes need to be rolled back.
        
        Returns True if rollback is required (e.g., tests fail), False otherwise.
        """
        logger.info("Measuring rollback rate")
        
        try:
            # Run tests to check if changes are valid
            if test_command:
                result = subprocess.run(
                    test_command,
                    cwd=repository_path,
                    capture_output=True,
                    timeout=120
                )
                
                # If tests fail, rollback is required
                rollback_required = result.returncode != 0
                logger.info(f"Rollback required: {rollback_required}")
                return rollback_required
            
            # If no test command, assume no rollback needed
            return False
        
        except subprocess.TimeoutExpired:
            logger.warning("Rollback rate measurement timed out")
            return True  # Assume rollback needed on timeout
        except Exception as e:
            logger.error(f"Rollback rate measurement failed: {e}")
            return True  # Assume rollback needed on error
    
    def measure_planning_quality(
        self,
        plan: Dict[str, Any],
        expected_steps: List[str],
        repository_context: Dict[str, Any]
    ) -> PlanningQualityMetrics:
        """
        Measure planning quality by analyzing the execution plan.
        
        Args:
            plan: The execution plan generated by the system
            expected_steps: List of steps that should be in the plan
            repository_context: Context about the repository structure
        
        Returns:
            PlanningQualityMetrics with detailed assessment
        """
        logger.info("Measuring planning quality")
        
        plan_steps = plan.get('steps', [])
        
        # Completeness: Does the plan cover all expected steps?
        plan_step_descriptions = [step.get('description', '') for step in plan_steps]
        completeness = self._calculate_completeness(
            plan_step_descriptions, expected_steps
        )
        
        # Correctness: Are the steps correct for the task?
        correctness = self._assess_step_correctness(plan_steps, repository_context)
        
        # Efficiency: Are there unnecessary steps?
        efficiency = self._assess_plan_efficiency(plan_steps, expected_steps)
        
        # Feasibility: Can the plan actually be executed?
        feasibility = self._assess_plan_feasibility(plan_steps, repository_context)
        
        metrics = PlanningQualityMetrics(
            plan_completeness=completeness,
            plan_correctness=correctness,
            plan_efficiency=efficiency,
            plan_feasibility=feasibility
        )
        
        logger.info(f"Planning quality score: {metrics.overall_score():.3f}")
        return metrics
    
    def _calculate_completeness(
        self,
        plan_steps: List[str],
        expected_steps: List[str]
    ) -> float:
        """Calculate how many expected steps are covered in the plan."""
        if not expected_steps:
            return 1.0
        
        covered = 0
        for expected in expected_steps:
            for step in plan_steps:
                if expected.lower() in step.lower():
                    covered += 1
                    break
        
        return covered / len(expected_steps)
    
    def _assess_step_correctness(
        self,
        plan_steps: List[Dict[str, Any]],
        repository_context: Dict[str, Any]
    ) -> float:
        """Assess if the steps in the plan are correct."""
        # This is a simplified assessment
        # In production, this would use static analysis and repository understanding
        
        correct_count = 0
        for step in plan_steps:
            step_type = step.get('type', '')
            # Check if step type is valid
            if step_type in ['edit', 'create', 'delete', 'test', 'analyze']:
                correct_count += 1
        
        return correct_count / len(plan_steps) if plan_steps else 0.0
    
    def _assess_plan_efficiency(
        self,
        plan_steps: List[Dict[str, Any]],
        expected_steps: List[str]
    ) -> float:
        """Assess if the plan is efficient (no unnecessary steps)."""
        if not plan_steps:
            return 0.0
        
        # Efficiency is high if the number of steps is close to expected
        expected_count = len(expected_steps)
        actual_count = len(plan_steps)
        
        if expected_count == 0:
            return 1.0 if actual_count == 0 else 0.5
        
        # Allow some flexibility (±2 steps)
        if abs(actual_count - expected_count) <= 2:
            return 1.0
        elif abs(actual_count - expected_count) <= 5:
            return 0.7
        else:
            return 0.4
    
    def _assess_plan_feasibility(
        self,
        plan_steps: List[Dict[str, Any]],
        repository_context: Dict[str, Any]
    ) -> float:
        """Assess if the plan is feasible to execute."""
        # Check if file paths in the plan exist
        repo_files = repository_context.get('files', set())
        
        feasible_count = 0
        for step in plan_steps:
            file_path = step.get('file_path', '')
            if not file_path:
                # Steps without file paths (like analysis) are always feasible
                feasible_count += 1
            elif file_path in repo_files:
                feasible_count += 1
        
        return feasible_count / len(plan_steps) if plan_steps else 1.0
    
    def measure_decision_quality(
        self,
        decisions: List[Dict[str, Any]],
        task_goal: str,
        execution_trace: List[Dict[str, Any]]
    ) -> DecisionQualityMetrics:
        """
        Measure decision quality by analyzing decisions made during execution.
        
        Args:
            decisions: List of decisions made by the system
            task_goal: The original goal of the task
            execution_trace: Trace of execution with outcomes
        
        Returns:
            DecisionQualityMetrics with detailed assessment
        """
        logger.info("Measuring decision quality")
        
        # Correctness: Were decisions aligned with the goal?
        correctness = self._assess_decision_correctness(decisions, task_goal)
        
        # Consistency: Were decisions consistent with each other?
        consistency = self._assess_decision_consistency(decisions)
        
        # Timeliness: Were decisions made in reasonable time?
        timeliness = self._assess_decision_timeliness(decisions, execution_trace)
        
        # Error recovery: How well were errors handled?
        error_recovery = self._assess_error_recovery(execution_trace)
        
        metrics = DecisionQualityMetrics(
            decision_correctness=correctness,
            decision_consistency=consistency,
            decision_timeliness=timeliness,
            error_recovery=error_recovery
        )
        
        logger.info(f"Decision quality score: {metrics.overall_score():.3f}")
        return metrics
    
    def _assess_decision_correctness(
        self,
        decisions: List[Dict[str, Any]],
        task_goal: str
    ) -> float:
        """Assess if decisions were correct for the task goal."""
        if not decisions:
            return 1.0  # No decisions to assess
        
        # Check if decisions reference the task goal
        goal_keywords = task_goal.lower().split()
        correct_count = 0
        
        for decision in decisions:
            decision_reason = decision.get('reason', '').lower()
            # Check if decision reason relates to goal
            if any(keyword in decision_reason for keyword in goal_keywords):
                correct_count += 1
        
        return correct_count / len(decisions)
    
    def _assess_decision_consistency(
        self,
        decisions: List[Dict[str, Any]]
    ) -> float:
        """Assess if decisions were consistent with each other."""
        if len(decisions) <= 1:
            return 1.0
        
        # Check if decisions don't contradict each other
        # Simplified: check if decision types are consistent
        decision_types = [d.get('type', '') for d in decisions]
        
        # If all decisions are of similar types, they're likely consistent
        unique_types = set(decision_types)
        consistency = 1.0 - (len(unique_types) - 1) / len(decisions)
        
        return max(0.0, min(1.0, consistency))
    
    def _assess_decision_timeliness(
        self,
        decisions: List[Dict[str, Any]],
        execution_trace: List[Dict[str, Any]]
    ) -> float:
        """Assess if decisions were made in reasonable time."""
        if not decisions or not execution_trace:
            return 1.0
        
        # Check if decisions were made before actions
        timely_count = 0
        for decision in decisions:
            decision_time = decision.get('timestamp', 0)
            # Find corresponding action in trace
            for trace_entry in execution_trace:
                if trace_entry.get('decision_id') == decision.get('id'):
                    action_time = trace_entry.get('timestamp', 0)
                    if decision_time < action_time:
                        timely_count += 1
                    break
        
        return timely_count / len(decisions) if decisions else 1.0
    
    def _assess_error_recovery(
        self,
        execution_trace: List[Dict[str, Any]]
    ) -> float:
        """Assess how well errors were recovered from."""
        if not execution_trace:
            return 1.0
        
        # Count errors and successful recoveries
        errors = [e for e in execution_trace if e.get('type') == 'error']
        recoveries = [e for e in execution_trace if e.get('type') == 'recovery']
        
        if not errors:
            return 1.0  # No errors, perfect score
        
        # Recovery score is ratio of recoveries to errors
        return len(recoveries) / len(errors)
    
    def measure_test_pass_rate(
        self,
        repository_path: str,
        test_command: Optional[List[str]] = None,
        timeout_seconds: int = 120
    ) -> float:
        """
        Measure test pass rate by running the test suite.
        
        Returns float between 0 and 1 representing pass rate.
        """
        logger.info("Measuring test pass rate")
        
        if not test_command:
            # Default test commands based on repository type
            if (Path(repository_path) / "pytest.ini").exists() or \
               (Path(repository_path) / "pyproject.toml").exists():
                test_command = ["python", "-m", "pytest", "--tb=short", "-q"]
            elif (Path(repository_path) / "package.json").exists():
                test_command = ["npm", "test"]
            else:
                # No test suite found
                logger.warning("No test suite found, assuming 100% pass rate")
                return 1.0
        
        try:
            result = subprocess.run(
                test_command,
                cwd=repository_path,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            
            # Parse test output to get pass rate
            output = result.stdout + result.stderr
            
            # Try to extract pass rate from common test frameworks
            pass_rate = self._parse_test_output(output)
            
            logger.info(f"Test pass rate: {pass_rate:.2%}")
            return pass_rate
        
        except subprocess.TimeoutExpired:
            logger.warning("Test execution timed out")
            return 0.0
        except Exception as e:
            logger.error(f"Test pass rate measurement failed: {e}")
            return 0.0
    
    def _parse_test_output(self, output: str) -> float:
        """Parse test output to extract pass rate."""
        # Try pytest format
        if "passed" in output.lower():
            try:
                # Look for patterns like "5 passed, 2 failed"
                import re
                match = re.search(r'(\d+)\s+passed(?:,\s+(\d+)\s+failed)?', output, re.IGNORECASE)
                if match:
                    passed = int(match.group(1))
                    failed = int(match.group(2)) if match.group(2) else 0
                    total = passed + failed
                    return passed / total if total > 0 else 0.0
            except:
                pass
        
        # Try npm test format
        if "passing" in output.lower():
            try:
                import re
                match = re.search(r'(\d+)\s+passing(?:,\s+(\d+)\s+failing)?', output, re.IGNORECASE)
                if match:
                    passing = int(match.group(1))
                    failing = int(match.group(2)) if match.group(2) else 0
                    total = passing + failing
                    return passing / total if total > 0 else 0.0
            except:
                pass
        
        # Default: if no failures mentioned, assume 100%
        if "fail" not in output.lower() and "error" not in output.lower():
            return 1.0
        
        # Otherwise, assume 50% as conservative estimate
        return 0.5
    
    def measure_memory_usage(
        self,
        pid: Optional[int] = None
    ) -> float:
        """
        Measure memory usage in MB.
        
        Returns memory usage in megabytes.
        """
        logger.info("Measuring memory usage")
        
        try:
            import psutil
            
            if pid:
                process = psutil.Process(pid)
            else:
                # Measure current process
                process = psutil.Process()
            
            memory_info = process.memory_info()
            memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
            
            logger.info(f"Memory usage: {memory_mb:.2f} MB")
            return memory_mb
        
        except ImportError:
            logger.warning("psutil not available, skipping memory measurement")
            return 0.0
        except Exception as e:
            logger.error(f"Memory usage measurement failed: {e}")
            return 0.0
    
    def measure_cost(
        self,
        token_usage: int,
        model_name: str = "claude-3-opus"
    ) -> float:
        """
        Measure cost in USD based on token usage.
        
        Returns cost in USD.
        """
        logger.info("Measuring cost")
        
        # Approximate pricing (adjust based on actual model pricing)
        pricing = {
            "claude-3-opus": {"input": 0.015 / 1000, "output": 0.075 / 1000},
            "claude-3-sonnet": {"input": 0.003 / 1000, "output": 0.015 / 1000},
            "gpt-4": {"input": 0.03 / 1000, "output": 0.06 / 1000},
        }
        
        if model_name not in pricing:
            model_name = "claude-3-sonnet"  # Default
        
        # Assume 50% input, 50% output tokens
        input_tokens = token_usage * 0.5
        output_tokens = token_usage * 0.5
        
        cost = (input_tokens * pricing[model_name]["input"] + 
                output_tokens * pricing[model_name]["output"])
        
        logger.info(f"Cost: ${cost:.6f}")
        return cost
