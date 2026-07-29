"""
Automated Test Runner - Runs tests in sandbox and production environments.

Executes test suites, captures results, and provides pass/fail metrics
for validating patches before and after deployment.
"""

import asyncio
import logging
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class TestResult:
    """Result of a test run."""

    test_suite: str
    passed: int
    failed: int
    errors: int
    skipped: int
    duration: float
    output: str
    success: bool
    details: List[Dict[str, Any]] = field(default_factory=list)
    run_at: datetime = field(default_factory=datetime.utcnow)

    @property
    def total(self) -> int:
        return self.passed + self.failed + self.errors + self.skipped

    @property
    def pass_rate(self) -> float:
        if self.total == 0:
            return 0.0
        return self.passed / self.total

    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_suite": self.test_suite,
            "passed": self.passed,
            "failed": self.failed,
            "errors": self.errors,
            "skipped": self.skipped,
            "duration": self.duration,
            "success": self.success,
            "pass_rate": self.pass_rate,
            "run_at": self.run_at.isoformat(),
        }


@dataclass
class TestConfig:
    """Configuration for test execution."""

    test_paths: List[str] = field(default_factory=lambda: ["tests"])
    pytest_args: List[str] = field(
        default_factory=lambda: [
            "-v",
            "--tb=short",
            "--strict-markers",
        ]
    )
    timeout: float = 300.0  # 5 minutes
    parallel: bool = True
    max_workers: int = 4
    coverage: bool = False
    coverage_threshold: float = 0.8


