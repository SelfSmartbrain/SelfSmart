"""
Self-Modification Loop - Connects patch generation to autonomous development.

This module implements the self-improvement cycle:
1. SelfDevelopment analyzes the codebase
2. Generates improvement plans
3. PatchGenerator creates code patches for the plans
4. Safety gates validate patches
5. Patches are applied in sandbox
6. Tests run to validate
7. If successful, patches are committed
8. If failed, rollback occurs
"""

from .self_modification_loop import SelfModificationLoop, ModificationConfig
from .patch_applier import PatchApplier, PatchResult
from .test_runner import TestRunner, TestResult
from .rollback_manager import RollbackManager

__all__ = [
    "SelfModificationLoop",
    "ModificationConfig",
    "PatchApplier",
    "PatchResult",
    "TestRunner",
    "TestResult",
    "RollbackManager",
]
