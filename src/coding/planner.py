"""Planner for converting coding tasks into executable steps."""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum


class TaskType(Enum):
    """Types of coding tasks."""
    BUG_FIX = "bug_fix"
    FEATURE_DEVELOPMENT = "feature_development"
    REFACTORING = "refactoring"
    TEST_GENERATION = "test_generation"
    DOCUMENTATION = "documentation"
    OPTIMIZATION = "optimization"


class StepType(Enum):
    """Types of execution steps."""
    ANALYZE = "analyze"
    LOCATE = "locate"
    READ = "read"
    GENERATE = "generate"
    APPLY = "apply"
    TEST = "test"
    VERIFY = "verify"
    ITERATE = "iterate"


@dataclass
class ExecutionStep:
    """Single step in an execution plan."""
    step_type: StepType
    description: str
    file_path: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    parameters: Dict[str, Any] = field(default_factory=dict)
    expected_output: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'step_type': self.step_type.value,
            'description': self.description,
            'file_path': self.file_path,
            'dependencies': self.dependencies,
            'parameters': self.parameters,
            'expected_output': self.expected_output
        }


@dataclass
class ExecutionPlan:
    """Complete execution plan for a coding task."""
    task_type: TaskType
    goal: str
    steps: List[ExecutionStep] = field(default_factory=list)
    context: Dict[str, Any] = field(default_factory=dict)
    estimated_steps: int = 0
    complexity: str = "medium"

    def add_step(self, step: ExecutionStep):
        """Add a step to the plan."""
        self.steps.append(step)
        self.estimated_steps = len(self.steps)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'task_type': self.task_type.value,
            'goal': self.goal,
            'steps': [step.to_dict() for step in self.steps],
            'context': self.context,
            'estimated_steps': self.estimated_steps,
            'complexity': self.complexity
        }


