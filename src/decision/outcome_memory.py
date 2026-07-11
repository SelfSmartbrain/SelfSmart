"""outcome_memory.py

Stores and retrieves past outcomes for learning.
Enables the system to learn from the results of its actions.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timezone

from src.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class OutcomeRecord:
    """A record of a past outcome."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    action_id: str = ""
    action_type: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    result: Dict[str, Any] = field(default_factory=dict)
    metrics: Dict[str, float] = field(default_factory=dict)
    success: bool = False
    unexpected_events: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "action_id": self.action_id,
            "action_type": self.action_type,
            "context": self.context,
            "result": self.result,
            "metrics": self.metrics,
            "success": self.success,
            "unexpected_events": self.unexpected_events,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class OutcomeMemory:
    """Memory for storing and retrieving past outcomes."""
    
    def __init__(self):
        self.outcomes: Dict[str, OutcomeRecord] = {}
        self.action_type_index: Dict[str, List[str]] = {}  # action_type -> outcome_record_ids
        self.success_index: Dict[bool, List[str]] = {True: [], False: []}
        logger.info("OutcomeMemory initialized")
    
    def store_outcome(
        self,
        action_id: str,
        action_type: str,
        context: Dict[str, Any],
        result: Dict[str, Any],
        metrics: Optional[Dict[str, float]] = None,
        unexpected_events: Optional[List[str]] = None,
    ) -> OutcomeRecord:
        """Store an outcome in memory."""
        record = OutcomeRecord(
            action_id=action_id,
            action_type=action_type,
            context=context,
            result=result,
            metrics=metrics or {},
            success=self._determine_success(result),
            unexpected_events=unexpected_events or [],
        )
        
        self.outcomes[record.id] = record
        
        # Index by action type
        if action_type not in self.action_type_index:
            self.action_type_index[action_type] = []
        self.action_type_index[action_type].append(record.id)
        
        # Index by success
        self.success_index[record.success].append(record.id)
        
        logger.info(f"Stored outcome for action: {action_id}")
        return record
    
    def _determine_success(self, result: Dict[str, Any]) -> bool:
        """Determine if an outcome was successful."""
        if not result:
            return False
        
        if "success" in result:
            return result["success"]
        
        result_str = str(result).lower()
        positive_indicators = ["success", "completed", "achieved", "positive"]
        return any(indicator in result_str for indicator in positive_indicators)
    
    def get_outcome(self, record_id: str) -> Optional[OutcomeRecord]:
        """Get an outcome record by ID."""
        return self.outcomes.get(record_id)
    
    def search_by_action_type(self, action_type: str, limit: int = 10) -> List[OutcomeRecord]:
        """Search for outcomes by action type."""
        if action_type in self.action_type_index:
            record_ids = self.action_type_index[action_type]
            records = [self.get_outcome(rid) for rid in record_ids if rid in self.outcomes]
            return sorted(records, key=lambda r: r.timestamp, reverse=True)[:limit]
        
        return []
    
    def get_successful_outcomes(self, limit: int = 10) -> List[OutcomeRecord]:
        """Get successful outcomes for learning."""
        record_ids = self.success_index[True]
        records = [self.get_outcome(rid) for rid in record_ids if rid in self.outcomes]
        return sorted(records, key=lambda r: r.timestamp, reverse=True)[:limit]
    
    def get_failed_outcomes(self, limit: int = 10) -> List[OutcomeRecord]:
        """Get failed outcomes for learning."""
        record_ids = self.success_index[False]
        records = [self.get_outcome(rid) for rid in record_ids if rid in self.outcomes]
        return sorted(records, key=lambda r: r.timestamp, reverse=True)[:limit]
    
    def analyze_outcome_patterns(self) -> Dict[str, Any]:
        """Analyze patterns in outcomes."""
        if not self.outcomes:
            return {"message": "No outcomes to analyze"}
        
        patterns = {
            "total_outcomes": len(self.outcomes),
            "success_rate": len(self.success_index[True]) / len(self.outcomes),
            "by_action_type": {},
            "common_unexpected_events": {},
        }
        
        # Analyze by action type
        for action_type, record_ids in self.action_type_index.items():
            records = [self.get_outcome(rid) for rid in record_ids if rid in self.outcomes]
            if records:
                success_count = sum(1 for r in records if r.success)
                patterns["by_action_type"][action_type] = {
                    "total": len(records),
                    "successful": success_count,
                    "success_rate": success_count / len(records),
                }
        
        # Analyze unexpected events
        event_counts = {}
        for record in self.outcomes.values():
            for event in record.unexpected_events:
                event_counts[event] = event_counts.get(event, 0) + 1
        
        # Top unexpected events
        sorted_events = sorted(event_counts.items(), key=lambda x: x[1], reverse=True)
        patterns["common_unexpected_events"] = dict(sorted_events[:5])
        
        return patterns
    
    def get_outcome_statistics(self) -> Dict[str, Any]:
        """Get statistics about outcome memory."""
        if not self.outcomes:
            return {"total_outcomes": 0}
        
        total = len(self.outcomes)
        successful = len(self.success_index[True])
        
        return {
            "total_outcomes": total,
            "successful_outcomes": successful,
            "failed_outcomes": total - successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "unique_action_types": len(self.action_type_index),
            "outcomes_with_unexpected_events": sum(
                1 for r in self.outcomes.values() if r.unexpected_events
            ),
        }
