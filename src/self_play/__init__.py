"""
Self-Play Package - Complete self-play system for autonomous improvement.

Components:
- CurriculumEngine: Adaptive problem progression
- SyntheticProblemGenerator: Realistic problem generation
- SandboxIntegration: Safe code execution and testing
- ExperienceRecorder: Learning experience capture
- SelfPlayManager: Main orchestration loop
"""

from .curriculum_engine import (
    CurriculumEngine,
    DifficultyLevel,
    SkillTag,
    ProblemDomain,
    ProblemSpec,
    ProblemAttempt,
    SkillProfile,
)

from .synthetic_problem_generator import (
    SyntheticProblemGenerator,
    ProblemType,
)

from .sandbox_integration import (
    SandboxTestRunner,
    SandboxConfig,
    TestCase,
    TestResult,
    SandboxExecutionResult,
    SandboxStatus,
    run_sandbox_test,
)

from .experience_recorder import (
    ExperienceRecorder,
    ExperienceType,
    ExperienceRecord,
    ExecutionTrace,
    TestResult as RecorderTestResult,
    TestSuiteResult,
)

from .self_play_manager import (
    SelfPlayManager,
    SelfPlayConfig,
    IterationResult,
)

__all__ = [
    # Curriculum
    "CurriculumEngine",
    "DifficultyLevel",
    "SkillTag",
    "ProblemDomain",
    "ProblemSpec",
    "ProblemAttempt",
    "SkillProfile",
    # Problem Generation
    "SyntheticProblemGenerator",
    "ProblemType",
    # Sandbox
    "SandboxTestRunner",
    "SandboxConfig",
    "TestCase",
    "TestResult",
    "SandboxExecutionResult",
    "SandboxStatus",
    "run_sandbox_test",
    # Experience
    "ExperienceRecorder",
    "ExperienceType",
    "ExperienceRecord",
    "ExecutionTrace",
    "TestResult",
    "TestSuiteResult",
    # Manager
    "SelfPlayManager",
    "SelfPlayConfig",
    "IterationResult",
]
