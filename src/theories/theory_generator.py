"""theory_generator.py

Generates generalized theories from concepts and observations.
Enables abstraction from specific instances to reusable principles.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Set
from enum import Enum
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class TheoryType(str, Enum):
    """Types of theories that can be generated."""
    CAUSAL = "causal"  # X causes Y
    CORRELATIONAL = "correlational"  # X correlates with Y
    PREDICTIVE = "predictive"  # If X then Y with probability P
    OPTIMIZATION = "optimization"  # Best way to achieve X
    GENERALIZATION = "generalization"  # X is a special case of Y
    PATTERN = "pattern"  # Recurring structure in X


class TheoryStrength(str, Enum):
    """Confidence levels for theories."""
    HYPOTHESIS = "hypothesis"  # Initial speculation
    TENTATIVE = "tentative"  # Some evidence
    SUPPORTED = "supported"  # Good evidence
    STRONG = "strong"  # Strong evidence
    LAW = "law"  # Well-established


@dataclass
class Theory:
    """A generalized theory abstracted from observations."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    theory_type: TheoryType = TheoryType.GENERALIZATION
    strength: TheoryStrength = TheoryStrength.HYPOTHESIS
    confidence: float = 0.5
    conditions: List[str] = field(default_factory=list)  # When does this apply?
    predictions: List[str] = field(default_factory=list)  # What does it predict?
    evidence: List[str] = field(default_factory=list)  # Supporting observations
    counterexamples: List[str] = field(default_factory=list)
    source_concepts: List[str] = field(default_factory=list)
    domain: str = ""  # Domain of applicability
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "theory_type": self.theory_type.value,
            "strength": self.strength.value,
            "confidence": self.confidence,
            "conditions": self.conditions,
            "predictions": self.predictions,
            "evidence_count": len(self.evidence),
            "counterexample_count": len(self.counterexamples),
            "source_concepts": self.source_concepts,
            "domain": self.domain,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
        }


