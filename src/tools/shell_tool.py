"""
Sandboxed shell execution tool for the Autonomous Agent Platform.

Executes shell commands in a controlled environment with:
- Timeout enforcement
- Working directory isolation
- Command allowlist/blocklist
"""

from __future__ import annotations

import re
import shlex
import os
import subprocess
import signal
import asyncio
from typing import Any, ClassVar

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.tools.base import AgentTool, ToolExecutionError

logger = get_logger(__name__)

# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class ShellInput(BaseModel):
    """Input schema for ShellTool."""

    command: str = Field(
        ...,
        min_length=1,
        max_length=5000,
        description="Shell command to execute",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        le=300,
        description="Execution timeout in seconds",
    )
    cwd: str | None = Field(
        default=None,
        description="Working directory (relative to workspace)",
    )

# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

class ShellTool(AgentTool):
    """Execute shell commands in a sandboxed environment.

    All commands run with a timeout and optional working directory.
    Dangerous commands (rm -rf, sudo, etc.) can be blocked via config.

    Example usage::

        tool = ShellTool()
        result = await tool._arun(command="ls -la", timeout=10)
    """

    name: str = "shell"
    description: str = (
        "Execute a shell command with timeout. Returns stdout, stderr, and return code."
    )
    args_schema: type[BaseModel] = ShellInput
    max_retries: int = 0
    timeout_seconds: float = 60.0

    # Blocked dangerous commands, matched against shell tokens rather than raw substrings.
    _blocked_patterns: ClassVar[list[re.Pattern[str]]] = [
        re.compile(r"^sudo$", re.IGNORECASE),
        re.compile(r"^su$", re.IGNORECASE),
        re.compile(r"^chmod$", re.IGNORECASE),
        re.compile(r"^chown$", re.IGNORECASE),
        re.compile(r"^dd$", re.IGNORECASE),
        re.compile(r"^mkfs", re.IGNORECASE),
        re.compile(r"^fdisk$", re.IGNORECASE),
        re.compile(r"^mount$", re.IGNORECASE),
        re.compile(r"^umount$", re.IGNORECASE),
    ]
    _blocked_arg_combos: ClassVar[list[tuple[re.Pattern[str], re.Pattern[str]]]] = [
        (re.compile(r"^rm$", re.IGNORECASE), re.compile(r"-.*r.*f|--force|--recursive")),
    ]

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        """Execute a shell command with timeout."""
        command: str = kwargs["command"]
        timeout: int = kwargs.get("timeout", 30)
        cwd: str | None = kwargs.get("cwd")

        log = logger.bind(tool=self.name, command=command, timeout=timeout)

        try:
            tokens = shlex.split(command)
        except ValueError as exc:
            raise ToolExecutionError(
                tool_name=self.name,
                message="Invalid command syntax (unmatched quotes or escape characters)",
                cause=exc,
            ) from exc

        for token in tokens:
            for pattern in self._blocked_patterns:
                if pattern.match(token):
                    raise ToolExecutionError(
                        tool_name=self.name,
                        message=f"Blocked command: {token}",
                    )

        if len(tokens) >= 2:
            for cmd_pattern, arg_pattern in self._blocked_arg_combos:
                if cmd_pattern.match(tokens[0]) and any(
                    arg_pattern.match(arg) for arg in tokens[1:]
                ):
                    raise ToolExecutionError(
                        tool_name=self.name,
                        message=f"Blocked dangerous command: {command}",
                    )

        for token in tokens:
            if token.lower() in {"bash", "sh", "zsh"} and len(tokens) > 2 and tokens[1] == "-c":
                raise ToolExecutionError(
                    tool_name=self.name,
                    message=f"Blocked shell trampoline: {token} -c",
                )

        # Resolve working directory
        if cwd:
            work_dir = os.path.abspath(cwd)
        else:
            work_dir = os.getcwd()

        try:
            result = await asyncio.to_thread(
                subprocess.run,
                command,
                shell=True,
                cwd=work_dir,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "returncode": result.returncode,
                "success": result.returncode == 0,
            }

        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout} seconds",
                "returncode": 124,
                "success": False,
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "returncode": 1,
                "success": False,
            }
