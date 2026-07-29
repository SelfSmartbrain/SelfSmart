"""
Enhanced Curriculum Engine - Adaptive problem progression with real problem generation.

Features:
- Dynamic problem generation from multiple sources
- Performance-based difficulty adjustment
- Skill tracking across multiple dimensions
- Spaced repetition for retention
- Transfer learning detection
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Set, Callable, Awaitable
from collections import defaultdict

from src.config.logging import get_logger

logger = get_logger(__name__)


class ProblemDomain(Enum):
    """Domains of problems for curriculum."""

    ALGORITHMIC = "algorithmic"
    DEBUGGING = "debugging"
    OPTIMIZATION = "optimization"
    ARCHITECTURE = "architecture"
    REFACTORING = "refactoring"
    TESTING = "testing"
    SECURITY = "security"
    CONCURRENCY = "concurrency"
    DATA_STRUCTURES = "data_structures"
    SYSTEM_DESIGN = "system_design"


class SkillTag(Enum):
    """Specific skills that problems can test."""

    RECURSION = "recursion"
    DYNAMIC_PROGRAMMING = "dynamic_programming"
    GRAPH_ALGORITHMS = "graph_algorithms"
    STRING_MANIPULATION = "string_manipulation"
    TREE_TRAVERSAL = "tree_traversal"
    SORTING_SEARCHING = "sorting_searching"
    MEMORY_MANAGEMENT = "memory_management"
    ERROR_HANDLING = "error_handling"
    PERFORMANCE_PROFILING = "performance_profiling"
    DESIGN_PATTERNS = "design_patterns"
    API_DESIGN = "api_design"
    DATABASE_DESIGN = "database_design"
    DISTRIBUTED_SYSTEMS = "distributed_systems"
    SECURITY_AUDITING = "security_auditing"
    TEST_DESIGN = "test_design"


@dataclass
class ProblemSpec:
    """Specification for a generated problem."""

    problem_id: str
    domain: ProblemDomain
    skills: List[SkillTag]
    difficulty: int  # 1-10
    description: str
    starter_code: str
    test_cases: List[Dict[str, Any]]
    expected_solution: Optional[str] = None
    hints: List[str] = field(default_factory=list)
    time_limit_seconds: int = 30
    memory_limit_mb: int = 256
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ProblemAttempt:
    """Record of a problem attempt."""

    problem_id: str
    timestamp: datetime
    success: bool
    execution_time: float
    memory_used: int
    test_results: List[Dict[str, Any]]
    solution_code: str
    error_message: Optional[str] = None
    skill_scores: Dict[SkillTag, float] = field(default_factory=dict)


@dataclass
class SkillProfile:
    """Tracks proficiency in each skill."""

    skill: SkillTag
    proficiency: float = 0.5  # 0.0 to 1.0
    attempts: int = 0
    successes: int = 0
    last_practiced: Optional[datetime] = None
    decay_rate: float = 0.01  # Per day

    def update(self, success: bool, score: float = 1.0):
        """Update proficiency based on attempt."""
        self.attempts += 1
        if success:
            self.successes += 1

        # Update proficiency with exponential moving average
        alpha = 0.3
        self.proficiency = (1 - alpha) * self.proficiency + alpha * (score if success else 0)
        self.last_practiced = datetime.utcnow()

    def apply_decay(self, days: float):
        """Apply time-based decay."""
        self.proficiency = max(0.0, self.proficiency - self.decay_rate * days)

    @property
    def success_rate(self) -> float:
        if self.attempts == 0:
            return 0.0
        return self.successes / self.attempts


class CurriculumEngine:
    """
    Advanced curriculum engine with adaptive difficulty and skill tracking.

    Features:
    - Multi-dimensional skill tracking
    - Adaptive difficulty based on performance
    - Spaced repetition for retention
    - Problem generation from templates
    - Transfer learning detection
    """

    def __init__(
        self,
        problem_generator: Optional[Callable[[], Awaitable[List[ProblemSpec]]]] = None,
        initial_difficulty: int = 3,
        max_difficulty: int = 10,
        advancement_threshold: float = 0.75,  # Success rate to advance
        regression_threshold: float = 0.4,  # Success rate to regress
        min_problems_per_level: int = 5,
        spaced_repetition_interval_hours: float = 24,
    ):
        self.problem_generator = problem_generator
        self.max_difficulty = max_difficulty
        self.advancement_threshold = advancement_threshold
        self.regression_threshold = regression_threshold
        self.min_problems_per_level = min_problems_per_level
        self.spaced_repetition_interval = spaced_repetition_interval_hours

        # State
        self.current_difficulty = initial_difficulty
        self.problems_attempted: List[ProblemAttempt] = []
        self.skill_profiles: Dict[SkillTag, SkillProfile] = {
            skill: SkillProfile(skill=skill) for skill in SkillTag
        }
        self.domain_performance: Dict[ProblemDomain, List[bool]] = defaultdict(list)

        # Problem pools by difficulty and domain
        self.problem_pools: Dict[int, Dict[ProblemDomain, List[ProblemSpec]]] = defaultdict(
            lambda: defaultdict(list)
        )
        self.used_problems: Set[str] = set()

        # Statistics
        self.stats = {
            "total_attempts": 0,
            "total_successes": 0,
            "current_streak": 0,
            "best_streak": 0,
            "level_changes": 0,
        }

    async def initialize(self):
        """Initialize problem pools by generating problems."""
        if self.problem_generator:
            problems = await self.problem_generator()
            for prob in problems:
                self.problem_pools[prob.difficulty][prob.domain].append(prob)
        else:
            # Generate default problems
            await self._generate_default_problems()

        logger.info(
            f"Curriculum initialized with {sum(len(p) for d in self.problem_pools.values() for p in d.values())} problems"
        )

    async def _generate_default_problems(self):
        """Generate default problem set for each domain/difficulty."""
        for domain in ProblemDomain:
            for difficulty in range(1, self.max_difficulty + 1):
                for i in range(5):  # 5 problems per domain per difficulty
                    prob = ProblemSpec(
                        problem_id=f"{domain.value}_d{difficulty}_{i}",
                        domain=domain,
                        skills=self._get_skills_for_domain(domain, difficulty),
                        difficulty=difficulty,
                        description=self._generate_description(domain, difficulty),
                        starter_code=self._generate_starter_code(domain, difficulty),
                        test_cases=self._generate_test_cases(domain, difficulty),
                    )
                    self.problem_pools[difficulty][domain].append(prob)

    def _get_skills_for_domain(self, domain: ProblemDomain, difficulty: int) -> List[SkillTag]:
        """Map domain and difficulty to relevant skills."""
        domain_skills = {
            ProblemDomain.ALGORITHMIC: [
                SkillTag.RECURSION,
                SkillTag.DYNAMIC_PROGRAMMING,
                SkillTag.GRAPH_ALGORITHMS,
                SkillTag.SORTING_SEARCHING,
            ],
            ProblemDomain.DEBUGGING: [
                SkillTag.ERROR_HANDLING,
                SkillTag.MEMORY_MANAGEMENT,
            ],
            ProblemDomain.OPTIMIZATION: [
                SkillTag.PERFORMANCE_PROFILING,
                SkillTag.DYNAMIC_PROGRAMMING,
            ],
            ProblemDomain.ARCHITECTURE: [
                SkillTag.DESIGN_PATTERNS,
                SkillTag.API_DESIGN,
                SkillTag.DATABASE_DESIGN,
                SkillTag.DISTRIBUTED_SYSTEMS,
            ],
            ProblemDomain.REFACTORING: [
                SkillTag.DESIGN_PATTERNS,
                SkillTag.ERROR_HANDLING,
            ],
            ProblemDomain.TESTING: [
                SkillTag.TEST_DESIGN,
                SkillTag.ERROR_HANDLING,
            ],
            ProblemDomain.SECURITY: [
                SkillTag.SECURITY_AUDITING,
                SkillTag.ERROR_HANDLING,
            ],
            ProblemDomain.CONCURRENCY: [
                SkillTag.MEMORY_MANAGEMENT,
                SkillTag.DISTRIBUTED_SYSTEMS,
            ],
            ProblemDomain.DATA_STRUCTURES: [
                SkillTag.TREE_TRAVERSAL,
                SkillTag.GRAPH_ALGORITHMS,
                SkillTag.SORTING_SEARCHING,
                SkillTag.RECURSION,
            ],
            ProblemDomain.SYSTEM_DESIGN: [
                SkillTag.DISTRIBUTED_SYSTEMS,
                SkillTag.API_DESIGN,
                SkillTag.DATABASE_DESIGN,
                SkillTag.DESIGN_PATTERNS,
            ],
        }
        skills = domain_skills.get(domain, [])
        # Return subset based on difficulty
        return skills[: min(len(skills), max(1, difficulty // 2))]

    def _generate_description(self, domain: ProblemDomain, difficulty: int) -> str:
        """Generate problem description template."""
        templates = {
            ProblemDomain.ALGORITHMIC: [
                "Implement an efficient algorithm to solve {task}.",
                "Design an algorithm with O({complexity}) complexity for {task}.",
            ],
            ProblemDomain.DEBUGGING: [
                "Fix the bug in the following code that {issue}.",
                "Identify and correct the error causing {issue}.",
            ],
            ProblemDomain.OPTIMIZATION: [
                "Optimize the following code to reduce {metric} by {target}%.",
                "Improve the performance of {component} to handle {scale}.",
            ],
            ProblemDomain.ARCHITECTURE: [
                "Design a {system_type} that supports {requirements}.",
                "Architect a solution for {scenario} with {constraints}.",
            ],
            ProblemDomain.REFACTORING: [
                "Refactor the following code to improve {quality}.",
                "Apply {pattern} pattern to improve the design of {component}.",
            ],
            ProblemDomain.TESTING: [
                "Write comprehensive tests for {component} covering {scenarios}.",
                "Design a test strategy for {system} with {coverage}% coverage.",
            ],
            ProblemDomain.SECURITY: [
                "Identify and fix the security vulnerability in {component}.",
                "Implement {security_measure} to protect against {threat}.",
            ],
            ProblemDomain.CONCURRENCY: [
                "Implement thread-safe {component} for {scenario}.",
                "Design a concurrent solution for {task} avoiding race conditions.",
            ],
            ProblemDomain.DATA_STRUCTURES: [
                "Implement {data_structure} with {operations} operations.",
                "Design a data structure to efficiently support {operations}.",
            ],
            ProblemDomain.SYSTEM_DESIGN: [
                "Design a scalable system for {use_case} with {requirements}.",
                "Architect a {system_type} that handles {scale} requests/second.",
            ],
        }

        domain_templates = templates.get(domain, ["Solve the following problem."])
        template = random.choice(domain_templates)

        # Fill in template variables based on difficulty
        complexity = "n log n" if difficulty <= 5 else "n"
        metrics = ["time complexity", "space complexity", "execution time"]

        return template.format(
            task=f"a difficulty-{difficulty} problem",
            complexity=complexity,
            issue="produces incorrect output",
            metric=random.choice(metrics),
            target=difficulty * 10,
            component="the given function",
            scale=f"{difficulty * 1000} concurrent users",
            system_type="distributed system",
            requirements="high availability and scalability",
            scenario="real-time data processing",
            constraints="strict latency requirements",
            quality="readability and maintainability",
            pattern="Strategy",
            scenarios="edge cases and error conditions",
            coverage=80 + difficulty * 2,
            security_measure="input validation",
            threat="SQL injection",
            data_structure="balanced BST",
            operations="insert, delete, search",
            use_case="real-time analytics",
            scale_int=difficulty * 1000,
        )

    def _generate_starter_code(self, domain: ProblemDomain, difficulty: int) -> str:
        """Generate starter code template."""
        templates = {
            ProblemDomain.ALGORITHMIC: '''
def solve(input_data):
    """
    Solve the problem.
    
    Args:
        input_data: The input to process
        
    Returns:
        The solution
    """
    # Your implementation here
    pass
''',
            ProblemDomain.DEBUGGING: '''
def buggy_function(data):
    """This function has a bug."""
    result = []
    for item in data:
        # Bug: off-by-one error
        if item > 0:
            result.append(item * 2)
        else:
            result.append(item / 2)  # Bug here
    return result
''',
            ProblemDomain.OPTIMIZATION: '''
def slow_function(items):
    """This function is slow."""
    result = []
    for i in range(len(items)):
        for j in range(len(items)):
            if items[i] < items[j]:
                result.append((items[i], items[j]))
    return result
''',
        }
        return templates.get(domain, templates[ProblemDomain.ALGORITHMIC])

    def _generate_test_cases(self, domain: ProblemDomain, difficulty: int) -> List[Dict[str, Any]]:
        """Generate test cases for the problem."""
        base_cases = [
            {"input": [1, 2, 3], "expected": [2, 4, 6], "description": "Basic case"},
            {"input": [], "expected": [], "description": "Empty input"},
            {"input": [0], "expected": [0], "description": "Single element"},
        ]

        # Add difficulty-specific cases
        if difficulty >= 3:
            base_cases.append(
                {"input": [-1, -2, 3], "expected": [-2, -4, 6], "description": "Negative numbers"}
            )
        if difficulty >= 5:
            base_cases.append(
                {
                    "input": list(range(1000)),
                    "expected": list(range(0, 2000, 2)),
                    "description": "Large input",
                }
            )

        return base_cases

    async def get_next_problem(
        self,
        domain: Optional[ProblemDomain] = None,
        preferred_skills: Optional[List[SkillTag]] = None,
    ) -> Optional[ProblemSpec]:
        """
        Get the next problem to attempt.

        Selects based on:
        - Current difficulty level
        - Domain preference
        - Skills needing practice (spaced repetition)
        - Unused problems preferred
        """
        # Apply decay to skills
        self._apply_skill_decay()

        # Determine candidate difficulties
        candidate_difficulties = self._get_candidate_difficulties()

        # Find best problem
        best_problem = None
        best_score = -1

        for difficulty in candidate_difficulties:
            domains_to_check = [domain] if domain else list(ProblemDomain)

            for d in domains_to_check:
                pool = self.problem_pools[difficulty][d]

                for prob in pool:
                    if prob.problem_id in self.used_problems:
                        continue

                    # Score problem based on relevance
                    score = self._score_problem(prob, preferred_skills)

                    if score > best_score:
                        best_score = score
                        best_problem = prob

        if best_problem:
            self.used_problems.add(best_problem.problem_id)
            return best_problem

        # If no unused problems, allow reuse of oldest
        return self._get_oldest_unused_problem(domain)

    def _get_candidate_difficulties(self) -> List[int]:
        """Get list of difficulty levels to consider."""
        # Current level ± 1
        candidates = [self.current_difficulty]

        if self.current_difficulty > 1:
            candidates.append(self.current_difficulty - 1)
        if self.current_difficulty < self.max_difficulty:
            candidates.append(self.current_difficulty + 1)

        return sorted(candidates)

    def _score_problem(
        self,
        problem: ProblemSpec,
        preferred_skills: Optional[List[SkillTag]] = None,
    ) -> float:
        """Score a problem for selection."""
        score = 0.0

        # Base score from difficulty match
        diff_diff = abs(problem.difficulty - self.current_difficulty)
        score += 10.0 / (1.0 + diff_diff)

        # Boost for skills needing practice
        for skill in problem.skills:
            profile = self.skill_profiles[skill]

            # Spaced repetition: boost if not practiced recently
            if profile.last_practiced:
                hours_since = (datetime.utcnow() - profile.last_practiced).total_seconds() / 3600
                if hours_since > self.spaced_repetition_interval:
                    score += 5.0 * (1.0 - profile.proficiency)

            # Boost for low proficiency skills
            score += 3.0 * (1.0 - profile.proficiency)

            # Boost for preferred skills
            if preferred_skills and skill in preferred_skills:
                score += 2.0

        # Boost for domains with low performance
        domain_perf = self.domain_performance.get(problem.domain, [])
        if domain_perf:
            success_rate = sum(domain_perf) / len(domain_perf)
            score += 4.0 * (1.0 - success_rate)

        return score

    def _apply_skill_decay(self):
        """Apply time-based decay to all skills."""
        now = datetime.utcnow()
        for profile in self.skill_profiles.values():
            if profile.last_practiced:
                days = (now - profile.last_practiced).total_seconds() / 86400
                profile.apply_decay(days)

    def _get_oldest_unused_problem(self, domain: Optional[ProblemDomain]) -> Optional[ProblemSpec]:
        """Get the oldest problem that was used longest ago."""
        # In practice, would track last used time
        # For now, just return a random problem from current level
        domains = [domain] if domain else list(ProblemDomain)
        for d in domains:
            pool = self.problem_pools[self.current_difficulty][d]
            if pool:
                return random.choice(pool)
        return None

    def record_attempt(self, attempt: ProblemAttempt):
        """Record a problem attempt and update curriculum."""
        self.problems_attempted.append(attempt)
        self.stats["total_attempts"] += 1

        if attempt.success:
            self.stats["total_successes"] += 1
            self.stats["current_streak"] += 1
            self.stats["best_streak"] = max(self.stats["best_streak"], self.stats["current_streak"])
        else:
            self.stats["current_streak"] = 0

        # Update domain performance
        # Need to find the problem to get domain
        problem = self._find_problem(attempt.problem_id)
        if problem:
            self.domain_performance[problem.domain].append(attempt.success)

        # Update skill profiles
        for skill, score in attempt.skill_scores.items():
            self.skill_profiles[skill].update(attempt.success, score)

        # Check for difficulty adjustment
        self._check_difficulty_adjustment()

        logger.info(
            f"Attempt recorded: {attempt.problem_id} - {'Success' if attempt.success else 'Failed'}"
        )

    def _find_problem(self, problem_id: str) -> Optional[ProblemSpec]:
        """Find a problem by ID."""
        for pool_dict in self.problem_pools.values():
            for pool in pool_dict.values():
                for prob in pool:
                    if prob.problem_id == problem_id:
                        return prob
        return None

    def _check_difficulty_adjustment(self):
        """Check if difficulty should be adjusted based on recent performance."""
        if len(self.problems_attempted) < self.min_problems_per_level:
            return

        # Look at recent performance at current difficulty
        recent = [a for a in self.problems_attempted[-self.min_problems_per_level :]]
        if not recent:
            return

        success_rate = sum(1 for a in recent if a.success) / len(recent)

        if (
            success_rate >= self.advancement_threshold
            and self.current_difficulty < self.max_difficulty
        ):
            self.current_difficulty += 1
            self.stats["level_changes"] += 1
            logger.info(
                f"Difficulty increased to {self.current_difficulty} (success rate: {success_rate:.2f})"
            )

        elif success_rate <= self.regression_threshold and self.current_difficulty > 1:
            self.current_difficulty -= 1
            self.stats["level_changes"] += 1
            logger.info(
                f"Difficulty decreased to {self.current_difficulty} (success rate: {success_rate:.2f})"
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get curriculum statistics."""
        skill_stats = {}
        for skill, profile in self.skill_profiles.items():
            if profile.attempts > 0:
                skill_stats[skill.value] = {
                    "proficiency": profile.proficiency,
                    "success_rate": profile.success_rate,
                    "attempts": profile.attempts,
                    "last_practiced": (
                        profile.last_practiced.isoformat() if profile.last_practiced else None
                    ),
                }

        domain_stats = {}
        for domain, results in self.domain_performance.items():
            if results:
                domain_stats[domain.value] = {
                    "success_rate": sum(results) / len(results),
                    "attempts": len(results),
                }

        return {
            "current_difficulty": self.current_difficulty,
            "max_difficulty": self.max_difficulty,
            "total_attempts": self.stats["total_attempts"],
            "total_successes": self.stats["total_successes"],
            "overall_success_rate": (
                self.stats["total_successes"] / self.stats["total_attempts"]
                if self.stats["total_attempts"] > 0
                else 0
            ),
            "current_streak": self.stats["current_streak"],
            "best_streak": self.stats["best_streak"],
            "level_changes": self.stats["level_changes"],
            "used_problems": len(self.used_problems),
            "skills": skill_stats,
            "domains": domain_stats,
        }

    def get_skill_recommendations(self, top_n: int = 5) -> List[Dict[str, Any]]:
        """Get recommended skills to practice."""
        skills = [
            {
                "skill": skill.value,
                "proficiency": profile.proficiency,
                "success_rate": profile.success_rate,
                "needs_practice": profile.proficiency < 0.6
                or (
                    profile.last_practiced
                    and (datetime.utcnow() - profile.last_practiced).total_seconds() / 3600
                    > self.spaced_repetition_interval
                ),
            }
            for skill, profile in self.skill_profiles.items()
            if profile.attempts > 0
        ]

        skills.sort(key=lambda x: x["proficiency"])
        return skills[:top_n]
