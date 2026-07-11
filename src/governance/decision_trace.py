"""decision_trace.py

Phase 16A: Decision Trace

Tracks the complete trace of a decision including:
- Decision context
- Reasoning chain
- Evidence used
- Options considered
- Final selection
- Execution outcome
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class TraceEventType(str, Enum):
    """Types of events in a decision trace."""
    DECISION_INITIATED = "decision_initiated"
    CONTEXT_GATHERED = "context_gathered"
    OPTIONS_GENERATED = "options_generated"
    OPTIONS_EVALUATED = "options_evaluated"
    RISK_ASSESSED = "risk_assessed"
    OPTION_SELECTED = "option_selected"
    DECISION_FINALIZED = "decision_finalized"
    EXECUTION_STARTED = "execution_started"
    EXECUTION_COMPLETED = "execution_completed"
    OUTCOME_RECORDED = "outcome_recorded"
    ERROR_OCCURRED = "error_occurred"


@dataclass
class TraceEvent:
    """A single event in the decision trace."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    event_type: TraceEventType = TraceEventType.DECISION_INITIATED
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    data: Dict[str, Any] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "data": self.data,
            "metadata": self.metadata,
        }


@dataclass
class DecisionTrace:
    """Complete trace of a decision from initiation to outcome."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    decision_query: str = ""
    events: List[TraceEvent] = field(default_factory=list)
    initial_context: Dict[str, Any] = field(default_factory=dict)
    final_outcome: Optional[Dict[str, Any]] = None
    success: bool = False
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def add_event(self, event_type: TraceEventType, data: Dict[str, Any]) -> None:
        """Add an event to the trace."""
        event = TraceEvent(event_type=event_type, data=data)
        self.events.append(event)
        logger.debug(f"Added trace event: {event_type.value} for decision {self.decision_id}")
    
    def get_events_by_type(self, event_type: TraceEventType) -> List[TraceEvent]:
        """Get all events of a specific type."""
        return [e for e in self.events if e.event_type == event_type]
    
    def get_timeline(self) -> List[Dict[str, Any]]:
        """Get the complete timeline of events."""
        return [e.to_dict() for e in sorted(self.events, key=lambda e: e.timestamp)]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "decision_query": self.decision_query,
            "events": [e.to_dict() for e in self.events],
            "initial_context": self.initial_context,
            "final_outcome": self.final_outcome,
            "success": self.success,
            "created_at": self.created_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "metadata": self.metadata,
        }


class DecisionTraceManager:
    """Manages decision traces."""
    
    def __init__(self):
        self.traces: Dict[str, DecisionTrace] = {}
        self.traces_by_decision: Dict[str, str] = {}  # decision_id -> trace_id
        logger.info("DecisionTraceManager initialized")
    
    def create_trace(
        self,
        decision_id: str,
        decision_query: str,
        initial_context: Optional[Dict[str, Any]] = None,
    ) -> DecisionTrace:
        """Create a new decision trace."""
        trace = DecisionTrace(
            decision_id=decision_id,
            decision_query=decision_query,
            initial_context=initial_context or {},
        )
        
        # Add initiation event
        trace.add_event(
            TraceEventType.DECISION_INITIATED,
            {"decision_id": decision_id, "query": decision_query},
        )
        
        self.traces[trace.id] = trace
        self.traces_by_decision[decision_id] = trace.id
        
        logger.info(f"Created trace {trace.id} for decision {decision_id}")
        
        return trace
    
    def get_trace(self, trace_id: str) -> Optional[DecisionTrace]:
        """Get a trace by ID."""
        return self.traces.get(trace_id)
    
    def get_trace_by_decision(self, decision_id: str) -> Optional[DecisionTrace]:
        """Get a trace by decision ID."""
        trace_id = self.traces_by_decision.get(decision_id)
        if trace_id:
            return self.traces.get(trace_id)
        return None
    
    def add_event(
        self,
        decision_id: str,
        event_type: TraceEventType,
        data: Dict[str, Any],
    ) -> None:
        """Add an event to a decision's trace."""
        trace = self.get_trace_by_decision(decision_id)
        if trace:
            trace.add_event(event_type, data)
    
    def complete_trace(
        self,
        decision_id: str,
        final_outcome: Dict[str, Any],
        success: bool,
    ) -> None:
        """Complete a decision trace with the final outcome."""
        trace = self.get_trace_by_decision(decision_id)
        if trace:
            trace.final_outcome = final_outcome
            trace.success = success
            trace.completed_at = datetime.now(timezone.utc)
            
            trace.add_event(
                TraceEventType.OUTCOME_RECORDED,
                {"outcome": final_outcome, "success": success},
            )
            
            logger.info(f"Completed trace for decision {decision_id}")
    
    def list_traces(self, limit: int = 100) -> List[DecisionTrace]:
        """List all traces, optionally limited."""
        traces = list(self.traces.values())
        traces.sort(key=lambda t: t.created_at, reverse=True)
        return traces[:limit]
    
    def get_trace_statistics(self) -> Dict[str, Any]:
        """Get statistics about decision traces."""
        total_traces = len(self.traces)
        completed_traces = sum(1 for t in self.traces.values() if t.completed_at)
        successful_traces = sum(1 for t in self.traces.values() if t.success)
        
        return {
            "total_traces": total_traces,
            "completed_traces": completed_traces,
            "successful_traces": successful_traces,
            "success_rate": successful_traces / completed_traces if completed_traces > 0 else 0.0,
        }
