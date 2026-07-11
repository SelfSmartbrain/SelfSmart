"""Decision tracking instrumentation for frozen/augmented/delegated ratio.

Phase 17: Decision Instrumentation

Tracks and logs decision types:
- FROZEN: Pure LLM call, no tool/retrieval
- AUGMENTED: RAG/graph-assisted decisions
- DELEGATED: Tool call did the real work

This turns "is this AGI" from a philosophical question into a measurable ratio.
"""

from __future__ import annotations

from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Optional, Dict, List
from datetime import datetime, timezone
from collections import defaultdict

from src.config.logging import get_logger

logger = get_logger(__name__)


class DecisionType(str, Enum):
    """Types of decisions made by the system."""
    
    FROZEN = "frozen"  # Pure LLM call, no tool/retrieval
    AUGMENTED = "augmented"  # RAG/graph-assisted
    DELEGATED = "delegated"  # Tool call did the real work


class DecisionDomain(str, Enum):
    """Domains where decisions are made."""
    
    PLANNING = "planning"
    EXECUTION = "execution"
    REASONING = "reasoning"
    TOOL_SELECTION = "tool_selection"
    OBJECTIVE_GENERATION = "objective_generation"
    ERROR_RECOVERY = "error_recovery"
    OTHER = "other"


@dataclass
class DecisionRecord:
    """A record of a single decision."""
    
    decision_id: str
    decision_type: DecisionType
    domain: DecisionDomain
    timestamp: datetime
    objective_id: Optional[str] = None
    task_id: Optional[str] = None
    
    # Context about the decision
    prompt: Optional[str] = None
    response: Optional[str] = None
    tool_used: Optional[str] = None
    retrieval_sources: List[str] = field(default_factory=list)
    graph_nodes_accessed: List[str] = field(default_factory=list)
    
    # Metrics
    latency_ms: Optional[float] = None
    token_count: Optional[int] = None
    
    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "decision_type": self.decision_type.value,
            "domain": self.domain.value,
            "timestamp": self.timestamp.isoformat(),
            "objective_id": self.objective_id,
            "task_id": self.task_id,
            "tool_used": self.tool_used,
            "retrieval_sources": self.retrieval_sources,
            "graph_nodes_accessed": self.graph_nodes_accessed,
            "latency_ms": self.latency_ms,
            "token_count": self.token_count,
            "metadata": self.metadata,
        }


