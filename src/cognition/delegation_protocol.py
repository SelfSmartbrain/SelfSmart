"""
Delegation Protocol - Inter-Agent Task Delegation

Implements structured delegation with task contracts, progress tracking,
and result aggregation for hierarchical multi-agent coordination.
"""

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable, Set
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

logger = logging.getLogger(__name__)


class DelegationStatus(Enum):
    """Delegation lifecycle status"""
    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"
    TIMEOUT = "timeout"


class DelegationPriority(Enum):
    """Delegation priority levels"""
    LOW = 1
    NORMAL = 5
    HIGH = 8
    CRITICAL = 10


@dataclass
class DelegationTask:
    """Task being delegated"""
    task_id: str
    description: str
    required_capabilities: List[str]
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: DelegationPriority = DelegationPriority.NORMAL
    deadline: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DelegationContract:
    """Contract between delegator and delegatee"""
    delegation_id: str
    task: DelegationTask
    delegator_id: str
    delegatee_id: str
    status: DelegationStatus = DelegationStatus.PENDING
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    assigned_at: Optional[float] = None
    started_at: Optional[float] = None
    completed_at: Optional[float] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DelegationResult:
    """Result of a delegation"""
    delegation_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    execution_time: float = 0.0
    delegatee_id: str = ""


class DelegationProtocol:
    """
    Manages task delegation between agents.
    
    Features:
    - Async delegation with callbacks
    - Progress tracking and timeouts
    - Result aggregation for parallel delegations
    - Delegation chaining (delegatee can sub-delegate)
    - Circuit breaker for failing delegatees
    """

    def __init__(
        self,
        agent_registry: Any,
        message_broker: Any,
        default_timeout: int = 300,
        max_retries: int = 2,
    ):
        self.registry = agent_registry
        self.broker = message_broker
        self.default_timeout = default_timeout
        self.max_retries = max_retries

        self._contracts: Dict[str, DelegationContract] = {}
        self._pending_callbacks: Dict[str, List[Callable]] = defaultdict(list)
        self._delegatee_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "success_count": 0,
            "failure_count": 0,
            "avg_execution_time": 0.0,
            "circuit_open": False,
            "circuit_open_until": 0.0,
        })

    async def delegate(
        self,
        task: DelegationTask,
        delegator_id: str,
        delegatee_id: Optional[str] = None,
        callback: Optional[Callable] = None,
    ) -> str:
        """
        Delegate a task to an agent.
        
        Args:
            task: Task to delegate
            delegator_id: ID of delegating agent
            delegatee_id: Specific delegatee (None = auto-select)
            callback: Optional callback for result
            
        Returns:
            Delegation ID
        """
        # Auto-select delegatee if not specified
        if delegatee_id is None:
            delegatee_id = await self.registry.delegate_task(
                task.__dict__,
                delegator_id,
                task.required_capabilities,
            )
            
            if not delegatee_id:
                raise RuntimeError("No capable delegatee found")

        # Check circuit breaker
        if self._is_circuit_open(delegatee_id):
            raise RuntimeError(f"Delegatee {delegatee_id} circuit breaker open")

        # Create contract
        delegation_id = f"del_{uuid.uuid4().hex[:12]}"
        contract = DelegationContract(
            delegation_id=delegation_id,
            task=task,
            delegator_id=delegator_id,
            delegatee_id=delegatee_id,
            status=DelegationStatus.ASSIGNED,
            assigned_at=datetime.now().timestamp(),
            metadata={"retries": 0},
        )

        self._contracts[delegation_id] = contract

        if callback:
            self._pending_callbacks[delegation_id].append(callback)

        # Send delegation message
        await self._send_delegation_message(contract)

        # Start timeout monitor
        asyncio.create_task(self._monitor_delegation(delegation_id))

        logger.info(f"Delegated task {task.task_id} to {delegatee_id} (delegation: {delegation_id})")
        return delegation_id

    async def _send_delegation_message(self, contract: DelegationContract) -> None:
        """Send delegation message via message broker"""
        message = {
            "type": "delegation_request",
            "delegation_id": contract.delegation_id,
            "task": {
                "task_id": contract.task.task_id,
                "description": contract.task.description,
                "required_capabilities": contract.task.required_capabilities,
                "parameters": contract.task.parameters,
                "priority": contract.task.priority.value,
                "deadline": contract.task.deadline,
                "metadata": contract.task.metadata,
            },
            "delegator_id": contract.delegator_id,
            "timestamp": datetime.now().timestamp(),
        }

        await self.broker.publish(f"agent.{contract.delegatee_id}.delegations", message)
        contract.status = DelegationStatus.IN_PROGRESS
        contract.started_at = datetime.now().timestamp()

    async def _monitor_delegation(self, delegation_id: str) -> None:
        """Monitor delegation for timeout"""
        contract = self._contracts.get(delegation_id)
        if not contract:
            return

        deadline = contract.task.deadline or (contract.created_at + self.default_timeout)
        
        while datetime.now().timestamp() < deadline:
            await asyncio.sleep(5)
            contract = self._contracts.get(delegation_id)
            if not contract or contract.status in (DelegationStatus.COMPLETED, DelegationStatus.FAILED, DelegationStatus.CANCELLED):
                return

        # Timeout
        await self._handle_timeout(delegation_id)

    async def _handle_timeout(self, delegation_id: str) -> None:
        """Handle delegation timeout"""
        contract = self._contracts.get(delegation_id)
        if not contract or contract.status not in (DelegationStatus.ASSIGNED, DelegationStatus.IN_PROGRESS):
            return

        contract.status = DelegationStatus.TIMEOUT
        contract.error = "Delegation timeout"
        contract.completed_at = datetime.now().timestamp()

        await self._notify_completion(contract)
        self._record_failure(contract.delegatee_id)

        logger.warning(f"Delegation {delegation_id} timed out")

    async def handle_delegation_response(
        self,
        delegatee_id: str,
        delegation_id: str,
        result: Any = None,
        error: Optional[str] = None,
        progress: Optional[float] = None,
    ) -> None:
        """
        Handle response from delegatee.
        
        Called by message broker when delegatee responds.
        """
        contract = self._contracts.get(delegation_id)
        if not contract:
            logger.warning(f"Unknown delegation ID: {delegation_id}")
            return

        if contract.delegatee_id != delegatee_id:
            logger.warning(f"Delegatee mismatch: expected {contract.delegatee_id}, got {delegatee_id}")
            return

        if progress is not None:
            contract.progress = progress
            return

        contract.completed_at = datetime.now().timestamp()
        contract.result = result
        contract.error = error

        if error:
            contract.status = DelegationStatus.FAILED
            self._record_failure(delegatee_id)
            
            # Retry logic
            if contract.metadata.get("retries", 0) < self.max_retries:
                contract.metadata["retries"] += 1
                logger.info(f"Retrying delegation {delegation_id} (attempt {contract.metadata['retries']})")
                await self._retry_delegation(contract)
                return
        else:
            contract.status = DelegationStatus.COMPLETED
            self._record_success(delegatee_id, contract.completed_at - contract.started_at)

        await self._notify_completion(contract)

    async def _retry_delegation(self, contract: DelegationContract) -> None:
        """Retry delegation with same or different delegatee"""
        contract.status = DelegationStatus.ASSIGNED
        contract.assigned_at = datetime.now().timestamp()
        contract.started_at = None
        contract.result = None
        contract.error = None
        contract.progress = 0.0

        # Could select different delegatee here
        await self._send_delegation_message(contract)
        asyncio.create_task(self._monitor_delegation(contract.delegation_id))

    async def _notify_completion(self, contract: DelegationContract) -> None:
        """Notify delegator and callbacks of completion"""
        result = DelegationResult(
            delegation_id=contract.delegation_id,
            success=contract.status == DelegationStatus.COMPLETED,
            result=contract.result,
            error=contract.error,
            execution_time=contract.completed_at - contract.started_at if contract.started_at else 0,
            delegatee_id=contract.delegatee_id,
        )

        # Send response to delegator
        await self.broker.publish(f"agent.{contract.delegator_id}.delegation_results", {
            "type": "delegation_result",
            "delegation_id": contract.delegation_id,
            "task_id": contract.task.task_id,
            "success": result.success,
            "result": result.result,
            "error": result.error,
            "execution_time": result.execution_time,
        })

        # Call callbacks
        for callback in self._pending_callbacks.get(contract.delegation_id, []):
            try:
                await callback(result)
            except Exception as e:
                logger.error(f"Delegation callback error: {e}")

        self._pending_callbacks.pop(contract.delegation_id, None)

    def _record_success(self, delegatee_id: str, execution_time: float) -> None:
        """Record successful delegation for delegatee stats"""
        stats = self._delegatee_stats[delegatee_id]
        stats["success_count"] += 1
        n = stats["success_count"] + stats["failure_count"]
        stats["avg_execution_time"] = (
            (stats["avg_execution_time"] * (n - 1) + execution_time) / n
        )

    def _record_failure(self, delegatee_id: str) -> None:
        """Record failed delegation for delegatee stats"""
        stats = self._delegatee_stats[delegatee_id]
        stats["failure_count"] += 1
        
        # Open circuit breaker if failure rate too high
        total = stats["success_count"] + stats["failure_count"]
        if total >= 5 and stats["failure_count"] / total > 0.5:
            stats["circuit_open"] = True
            stats["circuit_open_until"] = datetime.now().timestamp() + 600  # 10 min
            logger.warning(f"Circuit breaker opened for delegatee {delegatee_id}")

    def _is_circuit_open(self, delegatee_id: str) -> bool:
        """Check if circuit breaker is open for delegatee"""
        stats = self._delegatee_stats[delegatee_id]
        if stats["circuit_open"]:
            if datetime.now().timestamp() > stats["circuit_open_until"]:
                stats["circuit_open"] = False
                stats["failure_count"] = 0  # Reset after cooldown
                return False
            return True
        return False

    async def cancel_delegation(self, delegation_id: str, reason: str = "Cancelled by delegator") -> bool:
        """Cancel a pending delegation"""
        contract = self._contracts.get(delegation_id)
        if not contract or contract.status in (DelegationStatus.COMPLETED, DelegationStatus.FAILED, DelegationStatus.CANCELLED):
            return False

        contract.status = DelegationStatus.CANCELLED
        contract.error = reason
        contract.completed_at = datetime.now().timestamp()

        # Notify delegatee
        await self.broker.publish(f"agent.{contract.delegatee_id}.delegations", {
            "type": "delegation_cancelled",
            "delegation_id": delegation_id,
            "reason": reason,
        })

        await self._notify_completion(contract)
        return True

    def get_delegation_status(self, delegation_id: str) -> Optional[DelegationContract]:
        """Get delegation contract status"""
        return self._contracts.get(delegation_id)

    def get_delegations_by_delegator(self, delegator_id: str) -> List[DelegationContract]:
        """Get all delegations by a delegator"""
        return [c for c in self._contracts.values() if c.delegator_id == delegator_id]

    def get_delegations_by_delegatee(self, delegatee_id: str) -> List[DelegationContract]:
        """Get all delegations to a delegatee"""
        return [c for c in self._contracts.values() if c.delegatee_id == delegatee_id]

    def get_delegatee_stats(self, delegatee_id: str) -> Dict[str, Any]:
        """Get delegatee performance statistics"""
        stats = self._delegatee_stats[delegatee_id]
        total = stats["success_count"] + stats["failure_count"]
        return {
            "delegatee_id": delegatee_id,
            "success_count": stats["success_count"],
            "failure_count": stats["failure_count"],
            "success_rate": stats["success_count"] / total if total > 0 else 0,
            "avg_execution_time": stats["avg_execution_time"],
            "circuit_open": stats["circuit_open"],
        }


