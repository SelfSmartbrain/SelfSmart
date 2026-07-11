"""
Attention Engine - Core attention allocation system

The AttentionEngine is responsible for:
- Allocating cognitive attention to tasks
- Managing attention focus and shifts
- Balancing between different cognitive operations
- Implementing attention mechanisms similar to biological systems
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
import numpy as np


logger = logging.getLogger(__name__)


class AttentionMode(Enum):
    """Modes of attention"""
    FOCUSED = "focused"  # Single task, deep processing
    DISTRIBUTED = "distributed"  # Multiple tasks, shallow processing
    SCANNING = "scanning"  # Monitoring environment
    REFLECTIVE = "reflective"  # Internal processing


@dataclass
class AttentionFocus:
    """Current attention focus"""
    target: str
    intensity: float  # 0.0 to 1.0
    duration: float
    mode: AttentionMode
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class AttentionAllocation:
    """Result of attention allocation"""
    task_id: str
    attention_amount: float
    processing_mode: AttentionMode
    cognitive_resources: Dict[str, float]
    expected_duration: float
    confidence: float


class AttentionEngine:
    """
    Core attention allocation engine.
    
    Implements attention mechanisms similar to biological systems:
    - Bottom-up attention (stimulus-driven)
    - Top-down attention (goal-driven)
    - Attention shifts and focus management
    - Resource allocation based on importance
    """
    
    def __init__(
        self,
        total_attention: float = 1.0,
        min_attention_unit: float = 0.1,
    ):
        self.total_attention = total_attention
        self.min_attention_unit = min_attention_unit
        self.available_attention = total_attention
        
        # Current focus
        self.current_focus: Optional[AttentionFocus] = None
        self.attention_history: List[AttentionFocus] = []
        
        # Active allocations
        self.active_allocations: Dict[str, AttentionAllocation] = {}
        
        # Attention parameters
        self._bottom_up_sensitivity = 0.5
        self._top_down_weight = 0.5
        self._attention_decay = 0.95
        self._shift_threshold = 0.3
        
        # Statistics
        self._allocations_made = 0
        self._attention_shifts = 0
        self._focus_changes = 0
    
    async def initialize(self) -> None:
        """Initialize the attention engine"""
        logger.info("AttentionEngine initialized")
    
    async def allocate_attention(
        self,
        task_id: str,
        stimulus: Dict[str, Any],
        goals: Optional[List[str]] = None,
        required_attention: Optional[float] = None,
    ) -> AttentionAllocation:
        """
        Allocate attention to a task.
        
        Args:
            task_id: Task identifier
            stimulus: Input stimulus/data
            goals: Current goals (for top-down attention)
            required_attention: Required attention amount (optional)
            
        Returns:
            Attention allocation
        """
        # Calculate salience (bottom-up)
        bottom_up_salience = await self._calculate_bottom_up_salience(stimulus)
        
        # Calculate goal relevance (top-down)
        top_down_relevance = await self._calculate_top_down_relevance(
            stimulus, goals or []
        )
        
        # Combine bottom-up and top-down
        combined_importance = (
            self._bottom_up_sensitivity * bottom_up_salience +
            self._top_down_weight * top_down_relevance
        )
        
        # Determine attention amount
        if required_attention is not None:
            attention_amount = min(required_attention, self.available_attention)
        else:
            attention_amount = min(
                combined_importance * self.total_attention,
                self.available_attention,
            )
        
        # Ensure minimum attention unit
        if attention_amount < self.min_attention_unit and attention_amount > 0:
            attention_amount = self.min_attention_unit
        
        # Determine processing mode
        mode = self._determine_processing_mode(attention_amount, stimulus)
        
        # Allocate cognitive resources
        cognitive_resources = self._allocate_resources(attention_amount, mode)
        
        # Create allocation
        allocation = AttentionAllocation(
            task_id=task_id,
            attention_amount=attention_amount,
            processing_mode=mode,
            cognitive_resources=cognitive_resources,
            expected_duration=self._estimate_duration(attention_amount, mode),
            confidence=combined_importance,
        )
        
        # Update state
        self.available_attention -= attention_amount
        self.active_allocations[task_id] = allocation
        self._allocations_made += 1
        
        # Update focus if this is the most important task
        if self.current_focus is None or combined_importance > self._shift_threshold:
            await self._shift_focus(task_id, attention_amount, mode, combined_importance)
        
        logger.debug(
            f"Allocated {attention_amount:.2f} attention to {task_id} "
            f"(mode: {mode.value}, confidence: {combined_importance:.2f})"
        )
        
        return allocation
    
    async def release_attention(self, task_id: str) -> float:
        """
        Release attention from a task.
        
        Args:
            task_id: Task identifier
            
        Returns:
            Amount of attention released
        """
        if task_id not in self.active_allocations:
            return 0.0
        
        allocation = self.active_allocations[task_id]
        released = allocation.attention_amount
        
        self.available_attention += released
        del self.active_allocations[task_id]
        
        logger.debug(f"Released {released:.2f} attention from {task_id}")
        
        return released
    
    async def _calculate_bottom_up_salience(self, stimulus: Dict[str, Any]) -> float:
        """
        Calculate bottom-up salience (stimulus-driven).
        
        Factors:
        - Novelty
        - Intensity
        - Suddenness
        - Contrast
        """
        salience = 0.0
        
        # Novelty: Check if this is new
        novelty = stimulus.get("novelty", 0.5)
        salience += novelty * 0.3
        
        # Intensity: Strength of stimulus
        intensity = stimulus.get("intensity", 0.5)
        salience += intensity * 0.3
        
        # Suddenness: How sudden is this?
        suddenness = stimulus.get("suddenness", 0.0)
        salience += suddenness * 0.2
        
        # Contrast: How different from baseline?
        contrast = stimulus.get("contrast", 0.5)
        salience += contrast * 0.2
        
        return min(1.0, salience)
    
    async def _calculate_top_down_relevance(
        self,
        stimulus: Dict[str, Any],
        goals: List[str],
    ) -> float:
        """
        Calculate top-down relevance (goal-driven).
        
        Factors:
        - Goal alignment
        - Task relevance
        - Strategic importance
        """
        if not goals:
            return 0.3  # Default baseline
        
        relevance = 0.0
        
        # Check goal alignment
        stimulus_text = str(stimulus).lower()
        for goal in goals:
            if goal.lower() in stimulus_text:
                relevance += 0.3
        
        # Normalize by number of goals
        if goals:
            relevance = min(1.0, relevance / len(goals))
        
        # Add strategic importance
        strategic = stimulus.get("strategic_importance", 0.0)
        relevance += strategic * 0.3
        
        return min(1.0, relevance)
    
    def _determine_processing_mode(
        self,
        attention_amount: float,
        stimulus: Dict[str, Any],
    ) -> AttentionMode:
        """Determine the processing mode based on attention and stimulus"""
        if attention_amount > 0.7:
            return AttentionMode.FOCUSED
        elif attention_amount > 0.4:
            return AttentionMode.DISTRIBUTED
        elif stimulus.get("monitoring", False):
            return AttentionMode.SCANNING
        else:
            return AttentionMode.REFLECTIVE
    
    def _allocate_resources(
        self,
        attention_amount: float,
        mode: AttentionMode,
    ) -> Dict[str, float]:
        """Allocate cognitive resources based on attention amount and mode"""
        resources = {
            "working_memory": attention_amount * 0.3,
            "processing_power": attention_amount * 0.4,
            "memory_access": attention_amount * 0.2,
            "reasoning_capacity": attention_amount * 0.1,
        }
        
        # Adjust based on mode
        if mode == AttentionMode.FOCUSED:
            resources["reasoning_capacity"] = attention_amount * 0.3
            resources["working_memory"] = attention_amount * 0.4
        elif mode == AttentionMode.SCANNING:
            resources["processing_power"] = attention_amount * 0.6
            resources["reasoning_capacity"] = 0.05
        
        return resources
    
    def _estimate_duration(
        self,
        attention_amount: float,
        mode: AttentionMode,
    ) -> float:
        """Estimate expected duration of attention allocation"""
        base_duration = 10.0  # seconds
        
        if mode == AttentionMode.FOCUSED:
            return base_duration * 2.0
        elif mode == AttentionMode.SCANNING:
            return base_duration * 0.5
        else:
            return base_duration
    
    async def _shift_focus(
        self,
        target: str,
        intensity: float,
        mode: AttentionMode,
        importance: float,
    ) -> None:
        """Shift attention focus to a new target"""
        if self.current_focus:
            self.attention_history.append(self.current_focus)
        
        self.current_focus = AttentionFocus(
            target=target,
            intensity=intensity,
            duration=self._estimate_duration(intensity, mode),
            mode=mode,
        )
        
        self._focus_changes += 1
        self._attention_shifts += 1
        
        logger.debug(f"Shifted focus to {target} (intensity: {intensity:.2f})")
    
    async def monitor_attention(self) -> Dict[str, Any]:
        """
        Monitor current attention state.
        
        Returns:
            Attention state information
        """
        return {
            "available_attention": self.available_attention,
            "total_attention": self.total_attention,
            "current_focus": {
                "target": self.current_focus.target if self.current_focus else None,
                "intensity": self.current_focus.intensity if self.current_focus else 0.0,
                "mode": self.current_focus.mode.value if self.current_focus else None,
            } if self.current_focus else None,
            "active_allocations": len(self.active_allocations),
            "allocation_details": {
                task_id: {
                    "attention_amount": alloc.attention_amount,
                    "mode": alloc.processing_mode.value,
                    "confidence": alloc.confidence,
                }
                for task_id, alloc in self.active_allocations.items()
            },
        }
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get attention engine metrics"""
        return {
            "allocations_made": self._allocations_made,
            "attention_shifts": self._attention_shifts,
            "focus_changes": self._focus_changes,
            "focus_history_length": len(self.attention_history),
        }
