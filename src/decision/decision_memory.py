"""decision_memory.py

Stores and retrieves past decisions for learning.
Enables the system to learn from its decision history.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from dataclasses import dataclass, field

from src.config.logging import get_logger

if TYPE_CHECKING:
    from src.decision.decision_engine import Decision

logger = get_logger(__name__)


@dataclass
class DecisionRecord:
    """A record of a past decision."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    query: str = ""
    selected_option: str = ""
    reasoning: str = ""
    confidence: float = 0.0
    outcome: Optional[Dict[str, Any]] = None
    success: bool = False
    lesson_learned: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "query": self.query,
            "selected_option": self.selected_option,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "outcome": self.outcome,
            "success": self.success,
            "lesson_learned": self.lesson_learned,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class DecisionMemory:
    """Memory for storing and retrieving past decisions."""
    
    def __init__(self):
        self.decisions: Dict[str, DecisionRecord] = {}
        self.query_index: Dict[str, List[str]] = {}  # query -> decision_record_ids
        logger.info("DecisionMemory initialized")
    
    def store_decision(self, decision: Decision) -> DecisionRecord:
        """Store a decision in memory."""
        record = DecisionRecord(
            decision_id=decision.id,
            query=decision.query,
            selected_option=decision.selected_option_id or "",
            reasoning=decision.reasoning,
            confidence=decision.confidence,
            outcome=decision.outcome,
            success=self._determine_success(decision),
        )
        
        self.decisions[record.id] = record
        
        # Index by query
        query_key = self._normalize_query(decision.query)
        if query_key not in self.query_index:
            self.query_index[query_key] = []
        self.query_index[query_key].append(record.id)
        
        logger.info(f"Stored decision: {decision.id}")
        return record
    
    def _determine_success(self, decision: Decision) -> bool:
        """Determine if a decision was successful."""
        if decision.outcome is None:
            return False
        
        # Simple heuristic: success if outcome indicates positive result
        outcome_str = str(decision.outcome).lower()
        positive_indicators = ["success", "completed", "achieved", "positive"]
        return any(indicator in outcome_str for indicator in positive_indicators)
    
    def _normalize_query(self, query: str) -> str:
        """Normalize a query for indexing."""
        return query.lower().strip()
    
    def get_decision(self, record_id: str) -> Optional[DecisionRecord]:
        """Get a decision record by ID."""
        return self.decisions.get(record_id)
    
    def update_decision(self, decision: Decision) -> None:
        """Update a decision with outcome information."""
        # Find existing record
        for record in self.decisions.values():
            if record.decision_id == decision.id:
                record.outcome = decision.outcome
                record.success = self._determine_success(decision)
                logger.info(f"Updated decision record: {record.id}")
                return
    
        # If not found, store as new
        self.store_decision(decision)
    
    def record_outcome(self, decision_id: str, outcome: Dict[str, Any]) -> None:
        """Record the outcome of a decision."""
        for record in self.decisions.values():
            if record.decision_id == decision_id:
                record.outcome = outcome
                record.success = self._determine_success_from_outcome(outcome)
                logger.info(f"Recorded outcome for decision: {decision_id}")
                return
    
    def _determine_success_from_outcome(self, outcome: Dict[str, Any]) -> bool:
        """Determine success from outcome data."""
        if not outcome:
            return False
        
        # Check for explicit success flag
        if "success" in outcome:
            return outcome["success"]
        
        # Check for positive indicators
        outcome_str = str(outcome).lower()
        positive_indicators = ["success", "completed", "achieved", "positive"]
        return any(indicator in outcome_str for indicator in positive_indicators)
    
    def add_lesson(self, record_id: str, lesson: str) -> None:
        """Add a lesson learned from a decision."""
        record = self.get_decision(record_id)
        if record:
            record.lesson_learned = lesson
            logger.info(f"Added lesson to decision record: {record_id}")
    
    def search_similar_decisions(self, query: str, limit: int = 5) -> List[DecisionRecord]:
        """Search for similar past decisions."""
        query_key = self._normalize_query(query)
        
        # Simple exact match for now
        if query_key in self.query_index:
            record_ids = self.query_index[query_key]
            records = [self.get_decision(rid) for rid in record_ids if rid in self.decisions]
            return records[:limit]
        
        # If no exact match, return recent decisions
        recent = sorted(
            self.decisions.values(),
            key=lambda r: r.timestamp,
            reverse=True,
        )
        return recent[:limit]
    
    def get_successful_decisions(self, limit: int = 10) -> List[DecisionRecord]:
        """Get successful decisions for learning."""
        successful = [r for r in self.decisions.values() if r.success]
        return sorted(successful, key=lambda r: r.timestamp, reverse=True)[:limit]
    
    def get_failed_decisions(self, limit: int = 10) -> List[DecisionRecord]:
        """Get failed decisions for learning."""
        failed = [r for r in self.decisions.values() if not r.success]
        return sorted(failed, key=lambda r: r.timestamp, reverse=True)[:limit]
    
    def get_lessons_learned(self) -> List[str]:
        """Get all lessons learned from decisions."""
        lessons = []
        for record in self.decisions.values():
            if record.lesson_learned:
                lessons.append(record.lesson_learned)
        return lessons
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about decision memory."""
        if not self.decisions:
            return {"total_decisions": 0}
        
        total = len(self.decisions)
        successful = sum(1 for r in self.decisions.values() if r.success)
        
        return {
            "total_decisions": total,
            "successful_decisions": successful,
            "failed_decisions": total - successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "decisions_with_lessons": sum(1 for r in self.decisions.values() if r.lesson_learned),
        }
