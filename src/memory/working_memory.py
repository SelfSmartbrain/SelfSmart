'''working_memory.py

Implements a lightweight in‑memory store for the current task context and short‑term goals.

The store is a simple dictionary with time‑based eviction. It is used by the
Reasoning Engine to keep the most recent observations and intermediate
variables.
''' 

import time
from typing import Any, Dict

class WorkingMemory:
    """Transient, volatile memory for the current execution step.

    The memory automatically discards entries older than ``ttl`` seconds.
    """

    def __init__(self, ttl: int = 300):
        self.ttl = ttl
        self._store: Dict[str, Dict[str, Any]] = {}

    def set(self, key: str, value: Any) -> None:
        """Store ``value`` under ``key`` with the current timestamp."""
        self._store[key] = {"value": value, "ts": time.time()}

    def get(self, key: str, default: Any = None) -> Any:
        """Retrieve ``value`` for ``key`` if it hasn't expired."""
        entry = self._store.get(key)
        if not entry:
            return default
        if time.time() - entry["ts"] > self.ttl:
            del self._store[key]
            return default
        return entry["value"]

    def clear(self) -> None:
        """Remove all entries."""
        self._store.clear()

    def __repr__(self) -> str:
        return f"WorkingMemory(ttl={self.ttl}, entries={list(self._store.keys())})"
