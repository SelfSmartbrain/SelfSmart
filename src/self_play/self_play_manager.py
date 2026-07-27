"""
Self-Play Manager - Orchestrates the complete self-play loop.

Integrates:
- Problem generation (synthetic + real)
- Sandbox execution and testing
- Curriculum management
- Experience recording
- Learning signal extraction
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Awaitable

from src.config.logging import get_logger
from .curriculum_engine import (
    CurriculumEngine,
    DifficultyLevel,
    SkillTag,
    ProblemDomain,
    ProblemSpec,
    ProblemAttempt,
)
from .synthetic_problem_generator import SyntheticProblemGenerator, ProblemType
from .sandbox_integration import (
    SandboxTestRunner,
    SandboxConfig,
    TestCase,
    TestResult,
    SandboxExecutionResult,
)
from .experience_recorder import (
    ExperienceRecorder,
    ExperienceType,
    ExperienceRecord,
    ExecutionTrace,
    TestResult as RecorderTestResult,
    TestSuiteResult,
)

logger = get_logger(__name__)


@dataclass
class SelfPlayConfig:
    """Configuration for self-play manager."""

    # Execution
    max_iterations: int = 100
    max_concurrent: int = 3
    iteration_timeout_seconds: int = 300

    # Curriculum
    curriculum_config: Optional[Dict[str, Any]] = None

    # Sandbox
    sandbox_config: Optional[SandboxConfig] = None

    # Experience recording
    experience_storage_path: str = "./data/experiences"
    record_all_experiences: bool = True

    # Problem generation
    synthetic_problems_per_iteration: int = 1
    real_problem_probability: float = 0.3

    # Learning
    extract_learning_signals: bool = True
    update_curriculum: bool = True

    # Callbacks
    on_iteration_complete: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    on_learning_signal: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None
    on_error: Optional[Callable[[Exception], Awaitable[None]]] = None


@dataclass
class IterationResult:
    """Result of a single self-play iteration."""

    iteration: int
    timestamp: datetime
    problem: ProblemSpec
    solution_code: str
    execution_result: SandboxExecutionResult
    test_suite_result: TestSuiteResult
    experience_record: Optional[ExperienceRecord] = None
    learning_signals: Dict[str, Any] = field(default_factory=dict)
    duration_seconds: float = 0.0
    success: bool = False


class SelfPlayManager:
    """
    Manages the complete self-play loop.

    Flow:
    1. Get next problem from curriculum
    2. Generate problem (synthetic or real)
    3. Attempt solution using reasoning engine
    4. Execute and test in sandbox
    5. Record experience
    6. Extract learning signals
    7. Update curriculum
    8. Repeat
    """

    def __init__(
        self,
        reasoning_engine=None,  # Will be injected
        config: Optional[SelfPlayConfig] = None,
    ):
        self.reasoning_engine = reasoning_engine
        self.config = config or SelfPlayConfig()

        # Components
        self.curriculum = CurriculumEngine(**(self.config.curriculum_config or {}))
        self.problem_generator = SyntheticProblemGenerator()
        self.sandbox = SandboxTestRunner(self.config.sandbox_config or SandboxConfig())
        self.experience_recorder = ExperienceRecorder(
            storage_path=self.config.experience_storage_path,
        )

        # State
        self._running = False
        self._iteration = 0
        self._results: List[IterationResult] = []

        # Statistics
        self._stats = {
            "total_iterations": 0,
            "successful_iterations": 0,
            "failed_iterations": 0,
            "total_experiences_recorded": 0,
            "synthetic_problems": 0,
            "real_problems": 0,
        }

    async def initialize(self):
        """Initialize all components."""
        await self.experience_recorder.start()
        logger.info("SelfPlayManager initialized")

    async def shutdown(self):
        """Shutdown all components."""
        self._running = False
        await self.experience_recorder.stop()
        logger.info("SelfPlayManager shutdown complete")

    async def run_iteration(self) -> IterationResult:
        """
        Run a single self-play iteration.

        Returns:
            IterationResult with all details
        """
        start_time = datetime.utcnow()
        self._iteration += 1

        try:
            # Step 1: Get problem from curriculum
            problem = await self._get_next_problem()

            if not problem:
                logger.warning("No problem available from curriculum")
                return IterationResult(
                    iteration=self._iteration,
                    timestamp=start_time,
                    problem=ProblemSpec(
                        problem_id="none",
                        domain=ProblemDomain.ALGORITHMIC,
                        difficulty=1,
                        skills=[],
                        description="No problem available",
                        starter_code="",
                        test_cases=[],
                        metadata={},
                    ),
                    solution_code="",
                    execution_result=SandboxExecutionResult(
                        status=SandboxStatus.FAILED, error="No problem"
                    ),
                    test_suite_result=TestSuiteResult(suite_id="", test_results=[]),
                    success=False,
                )

            # Step 2: Generate or select problem
            if random.random() < self.config.real_problem_probability:
                problem = await self._generate_real_problem(problem)
                self._stats["real_problems"] += 1
            else:
                problem = await self._generate_synthetic_problem(problem)
                self._stats["synthetic_problems"] += 1

            # Step 3: Generate solution using reasoning engine
            solution_code = await self._generate_solution(problem)

            # Step 4: Execute in sandbox
            execution_result = await self._execute_in_sandbox(problem, solution_code)

            # Step 5: Run tests
            test_suite_result = await self._run_tests(problem, execution_result)

            # Step 6: Determine success
            success = (
                execution_result.status == SandboxStatus.COMPLETED and test_suite_result.all_passed
            )

            # Step 7: Extract learning signals
            learning_signals = await self._extract_learning_signals(
                problem, solution_code, execution_result, test_suite_result
            )

            # Step 8: Record experience
            experience_record = None
            if self.config.record_all_experiences:
                experience_record = await self._record_experience(
                    problem,
                    solution_code,
                    execution_result,
                    test_suite_result,
                    success,
                    learning_signals,
                )
                self._stats["total_experiences_recorded"] += 1

            # Step 9: Update curriculum
            if self.config.update_curriculum:
                await self._update_curriculum(problem, success, learning_signals)

            # Build result
            duration = (datetime.utcnow() - start_time).total_seconds()

            result = IterationResult(
                iteration=self._iteration,
                timestamp=start_time,
                problem=problem,
                solution_code=solution_code,
                execution_result=execution_result,
                test_suite_result=test_suite_result,
                experience_record=experience_record,
                learning_signals=learning_signals,
                duration_seconds=duration,
                success=success,
            )

            self._results.append(result)
            self._stats["total_iterations"] += 1
            if success:
                self._stats["successful_iterations"] += 1
            else:
                self._stats["failed_iterations"] += 1

            # Callback
            if self.config.on_iteration_complete:
                try:
                    await self.config.on_iteration_complete(
                        {
                            "iteration": self._iteration,
                            "problem_id": problem.problem_id,
                            "success": success,
                            "score": learning_signals.get("overall_score", 0.0),
                            "duration": duration,
                        }
                    )
                except Exception as e:
                    logger.error(f"Iteration callback failed: {e}")

            return result

        except Exception as e:
            logger.error(f"Iteration {self._iteration} failed: {e}")
            self._stats["failed_iterations"] += 1
            self._stats["total_iterations"] += 1

            if self.config.on_error:
                try:
                    await self.config.on_error(e)
                except Exception:
                    pass

            return IterationResult(
                iteration=self._iteration,
                timestamp=start_time,
                problem=ProblemSpec(
                    problem_id="error",
                    domain=ProblemDomain.ALGORITHMIC,
                    difficulty=1,
                    skills=[],
                    description="Iteration error",
                    starter_code="",
                    test_cases=[],
                    metadata={},
                ),
                solution_code="",
                execution_result=SandboxExecutionResult(status=SandboxStatus.ERROR, error=str(e)),
                test_suite_result=TestSuiteResult(suite_id="", test_results=[]),
                duration_seconds=(datetime.utcnow() - start_time).total_seconds(),
                success=False,
            )

    async def run(self, max_iterations: Optional[int] = None) -> List[IterationResult]:
        """
        Run self-play loop.

        Args:
            max_iterations: Maximum iterations (None = config default)

        Returns:
            List of iteration results
        """
        self._running = True
        max_iter = max_iterations or self.config.max_iterations

        logger.info(f"Starting self-play loop for {max_iter} iterations")

        for i in range(max_iter):
            if not self._running:
                break

            result = await self.run_iteration()

            # Small delay between iterations
            await asyncio.sleep(0.1)

        logger.info(f"Self-play loop completed: {len(self._results)} iterations")
        return self._results

    def stop(self):
        """Stop the self-play loop."""
        self._running = False

    async def _get_next_problem(self) -> Optional[ProblemSpec]:
        """Get next problem from curriculum."""
        return self.curriculum.get_next_problem()

    async def _generate_synthetic_problem(self, base_problem: ProblemSpec) -> ProblemSpec:
        """Generate a synthetic problem based on curriculum."""
        # Use the problem generator to create variations
        return self.problem_generator.generate(
            domain=base_problem.domain,
            difficulty=base_problem.difficulty,
            skills=base_problem.skills,
        )

    async def _generate_real_problem(self, base_problem: ProblemSpec) -> ProblemSpec:
        """Generate a real-world problem."""
        # This would connect to real problem sources
        # For now, return the base problem
        return base_problem

    async def _generate_solution(self, problem: ProblemSpec) -> str:
        """Generate solution code using reasoning engine."""
        if self.reasoning_engine:
            # Use reasoning engine to solve
            prompt = self._build_solution_prompt(problem)

            # This would call the actual reasoning engine
            # For now, return starter code as placeholder
            return problem.starter_code
        else:
            # Return starter code as baseline
            return problem.starter_code

    def _build_solution_prompt(self, problem: ProblemSpec) -> str:
        """Build prompt for solution generation."""
        test_desc = "\n".join(
            [
                f"- Input: {tc['input']} -> Expected: {tc['expected']} ({tc['description']})"
                for tc in problem.test_cases[:5]
            ]
        )

        return f"""Solve this problem:

