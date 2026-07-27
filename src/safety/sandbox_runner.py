"""Sandbox runner — executes code in an isolated subprocess."""

import asyncio
import os
import sys
from typing import Dict, Any


class SandboxRunner:
    """Executes untrusted Python code in an isolated subprocess with limits."""

    def __init__(self, timeout_seconds: int = 5, max_memory_mb: int = 128):
        self.timeout_seconds = timeout_seconds
        self.max_memory_bytes = max_memory_mb * 1024 * 1024

    async def run(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Execute code in a sandboxed environment.

        Args:
            code: The source code to execute
            language: Programming language (only 'python' supported)

        Returns:
            Dictionary with execution results including status, stdout, stderr, etc.
        """
        if language != "python":
            return {
                "status": "error",
                "error": f"Language '{language}' not supported. Only 'python' is available.",
            }

        # Prepare the code with safety wrappers
        safe_code = f"""
import sys
import resource

# Set memory limit
soft, hard = resource.getrlimit(resource.RLIMIT_AS)
resource.setrlimit(resource.RLIMIT_AS, ({self.max_memory_bytes}, hard))

# Execute user code
{code}
"""

        try:
            # Create subprocess with limited resources
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-c",
                safe_code,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                stdin=asyncio.subprocess.DEVNULL,
                # Set process group for clean termination
                preexec_fn=os.setsid if hasattr(os, "setsid") else None,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(), timeout=self.timeout_seconds
                )

                return {
                    "status": "completed" if process.returncode == 0 else "error",
                    "returncode": process.returncode,
                    "stdout": stdout.decode("utf-8", errors="replace")[:2000],
                    "stderr": stderr.decode("utf-8", errors="replace")[:500],
                    "execution_time": None,  # Could be measured if needed
                }
            except asyncio.TimeoutError:
                # Kill the process group if timeout
                try:
                    if hasattr(os, "killpg"):
                        os.killpg(os.getpgid(process.pid), 9)
                    else:
                        process.terminate()
                    await process.wait()
                except ProcessLookupError:
                    pass  # Process already terminated

                return {
                    "status": "timeout",
                    "error": f"Execution exceeded {self.timeout_seconds} second limit",
                    "stdout": "",
                    "stderr": "",
                }

        except Exception as e:
            return {
                "status": "error",
                "error": f"Failed to execute code: {str(e)}",
                "stdout": "",
                "stderr": "",
            }


# For backward compatibility with existing code that might instantiate without args
def create_sandbox_runner(**kwargs):
    """Factory function for creating SandboxRunner instances."""
    return SandboxRunner(**kwargs)
