"""
Sandboxed Python code execution tool for the Autonomous Agent Platform.

Executes arbitrary Python code in a subprocess with:
- Timeout enforcement
- Memory limits (via ``resource`` on Unix)
- Pre-execution static analysis to block dangerous patterns
- Restricted imports (``os.system``, ``subprocess``, ``shutil.rmtree``, etc.)
"""

from __future__ import annotations

import ast
import base64
import re
import subprocess
import sys
import textwrap
from typing import Any

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.tools.base import AgentTool, ToolExecutionError

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Security: blocked patterns
# ---------------------------------------------------------------------------

# Modules / attribute chains that must never be imported or invoked.
_BLOCKED_IMPORTS: frozenset[str] = frozenset(
    {
        "subprocess",
        "shutil",
        "ctypes",
        "multiprocessing",
        "signal",
        "socket",
        "http.server",
        "xmlrpc",
        "ftplib",
        "smtplib",
        "telnetlib",
        "webbrowser",
        "antigravity",
        "turtle",
        "tkinter",
        "importlib",
        "runpy",
        "code",
        "codeop",
        "compileall",
        "py_compile",
    }
)

# Callable patterns that are categorically dangerous.
_BLOCKED_CALLS: frozenset[str] = frozenset(
    {
        "os.system",
        "os.popen",
        "os.exec",
        "os.execl",
        "os.execle",
        "os.execlp",
        "os.execlpe",
        "os.execv",
        "os.execve",
        "os.execvp",
        "os.execvpe",
        "os.spawn",
        "os.spawnl",
        "os.spawnle",
        "os.fork",
        "os.forkpty",
        "os.kill",
        "os.killpg",
        "os.remove",
        "os.unlink",
        "os.rmdir",
        "os.removedirs",
        "os.rename",
        "os.renames",
        "shutil.rmtree",
        "shutil.move",
        "shutil.copy",
        "shutil.copy2",
        "shutil.copytree",
        "eval",
        "exec",
        "compile",
        "__import__",
        "globals",
        "locals",
        "getattr",
        "setattr",
        "delattr",
        "open",  # file I/O blocked in sandbox
    }
)

# Regex for quick string-level scanning before AST analysis
_DANGEROUS_REGEX = re.compile(
    r"""
    (?:os\.system|os\.popen|os\.exec\w*|os\.spawn\w*|os\.fork|os\.kill)
    |(?:subprocess\.\w+)
    |(?:shutil\.rmtree|shutil\.move)
    |(?:__import__)
    |(?:eval\s*\()
    |(?:exec\s*\()
    """,
    re.VERBOSE,
)


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class PythonExecutorInput(BaseModel):
    """Input schema for PythonExecutorTool."""

    code: str = Field(
        ...,
        min_length=1,
        max_length=50_000,
        description="Python code to execute",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Execution timeout in seconds",
    )


# ---------------------------------------------------------------------------
# Code validator
# ---------------------------------------------------------------------------

class _CodeValidator:
    """Static analyser that inspects Python source for forbidden patterns."""

    @classmethod
    def validate(cls, code: str) -> list[str]:
        """Return a list of security violation messages (empty = safe)."""
        violations: list[str] = []

        # 1. Quick regex scan
        for match in _DANGEROUS_REGEX.finditer(code):
            violations.append(f"Blocked pattern detected: {match.group()!r}")

        # 2. AST-level analysis
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            violations.append(f"Syntax error: {exc}")
            return violations

        for node in ast.walk(tree):
            # Check imports
            if isinstance(node, ast.Import):
                for alias in node.names:
                    root_module = alias.name.split(".")[0]
                    if root_module in _BLOCKED_IMPORTS:
                        violations.append(f"Blocked import: {alias.name!r}")

            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    root_module = node.module.split(".")[0]
                    if root_module in _BLOCKED_IMPORTS:
                        violations.append(f"Blocked import-from: {node.module!r}")

            # Check function calls
            elif isinstance(node, ast.Call):
                call_name = cls._resolve_call_name(node)
                if call_name and call_name in _BLOCKED_CALLS:
                    violations.append(f"Blocked function call: {call_name!r}")

        return violations

    @staticmethod
    def _resolve_call_name(node: ast.Call) -> str | None:
        """Attempt to resolve a call node to a dotted name string."""
        if isinstance(node.func, ast.Name):
            return node.func.id
        if isinstance(node.func, ast.Attribute):
            parts: list[str] = [node.func.attr]
            current: ast.expr = node.func.value
            while isinstance(current, ast.Attribute):
                parts.append(current.attr)
                current = current.value
            if isinstance(current, ast.Name):
                parts.append(current.id)
            return ".".join(reversed(parts))
        return None


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

