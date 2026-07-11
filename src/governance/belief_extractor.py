"""belief_extractor.py

Phase 16B: Belief Extractor

Extracts beliefs and mental models that underlie decisions.
Identifies:
- Core beliefs about the system
- Beliefs about capabilities
- Beliefs about limitations
- Beliefs about the environment
- Beliefs about success criteria
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class BeliefType(str, Enum):
    """Types of beliefs."""
    CAPABILITY = "capability"
    LIMITATION = "limitation"
    ENVIRONMENT = "environment"
    SUCCESS = "success"
    STRATEGY = "strategy"
    RESOURCE = "resource"


class BeliefSource(str, Enum):
    """Source of a belief."""
    EXPERIENCE = "experience"
    TRAINING = "training"
    ASSUMPTION = "assumption"
    EXTERNAL = "external"
    DERIVED = "derived"


@dataclass
class Belief:
    """A belief extracted from decisions."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    belief_type: BeliefType = BeliefType.CAPABILITY
    statement: str = ""
    confidence: float = 0.5
    source: BeliefSource = BeliefSource.EXPERIENCE
    evidence: List[str] = field(default_factory=list)
    counter_evidence: List[str] = field(default_factory=list)
    last_validated: Optional[str] = None
    validation_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "belief_type": self.belief_type.value,
            "statement": self.statement,
            "confidence": self.confidence,
            "source": self.source.value,
            "evidence": self.evidence,
            "counter_evidence": self.counter_evidence,
            "last_validated": self.last_validated,
            "validation_count": self.validation_count,
            "success_count": self.success_count,
            "failure_count": self.failure_count,
            "metadata": self.metadata,
        }
    
    def update_confidence(self, success: bool) -> None:
        """Update confidence based on validation outcome."""
        self.validation_count += 1
        
        if success:
            self.success_count += 1
            # Increase confidence
            self.confidence = min(1.0, self.confidence + 0.05)
        else:
            self.failure_count += 1
            # Decrease confidence
            self.confidence = max(0.0, self.confidence - 0.1)


