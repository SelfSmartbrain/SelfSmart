"""strategy_memory.py

Stores and retrieves past strategies for learning.
Enables the system to learn from strategic successes and failures.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from src.config.logging import get_logger
from src.decision.strategy_engine import Strategy

logger = get_logger(__name__)


@dataclass
class StrategyRecord:
    """A record of a past strategy."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    strategy_id: str = ""
    name: str = ""
    description: str = ""
    time_horizon: str = ""
    goals_count: int = 0
    success_probability: float = 0.0
    actual_outcome: Optional[Dict[str, Any]] = None
    success: bool = False
    lessons_learned: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "strategy_id": self.strategy_id,
            "name": self.name,
            "description": self.description,
            "time_horizon": self.time_horizon,
            "goals_count": self.goals_count,
            "success_probability": self.success_probability,
            "actual_outcome": self.actual_outcome,
            "success": self.success,
            "lessons_learned": self.lessons_learned,
            "timestamp": self.timestamp.isoformat(),
            "metadata": self.metadata,
        }


class StrategyMemory:
    """Memory for storing and retrieving past strategies."""
    
    def __init__(self):
        self.strategies: Dict[str, StrategyRecord] = {}
        self.horizon_index: Dict[str, List[str]] = {}  # horizon -> strategy_record_ids
        logger.info("StrategyMemory initialized")
    
    def store_strategy(
        self,
        strategy: Strategy,
        outcome: Optional[Dict[str, Any]] = None,
    ) -> StrategyRecord:
        """Store a strategy in memory."""
        record = StrategyRecord(
            strategy_id=strategy.id,
            name=strategy.name,
            description=strategy.description,
            time_horizon=strategy.time_horizon.value,
            goals_count=len(strategy.goals),
            success_probability=strategy.success_probability,
            actual_outcome=outcome,
            success=self._determine_success(strategy, outcome),
        )
        
        self.strategies[record.id] = record
        
        # Index by time horizon
        horizon = strategy.time_horizon.value
        if horizon not in self.horizon_index:
            self.horizon_index[horizon] = []
        self.horizon_index[horizon].append(record.id)
        
        logger.info(f"Stored strategy: {strategy.id}")
        return record
    
    def _determine_success(
        self,
        strategy: Strategy,
        outcome: Optional[Dict[str, Any]],
    ) -> bool:
        """Determine if a strategy was successful."""
        if outcome is None:
            return False
        
        # Check for explicit success flag
        if "success" in outcome:
            return outcome["success"]
        
        # Check goal completion
        if "goals_completed" in outcome:
            total_goals = len(strategy.goals)
            completed = outcome["goals_completed"]
            return completed / total_goals >= 0.8 if total_goals > 0 else False
        
        return False
    
    def get_strategy(self, record_id: str) -> Optional[StrategyRecord]:
        """Get a strategy record by ID."""
        return self.strategies.get(record_id)
    
    def update_strategy(
        self,
        strategy_id: str,
        outcome: Dict[str, Any],
    ) -> None:
        """Update a strategy with outcome information."""
        for record in self.strategies.values():
            if record.strategy_id == strategy_id:
                record.actual_outcome = outcome
                record.success = self._determine_success_from_outcome(outcome)
                logger.info(f"Updated strategy record: {record.id}")
                return
    
    def _determine_success_from_outcome(self, outcome: Dict[str, Any]) -> bool:
        """Determine success from outcome data."""
        if not outcome:
            return False
        
        if "success" in outcome:
            return outcome["success"]
        
        outcome_str = str(outcome).lower()
        positive_indicators = ["success", "completed", "achieved", "positive"]
        return any(indicator in outcome_str for indicator in positive_indicators)
    
    def add_lesson(self, record_id: str, lesson: str) -> None:
        """Add a lesson learned from a strategy."""
        record = self.get_strategy(record_id)
        if record:
            record.lessons_learned.append(lesson)
            logger.info(f"Added lesson to strategy record: {record_id}")
    
    def search_by_horizon(self, horizon: str, limit: int = 5) -> List[StrategyRecord]:
        """Search for strategies by time horizon."""
        if horizon in self.horizon_index:
            record_ids = self.horizon_index[horizon]
            records = [self.get_strategy(rid) for rid in record_ids if rid in self.strategies]
            return sorted(records, key=lambda r: r.timestamp, reverse=True)[:limit]
        
        return []
    
    def get_successful_strategies(self, limit: int = 10) -> List[StrategyRecord]:
        """Get successful strategies for learning."""
        successful = [r for r in self.strategies.values() if r.success]
        return sorted(successful, key=lambda r: r.timestamp, reverse=True)[:limit]
    
    def get_failed_strategies(self, limit: int = 10) -> List[StrategyRecord]:
        """Get failed strategies for learning."""
        failed = [r for r in self.strategies.values() if not r.success]
        return sorted(failed, key=lambda r: r.timestamp, reverse=True)[:limit]
    
    def get_all_lessons(self) -> List[str]:
        """Get all lessons learned from strategies."""
        lessons = []
        for record in self.strategies.values():
            lessons.extend(record.lessons_learned)
        return lessons
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics about strategy memory."""
        if not self.strategies:
            return {"total_strategies": 0}
        
        total = len(self.strategies)
        successful = sum(1 for r in self.strategies.values() if r.success)
        
        return {
            "total_strategies": total,
            "successful_strategies": successful,
            "failed_strategies": total - successful,
            "success_rate": successful / total if total > 0 else 0.0,
            "by_horizon": {
                horizon: len(self.horizon_index.get(horizon, []))
                for horizon in self.horizon_index
            },
        }
