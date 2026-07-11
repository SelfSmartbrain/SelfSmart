from __future__ import annotations
import os
import shutil
import tempfile
import asyncio
from pathlib import Path
from src.config.logging import get_logger

logger = get_logger(__name__)

class SandboxManager:
    def __init__(self, base_dir: str | None = None) -> None:
        self.base_dir = base_dir
        self.current_sandbox: Path | None = None

    async def create_sandbox(self) -> str:
        """Create a temporary directory for sandbox execution."""
        loop = asyncio.get_running_loop()
        def _create() -> str:
            self.current_sandbox = Path(tempfile.mkdtemp(dir=self.base_dir, prefix="modelx_sandbox_"))
            logger.info(f"Created sandbox at {self.current_sandbox}")
            return str(self.current_sandbox)
        return await loop.run_in_executor(None, _create)

    async def teardown_sandbox(self) -> None:
        """Tear down the temporary directory."""
        loop = asyncio.get_running_loop()
        def _teardown() -> None:
            if self.current_sandbox and self.current_sandbox.exists():
                shutil.rmtree(self.current_sandbox)
                logger.info(f"Tore down sandbox at {self.current_sandbox}")
                self.current_sandbox = None
        await loop.run_in_executor(None, _teardown)
