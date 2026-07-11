"""
Coding task dataset generator.

Generates real coding tasks for benchmarking engineering capabilities.
"""

import random
from typing import List, Dict, Any
from pathlib import Path

from ..framework.dataset_manager import DatasetGenerator, DatasetItem


class CodingDatasetGenerator(DatasetGenerator):
    """Generate coding tasks for benchmarking real engineering work."""
    
    def get_category(self) -> str:
        return "coding"
    
    def generate(self, num_items: int, seed: int) -> List[DatasetItem]:
        """Generate coding tasks."""
        random.seed(seed)
        
        items = []
        
        # Bug fixing tasks
        for i in range(num_items // 5):
            item = self._generate_bug_fix_task(i, seed)
            items.append(item)
        
        # Feature implementation tasks
        for i in range(num_items // 5):
            item = self._generate_feature_task(i, seed)
            items.append(item)
        
        # Test generation tasks
        for i in range(num_items // 5):
            item = self._generate_test_task(i, seed)
            items.append(item)
        
        # Refactoring tasks
        for i in range(num_items // 5):
            item = self._generate_refactor_task(i, seed)
            items.append(item)
        
        # Documentation tasks
        for i in range(num_items // 5):
            item = self._generate_documentation_task(i, seed)
            items.append(item)
        
        return items[:num_items]
    
    def _generate_bug_fix_task(self, index: int, seed: int) -> DatasetItem:
        """Generate bug fixing task."""
        bugs = [
            {
                "description": "Fix off-by-one error in loop",
                "file": "utils/helpers.py",
                "code": "for i in range(len(items)):\n    process(items[i])",
                "fix": "for i in range(len(items) - 1):\n    process(items[i])",
                "test": "assert loop processes all items correctly"
            },
            {
                "description": "Fix missing return statement",
                "file": "api/handlers.py",
                "code": "def calculate(x, y):\n    result = x + y",
                "fix": "def calculate(x, y):\n    result = x + y\n    return result",
                "test": "assert calculate(2, 3) == 5"
            },
            {
                "description": "Fix variable name typo",
                "file": "models/user.py",
                "code": "user_nmae = request.json['name']",
                "fix": "user_name = request.json['name']",
                "test": "assert user_name is set correctly"
            },
            {
                "description": "Fix null pointer exception",
                "file": "services/data.py",
                "code": "value = data['key'].lower()",
                "fix": "value = data.get('key', '').lower()",
                "test": "assert handles missing key gracefully"
            },
        ]
        
        bug = random.choice(bugs)
        
        return DatasetItem(
            item_id=f"coding_bug_{index}",
            category="coding",
            difficulty=random.choice(["easy", "medium"]),
            task_data={
                "type": "bug_fix",
                "description": bug["description"],
                "file": bug["file"],
                "code": bug["code"],
                "test": bug["test"],
            },
            ground_truth=bug["fix"],
            metadata={
                "file": bug["file"],
                "seed": seed,
            },
        )
    
    def _generate_feature_task(self, index: int, seed: int) -> DatasetItem:
        """Generate feature implementation task."""
        features = [
            {
                "description": "Add input validation to user registration",
                "file": "api/auth.py",
                "requirements": [
                    "Email must be valid format",
                    "Password must be at least 8 characters",
                    "Username must be alphanumeric"
                ],
                "test": "assert invalid inputs are rejected"
            },
            {
                "description": "Add caching to database queries",
                "file": "services/cache.py",
                "requirements": [
                    "Cache results for 5 minutes",
                    "Invalidate cache on data changes",
                    "Handle cache misses gracefully"
                ],
                "test": "assert cache improves performance"
            },
            {
                "description": "Add logging to API endpoints",
                "file": "api/middleware.py",
                "requirements": [
                    "Log request method and path",
                    "Log response status code",
                    "Include timestamp in logs"
                ],
                "test": "assert logs are written correctly"
            },
        ]
        
        feature = random.choice(features)
        
        return DatasetItem(
            item_id=f"coding_feature_{index}",
            category="coding",
            difficulty=random.choice(["medium", "hard"]),
            task_data={
                "type": "feature_implementation",
                "description": feature["description"],
                "file": feature["file"],
                "requirements": feature["requirements"],
                "test": feature["test"],
            },
            ground_truth={
                "file": feature["file"],
                "requirements": feature["requirements"],
            },
            metadata={
                "file": feature["file"],
                "seed": seed,
            },
        )
    
    def _generate_test_task(self, index: int, seed: int) -> DatasetItem:
        """Generate test generation task."""
        test_scenarios = [
            {
                "description": "Write unit tests for calculator module",
                "file": "tests/test_calculator.py",
                "module": "calculator.py",
                "functions": ["add", "subtract", "multiply", "divide"],
                "requirements": [
                    "Test normal cases",
                    "Test edge cases (zero, negative)",
                    "Test error handling (division by zero)"
                ],
            },
            {
                "description": "Write integration tests for API",
                "file": "tests/test_api.py",
                "endpoints": ["/users", "/posts", "/comments"],
                "requirements": [
                    "Test successful requests",
                    "Test error responses",
                    "Test authentication"
                ],
            },
        ]
        
        scenario = random.choice(test_scenarios)
        
        return DatasetItem(
            item_id=f"coding_test_{index}",
            category="coding",
            difficulty="medium",
            task_data={
                "type": "test_generation",
                "description": scenario["description"],
                "file": scenario["file"],
                "requirements": scenario["requirements"],
            },
            ground_truth={
                "file": scenario["file"],
                "requirements": scenario["requirements"],
            },
            metadata={
                "file": scenario["file"],
                "seed": seed,
            },
        )
    
    def _generate_refactor_task(self, index: int, seed: int) -> DatasetItem:
        """Generate refactoring task."""
        refactors = [
            {
                "description": "Extract duplicate code into function",
                "file": "utils/processor.py",
                "code": "def process_a(data):\n    # validation\n    if not data: return None\n    # transformation\n    result = data * 2\n    return result\n\ndef process_b(data):\n    # validation\n    if not data: return None\n    # transformation\n    result = data + 10\n    return result",
                "goal": "Extract validation logic into shared function",
            },
            {
                "description": "Replace magic numbers with constants",
                "file": "config/settings.py",
                "code": "timeout = 30\nmax_retries = 3\nbuffer_size = 1024",
                "goal": "Define constants at module level",
            },
            {
                "description": "Simplify complex conditional logic",
                "file": "business/rules.py",
                "code": "if (x > 0 and y > 0) or (x < 0 and y < 0) or (x == 0 and y == 0):",
                "goal": "Use mathematical simplification",
            },
        ]
        
        refactor = random.choice(refactors)
        
        return DatasetItem(
            item_id=f"coding_refactor_{index}",
            category="coding",
            difficulty="medium",
            task_data={
                "type": "refactoring",
                "description": refactor["description"],
                "file": refactor["file"],
                "code": refactor.get("code"),
                "goal": refactor["goal"],
            },
            ground_truth=refactor["goal"],
            metadata={
                "file": refactor["file"],
                "seed": seed,
            },
        )
    
    def _generate_documentation_task(self, index: int, seed: int) -> DatasetItem:
        """Generate documentation task."""
        docs = [
            {
                "description": "Add docstrings to API module",
                "file": "api/handlers.py",
                "requirements": [
                    "Document all public functions",
                    "Include parameter types",
                    "Include return value descriptions",
                    "Add usage examples"
                ],
            },
            {
                "description": "Write README for new feature",
                "file": "docs/new_feature.md",
                "requirements": [
                    "Describe feature purpose",
                    "Provide installation instructions",
                    "Include usage examples",
                    "Document configuration options"
                ],
            },
        ]
        
        doc = random.choice(docs)
        
        return DatasetItem(
            item_id=f"coding_doc_{index}",
            category="coding",
            difficulty="easy",
            task_data={
                "type": "documentation",
                "description": doc["description"],
                "file": doc["file"],
                "requirements": doc["requirements"],
            },
            ground_truth={
                "file": doc["file"],
                "requirements": doc["requirements"],
            },
            metadata={
                "file": doc["file"],
                "seed": seed,
            },
        )
