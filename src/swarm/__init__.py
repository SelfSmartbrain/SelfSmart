"""Swarm Orchestration Module (Phase 8).

This module enables hierarchical swarm architecture for large-scale goal execution:
- Director Agents managing sub-Orchestrator Agents
- Parallel execution across 50+ agent instances
- Distributed task coordination and load balancing
"""

from __future__ import annotations

from src.swarm.director import DirectorAgent
from src.swarm.sub_orchestrator import SubOrchestrator
from src.swarm.swarm_coordinator import SwarmCoordinator
from src.swarm.task_distributor import TaskDistributor
from src.swarm.load_balancer import LoadBalancer

__all__ = [
    "DirectorAgent",
    "SubOrchestrator",
    "SwarmCoordinator",
    "TaskDistributor",
    "LoadBalancer",
]