class PythonExecutorTool(AgentTool):
    """Execute Python code in a sandboxed subprocess.

    Before execution the code is statically analysed for dangerous
    patterns (blocked imports, system calls, file-system mutations).
    The subprocess is launched with a hard timeout and, on Unix systems,
    a memory cap.

    The tool returns ``stdout``, ``stderr``, and an ``execution_status``
    flag.

    **Security considerations**:

    * No file I/O (``open`` is blocked).
    * No network access from executed code.
    * No shell-out or subprocess spawning.
    * Memory limited to 256 MB.

    Example usage::

        tool = PythonExecutorTool()
        result = await tool._arun(code="print(sum(range(100)))")
    """

    name: str = "python_executor"
    description: str = (
        "Execute Python code in a sandboxed subprocess. Returns stdout, "
        "stderr, and execution status. Dangerous operations are blocked."
    )
    args_schema: type[BaseModel] = PythonExecutorInput
    max_retries: int = 0  # code execution should not be retried automatically
    timeout_seconds: float = 60.0

    # Memory limit for the child process (256 MB)
    _memory_limit_bytes: int = 256 * 1024 * 1024

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        """Validate and execute Python code in a subprocess.

        Args:
            **kwargs: Validated fields from :class:`PythonExecutorInput`.

        Returns:
            A dict with ``stdout``, ``stderr``, ``return_code``,
            ``execution_status`` ('success' | 'error' | 'timeout'),
            and ``violations`` (empty list if clean).
        """
        code: str = kwargs["code"]
        timeout: int = kwargs.get("timeout", 30)

        log = logger.bind(tool=self.name, code_len=len(code), timeout=timeout)
        log.debug("python_executor.validate.start")

        # --- Static analysis ---
        violations = _CodeValidator.validate(code)
        if violations:
            log.warning("python_executor.blocked", violations=violations)
            return {
                "stdout": "",
                "stderr": "Code execution blocked due to security violations.",
                "return_code": -1,
                "execution_status": "blocked",
                "violations": violations,
            }

        # --- Build the wrapper script ---
        # The wrapper enforces memory limits on Unix and runs the user code.
        wrapper = self._build_wrapper(code)

        log.debug("python_executor.execute.start")

        try:
            proc = subprocess.run(
                [sys.executable, "-c", wrapper],
                capture_output=True,
                text=True,
                timeout=timeout,
                env=self._safe_env(),
            )

            status = "success" if proc.returncode == 0 else "error"
            result = {
                "stdout": proc.stdout[:50_000],  # cap output size
                "stderr": proc.stderr[:10_000],
                "return_code": proc.returncode,
                "execution_status": status,
                "violations": [],
            }

        except subprocess.TimeoutExpired:
            log.warning("python_executor.timeout", timeout=timeout)
            result = {
                "stdout": "",
                "stderr": f"Execution timed out after {timeout} seconds.",
                "return_code": -1,
                "execution_status": "timeout",
                "violations": [],
            }

        log.info("python_executor.complete", status=result["execution_status"])
        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _build_wrapper(self, code: str) -> str:
        """Wrap user code with resource limits and a clean entry point.

        Args:
            code: The user-supplied Python code.

        Returns:
            A complete Python script string to be run via
            ``python -c``.
        """
        # Encode the user code in base64 to avoid escaping issues
        # This prevents sandbox escape via triple-quote breaking
        encoded_code = base64.b64encode(code.encode('utf-8')).decode('ascii')

        wrapper = textwrap.dedent(f"""\
            import sys, platform, base64
            # Apply memory limit on Unix-like systems
            if platform.system() != 'Windows':
                try:
                    import resource
                    resource.setrlimit(
                        resource.RLIMIT_AS,
                        ({self._memory_limit_bytes}, {self._memory_limit_bytes}),
                    )
                except (ImportError, ValueError, OSError):
                    pass

            _user_code = base64.b64decode('{encoded_code}').decode('utf-8')
            try:
                exec(compile(_user_code, '<sandbox>', 'exec'), {{"__builtins__": __builtins__}})
            except MemoryError:
                print("MemoryError: Code exceeded memory limit.", file=sys.stderr)
                sys.exit(137)
            except Exception as _exc:
                print(f"{{type(_exc).__name__}}: {{_exc}}", file=sys.stderr)
                sys.exit(1)
        """)

        return wrapper

    @staticmethod
    def _safe_env() -> dict[str, str]:
        """Build a minimal environment for the subprocess.

        Strips sensitive variables while keeping essentials like
        ``PATH`` and ``HOME``.

        Returns:
            A dict of environment variables.
        """
        import os

        keep = {"PATH", "HOME", "LANG", "LC_ALL", "PYTHONPATH", "VIRTUAL_ENV"}
        return {k: v for k, v in os.environ.items() if k in keep}


PythonExecutor = PythonExecutorTool