class TheoryGenerator:
    """Generates theories from concepts and observations."""
    
    def __init__(self):
        self.theories: Dict[str, Theory] = {}
        logger.info("TheoryGenerator initialized")
    
    def generate_from_pattern(
        self,
        pattern_name: str,
        observations: List[str],
        concepts: List[str],
        domain: str = "",
    ) -> Theory:
        """Generate a theory from a recurring pattern in observations."""
        theory = Theory(
            name=f"Pattern: {pattern_name}",
            description=f"Recurring pattern observed across {len(observations)} instances",
            theory_type=TheoryType.PATTERN,
            strength=TheoryStrength.TENTATIVE,
            confidence=min(0.9, 0.3 + len(observations) * 0.1),
            evidence=observations,
            source_concepts=concepts,
            domain=domain,
        )
        
        # Extract conditions from observations
        theory.conditions = self._extract_conditions(observations)
        
        # Generate predictions
        theory.predictions = self._generate_predictions(theory.conditions)
        
        self.theories[theory.id] = theory
        logger.info(f"Generated pattern theory: {theory.name}")
        return theory
    
    def generate_causal_theory(
        self,
        cause: str,
        effect: str,
        observations: List[str],
        confidence: float = 0.5,
        domain: str = "",
    ) -> Theory:
        """Generate a causal theory from observed cause-effect pairs."""
        theory = Theory(
            name=f"Causal: {cause} -> {effect}",
            description=f"{cause} causes {effect}",
            theory_type=TheoryType.CAUSAL,
            strength=self._strength_from_confidence(confidence),
            confidence=confidence,
            conditions=[f"When {cause} occurs"],
            predictions=[f"{effect} will follow"],
            evidence=observations,
            source_concepts=[cause, effect],
            domain=domain,
        )
        
        self.theories[theory.id] = theory
        logger.info(f"Generated causal theory: {theory.name}")
        return theory
    
    def generate_optimization_theory(
        self,
        goal: str,
        strategy: str,
        improvement_metric: str,
        improvement_value: float,
        observations: List[str],
    ) -> Theory:
        """Generate an optimization theory from performance improvements."""
        theory = Theory(
            name=f"Optimization: {goal}",
            description=f"{strategy} improves {goal} by {improvement_value:.1%}",
            theory_type=TheoryType.OPTIMIZATION,
            strength=TheoryStrength.SUPPORTED if improvement_value > 0.1 else TheoryStrength.TENTATIVE,
            confidence=min(0.95, 0.5 + improvement_value),
            conditions=[f"When applying {strategy}"],
            predictions=[f"{improvement_metric} improves by {improvement_value:.1%}"],
            evidence=observations,
            source_concepts=[goal, strategy],
            domain="optimization",
        )
        
        self.theories[theory.id] = theory
        logger.info(f"Generated optimization theory: {theory.name}")
        return theory
    
    def generate_generalization(
        self,
        specific_cases: List[str],
        general_concept: str,
        confidence: float = 0.5,
    ) -> Theory:
        """Generate a generalization theory from specific cases."""
        theory = Theory(
            name=f"Generalization: {general_concept}",
            description=f"{general_concept} generalizes {len(specific_cases)} specific cases",
            theory_type=TheoryType.GENERALIZATION,
            strength=self._strength_from_confidence(confidence),
            confidence=confidence,
            conditions=[f"When instances match {general_concept} pattern"],
            predictions=[f"Behavior consistent with {general_concept}"],
            evidence=specific_cases,
            source_concepts=[general_concept] + specific_cases[:3],
            domain="generalization",
        )
        
        self.theories[theory.id] = theory
        logger.info(f"Generated generalization theory: {theory.name}")
        return theory
    
    def generate_predictive_theory(
        self,
        antecedent: str,
        consequent: str,
        probability: float,
        observations: List[str],
        domain: str = "",
    ) -> Theory:
        """Generate a predictive theory with probability."""
        theory = Theory(
            name=f"Predictive: {antecedent} => {consequent}",
            description=f"If {antecedent}, then {consequent} with {probability:.1%} probability",
            theory_type=TheoryType.PREDICTIVE,
            strength=self._strength_from_confidence(probability),
            confidence=probability,
            conditions=[f"When {antecedent} occurs"],
            predictions=[f"{consequent} occurs with {probability:.1%} probability"],
            evidence=observations,
            source_concepts=[antecedent, consequent],
            domain=domain,
        )
        
        self.theories[theory.id] = theory
        logger.info(f"Generated predictive theory: {theory.name}")
        return theory
    
    def strengthen_theory(
        self,
        theory_id: str,
        new_evidence: str,
        confidence_boost: float = 0.05,
    ) -> Optional[Theory]:
        """Strengthen a theory with new evidence."""
        if theory_id not in self.theories:
            return None
        
        theory = self.theories[theory_id]
        theory.evidence.append(new_evidence)
        theory.confidence = min(1.0, theory.confidence + confidence_boost)
        theory.strength = self._strength_from_confidence(theory.confidence)
        theory.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Strengthened theory {theory_id}: confidence {theory.confidence:.2f}")
        return theory
    
    def weaken_theory(
        self,
        theory_id: str,
        counterexample: str,
        confidence_penalty: float = 0.1,
    ) -> Optional[Theory]:
        """Weaken a theory with a counterexample."""
        if theory_id not in self.theories:
            return None
        
        theory = self.theories[theory_id]
        theory.counterexamples.append(counterexample)
        theory.confidence = max(0.0, theory.confidence - confidence_penalty)
        theory.strength = self._strength_from_confidence(theory.confidence)
        theory.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Weakened theory {theory_id}: confidence {theory.confidence:.2f}")
        return theory
    
    def find_theories_by_concept(self, concept: str) -> List[Theory]:
        """Find all theories involving a specific concept."""
        return [
            t for t in self.theories.values()
            if concept in t.source_concepts or concept in t.name.lower()
        ]
    
    def find_theories_by_domain(self, domain: str) -> List[Theory]:
        """Find all theories in a specific domain."""
        return [t for t in self.theories.values() if t.domain == domain]
    
    def get_theory(self, theory_id: str) -> Optional[Theory]:
        """Retrieve a theory by ID."""
        return self.theories.get(theory_id)
    
    def list_theories(
        self,
        min_confidence: float = 0.0,
        theory_type: Optional[TheoryType] = None,
    ) -> List[Theory]:
        """List theories with optional filters."""
        theories = list(self.theories.values())
        
        if min_confidence > 0:
            theories = [t for t in theories if t.confidence >= min_confidence]
        
        if theory_type:
            theories = [t for t in theories if t.theory_type == theory_type]
        
        return sorted(theories, key=lambda t: t.confidence, reverse=True)
    
    def _extract_conditions(self, observations: List[str]) -> List[str]:
        """Extract common conditions from observations."""
        # Simple heuristic: look for common prefixes
        if not observations:
            return []
        
        # Find common words across observations
        words_sets = [set(obs.lower().split()) for obs in observations]
        common_words = set.intersection(*words_sets) if words_sets else set()
        
        conditions = []
        if common_words:
            conditions.append(f"When {' and '.join(list(common_words)[:3])} are present")
        
        return conditions
    
    def _generate_predictions(self, conditions: List[str]) -> List[str]:
        """Generate predictions based on conditions."""
        predictions = []
        for condition in conditions:
            # Simple transformation: condition -> prediction
            if "when" in condition.lower():
                prediction = condition.lower().replace("when", "then")
                predictions.append(prediction.capitalize())
        
        if not predictions:
            predictions.append("Expected behavior follows pattern")
        
        return predictions
    
    def _strength_from_confidence(self, confidence: float) -> TheoryStrength:
        """Map confidence to theory strength."""
        if confidence >= 0.9:
            return TheoryStrength.LAW
        elif confidence >= 0.75:
            return TheoryStrength.STRONG
        elif confidence >= 0.5:
            return TheoryStrength.SUPPORTED
        elif confidence >= 0.3:
            return TheoryStrength.TENTATIVE
        else:
            return TheoryStrength.HYPOTHESIS
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get theory generation statistics."""
        type_counts = {}
        for theory in self.theories.values():
            type_counts[theory.theory_type.value] = type_counts.get(theory.theory_type.value, 0) + 1
        
        strength_counts = {}
        for theory in self.theories.values():
            strength_counts[theory.strength.value] = strength_counts.get(theory.strength.value, 0) + 1
        
        return {
            "total_theories": len(self.theories),
            "by_type": type_counts,
            "by_strength": strength_counts,
            "average_confidence": sum(t.confidence for t in self.theories.values()) / len(self.theories) if self.theories else 0.0,
        }
