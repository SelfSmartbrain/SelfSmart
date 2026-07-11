"""
Society Runtime - Manages agent society and collaboration

The SocietyRuntime is responsible for:
- Managing agent society lifecycle
- Facilitating agent collaboration
- Coordinating multi-agent tasks
- Managing society resources
- Hierarchical delegation and supervision
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


logger = logging.getLogger(__name__)


class SocietyStatus(Enum):
    """Status of agent society"""
    FORMING = "forming"
    ACTIVE = "active"
    DISSOLVING = "dissolving"
    DISSOLVED = "dissolved"


class SocietyRole(Enum):
    """Roles within a society"""
    SUPERVISOR = "supervisor"
    COORDINATOR = "coordinator"
    WORKER = "worker"
    SPECIALIST = "specialist"


@dataclass
class Society:
    """An agent society"""
    society_id: str
    name: str
    members: Set[str]
    purpose: str
    status: SocietyStatus = SocietyStatus.FORMING
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    resources: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    # Hierarchical structure
    supervisors: Set[str] = field(default_factory=set)
    coordinators: Set[str] = field(default_factory=set)
    role_assignments: Dict[str, SocietyRole] = field(default_factory=dict)
    
    def add_member(self, agent_id: str, role: SocietyRole = SocietyRole.WORKER) -> None:
        """Add a member to the society with a role"""
        self.members.add(agent_id)
        self.role_assignments[agent_id] = role
        if role == SocietyRole.SUPERVISOR:
            self.supervisors.add(agent_id)
        elif role == SocietyRole.COORDINATOR:
            self.coordinators.add(agent_id)
    
    def remove_member(self, agent_id: str) -> None:
        """Remove a member from the society"""
        self.members.discard(agent_id)
        self.supervisors.discard(agent_id)
        self.coordinators.discard(agent_id)
        self.role_assignments.pop(agent_id, None)
    
    def is_member(self, agent_id: str) -> bool:
        """Check if an agent is a member"""
        return agent_id in self.members
    
    def get_role(self, agent_id: str) -> SocietyRole:
        """Get agent's role in society"""
        return self.role_assignments.get(agent_id, SocietyRole.WORKER)
    
    def get_supervisors(self) -> List[str]:
        """Get all supervisors"""
        return list(self.supervisors)
    
    def get_workers(self) -> List[str]:
        """Get all workers"""
        return [m for m in self.members if self.role_assignments.get(m) == SocietyRole.WORKER]


@dataclass
class Collaboration:
    """A collaboration between agents"""
    collaboration_id: str
    participants: Set[str]
    task: str
    society_id: Optional[str] = None
    started_at: float = field(default_factory=lambda: datetime.now().timestamp())
    ended_at: Optional[float] = None
    status: str = "active"
    results: Dict[str, Any] = field(default_factory=dict)
    # Delegation tracking
    delegation_tree: Dict[str, List[str]] = field(default_factory=dict)  # parent -> children


@dataclass
class DelegationTask:
    """A task delegation within society"""
    task_id: str
    description: str
    assigned_to: str
    assigned_by: str
    society_id: str
    required_capabilities: List[str]
    status: str = "pending"
    result: Any = None
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    completed_at: Optional[float] = None