class DecisionTracker:
    """Tracks decisions and calculates frozen/augmented/delegated ratios."""
    
    def __init__(self):
        self.decisions: List[DecisionRecord] = []
        self.decisions_by_type: Dict[DecisionType, List[DecisionRecord]] = defaultdict(list)
        self.decisions_by_domain: Dict[DecisionDomain, List[DecisionRecord]] = defaultdict(list)
        
        logger.info("DecisionTracker initialized")
    
    def record_decision(
        self,
        decision_type: DecisionType,
        domain: DecisionDomain,
        prompt: Optional[str] = None,
        response: Optional[str] = None,
        tool_used: Optional[str] = None,
        retrieval_sources: Optional[List[str]] = None,
        graph_nodes_accessed: Optional[List[str]] = None,
        latency_ms: Optional[float] = None,
        token_count: Optional[int] = None,
        objective_id: Optional[str] = None,
        task_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> DecisionRecord:
        """Record a decision."""
        
        import uuid
        
        record = DecisionRecord(
            decision_id=str(uuid.uuid4()),
            decision_type=decision_type,
            domain=domain,
            timestamp=datetime.now(timezone.utc),
            objective_id=objective_id,
            task_id=task_id,
            prompt=prompt,
            response=response,
            tool_used=tool_used,
            retrieval_sources=retrieval_sources or [],
            graph_nodes_accessed=graph_nodes_accessed or [],
            latency_ms=latency_ms,
            token_count=token_count,
            metadata=metadata or {},
        )
        
        self.decisions.append(record)
        self.decisions_by_type[decision_type].append(record)
        self.decisions_by_domain[domain].append(record)
        
        logger.debug(
            f"Recorded {decision_type.value} decision in {domain.value} domain "
            f"(total: {len(self.decisions)})"
        )
        
        return record
    
    def record_frozen_decision(
        self,
        domain: DecisionDomain,
        prompt: str,
        response: str,
        **kwargs,
    ) -> DecisionRecord:
        """Record a frozen-model-bound decision (pure LLM call)."""
        return self.record_decision(
            decision_type=DecisionType.FROZEN,
            domain=domain,
            prompt=prompt,
            response=response,
            **kwargs,
        )
    
    def record_augmented_decision(
        self,
        domain: DecisionDomain,
        prompt: str,
        response: str,
        retrieval_sources: Optional[List[str]] = None,
        graph_nodes_accessed: Optional[List[str]] = None,
        **kwargs,
    ) -> DecisionRecord:
        """Record an augmented decision (RAG/graph-assisted)."""
        return self.record_decision(
            decision_type=DecisionType.AUGMENTED,
            domain=domain,
            prompt=prompt,
            response=response,
            retrieval_sources=retrieval_sources,
            graph_nodes_accessed=graph_nodes_accessed,
            **kwargs,
        )
    
    def record_delegated_decision(
        self,
        domain: DecisionDomain,
        tool_used: str,
        prompt: str,
        response: str,
        **kwargs,
    ) -> DecisionRecord:
        """Record a delegated decision (tool call did the work)."""
        return self.record_decision(
            decision_type=DecisionType.DELEGATED,
            domain=domain,
            tool_used=tool_used,
            prompt=prompt,
            response=response,
            **kwargs,
        )
    
    def get_decision_ratio(self, window_minutes: Optional[int] = None) -> Dict[str, float]:
        """Calculate the frozen/augmented/delegated ratio.
        
        Args:
            window_minutes: If provided, only consider decisions from the last N minutes.
        
        Returns:
            Dict with ratios for each decision type (sums to 1.0).
        """
        if window_minutes:
            cutoff = datetime.now(timezone.utc) - timedelta(minutes=window_minutes)
            recent_decisions = [d for d in self.decisions if d.timestamp >= cutoff]
        else:
            recent_decisions = self.decisions
        
        if not recent_decisions:
            return {
                "frozen": 0.0,
                "augmented": 0.0,
                "delegated": 0.0,
                "total": 0,
            }
        
        total = len(recent_decisions)
        frozen_count = sum(1 for d in recent_decisions if d.decision_type == DecisionType.FROZEN)
        augmented_count = sum(1 for d in recent_decisions if d.decision_type == DecisionType.AUGMENTED)
        delegated_count = sum(1 for d in recent_decisions if d.decision_type == DecisionType.DELEGATED)
        
        return {
            "frozen": frozen_count / total,
            "augmented": augmented_count / total,
            "delegated": delegated_count / total,
            "total": total,
        }
    
    def get_decision_ratio_by_domain(self, domain: DecisionDomain) -> Dict[str, float]:
        """Calculate decision ratio for a specific domain."""
        domain_decisions = self.decisions_by_domain.get(domain, [])
        
        if not domain_decisions:
            return {
                "frozen": 0.0,
                "augmented": 0.0,
                "delegated": 0.0,
                "total": 0,
            }
        
        total = len(domain_decisions)
        frozen_count = sum(1 for d in domain_decisions if d.decision_type == DecisionType.FROZEN)
        augmented_count = sum(1 for d in domain_decisions if d.decision_type == DecisionType.AUGMENTED)
        delegated_count = sum(1 for d in domain_decisions if d.decision_type == DecisionType.DELEGATED)
        
        return {
            "frozen": frozen_count / total,
            "augmented": augmented_count / total,
            "delegated": delegated_count / total,
            "total": total,
        }
    
    def get_decision_statistics(self) -> Dict[str, Any]:
        """Get comprehensive decision statistics."""
        if not self.decisions:
            return {
                "total_decisions": 0,
                "by_type": {},
                "by_domain": {},
                "average_latency_ms": None,
                "total_tokens": 0,
            }
        
        # Count by type
        by_type = {
            dt.value: len(self.decisions_by_type.get(dt, []))
            for dt in DecisionType
        }
        
        # Count by domain
        by_domain = {
            dd.value: len(self.decisions_by_domain.get(dd, []))
            for dd in DecisionDomain
        }
        
        # Calculate average latency
        latencies = [d.latency_ms for d in self.decisions if d.latency_ms is not None]
        avg_latency = sum(latencies) / len(latencies) if latencies else None
        
        # Total tokens
        total_tokens = sum(d.token_count or 0 for d in self.decisions)
        
        # Get current ratio
        current_ratio = self.get_decision_ratio()
        
        return {
            "total_decisions": len(self.decisions),
            "by_type": by_type,
            "by_domain": by_domain,
            "current_ratio": current_ratio,
            "average_latency_ms": avg_latency,
            "total_tokens": total_tokens,
        }
    
    def get_decisions_by_objective(self, objective_id: str) -> List[DecisionRecord]:
        """Get all decisions for a specific objective."""
        return [d for d in self.decisions if d.objective_id == objective_id]
    
    def get_decisions_by_task(self, task_id: str) -> List[DecisionRecord]:
        """Get all decisions for a specific task."""
        return [d for d in self.decisions if d.task_id == task_id]
    
    def clear_old_decisions(self, keep_minutes: int = 60) -> int:
        """Clear decisions older than the specified time window.
        
        Returns the number of decisions removed.
        """
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=keep_minutes)
        original_count = len(self.decisions)
        
        self.decisions = [d for d in self.decisions if d.timestamp >= cutoff]
        
        # Rebuild by-type and by-domain indexes
        self.decisions_by_type = defaultdict(list)
        self.decisions_by_domain = defaultdict(list)
        
        for decision in self.decisions:
            self.decisions_by_type[decision.decision_type].append(decision)
            self.decisions_by_domain[decision.domain].append(decision)
        
        removed = original_count - len(self.decisions)
        logger.info(f"Cleared {removed} old decisions (kept {len(self.decisions)})")
        
        return removed


# Global singleton for easy access
_global_tracker: Optional[DecisionTracker] = None


def get_decision_tracker() -> DecisionTracker:
    """Get the global decision tracker instance."""
    global _global_tracker
    if _global_tracker is None:
        _global_tracker = DecisionTracker()
    return _global_tracker


def reset_decision_tracker() -> None:
    """Reset the global decision tracker (mainly for testing)."""
    global _global_tracker
    _global_tracker = None


from datetime import timedelta
