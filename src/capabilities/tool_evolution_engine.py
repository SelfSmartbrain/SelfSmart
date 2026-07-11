from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)

class ToolExecutionRecord(BaseModel):
    model_config = {"from_attributes": True}
    
    execution_id: str
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    success: bool
    latency_ms: float
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

class ToolStats(BaseModel):
    model_config = {"from_attributes": True}
    
    total_executions: int = 0
    success_count: int = 0
    failure_count: int = 0
    average_latency_ms: float = 0.0
    recent_records: List[ToolExecutionRecord] = Field(default_factory=list)
    version: str = "1.0.0"
    status: str = "active" # active, deprecated, evolving

class ToolEvolutionEngine:
    """
    Engine to track tool success rates, compare versions, and automatically deprecate
    or trigger upgrades for tools based on their execution history.
    """
    
    def __init__(self, history_limit: int = 100, success_threshold: float = 0.85):
        self.history_limit = history_limit
        self.success_threshold = success_threshold
        self.tool_stats: Dict[str, ToolStats] = {}
        
    def _ensure_tool(self, tool_name: str) -> None:
        if tool_name not in self.tool_stats:
            self.tool_stats[tool_name] = ToolStats()

    async def record_execution(
        self,
        tool_name: str,
        execution_id: str,
        success: bool,
        latency_ms: float,
        error_message: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Record a tool execution and update its performance metrics."""
        self._ensure_tool(tool_name)
        stats = self.tool_stats[tool_name]
        
        record = ToolExecutionRecord(
            execution_id=execution_id,
            success=success,
            latency_ms=latency_ms,
            error_message=error_message,
            metadata=metadata or {}
        )
        
        # Update metrics
        stats.total_executions += 1
        if success:
            stats.success_count += 1
        else:
            stats.failure_count += 1
            
        # Update rolling average latency
        n = stats.total_executions
        stats.average_latency_ms = ((stats.average_latency_ms * (n - 1)) + latency_ms) / n
        
        # Keep recent history
        stats.recent_records.append(record)
        if len(stats.recent_records) > self.history_limit:
            stats.recent_records.pop(0)
            
        logger.debug(f"Recorded execution for tool {tool_name}: success={success}")
        
    async def evaluate_tool(self, tool_name: str) -> Dict[str, Any]:
        """
        Evaluate a tool's recent performance to decide if it needs evolution or deprecation.
        """
        self._ensure_tool(tool_name)
        stats = self.tool_stats[tool_name]
        
        if len(stats.recent_records) < 10:
            return {
                "tool_name": tool_name,
                "action": "none",
                "reason": "insufficient_data"
            }
            
        recent_success_rate = sum(1 for r in stats.recent_records if r.success) / len(stats.recent_records)
        
        if recent_success_rate < self.success_threshold and stats.status == "active":
            stats.status = "evolving"
            logger.warning(f"Tool {tool_name} success rate ({recent_success_rate:.2f}) fell below threshold. Triggering evolution.")
            return {
                "tool_name": tool_name,
                "action": "evolve",
                "reason": "low_success_rate",
                "success_rate": recent_success_rate
            }
            
        return {
            "tool_name": tool_name,
            "action": "none",
            "reason": "healthy",
            "success_rate": recent_success_rate
        }

    async def deprecate_tool(self, tool_name: str, reason: str = "manual") -> None:
        """
        Mark a tool as deprecated.
        """
        self._ensure_tool(tool_name)
        self.tool_stats[tool_name].status = "deprecated"
        logger.info(f"Deprecated tool {tool_name}. Reason: {reason}")
        
    async def get_tool_stats(self, tool_name: str) -> Optional[ToolStats]:
        """Get the current statistics for a tool."""
        return self.tool_stats.get(tool_name)