class SocietyRuntime:
    """
    Runtime for agent society management.
    
    Provides:
    - Society creation and management
    - Agent collaboration coordination
    - Resource sharing
    - Society lifecycle management
    - Hierarchical delegation and supervision
    """
    
    def __init__(
        self,
        agent_registry: Any = None,
        delegation_protocol: Any = None,
        message_broker: Any = None,
    ):
        self.agent_registry = agent_registry
        self.delegation_protocol = delegation_protocol
        self.message_broker = message_broker
        
        self._societies: Dict[str, Society] = {}
        self._agent_societies: Dict[str, Set[str]] = defaultdict(set)
        self._collaborations: Dict[str, Collaboration] = {}
        self._delegation_tasks: Dict[str, DelegationTask] = {}
        
        # Statistics
        self._societies_created = 0
        self._collaborations_started = 0
        self._collaborations_completed = 0
        self._delegations_created = 0
    
    async def initialize(self) -> None:
        """Initialize the society runtime"""
        logger.info("SocietyRuntime initialized with hierarchical delegation support")
    
    async def create_society(
        self,
        name: str,
        purpose: str,
        initial_members: Optional[List[str]] = None,
        resources: Optional[Dict[str, Any]] = None,
        supervisors: Optional[List[str]] = None,
    ) -> Society:
        """
        Create a new agent society with hierarchical roles.
        
        Args:
            name: Society name
            purpose: Society purpose
            initial_members: Initial member agent IDs
            resources: Initial resources
            supervisors: Agent IDs to assign as supervisors
            
        Returns:
            Created society
        """
        society_id = f"society_{datetime.now().timestamp()}"
        
        society = Society(
            society_id=society_id,
            name=name,
            members=set(initial_members or []),
            purpose=purpose,
            resources=resources or {},
            status=SocietyStatus.ACTIVE,
        )
        
        # Assign roles
        for member_id in society.members:
            role = SocietyRole.SUPERVISOR if supervisors and member_id in supervisors else SocietyRole.WORKER
            society.add_member(member_id, role)
        
        self._societies[society_id] = society
        
        # Track agent memberships
        for member_id in society.members:
            self._agent_societies[member_id].add(society_id)
        
        self._societies_created += 1
        
        logger.info(f"Created society {society_id}: {name} with {len(society.members)} members "
                   f"({len(society.supervisors)} supervisors)")
        return society
    
    async def dissolve_society(self, society_id: str) -> bool:
        """
        Dissolve a society.
        
        Args:
            society_id: Society identifier
            
        Returns:
            True if dissolved successfully
        """
        if society_id not in self._societies:
            logger.warning(f"Society {society_id} not found")
            return False
        
        society = self._societies[society_id]
        society.status = SocietyStatus.DISSOLVED
        
        # Remove agent memberships
        for member_id in society.members:
            self._agent_societies[member_id].discard(society_id)
        
        logger.info(f"Dissolved society {society_id}")
        return True
    
    async def add_to_society(
        self,
        society_id: str,
        agent_id: str,
        role: SocietyRole = SocietyRole.WORKER,
    ) -> bool:
        """
        Add an agent to a society with a specific role.
        
        Args:
            society_id: Society identifier
            agent_id: Agent identifier
            role: Role in society
            
        Returns:
            True if added successfully
        """
        if society_id not in self._societies:
            logger.warning(f"Society {society_id} not found")
            return False
        
        society = self._societies[society_id]
        society.add_member(agent_id, role)
        self._agent_societies[agent_id].add(society_id)
        
        logger.debug(f"Added agent {agent_id} to society {society_id} as {role.value}")
        return True
    
    async def remove_from_society(
        self,
        society_id: str,
        agent_id: str,
    ) -> bool:
        """
        Remove an agent from a society.
        
        Args:
            society_id: Society identifier
            agent_id: Agent identifier
            
        Returns:
            True if removed successfully
        """
        if society_id not in self._societies:
            logger.warning(f"Society {society_id} not found")
            return False
        
        society = self._societies[society_id]
        society.remove_member(agent_id)
        self._agent_societies[agent_id].discard(society_id)
        
        logger.debug(f"Removed agent {agent_id} from society {society_id}")
        return True
    
    async def start_collaboration(
        self,
        participants: List[str],
        task: str,
        society_id: Optional[str] = None,
    ) -> Collaboration:
        """
        Start a collaboration between agents.
        
        Args:
            participants: List of participant agent IDs
            task: Task to collaborate on
            society_id: Optional society ID
            
        Returns:
            Collaboration object
        """
        collaboration_id = f"collab_{datetime.now().timestamp()}"
        
        collaboration = Collaboration(
            collaboration_id=collaboration_id,
            participants=set(participants),
            task=task,
            society_id=society_id,
        )
        
        self._collaborations[collaboration_id] = collaboration
        self._collaborations_started += 1
        
        logger.info(f"Started collaboration {collaboration_id} with {len(participants)} agents")
        return collaboration
    
    async def end_collaboration(
        self,
        collaboration_id: str,
        results: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """
        End a collaboration.
        
        Args:
            collaboration_id: Collaboration identifier
            results: Collaboration results
            
        Returns:
            True if ended successfully
        """
        if collaboration_id not in self._collaborations:
            logger.warning(f"Collaboration {collaboration_id} not found")
            return False
        
        collaboration = self._collaborations[collaboration_id]
        collaboration.ended_at = datetime.now().timestamp()
        collaboration.status = "completed"
        collaboration.results = results or {}
        
        self._collaborations_completed += 1
        
        logger.info(f"Ended collaboration {collaboration_id}")
        return True
    
    async def delegate_task(
        self,
        society_id: str,
        description: str,
        assigned_by: str,
        required_capabilities: List[str],
        assigned_to: Optional[str] = None,
    ) -> Optional[DelegationTask]:
        """
        Delegate a task within a society using hierarchical delegation.
        
        Args:
            society_id: Society identifier
            description: Task description
            assigned_by: Supervisor/coordinator delegating the task
            required_capabilities: Required capabilities
            assigned_to: Specific agent (None = auto-select from workers)
            
        Returns:
            DelegationTask or None if failed
        """
        society = self._societies.get(society_id)
        if not society:
            logger.warning(f"Society {society_id} not found")
            return None
        
        # Verify delegator has authority
        if not society.is_member(assigned_by):
            logger.warning(f"Agent {assigned_by} not a member of society {society_id}")
            return None
        
        delegator_role = society.get_role(assigned_by)
        if delegator_role not in (SocietyRole.SUPERVISOR, SocietyRole.COORDINATOR):
            logger.warning(f"Agent {assigned_by} lacks delegation authority (role: {delegator_role.value})")
            return None
        
        # Auto-select worker if not specified
        if assigned_to is None:
            # Use delegation protocol if available
            if self.delegation_protocol and self.agent_registry:
                from src.cognition.delegation_protocol import DelegationTask as ProtoDelegationTask, DelegationPriority
                proto_task = ProtoDelegationTask(
                    task_id=f"task_{datetime.now().timestamp()}",
                    description=description,
                    required_capabilities=required_capabilities,
                    priority=DelegationPriority.NORMAL,
                )
                assigned_to = await self.agent_registry.delegate_task(
                    proto_task.__dict__,
                    assigned_by,
                    required_capabilities,
                )
            else:
                # Fallback: pick first available worker
                workers = society.get_workers()
                assigned_to = workers[0] if workers else None
        
        if not assigned_to or not society.is_member(assigned_to):
            logger.warning(f"No suitable worker found for task in society {society_id}")
            return None
        
        # Create delegation task
        task_id = f"task_{datetime.now().timestamp()}"
        delegation_task = DelegationTask(
            task_id=task_id,
            description=description,
            assigned_to=assigned_to,
            assigned_by=assigned_by,
            society_id=society_id,
            required_capabilities=required_capabilities,
        )
        
        self._delegation_tasks[task_id] = delegation_task
        self._delegations_created += 1
        
        # Track in collaboration if exists
        for collab in self._collaborations.values():
            if collab.society_id == society_id and collab.status == "active":
                collab.delegation_tree.setdefault(assigned_by, []).append(assigned_to)
        
        # Send via message broker if available
        if self.message_broker:
            await self.message_broker.publish(f"agent.{assigned_to}.tasks", {
                "type": "delegated_task",
                "task_id": task_id,
                "description": description,
                "required_capabilities": required_capabilities,
                "assigned_by": assigned_by,
                "society_id": society_id,
            })
        
        logger.info(f"Delegated task {task_id} from {assigned_by} to {assigned_to} in society {society_id}")
        return delegation_task
    
    async def complete_task(
        self,
        task_id: str,
        result: Any = None,
        completed_by: Optional[str] = None,
    ) -> bool:
        """Mark a delegated task as completed"""
        task = self._delegation_tasks.get(task_id)
        if not task:
            return False
        
        if completed_by and task.assigned_to != completed_by:
            logger.warning(f"Task {task_id} completed by {completed_by} but assigned to {task.assigned_to}")
            return False
        
        task.status = "completed"
        task.result = result
        task.completed_at = datetime.now().timestamp()
        
        logger.info(f"Task {task_id} completed by {task.assigned_to}")
        return True
    
    def get_society(self, society_id: str) -> Optional[Society]:
        """Get a society by ID"""
        return self._societies.get(society_id)
    
    def get_agent_societies(self, agent_id: str) -> List[Society]:
        """Get all societies for an agent"""
        society_ids = self._agent_societies.get(agent_id, set())
        return [
            self._societies[sid]
            for sid in society_ids
            if sid in self._societies
        ]
    
    def get_collaboration(self, collaboration_id: str) -> Optional[Collaboration]:
        """Get a collaboration by ID"""
        return self._collaborations.get(collaboration_id)
    
    def get_active_collaborations(self) -> List[Collaboration]:
        """Get all active collaborations"""
        return [
            collab for collab in self._collaborations.values()
            if collab.status == "active"
        ]
    
    def get_delegation_task(self, task_id: str) -> Optional[DelegationTask]:
        """Get a delegation task by ID"""
        return self._delegation_tasks.get(task_id)
    
    def get_society_delegations(self, society_id: str) -> List[DelegationTask]:
        """Get all delegations for a society"""
        return [t for t in self._delegation_tasks.values() if t.society_id == society_id]
    
    def get_agent_delegations(self, agent_id: str, as_assigner: bool = True) -> List[DelegationTask]:
        """Get delegations assigned by or to an agent"""
        if as_assigner:
            return [t for t in self._delegation_tasks.values() if t.assigned_by == agent_id]
        return [t for t in self._delegation_tasks.values() if t.assigned_to == agent_id]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get society runtime metrics"""
        return {
            "societies_created": self._societies_created,
            "active_societies": sum(
                1 for s in self._societies.values()
                if s.status == SocietyStatus.ACTIVE
            ),
            "collaborations_started": self._collaborations_started,
            "collaborations_completed": self._collaborations_completed,
            "active_collaborations": len(self.get_active_collaborations()),
            "total_members": sum(len(s.members) for s in self._societies.values()),
            "delegations_created": self._delegations_created,
            "pending_delegations": sum(
                1 for t in self._delegation_tasks.values() if t.status == "pending"
            ),
            "completed_delegations": sum(
                1 for t in self._delegation_tasks.values() if t.status == "completed"
            ),
        }