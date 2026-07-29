"""
Synthetic Problem Generator - Creates realistic programming problems for self-play.

Generates problems across multiple domains with varying difficulty,
complete with test cases and starter code.
"""

import random
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from enum import Enum

from .curriculum_engine import SkillTag, ProblemDomain, ProblemSpec

logger = logging.getLogger(__name__)


class ProblemType(Enum):
    """Types of synthetic problems."""

    FUNCTION_IMPLEMENTATION = "function_implementation"
    BUG_FIX = "bug_fix"
    OPTIMIZATION = "optimization"
    REFACTORING = "refactoring"
    ALGORITHM = "algorithm"
    DATA_STRUCTURE = "data_structure"
    API_DESIGN = "api_design"
    ERROR_HANDLING = "error_handling"
    TEST_WRITING = "test_writing"
    SECURITY_AUDIT = "security_audit"


@dataclass
class ProblemTemplate:
    """Template for generating problems."""

    problem_type: ProblemType
    domain: ProblemDomain
    skills: List[SkillTag]
    difficulty_range: tuple = (1, 5)
    description_template: str = ""
    starter_code_template: str = ""
    test_case_generators: List[callable] = field(default_factory=list)


class SyntheticProblemGenerator:
    """
    Generates synthetic programming problems for training.

    Features:
    - Multiple problem domains
    - Adjustable difficulty
    - Skill-specific problems
    - Realistic test cases
    - Starter code templates
    """

    def __init__(self, seed: Optional[int] = None):
        if seed is not None:
            random.seed(seed)

        self._templates = self._build_templates()
        self._generated_count = 0

    def _build_templates(self) -> Dict[ProblemDomain, List[ProblemTemplate]]:
        """Build problem templates by domain."""
        templates = {}

        # Algorithmic problems
        templates[ProblemDomain.ALGORITHMIC] = [
            ProblemTemplate(
                problem_type=ProblemType.ALGORITHM,
                domain=ProblemDomain.ALGORITHMIC,
                skills=[SkillTag.SORTING_SEARCHING, SkillTag.RECURSION],
                difficulty_range=(1, 3),
                description_template="Implement {algorithm} to {task}.",
                starter_code_template='''
def {function_name}({params}):
    """
    {description}
    """
    # TODO: Implement {algorithm}
    pass
''',
                test_case_generators=[self._gen_sort_test, self._gen_search_test],
            ),
            ProblemTemplate(
                problem_type=ProblemType.ALGORITHM,
                domain=ProblemDomain.ALGORITHMIC,
                skills=[SkillTag.DYNAMIC_PROGRAMMING, SkillTag.RECURSION],
                difficulty_range=(3, 5),
                description_template="Solve {problem} using dynamic programming.",
                starter_code_template='''
def {function_name}({params}):
    """
    {description}
    Use dynamic programming for optimal solution.
    """
    # TODO: Implement DP solution
    pass
''',
                test_case_generators=[self._gen_dp_test],
            ),
        ]

        # Data structure problems
        templates[ProblemDomain.DATA_STRUCTURES] = [
            ProblemTemplate(
                problem_type=ProblemType.DATA_STRUCTURE,
                domain=ProblemDomain.DATA_STRUCTURES,
                skills=[SkillTag.TREE_TRAVERSAL, SkillTag.RECURSION],
                difficulty_range=(2, 4),
                description_template="Implement {operation} for a {data_structure}.",
                starter_code_template='''
class {class_name}:
    def __init__(self):
        self.root = None
    
    def {method_name}(self, {params}):
        """
        {description}
        """
        # TODO: Implement
        pass
''',
                test_case_generators=[self._gen_tree_test],
            ),
            ProblemTemplate(
                problem_type=ProblemType.DATA_STRUCTURE,
                domain=ProblemDomain.DATA_STRUCTURES,
                skills=[SkillTag.GRAPH_ALGORITHMS],
                difficulty_range=(3, 5),
                description_template="Implement {algorithm} for graph {task}.",
                starter_code_template='''
def {function_name}(graph, {params}):
    """
    {description}
    Graph represented as adjacency list.
    """
    # TODO: Implement {algorithm}
    pass
''',
                test_case_generators=[self._gen_graph_test],
            ),
        ]

        # Bug fixing
        templates[ProblemDomain.DEBUGGING] = [
            ProblemTemplate(
                problem_type=ProblemType.BUG_FIX,
                domain=ProblemDomain.DEBUGGING,
                skills=[SkillTag.ERROR_HANDLING, SkillTag.STRING_MANIPULATION],
                difficulty_range=(1, 3),
                description_template="Fix the bug in {function} that causes {issue}.",
                starter_code_template='''
def {function_name}({params}):
    """This function has a bug."""
    result = []
    for item in {iterable}:
        # Bug: {bug_description}
        if item {condition}:
            result.append(item * 2)
        else:
            result.append(item / 2)  # Bug here
    return result
''',
                test_case_generators=[self._gen_bug_fix_test],
            ),
        ]

        # Optimization
        templates[ProblemDomain.OPTIMIZATION] = [
            ProblemTemplate(
                problem_type=ProblemType.OPTIMIZATION,
                domain=ProblemDomain.OPTIMIZATION,
                skills=[SkillTag.PERFORMANCE_PROFILING, SkillTag.DYNAMIC_PROGRAMMING],
                difficulty_range=(3, 5),
                description_template="Optimize {function} to reduce {metric} from O({old_complexity}) to O({new_complexity}).",
                starter_code_template='''
def {function_name}({params}):
    """Current implementation is slow."""
    # O({old_complexity}) implementation
    result = []
    for i in range(len({iterable})):
        for j in range(len({iterable})):
            if {condition}:
                result.append(({iterable}[i], {iterable}[j]))
    return result
''',
                test_case_generators=[self._gen_optimization_test],
            ),
        ]

        # API Design
        templates[ProblemDomain.ARCHITECTURE] = [
            ProblemTemplate(
                problem_type=ProblemType.API_DESIGN,
                domain=ProblemDomain.ARCHITECTURE,
                skills=[SkillTag.API_DESIGN, SkillTag.DESIGN_PATTERNS],
                difficulty_range=(2, 4),
                description_template="Design a {pattern} pattern for {use_case}.",
                starter_code_template='''
class {class_name}:
    """{description}"""
    
    def __init__(self):
        # TODO: Initialize
        pass
    
    def {method_name}(self, {params}):
        """{method_description}"""
        # TODO: Implement
        pass
''',
                test_case_generators=[self._gen_api_test],
            ),
        ]

        # Error handling
        templates[ProblemDomain.TESTING] = [
            ProblemTemplate(
                problem_type=ProblemType.TEST_WRITING,
                domain=ProblemDomain.TESTING,
                skills=[SkillTag.TEST_DESIGN, SkillTag.ERROR_HANDLING],
                difficulty_range=(1, 3),
                description_template="Write comprehensive tests for {function} covering {scenarios}.",
                starter_code_template='''
import pytest

def {function_name}({params}):
    """Function to test."""
    # Implementation exists but needs tests
    pass

# TODO: Write tests below
''',
                test_case_generators=[self._gen_test_writing_test],
            ),
        ]

        # Security
        templates[ProblemDomain.SECURITY] = [
            ProblemTemplate(
                problem_type=ProblemType.SECURITY_AUDIT,
                domain=ProblemDomain.SECURITY,
                skills=[SkillTag.SECURITY_AUDITING],
                difficulty_range=(2, 4),
                description_template="Identify and fix the {vulnerability} vulnerability in {function}.",
                starter_code_template='''
def {function_name}({params}):
    """Vulnerable function."""
    # Vulnerability: {vulnerability_description}
    query = f"SELECT * FROM users WHERE name = '{params}'"
    return execute(query)
''',
                test_case_generators=[self._gen_security_test],
            ),
        ]

        return templates

    def generate(
        self,
        domain: Optional[ProblemDomain] = None,
        difficulty: Optional[int] = None,
        skills: Optional[List[SkillTag]] = None,
        problem_type: Optional[ProblemType] = None,
    ) -> ProblemSpec:
        """
        Generate a synthetic problem.

        Args:
            domain: Problem domain (random if None)
            difficulty: Difficulty 1-5 (random if None)
            skills: Required skills (inferred from domain if None)
            problem_type: Specific problem type (random if None)

        Returns:
            ProblemSpec with complete problem definition
        """
        # Select domain
        if domain is None:
            domain = random.choice(list(self._templates.keys()))

        templates = self._templates.get(domain, [])
        if not templates:
            # Fallback
            domain = ProblemDomain.ALGORITHMIC
            templates = self._templates[domain]

        # Filter by difficulty
        if difficulty is not None:
            templates = [
                t for t in templates if t.difficulty_range[0] <= difficulty <= t.difficulty_range[1]
            ]

        # Filter by problem type
        if problem_type is not None:
            templates = [t for t in templates if t.problem_type == problem_type]

        if not templates:
            # Relax filters
            templates = self._templates[domain]

        template = random.choice(templates)

        # Determine difficulty
        if difficulty is None:
            difficulty = random.randint(*template.difficulty_range)
        else:
            difficulty = max(
                template.difficulty_range[0], min(difficulty, template.difficulty_range[1])
            )

        # Determine skills
        if skills is None:
            skills = template.skills

        # Generate problem ID
        self._generated_count += 1
        problem_id = (
            f"{domain.value}_{template.problem_type.value}_{difficulty}_{self._generated_count}"
        )

        # Fill templates
        description = self._fill_template(
            template.description_template, domain, difficulty, template.problem_type
        )
        starter_code = self._fill_template(
            template.starter_code_template, domain, difficulty, template.problem_type
        )

        # Generate test cases
        test_cases = []
        for generator in template.test_case_generators:
            test_cases.extend(generator(domain, difficulty, template.problem_type))

        # Ensure minimum test cases
        if not test_cases:
            test_cases = self._generate_default_tests(domain, difficulty)

        return ProblemSpec(
            problem_id=problem_id,
            domain=domain,
            skills=skills,
            difficulty=difficulty,
            description=description,
            starter_code=starter_code,
            test_cases=test_cases,
            metadata={
                "problem_type": template.problem_type.value,
                "template": template.problem_type.value,
            },
        )

    def _fill_template(
        self, template: str, domain: ProblemDomain, difficulty: int, ptype: ProblemType
    ) -> str:
        """Fill template variables."""
        # Algorithm names by difficulty
        algorithms = {
            1: ["linear search", "bubble sort", "find max"],
            2: ["binary search", "merge sort", "fibonacci"],
            3: ["quick sort", "dijkstra", "knapsack"],
            4: ["A* search", "min cost flow", "edit distance"],
            5: ["traveling salesman approx", "max flow", "regex matching"],
        }

        algos = algorithms.get(difficulty, algorithms[1])
        algorithm = random.choice(algos)

        replacements = {
            "{algorithm}": algorithm,
            "{task}": "solve the problem efficiently",
            "{problem}": f"the {algorithm} problem",
            "{function_name}": f"solve_{algorithm.replace(' ', '_')}",
            "{params}": "data",
            "{description}": f"Implement {algorithm} algorithm",
            "{data_structure}": random.choice(["binary tree", "graph", "heap", "trie"]),
            "{operation}": random.choice(["insert", "delete", "search", "traverse"]),
            "{class_name}": "DataStructure",
            "{method_name}": "operation",
            "{iterable}": "items",
            "{condition}": "> 0",
            "{bug_description}": "division by zero",
            "{old_complexity}": "n^2",
            "{new_complexity}": "n log n",
            "{pattern}": random.choice(["Factory", "Strategy", "Observer", "Builder"]),
            "{use_case}": "payment processing",
            "{vulnerability}": random.choice(["SQL injection", "XSS", "path traversal"]),
            "{vulnerability_description}": "direct string interpolation in query",
        }

        result = template
        for key, value in replacements.items():
            result = result.replace(key, value)

        return result

    # Test case generators
    def _gen_sort_test(
        self, domain: ProblemDomain, difficulty: int, ptype: ProblemType
    ) -> List[Dict[str, Any]]:
        """Generate sorting test cases."""
        tests = []

        # Basic cases
        tests.append(
            {
                "input": [3, 1, 4, 1, 5],
                "expected": [1, 1, 3, 4, 5],
                "description": "Basic sorting",
            }
        )

        tests.append(
            {
                "input": [],
                "expected": [],
                "description": "Empty list",
            }
        )

        tests.append(
            {
                "input": [1],
                "expected": [1],
                "description": "Single element",
            }
        )

        if difficulty >= 2:
            tests.append(
                {
                    "input": [5, 4, 3, 2, 1],
                    "expected": [1, 2, 3, 4, 5],
                    "description": "Reverse sorted",
                }
            )

        if difficulty >= 3:
            tests.append(
                {
                    "input": list(range(100, 0, -1)),
                    "expected": list(range(1, 101)),
                    "description": "Large reverse sorted",
                }
            )

        return tests

    def _gen_search_test(
        self, domain: ProblemDomain, difficulty: int, ptype: ProblemType
    ) -> List[Dict[str, Any]]:
        """Generate search test cases."""
        arr = list(range(1, 21))

        tests = [
            {
                "input": {"array": arr, "target": 10},
                "expected": 9,
                "description": "Find middle element",
            },
            {
                "input": {"array": arr, "target": 1},
                "expected": 0,
                "description": "Find first element",
            },
            {
                "input": {"array": arr, "target": 20},
                "expected": 19,
                "description": "Find last element",
            },
            {"input": {"array": arr, "target": 25}, "expected": -1, "description": "Not found"},
        ]

        return tests

    def _gen_dp_test(
        self, domain: ProblemDomain, difficulty: int, ptype: ProblemType
    ) -> List[Dict[str, Any]]:
        """Generate dynamic programming test cases."""
        # Fibonacci
        tests = [
            {"input": 0, "expected": 0, "description": "Fibonacci base case 0"},
            {"input": 1, "expected": 1, "description": "Fibonacci base case 1"},
            {"input": 5, "expected": 5, "description": "Fibonacci 5"},
            {"input": 10, "expected": 55, "description": "Fibonacci 10"},
        ]

        if difficulty >= 4:
            tests.append({"input": 20, "expected": 6765, "description": "Fibonacci 20"})

        return tests

    def _gen_tree_test(
        self, domain: ProblemDomain, difficulty: int, ptype: ProblemType
    ) -> List[Dict[str, Any]]:
        """Generate tree test cases."""
        # Simple tree structure tests
        return [
            {"input": {"root": None}, "expected": [], "description": "Empty tree"},
            {
                "input": {"root": {"val": 1, "left": None, "right": None}},
                "expected": [1],
                "description": "Single node",
            },
        ]

    def _gen_graph_test(
        self, domain: ProblemDomain, difficulty: int, ptype: ProblemType
    ) -> List[Dict[str, Any]]:
        """Generate graph test cases."""
        return [
            {"input": {"graph": {}, "start": 0}, "expected": [], "description": "Empty graph"},
            {
                "input": {"graph": {0: [1], 1: [2], 2: []}, "start": 0},
                "expected": [0, 1, 2],
                "description": "Simple path",
            },
        ]

    def _gen_optimization_test(
        self, domain: ProblemDomain, difficulty: int, ptype: ProblemType
    ) -> List[Dict[str, Any]]:
        """Generate optimization test cases."""
        return [
            {
                "input": [1, 2, 3, 4],
                "expected": [(1, 2), (1, 3), (1, 4), (2, 3), (2, 4), (3, 4)],
                "description": "Pairs",
            },
        ]

    def _gen_api_test(
        self, domain: ProblemDomain, difficulty: int, ptype: ProblemType
    ) -> List[Dict[str, Any]]:
        """Generate API design test cases."""
        return [
            {
                "input": {"action": "create", "data": {"name": "test"}},
                "expected": {"id": 1, "name": "test"},
                "description": "Create resource",
            },
        ]

    def _gen_bug_fix_test(
        self, domain: ProblemDomain, difficulty: int, ptype: ProblemType
    ) -> List[Dict[str, Any]]:
        """Generate bug fix test cases."""
        return [
            {"input": [1, 2, 3], "expected": [2, 4, 6], "description": "Positive numbers"},
            {"input": [0], "expected": [0], "description": "Zero"},
            {"input": [-1, -2], "expected": [-2, -4], "description": "Negative numbers"},
        ]

    def _gen_test_writing_test(
        self, domain: ProblemDomain, difficulty: int, ptype: ProblemType
    ) -> List[Dict[str, Any]]:
        """Generate test writing test cases."""
        return [
            {"input": "test_file.py", "expected": "pass", "description": "Tests pass"},
        ]

    def _gen_security_test(
        self, domain: ProblemDomain, difficulty: int, ptype: ProblemType
    ) -> List[Dict[str, Any]]:
        """Generate security test cases."""
        return [
            {"input": "admin' --", "expected": "safe", "description": "SQL injection attempt"},
            {
                "input": "<script>alert(1)</script>",
                "expected": "escaped",
                "description": "XSS attempt",
            },
        ]

    def _generate_default_tests(
        self, domain: ProblemDomain, difficulty: int
    ) -> List[Dict[str, Any]]:
        """Generate default test cases."""
        return [
            {"input": "test", "expected": "result", "description": "Basic test"},
        ]
