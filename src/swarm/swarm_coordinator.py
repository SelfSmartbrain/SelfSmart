"""Swarm Coordinator for Swarm Orchestration (Phase 8).

Central coordinator for managing the entire swarm of agents.
Enhanced with in-process message queues, consensus evaluation, and load balancing.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Callable
from uuid import UUID, uuid4
from dataclasses import dataclass, field
from enum import Enum
from collections import deque

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.swarm.director import DirectorAgent, SwarmGoal

logger = get_logger(__name__)


class MessageType(str, Enum):
    """Types of messages in the swarm communication system"""
    TASK_ASSIGNMENT = "task_assignment"
    TASK_RESULT = "task_result"
    CONSENSUS_VOTE = "consensus_vote"
    CONSENSUS_RESULT = "consensus_result"
    HEARTBEAT = "heartbeat"
    STATUS_UPDATE = "status_update"
    LOAD_REPORT = "load_report"
    SCALING_SIGNAL = "scaling_signal"


@dataclass
class SwarmMessage:
    """Message for inter-agent communication"""
    msg_type: MessageType
    sender_id: UUID
    recipient_id: Optional[UUID]  # None for broadcast
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[UUID] = None
    reply_to: Optional[UUID] = None


class InProcessMessageRouter:
    """In-memory async message router for swarm communication"""
    
    def __init__(self):
        self._queues: Dict[UUID, asyncio.Queue] = {}
        self._subscriptions: Dict[MessageType, List[UUID]] = {}
        self._broadcast_queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._router_task: Optional[asyncio.Task] = None
    
    def register_agent(self, agent_id: UUID) -> asyncio.Queue:
        """Register an agent and return its message queue"""
        queue = asyncio.Queue()
        self._queues[agent_id] = queue
        return queue
    
    def unregister_agent(self, agent_id: UUID) -> None:
        """Unregister an agent"""
        if agent_id in self._queues:
            del self._queues[agent_id]
        # Remove from subscriptions
        for msg_type, subscribers in self._subscriptions.items():
            if agent_id in subscribers:
                subscribers.remove(agent_id)
    
    def subscribe(self, agent_id: UUID, msg_type: MessageType) -> None:
        """Subscribe agent to a message type"""
        if msg_type not in self._subscriptions:
            self._subscriptions[msg_type] = []
        if agent_id not in self._subscriptions[msg_type]:
            self._subscriptions[msg_type].append(agent_id)
    
    def unsubscribe(self, agent_id: UUID, msg_type: MessageType) -> None:
        """Unsubscribe agent from a message type"""
        if msg_type in self._subscriptions:
            if agent_id in self._subscriptions[msg_type]:
                self._subscriptions[msg_type].remove(agent_id)
    
    async def send(self, message: SwarmMessage) -> None:
        """Send a message to a specific recipient or broadcast"""
        if message.recipient_id is not None:
            # Direct message
            if message.recipient_id in self._queues:
                await self._queues[message.recipient_id].put(message)
            else:
                logger.warning(f"Recipient {message.recipient_id} not registered")
        else:
            # Broadcast
            await self._broadcast_queue.put(message)
    
    async def start(self) -> None:
        """Start the router"""
        self._running = True
        self._router_task = asyncio.create_task(self._route_loop())
        logger.info("InProcessMessageRouter started")
    
    async def stop(self) -> None:
        """Stop the router"""
        self._running = False
        if self._router_task:
            self._router_task.cancel()
            try:
                await self._router_task
            except asyncio.CancelledError:
                pass
        logger.info("InProcessMessageRouter stopped")
    
    async def _route_loop(self) -> None:
        """Main routing loop"""
        while self._running:
            try:
                # Process broadcast queue
                try:
                    message = await asyncio.wait_for(self._broadcast_queue.get(), timeout=0.1)
                    for agent_id, queue in self._queues.items():
                        if message.sender_id != agent_id:  # Don't send to sender
                            await queue.put(message)
                except asyncio.TimeoutError:
                    pass
                
                # Process direct messages (they're already in queues)
                await asyncio.sleep(0.01)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in router loop: {e}")
                await asyncio.sleep(0.1)
    
    async def receive(self, agent_id: UUID, timeout: float = 1.0) -> Optional[SwarmMessage]:
        """Receive a message for an agent"""
        if agent_id not in self._queues:
            return None
        try:
            return await asyncio.wait_for(self._queues[agent_id].get(), timeout=timeout)
        except asyncio.TimeoutError:
            return None


class ConsensusEvaluator:
    """Consensus evaluation for multi-agent agreement"""
    
    def __init__(self, min_agreement: float = 0.66):
        self.min_agreement = min_agreement
        self._votes: Dict[UUID, Dict[UUID, Any]] = {}  # proposal_id -> {voter_id: vote}
        self._vote_weights: Dict[UUID, float] = {}  # voter_id -> weight
    
    def register_voter(self, voter_id: UUID, weight: float = 1.0) -> None:
        """Register a voter with optional weight"""
        self._vote_weights[voter_id] = weight
    
    def unregister_voter(self, voter_id: UUID) -> None:
        """Unregister a voter"""
        if voter_id in self._vote_weights:
            del self._vote_weights[voter_id]
    
    def submit_vote(self, proposal_id: UUID, voter_id: UUID, vote: Any) -> None:
        """Submit a vote for a proposal"""
        if proposal_id not in self._votes:
            self._votes[proposal_id] = {}
        self._votes[proposal_id][voter_id] = vote
    
    def evaluate(self, proposal_id: UUID) -> Dict[str, Any]:
        """Evaluate consensus for a proposal"""
        if proposal_id not in self._votes:
            return {"consensus": False, "reason": "No votes submitted"}
        
        votes = self._votes[proposal_id]
        if not votes:
            return {"consensus": False, "reason": "No votes"}
        
        # Count votes by value
        vote_counts: Dict[Any, float] = {}
        total_weight = 0.0
        
        for voter_id, vote in votes.items():
            weight = self._vote_weights.get(voter_id, 1.0)
            vote_str = str(vote)
            vote_counts[vote_str] = vote_counts.get(vote_str, 0.0) + weight
            total_weight += weight
        
        # Find majority
        max_votes = max(vote_counts.values()) if vote_counts else 0
        agreement_ratio = max_votes / total_weight if total_weight > 0 else 0
        
        consensus_reached = agreement_ratio >= self.min_agreement
        
        # Get winning vote
        winning_vote = max(vote_counts, key=vote_counts.get) if vote_counts else None
        
        return {
            "consensus": consensus_reached,
            "agreement_ratio": agreement_ratio,
            "winning_vote": winning_vote,
            "vote_distribution": vote_counts,
            "total_voters": len(votes),
            "required_ratio": self.min_agreement,
        }
    
    def clear_proposal(self, proposal_id: UUID) -> None:
        """Clear votes for a proposal"""
        if proposal_id in self._votes:
            del self._votes[proposal_id]


class LoadBalancer:
    """Load balancer for distributing tasks across agents"""
    
    def __init__(self):
        self._agent_loads: Dict[UUID, float] = {}
        self._agent_capabilities: Dict[UUID, List[str]] = {}
        self._agent_status: Dict[UUID, str] = {}  # idle, busy, offline
        self._task_history: Dict[UUID, List[Dict]] = {}
    
    def register_agent(self, agent_id: UUID, capabilities: List[str] = None, max_load: float = 1.0) -> None:
        """Register an agent with capabilities"""
        self._agent_loads[agent_id] = 0.0
        self._agent_capabilities[agent_id] = capabilities or []
        self._agent_status[agent_id] = "idle"
        self._task_history[agent_id] = []
    
    def unregister_agent(self, agent_id: UUID) -> None:
        """Unregister an agent"""
        for d in [self._agent_loads, self._agent_capabilities, self._agent_status, self._task_history]:
            if agent_id in d:
                del d[agent_id]
    
    def update_load(self, agent_id: UUID, load: float) -> None:
        """Update agent load (0.0 to 1.0)"""
        if agent_id in self._agent_loads:
            self._agent_loads[agent_id] = max(0.0, min(1.0, load))
            self._agent_status[agent_id] = "busy" if load > 0.1 else "idle"
    
    def update_status(self, agent_id: UUID, status: str) -> None:
        """Update agent status"""
        if agent_id in self._agent_status:
            self._agent_status[agent_id] = status
    
    def record_task_completion(self, agent_id: UUID, task_info: Dict[str, Any]) -> None:
        """Record task completion for learning"""
        if agent_id in self._task_history:
            self._task_history[agent_id].append({
                **task_info,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })
            # Keep last 100 tasks
            if len(self._task_history[agent_id]) > 100:
                self._task_history[agent_id] = self._task_history[agent_id][-100:]
    
    def select_agent(self, required_capabilities: List[str] = None, strategy: str = "least_loaded") -> Optional[UUID]:
        """Select best agent for a task"""
        # Filter by capabilities
        candidates = []
        for agent_id, capabilities in self._agent_capabilities.items():
            if self._agent_status.get(agent_id) == "offline":
                continue
            if required_capabilities:
                if not all(cap in capabilities for cap in required_capabilities):
                    continue
            candidates.append(agent_id)
        
        if not candidates:
            return None
        
        if strategy == "least_loaded":
            return min(candidates, key=lambda a: self._agent_loads.get(a, 1.0))
        elif strategy == "most_capable":
            return max(candidates, key=lambda a: len(self._agent_capabilities.get(a, [])))
        elif strategy == "round_robin":
            # Simple round-robin based on task count
            return min(candidates, key=lambda a: len(self._task_history.get(a, [])))
        
        return candidates[0]
    
    def get_load_report(self) -> Dict[str, Any]:
        """Get current load report"""
        return {
            "agent_loads": {str(k): v for k, v in self._agent_loads.items()},
            "agent_status": {str(k): v for k, v in self._agent_status.items()},
            "total_agents": len(self._agent_loads),
            "busy_agents": sum(1 for s in self._agent_status.values() if s == "busy"),
            "idle_agents": sum(1 for s in self._agent_status.values() if s == "idle"),
        }


# Global instances for swarm communication
message_router = InProcessMessageRouter()
consensus_evaluator = ConsensusEvaluator()
load_balancer = LoadBalancer()


class SwarmMetrics(BaseModel):
    """Metrics for the entire swarm."""

    total_directors: int
    total_sub_orchestrators: int
    active_goals: int
    completed_goals: int
    failed_goals: int
    average_task_duration: float
    total_tasks_completed: int
    swarm_utilization: float
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class SwarmCoordinator:
    """Central coordinator for managing multiple director agents.
    
    Enhanced with in-process message queues, consensus evaluation, and load balancing.
    """
    
    def __init__(self, num_directors: int = 5, sub_orchestrators_per_director: int = 10):
        """Initialize swarm coordinator."""
        self.num_directors = num_directors
        self.sub_orchestrators_per_director = sub_orchestrators_per_director

        self.directors: Dict[UUID, DirectorAgent] = {}
        self._running = False
        self._monitor_task: Optional[asyncio.Task] = None
        self._message_router = message_router
        self._consensus = consensus_evaluator
        self._load_balancer = load_balancer

        logger.info(
            f"SwarmCoordinator initialized with {num_directors} directors, "
            f"{sub_orchestrators_per_director} sub-orchestrators per director"
        )

    async def initialize(self) -> None:
        """Initialize swarm coordinator and all directors."""
        logger.info("Initializing SwarmCoordinator")
        self._running = True

        # Start message router
        await self._message_router.start()

        # Initialize director agents
        for i in range(self.num_directors):
            director = DirectorAgent(max_sub_orchestrators=self.sub_orchestrators_per_director)
            await director.initialize()
            director_id = uuid4()
            self.directors[director_id] = director
            
            # Register with communication infrastructure
            self._message_router.register_agent(director_id)
            self._load_balancer.register_agent(director_id, ["director", "coordination"])
            self._consensus.register_voter(director_id, weight=1.0)

        # Start monitoring task
        self._monitor_task = asyncio.create_task(self._monitor_loop())

        logger.info(f"SwarmCoordinator initialized with {len(self.directors)} directors")

    async def shutdown(self) -> None:
        """Shutdown swarm coordinator and all directors."""
        logger.info("Shutting down SwarmCoordinator")
        self._running = False

        if self._monitor_task:
            self._monitor_task.cancel()
            try:
                await self._monitor_task
            except asyncio.CancelledError:
                pass

        # Stop message router
        await self._message_router.stop()

        # Shutdown all directors
        for director in self.directors.values():
            await director.shutdown()

        self.directors.clear()
        logger.info("SwarmCoordinator shutdown complete")

    async def submit_goal(self, goal: SwarmGoal) -> UUID:
        """Submit a goal to the swarm (assigns to least loaded director)."""
        logger.info(f"Submitting goal to swarm: {goal.description}")

        # Also register with the global runtime's ObjectiveManager
        try:
            from src.runtime.runtime_singleton import get_runtime

            runtime = get_runtime()
            runtime.objective_manager.set_objective(
                goal.description,
                priority=goal.priority,
                metadata={"swarm_goal": True, "goal_id": str(goal.goal_id)},
            )
        except RuntimeError:
            pass  # Runtime not initialized yet (startup)

        # Use load balancer to find best director
        director_id = self._load_balancer.select_agent(
            required_capabilities=["director"],
            strategy="least_loaded"
        )
        
        if not director_id or director_id not in self.directors:
            # Fallback to original method
            director = await self._get_least_loaded_director()
            if not director:
                raise RuntimeError("No available directors")
        else:
            director = self.directors[director_id]

        goal_id = await director.submit_goal(goal)
        logger.info(f"Goal {goal_id} assigned to director {director_id}")
        
        # Update load balancer
        self._load_balancer.update_load(director_id, 0.5)

        return goal_id

    async def _get_least_loaded_director(self) -> Optional[DirectorAgent]:
        """Get the director with the least current load."""
        if not self.directors:
            return None

        min_load = float("inf")
        least_loaded = None

        for director_id, director in self.directors.items():
            status = await director.monitor_swarm()
            load = status.get("busy_sub_orchestrators", 0) / max(1, status.get("total_sub_orchestrators", 1))

            if load < min_load:
                min_load = load
                least_loaded = director

        return least_loaded

    async def get_goal_status(self, goal_id: UUID) -> Optional[Dict[str, Any]]:
        """Get status of a goal from its director."""
        for director in self.directors.values():
            status = await director.get_goal_status(goal_id)
            if status:
                return status

        return None

    async def request_consensus(self, proposal: Dict[str, Any], voters: List[UUID] = None) -> Dict[str, Any]:
        """Request consensus from directors on a proposal"""
        proposal_id = uuid4()
        
        # Default to all directors if no voters specified
        if voters is None:
            voters = list(self.directors.keys())
        
        # Broadcast consensus request
        message = SwarmMessage(
            msg_type=MessageType.CONSENSUS_VOTE,
            sender_id=uuid4(),  # coordinator ID
            recipient_id=None,  # broadcast
            payload={
                "proposal_id": str(proposal_id),
                "proposal": proposal,
                "voters": [str(v) for v in voters],
            },
        )
        await self._message_router.send(message)
        
        # Collect votes (simplified - in real implementation would wait for responses)
        # For now, simulate voting
        for voter_id in voters:
            if voter_id in self.directors:
                # Simulate vote based on proposal
                vote = {"agree": True, "confidence": 0.8}
                self._consensus.submit_vote(proposal_id, voter_id, vote)
        
        # Evaluate consensus
        result = self._consensus.evaluate(proposal_id)
        self._consensus.clear_proposal(proposal_id)
        
        return result

    async def get_swarm_metrics(self) -> SwarmMetrics:
        """Get comprehensive metrics for the entire swarm."""
        total_sub_orchestrators = 0
        active_goals = 0
        completed_goals = 0
        failed_goals = 0
        total_tasks_completed = 0

        for director in self.directors.values():
            status = await director.monitor_swarm()
            total_sub_orchestrators += status.get("total_sub_orchestrators", 0)
            active_goals += status.get("active_goals", 0)

            # Count completed/failed goals from director's active_goals
            for goal in director.active_goals.values():
                if goal.status == "completed":
                    completed_goals += 1
                elif goal.status == "failed":
                    failed_goals += 1

        busy_orchestrators = sum(
            status.get("busy_sub_orchestrators", 0)
            for director in self.directors.values()
            if hasattr(director, "monitor_swarm")
        )

        swarm_utilization = (
            busy_orchestrators / total_sub_orchestrators if total_sub_orchestrators > 0 else 0.0
        )

        return SwarmMetrics(
            total_directors=len(self.directors),
            total_sub_orchestrators=total_sub_orchestrators,
            active_goals=active_goals,
            completed_goals=completed_goals,
            failed_goals=failed_goals,
            average_task_duration=0.0,
            total_tasks_completed=total_tasks_completed,
            swarm_utilization=swarm_utilization,
        )

    async def _monitor_loop(self) -> None:
        """Background monitoring loop for swarm health."""
        logger.info("SwarmCoordinator monitor loop started")

        while self._running:
            try:
                # Collect metrics
                metrics = await self.get_swarm_metrics()
                logger.info(
                    f"Swarm metrics: {metrics.total_sub_orchestrators} sub-orchestrators, "
                    f"{metrics.active_goals} active goals, "
                    f"{metrics.swarm_utilization:.2%} utilization"
                )

                # Get load balancer report
                load_report = self._load_balancer.get_load_report()
                logger.debug(f"Load report: {load_report}")

                # Auto-scale if needed
                await self._auto_scale(metrics)

                # Sleep for monitoring interval
                await asyncio.sleep(30)

            except asyncio.CancelledError:
                logger.info("SwarmCoordinator monitor loop cancelled")
                break
            except Exception as e:
                logger.error(f"Error in swarm monitor loop: {e}")
                await asyncio.sleep(30)

        logger.info("SwarmCoordinator monitor loop ended")

    async def _auto_scale(self, metrics: SwarmMetrics) -> None:
        """Auto-scale the swarm based on utilization."""
        # Scale up if utilization > 80%
        if metrics.swarm_utilization > 0.8:
            logger.info("High utilization detected, considering scale-up")
            # Would implement scale-up logic here

        # Scale down if utilization < 20%
        elif metrics.swarm_utilization < 0.2:
            logger.info("Low utilization detected, considering scale-down")
            # Would implement scale-down logic here

    async def scale_directors(self, target_count: int) -> bool:
        """Scale the number of directors."""
        current_count = len(self.directors)

        if target_count > current_count:
            # Scale up
            for i in range(target_count - current_count):
                director = DirectorAgent(max_sub_orchestrators=self.sub_orchestrators_per_director)
                await director.initialize()
                director_id = uuid4()
                self.directors[director_id] = director
                
                # Register with communication infrastructure
                self._message_router.register_agent(director_id)
                self._load_balancer.register_agent(director_id, ["director", "coordination"])
                self._consensus.register_voter(director_id, weight=1.0)
                
            logger.info(f"Scaled directors from {current_count} to {target_count}")
        elif target_count < current_count:
            # Scale down (remove idle directors)
            idle_directors = [
                director_id
                for director_id, director in self.directors.items()
                if all(
                    goal.status not in ["planning", "executing"]
                    for goal in director.active_goals.values()
                )
            ]

            to_remove = current_count - target_count
            for i in range(min(to_remove, len(idle_directors))):
                director_id = idle_directors[i]
                await self.directors[director_id].shutdown()
                del self.directors[director_id]
                
                # Unregister from communication infrastructure
                self._message_router.unregister_agent(director_id)
                self._load_balancer.unregister_agent(director_id)
                self._consensus.unregister_voter(director_id)

            logger.info(f"Scaled directors from {current_count} to {target_count}")

        return True

    async def get_director_status(self) -> List[Dict[str, Any]]:
        """Get status of all directors."""
        statuses = []
        for director_id, director in self.directors.items():
            status = await director.monitor_swarm()
            statuses.append({"director_id": str(director_id), **status})
        return statuses
