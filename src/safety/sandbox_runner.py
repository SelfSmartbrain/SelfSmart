"""Minimal sandbox command gate.

This class intentionally does not execute shell commands directly. It gives
callers a stable place to route sandbox work once a real container runner is
configured.
"""

from __future__ import annotations

from typing import Any

from src.safety.action_validator import ActionValidator


class SandboxRunner:
    def __init__(self, action_validator: ActionValidator | None = None) -> None:
        self.action_validator = action_validator or ActionValidator()

    def run_in_sandbox(self, command: str) -> dict[str, Any]:
        validation = self.action_validator.validate_action(
            {"type": "shell_command", "command": command}
        )
        if not validation:
            return {"status": "rejected", "reason": validation.reason}
        return {"status": "pending", "command": command, "reason": "No sandbox backend configured"}
