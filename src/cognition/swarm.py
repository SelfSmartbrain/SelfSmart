"""
Swarm - Hierarchical Multi-Agent Coordination

Replaces flat coordination with hierarchical delegation using
AgentRegistry and DelegationProtocol for structured agent collaboration.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Callable
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import uuid

from src.cognition.hierarchical_agent_registry import HierarchicalAgentRegistry, AgentRelationship
from src.cognition.delegation_protocol import (
    DelegationProtocol,
    DelegationTask,
    DelegationContract,
    DelegationStatus,
    DelegationPriority,
    ParallelDelegationManager,
)
from src.cognition.cognitive_bus import (
    CognitiveBus,
    CognitiveEventType,
    get_cognitive_bus,
    emit_delegation_event,
)

logger = logging.getLogger(__name__)


class SwarmRole(Enum):
    """Roles within the swarm hierarchy"""

    COORDINATOR = "coordinator"  # Top-level coordinator
    SUPERVISOR = "supervisor"  # Manages a team of workers
    WORKER = "worker"  # Executes delegated tasks
    SPECIALIST = "specialist"  # Domain-specific expert


@dataclass
class SwarmAgent:
    """Agent in the swarm with hierarchical role"""

    agent_id: str
    name: str
    role: SwarmRole
    capabilities: List[str]
    parent_id: Optional[str] = None
    children: List[str] = field(default_factory=list)
    status: str = "idle"
    current_task: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SwarmTask:
    """Task managed by the swarm"""

    task_id: str
    description: str
    required_capabilities: List[str]
    assigned_agent: Optional[str] = None
    parent_task_id: Optional[str] = None
    subtasks: List[str] = field(default_factory=list)
    status: str = "pending"
    result: Optional[Any] = None
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    completed_at: Optional[float] = None


class HierarchicalSwarm:
    """
    Hierarchical multi-agent swarm coordinator.

    Implements structured delegation where:
    - Coordinator decomposes goals and delegates to supervisors
    - Supervisors manage teams of workers/specialists
    - Workers execute tasks and report results up the chain
    - Results are aggregated hierarchically
    """

    def __init__(
        self,
        agent_registry: HierarchicalAgentRegistry,
        delegation_protocol: DelegationProtocol,
        cognitive_bus: Optional[CognitiveBus] = None,
    ):
        self.registry = agent_registry
        self.delegation = delegation_protocol
        self.bus = cognitive_bus or get_cognitive_bus()
        self.parallel_manager = ParallelDelegationManager(delegation_protocol)

        self._agents: Dict[str, SwarmAgent] = {}
        self._tasks: Dict[str, SwarmTask] = {}
        self._task_results: Dict[str, Any] = {}
        self._coordinator_id: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize the swarm"""
        await self.bus.start()
        logger.info("HierarchicalSwarm initialized")

    async def register_swarm_agent(
        self,
        agent_id: str,
        name: str,
        role: SwarmRole,
        capabilities: List[str],
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> SwarmAgent:
        """Register an agent in the swarm hierarchy"""
        # Register in hierarchical registry
        await self.registry.register_agent(
            agent_id=agent_id,
            name=name,
            agent_type=role.value,
            capabilities=[{"name": c, "proficiency": 0.8} for c in capabilities],
            parent_id=parent_id,
            metadata=metadata or {},
        )

        agent = SwarmAgent(
            agent_id=agent_id,
            name=name,
            role=role,
            capabilities=capabilities,
            parent_id=parent_id,
            metadata=metadata or {},
        )

        self._agents[agent_id] = agent

        # Update parent's children list
        if parent_id and parent_id in self._agents:
            self._agents[parent_id].children.append(agent_id)

        # Set coordinator if this is a coordinator role
        if role == SwarmRole.COORDINATOR:
            self._coordinator_id = agent_id

        await emit_delegation_event(
            CognitiveEventType.AGENT_REGISTERED,
            delegator_id="swarm",
            delegatee_id=agent_id,
            task_id="",
            source="swarm",
            details={"role": role.value, "capabilities": capabilities},
        )

        logger.info(f"Registered swarm agent {agent_id} ({name}) as {role.value}")
        return agent

    async def execute_hierarchical_task(
        self,
        goal: str,
        required_capabilities: List[str],
        coordinator_id: Optional[str] = None,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """
        Execute a task using hierarchical delegation.

        Flow:
        1. Coordinator receives goal
        2. Decomposes into subtasks
        3. Delegates to appropriate supervisors
        4. Supervisors delegate to workers
        5. Results aggregate back up
        """
        coordinator = coordinator_id or self._coordinator_id
        if not coordinator:
            raise RuntimeError("No coordinator available")

        # Create root task
        root_task = SwarmTask(
            task_id=f"task_{uuid.uuid4().hex[:12]}",
            description=goal,
            required_capabilities=required_capabilities,
            metadata=context or {},
        )
        self._tasks[root_task.task_id] = root_task

        # Delegate from coordinator
        result = await self._delegate_recursive(
            task=root_task,
            delegator_id=coordinator,
            depth=0,
        )

        root_task.status = "completed"
        root_task.completed_at = datetime.now().timestamp()
        root_task.result = result

        return result

    async def _delegate_recursive(
        self,
        task: SwarmTask,
        delegator_id: str,
        depth: int = 0,
        max_depth: int = 3,
    ) -> Any:
        """Recursively delegate task down the hierarchy"""
        if depth >= max_depth:
            # Execute directly at this level
            return await self._execute_at_level(task, delegator_id)

        delegator = self._agents.get(delegator_id)
        if not delegator:
            raise RuntimeError(f"Delegator {delegator_id} not found")

        # Find capable subordinates
        subordinates = await self.registry.get_subordinates(delegator_id, direct_only=True)
        subordinate_ids = [a["agent_id"] for a in subordinates]

        if not subordinate_ids:
            # No subordinates, execute at this level
            return await self._execute_at_level(task, delegator_id)

        # Check if any subordinate can handle the task
        capable_agents = await self.registry.find_capable_agents(
            task.required_capabilities,
            min_proficiency=0.6,
            strategy="hybrid",
            limit=len(subordinate_ids),
        )

        # Filter to actual subordinates
        candidate_ids = [
            c["agent"]["agent_id"]
            for c in capable_agents
            if c["agent"]["agent_id"] in subordinate_ids
        ]

        if not candidate_ids:
            # No capable subordinates, try peers or execute here
            candidate_ids = subordinate_ids

        if len(candidate_ids) == 1:
            # Single best candidate - delegate directly
            delegatee = candidate_ids[0]
            return await self._delegate_and_wait(task, delegator_id, delegatee)
        else:
            # Multiple candidates - use parallel delegation with aggregation
            return await self._delegate_parallel_and_aggregate(task, delegator_id, candidate_ids)

    async def _delegate_and_wait(
        self,
        task: SwarmTask,
        delegator_id: str,
        delegatee_id: str,
    ) -> Any:
        """Delegate task to a single agent and wait for result"""
        delegation_task = DelegationTask(
            task_id=task.task_id,
            description=task.description,
            required_capabilities=task.required_capabilities,
            parameters=task.metadata,
            priority=DelegationPriority.NORMAL,
            deadline=task.metadata.get("deadline"),
        )

        task.assigned_agent = delegatee_id
        task.status = "delegated"

        await emit_delegation_event(
            CognitiveEventType.AGENT_DELEGATED,
            delegator_id=delegator_id,
            delegatee_id=delegatee_id,
            task_id=task.task_id,
            source="swarm",
            details={"task": task.description},
        )

        # Create future for result
        result_future = asyncio.get_event_loop().create_future()

        async def callback(result):
            if result.success:
                self._task_results[task.task_id] = result.result
                task.result = result.result
                task.status = "completed"
                task.completed_at = datetime.now().timestamp()
            else:
                task.status = "failed"
                task.metadata["error"] = result.error
            result_future.set_result(result)

        await self.delegation.delegate(delegation_task, delegator_id, delegatee_id, callback)

        return await result_future

    async def _delegate_parallel_and_aggregate(
        self,
        task: SwarmTask,
        delegator_id: str,
        candidate_ids: List[str],
    ) -> Any:
        """Delegate to multiple agents in parallel and aggregate results"""
        # Decompose task into subtasks for parallel execution
        subtasks = await self._decompose_task(task, len(candidate_ids))

        delegation_tasks = [
            DelegationTask(
                task_id=f"{task.task_id}_sub_{i}",
                description=subtask,
                required_capabilities=task.required_capabilities,
                parameters={**task.metadata, "subtask_index": i},
                priority=DelegationPriority.NORMAL,
            )
            for i, subtask in enumerate(subtasks)
        ]

        results = await self.parallel_manager.delegate_parallel(
            delegation_tasks,
            delegator_id,
            delegatee_ids=candidate_ids[: len(delegation_tasks)],
            aggregation="all",
        )

        # Aggregate results
        successful_results = [r.result for r in results if r.success]
        failed_results = [r.error for r in results if not r.success]

        if failed_results:
            logger.warning(f"Some parallel delegations failed: {failed_results}")

        # Combine results (customize based on task type)
        aggregated = await self._aggregate_results(successful_results, task)

        task.result = aggregated
        task.status = "completed"
        task.completed_at = datetime.now().timestamp()

        return aggregated

    async def _decompose_task(self, task: SwarmTask, num_parts: int) -> List[str]:
        """Decompose a task into subtasks for parallel execution"""
        # This is a simplified decomposition
        # In production, would use LLM to intelligently decompose
        base_desc = task.description
        return [f"{base_desc} (part {i + 1}/{num_parts})" for i in range(num_parts)]

    async def _aggregate_results(self, results: List[Any], task: SwarmTask) -> Any:
        """Aggregate results from parallel delegations"""
        if not results:
            return {"error": "No successful results"}

        if len(results) == 1:
            return results[0]

        # Default aggregation: combine into list
        return {
            "aggregated": True,
            "parts": results,
            "task": task.description,
        }

    async def _execute_at_level(self, task: SwarmTask, agent_id: str) -> Any:
        """Execute task at current agent level (no further delegation)"""
        # This would integrate with the agent's actual execution capability
        # For now, return a placeholder
        logger.info(f"Agent {agent_id} executing task: {task.description}")

        task.assigned_agent = agent_id
        task.status = "executing"

        # Simulate execution
        await asyncio.sleep(0.1)

        task.status = "completed"
        task.completed_at = datetime.now().timestamp()
        task.result = {"status": "completed", "task": task.description}

        return task.result

    async def broadcast_to_level(
        self,
        level: SwarmRole,
        message: Dict[str, Any],
    ) -> List[Any]:
        """Broadcast message to all agents at a specific hierarchy level"""
        targets = [agent_id for agent_id, agent in self._agents.items() if agent.role == level]

        results = []
        for agent_id in targets:
            try:
                # Send via message broker (would integrate with actual broker)
                await self.bus.emit(
                    self.bus.create_event(
                        CognitiveEventType.AGENT_DELEGATED,
                        source="swarm_broadcast",
                        payload={"target": agent_id, "message": message},
                    )
                )
                results.append({"agent": agent_id, "status": "sent"})
            except Exception as e:
                results.append({"agent": agent_id, "error": str(e)})

        return results

    def get_swarm_status(self) -> Dict[str, Any]:
        """Get current swarm status"""
        return {
            "coordinator": self._coordinator_id,
            "total_agents": len(self._agents),
            "agents_by_role": {
                role.value: sum(1 for a in self._agents.values() if a.role == role)
                for role in SwarmRole
            },
            "active_tasks": sum(
                1 for t in self._tasks.values() if t.status in ("pending", "delegated", "executing")
            ),
            "completed_tasks": sum(1 for t in self._tasks.values() if t.status == "completed"),
            "agents": {
                agent_id: {
                    "name": agent.name,
                    "role": agent.role.value,
                    "status": agent.status,
                    "capabilities": agent.capabilities,
                    "parent": agent.parent_id,
                    "children": agent.children,
                }
                for agent_id, agent in self._agents.items()
            },
        }

    def get_task_status(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a specific task"""
        task = self._tasks.get(task_id)
        if not task:
            return None

        return {
            "task_id": task.task_id,
            "description": task.description,
            "status": task.status,
            "assigned_agent": task.assigned_agent,
            "parent_task": task.parent_task_id,
            "subtasks": task.subtasks,
            "result": task.result,
            "created_at": task.created_at,
            "completed_at": task.completed_at,
        }


class SwarmCoordinator:
    """
    High-level coordinator that manages the swarm lifecycle
    and integrates with the planner for goal execution.
    """

    def __init__(
        self,
        swarm: HierarchicalSwarm,
        planner: Any,
        memory_fabric: Any,
    ):
        self.swarm = swarm
        self.planner = planner
        self.memory = memory_fabric
        self._active_goals: Dict[str, Dict[str, Any]] = {}

    async def execute_goal(
        self,
        goal: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> Any:
        """Execute a high-level goal using the swarm"""
        goal_id = f"goal_{uuid.uuid4().hex[:12]}"

        # Create plan
        plan = await self.planner.create_plan(goal, context or {}, strategy="hierarchical")

        # Store goal context
        self._active_goals[goal_id] = {
            "goal": goal,
            "plan": plan,
            "context": context,
            "status": "planning",
            "created_at": datetime.now().timestamp(),
        }

        # Execute via swarm
        self._active_goals[goal_id]["status"] = "executing"

        try:
            # Extract required capabilities from plan
            required_caps = self._extract_capabilities(plan)

            result = await self.swarm.execute_hierarchical_task(
                goal=goal,
                required_capabilities=required_caps,
                context=context,
            )

            self._active_goals[goal_id]["status"] = "completed"
            self._active_goals[goal_id]["result"] = result
            self._active_goals[goal_id]["completed_at"] = datetime.now().timestamp()

            return result

        except Exception as e:
            self._active_goals[goal_id]["status"] = "failed"
            self._active_goals[goal_id]["error"] = str(e)
            raise

    def _extract_capabilities(self, plan: Any) -> List[str]:
        """Extract required capabilities from a plan"""
        # Simplified - in production would analyze plan actions
        return ["general_reasoning", "task_execution", "tool_use"]

    def get_goal_status(self, goal_id: str) -> Optional[Dict[str, Any]]:
        """Get status of a goal"""
        return self._active_goals.get(goal_id)


async def create_default_swarm(
    agent_registry: HierarchicalAgentRegistry,
    delegation_protocol: DelegationProtocol,
    cognitive_bus: Optional[CognitiveBus] = None,
) -> HierarchicalSwarm:
    """Factory to create a default swarm configuration"""
    swarm = HierarchicalSwarm(agent_registry, delegation_protocol, cognitive_bus)
    await swarm.initialize()
    return swarm
