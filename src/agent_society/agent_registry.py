"""
Agent Registry - Manages agent registration and capabilities

The AgentRegistry is responsible for:
- Agent registration and discovery
- Capability tracking
- Reputation management
- Agent lifecycle management
"""

import asyncio
import logging
from collections import defaultdict
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class AgentStatus(Enum):
    """Status of an agent"""

    ACTIVE = "active"
    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    DECOMMISSIONED = "decommissioned"


@dataclass
class AgentCapability:
    """An agent capability"""

    name: str
    proficiency: float  # 0.0 to 1.0
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentInfo:
    """Information about an agent"""

    agent_id: str
    name: str
    agent_type: str
    status: AgentStatus = AgentStatus.IDLE
    capabilities: List[AgentCapability] = field(default_factory=list)
    reputation: float = 0.5  # 0.0 to 1.0
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    last_active: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)

    def has_capability(self, capability_name: str) -> bool:
        """Check if agent has a capability"""
        return any(cap.name == capability_name for cap in self.capabilities)

    def get_proficiency(self, capability_name: str) -> float:
        """Get proficiency for a capability"""
        for cap in self.capabilities:
            if cap.name == capability_name:
                return cap.proficiency
        return 0.0


class AgentRegistry:
    """
    Registry for agent management.

    Provides:
    - Agent registration and discovery
    - Capability tracking
    - Reputation management
    - Agent lifecycle management
    """

    def __init__(self):
        self._agents: Dict[str, AgentInfo] = {}
        self._capability_index: Dict[str, Set[str]] = defaultdict(set)

        # Reputation history
        self._reputation_history: Dict[str, List[float]] = defaultdict(list)

        # Statistics
        self._agents_registered = 0
        self._agents_decommissioned = 0

    async def initialize(self) -> None:
        """Initialize the agent registry"""
        logger.info("AgentRegistry initialized")

    async def register_agent(
        self,
        agent_id: str,
        name: str,
        agent_type: str,
        capabilities: Optional[List[Dict[str, Any]]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> AgentInfo:
        """
        Register a new agent.

        Args:
            agent_id: Agent identifier
            name: Agent name
            agent_type: Type of agent
            capabilities: List of capability dictionaries
            metadata: Additional metadata

        Returns:
            Agent information
        """
        # Convert capability dicts to AgentCapability objects
        capability_objects = []
        if capabilities:
            for cap_dict in capabilities:
                capability_objects.append(
                    AgentCapability(
                        name=cap_dict["name"],
                        proficiency=cap_dict.get("proficiency", 0.5),
                        description=cap_dict.get("description", ""),
                        metadata=cap_dict.get("metadata", {}),
                    )
                )

        agent = AgentInfo(
            agent_id=agent_id,
            name=name,
            agent_type=agent_type,
            capabilities=capability_objects,
            metadata=metadata or {},
        )

        self._agents[agent_id] = agent

        # Index capabilities
        for cap in capability_objects:
            self._capability_index[cap.name].add(agent_id)

        self._agents_registered += 1

        logger.info(f"Registered agent {agent_id}: {name} ({agent_type})")
        return agent

    async def decommission_agent(self, agent_id: str) -> bool:
        """
        Decommission an agent.

        Args:
            agent_id: Agent identifier

        Returns:
            True if decommissioned successfully
        """
        if agent_id not in self._agents:
            logger.warning(f"Agent {agent_id} not found")
            return False

        agent = self._agents[agent_id]
        agent.status = AgentStatus.DECOMMISSIONED

        # Remove from capability index
        for cap in agent.capabilities:
            self._capability_index[cap.name].discard(agent_id)

        self._agents_decommissioned += 1

        logger.info(f"Decommissioned agent {agent_id}")
        return True

    async def update_status(
        self,
        agent_id: str,
        status: AgentStatus,
    ) -> bool:
        """
        Update agent status.

        Args:
            agent_id: Agent identifier
            status: New status

        Returns:
            True if updated successfully
        """
        if agent_id not in self._agents:
            logger.warning(f"Agent {agent_id} not found")
            return False

        agent = self._agents[agent_id]
        agent.status = status
        agent.last_active = datetime.now().timestamp()

        logger.debug(f"Updated agent {agent_id} status to {status.value}")
        return True

    async def update_reputation(
        self,
        agent_id: str,
        delta: float,
    ) -> bool:
        """
        Update agent reputation.

        Args:
            agent_id: Agent identifier
            delta: Reputation change (-1.0 to 1.0)

        Returns:
            True if updated successfully
        """
        if agent_id not in self._agents:
            logger.warning(f"Agent {agent_id} not found")
            return False

        agent = self._agents[agent_id]

        # Update reputation with bounds
        agent.reputation = max(0.0, min(1.0, agent.reputation + delta))

        # Record history
        self._reputation_history[agent_id].append(agent.reputation)

        logger.debug(f"Updated agent {agent_id} reputation to {agent.reputation:.2f}")
        return True

    async def add_capability(
        self,
        agent_id: str,
        capability_name: str,
        proficiency: float = 0.5,
        description: str = "",
    ) -> bool:
        """
        Add a capability to an agent.

        Args:
            agent_id: Agent identifier
            capability_name: Name of capability
            proficiency: Proficiency level
            description: Capability description

        Returns:
            True if added successfully
        """
        if agent_id not in self._agents:
            logger.warning(f"Agent {agent_id} not found")
            return False

        agent = self._agents[agent_id]

        # Check if capability already exists
        if agent.has_capability(capability_name):
            # Update proficiency instead
            for cap in agent.capabilities:
                if cap.name == capability_name:
                    cap.proficiency = proficiency
                    break
        else:
            # Add new capability
            capability = AgentCapability(
                name=capability_name,
                proficiency=proficiency,
                description=description,
            )
            agent.capabilities.append(capability)
            self._capability_index[capability_name].add(agent_id)

        logger.debug(f"Added capability {capability_name} to agent {agent_id}")
        return True

    def get_agent(self, agent_id: str) -> Optional[AgentInfo]:
        """Get agent information"""
        return self._agents.get(agent_id)

    def find_agents_by_capability(
        self,
        capability_name: str,
        min_proficiency: float = 0.0,
        status: Optional[AgentStatus] = None,
    ) -> List[AgentInfo]:
        """
        Find agents with a specific capability.

        Args:
            capability_name: Capability to search for
            min_proficiency: Minimum proficiency required
            status: Filter by status (optional)

        Returns:
            List of matching agents
        """
        agent_ids = self._capability_index.get(capability_name, set())

        agents = []
        for agent_id in agent_ids:
            agent = self._agents.get(agent_id)
            if agent and agent.status != AgentStatus.DECOMMISSIONED:
                if agent.get_proficiency(capability_name) >= min_proficiency:
                    if status is None or agent.status == status:
                        agents.append(agent)

        # Sort by proficiency and reputation
        agents.sort(
            key=lambda a: (a.get_proficiency(capability_name), a.reputation),
            reverse=True,
        )

        return agents

    def find_agents_by_type(
        self,
        agent_type: str,
        status: Optional[AgentStatus] = None,
    ) -> List[AgentInfo]:
        """
        Find agents by type.

        Args:
            agent_type: Agent type to search for
            status: Filter by status (optional)

        Returns:
            List of matching agents
        """
        agents = []

        for agent in self._agents.values():
            if agent.agent_type == agent_type:
                if status is None or agent.status == status:
                    agents.append(agent)

        return agents

    def get_all_agents(self, status: Optional[AgentStatus] = None) -> List[AgentInfo]:
        """Get all agents, optionally filtered by status"""
        agents = list(self._agents.values())

        if status:
            agents = [a for a in agents if a.status == status]

        return agents

    def get_capability_stats(self) -> Dict[str, int]:
        """Get statistics about capabilities"""
        return {cap_name: len(agent_ids) for cap_name, agent_ids in self._capability_index.items()}

    def get_metrics(self) -> Dict[str, Any]:
        """Get registry metrics"""
        return {
            "agents_registered": self._agents_registered,
            "agents_decommissioned": self._agents_decommissioned,
            "active_agents": sum(
                1 for a in self._agents.values() if a.status == AgentStatus.ACTIVE
            ),
            "idle_agents": sum(1 for a in self._agents.values() if a.status == AgentStatus.IDLE),
            "total_capabilities": len(self._capability_index),
            "average_reputation": (
                sum(a.reputation for a in self._agents.values()) / len(self._agents)
                if self._agents
                else 0.0
            ),
        }