Domain: {problem.domain.value}
Difficulty: {problem.difficulty}/5
Skills: {[s.value for s in problem.skills]}

Description:
{problem.description}

Test Cases:
{test_desc}

Starter Code:
```python
{problem.starter_code}
```

Write a complete Python solution that passes all test cases.
Return ONLY the solution code, no explanation."""

    async def _execute_in_sandbox(
        self,
        problem: ProblemSpec,
        solution_code: str,
    ) -> SandboxExecutionResult:
        """Execute solution in sandbox."""
        # Create test cases for sandbox
        test_cases = [
            TestCase(
                name=tc["description"].replace(" ", "_"),
                input_data=tc["input"],
                expected_output=tc["expected"],
                description=tc["description"],
            )
            for tc in problem.test_cases
        ]

        # Run in sandbox
        return await self.sandbox.run_tests(solution_code, test_cases)

    async def _run_tests(
        self,
        problem: ProblemSpec,
        execution_result: SandboxExecutionResult,
    ) -> TestSuiteResult:
        """Convert sandbox results to test suite result."""
        # Convert SandboxExecutionResult test results to TestSuiteResult
        test_results = []

        for r in execution_result.test_results:
            test_results.append(
                RecorderTestResult(
                    test_id=r.test_name,
                    name=r.test_name,
                    passed=r.passed,
                    input_data=r.actual_output,  # We don't have original input here
                    expected_output=r.expected_output,
                    actual_output=r.actual_output,
                    duration_ms=r.duration_ms,
                    error_message=r.error,
                )
            )

        return TestSuiteResult(
            suite_id=f"suite_{problem.problem_id}",
            test_results=test_results,
        )

    async def _extract_learning_signals(
        self,
        problem: ProblemSpec,
        solution_code: str,
        execution_result: SandboxExecutionResult,
        test_suite_result: TestSuiteResult,
    ) -> Dict[str, Any]:
        """Extract learning signals from iteration results."""
        signals = {
            "problem_id": problem,
            "problem_domain": problem.domain.value,
            "problem_difficulty": problem.difficulty,
            "success": execution_result.status == SandboxStatus.COMPLETED
            and test_suite_result.all_passed,
            "execution_status": execution_result.status.value,
            "test_pass_rate": test_suite_result.passed_tests
            / max(test_suite_result.total_tests, 1),
            "test_count": test_suite_result.total_tests,
            "passed_tests": test_suite_result.passed_tests,
            "execution_time_ms": execution_result.execution_time_ms,
        }

        # Error analysis
        if execution_result.status != SandboxStatus.COMPLETED:
            signals["error"] = execution_result.error
            signals["error_type"] = self._classify_error(execution_result.error or "")

        # Test failure patterns
        failed_tests = [r for r in test_suite_result.test_results if not r.passed]
        if failed_tests:
            signals["failure_patterns"] = self._analyze_failure_patterns(failed_tests)

        # Code quality signals
        signals["code_metrics"] = self._analyze_code(solution_code)

        # Skill-specific scores
        signals["skill_scores"] = self._compute_skill_scores(problem, test_suite_result)

        # Overall score
        signals["overall_score"] = self._compute_overall_score(signals)

        # Notify learning signal callback
        if self.config.on_learning_signal:
            try:
                await self.config.on_learning_signal(signals)
            except Exception as e:
                logger.error(f"Learning signal callback failed: {e}")

        return signals

    def _classify_error(self, error: str) -> str:
        """Classify error type."""
        error_lower = error.lower()

        if "timeout" in error_lower:
            return "timeout"
        elif "memory" in error_lower:
            return "memory"
        elif "syntax" in error_lower or "indentation" in error_lower:
            return "syntax"
        elif "import" in error_lower or "modulenotfound" in error_lower:
            return "import"
        elif "attribute" in error_lower:
            return "attribute"
        elif "type" in error_lower:
            return "type"
        elif "key" in error_lower:
            return "key"
        elif "index" in error_lower:
            return "index"
        elif "value" in error_lower:
            return "value"
        elif "assertion" in error_lower:
            return "assertion"
        else:
            return "runtime"

    def _analyze_failure_patterns(self, failed_tests: List[RecorderTestResult]) -> List[str]:
        """Analyze patterns in test failures."""
        patterns = []

        # Check for consistent failure types
        error_types = set()
        for test in failed_tests:
            if test.error_message:
                error_types.add(self._classify_error(test.error_message))

        if len(error_types) == 1:
            patterns.append(f"consistent_error_type: {list(error_types)[0]}")
        elif len(error_types) > 1:
            patterns.append(f"mixed_error_types: {', '.join(error_types)}")

        # Check if all failures are on similar inputs
        # (simplified)
        if len(failed_tests) == test_suite_result.total_tests:
            patterns.append("all_tests_failed")

        return patterns

    def _analyze_code(self, code: str) -> Dict[str, Any]:
        """Analyze code for quality metrics."""
        lines = code.split("\n")
        non_empty = [l for l in lines if l.strip() and not l.strip().startswith("#")]

        return {
            "total_lines": len(lines),
            "code_lines": len(non_empty),
            "has_docstring": '"""' in code or "'''" in code,
            "has_type_hints": ":" in code and "->" in code,
            "complexity_estimate": len(
                [
                    l
                    for l in non_empty
                    if any(kw in l for kw in ["if", "for", "while", "try", "except"])
                ]
            ),
        }

    def _compute_skill_scores(
        self,
        problem: ProblemSpec,
        test_suite_result: TestSuiteResult,
    ) -> Dict[str, float]:
        """Compute per-skill scores."""
        scores = {}

        if test_suite_result.total_tests == 0:
            return {s.value: 0.0 for s in problem.skills}

        base_score = test_suite_result.passed_tests / test_suite_result.total_tests

        for skill in problem.skills:
            # Adjust based on test relevance to skill
            # Simplified: just use base score
            scores[skill.value] = base_score

        return scores

    def _compute_overall_score(self, signals: Dict[str, Any]) -> float:
        """Compute overall learning score."""
        score = 0.0

        if signals.get("success"):
            score += 0.5

        score += signals.get("test_pass_rate", 0.0) * 0.3

        # Bonus for speed
        exec_time = signals.get("execution_time_ms", 10000)
        if exec_time < 100:
            score += 0.1
        elif exec_time < 500:
            score += 0.05

        # Bonus for code quality
        metrics = signals.get("code_metrics", {})
        if metrics.get("has_type_hints"):
            score += 0.05
        if metrics.get("has_docstring"):
            score += 0.05

        return min(1.0, score)

    async def _record_experience(
        self,
        problem: ProblemSpec,
        solution_code: str,
        execution_result: SandboxExecutionResult,
        test_suite_result: TestSuiteResult,
        success: bool,
        learning_signals: Dict[str, Any],
    ) -> ExperienceRecord:
        """Record experience to recorder."""

        # Build execution trace
        trace = ExecutionTrace(
            trace_id=f"trace_{problem.problem_id}_{datetime.utcnow().timestamp()}",
            started_at=datetime.utcnow(),
            code=solution_code,
            stdout=execution_result.stdout,
            stderr=execution_result.stderr,
            return_code=0 if execution_result.status == SandboxStatus.COMPLETED else 1,
            error_type=(
                self._classify_error(execution_result.error or "")
                if execution_result.error
                else None
            ),
            error_message=execution_result.error,
            duration_seconds=execution_result.execution_time_ms / 1000,
        )

        return await self.experience_recorder.record(
            experience_type=ExperienceType.SELF_PLAY,
            problem_id=problem.problem_id,
            problem_description=problem.description,
            problem_domain=problem.domain.value,
            problem_difficulty=problem.difficulty,
            problem_skills=[s.value for s in problem.skills],
            solution_code=solution_code,
            execution_trace=trace,
            test_results=test_suite_result,
            success=success,
            score=learning_signals.get("overall_score", 0.0),
            skill_scores=learning_signals.get("skill_scores", {}),
            error_patterns=learning_signals.get("failure_patterns", []),
            optimization_opportunities=learning_signals.get("optimization_opportunities", []),
        )

    async def _update_curriculum(
        self,
        problem: ProblemSpec,
        success: bool,
        learning_signals: Dict[str, Any],
    ):
        """Update curriculum based on results."""
        attempt = ProblemAttempt(
            problem_id=problem.problem_id,
            timestamp=datetime.utcnow(),
            success=success,
            duration_seconds=learning_signals.get("execution_time_ms", 0) / 1000,
            skill_scores=learning_signals.get("skill_scores", {}),
            error_type=learning_signals.get("error_type"),
        )

        self.curriculum.record_attempt(attempt)

    def get_stats(self) -> Dict[str, Any]:
        """Get manager statistics."""
        curriculum_stats = self.curriculum.get_stats()

        return {
            "iterations": self._stats,
            "curriculum": curriculum_stats,
            "experience_recorder": self.experience_recorder.get_stats(),
            "current_iteration": self._iteration,
            "running": self._running,
        }

    def get_recent_results(self, limit: int = 10) -> List[IterationResult]:
        """Get recent iteration results."""
        return self._results[-limit:]

    def get_skill_recommendations(self) -> List[Dict[str, Any]]:
        """Get recommended skills to practice."""
        return self.curriculum.get_skill_recommendations()
