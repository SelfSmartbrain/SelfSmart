"""Test runner for executing tests across multiple languages."""

import subprocess
import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum


class TestFramework(Enum):
    """Supported test frameworks."""
    PYTEST = "pytest"
    NPM = "npm"
    CARGO = "cargo"
    GO = "go"
    MAVEN = "maven"
    GRADLE = "gradle"


@dataclass
class TestResult:
    """Result of a test run."""
    framework: TestFramework
    success: bool
    pass_rate: float = 0.0
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    execution_time: float = 0.0
    errors: List[str] = field(default_factory=list)
    output: str = ""
    coverage: Optional[Dict] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'framework': self.framework.value,
            'success': self.success,
            'pass_rate': self.pass_rate,
            'total_tests': self.total_tests,
            'passed_tests': self.passed_tests,
            'failed_tests': self.failed_tests,
            'skipped_tests': self.skipped_tests,
            'execution_time': self.execution_time,
            'errors': self.errors,
            'output': self.output,
            'coverage': self.coverage
        }


class TestRunner:
    """Runs tests across multiple languages and frameworks."""

    FRAMEWORK_COMMANDS = {
        TestFramework.PYTEST: ['pytest', '-v', '--tb=short'],
        TestFramework.NPM: ['npm', 'test'],
        TestFramework.CARGO: ['cargo', 'test'],
        TestFramework.GO: ['go', 'test', './...'],
        TestFramework.MAVEN: ['mvn', 'test'],
        TestFramework.GRADLE: ['gradle', 'test'],
    }

    def __init__(self, repository_path: str):
        self.repository_path = Path(repository_path)

    def run_tests(self, framework: Optional[TestFramework] = None, args: Optional[List[str]] = None) -> TestResult:
        """Run tests with specified framework."""
        if framework is None:
            framework = self._detect_framework()

        if framework is None:
            return TestResult(
                framework=TestFramework.PYTEST,
                success=False,
                errors=["No test framework detected"]
            )

        command = self._build_command(framework, args)
        result = self._execute_command(command, framework)
        
        return result

    def _detect_framework(self) -> Optional[TestFramework]:
        """Detect the test framework from repository structure."""
        # Check for Python/pytest
        if (self.repository_path / 'pytest.ini').exists() or \
           (self.repository_path / 'pyproject.toml').exists() or \
           (self.repository_path / 'setup.py').exists():
            return TestFramework.PYTEST

        # Check for JavaScript/npm
        if (self.repository_path / 'package.json').exists():
            return TestFramework.NPM

        # Check for Rust/cargo
        if (self.repository_path / 'Cargo.toml').exists():
            return TestFramework.CARGO

        # Check for Go
        if (self.repository_path / 'go.mod').exists():
            return TestFramework.GO

        # Check for Java/Maven
        if (self.repository_path / 'pom.xml').exists():
            return TestFramework.MAVEN

        # Check for Java/Gradle
        if (self.repository_path / 'build.gradle').exists():
            return TestFramework.GRADLE

        return None

    def _build_command(self, framework: TestFramework, args: Optional[List[str]]) -> List[str]:
        """Build the test command."""
        base_command = self.FRAMEWORK_COMMANDS.get(framework, [])
        
        if args:
            command = base_command + args
        else:
            command = base_command

        # Add coverage flag for pytest if not specified
        if framework == TestFramework.PYTEST and '--cov' not in ' '.join(command):
            command = base_command + ['--cov=.', '--cov-report=json']

        return command

    def _execute_command(self, command: List[str], framework: TestFramework) -> TestResult:
        """Execute the test command and parse results."""
        try:
            result = subprocess.run(
                command,
                cwd=self.repository_path,
                capture_output=True,
                text=True,
                timeout=300  # 5 minute timeout
            )

            output = result.stdout + result.stderr
            success = result.returncode == 0

            if framework == TestFramework.PYTEST:
                return self._parse_pytest_output(output, success)
            elif framework == TestFramework.NPM:
                return self._parse_npm_output(output, success)
            elif framework == TestFramework.CARGO:
                return self._parse_cargo_output(output, success)
            elif framework == TestFramework.GO:
                return self._parse_go_output(output, success)
            else:
                return self._parse_generic_output(output, success, framework)

        except subprocess.TimeoutExpired:
            return TestResult(
                framework=framework,
                success=False,
                errors=["Test execution timed out"]
            )
        except Exception as e:
            return TestResult(
                framework=framework,
                success=False,
                errors=[str(e)]
            )

    def _parse_pytest_output(self, output: str, success: bool) -> TestResult:
        """Parse pytest output."""
        result = TestResult(framework=TestFramework.PYTEST, success=success, output=output)

        # Parse test counts
        match = re.search(r'(\d+) passed, (\d+) failed', output)
        if match:
            result.passed_tests = int(match.group(1))
            result.failed_tests = int(match.group(2))
            result.total_tests = result.passed_tests + result.failed_tests
        else:
            match = re.search(r'(\d+) passed', output)
            if match:
                result.passed_tests = int(match.group(1))
                result.total_tests = result.passed_tests

        # Parse skipped
        match = re.search(r'(\d+) skipped', output)
        if match:
            result.skipped_tests = int(match.group(1))

        # Parse execution time
        match = re.search(r'in ([\d.]+)s', output)
        if match:
            result.execution_time = float(match.group(1))

        # Calculate pass rate
        if result.total_tests > 0:
            result.pass_rate = result.passed_tests / result.total_tests

        # Parse coverage if available
        coverage_file = self.repository_path / 'coverage.json'
        if coverage_file.exists():
            try:
                with open(coverage_file) as f:
                    coverage_data = json.load(f)
                    result.coverage = {
                        'percent': coverage_data.get('totals', {}).get('percent_covered', 0),
                        'lines_covered': coverage_data.get('totals', {}).get('covered_lines', 0),
                        'lines_missing': coverage_data.get('totals', {}).get('missing_lines', 0)
                    }
            except (json.JSONDecodeError, IOError):
                pass

        # Extract errors
        if not success:
            result.errors = self._extract_errors(output)

        return result

    def _parse_npm_output(self, output: str, success: bool) -> TestResult:
        """Parse npm test output."""
        result = TestResult(framework=TestFramework.NPM, success=success, output=output)

        # Parse Jest or other test runner output
        match = re.search(r'Tests:\s+(\d+) passed, (\d+) failed', output)
        if match:
            result.passed_tests = int(match.group(1))
            result.failed_tests = int(match.group(2))
            result.total_tests = result.passed_tests + result.failed_tests
        else:
            # Try alternative patterns
            match = re.search(r'✓\s+(\d+)', output)
            if match:
                result.passed_tests = int(match.group(1))
                result.total_tests = result.passed_tests

        # Calculate pass rate
        if result.total_tests > 0:
            result.pass_rate = result.passed_tests / result.total_tests

        # Extract errors
        if not success:
            result.errors = self._extract_errors(output)

        return result

    def _parse_cargo_output(self, output: str, success: bool) -> TestResult:
        """Parse cargo test output."""
        result = TestResult(framework=TestFramework.CARGO, success=success, output=output)

        # Parse test results
        match = re.search(r'test result: ok\. (\d+) passed', output)
        if match:
            result.passed_tests = int(match.group(1))
            result.total_tests = result.passed_tests
        else:
            match = re.search(r'passed; (\d+) failed', output)
            if match:
                result.failed_tests = int(match.group(1))

        # Calculate pass rate
        if result.total_tests > 0:
            result.pass_rate = result.passed_tests / result.total_tests

        # Extract errors
        if not success:
            result.errors = self._extract_errors(output)

        return result

    def _parse_go_output(self, output: str, success: bool) -> TestResult:
        """Parse go test output."""
        result = TestResult(framework=TestFramework.GO, success=success, output=output)

        # Go test output is simple: PASS or FAIL
        if success:
            result.passed_tests = 1
            result.total_tests = 1
            result.pass_rate = 1.0
        else:
            result.failed_tests = 1
            result.total_tests = 1
            result.pass_rate = 0.0

        # Extract errors
        if not success:
            result.errors = self._extract_errors(output)

        return result

    def _parse_generic_output(self, output: str, success: bool, framework: TestFramework) -> TestResult:
        """Parse generic test output."""
        result = TestResult(framework=framework, success=success, output=output)

        if success:
            result.passed_tests = 1
            result.total_tests = 1
            result.pass_rate = 1.0
        else:
            result.failed_tests = 1
            result.total_tests = 1
            result.pass_rate = 0.0
            result.errors = self._extract_errors(output)

        return result

    def _extract_errors(self, output: str) -> List[str]:
        """Extract error messages from output."""
        errors = []
        
        # Common error patterns
        error_patterns = [
            r'Error: (.+)',
            r'FAILED\s+(.+)',
            r'AssertionError: (.+)',
            r'Exception: (.+)',
            r'panic: (.+)',
        ]

        for pattern in error_patterns:
            matches = re.findall(pattern, output)
            errors.extend(matches)

        return errors[:10]  # Limit to first 10 errors

    def run_specific_test(self, test_path: str, framework: Optional[TestFramework] = None) -> TestResult:
        """Run a specific test file or test."""
        if framework is None:
            framework = self._detect_framework()

        if framework == TestFramework.PYTEST:
            command = ['pytest', test_path, '-v']
        elif framework == TestFramework.NPM:
            command = ['npm', 'test', '--', test_path]
        elif framework == TestFramework.GO:
            command = ['go', 'test', test_path]
        else:
            command = self.FRAMEWORK_COMMANDS.get(framework, []) + [test_path]

        return self._execute_command(command, framework)

    def get_test_files(self) -> List[str]:
        """Get list of test files in the repository."""
        test_files = []
        
        # Python test files
        for pattern in ['test_*.py', '*_test.py']:
            test_files.extend([str(f.relative_to(self.repository_path)) 
                             for f in self.repository_path.rglob(pattern)])
        
        # JavaScript/TypeScript test files
        for pattern in ['*.test.js', '*.test.ts', '*.spec.js', '*.spec.ts']:
            test_files.extend([str(f.relative_to(self.repository_path)) 
                             for f in self.repository_path.rglob(pattern)])
        
        # Go test files
        test_files.extend([str(f.relative_to(self.repository_path)) 
                         for f in self.repository_path.rglob('*_test.go')])
        
        return test_files
