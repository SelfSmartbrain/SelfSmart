"""
Safety Module - Enhanced safety with static analysis for self-modified code.

This module provides:
- SelfPatchSafetyGate: Sandbox testing and CI integration for patches
- StaticAnalyzer: Static code analysis for security and correctness
- SafetyHypervisor: Continuous monitoring of self-modification
"""

from .self_patch_safety_gate import (
    SelfPatchSafetyGate,
    PatchSafetyLevel,
    TestResult,
    PatchSafetyCheck,
    PatchTestResult,
    PatchApplicationResult,
)
from .static_analyzer import (
    StaticAnalyzer,
    AnalysisConfig,
    AnalysisResult,
    Finding,
    Severity,
    FindingType,
)
from .safety_hypervisor import (
    SafetyHypervisor,
    SafetyEvent,
    SafetyPolicy,
    MonitoringConfig,
)

__all__ = [
    # Self-patch safety
    "SelfPatchSafetyGate",
    "PatchSafetyLevel",
    "TestResult",
    "PatchSafetyCheck",
    "PatchTestResult",
    "PatchApplicationResult",
    
    # Static analysis
    "StaticAnalyzer",
    "AnalysisConfig",
    "AnalysisResult",
    "Finding",
    "Severity",
    "FindingType",
    
    # Safety hypervisor
    "SafetyHypervisor",
    "SafetyEvent",
    "SafetyPolicy",
    "MonitoringConfig",
]