"""Safety checks for autonomous runtime actions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ValidationResult:
    allowed: bool
    reason: str = ""
    warnings: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return self.allowed


class ActionValidator:
    """Conservative validator for runtime-generated actions."""

    SAFE_ACTION_TYPES = {
        "observe",
        "think",
        "reflect",
        "plan",
        "research",
        "memory_consolidation",
        "execute_task",
    }
    BLOCKED_ACTION_TYPES = {
        "delete_file",
        "write_file",
        "network_request",
        "shell_command",
        "self_modify",
        "deploy",
    }
    BLOCKED_TERMS = ("rm -rf", "sudo", "chmod 777", "mkfs", ":(){")

    def validate_action(self, action: Any) -> ValidationResult:
        if action is None:
            return ValidationResult(False, "Action is empty")

        if isinstance(action, str):
            action_type = action
            payload = action
        elif isinstance(action, dict):
            action_type = str(action.get("type") or action.get("action") or "")
            payload = str(action)
        else:
            action_type = getattr(action, "type", action.__class__.__name__)
            payload = str(action)

        normalized_type = action_type.lower()
        normalized_payload = payload.lower()

        if normalized_type in self.BLOCKED_ACTION_TYPES:
            return ValidationResult(False, f"Action type '{normalized_type}' requires explicit approval")

        if any(term in normalized_payload for term in self.BLOCKED_TERMS):
            return ValidationResult(False, "Action contains a blocked operation")

        if normalized_type and normalized_type not in self.SAFE_ACTION_TYPES:
            return ValidationResult(
                True,
                "Action allowed with caution",
                [f"Unknown action type '{normalized_type}'"],
            )

        return ValidationResult(True, "Action allowed")