class ParallelDelegationManager:
    """
    Manages parallel delegation to multiple agents with result aggregation.
    """

    def __init__(self, protocol: DelegationProtocol):
        self.protocol = protocol

    async def delegate_parallel(
        self,
        tasks: List[DelegationTask],
        delegator_id: str,
        delegatee_ids: Optional[List[str]] = None,
        aggregation: str = "all",  # "all", "first", "majority"
        timeout: Optional[int] = None,
    ) -> List[DelegationResult]:
        """
        Delegate multiple tasks in parallel.
        
        Args:
            tasks: List of tasks to delegate
            delegator_id: Delegating agent
            delegatee_ids: Specific delegatees (must match tasks length)
            aggregation: How to aggregate results
            timeout: Overall timeout
            
        Returns:
            List of delegation results
        """
        if delegatee_ids and len(delegatee_ids) != len(tasks):
            raise ValueError("delegatee_ids length must match tasks length")

        # Start all delegations
        delegation_ids = []
        for i, task in enumerate(tasks):
            delegatee = delegatee_ids[i] if delegatee_ids else None
            del_id = await self.protocol.delegate(task, delegator_id, delegatee)
            delegation_ids.append(del_id)

        # Wait for results
        results = []
        completed = set()
        start_time = datetime.now().timestamp()
        deadline = start_time + (timeout or self.protocol.default_timeout)

        while len(completed) < len(delegation_ids):
            if datetime.now().timestamp() > deadline:
                # Cancel remaining
                for del_id in delegation_ids:
                    if del_id not in completed:
                        await self.protocol.cancel_delegation(del_id, "Parallel delegation timeout")
                break

            await asyncio.sleep(0.5)
            
            for del_id in delegation_ids:
                if del_id in completed:
                    continue
                contract = self.protocol.get_delegation_status(del_id)
                if contract and contract.status in (DelegationStatus.COMPLETED, DelegationStatus.FAILED, DelegationStatus.CANCELLED, DelegationStatus.TIMEOUT):
                    completed.add(del_id)
                    results.append(DelegationResult(
                        delegation_id=contract.delegation_id,
                        success=contract.status == DelegationStatus.COMPLETED,
                        result=contract.result,
                        error=contract.error,
                        execution_time=contract.completed_at - contract.started_at if contract.started_at else 0,
                        delegatee_id=contract.delegatee_id,
                    ))

            # Early termination for "first" aggregation
            if aggregation == "first" and results:
                break

        return results

    async def delegate_map_reduce(
        self,
        task_template: DelegationTask,
        data_partitions: List[Any],
        delegator_id: str,
        reduce_func: Callable[[List[Any]], Any],
    ) -> Any:
        """
        Map-reduce style delegation: partition data, delegate map tasks, reduce results.
        
        Args:
            task_template: Base task (parameters will be updated with partition)
            data_partitions: List of data partitions
            delegator_id: Delegating agent
            reduce_func: Function to aggregate results
            
        Returns:
            Reduced result
        """
        tasks = []
        for i, partition in enumerate(data_partitions):
            task = DelegationTask(
                task_id=f"{task_template.task_id}_map_{i}",
                description=f"{task_template.description} (partition {i})",
                required_capabilities=task_template.required_capabilities,
                parameters={**task_template.parameters, "partition": partition, "partition_index": i},
                priority=task_template.priority,
            )
            tasks.append(task)

        results = await self.delegate_parallel(tasks, delegator_id, aggregation="all")
        
        # Extract successful results
        successful_results = [r.result for r in results if r.success]
        
        if not successful_results:
            raise RuntimeError("All map tasks failed")

        return reduce_func(successful_results)