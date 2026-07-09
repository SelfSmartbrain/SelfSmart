"""
Cognitive Kernel - The Central Brain

The CognitiveKernel is the central orchestrator for all cognitive operations in ModelX.
It coordinates between memory, reasoning, attention, and agent communication.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum

from .scheduler import CognitiveScheduler
from .attention_manager import AttentionManager
from .cognitive_bus import CognitiveBus
from .context_manager import ContextManager
from ..memory.memory_fabric import MemoryFabric


logger = logging.getLogger(__name__)


class CognitiveState(Enum):
    """States of the cognitive kernel"""
    IDLE = "idle"
    ACTIVE = "active"
    FOCUSED = "focused"
    OVERLOADED = "overloaded"
    CONSOLIDATING = "consolidating"


@dataclass
class CognitiveMetrics:
    """Metrics for cognitive performance"""
    total_operations: int = 0
    successful_operations: int = 0
    failed_operations: int = 0
    attention_cycles: int = 0
    memory_consolidations: int = 0
    reasoning_depth: float = 0.0
    current_load: float = 0.0
    
    @property
    def success_rate(self) -> float:
        if self.total_operations == 0:
            return 0.0
        return self.successful_operations / self.total_operations


class CognitiveKernel:
    """
    The central cognitive kernel for ModelX.
    
    Responsibilities:
    - Global context management
    - Attention allocation
    - Memory prioritization
    - Agent coordination
    - Cognitive resource scheduling
    """
    
    def __init__(
        self,
        memory_fabric: Optional[MemoryFabric] = None,
        max_concurrent_tasks: int = 10,
        attention_threshold: float = 0.7,
    ):
        self.state = CognitiveState.IDLE
        self.metrics = CognitiveMetrics()
        self.max_concurrent_tasks = max_concurrent_tasks
        self.attention_threshold = attention_threshold
        
        # Initialize subsystems
        self.scheduler = CognitiveScheduler(kernel=self)
        self.attention_manager = AttentionManager(kernel=self)
        self.cognitive_bus = CognitiveBus(kernel=self)
        self.context_manager = ContextManager(kernel=self)
        self.memory_fabric = memory_fabric
        self.reasoning_hub = None
        
        # Active cognitive operations
        self._active_tasks: Set[str] = set()
        self._task_queue: asyncio.Queue = asyncio.Queue()
        self._lock = asyncio.Lock()
        
        logger.info("CognitiveKernel initialized")
    
    async def initialize(self) -> None:
        """Initialize all cognitive subsystems"""
        logger.info("Initializing CognitiveKernel subsystems")

        await self.cognitive_bus.initialize()
        await self.attention_manager.initialize()
        await self.context_manager.initialize()

        if self.memory_fabric:
            await self.memory_fabric.initialize()

        # Initialize ReasoningHub — await it fully so it is ready before first process() call
        from src.reasoning.reasoning_hub import ReasoningHub
        self.reasoning_hub = ReasoningHub()
        await self.reasoning_hub.initialize()

        # Start the cognitive scheduler as a background task
        asyncio.create_task(self.scheduler.run(), name="cognitive-scheduler")

        self.state = CognitiveState.ACTIVE
        logger.info("CognitiveKernel initialization complete")
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the cognitive kernel"""
        logger.info("Shutting down CognitiveKernel")
        
        self.state = CognitiveState.CONSOLIDATING
        
        # Wait for active tasks to complete
        await self._wait_for_tasks()
        
        # Shutdown subsystems
        await self.cognitive_bus.shutdown()
        await self.attention_manager.shutdown()
        await self.context_manager.shutdown()
        
        self.state = CognitiveState.IDLE
        logger.info("CognitiveKernel shutdown complete")
    
    async def process(
        self,
        input_data: Dict[str, Any],
        priority: float = 0.5,
        require_attention: bool = False,
    ) -> Dict[str, Any]:
        """
        Process input through the cognitive pipeline.
        
        Args:
            input_data: Input data to process
            priority: Task priority (0.0 to 1.0)
            require_attention: Whether this task requires focused attention
            
        Returns:
            Processing result
        """
        task_id = f"task_{datetime.now().timestamp()}"
        
        # Check if we can accept this task
        if len(self._active_tasks) >= self.max_concurrent_tasks:
            logger.warning(f"Kernel overloaded, queuing task {task_id}")
            self.state = CognitiveState.OVERLOADED
            await self._task_queue.put((task_id, input_data, priority, require_attention))
        
        # Acquire attention if required
        if require_attention:
            await self.attention_manager.acquire_focus(task_id, priority)
            self.state = CognitiveState.FOCUSED
        
        try:
            self._active_tasks.add(task_id)
            self.metrics.total_operations += 1
            
            # Update context
            await self.context_manager.update(input_data)
            
            # Determine attention allocation
            attention_allocation = await self.attention_manager.allocate(
                task_id, input_data, priority
            )
            
            # Process through cognitive pipeline
            result = await self._cognitive_pipeline(
                input_data, attention_allocation
            )
            
            # Consolidate memory if needed
            if attention_allocation.get("consolidate_memory", False):
                await self._consolidate_memory(input_data, result)
            
            self.metrics.successful_operations += 1
            return result
            
        except Exception as e:
            logger.error(f"Error processing task {task_id}: {e}")
            self.metrics.failed_operations += 1
            raise
        finally:
            self._active_tasks.discard(task_id)
            
            if require_attention:
                await self.attention_manager.release_focus(task_id)
            
            if len(self._active_tasks) < self.max_concurrent_tasks:
                self.state = CognitiveState.ACTIVE
    
    async def _cognitive_pipeline(
        self,
        input_data: Dict[str, Any],
        attention_allocation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Execute the cognitive pipeline.
        
        Pipeline stages:
        1. Context retrieval
        2. Memory query
        3. Reasoning
        4. Decision making
        5. Action execution
        """
        result = {"input": input_data, "stages": []}
        
        # Stage 1: Context retrieval
        context = await self.context_manager.get_relevant_context(input_data)
        result["context"] = context
        result["stages"].append("context_retrieval")
        
        # Stage 2: Memory query
        if self.memory_fabric:
            memories = await self.memory_fabric.query(
                input_data.get("query", str(input_data)),
                limit=attention_allocation.get("memory_limit", 5),
            )
            result["memories"] = memories
            result["stages"].append("memory_query")
        
        # Stage 3: Emit cognitive event
        await self.cognitive_bus.emit(
            event_type="cognitive_processing",
            data={
                "input": input_data,
                "context": context,
                "attention": attention_allocation,
            },
        )
        
        # Stage 4: Decision making (placeholder - will be enhanced by reasoning engine)
        decision = await self._make_decision(input_data, context, attention_allocation)
        result["decision"] = decision
        result["stages"].append("decision_making")
        
        return result
    
    async def _make_decision(
        self,
        input_data: Dict[str, Any],
        context: Dict[str, Any],
        attention_allocation: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Delegate decision-making to the ReasoningHub.

        Falls back to a safe default if the hub is not available.
        """
        if self.reasoning_hub is None:
            # Hub not yet initialized — return a safe, logged default
            logger.warning("ReasoningHub not initialized; using fallback decision")
            return {"action": "process", "confidence": 0.5, "reasoning": "hub-not-ready"}

        from src.reasoning.reasoning_hub import ReasoningRequest

        query = (
            input_data.get("query")
            or input_data.get("objective", {}).get("description", "")
            or str(input_data)
        )
        # Use attention-based timeout: high attention → slower/deeper System 2
        timeout = 30.0 if attention_allocation.get("reasoning_depth", 0.5) > 0.6 else 5.0

        request = ReasoningRequest(
            query=query,
            context={**context, "input": input_data, "attention": attention_allocation},
            timeout=timeout,
        )
        try:
            result = await self.reasoning_hub.reason(request)
            return {
                "action": "process",
                "confidence": result.confidence,
                "reasoning": result.conclusion,
                "mode": result.mode_used.value,
                "steps": result.reasoning_steps,
            }
        except Exception as exc:
            logger.error(f"ReasoningHub failed: {exc}")
            return {"action": "process", "confidence": 0.5, "reasoning": str(exc)}
    
    async def _consolidate_memory(
        self,
        input_data: Dict[str, Any],
        result: Dict[str, Any],
    ) -> None:
        """Consolidate important information into memory"""
        if not self.memory_fabric:
            return
        
        # Create memory entry
        memory_entry = {
            "content": str(input_data),
            "context": result.get("context", {}),
            "outcome": result.get("decision", {}),
            "timestamp": datetime.now().isoformat(),
            "importance": result.get("decision", {}).get("confidence", 0.5),
        }
        
        await self.memory_fabric.store(memory_entry)
        self.metrics.memory_consolidations += 1
    
    async def _wait_for_tasks(self, timeout: float = 30.0) -> None:
        """Wait for active tasks to complete"""
        start = datetime.now()
        while self._active_tasks:
            if (datetime.now() - start).total_seconds() > timeout:
                logger.warning(f"Timeout waiting for {len(self._active_tasks)} tasks")
                break
            await asyncio.sleep(0.1)
    
    def get_metrics(self) -> CognitiveMetrics:
        """Get current cognitive metrics"""
        self.metrics.current_load = len(self._active_tasks) / self.max_concurrent_tasks
        return self.metrics
    
    def get_state(self) -> CognitiveState:
        """Get current cognitive state"""
        return self.state
