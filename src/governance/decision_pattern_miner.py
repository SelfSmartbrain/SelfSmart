"""decision_pattern_miner.py

Phase 16C: Decision Pattern Miner

Discovers patterns in decision-making behavior.
Identifies:
- Recurring decision patterns
- Contextual patterns
- Temporal patterns
- Agent-specific patterns
"""

from __future__ import annotations

import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Tuple
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class PatternType(str, Enum):
    """Types of decision patterns."""
    CONTEXTUAL = "contextual"
    TEMPORAL = "temporal"
    SEQUENTIAL = "sequential"
    AGENT_SPECIFIC = "agent_specific"
    OUTCOME_CORRELATED = "outcome_correlated"


class PatternStrength(str, Enum):
    """Strength of a pattern."""
    WEAK = "weak"
    MODERATE = "moderate"
    STRONG = "strong"
    VERY_STRONG = "very_strong"


@dataclass
class DecisionPattern:
    """A discovered pattern in decision-making."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    pattern_type: PatternType = PatternType.CONTEXTUAL
    description: str = ""
    features: Dict[str, Any] = field(default_factory=dict)
    frequency: int = 0
    total_decisions: int = 0
    support: float = 0.0  # frequency / total
    confidence: float = 0.0
    strength: PatternStrength = PatternStrength.MODERATE
    examples: List[str] = field(default_factory=list)
    first_seen: Optional[datetime] = None
    last_seen: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "pattern_type": self.pattern_type.value,
            "description": self.description,
            "features": self.features,
            "frequency": self.frequency,
            "total_decisions": self.total_decisions,
            "support": self.support,
            "confidence": self.confidence,
            "strength": self.strength.value,
            "examples": self.examples[:5],
            "first_seen": self.first_seen.isoformat() if self.first_seen else None,
            "last_seen": self.last_seen.isoformat() if self.last_seen else None,
            "metadata": self.metadata,
        }


class DecisionPatternMiner:
    """Mines patterns from decision history."""
    
    def __init__(self):
        self.patterns: Dict[str, DecisionPattern] = {}
        self.decision_history: List[Dict[str, Any]] = []
        logger.info("DecisionPatternMiner initialized")
    
    def add_decision(self, decision_data: Dict[str, Any]) -> None:
        """Add a decision to the history for pattern mining."""
        self.decision_history.append(decision_data)
        
        # Re-mine patterns periodically
        if len(self.decision_history) % 10 == 0:
            self.mine_patterns()
    
    def mine_patterns(self) -> List[DecisionPattern]:
        """Mine patterns from the decision history."""
        if len(self.decision_history) < 3:
            logger.info("Not enough decisions to mine patterns")
            return []
        
        patterns = []
        
        # Mine contextual patterns
        patterns.extend(self._mine_contextual_patterns())
        
        # Mine temporal patterns
        patterns.extend(self._mine_temporal_patterns())
        
        # Mine sequential patterns
        patterns.extend(self._mine_sequential_patterns())
        
        # Mine outcome-correlated patterns
        patterns.extend(self._mine_outcome_patterns())
        
        # Store patterns
        for pattern in patterns:
            self.patterns[pattern.id] = pattern
        
        logger.info(f"Mined {len(patterns)} decision patterns")
        
        return patterns
    
    def _mine_contextual_patterns(self) -> List[DecisionPattern]:
        """Mine patterns based on decision context."""
        patterns = []
        
        # Group by context features
        context_groups = defaultdict(list)
        
        for decision in self.decision_history:
            context = decision.get("context", {})
            time_horizon = context.get("time_horizon", "unknown")
            risk_tolerance = context.get("risk_tolerance", 0.5)
            
            key = (time_horizon, round(risk_tolerance, 1))
            context_groups[key].append(decision)
        
        # Find patterns in groups
        for key, decisions in context_groups.items():
            if len(decisions) >= 3:
                time_horizon, risk_tolerance = key
                
                # Analyze common outcomes
                outcomes = [d.get("outcome") for d in decisions if d.get("outcome")]
                if outcomes:
                    success_rate = sum(1 for o in outcomes if o.get("success", False)) / len(outcomes)
                    
                    pattern = DecisionPattern(
                        pattern_type=PatternType.CONTEXTUAL,
                        description=f"Decisions with time_horizon={time_horizon}, risk_tolerance={risk_tolerance}",
                        features={
                            "time_horizon": time_horizon,
                            "risk_tolerance": risk_tolerance,
                            "success_rate": success_rate,
                        },
                        frequency=len(decisions),
                        total_decisions=len(self.decision_history),
                        support=len(decisions) / len(self.decision_history),
                        confidence=success_rate,
                        strength=self._calculate_strength(len(decisions), len(self.decision_history)),
                        examples=[d.get("id", "") for d in decisions[:3]],
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _mine_temporal_patterns(self) -> List[DecisionPattern]:
        """Mine patterns based on time."""
        patterns = []
        
        # Group by time of day
        hour_groups = defaultdict(list)
        
        for decision in self.decision_history:
            created_at = decision.get("created_at")
            if created_at:
                if isinstance(created_at, str):
                    try:
                        dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    except:
                        continue
                else:
                    dt = created_at
                
                hour = dt.hour
                hour_groups[hour].append(decision)
        
        # Find patterns in hour groups
        for hour, decisions in hour_groups.items():
            if len(decisions) >= 3:
                outcomes = [d.get("outcome") for d in decisions if d.get("outcome")]
                if outcomes:
                    success_rate = sum(1 for o in outcomes if o.get("success", False)) / len(outcomes)
                    
                    pattern = DecisionPattern(
                        pattern_type=PatternType.TEMPORAL,
                        description=f"Decisions made around hour {hour}",
                        features={
                            "hour": hour,
                            "success_rate": success_rate,
                        },
                        frequency=len(decisions),
                        total_decisions=len(self.decision_history),
                        support=len(decisions) / len(self.decision_history),
                        confidence=success_rate,
                        strength=self._calculate_strength(len(decisions), len(self.decision_history)),
                        examples=[d.get("id", "") for d in decisions[:3]],
                    )
                    patterns.append(pattern)
        
        return patterns
    
    def _mine_sequential_patterns(self) -> List[DecisionPattern]:
        """Mine sequential patterns in decision chains."""
        patterns = []
        
        if len(self.decision_history) < 5:
            return patterns
        
        # Look for common sequences of decision types
        decision_types = []
        for decision in self.decision_history:
            query = decision.get("query", "")
            # Simple type extraction - in production, use NLP
            if "resource" in query.lower():
                decision_types.append("resource")
            elif "time" in query.lower():
                decision_types.append("time")
            elif "strategy" in query.lower():
                decision_types.append("strategy")
            else:
                decision_types.append("general")
        
        # Find common 2-grams
        ngrams = []
        for i in range(len(decision_types) - 1):
            ngrams.append((decision_types[i], decision_types[i+1]))
        
        ngram_counts = Counter(ngrams)
        
        for ngram, count in ngram_counts.most_common(5):
            if count >= 2:
                pattern = DecisionPattern(
                    pattern_type=PatternType.SEQUENTIAL,
                    description=f"Sequence: {ngram[0]} -> {ngram[1]}",
                    features={
                        "sequence": list(ngram),
                    },
                    frequency=count,
                    total_decisions=len(self.decision_history),
                    support=count / len(self.decision_history),
                    confidence=0.7,
                    strength=self._calculate_strength(count, len(self.decision_history)),
                    examples=[],
                )
                patterns.append(pattern)
        
        return patterns
    
    def _mine_outcome_patterns(self) -> List[DecisionPattern]:
        """Mine patterns correlated with outcomes."""
        patterns = []
        
        # Group decisions by outcome
        successful = []
        failed = []
        
        for decision in self.decision_history:
            outcome = decision.get("outcome")
            if outcome:
                if outcome.get("success", False):
                    successful.append(decision)
                else:
                    failed.append(decision)
        
        # Analyze successful patterns
        if len(successful) >= 3:
            success_patterns = self._analyze_group_patterns(successful, "success")
            patterns.extend(success_patterns)
        
        # Analyze failure patterns
        if len(failed) >= 3:
            failure_patterns = self._analyze_group_patterns(failed, "failure")
            patterns.extend(failure_patterns)
        
        return patterns
    
    def _analyze_group_patterns(self, decisions: List[Dict[str, Any]], outcome_type: str) -> List[DecisionPattern]:
        """Analyze patterns in a group of decisions."""
        patterns = []
        
        # Common context features
        time_horizons = [d.get("context", {}).get("time_horizon") for d in decisions]
        time_horizon_counter = Counter([h for h in time_horizons if h])
        
        for time_horizon, count in time_horizon_counter.most_common(3):
            if count >= 2:
                pattern = DecisionPattern(
                    pattern_type=PatternType.OUTCOME_CORRELATED,
                    description=f"{outcome_type} pattern with time_horizon={time_horizon}",
                    features={
                        "outcome_type": outcome_type,
                        "time_horizon": time_horizon,
                    },
                    frequency=count,
                    total_decisions=len(decisions),
                    support=count / len(decisions),
                    confidence=0.8,
                    strength=self._calculate_strength(count, len(decisions)),
                    examples=[d.get("id", "") for d in decisions[:3]],
                )
                patterns.append(pattern)
        
        return patterns
    
    def _calculate_strength(self, frequency: int, total: int) -> PatternStrength:
        """Calculate pattern strength based on frequency and support."""
        support = frequency / total if total > 0 else 0
        
        if support > 0.3:
            return PatternStrength.VERY_STRONG
        elif support > 0.2:
            return PatternStrength.STRONG
        elif support > 0.1:
            return PatternStrength.MODERATE
        else:
            return PatternStrength.WEAK
    
    def get_pattern(self, pattern_id: str) -> Optional[DecisionPattern]:
        """Get a pattern by ID."""
        return self.patterns.get(pattern_id)
    
    def get_patterns_by_type(self, pattern_type: PatternType) -> List[DecisionPattern]:
        """Get all patterns of a specific type."""
        return [p for p in self.patterns.values() if p.pattern_type == pattern_type]
    
    def get_strong_patterns(self, min_strength: PatternStrength = PatternStrength.STRONG) -> List[DecisionPattern]:
        """Get patterns above a strength threshold."""
        strength_order = {
            PatternStrength.WEAK: 1,
            PatternStrength.MODERATE: 2,
            PatternStrength.STRONG: 3,
            PatternStrength.VERY_STRONG: 4,
        }
        
        min_level = strength_order.get(min_strength, 2)
        
        return [
            p for p in self.patterns.values()
            if strength_order.get(p.strength, 0) >= min_level
        ]
    
    def get_pattern_statistics(self) -> Dict[str, Any]:
        """Get statistics about patterns."""
        total_patterns = len(self.patterns)
        
        by_type = {
            pattern_type.value: len(self.get_patterns_by_type(pattern_type))
            for pattern_type in PatternType
        }
        
        by_strength = {
            strength.value: len([p for p in self.patterns.values() if p.strength == strength])
            for strength in PatternStrength
        }
        
        return {
            "total_patterns": total_patterns,
            "by_type": by_type,
            "by_strength": by_strength,
            "decisions_analyzed": len(self.decision_history),
        }
