"""
Permission manager — controls what actions agents can take.
"""

from enum import Enum
from typing import Set
from src.config.settings import get_settings


class Permission(Enum):
    READ_FILES = "read_files"
    WRITE_FILES = "write_files"
    EXECUTE_CODE = "execute_code"
    WEB_SEARCH = "web_search"
    SEND_REQUESTS = "send_requests"


class PermissionManager:
    """
    Enforces a whitelist of permissions for agent actions.
    Configured via settings; defaults to read-only + web search.
    """

    DEFAULT_GRANTS: Set[Permission] = {
        Permission.READ_FILES,
        Permission.WEB_SEARCH,
    }

    def __init__(self):
        self._grants: Set[Permission] = set(self.DEFAULT_GRANTS)

    def grant(self, permission: Permission) -> None:
        self._grants.add(permission)

    def revoke(self, permission: Permission) -> None:
        self._grants.discard(permission)

    def check_permission(self, action: str) -> bool:
        """Return True if the action is permitted."""
        try:
            perm = Permission(action)
            return perm in self._grants
        except ValueError:
            return False  # Unknown actions denied by default
