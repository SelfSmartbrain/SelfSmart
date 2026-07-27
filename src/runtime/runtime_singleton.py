"""Global AgentRuntime singleton, initialized at application startup.

Use `init_runtime()` once inside the FastAPI `lifespan` context and
`get_runtime()` anywhere else.  Thread-safe via an asyncio.Lock so that
concurrent lifespan callbacks (e.g. during testing) cannot double-initialize.
"""

from __future__ import annotations

import asyncio
from typing import Optional

from src.cognitive_kernel.kernel import CognitiveKernel
from src.config.logging import get_logger
from src.memory.memory_fabric import MemoryFabric
from src.runtime.agent_runtime import AgentRuntime

logger = get_logger(__name__)

_runtime: Optional[AgentRuntime] = None
_init_lock: asyncio.Lock = asyncio.Lock()  # prevents double-init under concurrent startup


def get_runtime() -> AgentRuntime:
    """Return the global AgentRuntime instance.

    Raises RuntimeError if called before `init_runtime()`.
    """
    if _runtime is None:
        raise RuntimeError(
            "AgentRuntime not initialized. Call init_runtime() inside the FastAPI lifespan."
        )
    return _runtime


def is_initialized() -> bool:
    """Return True if the runtime singleton has been initialized."""
    return _runtime is not None


async def init_runtime() -> AgentRuntime:
    """Initialize the global AgentRuntime singleton (idempotent)."""
    global _runtime
    async with _init_lock:
        if _runtime is not None:
            logger.warning("init_runtime() called but runtime already initialized; skipping.")
            return _runtime

        memory_fabric = MemoryFabric()  # backends attached later via attach_consolidation()
        cognitive_kernel = CognitiveKernel(memory_fabric=memory_fabric)
        _runtime = AgentRuntime(cognitive_kernel=cognitive_kernel)
        await _runtime.initialize()
        logger.info("AgentRuntime initialized successfully")
        return _runtime


async def shutdown_runtime() -> None:
    """Gracefully shut down and clear the global AgentRuntime singleton."""
    global _runtime
    async with _init_lock:
        if _runtime is None:
            return
        try:
            await _runtime.shutdown()
        except Exception as exc:  # pragma: no cover
            logger.error("Error during AgentRuntime shutdown", error=str(exc))
        finally:
            _runtime = None
            logger.info("AgentRuntime shut down")
