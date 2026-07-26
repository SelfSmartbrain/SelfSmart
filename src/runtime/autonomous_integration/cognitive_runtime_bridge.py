"""
Cognitive Runtime Bridge - Connects CognitiveKernel with AgentRuntime for autonomous operation.

This bridge enables the cognitive kernel to drive the runtime's execution loop,
allowing continuous autonomous thinking, goal management, and memory consolidation.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Dict, List, Optional, Callable, Awaitable
from contextlib import asynccontextmanager

from src.cognitive_kernel.kernel import CognitiveKernel
from src.cognitive_kernel.scheduler import CognitiveScheduler
from src.runtime.execution_loop import ExecutionLoop, LoopStepResult
from src.runtime.agent_runtime import AgentRuntime
from src.autonomy.objective_manager import Objective, ObjectiveManager
from src.autonomy.progress_tracker import ProgressTracker
from src.memory.memory_fabric import MemoryFabric, MemoryEntry, MemoryType

logger = logging.getLogger(__name__)


class BridgeMode(Enum):
    """Operating modes for the bridge."""
    REACTIVE = "reactive"          # Respond to objectives only
    PROACTIVE = "proactive"        # Set own goals when idle
    CONTINUOUS = "continuous"      # Constant cognitive cycle
    LEARNING = "learning"          # Focus on learning/consolidation


@dataclass
class BridgeConfig:
    """Configuration for the cognitive-runtime bridge."""
    
    # Operating mode
    mode: BridgeMode = BridgeMode.PROACTIVE
    
    # Timing
    cognitive_tick_interval: float = 5.0        # Seconds between cognitive cycles
    idle_threshold: float = 30.0                # Seconds before considered idle
    background_thinking_interval: float = 60.0  # Seconds between background thoughts
    consolidation_interval: float = 300.0       # Seconds between memory consolidation
    
    # Behavior
    auto_create_objectives: bool = True
    max_concurrent_objectives: int = 3
    objective_priority_boost: float = 0.2
    
    # Memory
    consolidation_batch_size: int = 50
    importance_threshold: float = 0.6
    
    # Safety
    max_cognitive_cycles_per_minute: int = 20
    emergency_stop_on_error: bool = True


@dataclass
class CognitiveState:
    """Current state of the cognitive system."""
    mode: BridgeMode = BridgeMode.REACTIVE
    last_cognitive_tick: Optional[datetime] = None
    last_background_thought: Optional[datetime] = None
    last_consolidation: Optional[datetime] = None
    cycles_this_minute: int = 0
    minute_start: datetime = field(default_factory=datetime.utcnow)
    is_thinking: bool = False
    current_objective: Optional[str] = None
    idle_since: Optional[datetime] = None
    error_count: int = 0
    total_thoughts: int = 0
    successful_objectives: int = 0
    failed_objectives: int = 0


class CognitiveRuntimeBridge:
    """
    Bridges the CognitiveKernel with the AgentRuntime for autonomous operation.
    
    This is the "heartbeat" that drives continuous cognitive processing,
    enabling the agent to think, plan, learn, and act autonomously.
    """
    
    def __init__(
        self,
        kernel: CognitiveKernel,
        runtime: AgentRuntime,
        memory_fabric: Optional[MemoryFabric] = None,
        config: Optional[BridgeConfig] = None,
    ):
        self.kernel = kernel
        self.runtime = runtime
        self.memory_fabric = memory_fabric
        self.config = config or BridgeConfig()
        
        # State
        self.state = CognitiveState()
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # Components (lazy initialized)
        self._scheduler: Optional[CognitiveScheduler] = None
        self._background_thinker = None
        self._goal_reflector = None
        self._memory_consolidator = None
        
        # Callbacks
        self._on_objective_created: List[Callable[[Objective], Awaitable[None]]] = []
        self._on_thought_complete: List[Callable[[Dict[str, Any]], Awaitable[None]]] = []
        self._on_error: List[Callable[[Exception], Awaitable[None]]] = []
        
        # Statistics
        self._stats = {
            "cognitive_ticks": 0,
            "background_thoughts": 0,
            "consolidations_run": 0,
            "objectives_auto_created": 0,
            "errors": 0,
        }
    
    async def initialize(self) -> None:
        """Initialize all components."""
        logger.info("Initializing CognitiveRuntimeBridge")
        
        # Initialize kernel if needed
        if hasattr(self.kernel, 'initialize') and not getattr(self.kernel, '_initialized', False):
            await self.kernel.initialize()
        
        # Initialize runtime
        if not self.runtime.initialized:
            await self.runtime.initialize()
        
        # Initialize cognitive scheduler
        self._scheduler = self.kernel.cognitive_scheduler
        if self._scheduler and hasattr(self._scheduler, 'initialize'):
            await self._scheduler.initialize()
        
        # Initialize sub-components
        await self._init_components()
        
        # Wire kernel to execution loop
        self.runtime.execution_loop.cognitive_kernel = self.kernel
        
        logger.info("CognitiveRuntimeBridge initialized")
    
    async def _init_components(self) -> None:
        """Initialize background components."""
        from .background_thinker import BackgroundThinker, ThinkingConfig
        from .goal_reflector import GoalReflector, ReflectionConfig
        from .memory_consolidator import MemoryConsolidator, ConsolidationConfig
        
        # Background thinker
        self._background_thinker = BackgroundThinker(
            kernel=self.kernel,
            memory_fabric=self.memory_fabric,
            config=ThinkingConfig(
                interval=self.config.background_thinking_interval,
                idle_threshold=self.config.idle_threshold,
            ),
        )
        
        # Goal reflector
        self._goal_reflector = GoalReflector(
            kernel=self.kernel,
            objective_manager=self.runtime.objective_manager,
            memory_fabric=self.memory_fabric,
            config=ReflectionConfig(
                auto_create=self.config.auto_create_objectives,
                max_concurrent=self.config.max_concurrent_objectives,
            ),
        )
        
        # Memory consolidator
        if self.memory_fabric:
            self._memory_consolidator = MemoryConsolidator(
                memory_fabric=self.memory_fabric,
                kernel=self.kernel,
                config=ConsolidationConfig(
                    interval=self.config.consolidation_interval,
                    batch_size=self.config.consolidation_batch_size,
                    importance_threshold=self.config.importance_threshold,
                ),
            )
    
    async def start(self) -> None:
        """Start autonomous cognitive operation."""
        if self._running:
            logger.warning("Bridge already running")
            return
        
        self._running = True
        logger.info(f"Starting CognitiveRuntimeBridge in {self.config.mode.value} mode")
        
        # Start background tasks
        self._tasks = [
            asyncio.create_task(self._cognitive_tick_loop()),
            asyncio.create_task(self._background_thinking_loop()),
            asyncio.create_task(self._goal_reflection_loop()),
        ]
        
        if self._memory_consolidator:
            self._tasks.append(
                asyncio.create_task(self._memory_consolidation_loop())
            )
        
        # Start the runtime execution loop
        if self.config.mode in (BridgeMode.PROACTIVE, BridgeMode.CONTINUOUS):
            self._tasks.append(
                asyncio.create_task(self.runtime.execution_loop.run())
            )
    
    async def stop(self) -> None:
        """Stop autonomous operation."""
        self._running = False
        
        # Cancel all tasks
        for task in self._tasks:
            task.cancel()
        
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)
        
        self._tasks = []
        
        # Stop runtime
        self.runtime.execution_loop.stop()
        
        # Shutdown components
        if self._scheduler and hasattr(self._scheduler, 'shutdown'):
            await self._scheduler.shutdown()
        
        logger.info("CognitiveRuntimeBridge stopped")
    
    async def _cognitive_tick_loop(self) -> None:
        """Main cognitive tick loop - drives the kernel's processing cycle."""
        while self._running:
            try:
                # Rate limiting
                if not self._check_rate_limit():
                    await asyncio.sleep(1.0)
                    continue
                
                self.state.is_thinking = True
                self.state.last_cognitive_tick = datetime.utcnow()
                self._stats["cognitive_ticks"] += 1
                
                # Process any pending objectives through kernel
                await self._process_kernel_tick()
                
                self.state.is_thinking = False
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.state.error_count += 1
                self._stats["errors"] += 1
                logger.error(f"Error in cognitive tick: {e}")
                await self._handle_error(e)
                
                if self.config.emergency_stop_on_error:
                    self._running = False
                    break
            
            await asyncio.sleep(self.config.cognitive_tick_interval)
    
    def _check_rate_limit(self) -> bool:
        """Check if we're within rate limits."""
        now = datetime.utcnow()
        if (now - self.state.minute_start).total_seconds() >= 60:
            self.state.cycles_this_minute = 0
            self.state.minute_start = now
        
        if self.state.cycles_this_minute >= self.config.max_cognitive_cycles_per_minute:
            return False
        
        self.state.cycles_this_minute += 1
        return True
    
    async def _process_kernel_tick(self) -> None:
        """Process a single kernel tick."""
        # Get current objective from runtime
        objective = self.runtime.objective_manager.get_current_objective()
        
        if objective:
            self.state.current_objective = objective.objective_id
            self.state.idle_since = None
            
            # Process through kernel
            try:
                result = await self.kernel.process(
                    {
                        "type": "objective_tick",
                        "objective": objective.to_dict(),
                        "context": {"mode": self.config.mode.value},
                    },
                    priority=objective.priority,
                    require_attention=objective.priority >= 0.8,
                )
                
                # Update progress
                await self.runtime.progress_tracker.track_progress(
                    objective,
                    "processing",
                    "Cognitive tick processed",
                    result,
                )
                
            except Exception as e:
                logger.error(f"Kernel processing failed: {e}")
                await self.runtime.progress_tracker.track_progress(
                    objective,
                    "error",
                    str(e),
                    {"error": str(e)},
                )
        else:
            # No objective - mark as idle
            if self.state.idle_since is None:
                self.state.idle_since = datetime.utcnow()
            self.state.current_objective = None
    
    async def _background_thinking_loop(self) -> None:
        """Background thinking when idle."""
        while self._running:
            try:
                await asyncio.sleep(self.config.background_thinking_interval)
                
                # Check if idle
                if (self.state.idle_since and 
                    (datetime.utcnow() - self.state.idle_since).total_seconds() >= self.config.idle_threshold):
                    
                    if self._background_thinker:
                        await self._background_thinker.think()
                        self._stats["background_thoughts"] += 1
                        self.state.last_background_thought = datetime.utcnow()
                        self.state.total_thoughts += 1
                        
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background thinking error: {e}")
                await self._handle_error(e)
    
    async def _goal_reflection_loop(self) -> None:
        """Reflect on goals and create new objectives when appropriate."""
        while self._running:
            try:
                await asyncio.sleep(30.0)  # Check every 30 seconds
                
                if self._goal_reflector and self.config.mode == BridgeMode.PROACTIVE:
                    created = await self._goal_reflector.reflect_and_create()
                    if created:
                        self._stats["objectives_auto_created"] += len(created)
                        for obj in created:
                            await self._notify_objective_created(obj)
                            
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Goal reflection error: {e}")
                await self._handle_error(e)
    
    async def _memory_consolidation_loop(self) -> None:
        """Periodic memory consolidation."""
        while self._running:
            try:
                await asyncio.sleep(self.config.consolidation_interval)
                
                if self._memory_consolidator:
                    count = await self._memory_consolidator.consolidate()
                    self._stats["consolidations_run"] += 1
                    self.state.last_consolidation = datetime.utcnow()
                    logger.info(f"Memory consolidation: {count} memories processed")
                    
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Memory consolidation error: {e}")
                await self._handle_error(e)
    
    async def _notify_objective_created(self, objective: Objective) -> None:
        """Notify callbacks of new objective."""
        for callback in self._on_objective_created:
            try:
                await callback(objective)
            except Exception as e:
                logger.error(f"Objective created callback failed: {e}")
    
    async def _handle_error(self, error: Exception) -> None:
        """Handle errors with callbacks."""
        for callback in self._on_error:
            try:
                await callback(error)
            except Exception as e:
                logger.error(f"Error callback failed: {e}")
    
    # Public API
    
    def on_objective_created(self, callback: Callable[[Objective], Awaitable[None]]) -> None:
        """Register callback for when new objectives are created."""
        self._on_objective_created.append(callback)
    
    def on_thought_complete(self, callback: Callable[[Dict[str, Any]], Awaitable[None]]) -> None:
        """Register callback for when background thoughts complete."""
        self._on_thought_complete.append(callback)
    
    def on_error(self, callback: Callable[[Exception], Awaitable[None]]) -> None:
        """Register error callback."""
        self._on_error.append(callback)
    
    def get_state(self) -> CognitiveState:
        """Get current cognitive state."""
        return self.state
    
    def get_stats(self) -> Dict[str, Any]:
        """Get bridge statistics."""
        return {
            **self._stats,
            "state": {
                "mode": self.state.mode.value,
                "is_thinking": self.state.is_thinking,
                "current_objective": self.state.current_objective,
                "idle_seconds": (
                    (datetime.utcnow() - self.state.idle_since).total_seconds()
                    if self.state.idle_since else None
                ),
                "error_count": self.state.error_count,
                "total_thoughts": self.state.total_thoughts,
                "successful_objectives": self.state.successful_objectives,
                "failed_objectives": self.state.failed_objectives,
            },
            "uptime_seconds": (
                datetime.utcnow() - self.state.minute_start
            ).total_seconds(),
        }
    
    async def trigger_thought(self, prompt: str, priority: float = 0.5) -> Dict[str, Any]:
        """Manually trigger a cognitive cycle with a prompt."""
        return await self.kernel.process(
            {"type": "manual_thought", "query": prompt},
            priority=priority,
        )
    
    async def set_mode(self, mode: BridgeMode) -> None:
        """Change operating mode."""
        old_mode = self.state.mode
        self.state.mode = mode
        self.config.mode = mode
        logger.info(f"Bridge mode changed: {old_mode.value} -> {mode.value}")
        
        # Restart loops if needed
        if mode == BridgeMode.CONTINUOUS and not self._running:
            await self.start()


@asynccontextmanager
async def create_bridge(
    kernel: CognitiveKernel,
    runtime: AgentRuntime,
    memory_fabric: Optional[MemoryFabric] = None,
    config: Optional[BridgeConfig] = None,
) -> CognitiveRuntimeBridge:
    """Context manager for creating and managing bridge lifecycle."""
    bridge = CognitiveRuntimeBridge(kernel, runtime, memory_fabric, config)
    await bridge.initialize()
    try:
        await bridge.start()
        yield bridge
    finally:
        await bridge.stop()