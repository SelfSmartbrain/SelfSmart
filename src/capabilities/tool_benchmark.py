from __future__ import annotations
import time
import asyncio
from pathlib import Path
from pydantic import BaseModel
from src.config.logging import get_logger
from src.sandbox.sandbox_manager import SandboxManager
from src.sandbox.sandbox_runner import SandboxRunner

logger = get_logger(__name__)

class ToolBenchmark(BaseModel):
    model_config = {"from_attributes": True}
    runs: int
    success_rate: float
    average_latency_seconds: float
    average_memory_mb: float

class ToolBenchmarkRunner:
    def __init__(self, runs: int = 5) -> None:
        self.runs = runs

    async def run_benchmark(self, tool_code: str, test_code: str) -> ToolBenchmark:
        """
        Runs the tool multiple times in the sandbox to measure average latency, memory,
        and success rate, storing results in ToolBenchmark.
        """
        logger.info(f"Running tool benchmark for {self.runs} runs")
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
            
            success_count = 0
            total_time = 0.0
            
            for _ in range(self.runs):
                start_time = time.time()
                return_code, _, _ = await runner.run_file(test_path, cwd=sandbox_dir)
                elapsed = time.time() - start_time
                
                total_time += elapsed
                if return_code == 0:
                    success_count += 1
                    
            success_rate = success_count / self.runs if self.runs > 0 else 0.0
            avg_latency = total_time / self.runs if self.runs > 0 else 0.0
            
            return ToolBenchmark(
                runs=self.runs,
                success_rate=success_rate,
                average_latency_seconds=avg_latency,
                average_memory_mb=0.0  # Memory measurement placeholder
            )
        finally:
            await manager.teardown_sandbox()