class Planner:
    """Converts coding tasks into structured execution plans."""

    TASK_PATTERNS = {
        'fix': TaskType.BUG_FIX,
        'bug': TaskType.BUG_FIX,
        'error': TaskType.BUG_FIX,
        'fail': TaskType.BUG_FIX,
        'add': TaskType.FEATURE_DEVELOPMENT,
        'implement': TaskType.FEATURE_DEVELOPMENT,
        'create': TaskType.FEATURE_DEVELOPMENT,
        'new': TaskType.FEATURE_DEVELOPMENT,
        'refactor': TaskType.REFACTORING,
        'clean': TaskType.REFACTORING,
        'improve': TaskType.REFACTORING,
        'test': TaskType.TEST_GENERATION,
        'coverage': TaskType.TEST_GENERATION,
        'document': TaskType.DOCUMENTATION,
        'doc': TaskType.DOCUMENTATION,
        'optimize': TaskType.OPTIMIZATION,
        'performance': TaskType.OPTIMIZATION,
    }

    def __init__(self, repository_analyzer=None):
        self.repository_analyzer = repository_analyzer

    def create_plan(self, goal: str, context: Optional[Dict] = None) -> ExecutionPlan:
        """Create an execution plan from a goal."""
        task_type = self._detect_task_type(goal)
        plan = ExecutionPlan(
            task_type=task_type,
            goal=goal,
            context=context or {}
        )

        # Generate steps based on task type
        if task_type == TaskType.BUG_FIX:
            self._plan_bug_fix(plan)
        elif task_type == TaskType.FEATURE_DEVELOPMENT:
            self._plan_feature_development(plan)
        elif task_type == TaskType.REFACTORING:
            self._plan_refactoring(plan)
        elif task_type == TaskType.TEST_GENERATION:
            self._plan_test_generation(plan)
        elif task_type == TaskType.DOCUMENTATION:
            self._plan_documentation(plan)
        elif task_type == TaskType.OPTIMIZATION:
            self._plan_optimization(plan)
        else:
            self._plan_generic(plan)

        return plan

    def _detect_task_type(self, goal: str) -> TaskType:
        """Detect task type from goal description."""
        goal_lower = goal.lower()
        
        for pattern, task_type in self.TASK_PATTERNS.items():
            if pattern in goal_lower:
                return task_type
        
        return TaskType.FEATURE_DEVELOPMENT  # Default

    def _plan_bug_fix(self, plan: ExecutionPlan):
        """Plan steps for bug fixing."""
        plan.complexity = "medium"
        
        plan.add_step(ExecutionStep(
            step_type=StepType.ANALYZE,
            description="Analyze the bug report and understand the issue",
            parameters={'focus': 'error_analysis'}
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.LOCATE,
            description="Locate the failing code and test cases",
            parameters={'search': 'test_failures'}
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.READ,
            description="Read relevant source files to understand context",
            dependencies=['locate']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.GENERATE,
            description="Generate fix for the identified bug",
            dependencies=['read']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.APPLY,
            description="Apply the fix to the codebase",
            dependencies=['generate']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.TEST,
            description="Run tests to verify the fix",
            dependencies=['apply'],
            expected_output='all_tests_pass'
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.VERIFY,
            description="Verify the fix resolves the issue without side effects",
            dependencies=['test']
        ))

    def _plan_feature_development(self, plan: ExecutionPlan):
        """Plan steps for feature development."""
        plan.complexity = "high"
        
        plan.add_step(ExecutionStep(
            step_type=StepType.ANALYZE,
            description="Analyze feature requirements and existing architecture",
            parameters={'focus': 'requirements_analysis'}
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.LOCATE,
            description="Locate appropriate location for new feature",
            parameters={'search': 'integration_points'}
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.READ,
            description="Read relevant modules to understand patterns",
            dependencies=['locate']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.GENERATE,
            description="Generate implementation for the feature",
            dependencies=['read']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.APPLY,
            description="Apply the feature implementation",
            dependencies=['generate']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.GENERATE,
            description="Generate tests for the new feature",
            dependencies=['apply'],
            parameters={'focus': 'test_generation'}
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.TEST,
            description="Run tests to verify feature works correctly",
            dependencies=['generate'],
            expected_output='all_tests_pass'
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.VERIFY,
            description="Verify feature meets requirements",
            dependencies=['test']
        ))

    def _plan_refactoring(self, plan: ExecutionPlan):
        """Plan steps for refactoring."""
        plan.complexity = "medium"
        
        plan.add_step(ExecutionStep(
            step_type=StepType.ANALYZE,
            description="Analyze code structure and identify refactoring opportunities",
            parameters={'focus': 'code_smells'}
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.LOCATE,
            description="Locate code to be refactored",
            parameters={'search': 'target_code'}
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.READ,
            description="Read and understand current implementation",
            dependencies=['locate']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.GENERATE,
            description="Generate refactored implementation",
            dependencies=['read']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.APPLY,
            description="Apply refactoring changes",
            dependencies=['generate']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.TEST,
            description="Run tests to ensure refactoring preserves behavior",
            dependencies=['apply'],
            expected_output='all_tests_pass'
        ))

    def _plan_test_generation(self, plan: ExecutionPlan):
        """Plan steps for test generation."""
        plan.complexity = "low"
        
        plan.add_step(ExecutionStep(
            step_type=StepType.ANALYZE,
            description="Analyze code to identify untested paths",
            parameters={'focus': 'coverage_analysis'}
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.LOCATE,
            description="Locate functions/modules needing tests",
            parameters={'search': 'uncovered_code'}
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.READ,
            description="Read code to understand behavior",
            dependencies=['locate']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.GENERATE,
            description="Generate test cases for uncovered code",
            dependencies=['read']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.APPLY,
            description="Apply generated tests",
            dependencies=['generate']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.TEST,
            description="Run tests to verify they pass",
            dependencies=['apply'],
            expected_output='all_tests_pass'
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.VERIFY,
            description="Verify coverage increase",
            dependencies=['test'],
            expected_output='coverage_improved'
        ))

    def _plan_documentation(self, plan: ExecutionPlan):
        """Plan steps for documentation."""
        plan.complexity = "low"
        
        plan.add_step(ExecutionStep(
            step_type=StepType.ANALYZE,
            description="Analyze code to understand what needs documentation",
            parameters={'focus': 'doc_gaps'}
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.READ,
            description="Read code to understand functionality",
            dependencies=['analyze']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.GENERATE,
            description="Generate documentation",
            dependencies=['read']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.APPLY,
            description="Apply documentation changes",
            dependencies=['generate']
        ))

    def _plan_optimization(self, plan: ExecutionPlan):
        """Plan steps for optimization."""
        plan.complexity = "high"
        
        plan.add_step(ExecutionStep(
            step_type=StepType.ANALYZE,
            description="Analyze performance bottlenecks",
            parameters={'focus': 'performance_analysis'}
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.LOCATE,
            description="Locate slow code paths",
            parameters={'search': 'bottlenecks'}
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.READ,
            description="Read and understand current implementation",
            dependencies=['locate']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.GENERATE,
            description="Generate optimized implementation",
            dependencies=['read']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.APPLY,
            description="Apply optimizations",
            dependencies=['generate']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.TEST,
            description="Run tests to ensure correctness",
            dependencies=['apply'],
            expected_output='all_tests_pass'
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.VERIFY,
            description="Verify performance improvement",
            dependencies=['test'],
            expected_output='performance_improved'
        ))

    def _plan_generic(self, plan: ExecutionPlan):
        """Plan steps for generic tasks."""
        plan.complexity = "medium"
        
        plan.add_step(ExecutionStep(
            step_type=StepType.ANALYZE,
            description="Analyze the task requirements",
            parameters={}
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.LOCATE,
            description="Locate relevant code",
            dependencies=['analyze']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.READ,
            description="Read relevant files",
            dependencies=['locate']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.GENERATE,
            description="Generate solution",
            dependencies=['read']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.APPLY,
            description="Apply solution",
            dependencies=['generate']
        ))
        
        plan.add_step(ExecutionStep(
            step_type=StepType.TEST,
            description="Test the solution",
            dependencies=['apply']
        ))