class TestRunner:
    """
    Runs test suites in sandbox and production environments.

    Supports:
    - pytest test discovery and execution
    - Parallel test execution
    - Coverage reporting
    - Timeout handling
    - Result aggregation
    """

    def __init__(
        self,
        repo_path: str,
        config: Optional[TestConfig] = None,
    ):
        self.repo_path = Path(repo_path).resolve()
        self.config = config or TestConfig()
        self._initialized = False

    async def initialize(self) -> None:
        """Initialize test runner."""
        if not self.repo_path.exists():
            raise ValueError(f"Repository not found: {self.repo_path}")

        # Check pytest availability
        try:
            proc = await asyncio.create_subprocess_exec(
                "python",
                "-m",
                "pytest",
                "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            await proc.communicate()
            if proc.returncode != 0:
                raise RuntimeError("pytest not available")
        except Exception as e:
            raise RuntimeError(f"pytest not available: {e}")

        self._initialized = True
        logger.info(f"TestRunner initialized for {self.repo_path}")

    async def run_tests(
        self,
        target_path: Optional[Path] = None,
        test_filter: Optional[str] = None,
    ) -> TestResult:
        """
        Run test suite on target path.

        Args:
            target_path: Path to test (defaults to repo_path)
            test_filter: Optional pytest -k filter

        Returns:
            TestResult with execution details
        """
        if not self._initialized:
            await self.initialize()

        target = target_path or self.repo_path
        start_time = datetime.utcnow()

        # Build pytest command
        cmd = ["python", "-m", "pytest"]
        cmd.extend(self.config.pytest_args)

        if self.config.parallel:
            cmd.extend(["-n", str(self.config.max_workers)])

        if test_filter:
            cmd.extend(["-k", test_filter])

        if self.config.coverage:
            cmd.extend(
                [
                    "--cov=src",
                    f"--cov-fail-under={int(self.config.coverage_threshold * 100)}",
                ]
            )

        cmd.extend(self.config.test_paths)

        logger.info(f"Running tests: {' '.join(cmd)}")

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=target,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.config.timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return TestResult(
                    test_suite="pytest",
                    passed=0,
                    failed=0,
                    errors=1,
                    skipped=0,
                    duration=self.config.timeout,
                    output=f"Test timeout after {self.config.timeout}s",
                    success=False,
                )

            duration = (datetime.utcnow() - start_time).total_seconds()
            output = stdout.decode() + stderr.decode()

            # Parse results
            passed, failed, errors, skipped = self._parse_pytest_output(output)
            success = proc.returncode == 0

            return TestResult(
                test_suite="pytest",
                passed=passed,
                failed=failed,
                errors=errors,
                skipped=skipped,
                duration=duration,
                output=output,
                success=success,
            )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            logger.error(f"Test execution failed: {e}")
            return TestResult(
                test_suite="pytest",
                passed=0,
                failed=0,
                errors=1,
                skipped=0,
                duration=duration,
                output=str(e),
                success=False,
            )

    def _parse_pytest_output(self, output: str) -> tuple[int, int, int, int]:
        """Parse pytest output to extract test counts."""
        passed = failed = errors = skipped = 0

        # Look for summary line like: "10 passed, 2 failed, 1 error, 3 skipped in 5.23s"
        import re

        summary_match = re.search(
            r"(\d+)\s+passed(?:, (\d+)\s+failed)?(?:, (\d+)\s+error)?(?:, (\d+)\s+skipped)?",
            output,
        )

        if summary_match:
            passed = int(summary_match.group(1) or 0)
            failed = int(summary_match.group(2) or 0)
            errors = int(summary_match.group(3) or 0)
            skipped = int(summary_match.group(4) or 0)

        return passed, failed, errors, skipped

    async def run_specific_tests(
        self,
        test_files: List[str],
        target_path: Optional[Path] = None,
    ) -> TestResult:
        """Run specific test files."""
        target = target_path or self.repo_path

        cmd = ["python", "-m", "pytest"]
        cmd.extend(self.config.pytest_args)
        cmd.extend(test_files)

        start_time = datetime.utcnow()

        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                cwd=target,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await asyncio.wait_for(
                proc.communicate(),
                timeout=self.config.timeout,
            )

            duration = (datetime.utcnow() - start_time).total_seconds()
            output = stdout.decode() + stderr.decode()

            passed, failed, errors, skipped = self._parse_pytest_output(output)
            success = proc.returncode == 0

            return TestResult(
                test_suite="specific",
                passed=passed,
                failed=failed,
                errors=errors,
                skipped=skipped,
                duration=duration,
                output=output,
                success=success,
            )

        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            return TestResult(
                test_suite="specific",
                passed=0,
                failed=0,
                errors=1,
                skipped=0,
                duration=duration,
                output=str(e),
                success=False,
            )

    async def run_in_sandbox(
        self,
        sandbox_path: Path,
        test_filter: Optional[str] = None,
    ) -> TestResult:
        """Run tests in a sandbox environment."""
        return await self.run_tests(sandbox_path, test_filter)

    async def validate_patch(
        self,
        target_path: Path,
        patch_description: str,
        critical_tests: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """
        Validate a patch by running relevant tests.

        Args:
            target_path: Path where patch was applied
            patch_description: Description of changes
            critical_tests: Specific tests to run for validation

        Returns:
            Validation result with pass/fail and details
        """
        # Run critical tests first
        if critical_tests:
            for test in critical_tests:
                result = await self.run_specific_tests([test], target_path)
                if not result.success:
                    return {
                        "valid": False,
                        "reason": f"Critical test failed: {test}",
                        "details": result.to_dict(),
                    }

        # Run full suite
        result = await self.run_tests(target_path)

        return {
            "valid": result.success,
            "pass_rate": result.pass_rate,
            "details": result.to_dict(),
        }


class SandboxTestRunner(TestRunner):
    """Test runner that automatically manages sandbox lifecycle."""

    def __init__(
        self,
        repo_path: str,
        patch_applier,
        config: Optional[TestConfig] = None,
    ):
        super().__init__(repo_path, config)
        self.patch_applier = patch_applier
        self._sandbox: Optional[Path] = None

    async def run_with_patch(
        self,
        patch,
        test_filter: Optional[str] = None,
    ) -> TestResult:
        """
        Create sandbox, apply patch, run tests, cleanup.

        Args:
            patch: GeneratedPatch to test
            test_filter: Optional test filter

        Returns:
            TestResult from sandbox execution
        """
        # Create sandbox
        self._sandbox = await self.patch_applier.create_sandbox()

        try:
            # Apply patch
            result = await self.patch_applier.apply_patch(self._sandbox, patch)

            if not result.success:
                return TestResult(
                    test_suite="sandbox",
                    passed=0,
                    failed=0,
                    errors=1,
                    skipped=0,
                    duration=0,
                    output=f"Patch failed: {result.error}",
                    success=False,
                )

            # Run tests
            test_result = await self.run_tests(self._sandbox, test_filter)
            return test_result

        finally:
            # Cleanup
            if self._sandbox:
                await self.patch_applier.cleanup_sandbox(self._sandbox)
                self._sandbox = None
