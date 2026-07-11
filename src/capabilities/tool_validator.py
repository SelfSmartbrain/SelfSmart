from __future__ import annotations
import os
import asyncio
from pathlib import Path
from pydantic import BaseModel
from src.config.logging import get_logger
from src.sandbox.sandbox_manager import SandboxManager
from src.sandbox.sandbox_runner import SandboxRunner
from src.capabilities.static_validator import StaticValidator

logger = get_logger(__name__)

class ToolValidationResult(BaseModel):
    model_config = {"from_attributes": True}
    is_valid: bool
    static_analysis_message: str
    return_code: int | None = None
    stdout: str | None = None
    stderr: str | None = None

class ToolValidator:
    def __init__(self) -> None:
        self.static_validator = StaticValidator()

    async def validate_tool(self, tool_code: str, test_code: str) -> ToolValidationResult:
        """
        Orchestrates writing the tool and tests to the sandbox, running static validator,
        running tests, and returning success/failure.
        """
        logger.info("Starting tool validation")
        is_valid, msg = await self.static_validator.validate_code(tool_code)
        if not is_valid:
            return ToolValidationResult(
                is_valid=False,
                static_analysis_message=msg
            )
            
        is_valid, msg = await self.static_validator.validate_code(test_code)
        if not is_valid:
            return ToolValidationResult(
                is_valid=False,
                static_analysis_message=f"Test code static analysis failed: {msg}"
            )

        manager = SandboxManager()
        sandbox_dir = await manager.create_sandbox()
        try:
            tool_path = Path(sandbox_dir) / "tool.py"
            test_path = Path(sandbox_dir) / "test_tool.py"
            
            loop = asyncio.get_running_loop()
            
            def _write_files() -> None:
                with open(tool_path, "w") as f:
                    f.write(tool_code)
                    
                test_content = f"import tool\n\n{test_code}"
                with open(test_path, "w") as f:
                    f.write(test_content)
                    
            await loop.run_in_executor(None, _write_files)
                
            runner = SandboxRunner()
            return_code, stdout, stderr = await runner.run_file(test_path, cwd=sandbox_dir)
            
            success = return_code == 0
            return ToolValidationResult(
                is_valid=success,
                static_analysis_message="Static validation passed.",
                return_code=return_code,
                stdout=stdout,
                stderr=stderr
            )
        finally:
            await manager.teardown_sandbox()
