"""
Sandbox Integration - Safe code execution and testing for self-play.

Provides isolated execution environment with resource limits,
test running capabilities, and detailed result tracking.
"""

import asyncio
import json
import logging
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class SandboxStatus(Enum):
    """Execution status."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"
    MEMORY_LIMIT = "memory_limit"
    ERROR = "error"


@dataclass
class SandboxConfig:
    """Sandbox configuration."""
    timeout_seconds: float = 30.0
    memory_limit_mb: int = 256
    cpu_limit_percent: int = 100
    network_allowed: bool = False
    filesystem_read_only: bool = True
    allowed_imports: List[str] = field(default_factory=lambda: [
        "math", "random", "datetime", "json", "collections",
        "itertools", "functools", "typing", "dataclasses",
    ])
    blocked_imports: List[str] = field(default_factory=lambda: [
        "os", "sys", "subprocess", "socket", "threading",
        "multiprocessing", "importlib", "ctypes", "pickle",
    ])


@dataclass
class TestCase:
    """A single test case."""
    test_id: str
    name: str
    input_data: Any
    expected_output: Any
    description: str = ""
    timeout_seconds: float = 5.0
    points: float = 1.0
    hidden: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class TestResult:
    """Result of a single test."""
    test_id: str
    name: str
    passed: bool
    input_data: Any
    expected_output: Any
    actual_output: Any
    duration_ms: float
    error_message: Optional[str] = None
    points_earned: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SandboxExecutionResult:
    """Result of sandbox execution."""
    execution_id: str
    status: SandboxStatus
    stdout: str = ""
    stderr: str = ""
    return_code: int = 0
    execution_time_ms: float = 0.0
    memory_used_mb: float = 0.0
    error: Optional[str] = None
    test_results: List[TestResult] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class SandboxTestRunner:
    """
    Runs code in isolated sandbox with test cases.
    
    Features:
    - Resource limits (time, memory, CPU)
    - Import restrictions
    - Test case execution
    - Detailed result tracking
    """
    
    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()
        self._execution_count = 0
    
    async def run_code(
        self,
        code: str,
        test_cases: Optional[List[TestCase]] = None,
        stdin: str = "",
    ) -> SandboxExecutionResult:
        """
        Execute code in sandbox with optional test cases.
        
        Args:
            code: Python code to execute
            test_cases: Optional test cases to run
            stdin: Standard input
            
        Returns:
            SandboxExecutionResult with execution details and test results
        """
        execution_id = f"exec_{uuid.uuid4().hex[:8]}"
        start_time = time.time()
        
        logger.debug(f"Executing {execution_id} with {len(test_cases or [])} tests")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
            f.write(code)
            code_file = f.name
        
        try:
            # Prepare test runner code
            if test_cases:
                runner_code = self._build_test_runner(code, test_cases, stdin)
            else:
                runner_code = self._build_simple_runner(code, stdin)
            
            # Write runner
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(runner_code)
                runner_file = f.name
            
            # Execute with resource limits
            result = await self._execute_with_limits(
                execution_id,
                runner_file,
                start_time,
            )
            
            # Parse test results if available
            if test_cases:
                result.test_results = self._parse_test_results(result.stdout, test_cases)
            
            return result
            
        finally:
            # Cleanup
            try:
                Path(code_file).unlink()
                Path(runner_file).unlink()
            except Exception:
                pass
    
    def _build_test_runner(
        self,
        user_code: str,
        test_cases: List[TestCase],
        stdin: str,
    ) -> str:
        """Build test runner that executes user code against test cases."""
        test_json = []
        for tc in test_cases:
            test_json.append({
                "test_id": tc.test_id,
                "name": tc.name,
                "input": tc.input_data,
                "expected": tc.expected_output,
                "timeout": tc.timeout_seconds,
            })
        
        return f'''
import json
import sys
import time
import traceback

# User code
{user_code}

# Test runner
def run_tests():
    test_cases = {json.dumps(test_json)}
    results = []
    
    for tc in test_cases:
        test_start = time.time()
        try:
            # Call user's solve function
            # Assume user defines solve(input) function
            if "solve" in globals():
                result = solve(tc["input"])
            elif "main" in globals():
                result = main(tc["input"])
            else:
                # Try to execute as script
                result = None
            
            # Compare result
            expected = tc["expected"]
            passed = result == expected
            
            results.append({{
                "test_id": tc["test_id"],
                "name": tc["name"],
                "passed": passed,
                "input": tc["input"],
                "expected": expected,
                "actual": result,
                "duration_ms": (time.time() - test_start) * 1000,
                "error": None,
            }})
            
        except Exception as e:
            results.append({{
                "test_id": tc["test_id"],
                "name": tc["name"],
                "passed": False,
                "input": tc["input"],
                "expected": tc["expected"],
                "actual": None,
                "duration_ms": (time.time() - test_start) * 1000,
                "error": str(e),
            }})
    
    # Output results as JSON
    print("__TEST_RESULTS__")
    print(json.dumps(results))

if __name__ == "__main__":
    run_tests()
'''
    
    def _build_simple_runner(self, code: str, stdin: str) -> str:
        """Build simple runner without tests."""
        return f'''
import sys
import io

# Redirect stdin
sys.stdin = io.StringIO({json.dumps(stdin)})

# User code
{code}
'''
    
    async def _execute_with_limits(
        self,
        execution_id: str,
        runner_file: str,
        start_time: float,
    ) -> SandboxExecutionResult:
        """Execute with resource limits."""
        
        # Build command with limits
        cmd = [
            "timeout", str(self.config.timeout_seconds),
            "python3", runner_file,
        ]
        
        try:
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                limit=1024 * 1024,  # 1MB output limit
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=self.config.timeout_seconds + 5,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                return SandboxExecutionResult(
                    execution_id=execution_id,
                    status=SandboxStatus.TIMEOUT,
                    error=f"Execution timed out after {self.config.timeout_seconds}s",
                    execution_time_ms=(time.time() - start_time) * 1000,
                )
            
            execution_time = (time.time() - start_time) * 1000
            
            return SandboxExecutionResult(
                execution_id=execution_id,
                status=SandboxStatus.COMPLETED if proc.returncode == 0 else SandboxStatus.FAILED,
                stdout=stdout.decode('utf-8', errors='replace'),
                stderr=stderr.decode('utf-8', errors='replace'),
                return_code=proc.returncode,
                execution_time_ms=execution_time,
            )
            
        except Exception as e:
            return SandboxExecutionResult(
                execution_id=execution_id,
                status=SandboxStatus.ERROR,
                error=str(e),
                execution_time_ms=(time.time() - start_time) * 1000,
            )
    
    def _parse_test_results(self, stdout: str, test_cases: List[TestCase]) -> List[TestResult]:
        """Parse test results from stdout."""
        results = []
        
        # Find JSON output
        marker = "__TEST_RESULTS__"
        if marker in stdout:
            json_part = stdout.split(marker)[-1].strip()
            try:
                test_data = json.loads(json_part)
                for td in test_data:
                    # Find matching test case
                    tc = next((t for t in test_cases if t.test_id == td["test_id"]), None)
                    
                    results.append(TestResult(
                        test_id=td["test_id"],
                        name=td["name"],
                        passed=td["passed"],
                        input_data=td["input"],
                        expected_output=td["expected"],
                        actual_output=td["actual"],
                        duration_ms=td["duration_ms"],
                        error_message=td["error"],
                        points_earned=tc.points if tc and td["passed"] else 0.0,
                    ))
            except json.JSONDecodeError:
                logger.warning("Failed to parse test results JSON")
        
        return results


# Convenience function
async def run_sandbox_test(
    code: str,
    test_cases: List[TestCase],
    config: Optional[SandboxConfig] = None,
) -> SandboxExecutionResult:
    """Quick function to run sandbox test."""
    runner = SandboxTestRunner(config)
    return await runner.run_code(code, test_cases)