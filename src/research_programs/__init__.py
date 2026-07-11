"""
Persistent Research Programs - Phase 13

Persistent Research Programs provide:
- Long-running research programs
- Autonomous research execution
- Program scheduling and management
- Research memory and knowledge accumulation
"""

from .research_program import ResearchProgram
from .program_scheduler import ProgramScheduler
from .program_memory import ProgramMemory

__all__ = [
    "ResearchProgram",
    "ProgramScheduler",
    "ProgramMemory",
]