class BeliefExtractor:
    """Extracts beliefs from decisions and outcomes."""
    
    def __init__(self):
        self.beliefs: Dict[str, Belief] = {}
        logger.info("BeliefExtractor initialized")
    
    def extract_beliefs(
        self,
        decision_data: Dict[str, Any],
        outcome: Optional[Dict[str, Any]] = None,
    ) -> List[Belief]:
        """Extract beliefs from a decision and its outcome."""
        beliefs = []
        
        # Extract from reasoning
        reasoning = decision_data.get("reasoning", "")
        if reasoning:
            beliefs.extend(self._extract_from_reasoning(reasoning))
        
        # Extract from context
        context = decision_data.get("context", {})
        beliefs.extend(self._extract_from_context(context))
        
        # Extract from options
        options = decision_data.get("options", [])
        for option in options:
            beliefs.extend(self._extract_from_option(option))
        
        # Update beliefs with outcome
        if outcome:
            for belief in beliefs:
                self._update_belief_with_outcome(belief, outcome)
        
        # Store beliefs
        for belief in beliefs:
            self._store_or_update_belief(belief)
        
        logger.info(f"Extracted {len(beliefs)} beliefs")
        
        return beliefs
    
    def _extract_from_reasoning(self, reasoning: str) -> List[Belief]:
        """Extract beliefs from reasoning text."""
        beliefs = []
        
        # Look for capability statements
        if "can" in reasoning.lower() or "able to" in reasoning.lower():
            beliefs.append(Belief(
                belief_type=BeliefType.CAPABILITY,
                statement=reasoning,
                confidence=0.6,
                source=BeliefSource.DERIVED,
            ))
        
        # Look for limitation statements
        if "cannot" in reasoning.lower() or "unable to" in reasoning.lower():
            beliefs.append(Belief(
                belief_type=BeliefType.LIMITATION,
                statement=reasoning,
                confidence=0.6,
                source=BeliefSource.DERIVED,
            ))
        
        return beliefs
    
    def _extract_from_context(self, context: Dict[str, Any]) -> List[Belief]:
        """Extract beliefs from decision context."""
        beliefs = []
        
        # Resource beliefs
        resources = context.get("available_resources", {})
        for resource, value in resources.items():
            beliefs.append(Belief(
                belief_type=BeliefType.RESOURCE,
                statement=f"Resource {resource} is available at level {value}",
                confidence=0.5,
                source=BeliefSource.ASSUMPTION,
            ))
        
        # Strategy beliefs
        objectives = context.get("objectives", [])
        for objective in objectives:
            beliefs.append(Belief(
                belief_type=BeliefType.STRATEGY,
                statement=f"Objective '{objective}' is achievable",
                confidence=0.5,
                source=BeliefSource.ASSUMPTION,
            ))
        
        return beliefs
    
    def _extract_from_option(self, option: Dict[str, Any]) -> List[Belief]:
        """Extract beliefs from a decision option."""
        beliefs = []
        
        # From benefits
        for benefit in option.get("benefits", []):
            beliefs.append(Belief(
                belief_type=BeliefType.CAPABILITY,
                statement=f"Action will result in: {benefit}",
                confidence=option.get("confidence", 0.5),
                source=BeliefSource.DERIVED,
            ))
        
        # From expected outcome
        expected_outcome = option.get("expected_outcome", {})
        if expected_outcome:
            beliefs.append(Belief(
                belief_type=BeliefType.SUCCESS,
                statement=f"Expected outcome: {expected_outcome}",
                confidence=option.get("confidence", 0.5),
                source=BeliefSource.DERIVED,
            ))
        
        return beliefs
    
    def _update_belief_with_outcome(self, belief: Belief, outcome: Dict[str, Any]) -> None:
        """Update a belief based on actual outcome."""
        success = outcome.get("success", False)
        
        if success:
            belief.evidence.append(f"Validated by successful outcome: {outcome}")
        else:
            belief.counter_evidence.append(f"Contradicted by failed outcome: {outcome}")
        
        belief.update_confidence(success)
    
    def _store_or_update_belief(self, belief: Belief) -> None:
        """Store a new belief or update an existing one."""
        # Check for similar existing beliefs
        for existing_id, existing_belief in self.beliefs.items():
            if self._beliefs_similar(belief, existing_belief):
                # Merge evidence
                existing_belief.evidence.extend(belief.evidence)
                existing_belief.counter_evidence.extend(belief.counter_evidence)
                # Update confidence
                existing_belief.confidence = (existing_belief.confidence + belief.confidence) / 2
                return
        
        # Store as new belief
        self.beliefs[belief.id] = belief
    
    def _beliefs_similar(self, belief1: Belief, belief2: Belief) -> bool:
        """Check if two beliefs are similar enough to merge."""
        if belief1.belief_type != belief2.belief_type:
            return False
        
        # Simple similarity check - in production, use semantic similarity
        words1 = set(belief1.statement.lower().split())
        words2 = set(belief2.statement.lower().split())
        
        intersection = words1 & words2
        union = words1 | words2
        
        if not union:
            return False
        
        similarity = len(intersection) / len(union)
        
        return similarity > 0.5
    
    def get_belief(self, belief_id: str) -> Optional[Belief]:
        """Get a belief by ID."""
        return self.beliefs.get(belief_id)
    
    def get_beliefs_by_type(self, belief_type: BeliefType) -> List[Belief]:
        """Get all beliefs of a specific type."""
        return [b for b in self.beliefs.values() if b.belief_type == belief_type]
    
    def get_high_confidence_beliefs(self, threshold: float = 0.8) -> List[Belief]:
        """Get beliefs with confidence above a threshold."""
        return [b for b in self.beliefs.values() if b.confidence >= threshold]
    
    def get_low_confidence_beliefs(self, threshold: float = 0.4) -> List[Belief]:
        """Get beliefs with confidence below a threshold."""
        return [b for b in self.beliefs.values() if b.confidence <= threshold]
    
    def get_belief_statistics(self) -> Dict[str, Any]:
        """Get statistics about beliefs."""
        total_beliefs = len(self.beliefs)
        
        by_type = {
            belief_type.value: len(self.get_beliefs_by_type(belief_type))
            for belief_type in BeliefType
        }
        
        avg_confidence = (
            sum(b.confidence for b in self.beliefs.values()) / total_beliefs
            if total_beliefs > 0 else 0.0
        )
        
        return {
            "total_beliefs": total_beliefs,
            "by_type": by_type,
            "average_confidence": avg_confidence,
            "high_confidence": len(self.get_high_confidence_beliefs()),
            "low_confidence": len(self.get_low_confidence_beliefs()),
        }
