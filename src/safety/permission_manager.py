"""Permission grants used by safety-sensitive runtime components."""

from __future__ import annotations

from collections import defaultdict


class PermissionManager:
    def __init__(self) -> None:
        self._grants: dict[str, set[str]] = defaultdict(set)

    def check_permission(self, action: str, level: str = "basic") -> bool:
        return level in self._grants.get(action, set())

    def grant_permission(self, action: str, level: str = "basic") -> None:
        self._grants[action].add(level)
