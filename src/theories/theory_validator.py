"""theory_validator.py

Validates theories against new evidence and observations.
Ensures theories remain accurate and useful over time.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from enum import Enum

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from .theory_generator import Theory, TheoryStrength

logger = get_logger(__name__)


class ValidationResult(str, Enum):
    """Possible validation results."""
    CONFIRMED = "confirmed"  # Theory holds
    REJECTED = "rejected"  # Theory disproven
    WEAKENED = "weakened"  # Theory needs revision
    STRENGTHENED = "strengthened"  # Theory more confident
    INSUFFICIENT = "insufficient"  # Need more data


class ValidationReport(BaseModel):
    """Report from theory validation."""
    theory_id: str
    result: ValidationResult
    confidence_before: float
    confidence_after: float
    evidence_count: int
    counterexample_count: int
    notes: str = ""
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TheoryValidator:
    """Validates theories against evidence and observations."""
    
    def __init__(self):
        self.validation_history: Dict[str, List[ValidationReport]] = {}
        logger.info("TheoryValidator initialized")
    
    def validate_theory(
        self,
        theory: Theory,
        new_observations: List[str],
        expected_outcomes: List[str],
    ) -> ValidationReport:
        """Validate a theory against new observations."""
        confidence_before = theory.confidence
        
        # Count matches and mismatches
        matches = 0
        mismatches = 0
        
        for obs, expected in zip(new_observations, expected_outcomes):
            if self._observation_matches_prediction(obs, theory.predictions):
                matches += 1
            else:
                mismatches += 1
        
        total = matches + mismatches
        if total == 0:
            return ValidationReport(
                theory_id=theory.id,
                result=ValidationResult.INSUFFICIENT,
                confidence_before=confidence_before,
                confidence_after=confidence_before,
                evidence_count=len(theory.evidence),
                counterexample_count=len(theory.counterexamples),
                notes="No new observations to validate",
            )
        
        match_rate = matches / total
        
        # Update confidence based on match rate
        confidence_adjustment = (match_rate - 0.5) * 0.2  # Max 0.1 adjustment
        new_confidence = max(0.0, min(1.0, theory.confidence + confidence_adjustment))
        
        # Determine validation result
        if match_rate >= 0.9:
            result = ValidationResult.STRENGTHENED
            theory.evidence.extend(new_observations)
        elif match_rate >= 0.7:
            result = ValidationResult.CONFIRMED
            theory.evidence.extend(new_observations)
        elif match_rate >= 0.5:
            result = ValidationResult.WEAKENED
            theory.counterexamples.extend([obs for obs in new_observations if not self._observation_matches_prediction(obs, theory.predictions)])
        else:
            result = ValidationResult.REJECTED
            theory.counterexamples.extend(new_observations)
        
        theory.confidence = new_confidence
        theory.updated_at = datetime.now(timezone.utc)
        
        report = ValidationReport(
            theory_id=theory.id,
            result=result,
            confidence_before=confidence_before,
            confidence_after=new_confidence,
            evidence_count=len(theory.evidence),
            counterexample_count=len(theory.counterexamples),
            notes=f"Match rate: {match_rate:.1%}",
        )
        
        # Store validation history
        if theory.id not in self.validation_history:
            self.validation_history[theory.id] = []
        self.validation_history[theory.id].append(report)
        
        logger.info(f"Validated theory {theory.id}: {result.value} (confidence {confidence_before:.2f} -> {new_confidence:.2f})")
        return report
    
    def check_theory_applicability(
        self,
        theory: Theory,
        context: Dict[str, Any],
    ) -> Tuple[bool, float]:
        """Check if a theory applies in a given context."""
        if not theory.conditions:
            return True, 1.0
        
        applicable = True
        match_score = 0.0
        
        for condition in theory.conditions:
            # Simple heuristic: check if condition keywords appear in context
            condition_lower = condition.lower()
            context_str = str(context).lower()
            
            if condition_lower in context_str:
                match_score += 1.0
            else:
                applicable = False
        
        if theory.conditions:
            match_score /= len(theory.conditions)
        
        return applicable, match_score
    
    def detect_theory_conflicts(self, theories: List[Theory]) -> List[Tuple[str, str]]:
        """Detect conflicting theories."""
        conflicts = []
        
        for i, theory_a in enumerate(theories):
            for theory_b in theories[i+1:]:
                if self._theories_conflict(theory_a, theory_b):
                    conflicts.append((theory_a.id, theory_b.id))
        
        return conflicts
    
    def rank_theories(
        self,
        theories: List[Theory],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[Theory, float]]:
        """Rank theories by relevance and confidence."""
        scored = []
        
        for theory in theories:
            score = theory.confidence
            
            # Boost for strong theories
            if theory.strength == TheoryStrength.LAW:
                score *= 1.2
            elif theory.strength == TheoryStrength.STRONG:
                score *= 1.1
            
            # Boost for recent updates
            days_since_update = (datetime.now(timezone.utc) - theory.updated_at).days
            if days_since_update < 7:
                score *= 1.05
            
            # Check applicability if context provided
            if context:
                applicable, match_score = self.check_theory_applicability(theory, context)
                if not applicable:
                    score *= 0.5
                else:
                    score *= (0.5 + match_score * 0.5)
            
            scored.append((theory, score))
        
        # Sort by score
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored
    
    def get_validation_history(self, theory_id: str) -> List[ValidationReport]:
        """Get validation history for a theory."""
        return self.validation_history.get(theory_id, [])
    
    def _observation_matches_prediction(self, observation: str, predictions: List[str]) -> bool:
        """Check if an observation matches any prediction."""
        obs_lower = observation.lower()
        
        for prediction in predictions:
            pred_lower = prediction.lower()
            # Simple substring match
            if pred_lower in obs_lower or obs_lower in pred_lower:
                return True
        
        return False
    
    def _theories_conflict(self, theory_a: Theory, theory_b: Theory) -> bool:
        """Check if two theories conflict."""
        # Check for opposite predictions
        for pred_a in theory_a.predictions:
            for pred_b in theory_b.predictions:
                if "not" in pred_a.lower() and "not" not in pred_b.lower():
                    # Simple heuristic: if one has negation and the other doesn't
                    return False
        
        # Check if they make predictions about same concepts
        common_concepts = set(theory_a.source_concepts) & set(theory_b.source_concepts)
        if common_concepts and theory_a.domain == theory_b.domain:
            # Potential conflict if they predict different things
            if set(theory_a.predictions) != set(theory_b.predictions):
                return True
        
        return False
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get validation statistics."""
        total_validations = sum(len(history) for history in self.validation_history.values())
        
        result_counts = {}
        for history in self.validation_history.values():
            for report in history:
                result_counts[report.result.value] = result_counts.get(report.result.value, 0) + 1
        
        return {
            "total_validations": total_validations,
            "theories_validated": len(self.validation_history),
            "by_result": result_counts,
        }
