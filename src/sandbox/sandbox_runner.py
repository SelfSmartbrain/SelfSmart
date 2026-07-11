from __future__ import annotations
import os
import subprocess
import resource
import asyncio
from pathlib import Path
from src.config.logging import get_logger

logger = get_logger(__name__)

class SandboxRunner:
    def __init__(self, timeout_seconds: int = 5, memory_limit_mb: int = 128) -> None:
        self.timeout_seconds = timeout_seconds
        self.memory_limit_bytes = memory_limit_mb * 1024 * 1024

    def _set_limits(self) -> None:
        """Set resource limits for the subprocess."""
        try:
            resource.setrlimit(resource.RLIMIT_AS, (self.memory_limit_bytes, self.memory_limit_bytes))
            resource.setrlimit(resource.RLIMIT_CPU, (self.timeout_seconds, self.timeout_seconds))
        except (ValueError, OSError) as e:
            logger.warning(f"Could not set resource limits: {e}")

    async def run_file(self, file_path: str | Path, cwd: str | Path | None = None) -> tuple[int, str, str]:
        """Executes a Python file securely using subprocess.run."""
        loop = asyncio.get_running_loop()
        
        def _run() -> tuple[int, str, str]:
            try:
                logger.info(f"Running file {file_path} in sandbox")
                result = subprocess.run(
                    ["python3", str(file_path)],
                    cwd=str(cwd) if cwd else None,
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    preexec_fn=self._set_limits
                )
                return result.returncode, result.stdout, result.stderr
            except subprocess.TimeoutExpired as e:
                logger.error(f"Execution timed out after {self.timeout_seconds} seconds")
                stdout = e.stdout.decode() if isinstance(e.stdout, bytes) else (e.stdout or "")
                return -1, stdout, f"TimeoutExpired: {e}"
            except Exception as e:
                logger.error(f"Execution failed: {e}")
                return -2, "", str(e)
                
        return await loop.run_in_executor(None, _run)
