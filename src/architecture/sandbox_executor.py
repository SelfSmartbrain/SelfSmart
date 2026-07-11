from __future__ import annotations
import os
import asyncio
import time
from datetime import datetime, timezone
from typing import Dict, Any

from src.config.logging import get_logger
from src.architecture.architecture_sandbox import SandboxExecutionRequest, SandboxExecutionResult

logger = get_logger(__name__)

async def execute_candidate_in_sandbox(request: SandboxExecutionRequest, script_path: str = "candidate_architecture/main.py") -> SandboxExecutionResult:
    """
    Executes the candidate architecture code in a strictly isolated environment
    using subprocess and environment variable overrides.
    """
    logger.info(f"Starting sandbox execution for candidate {request.candidate_id}, run_id {request.run_id}")
    
    env = os.environ.copy()
    env["DB_SCHEMA"] = f"sandbox_{request.run_id}"
    env["REDIS_PREFIX"] = f"sandbox_{request.run_id}:"
    
    env.update(request.env_overrides)
    
    started_at = datetime.now(timezone.utc)
    start_time = time.time()
    
    try:
        process = await asyncio.create_subprocess_exec(
            "python", script_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env
        )
        
        try:
            stdout_bytes, stderr_bytes = await asyncio.wait_for(
                process.communicate(), 
                timeout=request.timeout_seconds
            )
            stdout = stdout_bytes.decode() if stdout_bytes else ""
            stderr = stderr_bytes.decode() if stderr_bytes else ""
            exit_code = process.returncode or 0
            status = "success" if exit_code == 0 else "failed"
            
        except asyncio.TimeoutError:
            process.kill()
            await process.wait()
            stdout = ""
            stderr = "Execution timed out"
            exit_code = -1
            status = "timeout"
            
    except Exception as e:
        logger.error(f"Sandbox execution failed to start: {e}")
        stdout = ""
        stderr = str(e)
        exit_code = -2
        status = "error"
        
    execution_time_ms = (time.time() - start_time) * 1000
    completed_at = datetime.now(timezone.utc)
    
    result = SandboxExecutionResult(
        run_id=request.run_id,
        candidate_id=request.candidate_id,
        status=status,
        stdout=stdout,
        stderr=stderr,
        exit_code=exit_code,
        execution_time_ms=execution_time_ms,
        started_at=started_at,
        completed_at=completed_at
    )
    
    logger.info(f"Sandbox execution completed with status {status}")
    return result
