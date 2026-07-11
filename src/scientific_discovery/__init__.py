"""Scientific Discovery Loop - Phase 14I

This module integrates World Model, Theory Engine, Experiment Engine,
and Belief Engine into a continuous scientific discovery loop.
"""

from .discovery_loop import DiscoveryLoop, DiscoveryPhase
from .experiment_orchestrator import ExperimentOrchestrator

__all__ = [
    "DiscoveryLoop",
    "DiscoveryPhase",
    "ExperimentOrchestrator",
]
