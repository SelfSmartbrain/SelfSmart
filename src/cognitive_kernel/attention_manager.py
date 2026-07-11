"""
Attention Manager - Manages cognitive attention allocation

The AttentionManager is responsible for:
- Allocating attention to different cognitive tasks
- Detecting salient information
- Managing focus and distraction
- Prioritizing cognitive resources
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import math


logger = logging.getLogger(__name__)


class AttentionLevel(Enum):
    """Levels of cognitive attention"""
    NONE = 0.0
    LOW = 0.25
    MEDIUM = 0.5
    HIGH = 0.75
    FOCUSED = 1.0


@dataclass
class AttentionRequest:
    """A request for cognitive attention"""
    task_id: str
    priority: float
    timestamp: float
    duration: float = 10.0
    required_level: AttentionLevel = AttentionLevel.MEDIUM


@dataclass
class AttentionAllocation:
    """Result of attention allocation"""
    task_id: str
    allocated_attention: float
    memory_limit: int
    reasoning_depth: float
    consolidate_memory: bool
    timestamp: float


class AttentionManager:
    """
    Manages cognitive attention allocation.
    
    Similar to biological attention, this system decides:
    - What deserves thinking?
    - What deserves memory?
    - What deserves action?
    """
    
    def __init__(self, kernel: Any, max_attention: float = 1.0):
        self.kernel = kernel
        self.max_attention = max_attention
        self.current_attention = max_attention
        
        # Active attention allocations
        self._active_allocations: Dict[str, AttentionAllocation] = {}
        self._attention_requests: List[AttentionRequest] = []
        self._lock = asyncio.Lock()
        
        # Attention history for learning
        self._attention_history: List[Dict[str, Any]] = []
        
        # Salience detection parameters
        self._salience_threshold = 0.5
        self._novelty_boost = 0.3
        self._recency_decay = 0.95
    
    async def initialize(self) -> None:
        """Initialize the attention manager"""
        logger.info("AttentionManager initialized")
    
    async def shutdown(self) -> None:
        """Shutdown the attention manager"""
        logger.info("AttentionManager shutdown complete")
    
    async def acquire_focus(
        self,
        task_id: str,
        priority: float,
        duration: float = 10.0,
    ) -> bool:
        """
        Acquire focused attention for a task.
        
        Args:
            task_id: Unique identifier for the task
            priority: Task priority (0.0 to 1.0)
            duration: Duration of focus in seconds
            
        Returns:
            True if focus was acquired, False otherwise
        """
        async with self._lock:
            if self.current_attention >= priority:
                self.current_attention -= priority
                self._active_allocations[task_id] = AttentionAllocation(
                    task_id=task_id,
                    allocated_attention=priority,
                    memory_limit=10,
                    reasoning_depth=1.0,
                    consolidate_memory=True,
                    timestamp=datetime.now().timestamp(),
                )
                
                # Schedule release
                asyncio.create_task(self._release_focus_after(task_id, priority, duration))
                
                logger.debug(f"Acquired focus for task {task_id} with priority {priority}")
                return True
            else:
                logger.debug(f"Could not acquire focus for task {task_id} - insufficient attention")
                return False
    
    async def _release_focus_after(
        self,
        task_id: str,
        priority: float,
        duration: float,
    ) -> None:
        """Release focus after duration"""
        await asyncio.sleep(duration)
        await self.release_focus(task_id, priority)
    
    async def release_focus(self, task_id: str, priority: float) -> None:
        """Release focused attention for a task"""
        async with self._lock:
            if task_id in self._active_allocations:
                del self._active_allocations[task_id]
                self.current_attention = min(self.max_attention, self.current_attention + priority)
                logger.debug(f"Released focus for task {task_id}")
    
    async def allocate(
        self,
        task_id: str,
        input_data: Dict[str, Any],
        priority: float,
    ) -> Dict[str, Any]:
        """
        Allocate attention resources for a task.
        
        Args:
            task_id: Unique identifier for the task
            input_data: Input data for the task
            priority: Task priority (0.0 to 1.0)
            
        Returns:
            Attention allocation dictionary
        """
        # Calculate salience
        salience = await self._calculate_salience(input_data)
        
        # Determine attention allocation based on priority and salience
        allocated_attention = min(
            self.current_attention,
            priority * (1.0 + salience * 0.5),
        )
        
        # Determine resource allocation based on attention
        memory_limit = int(allocated_attention * 20)  # Up to 20 memories
        reasoning_depth = allocated_attention  # Deeper reasoning for higher attention
        consolidate_memory = allocated_attention > 0.5
        
        allocation = {
            "task_id": task_id,
            "allocated_attention": allocated_attention,
            "salience": salience,
            "memory_limit": memory_limit,
            "reasoning_depth": reasoning_depth,
            "consolidate_memory": consolidate_memory,
            "timestamp": datetime.now().timestamp(),
        }
        
        # Record for learning
        self._attention_history.append(allocation)
        
        return allocation
    
    async def _calculate_salience(self, input_data: Dict[str, Any]) -> float:
        """
        Calculate the salience (importance) of input data.
        
        Factors:
        - Novelty (how new is this information?)
        - Relevance (does it match current goals?)
        - Urgency (is time-sensitive?)
        - Complexity (is it complex enough to warrant attention?)
        """
        salience = 0.0
        
        # Novelty: Check if this is new information
        novelty = await self._calculate_novelty(input_data)
        salience += novelty * self._novelty_boost
        
        # Complexity: More complex inputs get more attention
        complexity = self._calculate_complexity(input_data)
        salience += complexity * 0.3
        
        # Urgency: Time-sensitive inputs get more attention
        urgency = input_data.get("urgency", 0.0)
        salience += urgency * 0.2
        
        # Relevance: Goal-relevant inputs get more attention
        relevance = await self._calculate_relevance(input_data)
        salience += relevance * 0.2
        
        return min(1.0, salience)
    
    async def _calculate_novelty(self, input_data: Dict[str, Any]) -> float:
        """Calculate how novel the input is"""
        # Simplified: check if similar inputs have been seen recently
        # In full implementation, would use semantic similarity with memory
        content = str(input_data)
        
        # Check against recent attention history
        recent_count = sum(
            1 for h in self._attention_history[-10:]
            if content in str(h.get("input_data", ""))
        )
        
        # Less recent = more novel
        novelty = 1.0 - (recent_count * 0.1)
        return max(0.0, novelty)
    
    def _calculate_complexity(self, input_data: Dict[str, Any]) -> float:
        """Calculate the complexity of input"""
        # Simple heuristic: length and nested structure
        content = str(input_data)
        length_factor = min(1.0, len(content) / 1000.0)
        
        # Count nested structures
        nesting = content.count("{") + content.count("[")
        nesting_factor = min(1.0, nesting / 20.0)
        
        return (length_factor + nesting_factor) / 2.0
    
    async def _calculate_relevance(self, input_data: Dict[str, Any]) -> float:
        """Calculate relevance to current goals"""
        # Simplified: check for goal-related keywords
        # In full implementation, would check against active goals and missions
        goal_keywords = ["goal", "objective", "mission", "task", "priority"]
        content = str(input_data).lower()
        
        relevance = sum(1 for kw in goal_keywords if kw in content) / len(goal_keywords)
        return relevance
    
    def get_current_attention(self) -> float:
        """Get current available attention"""
        return self.current_attention
    
    def get_active_allocations(self) -> Dict[str, AttentionAllocation]:
        """Get currently active attention allocations"""
        return self._active_allocations.copy()
